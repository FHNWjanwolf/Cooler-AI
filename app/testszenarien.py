"""Gespeicherte künstliche Vorräte, unabhängig von Uhrzeit und Nutzerdatenbank.

Prüfen: python -m app.testszenarien
"""
import json
import math
from datetime import date
from pathlib import Path

from wissensbasis.eignung import finde_kandidaten, lade_rezepte
from wissensbasis.wissen import Wissensbasis

SZENARIEN = Path(__file__).resolve().parents[1] / "daten" / "testszenarien"


def lade_szenarien(pfad=SZENARIEN):
    szenarien = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pfad.glob("*.json"))]
    if not szenarien:
        raise ValueError("Es wurden keine gespeicherten Testszenarien gefunden.")
    ids = [s["id"] for s in szenarien]
    if len(ids) != len(set(ids)):
        raise ValueError("Die Testszenario-IDs müssen eindeutig sein.")
    return szenarien


def szenario_vorrat(szenario, basis):
    """Konkrete Einträge ins Format der Wissensbasis übersetzen, mit festem Stichtag."""
    wb = basis.mit_grundstock(szenario["grundstock"])
    heute = date.fromisoformat(szenario["datum"])
    vorrat = []
    for eintrag_id, z in enumerate(szenario["zutaten"], start=1):
        if z["zutat"] not in wb.namen or not math.isfinite(z["menge"]) or z["menge"] <= 0:
            raise ValueError("Testszenarien benötigen bekannte Zutaten und konkrete positive Mengen.")
        if z["einheit"] not in ("g", "kg", "ml", "l", "Stück", "Stk"):
            raise ValueError("Unbekannte Einheit im Testszenario.")
        ablauf = date.fromisoformat(z["ablaufdatum"])
        geoeffnet = date.fromisoformat(z["geoeffnet_am"]) if z.get("geoeffnet_am") else None
        effektiv = wb.effektives_ablaufdatum(z["zutat"], ablauf, geoeffnet)
        vorrat.append({"id": eintrag_id, "zutat": z["zutat"], "menge": z["menge"],
                       "einheit": z["einheit"], "tage": (effektiv - heute).days})
    return wb, vorrat


def pruefe_szenario(szenario, basis, rezepte):
    wb, vorrat = szenario_vorrat(szenario, basis)
    kandidaten = finde_kandidaten(rezepte, vorrat, wb)
    ist = sorted(k["rezept"]["id"] for k in kandidaten)
    return ist == sorted(szenario["erwartete_rezepte"]), kandidaten


def main():
    basis, rezepte = Wissensbasis(), lade_rezepte()
    fehler = False
    for s in lade_szenarien():
        stimmt, kandidaten = pruefe_szenario(s, basis, rezepte)
        print(f"{'OK' if stimmt else 'FEHLER'}: {s['titel']} – "
              + ", ".join(k["rezept"]["id"] for k in kandidaten))
        fehler = fehler or not stimmt
    raise SystemExit(1 if fehler else 0)


if __name__ == "__main__":
    main()
