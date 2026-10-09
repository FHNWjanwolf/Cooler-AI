"""Rezeptmengen auf passende Vorratseinträge verteilen, älteste zuerst."""
from wissensbasis.eignung import _finde_ersatz, _finde_im_vorrat


def umrechnen(menge, von, nach):
    einheiten = {"g": ("gewicht", 1), "kg": ("gewicht", 1000),
                 "ml": ("volumen", 1), "l": ("volumen", 1000),
                 "Stück": ("anzahl", 1), "Stk": ("anzahl", 1)}
    if menge is None or von not in einheiten or nach not in einheiten:
        return None
    art_von, faktor_von = einheiten[von]
    art_nach, faktor_nach = einheiten[nach]
    return menge * faktor_von / faktor_nach if art_von == art_nach else None


def verbrauchsplan(rezept, vorrat, wb):
    """{ID: Verbrauch oder None}, ohne den Vorrat zu ändern.

    None verlangt eine manuelle Entscheidung: Mengen oder Einheiten fehlen bzw.
    sind nicht vergleichbar. Ersatzregeln enthalten keine Mengenverhältnisse.
    """
    plan = {}
    for zutat in rezept["zutaten"]:
        if wb.ist_grundstock(zutat["zutat"]):
            continue
        artikel = _finde_im_vorrat(vorrat, zutat["zutat"], wb)
        ersatz = False
        if artikel is None:
            regel = _finde_ersatz(vorrat, zutat["zutat"], wb)
            artikel = regel[1] if regel else None
            ersatz = True
        if artikel is None:
            continue
        passende = [v for v in vorrat if wb.ist_ein(v["zutat"],
                     artikel["zutat"] if ersatz else zutat["zutat"])]
        passende.sort(key=lambda v: v["tage"] if v["tage"] is not None else 10_000)
        rest = zutat["menge"]
        for v in passende:
            bedarf = umrechnen(rest, zutat["einheit"], v.get("einheit"))
            if ersatz or bedarf is None or v.get("menge") is None:
                plan[v["id"]] = None
                break
            bereits = plan.get(v["id"], 0.0)
            if bereits is None:
                break
            menge = min(bedarf, max(0.0, v["menge"] - bereits))
            plan[v["id"]] = bereits + menge
            rest -= umrechnen(menge, v["einheit"], zutat["einheit"])
            if rest <= 0:
                break
    return plan
