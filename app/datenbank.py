"""SQLite-Datenbank für die Nutzerdaten: Vorrat und Bewertungen.

Zwei Varianten, gleiches SQL:
  - Lokal (Entwicklung, Tests): Datei cooler_ai.db mit dem sqlite3-Modul von Python.
  - Test/Prod (Streamlit Cloud): Turso, eine SQLite-Datenbank in der Cloud. Wird benutzt,
    sobald die Umgebungsvariablen TURSO_DATABASE_URL und TURSO_AUTH_TOKEN gesetzt sind
    (in der Streamlit Cloud als Secrets). Details: docs/deployment.md

Das Fachwissen über Zutaten (Kategorien, Haltbarkeit, Ersatzregeln) liegt NICHT hier,
sondern in der Ontologie (wissensbasis/cooler_ai.ttl). In der Datenbank steht nur
die Zutat-ID, z.B. "Cherrytomate".
"""
import json
import os
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

DB_PFAD = Path(__file__).parent.parent / "cooler_ai.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vorratseintrag (
    id INTEGER PRIMARY KEY,
    zutat TEXT NOT NULL,          -- ID aus der Ontologie
    menge REAL,
    einheit TEXT,
    ablaufdatum TEXT,             -- ISO-Datum, z.B. 2026-10-01
    geoeffnet_am TEXT
);
CREATE TABLE IF NOT EXISTS bewertung (
    id INTEGER PRIMARY KEY,
    rezept_id TEXT NOT NULL,
    datum TEXT NOT NULL,
    note INTEGER NOT NULL,        -- 1 (passt gar nicht) bis 5 (passt perfekt)
    vorrat_snapshot TEXT NOT NULL, -- Vorrat zum Zeitpunkt der Bewertung als JSON (Pflicht fürs Training!)
    gekocht INTEGER DEFAULT 0      -- 1 = Rezept wurde wirklich gekocht (stärkeres Signal als nur bewertet)
);
"""


def verbinde(pfad=DB_PFAD):
    url = os.environ.get("TURSO_DATABASE_URL")
    if url:
        import libsql  # nur nötig, wenn Turso benutzt wird

        conn = libsql.connect(url, auth_token=os.environ.get("TURSO_AUTH_TOKEN", ""))
    else:
        conn = sqlite3.connect(pfad, check_same_thread=False)
    conn.executescript(SCHEMA)
    _ergaenze_spalte(conn, "bewertung", "gekocht", "INTEGER DEFAULT 0")
    return conn


def _ergaenze_spalte(conn, tabelle, spalte, typ):
    """Fügt eine Spalte hinzu, falls eine bestehende Datenbank sie noch nicht hat.

    CREATE TABLE IF NOT EXISTS ändert bestehende Tabellen nicht. Ohne diesen Schritt
    fehlte die neue Spalte in Datenbanken, die vor ihrer Einführung angelegt wurden.
    """
    vorhandene = [zeile[1] for zeile in conn.execute(f"PRAGMA table_info({tabelle})").fetchall()]
    if spalte not in vorhandene:
        conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {typ}")
        conn.commit()


def _als_dataframe(conn, sql):
    """Abfrage als DataFrame. (pd.read_sql kennt nur sqlite3, nicht den Turso-Client.)"""
    cursor = conn.execute(sql)
    spalten = [d[0] for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=spalten)


def _iso(d):
    return d.isoformat() if d is not None and pd.notna(d) else None


def _als_datum(text):
    return date.fromisoformat(text) if isinstance(text, str) and text else None  # leer = None oder NaN


# ---------------------------------------------------------------- Vorrat

def lade_vorrat(conn, wb, heute=None):
    """Vorrat als DataFrame, inkl. Tage bis zum effektiven Ablaufdatum, dringendste zuerst."""
    heute = heute or date.today()
    df = _als_dataframe(conn, "SELECT * FROM vorratseintrag")
    df["ablaufdatum"] = [_als_datum(d) for d in df["ablaufdatum"]]
    df["geoeffnet_am"] = [_als_datum(d) for d in df["geoeffnet_am"]]
    df["name"] = [wb.namen.get(z, z) for z in df["zutat"]]
    tage = []
    for r in df.itertuples():
        eff = wb.effektives_ablaufdatum(r.zutat, r.ablaufdatum, r.geoeffnet_am)
        tage.append((eff - heute).days if eff is not None else None)
    df["tage"] = pd.array(tage, dtype="Int64")  # Int64 erlaubt leere Werte
    return df.sort_values("tage", na_position="last").set_index("id")


def vorrat_als_liste(df):
    """Vorrat im Format, das die Wissensbasis und der Snapshot erwarten."""
    return [
        {
            "id": int(r.Index),   # Vorratseintrag, damit er nach dem Kochen entfernt werden kann
            "zutat": r.zutat,
            "menge": None if pd.isna(r.menge) else float(r.menge),
            "einheit": r.einheit,
            "tage": None if pd.isna(r.tage) else int(r.tage),
        }
        for r in df.itertuples()
    ]


def fuege_hinzu(conn, zutat, menge, einheit, ablaufdatum):
    conn.execute(
        "INSERT INTO vorratseintrag (zutat, menge, einheit, ablaufdatum) VALUES (?, ?, ?, ?)",
        (zutat, menge, einheit, _iso(ablaufdatum)),
    )
    conn.commit()


def aktualisiere(conn, eintrag_id, menge, ablaufdatum, geoeffnet_am):
    conn.execute(
        "UPDATE vorratseintrag SET menge = ?, ablaufdatum = ?, geoeffnet_am = ? WHERE id = ?",
        (menge, _iso(ablaufdatum), _iso(geoeffnet_am), eintrag_id),
    )
    conn.commit()


def loesche(conn, eintrag_id):
    conn.execute("DELETE FROM vorratseintrag WHERE id = ?", (eintrag_id,))
    conn.commit()


# ---------------------------------------------------------------- Bewertungen

def speichere_bewertung(conn, rezept_id, note, vorrat_snapshot, gekocht=False):
    conn.execute(
        "INSERT INTO bewertung (rezept_id, datum, note, vorrat_snapshot, gekocht) VALUES (?, ?, ?, ?, ?)",
        (rezept_id, date.today().isoformat(), note, json.dumps(vorrat_snapshot, ensure_ascii=False),
         int(gekocht)),
    )
    conn.commit()


def koche(conn, rezept_id, note, vorrat_snapshot, aufgebraucht_ids):
    """Rezept wurde gekocht: Bewertung speichern und aufgebrauchte Vorratseinträge entfernen.

    Der Snapshot ist der Vorrat VOR dem Kochen, damit das Training die Situation kennt.
    """
    speichere_bewertung(conn, rezept_id, note, vorrat_snapshot, gekocht=True)
    for eintrag_id in aufgebraucht_ids:
        loesche(conn, eintrag_id)


def lade_bewertungen(conn):
    """Alle Bewertungen, älteste zuerst, mit ausgepacktem Snapshot."""
    zeilen = conn.execute(
        "SELECT rezept_id, datum, note, vorrat_snapshot, gekocht FROM bewertung ORDER BY datum, id"
    ).fetchall()
    return [
        {"rezept_id": r, "datum": d, "note": n, "vorrat": json.loads(s), "gekocht": bool(g)}
        for r, d, n, s, g in zeilen
    ]
