"""Gespeicherte künstliche Vorräte prüfen die echte Wissensbasis und Bestandslogik."""
from copy import deepcopy
from datetime import date

import pytest

from app.datenbank import aktualisiere, fuege_hinzu, koche, lade_vorrat, verbinde, vorrat_als_liste
from app.testszenarien import lade_szenarien, pruefe_szenario, szenario_vorrat
from app.verbrauch import verbrauchsplan
from wissensbasis.eignung import lade_rezepte
from wissensbasis.wissen import Wissensbasis


@pytest.mark.parametrize("szenario", lade_szenarien(), ids=lambda s: s["id"])
def test_gespeicherte_szenarien(szenario):
    vorher = deepcopy(szenario)
    stimmt, _ = pruefe_szenario(szenario, Wissensbasis(), lade_rezepte())
    assert stimmt
    assert szenario == vorher


def test_szenario_hat_festes_datum_und_effektiven_ablauf():
    s = next(s for s in lade_szenarien() if s["id"] == "gratin")
    wb, vorrat = szenario_vorrat(s, Wissensbasis())
    assert vorrat[0]["tage"] == 1
    assert vorrat[1]["tage"] == 3  # Geöffnet + 4 Tage, früher als das Etikett.
    r = next(r for r in lade_rezepte() if r["id"] == "kartoffelgratin")
    assert verbrauchsplan(r, vorrat, wb) == {1: 600, 2: 150, 3: 150}


def test_kuenstlicher_vorrat_prueft_kochen_in_separater_datenbank(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    s = next(s for s in lade_szenarien() if s["id"] == "gratin")
    wb, _ = szenario_vorrat(s, Wissensbasis())
    conn = verbinde(tmp_path / "szenario.db")
    for z in s["zutaten"]:
        fuege_hinzu(conn, "testperson", z["zutat"], z["menge"], z["einheit"], date.fromisoformat(z["ablaufdatum"]))
        if z.get("geoeffnet_am"):
            eintrag_id = conn.execute("SELECT MAX(id) FROM vorratseintrag").fetchone()[0]
            aktualisiere(conn, "testperson", eintrag_id, z["menge"], date.fromisoformat(z["ablaufdatum"]),
                         date.fromisoformat(z["geoeffnet_am"]))
    vorher = vorrat_als_liste(lade_vorrat(conn, "testperson", wb, heute=date.fromisoformat(s["datum"])))
    r = next(r for r in lade_rezepte() if r["id"] == "kartoffelgratin")
    koche(conn, "testperson", r["id"], 4, vorher, verbrauchsplan(r, vorher, wb), grundstock=s["grundstock"])
    assert list(lade_vorrat(conn, "testperson", wb)["menge"]) == [200, 50, 50]
