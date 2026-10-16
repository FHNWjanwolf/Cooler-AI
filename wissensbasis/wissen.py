"""Zugriff auf die Wissensbasis (OWL-Ontologie in cooler_ai.ttl).

Die Ontologie wird einmal mit rdflib geladen und per SPARQL in einfache
Python-Dictionaries übersetzt. Danach arbeitet der Rest der App nur noch mit
diesen Methoden und muss nichts über RDF oder OWL wissen.

Zutaten werden überall mit ihrer ID angesprochen, z.B. "Cherrytomate"
(= lokaler Name der OWL-Klasse).
"""
from datetime import timedelta
from copy import copy
from functools import cache
from pathlib import Path

from rdflib import Graph
from wissensbasis.grundstock import STANDARD_GRUNDSTOCK

ONTOLOGIE = Path(__file__).with_name("cooler_ai.ttl")
NS = "http://example.org/cooler-ai#"
PREFIXE = f"""
    PREFIX :     <{NS}>
    PREFIX owl:  <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def _sortierschluessel(text):
    """Damit "Äpfel" bei A einsortiert wird und nicht am Ende."""
    return text.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u")


def _id(uri):
    """http://example.org/cooler-ai#Cherrytomate -> Cherrytomate"""
    return str(uri).removeprefix(NS)


class Wissensbasis:
    def __init__(self, pfad=ONTOLOGIE):
        g = Graph()
        g.parse(pfad, format="turtle")

        # 1) Alle Zutaten/Kategorien mit Namen und direkten Oberklassen.
        #    rdfs:subClassOf* heisst: beliebig viele Stufen unter :Zutat.
        self.namen = {}   # id -> Anzeigename
        self.eltern = {}  # id -> Liste direkter Oberklassen
        for zeile in g.query(PREFIXE + """
            SELECT ?klasse ?name ?oberklasse WHERE {
                ?klasse rdfs:subClassOf* :Zutat ;
                        rdfs:label ?name .
                OPTIONAL { ?klasse rdfs:subClassOf ?oberklasse }
            }"""):
            k = _id(zeile.klasse)
            self.namen[k] = str(zeile.name)
            self.eltern.setdefault(k, [])
            if zeile.oberklasse is not None:
                self.eltern[k].append(_id(zeile.oberklasse))

        # 2) Direkt eingetragene Eigenschaften (ohne Vererbung).
        self._werte = {}  # (id, eigenschaft) -> Wert
        for zeile in g.query(PREFIXE + """
            SELECT ?klasse ?eigenschaft ?wert WHERE {
                ?klasse ?eigenschaft ?wert .
                FILTER (?eigenschaft IN (:einheit, :haltbarTage, :haltbarOffenTage,
                                         :vegetarisch))
            }"""):
            self._werte[(_id(zeile.klasse), _id(zeile.eigenschaft))] = zeile.wert.toPython()

        # 3) Ersatzregeln
        self.ersatzregeln = [
            {"original": _id(z.original), "ersatz": _id(z.ersatz), "begruendung": str(z.begruendung)}
            for z in g.query(PREFIXE + """
                SELECT ?original ?ersatz ?begruendung WHERE {
                    ?regel a :Ersatzregel ;
                           :original ?original ;
                           :ersatz ?ersatz ;
                           :begruendung ?begruendung .
                }""")
        ]

        self.grundstock_ids = frozenset(STANDARD_GRUNDSTOCK)

    def mit_grundstock(self, zutaten):
        """Eigener Haushaltskontext, ohne die gemeinsam geladene Wissensbasis zu ändern."""
        zutaten = frozenset(zutaten)
        if not zutaten <= set(self.zutaten_zur_auswahl(ohne_grundstock=False)):
            raise ValueError("Der Grundstock darf nur bekannte konkrete Zutaten enthalten.")
        kontext = copy(self)
        kontext.grundstock_ids = zutaten
        return kontext

    # ------------------------------------------------------------ Hierarchie

    def vorfahren(self, zutat):
        """Die Zutat selbst und alle Oberkategorien, von nah nach fern.

        vorfahren("Cherrytomate") -> ["Cherrytomate", "Tomate", "Gemuese", "Zutat"]
        """
        ergebnis = []
        offen = [zutat]
        while offen:
            k = offen.pop(0)
            if k not in ergebnis:
                ergebnis.append(k)
                offen.extend(self.eltern.get(k, []))
        return ergebnis

    def ist_ein(self, zutat, kategorie):
        """True, wenn zutat gleich kategorie ist oder darunter liegt."""
        return kategorie in self.vorfahren(zutat)

    def kategorien(self, zutat):
        """Oberkategorien ohne die Zutat selbst und ohne die Wurzel "Zutat"."""
        return [k for k in self.vorfahren(zutat)[1:] if k != "Zutat"]

    # ------------------------------------------------------------ Eigenschaften

    def eigenschaft(self, zutat, name):
        """Wert einer Eigenschaft. Fehlt er, gilt der Wert der nächsten Oberkategorie."""
        if name == "grundstock":
            return self.ist_grundstock(zutat)
        for k in self.vorfahren(zutat):
            if (k, name) in self._werte:
                return self._werte[(k, name)]
        return None

    def ist_grundstock(self, zutat):
        # Ein explizit vorhandenes Olivenöl erfüllt "Öl", aber kein anderes Öl.
        return any(self.ist_ein(vorhanden, zutat) for vorhanden in self.grundstock_ids)

    def ist_vegetarisch(self, zutat):
        return self.eigenschaft(zutat, "vegetarisch") is not False

    def zutaten_zur_auswahl(self, ohne_grundstock=True):
        """Konkrete Zutaten (Klassen ohne Unterklassen), die man im Vorrat erfassen kann."""
        hat_kinder = {e for liste in self.eltern.values() for e in liste}
        blaetter = [k for k in self.namen if k not in hat_kinder
                    and (not ohne_grundstock or not self.ist_grundstock(k))]
        return sorted(blaetter, key=lambda k: _sortierschluessel(self.namen[k]))

    def grundstock(self):
        namen = [self.namen[k] for k in self.grundstock_ids]
        return sorted(namen, key=_sortierschluessel)

    # ------------------------------------------------------------ Ersatz und Haltbarkeit

    def ersatz_fuer(self, zutat):
        """Ersatzregeln, die für die benötigte Zutat gelten (auch über Oberkategorien)."""
        return [r for r in self.ersatzregeln if self.ist_ein(zutat, r["original"])]

    def effektives_ablaufdatum(self, zutat, ablaufdatum, geoeffnet_am):
        """Früheres von Etikett-Datum und (Öffnungsdatum + Haltbarkeit nach dem Öffnen)."""
        kandidaten = [ablaufdatum] if ablaufdatum is not None else []
        offen_tage = self.eigenschaft(zutat, "haltbarOffenTage")
        if geoeffnet_am is not None and offen_tage is not None:
            kandidaten.append(geoeffnet_am + timedelta(days=offen_tage))
        return min(kandidaten) if kandidaten else None


@cache
def lade_wissensbasis():
    """Lädt die Ontologie nur einmal pro Programmlauf."""
    return Wissensbasis()
