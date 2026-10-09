# Fahrplan: Was noch fehlt

Stand: Das Grundgerüst läuft durchgehend (Vorrat → Wissensbasis → Ranking → Top 3 → Bewertung → Training). Alles Folgende baut darauf auf.

## Sofort klären (Woche 1–2)

- [ ] **Lehrperson fragen**: Ist OWL als Wissensbasis in Ordnung bzw. erwünscht? Reicht eine logistische Regression als ML-Komponente, wenn sie gegen eine Baseline evaluiert wird?
- [ ] **Datenmodell im Team bestätigen** (`docs/datenmodell.md`), besonders: Rezepte als JSON, nur Vorhandensein statt Mengen.
- [x] Bewertungen pro Person speichern (Feld `person`): ja, eingebaut. Anmeldung nur mit Namen, jede Person sieht ihren eigenen Vorrat.

## Person B – Wissensbasis und Rezepte

- [ ] Rezeptsammlung auf **mindestens 60–100 Rezepte** ausbauen (aktuell 18). Ohne genug Rezepte hat das Ranking wenig zu sortieren. Quelle pro Rezept in `daten/README.md` dokumentieren.
- [ ] Ontologie entsprechend erweitern (Zutaten, Kategorien, 20–30 Ersatzregeln mit guter Begründung).
- [ ] Prüfen, welche Zutaten wirklich im Vorrat landen, und die Haltbarkeiten realistisch setzen.
- [ ] Optional: Hierarchie für den Bericht in Protégé visualisieren.

## Person A – App

- [ ] Mit echten Vorräten testen und Stolpersteine beheben (z.B. Menge beim Erfassen, schnelles Mehrfach-Erfassen).
- [ ] Knopf "Gekocht" bei einem Rezept: verbrauchte Zutaten aus dem Vorrat entfernen.
- [ ] Anzeige, wie viele Bewertungen schon gesammelt sind (motiviert zur Datenerhebung).

## Person C – ML und Evaluation

- [ ] **Datenerhebung ab Woche 3–4 starten**: alle drei bewerten regelmässig Vorschläge mit ihrem echten Vorrat. Ziel: 150+ Bewertungen bis zur ML-Phase. Auch die "weiteren Rezepte" bewerten, nicht nur die Top 3 (sonst lernt das Modell nur von dem, was die Baseline zeigt).
- [ ] Ehrlich festhalten, nach welchen Kriterien bewertet wurde (persönliche Vorliebe, nicht "hat am meisten Zutaten"), sonst lernt das Modell nur die Regeln nach (Zirkularität).
- [ ] Optional mehr Daten: Food.com Interactions (Kaggle) als zusätzliche Präferenzdaten prüfen. Aufwand: Zutaten auf die Ontologie-IDs abbilden.
- [ ] Evaluation ausbauen: mehrere Splits, Vergleich mehrerer Modelle (z.B. Random Forest), Einfluss der Kategorie-Merkmale.
- [ ] Ergebnisse in `docs/` festhalten (Tabelle Baseline vs. ML).

## Für den Bericht

- Warum Wissensbasis und ML getrennt sind (OB vs. REIHENFOLGE).
- Welche Schlüsse die Wissensbasis zieht: Hierarchie, Vererbung von Eigenschaften, Ersatzregeln, abgeleitetes "vegetarisch".
- Evaluation mit Baseline-Vergleich und Grenzen (wenig Daten, wenige Personen, Position-Bias).
