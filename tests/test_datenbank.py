"""Tests für den Datenbankzugriff, mit sqlite3 und mit dem Turso-Client (libsql) auf einer lokalen Datei."""
import sqlite3
from datetime import date, timedelta

import pytest

from app.datenbank import (fuege_hinzu, koche, lade_bewertungen, lade_vorrat, loesche, normalisiere_person,
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

    koche(conn, "anna", "omelette_spinat_feta", 5, vorher, [spinat_id])  # Eier sind noch übrig

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
