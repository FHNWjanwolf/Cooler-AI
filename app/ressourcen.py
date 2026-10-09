"""Datenbankverbindung, Wissensbasis und ML-Modell, die sich alle Seiten teilen.

st.cache_resource sorgt dafür, dass Wissensbasis und Modell nur einmal erzeugt werden
und nicht bei jedem Klick neu. Die Datenbankverbindung dagegen wird bei jedem
Seitenaufruf neu geöffnet, weil Turso unbenutzte Verbindungen nach ca. 10 Sekunden beendet.
"""
import streamlit as st

from app.datenbank import lade_bewertungen, oeffne, richte_ein
from ml.trainiere import trainiere_falls_moeglich
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis


@st.cache_resource
def _datenbank_einrichten():
    # Tabellen nur einmal pro App-Start prüfen, nicht bei jedem Klick.
    richte_ein(oeffne())
    return True


def verbindung():
    """Frische Verbindung für den aktuellen Seitenaufruf."""
    _datenbank_einrichten()
    return oeffne()


@st.cache_resource
def wissensbasis():
    return Wissensbasis()


@st.cache_resource(max_entries=1)
def _modell_fuer(anzahl_bewertungen):
    # anzahl_bewertungen dient nur als Schlüssel für den Cache:
    # Sobald eine neue Bewertung dazukommt, wird neu trainiert.
    return trainiere_falls_moeglich(lade_bewertungen(verbindung()), lade_rezepte(), wissensbasis())


def ml_modell():
    """Aktuelles ML-Modell, oder None, solange es zu wenig Bewertungen gibt."""
    anzahl = verbindung().execute("SELECT COUNT(*) FROM bewertung").fetchone()[0]
    return _modell_fuer(anzahl)
