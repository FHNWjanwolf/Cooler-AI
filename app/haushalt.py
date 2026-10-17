"""Profil, expliziter Grundstock und getrennte Projektwerkzeuge."""
import streamlit as st

from app import ressourcen
from app.datenbank import speichere_grundstock
from app.gestaltung import kopf
from app.rezeptansicht import zeige_meldung
from wissensbasis.grundstock import STANDARD_GRUNDSTOCK


def setze_entwicklermodus():
    # Der Modus bleibt auch auf Seiten erhalten, die dieses Widget nicht zeigen.
    st.session_state.entwicklermodus = st.session_state._testsicht


kopf('Deine Küche einrichten', 'Einstellungen')
zeige_meldung()
wb = ressourcen.wissensbasis()
st.subheader('Dein Grundstock')
st.write('Salz, Öl und andere Zutaten, die du normalerweise zu Hause hast. '
         'Sie zählen bei Rezepten als vorhanden, ohne Mengen oder Ablaufdatum.')
with st.form('grundstock_form'):
    auswahl = st.multiselect('Normalerweise vorhanden', wb.zutaten_zur_auswahl(ohne_grundstock=False),
                            default=sorted(wb.grundstock_ids), format_func=wb.namen.get,
                            key=f'grundstock_auswahl_{st.session_state.person}')
    if st.form_submit_button('Grundstock speichern', type='primary'):
        with ressourcen.datenbank() as conn:
            speichere_grundstock(conn, st.session_state.person, auswahl, wb)
        st.session_state.meldung = 'Dein Grundstock wurde gespeichert.'
        st.rerun()
if st.button('Standardliste wiederherstellen'):
    with ressourcen.datenbank() as conn:
        speichere_grundstock(conn, st.session_state.person, STANDARD_GRUNDSTOCK, wb)
    st.session_state.pop(f'grundstock_auswahl_{st.session_state.person}', None)
    st.session_state.meldung = 'Die Standardliste wurde wiederhergestellt.'
    st.rerun()
st.caption('Nur ausgewählte Zutaten zählen. Lebensmittel mit einer Restmenge erfasst du im Vorrat.')

with st.container(key='profilhinweis'):
    st.subheader('Dein Profil')
    st.write(f'Aktuelles Profil: **{st.session_state.person}**')
    st.info('Projektvorschau ohne Passwortschutz. Wer deinen Profilnamen kennt, kann die Daten öffnen. '
            'Verwende keine vertraulichen Daten.')
    if st.button('Profil wechseln', icon=':material/logout:'):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
with st.expander('Für das Projektteam', icon=':material/science:'):
    st.caption('Gespeicherte Testszenarien sind von persönlichen Vorräten und Bewertungen getrennt.')
    st.toggle('Testszenarien in der Navigation anzeigen', key='_testsicht',
              value=st.session_state.get('entwicklermodus', False), on_change=setze_entwicklermodus)
    if st.session_state.get('entwicklermodus'):
        st.page_link('app/szenarien_seite.py', label='Testszenarien öffnen', icon=':material/science:')
