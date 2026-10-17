"""Gemeinsame Einkaufsideen mit direkter Übernahme in den Vorrat."""
from datetime import date, timedelta

import streamlit as st

from app.datenbank import lade_einkaufsliste, merke_einkauf
from app import ressourcen
from app.verbrauch import umrechnen
from ml.ranking import einkaufsideen
from wissensbasis.eignung import fast_geeignete, lade_rezepte


def kaufmenge(idee, wb):
    """Menge für das bestplatzierte freigeschaltete Rezept in der Vorratseinheit."""
    einheit = wb.eigenschaft(idee["zutat"], "einheit")
    rezept = idee["rezepte"][0]["rezept"]
    zutaten = [z for z in rezept["zutaten"] if z["pflicht"]
               and wb.ist_ein(idee["zutat"], z["zutat"])]
    mengen = [umrechnen(z["menge"], z["einheit"], einheit) for z in zutaten]
    menge = sum(mengen) if mengen and all(m is not None for m in mengen) else None
    return menge, einheit


def zeige_einkaufsideen(vorrat_liste):
    st.subheader("Einkaufsideen")
    if not vorrat_liste:
        st.caption("Mit deinem ersten Vorrat zeigen wir dir, welche Einkäufe passende Menüs ergänzen.")
        return
    wb = ressourcen.wissensbasis()
    with ressourcen.datenbank() as conn:
        auf_liste = {a['zutat'] for a in lade_einkaufsliste(conn, st.session_state.person)}
    ideen = einkaufsideen(fast_geeignete(lade_rezepte(), vorrat_liste, wb), wb, ressourcen.ml_modell())
    if not ideen:
        st.caption("Gerade fehlt keinem passenden Rezept genau eine Zutat.")
        return
    for idee in ideen[:3]:
        rezepte = idee["rezepte"]
        menge, einheit = kaufmenge(idee, wb)
        haltbar = wb.eigenschaft(idee["zutat"], "haltbarTage")
        ablauf = date.today() + timedelta(days=haltbar) if haltbar is not None else None
        name = wb.namen[idee["zutat"]]
        menge_text = f"{menge:g} {einheit} " if menge is not None else ""
        anzahl = "1 Rezept" if len(rezepte) == 1 else f"{len(rezepte)} Rezepte"
        with st.container(border=True):
            st.markdown(f"**{menge_text}{name}** ergänzen → {anzahl}: "
                        + ", ".join(r["rezept"]["titel"] for r in rezepte))
            if menge is not None:
                st.caption(f"Menge für {rezepte[0]['rezept']['titel']} "
                           f"({rezepte[0]['rezept']['portionen']} Portionen).")
            else:
                st.caption("Rezeptmenge nicht bestimmbar. Wird mit offener Menge hinzugefügt.")
            if ablauf is not None:
                st.caption(f"Vorgeschlagenes Ablaufdatum: {ablauf:%d.%m.%Y}. Im Vorrat anpassbar.")
            if idee["gerettet"]:
                st.caption("Verwertet, was bald abläuft: " + ", ".join(wb.namen[z] for z in idee["gerettet"]))
            if st.button('Steht auf deiner Liste' if idee['zutat'] in auf_liste else 'Auf die Einkaufsliste',
                         key=f"einkauf_{idee['zutat']}", disabled=idee['zutat'] in auf_liste,
                         icon=':material/shopping_basket:'):
                with ressourcen.datenbank() as conn:
                    merke_einkauf(conn, st.session_state.person, idee['zutat'], menge, einheit)
                st.session_state.meldung = f'{name} auf die Einkaufsliste gesetzt.'
                st.rerun()
    st.page_link('app/einkaufsliste.py', label='Einkaufsliste öffnen', icon=':material/arrow_forward:')
