# Datenmodell

Die Daten liegen an drei Orten, je nach Art:

| Ort | Inhalt | Ändert sich |
|---|---|---|
| `wissensbasis/cooler_ai.ttl` (OWL) | Zutaten, Kategorien, Eigenschaften, Ersatzregeln | selten, per Pull Request |
| `daten/rezepte.json` | Rezepte mit Zutaten | selten, per Pull Request |
| `cooler_ai.db` (SQLite, lokal) | Vorrat, Bewertungen | laufend, wird nicht eingecheckt |

Verbunden sind sie über die **Zutat-ID** (lokaler Name der OWL-Klasse, z.B. `Cherrytomate`) und die **Rezept-ID** (z.B. `spaghetti_carbonara`).

## Ontologie

```mermaid
classDiagram
    Zutat <|-- Gemuese
    Gemuese <|-- Tomate
    Tomate <|-- Cherrytomate
    Zutat <|-- Milchprodukt
    Milchprodukt <|-- Rahm
    Rahm <|-- Vollrahm
    Milchprodukt <|-- CremeFraiche
    class Zutat {
        einheit
        haltbarTage
        haltbarOffenTage
        grundstock
        vegetarisch
    }
    class Ersatzregel {
        original
        ersatz
        begruendung
    }
```

Ausschnitt; vollständig in `wissensbasis/cooler_ai.ttl`, Erklärung in `docs/wissensbasis.md`.

## Rezepte (`daten/rezepte.json`)

```json
{
  "id": "spaghetti_carbonara", "titel": "Spaghetti Carbonara", "kochzeit_min": 20, "portionen": 2,
  "zutaten": [
    {"zutat": "Spaghetti", "menge": 200, "einheit": "g", "pflicht": true},
    {"zutat": "Pfeffer", "menge": null, "einheit": null, "pflicht": true}
  ]
}
```

`zutat` darf auch eine Kategorie sein (`Teigwaren`), dann passt jede Unterart. `vegetarisch` wird nicht eingetragen, sondern aus der Ontologie abgeleitet.

## SQLite

```mermaid
erDiagram
  VORRATSEINTRAG {
    int id PK
    string zutat "ID aus der Ontologie"
    float menge
    string einheit
    date ablaufdatum
    date geoeffnet_am
  }
  BEWERTUNG {
    int id PK
    string rezept_id "ID aus rezepte.json"
    date datum
    int note "1 bis 5"
    string vorrat_snapshot "JSON"
  }
```

## Hinweise

- **Effektives Ablaufdatum** = früheres von Etikett und Öffnungsdatum + `haltbarOffenTage` (`Wissensbasis.effektives_ablaufdatum`).
- **`BEWERTUNG.vorrat_snapshot`** speichert den Vorrat zum Zeitpunkt der Bewertung als JSON (Zutat, Menge, Einheit, Tage bis Ablauf). Ohne ihn lassen sich die Trainingsmerkmale nicht rekonstruieren.
- Wird eine Zutat aus der Ontologie gelöscht, bleiben alte Vorratseinträge mit dieser ID stehen. Zutaten deshalb lieber umbenennen (`rdfs:label`) als die ID ändern.
