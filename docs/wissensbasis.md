# Wissensbasis pflegen

Die Wissensbasis ist eine OWL-Ontologie in `wissensbasis/cooler_ai.ttl` (Turtle-Format).
Sie ist bewusst von Code und Datenbank getrennt: Wer Zutaten oder Ersatzregeln ergänzt, muss keinen Python-Code anfassen.

## Was steht wo?

| Wissen | Ort | Warum dort |
|---|---|---|
| Zutaten, Kategorien, Hierarchie | Ontologie | Fachwissen, gilt für alle Nutzer |
| Haltbarkeit, Einheit, Grundstock, vegetarisch | Ontologie | wird entlang der Hierarchie vererbt |
| Ersatzregeln mit Begründung | Ontologie | Fachwissen |
| Rezepte | `daten/rezepte.json` | viele Einträge, einfache Struktur, leicht zu ergänzen oder zu importieren |
| Vorrat, Bewertungen | SQLite (lokal `cooler_ai.db`, Test/Prod Turso) | Nutzerdaten, ändern sich ständig |

## Modellierung in einem Satz pro Konzept

- **Zutat und Kategorie** sind beide OWL-Klassen. `rdfs:subClassOf` bildet die Hierarchie: `Cherrytomate → Tomate → Gemuese → Zutat`.
- **Konkrete Zutaten** sind Klassen ohne Unterklassen. Nur diese erscheinen in der Auswahl beim Vorrat.
- **Vererbung**: Fehlt bei einer Zutat ein Wert (z.B. `:einheit`), gilt der Wert der nächsten Oberkategorie. Ein eigener Wert überschreibt den geerbten.
- **Hierarchie beim Kochen**: Braucht ein Rezept `Tomate`, passen `Cherrytomate` und `Rispentomate` aus dem Vorrat. Umgekehrt nicht.
- **Ersatzregel**: Individuum der Klasse `:Ersatzregel` mit `:original`, `:ersatz` und `:begruendung`. Die Regel gilt auch für Unterklassen auf beiden Seiten (Regel `Rahm → CremeFraiche` gilt auch, wenn das Rezept `Vollrahm` braucht).
- **Vegetarisch** wird nicht pro Rezept eingetragen, sondern abgeleitet: Ein Rezept ist vegetarisch, wenn keine Zutat unter `Fleisch` oder `Fisch` liegt.
- **Grundstock** (`:grundstock true`): gilt als immer vorhanden, wird nicht erfasst. Steht bei `Oel`, `Gewuerz`, `Backzutat` und wird an alle Unterklassen vererbt.

Die Eigenschaften sind als `owl:AnnotationProperty` angelegt. Dadurch bleibt die Ontologie OWL 2 DL und lässt sich in Protégé ohne Warnungen öffnen.

## Typische Änderungen

### Neue Zutat

```turtle
:Aubergine a owl:Class ; rdfs:subClassOf :Gemuese ; rdfs:label "Auberginen"@de ;
    :haltbarTage 7 .
```

Die Einheit `g` erbt sie von `Gemuese`. Die ID (`Aubergine`) ohne Umlaute und Leerzeichen schreiben, der Anzeigename kommt aus `rdfs:label`.

### Neue Kategorie zwischen bestehenden Zutaten

Z.B. `Blattgemuese` für Spinat einführen: Klasse anlegen, bei `Spinat` die Oberklasse auf `:Blattgemuese` ändern. Rezepte, die `Spinat` verlangen, funktionieren weiter; neue Rezepte können `Blattgemuese` verlangen.

### Neue Ersatzregel

```turtle
:ersatz_zucchetti_aubergine a owl:NamedIndividual , :Ersatzregel ;
    :original :Zucchetti ; :ersatz :Aubergine ;
    :begruendung "Aubergine hat eine ähnliche Konsistenz, etwas länger garen."@de .
```

Die Begründung wird in der App 1:1 angezeigt, also als ganzen Satz formulieren.

### Neues Rezept

In `daten/rezepte.json` einen Eintrag ergänzen. Bei `zutat` eine ID aus der Ontologie verwenden. Man darf auch eine Kategorie angeben (`Teigwaren` statt `Spaghetti`), wenn jede Unterart passt.

## Nach jeder Änderung

```bash
pytest
```

Die Tests in `tests/test_wissensbasis.py` prüfen u.a., ob jede Rezeptzutat in der Ontologie existiert, ob Ersatzregeln auf bekannte Zutaten zeigen und ob jede auswählbare Zutat eine Einheit hat. Ein Tippfehler in einer ID fällt so sofort auf und nicht erst in der App.

## Mit Protégé arbeiten (optional)

[Protégé](https://protege.stanford.edu/) (kostenlos) kann `cooler_ai.ttl` öffnen und die Hierarchie grafisch anzeigen, gut für Präsentation und Bericht.

- Öffnen: *File → Open* und die `.ttl`-Datei wählen.
- Speichern: *File → Save as* → Format **Turtle** wählen, sonst entsteht RDF/XML.
- Achtung: Protégé sortiert die Datei beim Speichern um und entfernt die Kommentare. Im Team entscheiden: entweder immer von Hand im Texteditor pflegen (empfohlen, weil Pull Requests dann gut lesbar sind) oder immer mit Protégé.

## Technik

`wissensbasis/wissen.py` lädt die Datei mit [rdflib](https://rdflib.readthedocs.io/) und liest sie mit drei SPARQL-Abfragen aus (Klassen mit Hierarchie, Eigenschaften, Ersatzregeln). Danach arbeitet die App nur noch mit normalen Python-Dicts. Ein Reasoner (und damit Java) ist nicht nötig; Hierarchie und Vererbung werden in Python ausgewertet und sind dort in wenigen Zeilen nachvollziehbar (`vorfahren`, `eigenschaft`).
