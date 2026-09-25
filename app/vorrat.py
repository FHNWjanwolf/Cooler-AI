"""Cooler AI – Vorratserfassung (Prototyp).

Start: streamlit run vorrat.py
"""
import sqlite3
from datetime import date, timedelta

import pandas as pd
import streamlit as st

DB = "cooler_ai.db"

# name, standard_einheit, haltbar_tage (ungeöffnet), haltbar_offen_tage, grundstock
BEISPIEL_ZUTATEN = [
    ("Vollrahm", "ml", 21, 4, 0),
    ("Crème fraîche", "g", 21, 5, 0),
    ("Karotten", "g", 14, None, 0),
    ("Cherrytomaten", "g", 7, None, 0),
    ("Eier", "Stück", 28, None, 0),
    ("Spaghetti", "g", 365, None, 0),
    ("Parmesan", "g", 60, 21, 0),
    ("Olivenöl", "ml", None, None, 1),
    ("Salz", "g", None, None, 1),
]


@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS zutat (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            standard_einheit TEXT NOT NULL,
            haltbar_tage INTEGER,
            haltbar_offen_tage INTEGER,
            grundstock INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS vorratseintrag (
            id INTEGER PRIMARY KEY,
            zutat_id INTEGER NOT NULL REFERENCES zutat(id),
            menge REAL,
            einheit TEXT,
            ablaufdatum TEXT,
            geoeffnet_am TEXT
        );
    """)
    if conn.execute("SELECT COUNT(*) FROM zutat").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO zutat (name, standard_einheit, haltbar_tage, haltbar_offen_tage, grundstock) "
            "VALUES (?, ?, ?, ?, ?)",
            BEISPIEL_ZUTATEN,
        )
        conn.commit()
    return conn


def iso(d):
    return d.isoformat() if d is not None and pd.notna(d) else None


def als_datum(spalte):
    return [d.date() if pd.notna(d) else None for d in pd.to_datetime(spalte)]


def effektives_ablaufdatum(r):
    """Früheres von Ablaufdatum und (Öffnungsdatum + Haltbarkeit nach dem Öffnen)."""
    kandidaten = [r.ablaufdatum] if r.ablaufdatum is not None else []
    if r.geoeffnet_am is not None and pd.notna(r.haltbar_offen_tage):
        kandidaten.append(r.geoeffnet_am + timedelta(days=int(r.haltbar_offen_tage)))
    return min(kandidaten) if kandidaten else None


def status(tage):
    if tage is None:
        return "⚪ ohne Datum"
    if tage < 0:
        return "⚫ abgelaufen"
    if tage <= 1:
        return "🔴 heute verbrauchen"
    if tage <= 3:
        return "🟠 bald"
    return "🟢 ok"


def lade_vorrat(conn):
    df = pd.read_sql(
        """SELECT v.id, z.name AS zutat, v.menge, v.einheit, v.ablaufdatum,
                  v.geoeffnet_am, z.haltbar_offen_tage
           FROM vorratseintrag v JOIN zutat z ON z.id = v.zutat_id""",
        conn,
    )
    df["ablaufdatum"] = als_datum(df["ablaufdatum"])
    df["geoeffnet_am"] = als_datum(df["geoeffnet_am"])
    heute = date.today()
    eff = df.apply(effektives_ablaufdatum, axis=1) if len(df) else []
    df["tage"] = [(e - heute).days if e is not None else None for e in eff]
    df["status"] = [status(t) for t in df["tage"]]
    df["aufgebraucht"] = False
    return df.sort_values("tage", na_position="last").set_index("id")


# ---------------------------------------------------------------- Oberfläche
st.set_page_config(page_title="Cooler AI – Vorrat", page_icon="🥕")
st.title("Vorrat")
conn = get_conn()
zutaten = pd.read_sql("SELECT * FROM zutat ORDER BY name", conn)
auswahl = zutaten[zutaten.grundstock == 0]

with st.form("erfassen", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 1.5, 2])
    name = c1.selectbox("Zutat", auswahl["name"], index=None, placeholder="Tippen zum Suchen")
    menge = c2.number_input("Menge", min_value=0.0, step=50.0, value=None)
    ablauf = c3.date_input("Ablaufdatum", value=None, format="DD.MM.YYYY",
                           help="Leer lassen, um die übliche Haltbarkeit zu übernehmen.")
    if st.form_submit_button("Hinzufügen", type="primary"):
        if name is None:
            st.warning("Wähle zuerst eine Zutat aus.")
        else:
            z = zutaten.set_index("name").loc[name]
            if ablauf is None and pd.notna(z.haltbar_tage):
                ablauf = date.today() + timedelta(days=int(z.haltbar_tage))
            conn.execute(
                "INSERT INTO vorratseintrag (zutat_id, menge, einheit, ablaufdatum) VALUES (?, ?, ?, ?)",
                (int(z.id), menge, z.standard_einheit, iso(ablauf)),
            )
            conn.commit()
            menge_text = f"{menge:g} {z.standard_einheit} " if menge else ""
            st.success(f"{menge_text}{name} hinzugefügt.")

grundstock = ", ".join(zutaten[zutaten.grundstock == 1]["name"])
st.caption(f"Immer vorhanden: {grundstock}")

vorrat = lade_vorrat(conn)
if vorrat.empty:
    st.info("Der Vorrat ist leer. Füge oben deine erste Zutat hinzu.")
else:
    bearbeitet = st.data_editor(
        vorrat,
        hide_index=True,
        column_order=["status", "zutat", "menge", "einheit", "ablaufdatum", "geoeffnet_am", "aufgebraucht"],
        disabled=["status", "zutat", "einheit"],
        column_config={
            "status": "Status",
            "zutat": "Zutat",
            "menge": st.column_config.NumberColumn("Menge", min_value=0),
            "einheit": "Einheit",
            "ablaufdatum": st.column_config.DateColumn("Ablaufdatum", format="DD.MM.YYYY"),
            "geoeffnet_am": st.column_config.DateColumn("Geöffnet am", format="DD.MM.YYYY"),
            "aufgebraucht": st.column_config.CheckboxColumn("Aufgebraucht"),
        },
        key="vorrat_editor",
    )
    if st.button("Änderungen speichern"):
        for vid, r in bearbeitet.iterrows():
            leer = pd.notna(r.menge) and r.menge <= 0
            if r.aufgebraucht or leer:
                conn.execute("DELETE FROM vorratseintrag WHERE id = ?", (int(vid),))
            else:
                conn.execute(
                    "UPDATE vorratseintrag SET menge = ?, ablaufdatum = ?, geoeffnet_am = ? WHERE id = ?",
                    (r.menge if pd.notna(r.menge) else None, iso(r.ablaufdatum), iso(r.geoeffnet_am), int(vid)),
                )
        conn.commit()
        st.rerun()
