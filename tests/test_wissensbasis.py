"""Tests für Wissensbasis und Rezeptdaten.

Start (im Hauptordner):  pytest

Die ersten Tests prüfen die KONSISTENZ der Daten. Sie schlagen an, wenn beim Pflegen
der Ontologie oder der Rezepte ein Tippfehler passiert (z.B. unbekannte Zutat-ID).
"""
from datetime import date

import pytest

from wissensbasis.eignung import (fast_geeignete, fehlende_pflichtzutaten, finde_kandidaten, lade_rezepte,
                                  pruefe_rezept)
from wissensbasis.wissen import Wissensbasis


@pytest.fixture(scope="module")
def wb():
    return Wissensbasis()


@pytest.fixture(scope="module")
def rezepte():
    return lade_rezepte()


# ------------------------------------------------------------ Konsistenz der Daten

def test_rezeptzutaten_existieren_in_ontologie(wb, rezepte):
    for r in rezepte:
        for e in r["zutaten"]:
            assert e["zutat"] in wb.namen, f"{r['id']}: unbekannte Zutat {e['zutat']}"


def test_rezept_ids_eindeutig(rezepte):
    ids = [r["id"] for r in rezepte]
    assert len(ids) == len(set(ids))


def test_ersatzregeln_verweisen_auf_bekannte_zutaten(wb):
    for regel in wb.ersatzregeln:
        assert regel["original"] in wb.namen, regel
        assert regel["ersatz"] in wb.namen, regel


def test_auswaehlbare_zutaten_haben_einheit(wb):
    for z in wb.zutaten_zur_auswahl():
        assert wb.eigenschaft(z, "einheit") in ("g", "ml", "Stück"), z


def test_jede_zutat_haengt_unter_zutat(wb):
    for z in wb.namen:
        assert wb.ist_ein(z, "Zutat"), z


# ------------------------------------------------------------ Logik der Wissensbasis

def test_hierarchie(wb):
    assert wb.vorfahren("Cherrytomate") == ["Cherrytomate", "Tomate", "Gemuese", "Zutat"]
    assert wb.ist_ein("Cherrytomate", "Tomate")
    assert not wb.ist_ein("Tomate", "Cherrytomate")


def test_eigenschaften_werden_vererbt(wb):
    assert wb.eigenschaft("Vollrahm", "einheit") == "ml"      # von Rahm
    assert wb.eigenschaft("Kochrahm", "haltbarTage") == 30     # eigener Wert überschreibt Rahm (21)
    assert wb.ist_grundstock("Salz")                           # von Gewuerz
    assert not wb.ist_vegetarisch("Speck")                     # von Fleisch
    assert wb.ist_vegetarisch("Karotte")                       # von Zutat


def test_effektives_ablaufdatum(wb):
    etikett = date(2026, 10, 20)
    # Rahm hält geöffnet 4 Tage -> früheres Datum gewinnt
    assert wb.effektives_ablaufdatum("Vollrahm", etikett, date(2026, 10, 1)) == date(2026, 10, 5)
    assert wb.effektives_ablaufdatum("Vollrahm", etikett, None) == etikett
    # Karotten haben keine Haltbarkeit nach dem Öffnen
    assert wb.effektives_ablaufdatum("Karotte", etikett, date(2026, 10, 1)) == etikett


# ------------------------------------------------------------ Eignungsprüfung

def rezept(*zutaten):
    """Hilfsfunktion: Testrezept aus (zutat, pflicht)-Paaren."""
    return {"id": "test", "titel": "Test", "kochzeit_min": 10, "portionen": 1,
            "zutaten": [{"zutat": z, "menge": None, "einheit": None, "pflicht": p} for z, p in zutaten]}


def test_pflichtzutat_fehlt(wb):
    assert pruefe_rezept(rezept(("Poulet", True)), [], wb) is None


def test_optionale_zutat_fehlt(wb):
    ergebnis = pruefe_rezept(rezept(("Karotte", True), ("Lauch", False)), [{"zutat": "Karotte", "tage": 5}], wb)
    assert ergebnis["fehlend_optional"] == ["Lauch"]


