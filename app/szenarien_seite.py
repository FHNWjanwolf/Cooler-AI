"""Künstliche Vorräte betrachten und prüfen, ohne echte Vorräte zu verändern."""
import json
import streamlit as st

from app.testszenarien import lade_szenarien, pruefe_szenario, szenario_vorrat
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis

st.title("Künstliche Vorräte · Testszenarien")
st.write("Gespeicherte Beispielsituationen mit konkreten Mengen und Ablaufdaten. "
         "Die Prüfung verwendet den festen Stichtag des Szenarios.")
st.info("Diese Vorschau verändert weder deinen Vorrat noch deinen Grundstock und erzeugt keine Bewertungen.")
szenario = st.selectbox("Testszenario", lade_szenarien(), format_func=lambda s: s["titel"])
wb, vorrat = szenario_vorrat(szenario, Wissensbasis())
st.caption("Stichtag: " + szenario["datum"])
st.caption("Grundstock dieses Szenarios: " + (", ".join(wb.grundstock()) or "leer"))
st.dataframe([
    {"Zutat": wb.namen[z["zutat"]], "Menge": z["menge"], "Einheit": z["einheit"],
     "Ablaufdatum": z["ablaufdatum"], "Geöffnet am": z.get("geoeffnet_am"),
     "Tage bis effektivem Ablauf": v["tage"]}
    for z, v in zip(szenario["zutaten"], vorrat)
], hide_index=True)
stimmt, kandidaten = pruefe_szenario(szenario, wb, lade_rezepte())
st.subheader("Ergebnis der Wissensbasis")
if stimmt:
    st.success("Das Ergebnis entspricht dem gespeicherten erwarteten Ergebnis.")
else:
    st.error("Das Ergebnis weicht vom gespeicherten erwarteten Ergebnis ab.")
for k in kandidaten:
    st.markdown("**" + k["rezept"]["titel"] + "**")
    for grund in k["begruendungen"]:
        st.write(grund)
if not kandidaten:
    st.write("Mit diesem Testszenario ist kein Rezept geeignet.")
st.caption("Erwartete Rezept-IDs: " + (", ".join(szenario["erwartete_rezepte"]) or "keine"))
st.download_button("Testszenario als JSON herunterladen", data=json.dumps(
    szenario, ensure_ascii=False, indent=2), file_name=szenario["id"] + ".json", mime="application/json")
