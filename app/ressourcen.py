"""Datenbankverbindung, Wissensbasis und ML-Modell, die sich alle Seiten teilen.

st.cache_resource sorgt dafür, dass beides nur einmal erzeugt wird
und nicht bei jedem Klick neu.
"""
import streamlit as st

from app.datenbank import lade_bewertungen, verbinde
from ml.trainiere import trainiere_falls_moeglich
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis


@st.cache_resource
def verbindung():
    return verbinde()


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
