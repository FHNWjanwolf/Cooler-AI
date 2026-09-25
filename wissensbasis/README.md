# Wissensbasis

- `cooler_ai.ttl`: OWL-Ontologie mit Zutaten, Kategorien, Haltbarkeiten und Ersatzregeln.
- `wissen.py`: lädt die Ontologie (rdflib + SPARQL) und bietet Hierarchie, Vererbung, Ersatzregeln und effektives Ablaufdatum.
- `eignung.py`: prüft, ob ein Rezept mit dem Vorrat in Frage kommt, und erzeugt Begründungen und ML-Merkmale.

Pflege und Modellierung: siehe [`docs/wissensbasis.md`](../docs/wissensbasis.md).
