"""Graphe LangGraph : question -> SQL -> validation -> exécution -> réponse (avec boucle de correction)."""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agent.db import run_query
from agent.llm import get_llm
from agent.sql_guard import SqlRejected, validate_sql

MAX_ATTEMPTS = 3


class State(TypedDict, total=False):
    question: str
    sql: str
    error: str | None
    attempts: int
    columns: list
    rows: list
    answer: str
    refused: str


def load_schema_context() -> str:
    """Schéma autorisé + valeurs réelles lues dans gold (pour que le LLM n'invente rien)."""
    _, r = run_query("SELECT DISTINCT violation_type FROM gold.violations_hourly ORDER BY 1")
    types = [x[0] for x in r]
    _, r = run_query("SELECT MIN(day), MAX(day), ARRAY_AGG(DISTINCT camera_id) FROM gold.daily_summary")
    dmin, dmax, cams = r[0]
    return (
        "Base PostgreSQL. Tables autorisées (toujours préfixées par gold.) :\n"
        "- gold.violations_hourly(hour TIMESTAMP, camera_id INT, violation_type TEXT, "
        "violation_count INT, avg_confidence DOUBLE PRECISION) : violations agrégées par heure, caméra et type.\n"
        "- gold.daily_summary(day DATE, camera_id INT, total_violations INT, tracked_violations INT) : "
        "résumé par jour et par caméra.\n"
        f"Valeurs réelles : violation_type ∈ {types} ; camera_id ∈ {sorted(cams)} ; "
        f"jours de {dmin} à {dmax}."
    )


def build_graph(llm=None):
    llm = llm or get_llm()
    schema = load_schema_context()

    def generate_sql(s: State) -> State:
        prompt = (
            "Tu es un expert SQL PostgreSQL. Réponds UNIQUEMENT par UNE requête SELECT, sans explication.\n"
            "Utilise seulement les tables ci-dessous, toujours avec le préfixe gold.\n"
            "Si la question ne peut PAS être répondue avec ces tables (sujet sans rapport, ou demande de "
            "modifier/supprimer des données), réponds exactement : IMPOSSIBLE: <raison courte, dans la langue de la question>. "
            "N'invente jamais de valeur.\n\n"
            f"{schema}\n\nQuestion : {s['question']}\n"
        )
        if s.get("error"):
            prompt += (
                f"\nTa tentative précédente a été refusée.\nSQL précédent :\n{s.get('sql')}\n"
                f"Erreur : {s['error']}\nCorrige-la.\n"
            )
        return {"sql": llm.invoke(prompt), "attempts": s.get("attempts", 0) + 1}

    def validate(s: State) -> State:
        if s["sql"].strip().strip("`").strip().upper().startswith("IMPOSSIBLE"):
            return {"refused": s["sql"].strip().strip("`").strip(), "error": None}
        try:
            return {"sql": validate_sql(s["sql"]), "error": None}
        except SqlRejected as e:
            return {"error": f"validation : {e}"}

    def execute(s: State) -> State:
        try:
            cols, rows = run_query(s["sql"])
            return {"columns": cols, "rows": rows, "error": None}
        except Exception as e:  # noqa: BLE001
            return {"error": f"base de données : {str(e).splitlines()[0][:150]}"}

    def answer(s: State) -> State:
        shown = [dict(zip(s["columns"], r)) for r in s["rows"][:50]]
        prompt = (
            "Réponds à la question en 1 ou 2 phrases, dans la langue de la question, "
            "en te basant UNIQUEMENT sur ces résultats, avec les chiffres exacts. "
            "Si le résultat est vide, dis-le.\n"
            f"Question : {s['question']}\nRésultats ({len(s['rows'])} lignes) : {shown}"
        )
        return {"answer": llm.invoke(prompt)}

    def refuse(s: State) -> State:
        reason = s["refused"].split(":", 1)[-1].strip()
        return {"answer": f"Je ne peux pas répondre avec les données gold : {reason}"}

    def give_up(s: State) -> State:
        return {"answer": f"Je n'ai pas pu produire une requête valide après {s['attempts']} essais. Dernière erreur : {s['error']}"}

    def after_check(ok_target: str):
        def route(s: State) -> str:
            if s.get("refused"):
                return "refuse"
            if not s.get("error"):
                return ok_target
            return "retry" if s["attempts"] < MAX_ATTEMPTS else "give_up"
        return route

    g = StateGraph(State)
    for name, fn in [("generate_sql", generate_sql), ("validate", validate), ("execute", execute),
                     ("answer", answer), ("give_up", give_up), ("refuse", refuse)]:
        g.add_node(name, fn)
    g.add_edge(START, "generate_sql")
    g.add_edge("generate_sql", "validate")
    g.add_conditional_edges("validate", after_check("execute"),
                            {"execute": "execute", "retry": "generate_sql", "give_up": "give_up", "refuse": "refuse"})
    g.add_conditional_edges("execute", after_check("answer"),
                            {"answer": "answer", "retry": "generate_sql", "give_up": "give_up"})
    g.add_edge("answer", END)
    g.add_edge("give_up", END)
    g.add_edge("refuse", END)
    return g.compile()
