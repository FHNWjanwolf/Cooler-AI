"""Tests für den Datenbankzugriff, mit sqlite3 und mit dem Turso-Client (libsql) auf einer lokalen Datei."""
import sqlite3
from datetime import date, timedelta

import pytest

from app.datenbank import (aktualisiere, fuege_hinzu, koche, lade_bewertungen, lade_vorrat, loesche, normalisiere_person,
                           speichere_bewertung, verbinde, vorrat_als_liste)
from wissensbasis.wissen import Wissensbasis


@pytest.fixture(params=["sqlite3", "libsql"])
def conn(request, tmp_path, monkeypatch):
    if request.param == "libsql":
        # libsql kann auch eine lokale Datei öffnen; so wird der Turso-Weg ohne Netz getestet.
        monkeypatch.setenv("TURSO_DATABASE_URL", str(tmp_path / "turso.db"))
    else:
        monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    return verbinde(tmp_path / "test.db")


def test_vorrat_speichern_und_laden(conn):
    wb = Wissensbasis()
    assert lade_vorrat(conn, "anna", wb).empty
    heute = date.today()
    fuege_hinzu(conn, "anna", "Spinat", 200.0, "g", heute + timedelta(days=2))
    fuege_hinzu(conn, "anna", "Ei", 6.0, "Stk", None)
    df = lade_vorrat(conn, "anna", wb)
    assert list(df["zutat"]) == ["Spinat", "Ei"]  # dringendste zuerst
    assert df["tage"].iloc[0] == 2


def test_jede_person_sieht_nur_ihren_vorrat(conn):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Spinat", 200.0, "g", None)
    fuege_hinzu(conn, "ben", "Ei", 6.0, "Stk", None)
    assert list(lade_vorrat(conn, "anna", wb)["zutat"]) == ["Spinat"]
    assert list(lade_vorrat(conn, "ben", wb)["zutat"]) == ["Ei"]

    # Ben kann Annas Eintrag nicht löschen
    annas_id = int(lade_vorrat(conn, "anna", wb).index[0])
    loesche(conn, "ben", annas_id)
    assert len(lade_vorrat(conn, "anna", wb)) == 1


def test_bewertung_speichern_und_laden(conn):
    speichere_bewertung(conn, "anna", "spaghetti_carbonara", 5, [{"zutat": "Ei", "tage": 3}])
    assert lade_bewertungen(conn) == [
        {"person": "anna", "rezept_id": "spaghetti_carbonara", "datum": date.today().isoformat(),
         "note": 5, "vorrat": [{"zutat": "Ei", "tage": 3}], "gekocht": False}
    ]


def test_name_wird_vereinheitlicht():
    assert normalisiere_person("  Yann ") == "yann"


def test_alte_datenbank_bekommt_spalte_person(tmp_path, monkeypatch):
    """Datenbanken von vor der Einführung der Personen (z.B. auf Turso) werden ergänzt."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    pfad = tmp_path / "alt.db"
    alt = sqlite3.connect(pfad)
    alt.executescript("""
        CREATE TABLE vorratseintrag (id INTEGER PRIMARY KEY, zutat TEXT NOT NULL, menge REAL,
                                     einheit TEXT, ablaufdatum TEXT, geoeffnet_am TEXT);
        CREATE TABLE bewertung (id INTEGER PRIMARY KEY, rezept_id TEXT NOT NULL, datum TEXT NOT NULL,
                                note INTEGER NOT NULL, vorrat_snapshot TEXT NOT NULL);
        INSERT INTO vorratseintrag (zutat) VALUES ('Ei');
    """)
    alt.close()

    conn = verbinde(pfad)
    fuege_hinzu(conn, "anna", "Spinat", None, None, None)
    assert list(lade_vorrat(conn, "anna", Wissensbasis())["zutat"]) == ["Spinat"]  # alter Eintrag gehört niemandem


def test_kochen_baut_vorrat_ab(conn):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Spinat", 200.0, "g", date.today() + timedelta(days=1))
    fuege_hinzu(conn, "anna", "Ei", 6.0, "Stück", None)
    vorher = vorrat_als_liste(lade_vorrat(conn, "anna", wb))
    spinat_id = next(v["id"] for v in vorher if v["zutat"] == "Spinat")

    koche(conn, "anna", "omelette_spinat_feta", 5, vorher, {spinat_id: 200.0})  # Eier sind noch übrig

    assert list(lade_vorrat(conn, "anna", wb)["zutat"]) == ["Ei"]
    bewertung = lade_bewertungen(conn)[0]
    assert bewertung["gekocht"] is True
    assert len(bewertung["vorrat"]) == 2  # Snapshot zeigt den Vorrat VOR dem Kochen


def test_alte_datenbank_bekommt_spalte_gekocht(tmp_path, monkeypatch):
    """Test/Prod laufen auf bestehenden Turso-Datenbanken ohne die neue Spalte."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    pfad = tmp_path / "alt.db"
    alt = sqlite3.connect(pfad)
    alt.execute("CREATE TABLE bewertung (id INTEGER PRIMARY KEY, rezept_id TEXT NOT NULL, "
                "datum TEXT NOT NULL, note INTEGER NOT NULL, vorrat_snapshot TEXT NOT NULL)")
    alt.execute("INSERT INTO bewertung (rezept_id, datum, note, vorrat_snapshot) "
                "VALUES ('caprese', '2026-10-01', 4, '[]')")
    alt.commit()
    alt.close()

    conn = verbinde(pfad)
    assert lade_bewertungen(conn)[0]["gekocht"] is False


