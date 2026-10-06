"""Barrière n°2 : exécution avec le rôle agent_ro (lecture seule, schéma gold, timeout 5 s)."""
import os

import psycopg

MAX_ROWS = 1000


def _conninfo() -> str:
    return (
        f"host={os.environ.get('AGENT_PG_HOST', 'localhost')} "
        f"port={os.environ.get('AGENT_PG_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['AGENT_PG_USER']} "
        f"password={os.environ['AGENT_PG_PASSWORD']} "
        "connect_timeout=5"
    )


def run_query(sql: str):
    """Exécute un SELECT déjà validé. Renvoie (colonnes, lignes)."""
    with psycopg.connect(_conninfo()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [d.name for d in cur.description]
            rows = cur.fetchmany(MAX_ROWS)
    return columns, rows
