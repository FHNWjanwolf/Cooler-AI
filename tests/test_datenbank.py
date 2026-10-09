"""Tests für den Datenbankzugriff, mit sqlite3 und mit dem Turso-Client (libsql) auf einer lokalen Datei."""
import sqlite3
from datetime import date, timedelta

import pytest

from app.datenbank import (fuege_hinzu, lade_bewertungen, lade_vorrat, loesche, normalisiere_person,
                           speichere_bewertung, verbinde)
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
         "note": 5, "vorrat": [{"zutat": "Ei", "tage": 3}]}
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
