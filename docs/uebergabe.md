# Cooler-AI – Projekt- und Kontextübergabe an Codex Cloud

Stand: 17. Oktober 2026, Zeitzone Europe/Zurich.

Diese Datei übergibt den Kontext des bisherigen Planungs- und Cloud-Einrichtungs-Chats. Sie ist keine vollständige Kopie aller Chats und ersetzt nicht die aktuelle Prüfung des Repositorys. Technische Angaben wurden, soweit unten bezeichnet, am 17. Oktober über den GitHub-Connector geprüft. Aussagen aus Screenshots und Rückmeldungen anderer Cloud-Chats sind entsprechend gekennzeichnet.

## 1. Auftrag und Zusammenarbeit

Jan arbeitet mit zwei weiteren Personen an einem FHNW-Gruppenprojekt im Modul Maschinelles Lernen und Wissensverarbeitung. Die bestätigte Abgabe ist **18. Dezember 2026**. Beide fachlichen Teile – Wissensrepräsentation und echtes Machine Learning – sollen erkennbar sein. Verbindliche Bewertungskriterien und Ergebnisse des Dozentengesprächs liegen in diesem Chat noch nicht vor.

Projektidee: Eine App ersetzt die Bestandskenntnis eines smarten Kühlschranks und schlägt passende Rezepte zur Resteverwertung vor. Leitfrage: **Was koche ich heute mit dem, was vorhanden ist und bald abläuft?** Der Vorrat wird manuell erfasst. Fotoerkennung und Kassenzettel-OCR gehören nach bisherigem Stand nicht zum Kernumfang.

Teamaufteilung aus der Repository-Dokumentation:

- A: App, Oberfläche, Vorrat, Datenbankzugriff.
- B: Wissensbasis, Zutaten, Rezepte.
- C: ML, Training, Evaluation.

Kommunikation auf Hochdeutsch, mit Umlauten und ss statt scharfem S. Knapp und verständlich erklären. Jan bevorzugt konkrete Ausführung und einfache einzelne Schritte bei Oberflächenfragen. Nicht immer neue Bestätigungen für bereits beauftragte, reversible Arbeiten verlangen. Ergebnisse, Grenzen und Blockaden ehrlich benennen. Keine nicht geprüfte Funktionsfähigkeit behaupten.

## 2. Repository und zuletzt geprüfter Stand

Repository: https://github.com/FHNWjanwolf/Cooler-AI

Am 17. Oktober direkt über GitHub geprüft:

- `dev`: `8245d6068633f753ae43bea8ba13f570b101a428`
- `main`: `dcd4ff83bb779b107b40ab2b978f8dbc14fbafc4`
- `test`: `009bb79f930b8b24b56f40cabb12a96b75756c76`
- Keine offenen Pull Requests zum Abfragezeitpunkt.

Die unterschiedlichen Commit-IDs allein bedeuten keine unterschiedlichen Dateiinhalte. Vor Beginn Branch, Dateistand, Arbeitsverzeichnis und neue GitHub-Änderungen prüfen. Ein älterer Checkout in einem anderen Chat ist nicht automatisch aktuell. Vorhandene uncommittete Arbeiten niemals überschreiben.

Wichtige Einstiegsdateien:

- `README.md`, `CLAUDE.md` und gegebenenfalls geltende `AGENTS.md`.
- `docs/architektur.md`, `docs/datenmodell.md`, `docs/wissensbasis.md`, `docs/deployment.md`, `docs/fahrplan.md`.
- `ml/trainiere.py`, `ml/ranking.py`, `app/ressourcen.py`.
- `wissensbasis/cooler_ai.ttl`, `wissensbasis/wissen.py`, `wissensbasis/eignung.py`, `wissensbasis/grundstock.py`.

Dokumentation kann ältere Planungen enthalten. Beispielsweise steht im Fahrplan weiterhin eine umfangreiche eigene Datenerhebung; Jan hat inzwischen erklärt, dass diese zu aufwendig wäre und externe Daten beziehungsweise KI-Unterstützung bevorzugt werden. Technische Änderungen und Empfehlungen aus diesem Dokument nicht ungeprüft als bereits implementiert oder vom Dozenten genehmigt behandeln.

