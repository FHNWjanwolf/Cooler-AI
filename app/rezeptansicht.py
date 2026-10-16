"""Seite: Top-3-Rezeptvorschläge mit Begründung und Bewertung.

Ablauf: Vorrat laden -> Wissensbasis filtert geeignete Rezepte -> Ranking sortiert
-> Anzeige mit Begründung -> Bewertung wird mit Vorrat-Snapshot gespeichert (Trainingsdaten).
Mit "Gekocht" werden die verbrauchten Mengen vom Vorrat abgezogen.
"""
import streamlit as st

from app.datenbank import koche, vorrat_als_liste
from app import ressourcen
from app.verbrauch import verbrauchsplan
from ml.ranking import sortiere
from wissensbasis.eignung import finde_kandidaten, lade_rezepte


def zutaten_text(rezept):
    wb = ressourcen.wissensbasis()
    teile = []
    for e in rezept["zutaten"]:
        text = wb.namen[e["zutat"]]
        if e["menge"]:
            text = f"{e['menge']:g} {e['einheit']} {text}"
        if not e["pflicht"]:
            text += " (optional)"
        teile.append(text)
    return ", ".join(teile)


@st.dialog("Guten Appetit!")
def gekocht_dialog(kandidat, vorrat):
    """Verbrauch prüfen, Bewertung speichern und Restmengen behalten."""
    wb = ressourcen.wissensbasis()
    if "grundstock" in kandidat:
        wb = wb.mit_grundstock(kandidat["grundstock"])
    person = st.session_state.person
    rezept = kandidat["rezept"]
    st.markdown(f"**{rezept['titel']}**")
    st.caption("Rezeptmengen: " + zutaten_text(rezept))

    verbrauch = {}
    plan = verbrauchsplan(rezept, vorrat, wb)
    fehlmenge = False
    if plan:
        st.write("Wie viel hast du verwendet? Prüfe die Rezeptmengen und passe sie bei Bedarf an. "
                 "Mit 0 bleibt eine Zutat unverändert.")
        for artikel in vorrat:
            if artikel["id"] not in plan:
                continue
            name = wb.namen.get(artikel["zutat"], artikel["zutat"])
            einheit = artikel["einheit"] or ""
            menge = artikel["menge"]
            vorschlag = plan[artikel["id"]]
            key = f"verbrauch_{rezept['id']}_{artikel['id']}"
            if menge is not None and menge >= 0:
                if vorschlag is None:
                    st.caption(f"{name}: Verbrauch bitte selbst eintragen (fehlende Mengen, "
                               "unterschiedliche Einheiten oder Ersatzprodukt).")
                verwendet = st.number_input(
                    f"{name}: verwendet ({einheit})", min_value=0.0,
                    value=float(vorschlag) if vorschlag is not None else None, key=key,
                )
                verwendet = verwendet or 0.0
                if verwendet > menge:
                    fehlmenge = True
                    st.warning(f"{name}: Vorgeschlagen sind {verwendet:g} {einheit}, erfasst sind "
                               f"{menge:g} {einheit}. Passe den tatsächlichen Verbrauch an oder "
                               "ergänze zuerst den Vorrat.")
                else:
                    st.caption(f"Vorhanden: {menge:g} {einheit} · Übrig: {menge - verwendet:g} {einheit}")
                verbrauch[artikel["id"]] = verwendet
            else:
                st.number_input(f"{name}: verwendet ({einheit})", min_value=0.0,
                                value=float(vorschlag) if vorschlag is not None else None, key=key)
                st.caption(f"{name}: Vorratsmenge unbekannt; auch die Restmenge bleibt unbekannt. "
                           "Für einen berechneten Restbestand zuerst die Menge unter «Vorrat» erfassen.")
                if st.checkbox(f"{name} vollständig aufgebraucht", value=False, key=key + "_aufgebraucht"):
                    verbrauch[artikel["id"]] = None
    else:
        st.write("Das Rezept braucht nur Zutaten aus dem Grundstock.")

    st.caption("Bei Ersatzprodukten ist die Rezeptmenge ein Vorschlag; prüfe den tatsächlichen Verbrauch.")
    st.write("Wie hat es geschmeckt?")
    sterne = st.feedback("stars", key=f"sterne_{person}_{rezept['id']}")
    if sterne is not None:
        st.caption(f"{sterne + 1} von 5 Sternen")
    if st.button("Speichern", type="primary", disabled=sterne is None or fehlmenge):
        try:
            # Der Dialog kann länger offen sein als die Turso-Verbindung gültig ist.
            koche(ressourcen.verbindung(), person, rezept["id"], sterne + 1, vorrat, verbrauch,
                  grundstock=kandidat.get("grundstock", sorted(wb.grundstock_ids)))
        except ValueError as fehler:
            st.error(str(fehler))
            return
        anzahl = sum(m is None or m > 0 for m in verbrauch.values())
        meldung = f"Verbrauch für {anzahl} Vorratseinträge gespeichert. Restmengen bleiben im Vorrat."
        gerettete = [v["zutat"] for v in vorrat if v["zutat"] in kandidat["dringend"]
                     and v["id"] in verbrauch
                     and (verbrauch[v["id"]] is None or verbrauch[v["id"]] > 0)]
        if gerettete:
            gerettet = ", ".join(wb.namen[z] for z in dict.fromkeys(gerettete))
            meldung = f"Gerettet: {gerettet}! " + meldung
        st.session_state.meldung = meldung  # wird nach dem Neuladen oben angezeigt
        st.rerun()


