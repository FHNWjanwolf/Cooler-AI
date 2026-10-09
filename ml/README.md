# ML

- `ranking.py`: sortiert die geeigneten Rezepte. Regelbasierte Baseline, solange kein Modell trainiert ist, sonst logistische Regression.
- `trainiere.py`: trainiert das Modell aus den Bewertungen und vergleicht es mit der Baseline. Start: `python -m ml.trainiere`

Vorab-Rückmeldungen (Daumen hoch/runter) haben Trainingsgewicht 1,
Bewertungen nach dem Kochen Trainingsgewicht 3. Die bestehende 1–5-Skala
bleibt für Kochbewertungen erhalten; Daumen werden als positive/negative
Labels im bisherigen Schema gespeichert.

Evaluation auf separaten Testbeispielen (zeitlicher Split). Hauptmetrik: Anteil Situationen mit passendem Rezept unter den ersten drei Vorschlägen. Immer Vergleich mit der regelbasierten Baseline.
