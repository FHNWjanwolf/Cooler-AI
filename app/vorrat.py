"""Seite: Vorrat erfassen, bearbeiten und entfernen. Dazu Einkaufsideen."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.datenbank import aktualisiere, fuege_hinzu, lade_vorrat, loesche, vorrat_als_liste
from app.ressourcen import ml_modell, verbindung, wissensbasis
from ml.ranking import einkaufsideen
from wissensbasis.eignung import fast_geeignete, lade_rezepte


def zeige_einkaufsideen(vorrat_liste):
    """Welche eine Zutat würde die meisten passenden Rezepte freischalten?"""
    st.subheader("Einkaufsideen")
    modell = ml_modell()
    ideen = einkaufsideen(fast_geeignete(lade_rezepte(), vorrat_liste, wb), wb, modell)
    if not ideen:
        st.caption("Gerade fehlt keinem passenden Rezept genau eine Zutat.")
        return

    for idee in ideen[:3]:
        rezepte = idee["rezepte"]
        anzahl = "1 Rezept" if len(rezepte) == 1 else f"{len(rezepte)} Rezepte"
        with st.container(border=True):
            st.markdown(f"**{wb.namen[idee['zutat']]}** kaufen → {anzahl}: "
                        + ", ".join(r["rezept"]["titel"] for r in rezepte))
            if idee["gerettet"]:
                st.caption("Verwertet, was bald abläuft: " + ", ".join(wb.namen[z] for z in idee["gerettet"]))

    if modell is None:
        st.caption("Sortiert nach Anzahl Rezepte und geretteten Zutaten. "
                   "Sobald es genug Bewertungen gibt, zählen auch eure Vorlieben (ML-Modell).")
    else:
        st.caption("Sortiert nach euren Vorlieben (ML-Modell) und geretteten Zutaten.")


def status(tage):
    if pd.isna(tage):
        return "⚪ ohne Datum"
    if tage < 0:
        return "⚫ abgelaufen"
    if tage <= 1:
        return "🔴 heute verbrauchen"
    if tage <= 3:
        return "🟠 bald"
    return "🟢 ok"


st.title("Vorrat")
conn = verbindung()
wb = wissensbasis()

with st.form("erfassen", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 1.5, 2])
    zutat = c1.selectbox("Zutat", wb.zutaten_zur_auswahl(), format_func=wb.namen.get,
                         index=None, placeholder="Tippen zum Suchen")
    menge = c2.number_input("Menge", min_value=0.0, step=50.0, value=None)
    ablauf = c3.date_input("Ablaufdatum", value=None, format="DD.MM.YYYY",
                           help="Leer lassen, um die übliche Haltbarkeit zu übernehmen.")
    if st.form_submit_button("Hinzufügen", type="primary"):
        if zutat is None:
            st.warning("Wähle zuerst eine Zutat aus.")
        else:
            einheit = wb.eigenschaft(zutat, "einheit")
            haltbar = wb.eigenschaft(zutat, "haltbarTage")
            if ablauf is None and haltbar is not None:
                ablauf = date.today() + timedelta(days=haltbar)
            fuege_hinzu(conn, zutat, menge, einheit, ablauf)
            menge_text = f"{menge:g} {einheit} " if menge else ""
            st.success(f"{menge_text}{wb.namen[zutat]} hinzugefügt.")

st.caption("Immer vorhanden: " + ", ".join(wb.grundstock()))

vorrat = lade_vorrat(conn, wb)
if vorrat.empty:
    st.info("Der Vorrat ist leer. Füge oben deine erste Zutat hinzu.")
else:
    vorrat["status"] = [status(t) for t in vorrat["tage"]]
    vorrat["aufgebraucht"] = False
    bearbeitet = st.data_editor(
        vorrat,
        hide_index=True,
        column_order=["status", "name", "menge", "einheit", "ablaufdatum", "geoeffnet_am", "aufgebraucht"],
        disabled=["status", "name", "einheit"],
        column_config={
            "status": "Status",
            "name": "Zutat",
            "menge": st.column_config.NumberColumn("Menge", min_value=0),
            "einheit": "Einheit",
            "ablaufdatum": st.column_config.DateColumn("Ablaufdatum", format="DD.MM.YYYY"),
            "geoeffnet_am": st.column_config.DateColumn("Geöffnet am", format="DD.MM.YYYY"),
            "aufgebraucht": st.column_config.CheckboxColumn("Aufgebraucht"),
        },
        key="vorrat_editor",
    )
    st.caption("Wer ein Öffnungsdatum einträgt, bekommt ein angepasstes Ablaufdatum "
               "(Haltbarkeit nach dem Öffnen aus der Wissensbasis).")
    if st.button("Änderungen speichern"):
        for eintrag_id, r in bearbeitet.iterrows():
            leer = pd.notna(r.menge) and r.menge <= 0
            if r.aufgebraucht or leer:
                loesche(conn, int(eintrag_id))
            else:
                menge = float(r.menge) if pd.notna(r.menge) else None
                aktualisiere(conn, int(eintrag_id), menge, r.ablaufdatum, r.geoeffnet_am)
        st.rerun()

    zeige_einkaufsideen(vorrat_als_liste(vorrat))
