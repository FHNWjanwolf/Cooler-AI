"""Seite mit allen Menüvorschlägen."""
import streamlit as st

from app.datenbank import lade_vorrat
from app.rezeptansicht import zeige_meldung, zeige_vorschlaege
from app.ressourcen import verbindung, wissensbasis

st.title("Was koche ich heute?")
zeige_meldung()
zeige_vorschlaege(lade_vorrat(verbindung(), st.session_state.person, wissensbasis()))
