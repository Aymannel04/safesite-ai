"""Page Streamlit : poser une question en langage naturel à l'agent (couche gold, lecture seule)."""
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # racine du dépôt, pour importer `agent`
load_dotenv()

from agent.graph import build_graph  # noqa: E402

st.set_page_config(page_title="Ask the data - SafeSite AI", layout="wide")
st.title("Ask the data")
st.caption("Question en langage naturel -> SQL sur la couche gold (lecture seule) -> réponse. Le SQL utilisé est toujours affiché.")


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


def render(item):
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        st.write(item["answer"])
        if item.get("rows"):
            st.dataframe(pd.DataFrame(item["rows"], columns=item["columns"]), use_container_width=True, hide_index=True)
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
