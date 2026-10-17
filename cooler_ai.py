"""Cooler AI – Streamlit-App mit gemeinsamer Gestaltung und klarer Navigation."""
import streamlit as st

from app.datenbank import normalisiere_person
from app.gestaltung import illustration, kopf, lade_design, markenleiste
from app.ressourcen import beginne_seitenaufruf

st.set_page_config(page_title='Cooler · Deine Küche im Blick', page_icon='🥕', layout='wide')
lade_design()
markenleiste()


def anmelden():
    # Profile sind keine Authentifizierung. Keine Profilnamen mehr in der URL.
    st.query_params.clear()
    if not st.session_state.get('person'):
        with st.container(key='hero'):
            links, rechts = st.columns([1.5, 1])
            with links:
                kopf('Deine Küche, gut genutzt', 'Gutes Essen beginnt mit dem, was da ist.',
                     'Behalte deinen Vorrat im Blick und finde Gerichte, die dazu passen. '
                     'Damit aus den Resten von heute dein Lieblingsessen wird.')
            with rechts:
                illustration()
        st.subheader('Willkommen in deiner Küche')
        st.caption('Projektvorschau · Profile ohne Passwort. Verwende hier keine vertraulichen Daten.')
        with st.form('anmelden'):
            name = st.text_input('Dein Profilname', placeholder='Wie sollen wir dich nennen?', max_chars=60)
            if st.form_submit_button('Küche öffnen', type='primary'):
                if normalisiere_person(name):
                    st.session_state.person = normalisiere_person(name)
                    st.rerun()
                else:
                    st.warning('Gib einen Profilnamen ein, um deinen Vorrat wiederzufinden.')
        st.caption('Immer denselben Namen verwenden. Wer den Namen kennt, kann das Profil öffnen.')
        st.stop()


anmelden()
beginne_seitenaufruf()
seiten = [
    st.Page('app/startseite.py', title='Heute', icon=':material/wb_sunny:', default=True),
    st.Page('app/vorrat.py', title='Vorrat', icon=':material/kitchen:'),
    st.Page('app/vorschlaege.py', title='Rezepte', icon=':material/restaurant:'),
    st.Page('app/einkaufsliste.py', title='Einkauf', icon=':material/shopping_basket:'),
    st.Page('app/haushalt.py', title='Einstellungen', icon=':material/tune:'),
]
if st.session_state.get('entwicklermodus'):
    seiten.append(st.Page('app/szenarien_seite.py', title='Testszenarien', icon=':material/science:'))
ausgewaehlt = st.navigation(seiten, position='hidden')
with st.container(key='navigation', horizontal=True, gap='small'):
    for seite in seiten:
        st.page_link(seite, label=seite.title, icon=seite.icon, width='content')
ausgewaehlt.run()
