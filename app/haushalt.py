"""Dauerhafter Grundstock des angemeldeten Haushalts, ohne Mengen oder Ablaufdaten."""
import streamlit as st

from app import ressourcen
from app.datenbank import speichere_grundstock
from app.rezeptansicht import zeige_meldung
from wissensbasis.grundstock import STANDARD_GRUNDSTOCK

st.title("Grundstock")
zeige_meldung()
wb = ressourcen.wissensbasis()
st.write("Welche Zutaten hast du normalerweise zu Hause? Diese Auswahl gilt bei Menü- "
         "und Einkaufsvorschlägen als vorhanden, ohne Mengen und Ablaufdaten.")
st.caption("Nur einzeln ausgewählte Zutaten zählen. Neue Gewürze oder andere Unterarten "
           "werden nicht automatisch vorausgesetzt.")
with st.form("grundstock_form"):
    auswahl = st.multiselect("Normalerweise vorhanden", wb.zutaten_zur_auswahl(ohne_grundstock=False),
                            default=sorted(wb.grundstock_ids), format_func=wb.namen.get,
                            key=f"grundstock_auswahl_{st.session_state.person}")
    if st.form_submit_button("Grundstock speichern", type="primary"):
        speichere_grundstock(ressourcen.verbindung(), st.session_state.person, auswahl, wb)
        st.session_state.meldung = "Dein Grundstock wurde gespeichert."
        st.rerun()
if st.button("Standardliste wiederherstellen"):
    speichere_grundstock(ressourcen.verbindung(), st.session_state.person, STANDARD_GRUNDSTOCK, wb)
    del st.session_state[f"grundstock_auswahl_{st.session_state.person}"]
    st.session_state.meldung = "Die Standardliste wurde wiederhergestellt."
    st.rerun()
st.info("Zutaten, die du nur gelegentlich besitzt oder deren Restmenge du verfolgen möchtest, "
        "erfasst du im Vorrat. Künstliche Vorräte findest du separat unter «Testszenarien».")