## 3. Architektur und vorhandene Funktionen

Stack: Python, Streamlit, scikit-learn, rdflib/SPARQL, SQLite lokal und Turso für die gehostete App. Die App wird über Streamlit Community Cloud betrieben. Codex Cloud dient der Entwicklung, nicht dem Hosting der Produktions-App.

Fachlicher Ablauf:

**Vorrat + persönlicher Grundstock → Wissensbasis prüft Eignung und Ersetzungen → Baseline oder ML sortiert → Rezeptvorschläge → Kochen, Sterne und Verbrauch → Trainingsdaten.**

Vorhandener Funktionsumfang im zuletzt geprüften Projektstand:

- Einstieg mit Namen, Vorrat und Grundstock pro Person. Das ist eine Datentrennung, keine passwortgeschützte Authentifizierung.
- Startseite mit Vorrat links und Rezept-/Einkaufsvorschlägen rechts.
- Zutaten erfassen, Mengen und Einheiten bearbeiten, Ablaufdatum und Öffnungsdatum verwalten.
- Expliziter, pro Person anpassbarer Grundstock; Standardliste in `wissensbasis/grundstock.py`.
- Standard-Grundstock: Salz, Pfeffer, Currypulver, Bouillon, Olivenöl, Rapsöl, Mehl, Zucker.
- Kein automatisches Vorhandensein jeder neu hinzugefügten Unterklasse einer Gewürzkategorie mehr.
- Geeignete Rezepte mit Begründungen; vegetarischer Filter und maximale Kochzeit.
- Einkaufsideen für Rezepte mit genau einer fehlenden Pflichtzutat; vorgeschlagene Menge, Einheit und Ablaufdatum lassen sich in den eigenen Vorrat übernehmen.
- Kochdialog mit Rezeptmengen, bearbeitbarem Verbrauch, Umrechnung vergleichbarer Einheiten und Verteilung über Packungen. Restmengen bleiben erhalten, Fehlmengen werden angezeigt.
- Sternebewertung nach dem Kochen. Verbrauch und Bewertung werden gemeinsam gespeichert. Historischer Vorrat und Grundstock bleiben als Trainingskontext erhalten.
- Drei getrennte JSON-Testszenarien: Carbonara, Gratin und ohne Grundstock. Fester Stichtag und erwartete Rezept-IDs; keine künstlichen Nutzerbewertungen durch diese Szenarien.

Grenze: Die Rezeptauswahl prüft grundsätzlich das Vorhandensein beziehungsweise die Ersetzbarkeit von Zutaten. Sie garantiert nicht, dass sämtliche benötigten Mengen vorhanden sind. Mengenprüfung und Verbrauch sind im Kochdialog umgesetzt.

## 4. Wissensrepräsentation

Zuletzt geprüft: 18 Rezepte, 68 OWL-Klassen einschliesslich Kategorien und zehn Ersatzregeln. Rezeptdaten wurden seit diesem überprüften Stand nicht ausgebaut; bei Weiterarbeit nochmals zählen.

- Ontologie als Turtle/OWL in `wissensbasis/cooler_ai.ttl`.
- Hierarchie beispielsweise Cherrytomate → Tomate → Gemüse → Zutat.
- Eigenschaften wie Einheit, Haltbarkeit und vegetarische Einordnung.
- Ersatzregeln mit angezeigter Begründung, etwa Crème fraîche statt Rahm.
- Effektives Ablaufdatum ist das frühere aus eingetragenem Datum und Öffnungsdatum plus Haltbarkeit nach Öffnung.
- Rezepte als JSON; Nutzerdaten als SQLite/Turso. Verbindung über stabile Zutaten- und Rezept-IDs.

