"""Startseite nach der Anmeldung: Vorrat links, Menüs und Einkaufsideen rechts."""
import pandas as pd
import streamlit as st

from app.datenbank import lade_vorrat, vorrat_als_liste
from app.einkauf import zeige_einkaufsideen
from app.rezeptansicht import zeige_meldung, zeige_vorschlaege
from app.ressourcen import verbindung, wissensbasis

st.title("Was koche ich heute?")
zeige_meldung()
wb = wissensbasis()
vorrat = lade_vorrat(verbindung(), st.session_state.person, wb)
links, rechts = st.columns([1, 2], gap="large")

with links:
    st.subheader("Dein Vorrat")
    if st.button("Vorrat anpassen", icon="🥕", use_container_width=True):
        st.switch_page("app/vorrat.py")
    if vorrat.empty:
        st.info("Dein Vorrat ist noch leer. Erfasse, was du zu Hause hast.")
    else:
        for eintrag in vorrat.itertuples():
            with st.container(border=True):
                menge = f"{eintrag.menge:g} {eintrag.einheit or ''}" if pd.notna(eintrag.menge) else "Menge offen"
                st.markdown(f"**{eintrag.name}** · {menge}")
                if pd.isna(eintrag.tage):
                    st.caption("Ohne Ablaufdatum")
                elif eintrag.tage < 0:
                    st.caption("⚫ Abgelaufen – vor dem Verwenden prüfen")
                elif eintrag.tage <= 1:
                    st.caption("🔴 Heute oder morgen verbrauchen")
                elif eintrag.tage <= 3:
                    st.caption(f"🟠 Läuft in {eintrag.tage} Tagen ab")
                else:
                    st.caption(f"Läuft in {eintrag.tage} Tagen ab")
    st.caption("Immer vorhanden: " + ", ".join(wb.grundstock()))

with rechts:
    st.subheader("Deine Menüvorschläge")
    zeige_vorschlaege(vorrat)
    st.divider()
    zeige_einkaufsideen(vorrat_als_liste(vorrat))
