"""Ranking-Modell trainieren und gegen die regelbasierte Baseline evaluieren.

Start (im Hauptordner):  python -m ml.trainiere

Ablauf:
  1. Bewertungen aus der Datenbank laden (älteste zuerst).
  2. Für jede Bewertung die Merkmale aus dem gespeicherten Vorrat-Snapshot neu berechnen.
  3. Zeitlicher Split: die ältesten 80 % zum Trainieren, die neuesten 20 % zum Testen.
  4. Metrik: Top-3-Trefferquote. Für jede gut bewertete Test-Situation wird geprüft,
     ob das Rezept unter den ersten drei Vorschlägen gelandet wäre (Modell vs. Baseline).
  5. Zum Schluss mit ALLEN Daten neu trainieren und das Modell speichern.
"""
from app.datenbank import lade_bewertungen, verbinde
from ml.ranking import gewichte, neues_modell, sortiere, speichere_modell
from wissensbasis.eignung import finde_kandidaten, lade_rezepte, pruefe_rezept
from wissensbasis.wissen import lade_wissensbasis

MIN_BEWERTUNGEN = 20
GUT_AB_NOTE = 4


def erstelle_datensatz(bewertungen, rezepte, wb):
    """Merkmale (X) und Labels (y: 1 = gut bewertet) aus den Bewertungen."""
    nach_id = {r["id"]: r for r in rezepte}
    X, y = [], []
    for b in bewertungen:
        rezept = nach_id.get(b["rezept_id"])
        if rezept is None:
            continue  # Rezept wurde inzwischen gelöscht
        pruefung = pruefe_rezept(rezept, b["vorrat"], wb)
        if pruefung is None:
            continue  # Wissensbasis wurde geändert, Rezept wäre heute nicht mehr geeignet
        X.append(pruefung["merkmale"])
        y.append(int(b["note"] >= GUT_AB_NOTE))
    return X, y


def trainiere(bewertungen, rezepte, wb):
    X, y = erstelle_datensatz(bewertungen, rezepte, wb)
    if len(set(y)) < 2:
        raise ValueError("Es braucht gute UND schlechte Bewertungen, sonst gibt es nichts zu lernen.")
    modell = neues_modell()
    modell.fit(X, y)
    return modell


def top3_trefferquote(test_bewertungen, rezepte, wb, modell):
    """Anteil gut bewerteter Situationen, in denen das Rezept unter den Top 3 wäre.

    modell=None bedeutet: Baseline. Gibt (Quote, Anzahl Situationen, davon mit <= 3 Kandidaten) zurück.
    """
    treffer = situationen = trivial = 0
    for b in test_bewertungen:
        if b["note"] < GUT_AB_NOTE:
            continue
        kandidaten = finde_kandidaten(rezepte, b["vorrat"], wb)
        if b["rezept_id"] not in [k["rezept"]["id"] for k in kandidaten]:
            continue
        top3 = [k["rezept"]["id"] for k in sortiere(kandidaten, modell)[:3]]
        situationen += 1
        treffer += b["rezept_id"] in top3
        trivial += len(kandidaten) <= 3  # hier ist jedes Ranking ein Treffer
    quote = treffer / situationen if situationen else float("nan")
    return quote, situationen, trivial


def main():
    wb = lade_wissensbasis()
    rezepte = lade_rezepte()
    bewertungen = lade_bewertungen(verbinde())
    print(f"{len(bewertungen)} Bewertungen gefunden.")
    if len(bewertungen) < MIN_BEWERTUNGEN:
        print(f"Zu wenig Daten: mindestens {MIN_BEWERTUNGEN} Bewertungen sammeln, dann erneut starten.")
        return

    # --- Evaluation mit zeitlichem Split (kein Zufall: wir testen auf "späteren" Situationen)
    grenze = int(len(bewertungen) * 0.8)
    train, test = bewertungen[:grenze], bewertungen[grenze:]
    modell = trainiere(train, rezepte, wb)
    quote_ml, n, trivial = top3_trefferquote(test, rezepte, wb, modell)
    quote_base, _, _ = top3_trefferquote(test, rezepte, wb, None)
    print(f"\nEvaluation auf {n} gut bewerteten Test-Situationen ({trivial} davon mit höchstens 3 Kandidaten):")
    print(f"  Top-3-Trefferquote Baseline: {quote_base:.0%}")
    print(f"  Top-3-Trefferquote ML:       {quote_ml:.0%}")

    # --- Endgültiges Modell mit allen Daten
    modell = trainiere(bewertungen, rezepte, wb)
    speichere_modell(modell)
    print("\nModell gespeichert. Wichtigste gelernte Gewichte:")
    for name, gewicht in gewichte(modell)[:10]:
        print(f"  {name:30s} {gewicht:+.2f}")


if __name__ == "__main__":
    main()
