"""Barrière n°1 : valide le SQL produit par le LLM avant toute exécution (analyse syntaxique)."""
import re

import sqlglot
from sqlglot import exp

ALLOWED_SCHEMA = "gold"
ALLOWED_TABLES = {"violations_hourly", "daily_summary"}
MAX_ROWS = 1000

_FORBIDDEN_NAMES = (
    "Insert", "Update", "Delete", "Merge", "Drop", "Create", "Alter", "Command",
    "TruncateTable", "Copy", "Into", "Lock", "Set", "Grant", "Use",
)
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))
FORBIDDEN_FUNC_PREFIXES = ("pg_", "lo_")
FORBIDDEN_FUNCS = {"set_config", "current_setting", "dblink", "dblink_exec"}


class SqlRejected(Exception):
    """Le SQL est refusé ; le message est renvoyé au LLM pour qu'il se corrige."""


def extract_sql(text: str) -> str:
    """Le LLM entoure souvent le SQL de ```sql ... ``` : on garde seulement l'intérieur."""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return (m.group(1) if m else text).strip()


def validate_sql(raw: str) -> str:
    """Renvoie le SQL normalisé (avec LIMIT) ou lève SqlRejected."""
    sql = extract_sql(raw)
    if not sql:
        raise SqlRejected("requête vide")

    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.SqlglotError as e:
        raise SqlRejected(f"SQL illisible : {str(e)[:120]}")

    if len(statements) != 1:
        raise SqlRejected(f"un seul statement autorisé (reçu : {len(statements)})")
    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union)):
        raise SqlRejected("seules les requêtes SELECT sont autorisées")

    bad = tree.find(*FORBIDDEN_NODES)
    if bad is not None:
        raise SqlRejected(f"opération interdite : {type(bad).__name__}")

    cte_names = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        name, schema = t.name.lower(), t.db.lower()
        if not schema and name in cte_names:
            continue  # référence à un WITH défini dans la requête
        if schema != ALLOWED_SCHEMA:
            raise SqlRejected(
                f"table '{schema + '.' if schema else ''}{name}' refusée : "
                f"utilise uniquement {ALLOWED_SCHEMA}.<table> avec {sorted(ALLOWED_TABLES)}"
            )
        if name not in ALLOWED_TABLES:
            raise SqlRejected(f"table 'gold.{name}' inconnue ; tables permises : {sorted(ALLOWED_TABLES)}")

    for f in tree.find_all(exp.Func):
        fname = (f.name if isinstance(f, exp.Anonymous) else f.sql_name()).lower()
        if fname in FORBIDDEN_FUNCS or fname.startswith(FORBIDDEN_FUNC_PREFIXES):
            raise SqlRejected(f"fonction interdite : {fname}")

    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        try:
            if int(limit.expression.name) > MAX_ROWS:
                tree = tree.limit(MAX_ROWS)
        except (ValueError, AttributeError):
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="postgres")
