"""Cooler AI – Einstiegspunkt der App.

Start (im Hauptordner):  streamlit run cooler_ai.py
"""
import streamlit as st

from app.datenbank import normalisiere_person

st.set_page_config(page_title="Cooler AI", page_icon="🥕")


def anmelden():
    """Name der Person in st.session_state.person, oder Anmeldeformular und Abbruch.

    Kein Passwort: Der Name trennt nur die Daten (jede Person sieht ihren eigenen Vorrat),
    er schützt sie nicht. Der Name steht zusätzlich in der URL (?person=yann),
    damit man die Seite als Lesezeichen speichern kann und nicht jedes Mal neu eingibt.
    """
    if "person" not in st.session_state:
        st.session_state.person = normalisiere_person(st.query_params.get("person", ""))

    if not st.session_state.person:
        st.title("Willkommen bei Cooler AI")
        with st.form("anmelden"):
            name = st.text_input("Dein Name", placeholder="z.B. Yann")
            if st.form_submit_button("Weiter", type="primary") and normalisiere_person(name):
                st.session_state.person = normalisiere_person(name)
                st.rerun()
        st.caption("Jede Person sieht nur ihren eigenen Vorrat. Gib immer denselben Namen ein.")
        st.stop()

    st.query_params["person"] = st.session_state.person
    with st.sidebar:
        st.write(f"Angemeldet als **{st.session_state.person}**")
        if st.button("Abmelden"):
            st.session_state.person = ""
            st.query_params.clear()
            st.rerun()


anmelden()

seiten = st.navigation([
    st.Page("app/vorschlaege.py", title="Was koche ich heute?", icon="🍳", default=True),
    st.Page("app/vorrat.py", title="Vorrat", icon="🥕"),
])
seiten.run()
