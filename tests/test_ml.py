"""Tests für Ranking und Training (mit künstlichen Bewertungen, nur zum Prüfen der Mechanik)."""
from ml.ranking import sortiere
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