Präzise beschreiben: rdflib/SPARQL liest die Ontologie; Python verarbeitet die Hierarchie, Eigenschaftsvererbung und Eignungsregeln. Es gibt bisher keinen allgemeinen OWL-Reasoner. Insbesondere Annotationseigenschaften werden durch eigene Anwendungslogik vererbt. Ob dies die Modulanforderungen erfüllt, muss mit dem Dozenten geklärt werden.

Ersatzregeln sollen fachlich und im Rezeptkontext geprüft werden. Eine Regel wie Butter → Öl ist nicht für jede Zubereitung universell korrekt. Auch vegetarische Einordnung bei optionalen Zutaten beziehungsweise Ersetzungen ist ein sinnvoller Prüfpunkt.

## 5. Aktueller ML-Stand – wichtiges Update

Am 17. Oktober wurden `CLAUDE.md`, `ml/trainiere.py` und `app/rezeptansicht.py` auf dem oben genannten `dev` geprüft:

**Nur Bewertungen nach tatsächlichem Kochen werden aktuell fürs Training und die Evaluation verwendet.**

- Vorab-Daumen sind aus der Oberfläche entfernt.
- Historische Einträge mit `gekocht = 0` oder ohne gesetztes `gekocht` werden ignoriert.
- Die frühere Gewichtung Vorab = 1, gekocht = 3 ist nicht mehr der aktuelle Ansatz.
- Mindestens 20 **brauchbare** Kochbewertungen werden für die Modellaktivierung verlangt; Trainingsdaten benötigen beide Labelklassen.
- Positiv = Note mindestens 4.
- Modell: DictVectorizer, StandardScaler und logistische Regression.
- Merkmale: unter anderem Kochzeit, Zutatenkategorien, Dringlichkeit, Abdeckung, Ersetzungen und fehlende optionale Zutaten.
- Modell lernt gemeinsam aus den Bewertungen aller Personen; noch keine echte Personalisierung.
- Ohne Modell wird eine feste regelbasierte Resteverwertungs-Baseline verwendet.
- Modelltraining aus Datenbankbewertungen; bisher keine dauerhaft gespeicherte externe Modellpipeline.
- Evaluation im vorhandenen Skript: zeitlicher 80/20-Split und Top-3-Trefferquote positiv bewerteter Testeinträge. Situationen mit höchstens drei Kandidaten werden gezählt, weil das Ranking dort trivial ist.

Die Mindestzahl 20 ist eine technische Schwelle, kein Nachweis ausreichender Datenqualität. Die Zahl echter Produktionsbewertungen und der tatsächliche ML-Vorteil sind hier nicht verifiziert. Tests mit künstlichen Präferenzen belegen lediglich die Mechanik.

## 6. Gewünschte weitere Richtung für ML und Daten

**Ausdrücklicher Nutzerwunsch:** Die drei Studierenden möchten nicht umfangreich selbst Rezepte bewerten und viele echte Vorräte erheben. Sie möchten KI einsetzen und auf realistischen Daten aufbauen.

Bevorzugte Empfehlung aus diesem Chat, noch nicht vollständig umgesetzt und noch nicht vom Dozenten bestätigt:

1. Öffentlichen Datensatz mit Rezepten und echten menschlichen Bewertungen prüfen, beispielsweise Food.com Recipes/Interactions. Lizenz, Herkunft, verfügbare Felder und Klassenverteilung zuerst prüfen.
2. Einen Pilotimport mit etwa 50–100 Rezepten aufbauen; Umfang danach datengetrieben erhöhen. Die bisherigen Vorschläge von 100–200 Rezepten beziehungsweise 150–300 eigenen Bewertungen waren Planungsgrössen, keine verbindlichen Anforderungen.
3. KI für Übersetzung, Normalisierung und Zuordnung von Zutaten zu Ontologie-IDs verwenden. Zuordnungen in einer wiederverwendbaren Mapping-Tabelle speichern, Unsicherheiten markieren, Stichproben prüfen.
4. Zutatenwissen anhand tatsächlich benötigter Rezeptzutaten erweitern. Nicht zuerst eine riesige beliebige Zutatenliste erzeugen.
5. Künstliche Vorräte als reproduzierbare Testszenarien ausbauen: mehrere mögliche Gerichte, kleine Vorräte, Ersatzfälle, eine fehlende Zutat, verschiedene Ablaufdaten. Die bestehenden drei Szenarien sind die Grundlage.
6. Externe Bewertungen getrennt von App-Kochbewertungen speichern und über stabile Quellen-IDs mit Rezepten verbinden. Bisher gibt es keine fertige externe Importpipeline im geprüften Dateibaum.

