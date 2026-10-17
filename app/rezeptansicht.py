"""Seite: Top-3-Rezeptvorschläge mit Begründung und Bewertung.

Ablauf: Vorrat laden -> Wissensbasis filtert geeignete Rezepte -> Ranking sortiert
-> Anzeige mit Begründung -> Bewertung wird mit Vorrat-Snapshot gespeichert (Trainingsdaten).
«Kochen» öffnet Zutaten und Zubereitung. Erst beim Abschluss werden Verbrauch und Bewertung gespeichert.
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


def _kochkey(kandidat):
    return f"kochablauf_{st.session_state.person}_{kandidat['rezept']['id']}"


def zubereitungsschritte(rezept):
    """Importierte Listen und einfache Texte unterstützen, leere Einträge auslassen."""
    schritte = rezept.get('zubereitung') or []
    if isinstance(schritte, str):
        schritte = schritte.splitlines()
    return [s.strip() for s in schritte if isinstance(s, str) and s.strip()]


def _kochphase(flowkey, phase, schritt=0):
    st.session_state[flowkey].update(phase=phase, schritt=schritt)


def _merke_kochwert(flowkey, widgetkey):
    # Separate Entwurfswerte überleben das Entfernen von Widgets beim Zurückgehen.
    st.session_state[flowkey]['werte'][widgetkey] = st.session_state[widgetkey]


@st.dialog('Dein Kochmodus', width='large')
def kochen_dialog(kandidat, vorrat):
    """Zutaten → je ein Zubereitungsschritt → Verbrauch und Bewertung.

    Die ersten beiden Phasen sind reine Vorschau. Keine Datenbankverbindung
    bleibt während der Zubereitung offen. Abbrechen schreibt nichts.
    """
    rezept = kandidat['rezept']
    flowkey = _kochkey(kandidat)
    if flowkey not in st.session_state:
        st.session_state[flowkey] = {'phase': 'zutaten', 'schritt': 0, 'werte': {}}
    zustand = st.session_state[flowkey]
    phase = zustand['phase']
    st.subheader(rezept['titel'])
    st.caption(f"{rezept['portionen']} Portionen · {rezept['kochzeit_min']} Minuten")
    phasen = [('zutaten', '1 Zutaten'), ('zubereitung', '2 Kochen'), ('abschluss', '3 Bewerten')]
    st.html('<div class="kochphasen">' + ''.join(
        f'<span class="{"aktiv" if name == phase else ""}">{label}</span>'
        for name, label in phasen) + '</div>')
    wb = ressourcen.wissensbasis()
    if 'grundstock' in kandidat:
        wb = wb.mit_grundstock(kandidat['grundstock'])
    if phase == 'zutaten':
        st.write('Lege dir diese Zutaten bereit.')
        for z in rezept['zutaten']:
            menge = f"{z['menge']:g} {z['einheit']} " if z['menge'] is not None else ''
            zusatz = ' · optional' if not z['pflicht'] else ''
            if wb.ist_grundstock(z['zutat']):
                zusatz += ' · Grundstock'
            st.write(f"{menge}{wb.namen[z['zutat']]}{zusatz}")
        if kandidat['fehlend_optional']:
            st.caption('Optional nicht vorhanden: ' + ', '.join(kandidat['fehlend_optional']))
        for begruendung in kandidat['begruendungen']:
            if 'statt' in begruendung:
                st.info(begruendung)
        plan = verbrauchsplan(rezept, vorrat, wb)
        for artikel in vorrat:
            bedarf = plan.get(artikel['id'])
            if bedarf is not None and artikel.get('menge') is not None and bedarf > artikel['menge']:
                st.warning(f"{wb.namen.get(artikel['zutat'], artikel['zutat'])}: "
                           f"benötigt {bedarf:g} {artikel['einheit']}, erfasst {artikel['menge']:g}. "
                           'Prüfe die verfügbare Menge vor dem Kochen.')
        if any(a.get('tage') is not None and a['tage'] < 0 for a in kandidat['verwendet']):
            st.warning('Mindestens eine verwendete Zutat hat ihr eingetragenes Ablaufdatum überschritten. '
                       'Prüfe sie vor dem Verwenden; ein Vorschlag bestätigt keine Geniessbarkeit.')
        st.button('Mit dem Kochen beginnen', type='primary', on_click=_kochphase,
                  args=(flowkey, 'zubereitung'))
    elif phase == 'zubereitung':
        schritte = zubereitungsschritte(rezept)
        if schritte:
            index = min(zustand['schritt'], len(schritte) - 1)
            st.caption(f'Schritt {index + 1} von {len(schritte)}')
            st.progress((index + 1) / len(schritte))
            st.html(f'<div class="kochschritt">{escape(schritte[index])}</div>')
            with st.expander('Zutaten nachsehen'):
                st.write(zutaten_text(rezept))
            if index > 0:
                st.button('Zurück', on_click=_kochphase, args=(flowkey, 'zubereitung', index - 1))
            else:
                st.button('Zur Zutatenliste', on_click=_kochphase, args=(flowkey, 'zutaten'))
            if index < len(schritte) - 1:
                st.button('Nächster Schritt', type='primary', on_click=_kochphase,
                          args=(flowkey, 'zubereitung', index + 1))
            else:
                st.button('Fertig gekocht', type='primary', on_click=_kochphase,
                          args=(flowkey, 'abschluss'))
        else:
            st.info('Für dieses Gericht ist noch keine Zubereitungsanleitung hinterlegt. '
                    'Du kannst die Zutatenliste nutzen und nach dem Kochen deinen Verbrauch speichern.')
            st.button('Zur Zutatenliste', on_click=_kochphase, args=(flowkey, 'zutaten'))
            st.button('Fertig gekocht', type='primary', on_click=_kochphase, args=(flowkey, 'abschluss'))
    else:
        schritte = zubereitungsschritte(rezept)
        st.button('Zur Zubereitung', on_click=_kochphase,
                  args=(flowkey, 'zubereitung', max(0, len(schritte) - 1)))
        _zeige_abschluss(kandidat, vorrat, flowkey)


def _zeige_abschluss(kandidat, vorrat, flowkey):
    """Verbrauch prüfen, Bewertung speichern und Restmengen behalten."""
    wb = ressourcen.wissensbasis()
    if "grundstock" in kandidat:
        wb = wb.mit_grundstock(kandidat["grundstock"])
    person = st.session_state.person
    rezept = kandidat["rezept"]
    with st.expander("Rezeptmengen ansehen"):
        st.write(zutaten_text(rezept))
    st.subheader("Verbrauch prüfen")
    entwurf = st.session_state[flowkey]["werte"]

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
                    value=entwurf.get(key, float(vorschlag) if vorschlag is not None else None), key=key,
                    on_change=_merke_kochwert, args=(flowkey, key),
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
                                value=entwurf.get(key, float(vorschlag) if vorschlag is not None else None), key=key,
                                on_change=_merke_kochwert, args=(flowkey, key))
                st.caption(f"{name}: Vorratsmenge unbekannt; auch die Restmenge bleibt unbekannt. "
                           "Für einen berechneten Restbestand zuerst die Menge unter «Vorrat» erfassen.")
                if st.checkbox(f"{name} vollständig aufgebraucht",
                               value=entwurf.get(key + "_aufgebraucht", False), key=key + "_aufgebraucht",
                               on_change=_merke_kochwert, args=(flowkey, key + "_aufgebraucht")):
                    verbrauch[artikel["id"]] = None
    else:
        st.write("Das Rezept braucht nur Zutaten aus dem Grundstock.")

    st.caption("Bei Ersatzprodukten ist die Rezeptmenge ein Vorschlag; prüfe den tatsächlichen Verbrauch.")
    st.subheader("Wie hat es geschmeckt?")
    st.caption("Bewerte das Gericht nach dem Kochen. Deine Rückmeldung wird mit dem Verbrauch gespeichert.")
    sternkey = f"sterne_{person}_{rezept['id']}"
    if sternkey not in st.session_state and sternkey in entwurf:
        st.session_state[sternkey] = entwurf[sternkey]
    sterne = st.feedback('stars', key=sternkey, on_change=_merke_kochwert, args=(flowkey, sternkey))
    if sterne is not None:
        st.caption(f"{sterne + 1} von 5 Sternen")
    if st.button("Bewertung & Verbrauch speichern", type="primary", disabled=sterne is None or fehlmenge):
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
        st.session_state.meldung = meldung
        st.session_state.pop(flowkey, None)
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
        if st.button('Kochen', icon=':material/skillet:', key=f"gekocht_{rezept['id']}",
                     use_container_width=True):
            for key in list(st.session_state):
                if key.startswith(f"verbrauch_{rezept['id']}_") or key == f"sterne_{person}_{rezept['id']}":
                    del st.session_state[key]
            st.session_state[_kochkey(kandidat)] = {'phase': 'zutaten', 'schritt': 0, 'werte': {}}
            kochen_dialog(kandidat, vorrat)


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
