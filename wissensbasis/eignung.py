"""Eignungsprüfung: Kommt ein Rezept mit dem aktuellen Vorrat in Frage?

Hier entscheidet ausschliesslich die Wissensbasis (Regeln), nicht das ML-Modell.
Ein Rezept ist geeignet, wenn jede Pflichtzutat
  1. zum Grundstock gehört (Salz, Öl, ...), oder
  2. im Vorrat liegt, direkt oder über die Hierarchie (Cherrytomate zählt als Tomate), oder
  3. über eine Ersatzregel ersetzt werden kann (Rahm -> Crème fraîche).
Fehlende optionale Zutaten werden nur vermerkt.

Der Vorrat ist eine Liste von Dicts mit mindestens {"zutat": "<ID>", "tage": <int oder None>},
wobei "tage" die Tage bis zum effektiven Ablaufdatum sind.
"""
import json
from pathlib import Path

REZEPTE = Path(__file__).parent.parent / "daten" / "rezepte.json"
DRINGEND_AB_TAGEN = 3  # Artikel, die in höchstens so vielen Tagen ablaufen, gelten als dringend


def lade_rezepte(pfad=REZEPTE):
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def _finde_im_vorrat(vorrat, benoetigt, wb):
    """Passender Vorratsartikel. Bei mehreren den, der am frühesten abläuft."""
    passende = [v for v in vorrat if wb.ist_ein(v["zutat"], benoetigt)]
    if not passende:
        return None
    return min(passende, key=lambda v: v["tage"] if v["tage"] is not None else 10_000)


def _finde_ersatz(vorrat, benoetigt, wb):
    """Erste anwendbare Ersatzregel als (regel, vorratsartikel). Artikel ist None bei Grundstock."""
    for regel in wb.ersatz_fuer(benoetigt):
        if wb.ist_grundstock(regel["ersatz"]):
            return regel, None
        artikel = _finde_im_vorrat(vorrat, regel["ersatz"], wb)
        if artikel is not None:
            return regel, artikel
    return None


def _ablauf_text(tage):
    if tage < 0:
        return "abgelaufen, vorher prüfen"
    if tage == 0:
        return "läuft heute ab"
    if tage == 1:
        return "läuft morgen ab"
    return f"läuft in {tage} Tagen ab"


def pruefe_rezept(rezept, vorrat, wb):
    """Gibt None zurück, wenn das Rezept nicht in Frage kommt, sonst ein Prüfergebnis (Dict)."""
    begruendungen = []
    fehlend_optional = []
    verwendet = []        # Vorratsartikel, die das Rezept verbraucht
    anzahl_zutaten = 0    # ohne Grundstock
    direkt_vorhanden = 0
    ersetzungen = 0

    for eintrag in rezept["zutaten"]:
        benoetigt = eintrag["zutat"]
        name = wb.namen[benoetigt]
        if wb.ist_grundstock(benoetigt):
            continue
        anzahl_zutaten += 1

        artikel = _finde_im_vorrat(vorrat, benoetigt, wb)
        if artikel is not None:
            direkt_vorhanden += 1
            verwendet.append(artikel)
            if artikel["zutat"] != benoetigt:
                begruendungen.append(f"{wb.namen[artikel['zutat']]} zählt als {name}.")
            continue

        ersatz = _finde_ersatz(vorrat, benoetigt, wb)
        if ersatz is not None:
            regel, artikel = ersatz
            ersetzungen += 1
            if artikel is not None:
                verwendet.append(artikel)
            ersatz_name = wb.namen[artikel["zutat"] if artikel else regel["ersatz"]]
            begruendungen.append(f"{ersatz_name} statt {name}: {regel['begruendung']}")
            continue

        if eintrag["pflicht"]:
            return None  # Pflichtzutat fehlt und ist nicht ersetzbar
        fehlend_optional.append(name)

    # Welche dringenden Artikel werden verwertet? (Food-Waste-Begründung zuerst anzeigen)
    dringend = []
    for v in verwendet:
        if v["tage"] is not None and v["tage"] <= DRINGEND_AB_TAGEN and v["zutat"] not in dringend:
            dringend.append(v["zutat"])
            begruendungen.insert(0, f"Verwertet {wb.namen[v['zutat']]} ({_ablauf_text(v['tage'])}).")

    vegetarisch = all(wb.ist_vegetarisch(e["zutat"]) for e in rezept["zutaten"])

    # Merkmale für das ML-Ranking. Nur Zahlen; das Modell lernt daraus die Reihenfolge.
    merkmale = {
        "abdeckung": direkt_vorhanden / anzahl_zutaten if anzahl_zutaten else 1.0,
        "ersetzungen": ersetzungen,
        "fehlend_optional": len(fehlend_optional),
        "dringend": len(dringend),
        "kochzeit_min": rezept["kochzeit_min"],
        "vegetarisch": int(vegetarisch),
    }
    # Welche Kategorien kommen im Rezept vor? Damit kann das Modell Vorlieben lernen
    # (z.B. "wir mögen Teigwaren"), die keine Regel abbildet.
    for e in rezept["zutaten"]:
        if not wb.ist_grundstock(e["zutat"]):
            for k in wb.vorfahren(e["zutat"]):
                if k != "Zutat":
                    merkmale[f"enthaelt_{k}"] = 1

    return {
        "rezept": rezept,
        "vegetarisch": vegetarisch,
        "begruendungen": begruendungen,
        "fehlend_optional": fehlend_optional,
        "merkmale": merkmale,
    }


def finde_kandidaten(rezepte, vorrat, wb):
    """Alle geeigneten Rezepte (unsortiert)."""
    ergebnisse = (pruefe_rezept(r, vorrat, wb) for r in rezepte)
    return [e for e in ergebnisse if e is not None]
