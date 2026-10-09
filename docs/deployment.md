# Deployment

## Branches und Umgebungen

```
feature/...  ──PR──▶  dev  ──PR──▶  test  ──PR (manuell)──▶  main
                                     │                        │
                              Testumgebung              Produktion
                         (deployt automatisch)    (deployt automatisch
                                                   nach dem Merge)
```

| Branch | Zweck | Umgebung | Datenbank |
|---|---|---|---|
| `feature/...` | eine Aufgabe, Branch von `dev` | lokal | `cooler_ai.db` (Datei) |
| `dev` | Integration, alles Fertige landet zuerst hier | lokal | `cooler_ai.db` (Datei) |
| `test` | Testumgebung | Streamlit Cloud, App "cooler-ai-test" | Turso `cooler-ai-test` |
| `main` | Produktion, hier werden die echten Bewertungen gesammelt | Streamlit Cloud, App "cooler-ai" | Turso `cooler-ai-prod` |

**Auf die Testumgebung:** Pull Request `dev` → `test` mergen. Die Streamlit Cloud deployt automatisch.

**Auf Prod deployen:** Erst wenn der Stand auf der Testumgebung geprüft wurde: Pull Request `test` → `main` erstellen und mergen. Das Mergen ist der manuelle Schritt. Danach deployt die Streamlit Cloud automatisch.

Bei jedem Pull Request auf `dev`, `test` und `main` läuft `pytest` automatisch (`.github/workflows/tests.yml`). Nur mergen, wenn der Lauf grün ist.

Auf `test` und `main` nie direkt pushen, immer per Pull Request. Auch Änderungen, die direkt in GitHub oder in der Streamlit Cloud entstehen (z.B. Codespaces), gehen zuerst auf `dev`.

## Warum Turso

Die Streamlit Cloud behält keine Dateien: Bei jedem Neustart oder Deploy wäre eine lokale `cooler_ai.db` leer. In Prod sind die Bewertungen aber unsere Trainingsdaten. Turso ist SQLite in der Cloud (gleiches SQL, gleiches Schema), der Gratis-Plan reicht für das Projekt.

`app/datenbank.py` entscheidet selbst:

- `TURSO_DATABASE_URL` gesetzt → Turso (Client `libsql`)
- sonst → lokale Datei `cooler_ai.db` (sqlite3)

Wichtig: Turso beendet eine Verbindung, die ca. 10 Sekunden nicht benutzt wird (Fehler `STREAM_EXPIRED`). Die App öffnet deshalb bei jedem Seitenaufruf eine neue Verbindung (`verbindung()` in `app/ressourcen.py`) und bewahrt sie nicht mit `st.cache_resource` auf.

Das ML-Modell wird aus demselben Grund nicht als Datei gespeichert. Die App trainiert es beim Start und nach jeder neuen Bewertung aus den Bewertungen in der Datenbank (`app/ressourcen.py`).

## Einmalig einrichten

### 1. Turso

1. Konto auf <https://turso.tech> erstellen (Gratis-Plan, Login mit GitHub geht).
2. Zwei Datenbanken anlegen: `cooler-ai-test` und `cooler-ai-prod` (Region möglichst Europa, z.B. Frankfurt).
3. Für jede Datenbank notieren:
   - die URL, z.B. `libsql://cooler-ai-prod-<konto>.turso.io`
   - ein Token ("Create Token", Lesen und Schreiben)

Die Tabellen muss niemand anlegen. Die App erstellt sie beim ersten Start (`CREATE TABLE IF NOT EXISTS`).

Mit der CLI geht es auch:

```bash
turso db create cooler-ai-prod
turso db show cooler-ai-prod --url
turso db tokens create cooler-ai-prod
```

### 2. Streamlit Community Cloud

1. Auf <https://share.streamlit.io> mit GitHub anmelden. Wer das Repo verwaltet, gibt der Streamlit-App Zugriff darauf.
2. App "Test" erstellen: Repository `FHNWjanwolf/Cooler-AI`, Branch `test`, Datei `cooler_ai.py`, URL z.B. `cooler-ai-test`.
3. App "Prod" erstellen: gleich, aber Branch `main`, URL z.B. `cooler-ai`.
4. Bei jeder App unter "Advanced settings" → "Secrets" die passende Datenbank eintragen:

   ```toml
   TURSO_DATABASE_URL = "libsql://cooler-ai-test-<konto>.turso.io"
   TURSO_AUTH_TOKEN = "..."
   ```

   Pro App nur das eigene Paar eintragen: Test-App die Werte von `cooler-ai-test`, Prod-App die von `cooler-ai-prod`. Stehen beide Paare im selben Feld, meldet Streamlit "Invalid format: please enter valid TOML" (doppelte Namen).

   Streamlit stellt Secrets auf oberster Ebene auch als Umgebungsvariablen bereit. Deshalb braucht `app/datenbank.py` kein Streamlit.

### 3. GitHub

Für `test` und `main` eine Regel anlegen (Settings → Rules → Rulesets → New branch ruleset):

- "Restrict deletions" und "Block force pushes"
- "Require a pull request before merging", bei `main` mit mindestens einer Freigabe
- "Require status checks to pass" mit dem Check `pytest`

Für `dev`: Änderungen nur per Pull Request mit Review (gleiche Regel ohne Pflicht-Freigabe genügt).

## Lokal mit einer Cloud-Datenbank arbeiten

Zum Beispiel, um `python -m ml.trainiere` auf den echten Prod-Bewertungen laufen zu lassen:

```bash
export TURSO_DATABASE_URL="libsql://cooler-ai-prod-<konto>.turso.io"
export TURSO_AUTH_TOKEN="..."
python -m ml.trainiere
```

Achtung: `streamlit run cooler_ai.py` mit diesen Variablen schreibt direkt in die Prod-Datenbank. Für die normale Entwicklung die Variablen nicht setzen.

Tokens nie einchecken. `.env` und `.streamlit/secrets.toml` stehen in `.gitignore`.
