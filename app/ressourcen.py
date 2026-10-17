"""Datenbankverbindung, Wissensbasis und ML-Modell, die sich alle Seiten teilen.

st.cache_resource sorgt dafür, dass Wissensbasis und Modell nur einmal erzeugt werden
und nicht bei jedem Klick neu. Die Datenbankverbindung dagegen wird bei jedem
Seitenaufruf neu geöffnet, weil Turso unbenutzte Verbindungen nach ca. 10 Sekunden beendet.
"""
from contextlib import contextmanager

import streamlit as st

from app.datenbank import SCHEMA, lade_bewertungen, lade_grundstock, oeffne, richte_ein
from ml.trainiere import trainiere_falls_moeglich
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis


@st.cache_resource
def _datenbank_einrichten(schema):
    # Tabellen nur einmal pro App-Start prüfen, nicht bei jedem Klick.
    # Das Schema dient als Schlüssel für den Cache: Ändert es sich mit einem Deploy,
    # wird neu eingerichtet (neue Spalten), auch wenn die App nicht neu gestartet wurde.
    conn = oeffne()
    try:
        richte_ein(conn)
    finally:
        conn.close()
    return True


def verbindung():
    """Frische Verbindung für den aktuellen Seitenaufruf."""
    _datenbank_einrichten(SCHEMA)
    return oeffne()


@contextmanager
def datenbank():
    """Verbindungen nur für die Dauer der Abfrage offen halten, auch bei Fehlern."""
    conn = verbindung()
    try:
        yield conn
    finally:
        conn.close()


def beginne_seitenaufruf():
    """Nur innerhalb dieses Aufrufs wiederverwenden, nie über Personen hinweg.

    Kein TTL-Cache für persönliche Daten: Nach jeder Aktion oder Navigation wird
    frisch gelesen. Turso-Verbindungen bleiben nicht in der Sitzung liegen.
    """
    st.session_state['_aufruf_cache'] = {}


def _einmal(name, laden):
    cache = st.session_state.get('_aufruf_cache')
    if cache is None:
        return laden()  # Auch eigenständige Dialoge und Tests funktionieren.
    schluessel = (st.session_state.get('person'), name)
    if schluessel not in cache:
        cache[schluessel] = laden()
    return cache[schluessel]


@st.cache_resource
def _basis():
    return Wissensbasis()


def wissensbasis():
    """Haushaltskontext pro Aufruf; keine Nutzerpräferenzen im gemeinsamen Cache."""
    person = st.session_state.get("person")
    if not person:
        return _basis()
    def laden():
        with datenbank() as conn:
            return _basis().mit_grundstock(lade_grundstock(conn, person))
    return _einmal('wissensbasis', laden)


@st.cache_resource(max_entries=1)
def _modell_fuer_kochbewertungen(anzahl_kochbewertungen):
    # anzahl_kochbewertungen dient nur als Schlüssel für den Cache:
    # Sobald eine Kochbewertung dazukommt, wird neu trainiert.
    with datenbank() as conn:
        bewertungen = lade_bewertungen(conn, nur_gekocht=True)
    return trainiere_falls_moeglich(bewertungen, lade_rezepte(), _basis())


def ml_modell():
    """Aktuelles ML-Modell, oder None, solange es zu wenig Bewertungen gibt."""
    def laden():
        with datenbank() as conn:
            anzahl = conn.execute("SELECT COUNT(*) FROM bewertung WHERE gekocht = 1").fetchone()[0]
        return _modell_fuer_kochbewertungen(anzahl)
    return _einmal('modell', laden)
