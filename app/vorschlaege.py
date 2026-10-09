"""Seite: Top-3-Rezeptvorschläge mit Begründung und Bewertung.

Ablauf: Vorrat laden -> Wissensbasis filtert geeignete Rezepte -> Ranking sortiert
-> Anzeige mit Begründung -> Bewertung wird mit Vorrat-Snapshot gespeichert (Trainingsdaten).
Mit "Gekocht" werden die verwendeten Zutaten aus dem Vorrat entfernt.
"""
import streamlit as st

from app.datenbank import koche, lade_vorrat, speichere_bewertung, vorrat_als_liste
from app.ressourcen import ml_modell, verbindung, wissensbasis
from ml.ranking import sortiere
from wissensbasis.eignung import finde_kandidaten, lade_rezepte

conn = verbindung()
wb = wissensbasis()
person = st.session_state.person  # gesetzt in cooler_ai.py


def zutaten_text(rezept):
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
    """Fragt, was aufgebraucht ist, speichert die Bewertung und baut den Vorrat ab."""
    rezept = kandidat["rezept"]
    st.markdown(f"**{rezept['titel']}**")

    aufgebraucht = []
    if kandidat["verwendet"]:
        st.write("Welche Zutaten sind jetzt aufgebraucht? Abwählen, was noch übrig ist.")
        for artikel in kandidat["verwendet"]:
            if st.checkbox(wb.namen.get(artikel["zutat"], artikel["zutat"]), value=True,
                           key=f"aufgebraucht_{rezept['id']}_{artikel['id']}"):
                aufgebraucht.append(artikel["id"])
    else:
        st.write("Das Rezept braucht nur Zutaten aus dem Grundstock.")

    note = st.select_slider("Wie hat es geschmeckt?", options=[1, 2, 3, 4, 5], value=4)
    if st.button("Speichern", type="primary"):
        koche(conn, person, rezept["id"], note, vorrat, aufgebraucht)
        meldung = f"{len(aufgebraucht)} Zutaten aus dem Vorrat entfernt."
        if kandidat["dringend"]:
            gerettet = ", ".join(wb.namen[z] for z in kandidat["dringend"])
            meldung = f"Gerettet: {gerettet}! " + meldung
        st.session_state.meldung = meldung  # wird nach dem Neuladen oben angezeigt
        st.rerun()


def zeige_rezept(kandidat, vorrat):
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

        with st.form(f"bewertung_{rezept['id']}", border=False):
            note = st.select_slider("Wie gerne würdest du das heute kochen?",
                                    options=[1, 2, 3, 4, 5], value=3)
            if st.form_submit_button("Bewertung speichern"):
                speichere_bewertung(conn, person, rezept["id"], note, vorrat)
                st.success("Danke! Die Bewertung fliesst ins nächste Training ein.")

        if st.button("🍳 Gekocht", key=f"gekocht_{rezept['id']}",
                     help="Bewertet das Rezept und entfernt die verwendeten Zutaten aus dem Vorrat."):
            gekocht_dialog(kandidat, vorrat)


st.title("Was koche ich heute?")
if "meldung" in st.session_state:
    st.success(st.session_state.pop("meldung"), icon="🎉")

vorrat_df = lade_vorrat(conn, person, wb)
if vorrat_df.empty:
    st.info("Der Vorrat ist leer. Erfasse zuerst unter «Vorrat», was du zu Hause hast.")
    st.stop()
vorrat = vorrat_als_liste(vorrat_df)

c1, c2 = st.columns(2)
nur_vegetarisch = c1.toggle("Nur vegetarisch")
max_kochzeit = c2.slider("Maximale Kochzeit (Minuten)", 10, 90, 90, step=5)

kandidaten = [
    k for k in finde_kandidaten(lade_rezepte(), vorrat, wb)
    if (k["vegetarisch"] or not nur_vegetarisch) and k["rezept"]["kochzeit_min"] <= max_kochzeit
]

modell = ml_modell()
sortiert = sortiere(kandidaten, modell)
if modell is None:
    st.caption("Sortierung: regelbasiert (noch zu wenig Bewertungen für das ML-Modell).")
else:
    st.caption("Sortierung: ML-Modell, gelernt aus euren Bewertungen.")

if not sortiert:
    st.warning("Mit dem aktuellen Vorrat passt kein Rezept. Ergänze den Vorrat oder lockere die Filter.")
    st.stop()

for kandidat in sortiert[:3]:
    zeige_rezept(kandidat, vorrat)

rest = sortiert[3:]
if rest and st.toggle(f"{len(rest)} weitere geeignete Rezepte anzeigen"):
    st.caption("Bitte auch hier ab und zu bewerten, sonst lernt das Modell nur von den Top 3.")
    for kandidat in rest:
        zeige_rezept(kandidat, vorrat)
