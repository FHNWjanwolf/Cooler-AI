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