### Methodische Grenzen unbedingt erhalten

- Eine echte öffentliche Rezeptbewertung enthält keinen bekannten Vorratssnapshot. Ihr darf kein künstlicher Vorrat angehängt werden mit der Behauptung, dies sei eine echte Situationsbewertung.
- Für den ersten externen ML-Versuch Rezeptmerkmale nutzen und allgemeine positive Bewertung beziehungsweise Beliebtheit vorhersagen. Vorratskontext kommt aus der Wissensbasis; Dringlichkeit bleibt zunächst eine gesonderte Regelkomponente.
- KI-generierte Labels dürfen als synthetisches Experiment dienen, aber keinen Nachweis menschlicher Präferenzen vortäuschen. Ein Modell, das KI-Labels nachahmt, ist entsprechend zu beschreiben.
- Denselben echten Bewertungsdatensatz nicht durch viele synthetische Vorräte scheinbar vervielfachen. Abhängige Wiederholungen gemeinsam behandeln und Herkunft markieren.
- Für die Generalisierung auf unbekannte Rezepte sämtliche Bewertungen eines Rezepts demselben Datensplit zuordnen. Bei situativen Daten alle Bewertungen einer Situation zusammenhalten. Aufgabenziel vor Split und Metrik festlegen.
- Nicht bewertete Rezepte sind nicht automatisch negativ.
- Filter, Kandidatenlisten, Daten-/Ontologieversionen oder verwendete Merkmale für reproduzierbare Vergleiche erhalten. Der bisherige Vorrat-/Grundstock-Snapshot löst noch nicht jede dieser Fragen.

Vorgeschlagener Vergleich: feste Baseline, einfache Beliebtheits-Baseline und ML auf identischen Testfällen. Beliebtheitswerte ausschliesslich aus zulässigen Trainingsdaten ableiten. Kategorien-Merkmale als Ablation entfernen. Rankingmetriken nur bei dafür geeigneten Bewertungsgruppen verwenden. Anzahl Fälle und Unsicherheit nennen. Food-Waste-Wirkung getrennt von Vorliebe untersuchen; potenziell verwertete Zutaten sind kein Beleg tatsächlicher Abfallreduktion.

## 7. Dozentengespräch und offene Entscheidungen

Am 16. Oktober wollte das Team den Stand dem Dozenten zeigen. Ergebnisse dieses Gesprächs wurden hier noch nicht mitgeteilt. Nicht so tun, als sei der vorgeschlagene Datenansatz bereits genehmigt.

Zu klären beziehungsweise nachzutragen:

1. Reicht ein ML-Ranking für allgemeine Rezeptbewertung, oder werden Personalisierung und echter Situationsbezug erwartet?
2. Sind öffentliche menschliche Bewertungen und synthetische Vorräte zulässig? Welche Rolle dürfen KI-generierte Labels haben?
3. Genügt die bestehende Ontologie mit SPARQL/Python-Regeln oder ist ein Reasoner/bestimmtes Regelverfahren gefordert?
4. Erwartete Modelle, Datenmenge, Baselines und Evaluationsmetriken?
5. Gewichtung App, Wissensbasis, ML und Bericht sowie formale Abgabeanforderungen?

Einzige hier hochgeladene Vorlesung: `WissenbasierteSysteme Week 01.pdf`. Der Download scheiterte an der Transfergrenze von 32 MiB; die Datei wurde in diesem Chat nicht gelesen. Ihr Inhalt darf nicht als bekannte Anforderung behandelt werden. Bei Bedarf komprimierte Fassung oder relevante Seiten anfordern.

## 8. Nächste Schritte und Termine

