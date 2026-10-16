# ML

- `ranking.py`: sortiert die geeigneten Rezepte. Regelbasierte Baseline, solange kein Modell trainiert ist, sonst logistische Regression.
- `trainiere.py`: trainiert das Modell aus den Bewertungen und vergleicht es mit der Baseline. Start: `python -m ml.trainiere`

Das Modell verwendet ausschliesslich Sternebewertungen nach dem Kochen
(`gekocht = 1`). Frühere Daumen-Rückmeldungen und Bewertungen ohne
Kochbestätigung werden bei Training, Evaluation, zeitlichem Split und
Mindestanzahl vollständig ausgeschlossen. Ab 20 brauchbaren Kochbewertungen
mit positiven und negativen Beispielen wird trainiert; vorher gilt die Baseline.

Evaluation auf separaten Testbeispielen (zeitlicher Split). Hauptmetrik: Anteil Situationen mit passendem Rezept unter den ersten drei Vorschlägen. Immer Vergleich mit der regelbasierten Baseline.
