# Künstliche Vorräte

Diese JSON-Dateien sind gespeicherte Testszenarien und keine Haushalts-Grundstöcke.
Jede Datei beschreibt konkrete Zutaten, Mengen, Einheiten und Ablaufdaten sowie
einen festen Stichtag. Optional ist ein Öffnungsdatum enthalten. So ändern sich
Testergebnisse nicht, nur weil das heutige Datum weiterläuft.

Der explizite `grundstock` gehört zum Szenario und bleibt von der persönlichen
Auswahl in der App getrennt. `erwartete_rezepte` enthält exakt die Rezept-IDs,
die mit diesem Vorrat geeignet sein sollen, unabhängig von ihrer Rangfolge.

Prüfen im Projektordner:

```bash
python -m app.testszenarien
pytest
```

Die CLI meldet Abweichungen und endet mit Status 1, falls eine Erwartung nicht
erfüllt ist. Die App-Seite «Testszenarien» zeigt dieselben Daten und bietet einen
JSON-Download. Sie schreibt keine Nutzerbestände oder Trainingsbewertungen.

Für einen weiteren Fall eine JSON-Datei nach dem Muster von `gratin.json`
ergänzen. Zutaten-IDs müssen in der Ontologie vorkommen, Mengen positiv und
konkret sein. Ablaufdatum und Stichtag sind ISO-Daten. Dann bewusst die erwarteten
Rezept-IDs festlegen und die Prüfung starten. Dateien werden automatisch von
der Testsuite und der Prüfseite gefunden.
