# Datenmodell

```mermaid
erDiagram
  KATEGORIE ||--o{ ZUTAT : enthaelt
  KATEGORIE |o--o{ KATEGORIE : "ist Unterkategorie"
  ZUTAT ||--o{ ERSATZREGEL : "wird ersetzt"
  ZUTAT ||--o{ ERSATZREGEL : ersetzt
  REZEPT ||--|{ REZEPT_ZUTAT : "besteht aus"
  ZUTAT ||--o{ REZEPT_ZUTAT : "wird verwendet"
  ZUTAT ||--o{ VORRATSEINTRAG : "liegt im Vorrat"
  REZEPT ||--o{ BEWERTUNG : erhaelt
  KATEGORIE {
    int id PK
    string name
    int oberkategorie_id FK
  }
  ZUTAT {
    int id PK
    string name
    int kategorie_id FK
    string standard_einheit
    int haltbar_tage
    int haltbar_offen_tage
    bool grundstock
  }
  ERSATZREGEL {
    int id PK
    int zutat_id FK
    int ersatz_id FK
    string begruendung
  }
  REZEPT {
    int id PK
    string titel
    int kochzeit_min
    bool vegetarisch
    int portionen
  }
  REZEPT_ZUTAT {
    int rezept_id FK
    int zutat_id FK
    float menge
    string einheit
    bool pflicht
  }
  VORRATSEINTRAG {
    int id PK
    int zutat_id FK
    float menge
    string einheit
    date ablaufdatum
    date geoeffnet_am
  }
  BEWERTUNG {
    int id PK
    int rezept_id FK
    date datum
    string vorrat_snapshot
    int note
  }
```

## Hinweise

- `KATEGORIE` verweist auf sich selbst und bildet so die Hierarchie (Cherrytomate → Tomate → Gemüse).
- `REZEPT_ZUTAT.pflicht` trennt Pflicht- von optionalen Zutaten.
- `BEWERTUNG.vorrat_snapshot` speichert den Vorrat zum Zeitpunkt der Bewertung als JSON. Ohne diesen Snapshot lassen sich die Trainingsdaten nicht rekonstruieren.
