"""Page Streamlit : poser une question en langage naturel à l'agent (couche gold, lecture seule)."""
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # racine du dépôt, pour importer `agent`
load_dotenv()

from agent.db import run_query  # noqa: E402
from agent.graph import build_graph  # noqa: E402

st.set_page_config(page_title="Ask the data - SafeSite AI", layout="wide")
st.title("Ask the data")
st.caption("Question en langage naturel -> SQL sur la couche gold (lecture seule) -> réponse. Le SQL utilisé est toujours affiché.")


@st.cache_data(ttl=60)
def get_freshness():
    """Période couverte par le gold, dernier calcul et ancienneté (en heures)."""
    _, r = run_query(
        "SELECT MAX(computed_at), MIN(day), MAX(day), "
        "EXTRACT(EPOCH FROM (NOW()::timestamp - MAX(computed_at))) / 3600 FROM gold.daily_summary"
    )
    return r[0]


computed_at, first_day, last_day, age_h = get_freshness()
if computed_at is None:
    st.warning("La couche gold est vide : l'agent ne pourra rien répondre.")
else:
    st.caption(f"Données gold : du {first_day} au {last_day} · dernier calcul : {computed_at:%Y-%m-%d %H:%M} ({float(age_h):.1f} h)")
    if float(age_h) > 36:
        st.warning("Le gold date de plus de 36 h (le DAG gold_daily tourne chaque nuit) : les réponses peuvent être périmées.")


@st.cache_resource(show_spinner="Connexion à l'agent...")
def get_app():
    return build_graph()


EXAMPLES = [
    "Combien de violations par caméra ?",
    "Quel jour la caméra 1 a-t-elle eu le plus de violations ?",
    "Quel est le type de violation le plus fréquent ?",
    "Combien de violations en septembre 2026 ?",
]

if "history" not in st.session_state:
    st.session_state.history = []

st.sidebar.header("Exemples")
clicked = None
for ex in EXAMPLES:
    if st.sidebar.button(ex, use_container_width=True):
        clicked = ex
if st.sidebar.button("Effacer l'historique", use_container_width=True):
    st.session_state.history = []


def show_chart(columns, rows):
    """Graphique automatique : 2 colonnes (catégorie ou date + nombre), 2 à 60 lignes."""
    if not columns or len(columns) != 2 or not (2 <= len(rows) <= 60):
        return
    labels, values = zip(*rows)
    if not all(isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) for v in values):
        return
    numbers = [float(v) for v in values]
    if all(isinstance(x, (date, datetime)) for x in labels) and len(rows) >= 8:
        st.line_chart(pd.DataFrame({columns[1]: numbers}, index=pd.to_datetime(list(labels))).sort_index())
    else:
        st.bar_chart(pd.DataFrame({columns[1]: numbers}, index=[str(x) for x in labels]))


def render(item):
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        st.write(item["answer"])
        if item.get("rows"):
            st.dataframe(pd.DataFrame(item["rows"], columns=item["columns"]), use_container_width=True, hide_index=True)
            show_chart(item["columns"], item["rows"])
        with st.expander(f"SQL utilisé ({item['attempts']} essai(s), {item['seconds']:.1f}s)"):
            st.code(item.get("sql") or "-", language="sql")


for item in st.session_state.history:
    render(item)

question = st.chat_input("Pose ta question sur les violations...") or clicked
if question:
    t = time.time()
    with st.spinner("L'agent réfléchit..."):
        state = get_app().invoke({"question": question, "attempts": 0})
    item = {
        "question": question,
        "answer": state["answer"],
        "sql": state.get("sql"),
        "columns": state.get("columns"),
        "rows": state.get("rows"),
        "attempts": state["attempts"],
        "seconds": time.time() - t,
    }
    st.session_state.history.append(item)
    render(item)
