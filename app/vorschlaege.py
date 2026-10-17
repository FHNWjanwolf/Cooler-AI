"""Passende Rezepte mit Suche und Filtern."""
import streamlit as st

from app import ressourcen
from app.datenbank import lade_vorrat
from app.gestaltung import kopf
from app.rezeptansicht import zeige_meldung, zeige_vorschlaege

kopf('Für deine Küche', 'Deine Rezepte', 'Passende Gerichte für das, was du schon zu Hause hast.')
zeige_meldung()
wb = ressourcen.wissensbasis()
with ressourcen.datenbank() as conn:
    vorrat = lade_vorrat(conn, st.session_state.person, wb)
zeige_vorschlaege(vorrat)
