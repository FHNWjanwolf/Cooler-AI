"""Vorrat als mobile Liste mit Suche, Ablauf-Filtern und einzelnen Bearbeitungsformularen."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app import ressourcen
from app.datenbank import aktualisiere, fuege_hinzu, lade_vorrat, loesche
from app.gestaltung import EINHEITEN, ablauf_status, kopf, leer, menge_text
from app.rezeptansicht import zeige_meldung

kopf('Alles im Blick', 'Dein Vorrat', 'Was da ist, was bald fällig ist und was du daraus machen kannst.')
zeige_meldung()
wb = ressourcen.wissensbasis()
person = st.session_state.person

with ressourcen.datenbank() as conn:
    vorrat = lade_vorrat(conn, person, wb)

with st.expander('Zutat hinzufügen', icon=':material/add:', expanded=vorrat.empty):
    zutat = st.selectbox('Zutat', wb.zutaten_zur_auswahl(), format_func=wb.namen.get,
                         index=None, placeholder='Tippen zum Suchen', key='erfassen_zutat')
    standard = wb.eigenschaft(zutat, 'einheit') if zutat else 'g'
    with st.form('erfassen', clear_on_submit=True):
        c1, c2 = st.columns(2)
        menge = c1.number_input('Menge', min_value=0.0, value=None, step=1.0,
                                help='Offen lassen, wenn du die Menge nicht kennst.')
        einheit = c2.selectbox('Einheit', EINHEITEN, index=EINHEITEN.index(standard),
                               key=f'erfassen_einheit_{zutat}')
        ablauf = st.date_input('Ablaufdatum', value=None, format='DD.MM.YYYY',
                               help='Ohne Datum verwenden wir die übliche Haltbarkeit als Schätzung.')
        if st.form_submit_button('Hinzufügen', type='primary', use_container_width=True):
            if zutat is None:
                st.warning('Wähle zuerst eine Zutat aus.')
            elif menge is not None and menge <= 0:
                st.warning('Gib eine Menge grösser als 0 ein oder lasse sie offen.')
            else:
                haltbar = wb.eigenschaft(zutat, 'haltbarTage')
                if ablauf is None and haltbar is not None:
                    ablauf = date.today() + timedelta(days=haltbar)
                with ressourcen.datenbank() as conn:
                    fuege_hinzu(conn, person, zutat, menge, einheit, ablauf)
                st.session_state.meldung = f'{menge_text(menge, einheit)} {wb.namen[zutat]} hinzugefügt.'
                st.rerun()

st.subheader('Was du zu Hause hast')
st.caption('Mehrere Packungen bleiben getrennt, damit ihre Ablaufdaten und Restmengen stimmen.')
if vorrat.empty:
    leer('Noch Platz im Kühlschrank.', 'Erfasse oben deine erste Zutat. Menge und Ablaufdatum können offen bleiben.')
else:
    suche = st.text_input('Im Vorrat suchen', placeholder='Zutat suchen …', key='vorrat_suche')
    filter_ = st.pills('Anzeigen', ['Alles', 'Bald fällig', 'Abgelaufen', 'Ohne Datum'],
                       default='Alles', key='vorrat_filter')
    auswahl = vorrat[vorrat['name'].str.contains(suche, case=False, regex=False)]
    if filter_ == 'Bald fällig':
        auswahl = auswahl[auswahl.tage.notna() & (auswahl.tage >= 0) & (auswahl.tage <= 3)]
    elif filter_ == 'Abgelaufen':
        auswahl = auswahl[auswahl.tage.notna() & (auswahl.tage < 0)]
    elif filter_ == 'Ohne Datum':
        auswahl = auswahl[auswahl.tage.isna()]
    st.caption(f'{len(auswahl)} von {len(vorrat)} Einträgen · nach Ablaufdatum sortiert')
    if auswahl.empty:
        leer('Hier ist alles erledigt.', 'Keine Einträge für diese Suche oder diesen Filter.')
    for artikel in auswahl.itertuples():
        eintrag_id = int(artikel.Index)
        _, status = ablauf_status(artikel.tage)
        with st.expander(f'{artikel.name} · {menge_text(artikel.menge, artikel.einheit)} · {status}'):
            if pd.notna(artikel.tage) and artikel.tage < 0:
                st.warning('Das eingetragene Ablaufdatum ist überschritten. Prüfe die Zutat vor dem Verwenden.')
            with st.form(f'vorrat_bearbeiten_{eintrag_id}'):
                c1, c2 = st.columns(2)
                menge = c1.number_input('Menge', min_value=0.0,
                                        value=None if pd.isna(artikel.menge) else float(artikel.menge),
                                        key=f'menge_{eintrag_id}')
                standard = artikel.einheit if artikel.einheit in EINHEITEN else 'g'
                einheit = c2.selectbox('Einheit', EINHEITEN, index=EINHEITEN.index(standard),
                                       key=f'einheit_{eintrag_id}')
                st.caption('Bei anderer Einheit auch die Menge anpassen: 800 g entsprechen 0.8 kg.')
                ablauf = st.date_input('Ablaufdatum', value=artikel.ablaufdatum, format='DD.MM.YYYY',
                                       key=f'ablauf_{eintrag_id}')
                geoeffnet = st.date_input('Geöffnet am', value=artikel.geoeffnet_am, format='DD.MM.YYYY',
                                          key=f'geoeffnet_{eintrag_id}')
                st.caption('Nach dem Öffnen kann die übliche Haltbarkeit das angezeigte Ablaufdatum verkürzen.')
                if st.form_submit_button('Änderungen speichern', type='primary'):
                    with ressourcen.datenbank() as conn:
                        if menge is not None and menge == 0:
                            loesche(conn, person, eintrag_id)
                        else:
                            aktualisiere(conn, person, eintrag_id, menge, ablauf, geoeffnet, einheit=einheit)
                    st.session_state.meldung = f'{artikel.name} aktualisiert.'
                    st.rerun()
            if st.button('Aufgebraucht · entfernen', key=f'entfernen_{eintrag_id}', icon=':material/delete:'):
                with ressourcen.datenbank() as conn:
                    loesche(conn, person, eintrag_id)
                st.session_state.meldung = f'{artikel.name} aus dem Vorrat entfernt.'
                st.rerun()

st.page_link('app/haushalt.py', label='Dauerhaft vorhandenen Grundstock anpassen', icon=':material/tune:')