def zeige_rezept(kandidat, vorrat):
    wb = ressourcen.wissensbasis()
    person = st.session_state.person
    rezept = kandidat["rezept"]
    with st.container(border=True):
        st.subheader(rezept["titel"])
        info = f"{rezept['kochzeit_min']} Min. · {rezept['portionen']} Portionen"
        if kandidat["vegetarisch"]:
            info += " · vegetarisch"
        st.caption(info)

        for b in kandidat["begruendungen"]:
            st.markdown(f"- {b}")
        if kandidat["fehlend_optional"]:
            st.caption("Optional, aber nicht im Vorrat: " + ", ".join(kandidat["fehlend_optional"]))
        st.caption("Zutaten: " + zutaten_text(rezept))

        if st.button("🍳 Gekocht", key=f"gekocht_{rezept['id']}",
                     help="Bewertet das Rezept und zieht die verbrauchten Mengen vom Vorrat ab."):
            # Bei jedem neuen Öffnen wieder mit den aktuellen Rezeptmengen
            # beginnen, auch wenn ein vorheriger Dialog abgebrochen wurde.
            for key in list(st.session_state):
                if key.startswith(f"verbrauch_{rezept['id']}_") or key == f"sterne_{person}_{rezept['id']}":
                    del st.session_state[key]
            gekocht_dialog(kandidat, vorrat)


def zeige_vorschlaege(vorrat_df):
    """Menüvorschläge auf Startseite und Rezeptseite identisch anzeigen."""
    wb = ressourcen.wissensbasis()
    if vorrat_df.empty:
        st.info("Erfasse zuerst deinen Vorrat, dann erscheinen hier passende Menüs.")
    vorrat = vorrat_als_liste(vorrat_df)
    c1, c2 = st.columns(2)
    nur_vegetarisch = c1.toggle("Nur vegetarisch")
    max_kochzeit = c2.slider("Maximale Kochzeit (Minuten)", 10, 90, 90, step=5)
    kandidaten = [
        k for k in finde_kandidaten(lade_rezepte(), vorrat, wb)
        if (k["vegetarisch"] or not nur_vegetarisch) and k["rezept"]["kochzeit_min"] <= max_kochzeit
    ]
    modell = ressourcen.ml_modell()
    sortiert = sortiere(kandidaten, modell)
    if modell is None:
        st.caption("Sortierung nach Resteverwertung. Mit genügend Kochbewertungen lernt die App eure Vorlieben.")
    else:
        st.caption("Sortierung nach euren Vorlieben und bisherigen Bewertungen.")
    if not sortiert:
        st.info("Mit deinem Vorrat passt noch kein Menü. Schau dir die Einkaufsideen an oder passe die Filter an.")
        return
    for kandidat in sortiert[:3]:
        zeige_rezept(kandidat, vorrat)
    rest = sortiert[3:]
    if rest and st.toggle(f"{len(rest)} weitere geeignete Rezepte anzeigen"):
        for kandidat in rest:
            zeige_rezept(kandidat, vorrat)


def zeige_meldung():
    if "meldung" in st.session_state:
        st.success(st.session_state.pop("meldung"), icon="🎉")