def test_kochen_behaelt_restmenge_und_snapshot(conn):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Kartoffel", 800.0, "g", date.today())
    vorher = vorrat_als_liste(lade_vorrat(conn, "anna", wb))
    koche(conn, "anna", "kartoffelgratin", 5, vorher, {vorher[0]["id"]: 600.0})
    nachher = lade_vorrat(conn, "anna", wb)
    assert nachher.iloc[0]["menge"] == 200.0
    assert nachher.iloc[0]["ablaufdatum"] == date.today()
    assert lade_bewertungen(conn)[0]["vorrat"] == vorher


@pytest.mark.parametrize("ungueltig", [-1.0, float("nan"), float("inf"), 900.0])
def test_ungueltiger_verbrauch_rollt_alles_zurueck(conn, ungueltig):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Kartoffel", 800.0, "g", None)
    fuege_hinzu(conn, "anna", "Rahm", 200.0, "ml", None)
    vorher = vorrat_als_liste(lade_vorrat(conn, "anna", wb))
    with pytest.raises(ValueError):
        koche(conn, "anna", "test", 4, vorher,
              {vorher[1]["id"]: 100.0, vorher[0]["id"]: ungueltig})
    assert vorrat_als_liste(lade_vorrat(conn, "anna", wb)) == vorher
    assert lade_bewertungen(conn) == []


def test_kochen_fremder_vorrat_ist_geschuetzt(conn):
    fuege_hinzu(conn, "ben", "Kartoffel", 800.0, "g", None)
    vorher = vorrat_als_liste(lade_vorrat(conn, "ben", Wissensbasis()))
    with pytest.raises(ValueError):
        koche(conn, "anna", "test", 4, [], {vorher[0]["id"]: 600.0})
    assert lade_vorrat(conn, "ben", Wissensbasis()).iloc[0]["menge"] == 800.0


def test_kochen_null_und_unbekannte_mengen(conn):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Kartoffel", 800.0, "g", None)
    fuege_hinzu(conn, "anna", "Rahm", None, "ml", None)
    vorher = vorrat_als_liste(lade_vorrat(conn, "anna", wb))
    koche(conn, "anna", "test", 4, vorher,
          {vorher[0]["id"]: 0.0, vorher[1]["id"]: None})
    assert list(lade_vorrat(conn, "anna", wb)["menge"]) == [800.0]


def test_einheit_aendern_und_personenschutz(conn):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Brokkoli", 800, "g", None)
    eintrag_id = int(lade_vorrat(conn, "anna", wb).index[0])
    aktualisiere(conn, "ben", eintrag_id, 2, None, None, einheit="Stück")
    assert lade_vorrat(conn, "anna", wb).loc[eintrag_id, "einheit"] == "g"
    aktualisiere(conn, "anna", eintrag_id, 0.8, None, None, einheit="kg")
    aktualisiere(conn, "anna", eintrag_id, 0.5, None, None)  # Ohne Einheit bleibt sie bestehen.
    zeile = lade_vorrat(conn, "anna", wb).loc[eintrag_id]
    assert zeile["menge"] == 0.5 and zeile["einheit"] == "kg"


def test_geaenderte_einheit_waehrend_gekocht_dialog_wird_abgelehnt(conn):
    wb = Wissensbasis()
    fuege_hinzu(conn, "anna", "Brokkoli", 800, "g", None)
    vorher = vorrat_als_liste(lade_vorrat(conn, "anna", wb))
    eintrag_id = vorher[0]["id"]
    aktualisiere(conn, "anna", eintrag_id, 800, None, None, einheit="Stück")
    with pytest.raises(ValueError, match="geändert"):
        koche(conn, "anna", "test", 5, vorher, {eintrag_id: 300})
    assert lade_bewertungen(conn) == []
    assert lade_vorrat(conn, "anna", wb).loc[eintrag_id, "menge"] == 800
