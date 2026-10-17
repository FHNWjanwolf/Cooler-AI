"""Persönliche Kontexte bleiben frisch; keine offenen oder global geteilten Nutzerverbindungen."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app import ressourcen
from app.datenbank import verbinde, speichere_grundstock
from wissensbasis.wissen import Wissensbasis

ROOT = Path(__file__).parents[1]


def test_wiederholte_lesezugriffe_nutzen_einen_kontext_und_schliessen_verbindungen(tmp_path, monkeypatch):
    monkeypatch.delenv('TURSO_DATABASE_URL', raising=False)
    pfad = tmp_path / 'kontext.db'
    conn = verbinde(pfad)
    speichere_grundstock(conn, 'anna', [], Wissensbasis())
    conn.close()
    geoeffnet, geschlossen = [], []

    class Verbindung:
        def __init__(self):
            self.conn = verbinde(pfad)
            geoeffnet.append(self)

        def __getattr__(self, name):
            return getattr(self.conn, name)

        def close(self):
            self.conn.close()
            geschlossen.append(self)

    monkeypatch.setattr(ressourcen, 'verbindung', Verbindung)
    at = AppTest.from_string('''
import streamlit as st
from app.ressourcen import beginne_seitenaufruf, wissensbasis
beginne_seitenaufruf()
eins = wissensbasis()
zwei = wissensbasis()
st.write(sorted(eins.grundstock_ids))
st.write(eins is zwei)
''')
    at.session_state.person = 'anna'
    at.run()
    assert not at.exception
    assert len(geoeffnet) == len(geschlossen) == 1
    assert at.json[0].value == '[]'
    # Änderungen ausserhalb dieses Aufrufs müssen beim nächsten Aufruf sichtbar sein.
    conn = verbinde(pfad)
    speichere_grundstock(conn, 'anna', ['Pfeffer'], Wissensbasis())
    conn.close()
    at.run()
    assert not at.exception
    assert 'Pfeffer' in at.json[0].value
    at.session_state.person = 'ben'
    at.run()
    assert not at.exception
    assert 'Olivenoel' in at.json[0].value
    assert len(geoeffnet) == len(geschlossen) == 3


def test_datenbank_wird_auch_bei_fehler_geschlossen(monkeypatch):
    class Verbindung:
        geschlossen = False

        def close(self):
            self.geschlossen = True

    conn = Verbindung()
    monkeypatch.setattr(ressourcen, 'verbindung', lambda: conn)
    try:
        with ressourcen.datenbank():
            raise ValueError('Testfehler')
    except ValueError:
        pass
    assert conn.geschlossen


def test_profilname_aus_url_oeffnet_keinen_fremden_vorrat():
    at = AppTest.from_file(ROOT / 'cooler_ai.py')
    at.query_params['person'] = 'anna'
    at.run()
    assert not at.exception
    assert 'person' not in at.session_state
    assert at.text_input[0].label == 'Dein Profilname'
    assert not at.query_params
