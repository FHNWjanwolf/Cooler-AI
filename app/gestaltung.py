"""Gemeinsame Darstellung. Dynamische Inhalte werden vor HTML-Ausgabe escaped."""
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

EINHEITEN = ['g', 'kg', 'ml', 'l', 'Stück', 'Stk']


def lade_design():
    css = Path(__file__).with_name('design.css').read_text(encoding='utf-8')
    sterne = Path(__file__).with_name('sterne.css').read_text(encoding='utf-8')
    st.html(f'<style>{css}\n{sterne}</style>')


def kopf(kategorie, titel, beschreibung=''):
    st.html(f'<p class="augenbraue">{escape(kategorie)}</p>')
    st.title(titel)
    if beschreibung:
        st.write(beschreibung)


def menge_text(menge, einheit):
    return f'{menge:g} {einheit or ""}'.strip() if pd.notna(menge) else 'Menge offen'


def ablauf_status(tage):
    """Ablaufzustand immer auch als Text; keine alleinige Farbcodierung."""
    if pd.isna(tage):
        return 'neutral', 'Ohne Datum'
    if tage < 0:
        return 'pruefen', f'Seit {abs(tage)} Tag' + ('en' if tage != -1 else '') + ' abgelaufen · prüfen'
    if tage == 0:
        return 'dringend', 'Heute verbrauchen'
    if tage == 1:
        return 'dringend', 'Morgen fällig'
    if tage <= 3:
        return 'bald', f'In {tage} Tagen fällig'
    return 'neutral', f'Noch {tage} Tage'


def vorrat_zeile(name, menge, einheit, tage):
    stil, status = ablauf_status(tage)
    st.html(f'<div class="vorrat-zeile"><div><strong>{escape(name)}</strong>'
            f'<span class="menge">{escape(menge_text(menge, einheit))}</span></div>'
            f'<span class="status {stil}">{escape(status)}</span></div>')


def leer(titel, text):
    st.html(f'<div class="leer"><strong>{escape(titel)}</strong><p>{escape(text)}</p></div>')


def markenleiste():
    st.html('<div class="markenleiste"><div class="wortmarke">'
            '<span class="markenzeichen" aria-hidden="true"><span></span></span>'
            '<span>Cooler <span class="marken-ai">AI</span></span></div>'
            '<span>Gut essen. Weniger verschwenden.</span></div>')


def illustration():
    """Eigene kleine Vektorzeichnung, keine fremden Rezeptfotos oder Netzabrufe."""
    with st.container(key='kuechenbild'):
        st.image(str(Path(__file__).parent / 'assets' / 'kueche.svg'), width='stretch')
