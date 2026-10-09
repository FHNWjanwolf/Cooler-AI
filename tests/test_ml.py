"""Tests für Ranking und Training (mit künstlichen Bewertungen, nur zum Prüfen der Mechanik)."""
import numpy as np

from ml.ranking import einkaufsideen, sortiere
from ml.trainiere import erstelle_datensatz, top3_trefferquote, trainiere
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis


def kandidat(rezept_id, dringend):
    merkmale = {"abdeckung": 1.0, "ersetzungen": 0, "fehlend_optional": 0, "dringend": dringend}
    return {"rezept": {"id": rezept_id}, "merkmale": merkmale}


def test_baseline_bevorzugt_dringende_rezepte():
    sortiert = sortiere([kandidat("a", 0), kandidat("b", 2), kandidat("c", 1)])
    assert [k["rezept"]["id"] for k in sortiert] == ["b", "c", "a"]


def test_training_lernt_vorliebe():
    """Künstlicher Nutzer mag Teigwaren und mag keinen Fisch. Das Modell soll das lernen."""
    wb = Wissensbasis()
    rezepte = lade_rezepte()
    vorrat = [{"zutat": z, "tage": 10} for z in
              ["Spaghetti", "Ei", "Speck", "Parmesan", "Pelati", "Vollrahm", "Zwiebel",
               "Lachs", "Kartoffel", "Brokkoli", "Reis", "Linsen"]]
    bewertungen = []
    for _ in range(3):
        for r in rezepte:
            zutaten = [e["zutat"] for e in r["zutaten"]]
            if any(wb.ist_ein(z, "Teigwaren") for z in zutaten):
                note = 5
            elif any(wb.ist_ein(z, "Fisch") for z in zutaten):
                note = 1
            else:
                note = 3
            bewertungen.append({"rezept_id": r["id"], "note": note, "vorrat": vorrat})

    X, y = erstelle_datensatz(bewertungen, rezepte, wb)
    assert len(X) == len(y) > 0

    modell = trainiere(bewertungen, rezepte, wb)
    quote, situationen, _ = top3_trefferquote(bewertungen, rezepte, wb, modell)
    assert situationen > 0
    assert quote == 1.0  # alle Teigwaren-Rezepte landen oben


def test_gekocht_zaehlt_staerker_als_widersprechender_daumen():
    wb = Wissensbasis()
    rezepte = lade_rezepte()
    vorrat = [{"zutat": z, "tage": 10} for z in ["Kartoffel", "Rahm", "Milch"]]
    bewertungen = [
        {"rezept_id": "kartoffelgratin", "note": 1, "gekocht": False, "vorrat": vorrat},
        {"rezept_id": "kartoffelgratin", "note": 5, "gekocht": True, "vorrat": vorrat},
    ]
    X, y, gewichte = erstelle_datensatz(bewertungen, rezepte, wb, mit_gewichten=True)
    assert y == [0, 1] and gewichte == [1, 3]
    modell = trainiere(bewertungen, rezepte, wb)
    assert modell.predict_proba(X)[0, 1] > 0.7


def fast(fehlt, rezept_id, dringend=(), kategorie="Gemuese"):
    """Hilfsfunktion: ein fast geeignetes Rezept, wie es die Wissensbasis liefert."""
    kandidat = {"rezept": {"id": rezept_id}, "dringend": list(dringend),
                "merkmale": {f"enthaelt_{kategorie}": 1}}
    return {"fehlt": fehlt, "kandidat": kandidat}


def test_einkauf_deckt_allgemeinere_luecken_ab():
    wb = Wissensbasis()
    ideen = einkaufsideen([fast("Rahm", "a"), fast("Vollrahm", "b")], wb)
    nach_zutat = {i["zutat"]: [r["rezept"]["id"] for r in i["rezepte"]] for i in ideen}
    assert sorted(nach_zutat["Vollrahm"]) == ["a", "b"]  # Vollrahm ist auch Rahm
    assert nach_zutat["Rahm"] == ["a"]                    # irgendein Rahm reicht nicht für "Vollrahm"
    assert ideen[0]["zutat"] == "Vollrahm"


def test_einkauf_bevorzugt_rettung_ohne_modell():
    wb = Wissensbasis()
    ideen = einkaufsideen([fast("Lauch", "a"), fast("Ei", "b", dringend=["Spinat"])], wb)
    assert ideen[0]["zutat"] == "Ei"
    assert ideen[0]["gerettet"] == ["Spinat"]


class FischHasser:
    """Ersatz für ein trainiertes Modell: mag keinen Fisch."""
    def predict_proba(self, merkmale):
        p = [0.1 if m.get("enthaelt_Fisch") else 0.9 for m in merkmale]
        return np.array([[1 - x, x] for x in p])


def test_einkauf_beruecksichtigt_vorlieben_des_modells():
    wb = Wissensbasis()
    fast_geeignet = [fast("Lachs", "fisch", kategorie="Fisch"), fast("Lauch", "gemuese")]
    assert einkaufsideen(fast_geeignet, wb)[0]["zutat"] == "Lachs"            # ohne Modell: Gleichstand, alphabetisch
    assert einkaufsideen(fast_geeignet, wb, FischHasser())[0]["zutat"] == "Lauch"
