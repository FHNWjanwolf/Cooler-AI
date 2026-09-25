"""Cooler AI – Einstiegspunkt der App.

Start (im Hauptordner):  streamlit run cooler_ai.py
"""
import streamlit as st

st.set_page_config(page_title="Cooler AI", page_icon="🥕")

seiten = st.navigation([
    st.Page("app/vorschlaege.py", title="Was koche ich heute?", icon="🍳", default=True),
    st.Page("app/vorrat.py", title="Vorrat", icon="🥕"),
])
seiten.run()
