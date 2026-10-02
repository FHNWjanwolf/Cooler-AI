"""Tests für den Datenbankzugriff, mit sqlite3 und mit dem Turso-Client (libsql) auf einer lokalen Datei."""
from datetime import date, timedelta

import pytest

from app.datenbank import fuege_hinzu, lade_bewertungen, lade_vorrat, speichere_bewertung, verbinde
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
    assert lade_vorrat(conn, wb).empty
    heute = date.today()
    fuege_hinzu(conn, "Spinat", 200.0, "g", heute + timedelta(days=2))
    fuege_hinzu(conn, "Ei", 6.0, "Stk", None)
    df = lade_vorrat(conn, wb)
    assert list(df["zutat"]) == ["Spinat", "Ei"]  # dringendste zuerst
    assert df["tage"].iloc[0] == 2


def test_bewertung_speichern_und_laden(conn):
    speichere_bewertung(conn, "spaghetti_carbonara", 5, [{"zutat": "Ei", "tage": 3}])
    assert lade_bewertungen(conn) == [
        {"rezept_id": "spaghetti_carbonara", "datum": date.today().isoformat(), "note": 5,
         "vorrat": [{"zutat": "Ei", "tage": 3}]}
    ]
