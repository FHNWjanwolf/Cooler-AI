"""Heute: die nächsten Lebensmittel und drei passende Gerichte."""
import streamlit as st

from app import ressourcen
from app.datenbank import lade_vorrat, vorrat_als_liste
from app.einkauf import zeige_einkaufsideen
from app.gestaltung import illustration, kopf, leer, vorrat_zeile
from app.rezeptansicht import zeige_meldung, zeige_vorschlaege

zeige_meldung()
wb = ressourcen.wissensbasis()
with ressourcen.datenbank() as conn:
    vorrat = lade_vorrat(conn, st.session_state.person, wb)
bald = vorrat[vorrat.tage.notna() & (vorrat.tage >= 0) & (vorrat.tage <= 3)]
abgelaufen = vorrat[vorrat.tage.notna() & (vorrat.tage < 0)]

with st.container(key='hero'):
    links, rechts = st.columns([1.7, 1])
    with links:
        kopf('Weniger verschwenden. Besser essen.', 'Was kochen wir heute?',
             'Dein Vorrat steckt voller Möglichkeiten. Finde etwas Gutes daraus.')
        if st.button('Vorrat ergänzen', type='primary', icon=':material/add:'):
            st.switch_page('app/vorrat.py')
    with rechts:
        illustration()

with st.container(key='kennzahlen'):
    a, b = st.columns(2)
    a.metric('Zutaten im Vorrat', len(vorrat))
    b.metric('Bald fällig', len(bald), help='Heute oder in den nächsten drei Tagen fällig; abgelaufene Einträge zählen separat.')

st.subheader('Als Nächstes verbrauchen')
if vorrat.empty:
    leer('Deine Küche wartet auf die erste Zutat.',
         'Füge ein paar Lebensmittel hinzu. Danach findest du hier passende Gerichte.')
elif bald.empty:
    st.caption('In den nächsten drei Tagen ist nichts fällig. Ein guter Moment, entspannt zu planen.')
else:
    spalten = st.columns(3)
    for spalte, eintrag in zip(spalten, bald.head(3).itertuples()):
        with spalte:
            vorrat_zeile(eintrag.name, eintrag.menge, eintrag.einheit, eintrag.tage)
    if len(bald) > 3:
        st.caption(f'{len(bald) - 3} weitere bald fällige Einträge findest du im Vorrat.')
if not abgelaufen.empty:
    st.warning(f'{len(abgelaufen)} Vorratseinträge haben ihr eingetragenes Ablaufdatum überschritten. '
               'Prüfe sie vor dem Verwenden. Ein Rezeptvorschlag bestätigt keine Geniessbarkeit.')
st.page_link('app/vorrat.py', label='Gesamten Vorrat ansehen', icon=':material/arrow_forward:')

st.subheader('Das passt zu deinem Vorrat')
zeige_vorschlaege(vorrat, kompakt=True)
with st.expander('Mit einem kleinen Einkauf mehr Möglichkeiten', icon=':material/shopping_basket:'):
    zeige_einkaufsideen(vorrat_als_liste(vorrat))
