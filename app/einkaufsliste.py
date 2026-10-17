"""Einkaufsliste: planen und erst nach dem Kauf in den Vorrat übernehmen."""
from datetime import date, timedelta

import streamlit as st

from app import ressourcen
from app.datenbank import entferne_einkauf, kaufe_ein, lade_einkaufsliste, merke_einkauf
from app.gestaltung import EINHEITEN, kopf, leer, menge_text
from app.rezeptansicht import zeige_meldung

kopf('Gut geplant', 'Dein Einkauf', 'Erst auf die Liste. Nach dem Einkauf in deinen Vorrat.')
zeige_meldung()
person = st.session_state.person
wb = ressourcen.wissensbasis()

with st.expander('Etwas auf die Liste setzen', icon=':material/add:'):
    with st.form('eigener_einkauf', clear_on_submit=True):
        zutat = st.selectbox('Zutat', wb.zutaten_zur_auswahl(ohne_grundstock=False),
                            format_func=wb.namen.get, index=None, key='einkauf_zutat')
        if st.form_submit_button('Auf die Liste', type='primary'):
            if zutat:
                with ressourcen.datenbank() as conn:
                    neu = merke_einkauf(conn, person, zutat, None, wb.eigenschaft(zutat, 'einheit'))
                st.session_state.meldung = 'Zur Einkaufsliste hinzugefügt.' if neu else 'Steht bereits auf deiner Liste.'
                st.rerun()
            else:
                st.warning('Wähle zuerst eine Zutat.')

with ressourcen.datenbank() as conn:
    liste = lade_einkaufsliste(conn, person)
if not liste:
    leer('Alles auf deiner Liste ist erledigt.',
         'Füge etwas hinzu oder merke eine Einkaufsidee bei deinen Rezeptvorschlägen vor.')
    st.page_link('app/startseite.py', label='Zu deinen Vorschlägen', icon=':material/arrow_forward:')
else:
    st.caption(f'{len(liste)} Zutaten vorgemerkt. Öffne einen Eintrag, sobald du ihn gekauft hast.')
    for artikel in liste:
        artikel_id = artikel['id']
        name = wb.namen.get(artikel['zutat'], artikel['zutat'])
        with st.expander(f"{name} · {menge_text(artikel['menge'], artikel['einheit'])}"):
            with st.form(f'einkauf_kaufen_{artikel_id}'):
                st.caption('Prüfe die tatsächliche Menge und das Datum auf der Packung.')
                menge = st.number_input('Gekaufte Menge', min_value=0.0, value=artikel['menge'],
                                        key=f'kauf_menge_{artikel_id}')
                standard = artikel['einheit'] if artikel['einheit'] in EINHEITEN else 'g'
                einheit = st.selectbox('Einheit', EINHEITEN, index=EINHEITEN.index(standard),
                                       key=f'kauf_einheit_{artikel_id}')
                haltbar = wb.eigenschaft(artikel['zutat'], 'haltbarTage')
                ablauf = st.date_input('Ablaufdatum', value=date.today() + timedelta(days=haltbar) if haltbar else None,
                                      format='DD.MM.YYYY', key=f'kauf_datum_{artikel_id}')
                if st.form_submit_button('Gekauft · in den Vorrat', type='primary'):
                    try:
                        with ressourcen.datenbank() as conn:
                            kaufe_ein(conn, person, artikel_id, menge, einheit, ablauf)
                    except ValueError as fehler:
                        st.error(str(fehler))
                    else:
                        st.session_state.meldung = f'{name} ist jetzt in deinem Vorrat.'
                        st.rerun()
            if st.button('Von der Liste entfernen', key=f'einkauf_entfernen_{artikel_id}'):
                with ressourcen.datenbank() as conn:
                    entferne_einkauf(conn, person, artikel_id)
                st.session_state.meldung = f'{name} von der Einkaufsliste entfernt.'
                st.rerun()