Empfohlene Reihenfolge, abhängig von den Dozentenrückmeldungen:

1. Cloud-Veröffentlichung und Arbeit vom Handy mit der neuen privaten Umgebung abschliessen und testen.
2. Ergebnisse des Dozentengesprächs in der Projektdokumentation festhalten und ML-Aufgabe verbindlich auswählen.
3. Pilotdatensatz beschaffen, Lizenz/Felder prüfen, externes Datenschema und Import entwickeln.
4. Zutaten-Mapping und Ontologie passend erweitern; unabhängig davon einen ersten externen ML-Lauf vorbereiten.
5. Datensatz, Split und Baselines festlegen; anschliessend integrieren und auswerten.

Unverbindliche Meilensteine aus der bisherigen Planung: bis Ende Oktober Import und erster ML-Vergleich; im November Experimente und Auswertung; bis 27. November Funktionen/Varianten einfrieren; bis 4. Dezember vollständiger Berichtsentwurf; Generalprobe um 11. Dezember; Puffer bis Abgabe am 18. Dezember. Keine Behauptung, dass das Team diese Termine bereits zugesagt hat. Bericht und Abbildungen parallel pflegen.

## 9. Cloud-Wechsel: aktueller Stand und Fehlerhistorie

Ziel von Jan: Entwicklung ohne laufenden eigenen PC, steuerbar im Browser und am Handy. GitHub bleibt gemeinsame Quelle; Cloud-Aufgaben besitzen eigene Arbeitsbereiche. Chatverlauf, lokale Dateien und Sidebar-Gruppen werden nicht automatisch in neue Aufgaben übertragen.

Die alte Umgebung hiess Cooler-AI und war als «Von dir geteilt» sichtbar. Bearbeiten war trotz persönlichem Plus-Konto gesperrt mit «Bitte deinen Admin um Bearbeitungsrechte». Ab-/Anmelden half nicht. Zusätzlich scheiterte Shell-Git-Zugriff mit:

```text
fatal: unable to access 'https://github.com/FHNWjanwolf/Cooler-AI.git/':
Failed to connect to proxy port 8080 after 0 ms: Could not connect to server
```

Lesen über den GitHub-Connector funktionierte separat. Der konfigurierte Cloud-Proxy war vorgegeben; keine Umgehung der Proxy-/Netzwerkregeln versuchen. GitHub-Adminrechte beheben die Codex-Umgebungsrechte nicht.

Der von Jan kontaktierte OpenAI-Support empfahl eine **neue persönliche Umgebung mit «Only me / Privat»** und eine frische Aufgabe daraus. Dieser Weg wurde gestartet.

Laut vom Nutzer gezeigtem Einrichtungsbericht der neuen Umgebung:

- Python 3.12 und Abhängigkeiten in `.venv` installiert.
- 90 Tests und alle drei Vorratsszenarien bestanden.
- Streamlit gestartet und geprüft.
- Keine Repository-Dateien verändert.
- Installationsskript und Startanweisungen als Konfigurationsentwurf gespeichert.

Dies sind Rückmeldungen des anderen Cloud-Chats, keine hier neu ausgeführten Tests. Die letzte gezeigte Oberfläche bot noch **«Speichern und veröffentlichen»** an; sie zeigte GitHub-Repository und Internetzugriff mit Paketmanager-Preset. **Der erfolgreiche Abschluss der Veröffentlichung und ein Zugriff vom Handy sind in diesem Chat noch nicht bestätigt.** Nicht erneut pauschal annehmen, die Einrichtung sei vollständig fertig oder weiterhin defekt.

Neue Umgebung weiterhin privat halten. Ein neues Arbeitsgespräch daraus starten, Abhängigkeiten/Git-Zugriff kurz prüfen, denselben Chat am Handy mit identischem Konto öffnen. Git-Schreibzugriff ist separat zu prüfen; öffentliches Lesen beweist keine Push-Berechtigung.

