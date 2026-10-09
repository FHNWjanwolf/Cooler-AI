"""Seite: Top-3-Rezeptvorschläge mit Begründung und Bewertung.

Ablauf: Vorrat laden -> Wissensbasis filtert geeignete Rezepte -> Ranking sortiert
-> Anzeige mit Begründung -> Bewertung wird mit Vorrat-Snapshot gespeichert (Trainingsdaten).
Mit "Gekocht" werden die verbrauchten Mengen vom Vorrat abgezogen.
"""
import streamlit as st

from app.datenbank import koche, speichere_bewertung, vorrat_als_liste
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
    person = st.session_state.person
    rezept = kandidat["rezept"]
    st.markdown(f"**{rezept['titel']}**")

    verbrauch = {}
    plan = verbrauchsplan(rezept, vorrat, wb)
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
                    f"{name}: verwendet ({einheit})", min_value=0.0, max_value=float(menge),
                    value=float(vorschlag or 0), key=key,
                )
                st.caption(f"Vorhanden: {menge:g} {einheit} · Übrig: {menge - verwendet:g} {einheit}")
                verbrauch[artikel["id"]] = verwendet
            else:
                st.caption(f"{name}: Vorratsmenge unbekannt. Für einen Teilverbrauch zuerst "
                           "die Menge unter «Vorrat» erfassen.")
                if st.checkbox(f"{name} vollständig aufgebraucht", value=False, key=key):
                    verbrauch[artikel["id"]] = None
    else:
        st.write("Das Rezept braucht nur Zutaten aus dem Grundstock.")

    note = st.select_slider("Wie hat es geschmeckt?", options=[1, 2, 3, 4, 5], value=4)
    if st.button("Speichern", type="primary"):
        try:
            # Der Dialog kann länger offen sein als die Turso-Verbindung gültig ist.
            koche(ressourcen.verbindung(), person, rezept["id"], note, vorrat, verbrauch)
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

        st.write("Würdest du das gerne kochen?")
        auswahl_key = f"interesse_{person}_{rezept['id']}"
        auswahl = st.session_state.get(auswahl_key)
        hoch, runter = st.columns(2)
        for spalte, wert, text in [(hoch, 5, "👍 Ja"), (runter, 1, "👎 Nein")]:
            if spalte.button(text, key=f"{auswahl_key}_{wert}", disabled=auswahl == wert):
                speichere_bewertung(ressourcen.verbindung(), person, rezept["id"], wert, vorrat)
                st.session_state[auswahl_key] = wert
                st.rerun()
        if auswahl is not None:
            st.caption("Danke, deine Rückmeldung ist gespeichert.")

        if st.button("🍳 Gekocht", key=f"gekocht_{rezept['id']}",
                     help="Bewertet das Rezept und zieht die verbrauchten Mengen vom Vorrat ab."):
            gekocht_dialog(kandidat, vorrat)


def zeige_vorschlaege(vorrat_df):
    """Menüvorschläge auf Startseite und Rezeptseite identisch anzeigen."""
    wb = ressourcen.wissensbasis()
    if vorrat_df.empty:
        st.info("Erfasse zuerst deinen Vorrat, dann erscheinen hier passende Menüs.")
        return
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
        st.caption("Sortierung nach Resteverwertung. Mit genügend Rückmeldungen lernt die App eure Vorlieben.")
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
