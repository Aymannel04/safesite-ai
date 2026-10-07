"""Interface en ligne de commande de l'agent : python -m agent "ta question"  (ou sans argument : mode interactif)."""
import logging
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()  # lit .env : plus besoin de "source .env"
except ImportError:
    pass

from agent.graph import build_graph

logging.getLogger("google_genai").setLevel(logging.ERROR)  # coupe le bruit de l'avertissement AFC


def ask(app, question: str) -> None:
    t = time.time()
    s = app.invoke({"question": question, "attempts": 0})
    print(f"\n SQL     : {s.get('sql', '-')}")
    rows = s.get("rows")
    if rows:
        print(f" Lignes  : {len(rows)} (colonnes : {', '.join(s['columns'])})")
        for r in rows[:10]:
            print("           ", r)
        if len(rows) > 10:
            print(f"            ... {len(rows) - 10} de plus")
    print(f" Réponse : {s['answer']}")
    print(f" ({s['attempts']} essai(s), {time.time() - t:.1f}s)\n")


def main() -> None:
    app = build_graph()
    if len(sys.argv) > 1:
        ask(app, " ".join(sys.argv[1:]))
        return
    print("Agent SafeSite (gold). Question vide ou 'exit' pour quitter.")
    while True:
        try:
            q = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in {"exit", "quit"}:
            break
        ask(app, q)


if __name__ == "__main__":
    main()
