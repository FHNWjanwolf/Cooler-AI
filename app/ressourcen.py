"""Datenbankverbindung und Wissensbasis, die sich alle Seiten teilen.

st.cache_resource sorgt dafür, dass beides nur einmal erzeugt wird
und nicht bei jedem Klick neu.
"""
import streamlit as st

from app.datenbank import verbinde
from wissensbasis.wissen import Wissensbasis


@st.cache_resource
def verbindung():
    return verbinde()


@st.cache_resource
def wissensbasis():
    return Wissensbasis()
