# Cooler AI

Resteverwertungs-App: Welche Rezepte lassen sich mit dem aktuellen Vorrat kochen, und was muss zuerst weg?
Gruppenprojekt im Modul Maschinelles Lernen und Wissensverarbeitung (FHNW).

## Ablauf

Vorrat erfassen → Wissensbasis filtert geeignete Rezepte → ML-Modell sortiert sie → Top 3 mit Begründung → Bewertung fliesst ins Training zurück.

## Starten

```bash
pip install -r requirements.txt
streamlit run app/vorrat.py
```

## Struktur

| Ordner | Inhalt | Verantwortlich |
|---|---|---|
| `app/` | Streamlit-Oberfläche, Vorratsverwaltung | Person A |
| `wissensbasis/` | Kategorien, Ersatzregeln, Eignungsprüfung | Person B |
| `ml/` | Trainingsdaten, Ranking-Modell, Evaluation | Person C |
| `daten/` | Rezeptdaten und Zutatenliste (Rohdaten) | Person B |
| `docs/` | Architektur, Datenmodell, Entscheide, Testergebnisse | alle |

## Zusammenarbeit

- Aufgaben als GitHub Issues erfassen.
- Pro Aufgabe ein eigener Branch, z.B. `feature/vorrat-bearbeiten`.
- Änderungen per Pull Request, eine andere Person prüft vor dem Zusammenführen.
- Die lokale Datenbank (`cooler_ai.db`) wird nicht eingecheckt.
