"""Startseite, Kochbewertungen und Einkauf durch die Oberfläche prüfen."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import ressourcen
from app.datenbank import fuege_hinzu, lade_bewertungen, lade_vorrat, verbinde
from app.einkauf import kaufmenge
from wissensbasis.wissen import Wissensbasis

ROOT = Path(__file__).parents[1]


@pytest.fixture
def app_db(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    pfad = tmp_path / "app.db"
    conn = verbinde(pfad)
    monkeypatch.setattr(ressourcen, "verbindung", lambda: verbinde(pfad))
    monkeypatch.setattr(ressourcen, "ml_modell", lambda: None)
    return conn


def startseite():
    at = AppTest.from_file(ROOT / "cooler_ai.py")
    at.session_state.person = "anna"
    return at.run()


def test_anmeldung_startet_auf_startseite_und_vorrat_ist_erreichbar(app_db):
    at = AppTest.from_file(ROOT / "cooler_ai.py").run()
    at.text_input[0].set_value(" Anna ")
    next(b for b in at.button if b.label == "Weiter").click().run()
    assert not at.exception
    assert at.session_state.person == "anna"
    assert {s.value for s in at.subheader} >= {"Dein Vorrat", "Deine Menüvorschläge", "Einkaufsideen"}
    assert at.columns[0].subheader[0].value == "Dein Vorrat"
    assert at.columns[1].subheader[0].value == "Deine Menüvorschläge"
    next(b for b in at.button if b.label == "Vorrat anpassen").click().run()
    assert not at.exception
    assert at.title[0].value == "Vorrat"
    assert at.selectbox[0].label == "Zutat"


def test_startseite_zeigt_nur_eigenen_vorrat_ohne_vorab_bewertung(app_db):
    fuege_hinzu(app_db, "anna", "Kartoffel", 800, "g", date.today())
    fuege_hinzu(app_db, "anna", "Rahm", 200, "ml", None)
    fuege_hinzu(app_db, "anna", "Milch", 200, "ml", None)
    fuege_hinzu(app_db, "ben", "Banane", 3, "Stück", None)
    at = startseite()
    assert not at.exception
    assert any("800 g" in m.value for m in at.markdown)
    assert not any("Banane" in m.value for m in at.markdown)
    assert not at.select_slider  # Die 1–5-Skala ist nur im Gekocht-Dialog.
    assert not any("Würdest du das gerne kochen?" in m.value for m in at.markdown)
    assert not any(b.label in ("👍 Ja", "👎 Nein") for b in at.button)
    assert at.button(key="gekocht_kartoffelgratin")
    assert lade_bewertungen(app_db) == []


def test_einkauf_uebernehmen_aktualisiert_vorrat_und_menues(app_db):
    wb = Wissensbasis()
    for z, m, e in [("Spaghetti", 200, "g"), ("Ei", 2, "Stück"), ("Parmesan", 40, "g")]:
        fuege_hinzu(app_db, "anna", z, m, e, None)
    at = startseite()
    assert not at.exception
    assert not any(s.value == "Spaghetti Carbonara" for s in at.subheader)
    at.button(key="einkauf_Speck").click().run()
    assert not at.exception
    gekauft = lade_vorrat(app_db, "anna", wb)
    speck = gekauft[gekauft["zutat"] == "Speck"].iloc[0]
    assert speck["menge"] == 100 and speck["einheit"] == "g"
    assert speck["ablaufdatum"] == date.today() + timedelta(days=wb.eigenschaft("Speck", "haltbarTage"))
    assert lade_vorrat(app_db, "ben", wb).empty
    assert any(s.value == "Spaghetti Carbonara" for s in at.subheader)
    assert not any(b.key == "einkauf_Speck" for b in at.button)
    assert lade_bewertungen(app_db) == []  # Ein Einkauf ist keine Bewertung.


def test_kaufmenge_unbekannt_und_hierarchie():
    wb = Wissensbasis()
    idee = {"zutat": "Vollrahm", "rezepte": [{"rezept": {"zutaten": [
        {"zutat": "Rahm", "menge": 0.15, "einheit": "l", "pflicht": True}]}}]}
    assert kaufmenge(idee, wb) == (150, "ml")
    idee["rezepte"][0]["rezept"]["zutaten"][0]["menge"] = None
    assert kaufmenge(idee, wb) == (None, "ml")


def test_zutat_zeigt_passende_einheit_und_abweichende_einheit_wird_gespeichert(app_db):
    at = startseite()
    at.switch_page("app/vorrat.py").run()
    for zutat, einheit in [("Ei", "Stück"), ("Vollrahm", "ml"), ("Brokkoli", "g")]:
        at.selectbox(key="erfassen_zutat").select(zutat).run()
        assert not at.exception
        assert at.selectbox(key=f"erfassen_einheit_{zutat}").value == einheit
    at.selectbox(key="erfassen_einheit_Brokkoli").select("kg")
    at.number_input[0].set_value(0.8)
    next(b for b in at.button if b.label == "Hinzufügen").click().run()
    assert not at.exception
    brokkoli = lade_vorrat(app_db, "anna", Wissensbasis()).iloc[0]
    assert brokkoli["zutat"] == "Brokkoli"
    assert brokkoli["menge"] == 0.8 and brokkoli["einheit"] == "kg"
    assert any("0.8 kg" in s.value for s in at.success)
    at.switch_page("app/startseite.py").run()
    assert any("0.8 kg" in m.value for m in at.markdown)


def test_einheit_und_menge_im_editor_anpassen(app_db, monkeypatch):
    import streamlit as st

    # AppTest unterstützt das Bearbeiten von data_editor noch nicht. Die
    # bearbeiteten Zellen simulieren, dann den echten Speichern-Ablauf prüfen.
    def bearbeiteter_vorrat(df, **optionen):
        assert "einheit" not in optionen["disabled"]
        assert "kg" in optionen["column_config"]["einheit"]["type_config"]["options"]
        df = df.copy()
        df.loc[df.index[0], ["menge", "einheit"]] = [0.8, "kg"]
        return df

    monkeypatch.setattr(st, "data_editor", bearbeiteter_vorrat)
    fuege_hinzu(app_db, "anna", "Brokkoli", 800, "g", None)
    at = startseite()
    at.switch_page("app/vorrat.py").run()
    next(b for b in at.button if b.label == "Änderungen speichern").click().run()
    assert not at.exception
    brokkoli = lade_vorrat(app_db, "anna", Wissensbasis()).iloc[0]
    assert brokkoli["menge"] == 0.8 and brokkoli["einheit"] == "kg"


def test_grundstock_anpassen_ohne_andere_personen_zu_aendern(app_db):
    from app.datenbank import lade_grundstock
    from wissensbasis.grundstock import STANDARD_GRUNDSTOCK

    for z, m, e in [("Spaghetti", 200, "g"), ("Ei", 2, "Stück"),
                     ("Parmesan", 40, "g"), ("Speck", 100, "g")]:
        fuege_hinzu(app_db, "anna", z, m, e, None)
    at = startseite()
    assert any(s.value == "Spaghetti Carbonara" for s in at.subheader)
    at.switch_page("app/haushalt.py").run()
    at.multiselect[0].set_value([])
    next(b for b in at.button if b.label == "Grundstock speichern").click().run()
    assert not at.exception
    assert lade_grundstock(app_db, "anna") == []
    assert lade_grundstock(app_db, "ben") == list(STANDARD_GRUNDSTOCK)
    at.switch_page("app/startseite.py").run()
    assert not any(s.value == "Spaghetti Carbonara" for s in at.subheader)
    assert any(b.key == "einkauf_Pfeffer" for b in at.button)
    at.switch_page("app/vorrat.py").run()
    at.selectbox(key="erfassen_zutat").select("Pfeffer").run()
    assert not at.exception
    assert at.selectbox(key="erfassen_einheit_Pfeffer").value == "g"
    at.switch_page("app/haushalt.py").run()
    next(b for b in at.button if b.label == "Standardliste wiederherstellen").click().run()
    assert not at.exception
    assert set(lade_grundstock(app_db, "anna")) == set(STANDARD_GRUNDSTOCK)


def test_testszenario_seite_verwendet_keine_nutzerdatenbank(app_db, monkeypatch):
    at = startseite()

    def kein_datenbankzugriff():
        raise AssertionError("Testszenario darf nicht auf Nutzerdaten zugreifen")

    monkeypatch.setattr(ressourcen, "verbindung", kein_datenbankzugriff)
    at.switch_page("app/szenarien_seite.py").run()
    assert not at.exception
    for index in range(3):
        at.selectbox[0].select_index(index).run()
        assert not at.exception
        assert at.success
        assert not at.feedback
    assert lade_vorrat(app_db, "anna", Wissensbasis()).empty
    assert lade_bewertungen(app_db) == []


@pytest.mark.parametrize("kartoffeln", [200, 800])
def test_gratin_mit_halbrahm_zeigt_sterne_und_rezeptmengen(app_db, kartoffeln):
    fuege_hinzu(app_db, "anna", "Kartoffel", kartoffeln, "g", None)
    fuege_hinzu(app_db, "anna", "Halbrahm", 350, "ml", None)
    at = AppTest.from_string("""
