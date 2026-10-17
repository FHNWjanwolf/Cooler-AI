"""Einkaufsplanung darf keinen Vorrat erfinden oder doppelte Käufe speichern."""
import sqlite3
from datetime import date

import pytest

from app.datenbank import (kaufe_ein, lade_einkaufsliste, lade_vorrat, merke_einkauf,
                           entferne_einkauf, verbinde)
from wissensbasis.wissen import Wissensbasis


@pytest.fixture(params=['sqlite3', 'libsql'])
def conn(request, tmp_path, monkeypatch):
    pfad = tmp_path / 'einkauf.db'
    if request.param == 'libsql':
        monkeypatch.setenv('TURSO_DATABASE_URL', str(pfad))
    else:
        monkeypatch.delenv('TURSO_DATABASE_URL', raising=False)
    verbindung = verbinde(pfad)
    yield verbindung
    verbindung.close()


def test_planen_ist_kein_kauf_und_doppelklick_addiert_nichts(conn):
    assert merke_einkauf(conn, 'anna', 'Ei', 6, 'Stück')
    assert not merke_einkauf(conn, 'anna', 'Ei', 6, 'Stück')
    assert len(lade_einkaufsliste(conn, 'anna')) == 1
    assert lade_vorrat(conn, 'anna', Wissensbasis()).empty
    assert lade_einkaufsliste(conn, 'ben') == []


def test_kaufen_uebernimmt_bearbeitete_menge_genau_einmal(conn):
    merke_einkauf(conn, 'anna', 'Kartoffel', 600, 'g')
    eintrag = lade_einkaufsliste(conn, 'anna')[0]
    kaufe_ein(conn, 'anna', eintrag['id'], 0.8, 'kg', date(2026, 11, 1))
    assert lade_einkaufsliste(conn, 'anna') == []
    vorrat = lade_vorrat(conn, 'anna', Wissensbasis())
    assert len(vorrat) == 1
    assert vorrat.iloc[0].menge == 0.8 and vorrat.iloc[0].einheit == 'kg'
    with pytest.raises(ValueError):
        kaufe_ein(conn, 'anna', eintrag['id'], 0.8, 'kg', date(2026, 11, 1))
    assert len(lade_vorrat(conn, 'anna', Wissensbasis())) == 1


def test_fremde_einkaeufe_sind_weder_kaufbar_noch_loeschbar(conn):
    merke_einkauf(conn, 'anna', 'Ei', None, 'Stück')
    eintrag = lade_einkaufsliste(conn, 'anna')[0]
    entferne_einkauf(conn, 'ben', eintrag['id'])
    with pytest.raises(ValueError):
        kaufe_ein(conn, 'ben', eintrag['id'], 6, 'Stück', None)
    assert len(lade_einkaufsliste(conn, 'anna')) == 1
    assert lade_vorrat(conn, 'ben', Wissensbasis()).empty


def test_alter_kaufdialog_kann_keinen_neuen_listeneintrag_kaufen(conn):
    merke_einkauf(conn, 'anna', 'Ei', 6, 'Stück')
    alter_einkauf = lade_einkaufsliste(conn, 'anna')[0]
    entferne_einkauf(conn, 'anna', alter_einkauf['id'])
    merke_einkauf(conn, 'anna', 'Milch', 1000, 'ml')
    assert lade_einkaufsliste(conn, 'anna')[0]['id'] != alter_einkauf['id']
    with pytest.raises(ValueError):
        kaufe_ein(conn, 'anna', alter_einkauf['id'], 6, 'Stück', None)
    assert lade_einkaufsliste(conn, 'anna')[0]['zutat'] == 'Milch'
    assert lade_vorrat(conn, 'anna', Wissensbasis()).empty


@pytest.mark.parametrize('menge', [0, -1, float('inf'), float('nan')])
def test_ungueltiger_kauf_bewahrt_liste(conn, menge):
    merke_einkauf(conn, 'anna', 'Ei', 6, 'Stück')
    eintrag = lade_einkaufsliste(conn, 'anna')[0]
    with pytest.raises(ValueError):
        kaufe_ein(conn, 'anna', eintrag['id'], menge, 'Stück', None)
    assert len(lade_einkaufsliste(conn, 'anna')) == 1
    assert lade_vorrat(conn, 'anna', Wissensbasis()).empty


def test_fehler_beim_speichern_stellt_einkauf_wieder_her(conn):
    merke_einkauf(conn, 'anna', 'Ei', 6, 'Stück')
    eintrag = lade_einkaufsliste(conn, 'anna')[0]
    conn.executescript("""
        CREATE TRIGGER kauf_fehler BEFORE INSERT ON vorratseintrag
        BEGIN SELECT RAISE(ABORT, 'Testfehler'); END;
    """)
    with pytest.raises(Exception, match='Testfehler'):
        kaufe_ein(conn, 'anna', eintrag['id'], 6, 'Stück', None)
    assert len(lade_einkaufsliste(conn, 'anna')) == 1
    assert lade_vorrat(conn, 'anna', Wissensbasis()).empty


def test_neue_tabelle_bewahrt_bestehende_daten(tmp_path, monkeypatch):
    monkeypatch.delenv('TURSO_DATABASE_URL', raising=False)
    pfad = tmp_path / 'bestehend.db'
    alt = sqlite3.connect(pfad)
    alt.executescript("""
        CREATE TABLE haushalt (person TEXT PRIMARY KEY, grundstock TEXT NOT NULL);
        INSERT INTO haushalt VALUES ('anna', '["Pfeffer"]');
    """)
    alt.close()
    neu = verbinde(pfad)
    assert neu.execute('SELECT grundstock FROM haushalt WHERE person = ?', ('anna',)).fetchone()[0] == '["Pfeffer"]'
    assert lade_einkaufsliste(neu, 'anna') == []
    neu.close()
