# Cooler AI – Kontext für Claude Code

## Sprache und Stil

- Antworten, Kommentare, UI-Texte und Doku auf Hochdeutsch (kein Schweizerdeutsch).
- Kein scharfes ß, immer "ss". Umlaute normal schreiben.
- Knapp und direkt, ehrliche Einschätzungen statt Absicherungen.

## Projekt

Gruppenprojekt (FHNW, Modul Maschinelles Lernen und Wissensverarbeitung), 3 Personen, ca. 12 Wochen.
Kernfrage der App: "Was koche ich heute mit dem, was ich habe und was bald abläuft?"
Fokus Resteverwertung / Food Waste, nicht allgemeine Rezeptinspiration.

Das Modul verlangt beide Teile: ein wissensbasiertes System und eine echte ML-Komponente.
Reine Mengen- oder Regellogik ("Rezepte mit den meisten vorhandenen Zutaten") zählt NICHT als ML.

## Entschieden

- Team: 3 Personen. A = UI und Vorrat (`app/`), B = Wissensbasis und Rezeptdaten (`wissensbasis/`, `daten/`), C = ML und Evaluation (`ml/`).
- Vorrat wird manuell erfasst. Kein Kassenzettel-OCR, keine Kühlschrank-Fotoerkennung.
- Stack: Python, Streamlit, SQLite, scikit-learn. Doku in Markdown.
- Kein Scraping von Betty Bossi, Migusto oder Fooby. Offene Datensätze (z.B. Food.com, RecipeNLG) oder eigene Sammlung.

## Architektur

Vorrat erfassen → SQLite → Wissensbasis (filtert, ersetzt, begründet) → ML-Ranking (sortiert die geeigneten Rezepte) → Top 3 mit Begründung → Bewertung → Trainingsdaten → zurück ins Ranking.

- Wissensbasis entscheidet, OB ein Rezept in Frage kommt (Pflichtzutaten vorhanden oder ersetzbar, Einschränkungen).
- ML entscheidet nur die REIHENFOLGE.
- Details: `docs/architektur.md`, Datenmodell: `docs/datenmodell.md`.

## Wichtige Konzepte der Wissensbasis

- Zutatenhierarchie über selbstreferenzierende Kategorie (Cherrytomate → Tomate → Gemüse).
- Ersatzregeln mit Begründung (Rahm → Crème fraîche), in der App angezeigt.
- Pflicht- vs. optionale Zutaten (`REZEPT_ZUTAT.pflicht`).
- Haltbarkeit: effektives Ablaufdatum = früheres von Etikett und Öffnungsdatum + `haltbar_offen_tage`.
- Grundstock (Salz, Öl, Gewürze) gilt als immer vorhanden und wird nicht erfasst.

## Offene Entscheide (nicht eigenmächtig festlegen, nachfragen)

- Wissensbasis als SQLite-Tabellen oder OWL-Ontologie (owlready2)? Hängt von den Anforderungen der Lehrperson ab.
- Muss ein eigenes Modell trainiert werden oder reicht ein vortrainiertes (z.B. Sentence-Transformers fürs Zutaten-Matching)?
- Mengenabgleich oder nur Vorhandensein prüfen? Falls Mengen: wenige Einheiten (g, ml, Stück).
- Bewertungen pro Person erfassen (Feld `person` in BEWERTUNG)?
- Rolle von Nährwerten (Kalorien/Protein): höchstens einfacher Filter, nicht Kernfunktion.

## Bekannte Risiken

- Zirkularität beim ML: Wenn Trainingsbewertungen nach denselben Kriterien wie die Regeln entstehen, lernt das Modell nur die Regeln nach. Bewertungen sollten echte persönliche Präferenzen abbilden oder aus öffentlichen Daten stammen (Food.com Interactions).
- Zu wenig Trainingsdaten: Datenerhebung früh starten (ab Woche 3–4), nicht erst in der ML-Phase.
- `BEWERTUNG.vorrat_snapshot` (JSON) ist Pflicht, sonst lassen sich Trainingssituationen nicht rekonstruieren.
- Evaluation auf separaten Testbeispielen; Hauptmetrik: passendes Rezept unter den ersten drei. Immer gegen eine regelbasierte Baseline vergleichen.

## Aktueller Stand

- Repo-Grundstruktur, README, Architektur- und Datenmodell-Doku vorhanden.
- `app/vorrat.py`: Prototyp der Vorratserfassung (Auswahl aus Zutatenliste, Standard-Haltbarkeit, Bearbeiten und Entfernen in der Tabelle, Status nach Dringlichkeit). Entwurf, Datenmodell noch nicht vom Team bestätigt.
- `effektives_ablaufdatum` in `app/vorrat.py` gehört fachlich in `wissensbasis/` und soll dorthin verschoben werden.
- Zutat hat im Prototyp zusätzlich `standard_einheit`, `haltbar_tage`, `grundstock`; Kategorien fehlen dort noch.

## Arbeitsweise

- Pro Aufgabe ein Branch (`feature/...`), Pull Request, Review durch eine andere Person.
- Lokale DB (`cooler_ai.db`) nicht einchecken.
- Code so schreiben, dass die Studierenden ihn nachvollziehen und erklären können: lieber einfach und kommentiert als clever.
