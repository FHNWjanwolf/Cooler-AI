"""Zubereiten ist eine Vorschau; Verbrauch und Bewertung erst am bestätigten Ende."""
import pytest
from streamlit.testing.v1 import AppTest

from app import ressourcen
from app.datenbank import fuege_hinzu, lade_bewertungen, lade_vorrat, verbinde
from app.rezeptansicht import zubereitungsschritte
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis


@pytest.fixture
def app_db(tmp_path, monkeypatch):
    monkeypatch.delenv('TURSO_DATABASE_URL', raising=False)
    pfad = tmp_path / 'kochen.db'
    conn = verbinde(pfad)
    monkeypatch.setattr(ressourcen, 'verbindung', lambda: verbinde(pfad))
    for z, m, e in [('Kartoffel', 800, 'g'), ('Rahm', 150, 'ml'), ('Milch', 150, 'ml')]:
        fuege_hinzu(conn, 'anna', z, m, e, None)
    yield conn
    conn.close()


def dialog(schritte=True):
    at = AppTest.from_string('''
import streamlit as st
from app.rezeptansicht import kochen_dialog
from app.datenbank import lade_vorrat, vorrat_als_liste
from app.ressourcen import verbindung, wissensbasis
from wissensbasis.eignung import finde_kandidaten, lade_rezepte
if st.session_state.get('meldung'):
    st.success(st.session_state.meldung)
    st.stop()
wb = wissensbasis()
vorrat = vorrat_als_liste(lade_vorrat(verbindung(), 'anna', wb))
kandidat = next(k for k in finde_kandidaten(lade_rezepte(), vorrat, wb)
                if k['rezept']['id'] == 'kartoffelgratin')
kandidat['rezept']['zubereitung'] = ['Kartoffeln vorbereiten.', 'Gratin backen.'] if st.session_state.anleitung else None
kochen_dialog(kandidat, vorrat)
''')
    at.session_state.person = 'anna'
    at.session_state.anleitung = schritte
    return at.run()


def klick(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception


def bis_abschluss(at):
    klick(at, 'Mit dem Kochen beginnen')
    while any(b.label == 'Nächster Schritt' for b in at.button):
        klick(at, 'Nächster Schritt')
    klick(at, 'Fertig gekocht')


def test_vorschau_schreibt_nichts_erst_abschluss_speichert(app_db):
    at = dialog()
    assert not at.exception
    assert not at.feedback and not at.number_input
    klick(at, 'Mit dem Kochen beginnen')
    assert not at.feedback
    assert any('Kartoffeln vorbereiten.' in h.value for h in at.get('html'))
    klick(at, 'Nächster Schritt')
    assert any('Gratin backen.' in h.value for h in at.get('html'))
    assert lade_bewertungen(app_db) == []
    assert lade_vorrat(app_db, 'anna', Wissensbasis()).iloc[0].menge == 800
    klick(at, 'Fertig gekocht')
    speichern = next(b for b in at.button if b.label == 'Bewertung & Verbrauch speichern')
    assert speichern.disabled
    at.feedback[0].set_value(3).run()
    klick(at, 'Bewertung & Verbrauch speichern')
    bewertung = lade_bewertungen(app_db)[0]
    assert bewertung['note'] == 4 and bewertung['gekocht']
    assert bewertung['vorrat'][0]['menge'] == 800
    rest = lade_vorrat(app_db, 'anna', Wissensbasis())
    assert len(rest) == 1 and rest.iloc[0].menge == 200


def test_zurueckgehen_behaelt_entwurf_ohne_zu_speichern(app_db):
    at = dialog()
    bis_abschluss(at)
    at.number_input[0].set_value(550).run()
    at.feedback[0].set_value(2).run()
    klick(at, 'Zur Zubereitung')
    klick(at, 'Zurück')
    klick(at, 'Zur Zutatenliste')
    bis_abschluss(at)
    assert at.number_input[0].value == 550
    assert at.feedback[0].value == 2
    assert lade_bewertungen(app_db) == []
    assert lade_vorrat(app_db, 'anna', Wissensbasis()).iloc[0].menge == 800


def test_fehlende_anleitung_wird_nicht_erfunden(app_db):
    at = dialog(schritte=False)
    klick(at, 'Mit dem Kochen beginnen')
    assert any('noch keine Zubereitungsanleitung' in i.value for i in at.info)
    assert not any(b.label == 'Nächster Schritt' for b in at.button)
    klick(at, 'Fertig gekocht')
    assert at.feedback
    assert lade_bewertungen(app_db) == []


def test_anleitungsformate_und_bestehende_rezepte():
    assert zubereitungsschritte({'zubereitung': 'Vorbereiten.\n\nKochen.'}) == ['Vorbereiten.', 'Kochen.']
    assert zubereitungsschritte({'zubereitung': [' ', None, ' Garen. ']}) == ['Garen.']
    assert zubereitungsschritte({}) == []
    rezepte = lade_rezepte()
    assert all(len(zubereitungsschritte(r)) >= 3 for r in rezepte)