In der neuen Umgebung sind keine zusätzlichen Domains oder Umgebungsvariablen nötig, solange nur lokal entwickelt und getestet wird. Konkrete externe Datenquellen gegebenenfalls gezielt erlauben. Für echte Cloud-App-Tests erforderliche Turso-Zugänge gesondert und sicher konfigurieren; keine Produktionsdaten als Standard-Testziel.

## 10. Entwicklungsregeln und Prüfung

- Ausgangspunkt neuer Features: aktuelles `dev`; eigener Aufgabenbranch; Pull Request auf `dev`.
- Weitergabe über `dev → test → main` nach Projektworkflow. Kein Merge oder Deployment ohne entsprechenden Nutzerauftrag.
- Keine lokalen Datenbanken oder Zugangsdaten committen. Keine Geheimnisse ausgeben oder in diese Übergabe kopieren.
- Lokale beziehungsweise temporäre Datenbanken für Tests verwenden. Produktiv-Turso nicht versehentlich durch Umgebungsvariablen als Testziel nutzen.
- Bestehende Datenmigrationen additiv und rückwärtsverträglich halten; historische Kochbewertungen/Grundstock-Snapshots bewahren.
- Einfacher, nachvollziehbarer Code, den Studierende erklären können.
- Vor PR die passenden Tests durchführen; künstliche Szenarien sind Funktionstests, keine ML-Ergebnisstudie.

Typische Befehle im Repository, mit dem Python der eingerichteten `.venv`:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m app.testszenarien
.venv/bin/python -m streamlit run cooler_ai.py
.venv/bin/python -m ml.trainiere
```

Der letzte Befehl liest die konfigurierte Datenbank. Ohne passende Kochbewertungen wird kein belastbares ML-Ergebnis entstehen. Keine Dummy-Bewertungen in Produktionsdaten einfügen, um die Schwelle zu erreichen.

## 11. Andere Chats und Organisation

Jans bestehende Projektgruppe «Cooler AI» enthält unter anderem PLAN, NEW FEATURE, WV und CHECK CONNECTION. Diese Datei stammt aus dem PLAN-Kontext. Vollständige Inhalte und noch offene Aufträge der anderen Chats sind hier nicht vorhanden.

Um nichts zu erfinden: vorhandene Repo-Dokumentation lesen; Entscheidungen und unerledigte Arbeiten aus den anderen Chats bei Bedarf separat ergänzen lassen. Die alte Projektgruppe nicht löschen. Ein Cloud-Umgebungswechsel organisiert bestehende Chats nicht automatisch um; identische Gruppierung auf Desktop und Handy ist nicht verifiziert.

## 12. Startauftrag für den neuen Cloud-Chat

> Lies diese Übergabe vollständig sowie README.md, CLAUDE.md, geltende AGENTS.md und docs/ im Repository. Prüfe den aktuellen dev-Stand und das saubere Arbeitsverzeichnis, ohne vorhandene Arbeiten zu überschreiben. Prüfe kurz die Cloud-Einsatzbereitschaft mit Git-Lesezugriff und den vorhandenen Tests. Beachte: aktuell nur Kochbewertungen fürs ML, keine Vorab-Daumen. Halte die Ergebnisse des Dozentengesprächs und den externen ML-Datenansatz als noch offen fest, solange keine neueren Belege vorliegen. Fasse danach vorhandene Funktionen, offene Entscheidungen und die nächsten drei konkreten Aufgaben zusammen. Speichere diese Übergabe im Projekt unter docs/uebergabe.md und bereite dafür einen Pull Request auf dev vor; vorher aktuelle Fakten abgleichen. Kein Merge oder Deployment und keine Änderungen an Produktionsdaten. Führe noch keine ungefragten Feature-Umbauten oder Neuausrichtung des ML durch.

Speicherhinweis: Diese Übergabedatei wurde zunächst als eigenständige Datei im bisherigen Chat erstellt. Sie ist dadurch noch nicht in GitHub oder in einer anderen Cloud-Aufgabe gespeichert. Für die Fortsetzung herunterladen und im neuen Chat anhängen; danach wie oben beschrieben ins Repository übernehmen.
