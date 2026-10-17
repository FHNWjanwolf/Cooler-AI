"""Seite: Top-3-Rezeptvorschläge mit Begründung und Bewertung.

Ablauf: Vorrat laden -> Wissensbasis filtert geeignete Rezepte -> Ranking sortiert
-> Anzeige mit Begründung -> Bewertung wird mit Vorrat-Snapshot gespeichert (Trainingsdaten).
Mit "Gekocht" werden die verbrauchten Mengen vom Vorrat abgezogen.
"""
from html import escape

import streamlit as st

from app.datenbank import koche, vorrat_als_liste
from app import ressourcen
from app.gestaltung import leer
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


@st.dialog("Kochen abschliessen", width="large")
def gekocht_dialog(kandidat, vorrat):
    """Verbrauch prüfen, Bewertung speichern und Restmengen behalten."""
    wb = ressourcen.wissensbasis()
    if "grundstock" in kandidat:
        wb = wb.mit_grundstock(kandidat["grundstock"])
    person = st.session_state.person
    rezept = kandidat["rezept"]
    st.markdown(f"**{rezept['titel']}**")
    st.caption(f"Für {rezept['portionen']} Portionen · {rezept['kochzeit_min']} Minuten")
    with st.expander("Rezeptmengen ansehen"):
        st.write(zutaten_text(rezept))
    st.subheader("1. Verbrauch prüfen")

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
    st.subheader("2. Wie hat es geschmeckt?")
    st.caption("Bewerte das Gericht nach dem Kochen. Deine Rückmeldung wird mit dem Verbrauch gespeichert.")
    sterne = st.feedback("stars", key=f"sterne_{person}_{rezept['id']}")
    if sterne is not None:
        st.caption(f"{sterne + 1} von 5 Sternen")
    if st.button("Speichern", type="primary", disabled=sterne is None or fehlmenge):
        try:
            # Der Dialog kann länger offen sein als die Turso-Verbindung gültig ist.
            with ressourcen.datenbank() as conn:
                koche(conn, person, rezept["id"], sterne + 1, vorrat, verbrauch,
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


def zeige_rezept(kandidat, vorrat, nummer=None):
    wb = ressourcen.wissensbasis()
    person = st.session_state.person
    rezept = kandidat['rezept']
    with st.container(border=True):
        if nummer is not None:
            st.html(f'<p class="nummer">Deine Küchenidee / {nummer:02}</p>')
        st.subheader(rezept['titel'])
        info = f"{rezept['kochzeit_min']} Min. · {rezept['portionen']} Portionen"
        if kandidat['vegetarisch']:
            info += ' · vegetarisch'
        st.html(f'<p class="rezept-meta">{escape(info)}</p>')
        grund = kandidat['begruendungen'][0] if kandidat['begruendungen'] else 'Passt zu deinem Vorrat und Grundstock.'
        st.html(f'<p class="rezept-grund">{escape(grund)}</p>')
        with st.expander('Zutaten & Details', icon=':material/menu_book:'):
            for e in rezept['zutaten']:
                menge = f"{e['menge']:g} {e['einheit']} " if e['menge'] is not None else ''
                optional = ' · optional' if not e['pflicht'] else ''
                st.write(f"{menge}{wb.namen[e['zutat']]}{optional}")
            if kandidat['fehlend_optional']:
                st.caption('Optional ergänzen: ' + ', '.join(kandidat['fehlend_optional']))
            if kandidat['begruendungen']:
                st.markdown('**Warum dieses Gericht?**')
                for begruendung in kandidat['begruendungen']:
                    st.write(begruendung)
            schritte = rezept.get('zubereitung')
            if schritte:
                st.markdown('**Zubereitung**')
                if isinstance(schritte, list):
                    for index, schritt in enumerate(schritte, 1):
                        st.write(f'{index}. {schritt}')
                else:
                    st.write(schritte)
            else:
                st.caption('Eine Schritt-für-Schritt-Zubereitung ist für dieses Gericht noch nicht hinterlegt.')
            st.caption('Zutaten sind vorhanden oder ersetzbar. Die benötigten Mengen prüfst du vor dem Speichern.')
        if st.button('Gekocht', icon=':material/check:', key=f"gekocht_{rezept['id']}",
                     use_container_width=True):
            for key in list(st.session_state):
                if key.startswith(f"verbrauch_{rezept['id']}_") or key == f"sterne_{person}_{rezept['id']}":
                    del st.session_state[key]
            gekocht_dialog(kandidat, vorrat)


def zeige_vorschlaege(vorrat_df, kompakt=False):
    """Heute zeigt drei Ideen; die Rezeptseite bietet Suche, Filter und weitere Treffer."""
    wb = ressourcen.wissensbasis()
    vorrat = vorrat_als_liste(vorrat_df)
    nur_vegetarisch, max_kochzeit, suche = False, 90, ''
    if not kompakt:
        with st.container(border=True):
            suche = st.text_input('Rezept suchen', placeholder='Zum Beispiel Pasta oder Suppe', key='rezept_suche')
            c1, c2 = st.columns(2)
            nur_vegetarisch = c1.toggle('Nur vegetarisch', key='rezept_vegetarisch')
            max_kochzeit = c2.select_slider('Maximale Kochzeit', options=[10, 15, 20, 30, 45, 60, 90],
                                           value=90, format_func=lambda x: f'{x} Min.', key='rezept_zeit')
    kandidaten = [k for k in finde_kandidaten(lade_rezepte(), vorrat, wb)
                  if (k['vegetarisch'] or not nur_vegetarisch)
                  and k['rezept']['kochzeit_min'] <= max_kochzeit
                  and suche.casefold() in k['rezept']['titel'].casefold()]
    modell = ressourcen.ml_modell()
    sortiert = sortiere(kandidaten, modell)
    if not sortiert:
        if vorrat_df.empty:
            leer('Deine nächsten Lieblingsgerichte warten schon.',
                 'Erfasse zuerst ein paar Lebensmittel in deinem Vorrat.')
        else:
            leer('Hier passt gerade noch kein Gericht.',
                 'Ergänze deinen Vorrat oder lockere die Filter. Auf Heute findest du auch Einkaufsideen.')
        return
    if not kompakt:
        st.caption(f'{len(sortiert)} passende Gerichte · ' +
                   ('Nach bisherigen Kochbewertungen sortiert' if modell is not None else 'Nach Resteverwertung sortiert'))
    anzahl = 3 if kompakt else len(sortiert)
    if not kompakt and len(sortiert) > 9:
        if not st.toggle(f'Alle {len(sortiert)} Gerichte anzeigen'):
            anzahl = 9
    with st.container(key='rezeptliste'):
        for start in range(0, min(anzahl, len(sortiert)), 3):
            spalten = st.columns(3, gap='medium')
            for i, kandidat in enumerate(sortiert[start:min(start + 3, anzahl)]):
                with spalten[i]:
                    zeige_rezept(kandidat, vorrat, start + i + 1)
    if kompakt:
        st.page_link('app/vorschlaege.py', label='Alle passenden Rezepte & Filter', icon=':material/arrow_forward:')


def zeige_meldung():
    if "meldung" in st.session_state:
        st.success(st.session_state.pop("meldung"), icon="🎉")
