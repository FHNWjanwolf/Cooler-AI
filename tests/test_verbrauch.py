"""Mengenplanung und Gekocht-Dialog für Teilverbrauch."""
from pathlib import Path
from app.verbrauch import verbrauchsplan
from wissensbasis.wissen import Wissensbasis


def artikel(eintrag_id, zutat, menge, einheit="g", tage=2):
    return {"id": eintrag_id, "zutat": zutat, "menge": menge, "einheit": einheit, "tage": tage}


def rezept(zutat="Kartoffel", menge=600, einheit="g"):
    return {"zutaten": [{"zutat": zutat, "menge": menge, "einheit": einheit, "pflicht": True}]}


def test_rezeptmenge_auf_mehrere_packungen_verteilen():
    vorrat = [artikel(1, "Kartoffel", 500, tage=5), artikel(2, "Kartoffel", 300, tage=1)]
    assert verbrauchsplan(rezept(), vorrat, Wissensbasis()) == {2: 300, 1: 300}


def test_einheiten_und_hierarchie():
    wb = Wissensbasis()
    assert verbrauchsplan(rezept(), [artikel(1, "Kartoffel", 0.8, "kg")], wb) == {1: 0.6}
    assert verbrauchsplan(rezept("Tomate", 100), [artikel(1, "Cherrytomate", 200)], wb) == {1: 100}
    assert verbrauchsplan(rezept("Ei", 2, "Stück"), [artikel(1, "Ei", 6, "Stk")], wb) == {1: 2}


def test_unbekannte_mengen_und_ersatz_nicht_schaetzen():
    wb = Wissensbasis()
    assert verbrauchsplan(rezept(), [artikel(1, "Kartoffel", None)], wb) == {1: None}
    assert verbrauchsplan(rezept(), [artikel(1, "Kartoffel", 2, "Stück")], wb) == {1: None}
    assert verbrauchsplan(rezept("Rahm", 150, "ml"),
                         [artikel(1, "CremeFraiche", 200)], wb) == {1: None}


def test_gleicher_artikel_fuer_mehrere_rezeptzutaten():
    r = rezept("Tomate", 100)
    r["zutaten"] += rezept("Cherrytomate", 50)["zutaten"]
    assert verbrauchsplan(r, [artikel(1, "Cherrytomate", 200)], Wissensbasis()) == {1: 150}


def test_gekocht_dialog_speichert_teilverbrauch(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from app import ressourcen
    from app.datenbank import fuege_hinzu, lade_bewertungen, lade_vorrat, verbinde

    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    pfad = tmp_path / "ui.db"
    conn = verbinde(pfad)
    for zutat, menge, einheit in [("Kartoffel", 800, "g"), ("Rahm", 200, "ml"), ("Milch", 200, "ml")]:
        fuege_hinzu(conn, "anna", zutat, menge, einheit, None)
    monkeypatch.setattr(ressourcen, "verbindung", lambda: verbinde(pfad))
    monkeypatch.setattr(ressourcen, "ml_modell", lambda: None)
    at = AppTest.from_file(Path(__file__).parents[1] / "app/vorschlaege.py")
    at.session_state.person = "anna"
    at.run()
    assert not at.exception
    at.button(key="gekocht_kartoffelgratin").click().run()
    assert not at.exception
    # AppTest führt bei Änderungen einen ganzen Seitenlauf aus und unterstützt
    # Dialog-Fragmente noch nicht vollständig. Im Test den Dialog pro Lauf öffnen.
    at = AppTest.from_string("""
from app.rezeptansicht import gekocht_dialog
from app.datenbank import lade_vorrat, vorrat_als_liste
from app.ressourcen import verbindung, wissensbasis
from wissensbasis.eignung import finde_kandidaten, lade_rezepte
vorrat = vorrat_als_liste(lade_vorrat(verbindung(), 'anna', wissensbasis()))
kandidat = next(k for k in finde_kandidaten(lade_rezepte(), vorrat, wissensbasis())
                if k['rezept']['id'] == 'kartoffelgratin')
gekocht_dialog(kandidat, vorrat)
""")
    at.session_state.person = "anna"
    at.run()
    kartoffel_id = int(lade_vorrat(conn, "anna", Wissensbasis()).index[0])
    feld = at.number_input(key=f"verbrauch_kartoffelgratin_{kartoffel_id}")
    assert feld.value == 600
    feld.set_value(550).run()
    next(b for b in at.button if b.label == "Speichern").click().run()
    assert not at.exception
    assert lade_vorrat(conn, "anna", Wissensbasis()).loc[kartoffel_id, "menge"] == 250
    assert lade_bewertungen(conn)[0]["gekocht"] is True