from app.rezeptansicht import gekocht_dialog
from app.datenbank import lade_vorrat, vorrat_als_liste
from app.ressourcen import verbindung, wissensbasis
from wissensbasis.eignung import finde_kandidaten, lade_rezepte
wb = wissensbasis()
vorrat = vorrat_als_liste(lade_vorrat(verbindung(), 'anna', wb))
kandidat = next(k for k in finde_kandidaten(lade_rezepte(), vorrat, wb)
                if k['rezept']['id'] == 'kartoffelgratin')
gekocht_dialog(kandidat, vorrat)
""")
    at.session_state.person = "anna"
    at.run()
    assert not at.exception
    vorher = lade_vorrat(app_db, "anna", Wissensbasis())
    ids = {r.zutat: int(r.Index) for r in vorher.itertuples()}
    assert at.number_input(key=f"verbrauch_kartoffelgratin_{ids['Kartoffel']}").value == 600
    # 150 ml Rahm und 150 ml Milch-Ersatz aus derselben Packung.
    assert at.number_input(key=f"verbrauch_kartoffelgratin_{ids['Halbrahm']}").value == 300
    assert not at.select_slider
    at.feedback(key="sterne_anna_kartoffelgratin").set_value(3).run()
    speichern = next(b for b in at.button if b.label == "Speichern")
    assert speichern.disabled == (kartoffeln < 600)
    if kartoffeln >= 600:
        speichern.click().run()
        assert not at.exception
        nachher = lade_vorrat(app_db, "anna", Wissensbasis())
        assert nachher.loc[ids["Kartoffel"], "menge"] == 200
        assert nachher.loc[ids["Halbrahm"], "menge"] == 50
        assert lade_bewertungen(app_db)[0]["note"] == 4