def test_grundstock_muss_nicht_im_vorrat_sein(wb):
    assert pruefe_rezept(rezept(("Salz", True), ("Olivenoel", True)), [], wb) is not None


def test_unterklasse_erfuellt_oberklasse(wb):
    ergebnis = pruefe_rezept(rezept(("Tomate", True)), [{"zutat": "Cherrytomate", "tage": 5}], wb)
    assert ergebnis is not None
    assert ergebnis["merkmale"]["abdeckung"] == 1.0


def test_ersatzregel_wird_angewendet_und_begruendet(wb):
    ergebnis = pruefe_rezept(rezept(("Vollrahm", True)), [{"zutat": "CremeFraiche", "tage": 5}], wb)
    assert ergebnis is not None
    assert ergebnis["merkmale"]["ersetzungen"] == 1
    assert any("Crème fraîche statt Vollrahm" in b for b in ergebnis["begruendungen"])


def test_dringende_zutat_wird_erkannt(wb):
    ergebnis = pruefe_rezept(rezept(("Spinat", True)), [{"zutat": "Spinat", "tage": 1}], wb)
    assert ergebnis["merkmale"]["dringend"] == 1
    assert ergebnis["begruendungen"][0].startswith("Verwertet Spinat")


def test_vegetarisch_wird_aus_hierarchie_abgeleitet(wb, rezepte):
    nach_id = {r["id"]: r for r in rezepte}
    vorrat = [{"zutat": z, "tage": 5} for z in ["Spaghetti", "Ei", "Speck", "Parmesan", "Linsen", "Pelati", "Zwiebel"]]
    ergebnisse = {k["rezept"]["id"]: k for k in finde_kandidaten(rezepte, vorrat, wb)}
    assert not ergebnisse["spaghetti_carbonara"]["vegetarisch"]
    assert ergebnisse["linsen_chili"]["vegetarisch"]
    assert "spaghetti_carbonara" in nach_id


def test_verwendete_artikel_werden_zurueckgegeben(wb):
    rahm = {"id": 1, "zutat": "Vollrahm", "tage": 2}
    karotte = {"id": 2, "zutat": "Karotte", "tage": 10}
    # Rahm deckt Rahm direkt und Milch per Ersatzregel ab, soll aber nur einmal aufgebraucht werden
    ergebnis = pruefe_rezept(rezept(("Rahm", True), ("Milch", True)), [rahm, karotte], wb)
    assert ergebnis["verwendet"] == [rahm]
    assert ergebnis["dringend"] == ["Vollrahm"]


# ------------------------------------------------------------ Einkaufsideen (fast geeignete Rezepte)

def test_fehlende_pflichtzutaten(wb):
    r = rezept(("Karotte", True), ("Lauch", True), ("Feta", False), ("Salz", True))
    assert fehlende_pflichtzutaten(r, [{"zutat": "Karotte", "tage": 5}], wb) == ["Lauch"]
    # Ersetzbare Zutaten fehlen nicht: Lauch ersetzt Zwiebel
    r = rezept(("Zwiebel", True))
    assert fehlende_pflichtzutaten(r, [{"zutat": "Lauch", "tage": 5}], wb) == []


def test_fast_geeignet_bei_genau_einer_luecke(wb):
    rezepte = [
        {**rezept(("Karotte", True), ("Lauch", True)), "id": "eine_luecke"},
        {**rezept(("Karotte", True), ("Lauch", True), ("Poulet", True)), "id": "zwei_luecken"},
        {**rezept(("Lachs", True)), "id": "nichts_aus_dem_vorrat"},
        {**rezept(("Karotte", True)), "id": "schon_geeignet"},
    ]
    vorrat = [{"zutat": "Karotte", "tage": 1}]
    ergebnis = fast_geeignete(rezepte, vorrat, wb)
    assert [(f["fehlt"], f["kandidat"]["rezept"]["id"]) for f in ergebnis] == [("Lauch", "eine_luecke")]
    # Die Karotte im Vorrat wird gerettet, der gekaufte Lauch zählt nicht als dringend
    assert ergebnis[0]["kandidat"]["dringend"] == ["Karotte"]
