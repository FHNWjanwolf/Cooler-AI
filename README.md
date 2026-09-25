# Cooler AI

Resteverwertungs-App: Welche Rezepte lassen sich mit dem aktuellen Vorrat kochen, und was muss zuerst weg?
Gruppenprojekt im Modul Maschinelles Lernen und Wissensverarbeitung (FHNW).

## Ablauf

Vorrat erfassen → Wissensbasis (OWL) filtert geeignete Rezepte → ML-Modell sortiert sie → Top 3 mit Begründung → Bewertung fliesst ins Training zurück.

## Starten

```bash
pip install -r requirements.txt
streamlit run cooler_ai.py      # App
pytest                          # Tests (vor jedem Pull Request)
python -m ml.trainiere          # Modell trainieren + gegen Baseline evaluieren (ab 20 Bewertungen)
```

Alle Befehle im Hauptordner ausführen.

## Struktur

| Ordner / Datei | Inhalt | Verantwortlich |
|---|---|---|
| `cooler_ai.py` | Einstiegspunkt der App | Person A |
| `app/` | Streamlit-Seiten (Vorrat, Vorschläge), Datenbankzugriff | Person A |
| `wissensbasis/` | Ontologie (`cooler_ai.ttl`), Zugriff darauf, Eignungsprüfung | Person B |
| `daten/` | Rezepte (`rezepte.json`) | Person B |
| `ml/` | Ranking, Training, Evaluation | Person C |
| `tests/` | Automatische Tests | alle |
| `docs/` | Architektur, Datenmodell, Pflege der Wissensbasis, Fahrplan | alle |

Einstieg in die Doku: [`docs/architektur.md`](docs/architektur.md), dann [`docs/wissensbasis.md`](docs/wissensbasis.md) und [`docs/fahrplan.md`](docs/fahrplan.md).

## Zusammenarbeit

- Aufgaben als GitHub Issues erfassen.
- Pro Aufgabe ein eigener Branch, z.B. `feature/vorrat-bearbeiten`.
- Änderungen per Pull Request, eine andere Person prüft vor dem Zusammenführen.
- Die lokale Datenbank (`cooler_ai.db`) und das trainierte Modell (`ml/modell.joblib`) werden nicht eingecheckt.
