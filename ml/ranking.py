"""Ranking: sortiert die Rezepte, die die Wissensbasis als geeignet eingestuft hat.

Zwei Varianten:
  - baseline_score: feste, von Hand gewählte Gewichte (regelbasiert, kein ML).
  - ML-Modell: logistische Regression, gelernt aus den Bewertungen (ml/trainiere.py).
    Sie schätzt die Wahrscheinlichkeit, dass ein Rezept gut bewertet wird (Note >= 4).

Solange es zu wenig Bewertungen gibt, sortiert die App nach der Baseline.
Das Modell wird nicht als Datei gespeichert, sondern beim Start der App aus den
Bewertungen in der Datenbank trainiert (siehe app/ressourcen.py). Das dauert nur
Sekunden und funktioniert auch in der Streamlit Cloud, wo Dateien nicht erhalten bleiben.
"""
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def baseline_score(merkmale):
    """Regelbasierte Reihenfolge: zuerst verwerten, was bald abläuft, dann möglichst wenig Ersatz."""
    return (
        2.0 * merkmale["dringend"]
        + 1.0 * merkmale["abdeckung"]
        - 0.5 * merkmale["ersetzungen"]
        - 0.2 * merkmale["fehlend_optional"]
    )


def neues_modell():
    # DictVectorizer: wandelt die Merkmal-Dicts in eine Zahlenmatrix um
    #                 (unbekannte Merkmale beim Vorhersagen werden ignoriert).
    # StandardScaler: bringt Kochzeit (10-60) und 0/1-Merkmale auf eine vergleichbare Skala.
    # LogisticRegression: einfaches, gut erklärbares Modell; die Gewichte lassen sich anzeigen.
    return make_pipeline(
        DictVectorizer(sparse=False),
        StandardScaler(),
        LogisticRegression(max_iter=1000),
    )


def sortiere(kandidaten, modell=None):
    """Kandidaten absteigend nach Score. Jeder Kandidat bekommt das Feld "score"."""
    if not kandidaten:
        return []
    merkmale = [k["merkmale"] for k in kandidaten]
    if modell is None:
        scores = [baseline_score(m) for m in merkmale]
    else:
        scores = modell.predict_proba(merkmale)[:, 1]
    mit_score = [{**k, "score": float(s)} for k, s in zip(kandidaten, scores)]
    return sorted(mit_score, key=lambda k: k["score"], reverse=True)


def gewichte(modell):
    """Gelernte Gewichte pro Merkmal, wichtigste zuerst (zum Erklären in Präsentation/Bericht)."""
    namen = modell.named_steps["dictvectorizer"].get_feature_names_out()
    werte = modell.named_steps["logisticregression"].coef_[0]
    return sorted(zip(namen, werte), key=lambda x: abs(x[1]), reverse=True)


# ---------------------------------------------------------------- Einkaufsideen

NEUTRALE_VORLIEBE = 0.5   # ohne Modell zählt jedes Rezept gleich viel
GEWICHT_RETTUNG = 0.5     # Bonus pro Zutat, die bald abläuft und dank des Einkaufs verwertet wird


def einkaufsideen(fast_geeignete, wb, modell=None):
    """Welche Zutat lohnt sich zu kaufen? Wichtigste zuerst.

    Die Wissensbasis liefert die Rezepte, denen genau eine Zutat fehlt (fast_geeignete).
    Hier wird nur noch gewichtet und sortiert:

        Wert einer Zutat = Summe über alle Rezepte, die sie freischaltet, von
                           Vorliebe (ML: Wahrscheinlichkeit einer guten Bewertung)
                           + GEWICHT_RETTUNG * Anzahl verwerteter dringender Zutaten

    Über die Hierarchie deckt ein Kauf auch allgemeinere Lücken ab:
    Wer Vollrahm kauft, schaltet auch Rezepte frei, die nur "Rahm" verlangen.

    Rückgabe: Liste von Dicts {"zutat", "wert", "rezepte" (beste zuerst), "gerettet" (IDs)}.
    """
    if not fast_geeignete:
        return []
    kandidaten = [f["kandidat"] for f in fast_geeignete]
    if modell is None:
        vorlieben = [NEUTRALE_VORLIEBE] * len(kandidaten)
    else:
        vorlieben = modell.predict_proba([k["merkmale"] for k in kandidaten])[:, 1]

    ideen = []
    for kauf in sorted({f["fehlt"] for f in fast_geeignete}):
        rezepte, gerettet, wert = [], [], 0.0
        for f, vorliebe in zip(fast_geeignete, vorlieben):
            if not wb.ist_ein(kauf, f["fehlt"]):
                continue  # dieser Kauf füllt die Lücke des Rezepts nicht
            k = f["kandidat"]
            wert += float(vorliebe) + GEWICHT_RETTUNG * len(k["dringend"])
            rezepte.append({**k, "score": float(vorliebe)})
            gerettet += [z for z in k["dringend"] if z not in gerettet]
        rezepte.sort(key=lambda k: k["score"], reverse=True)
        ideen.append({"zutat": kauf, "wert": wert, "rezepte": rezepte, "gerettet": gerettet})

    return sorted(ideen, key=lambda i: i["wert"], reverse=True)
