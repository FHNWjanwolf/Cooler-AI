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
- Stack: Python, Streamlit, SQLite (lokal Datei, Test/Prod über Turso), scikit-learn, rdflib. Doku in Markdown.
- Deployment: Streamlit Community Cloud. `test` = Testumgebung, `main` = Produktion. Branches: `feature/...` → `dev` → `test` → `main`, jeweils per Pull Request (`test` → `main` erst nach Prüfung auf der Testumgebung). Details: `docs/deployment.md`.
- ML-Modell wird nicht als Datei gespeichert, sondern beim App-Start aus den Bewertungen trainiert.
- Wissensbasis als OWL-Ontologie (`wissensbasis/cooler_ai.ttl`, Turtle, rdflib + SPARQL, kein Reasoner). Getrennt von Code und Nutzerdaten. Noch von der Lehrperson zu bestätigen.
- Rezepte in `daten/rezepte.json`, Vorrat und Bewertungen in SQLite bzw. Turso. Verknüpfung über Zutat-ID (lokaler Name der OWL-Klasse).
- Vorerst nur Vorhandensein prüfen, keine Mengen.
- Kein Scraping von Betty Bossi, Migusto oder Fooby. Offene Datensätze (z.B. Food.com, RecipeNLG) oder eigene Sammlung.

## Architektur

Vorrat erfassen → SQLite → Wissensbasis (filtert, ersetzt, begründet) → ML-Ranking (sortiert die geeigneten Rezepte) → Top 3 mit Begründung → Bewertung → Trainingsdaten → zurück ins Ranking.

- Wissensbasis entscheidet, OB ein Rezept in Frage kommt (Pflichtzutaten vorhanden oder ersetzbar, Einschränkungen).
- ML entscheidet nur die REIHENFOLGE.
- Details: `docs/architektur.md`, Datenmodell: `docs/datenmodell.md`, Pflege der Ontologie: `docs/wissensbasis.md`, offene Aufgaben: `docs/fahrplan.md`.

## Wichtige Konzepte der Wissensbasis

- Zutatenhierarchie über `rdfs:subClassOf` (Cherrytomate → Tomate → Gemüse). Eigenschaften (Einheit, Haltbarkeit, Grundstock, vegetarisch) werden entlang der Hierarchie vererbt.
- Ersatzregeln mit Begründung (Rahm → Crème fraîche), in der App angezeigt.
- Pflicht- vs. optionale Zutaten (Feld `pflicht` in `daten/rezepte.json`).
- Haltbarkeit: effektives Ablaufdatum = früheres von Etikett und Öffnungsdatum + `haltbarOffenTage`.
- Grundstock (Salz, Öl, Gewürze) gilt als immer vorhanden und wird nicht erfasst.

## Offene Entscheide (nicht eigenmächtig festlegen, nachfragen)

- Muss ein eigenes Modell trainiert werden oder reicht ein vortrainiertes (z.B. Sentence-Transformers fürs Zutaten-Matching)?
- Bewertungen pro Person erfassen (Feld `person` in BEWERTUNG)?
- Rolle von Nährwerten (Kalorien/Protein): höchstens einfacher Filter, nicht Kernfunktion.

## Bekannte Risiken

- Zirkularität beim ML: Wenn Trainingsbewertungen nach denselben Kriterien wie die Regeln entstehen, lernt das Modell nur die Regeln nach. Bewertungen sollten echte persönliche Präferenzen abbilden oder aus öffentlichen Daten stammen (Food.com Interactions).
- Zu wenig Trainingsdaten: Datenerhebung früh starten (ab Woche 3–4), nicht erst in der ML-Phase.
- `BEWERTUNG.vorrat_snapshot` (JSON) ist Pflicht, sonst lassen sich Trainingssituationen nicht rekonstruieren.
- Evaluation auf separaten Testbeispielen; Hauptmetrik: passendes Rezept unter den ersten drei. Immer gegen eine regelbasierte Baseline vergleichen.

## Aktueller Stand

- Grundgerüst läuft durchgehend: `streamlit run cooler_ai.py` (Seiten Vorrat und Vorschläge), `pytest`, `python -m ml.trainiere`.
- Ontologie mit ca. 65 Klassen und 10 Ersatzregeln, 18 selbst geschriebene Rezepte.
- Ranking: regelbasierte Baseline, logistische Regression ab 20 Bewertungen (beim App-Start trainiert).
- "Gekocht"-Dialog baut den Vorrat ab und speichert eine Bewertung mit `gekocht = 1`. Einkaufsideen auf der Vorratsseite (Rezepte mit genau einer fehlenden Pflichtzutat, nach ML-Vorliebe gewichtet).
- Offene Aufgaben pro Person: `docs/fahrplan.md`.

## Arbeitsweise

- Pro Aufgabe ein Branch (`feature/...`) von `dev`, Pull Request auf `dev`, Review durch eine andere Person. Vor dem Pull Request `pytest` laufen lassen.
- Lokale DB (`cooler_ai.db`) und Secrets (`.streamlit/secrets.toml`) nicht einchecken.
- Code so schreiben, dass die Studierenden ihn nachvollziehen und erklären können: lieber einfach und kommentiert als clever.
