"""DAG gold_daily: builds the gold tables (Postgres schema `gold`) from `violations`.

Chain: resolve_day -> check_sources -> write_gold -> quality_check
Idempotent: a day's gold rows are deleted then rewritten in one transaction.
Violation types are normalised to canonical labels (TYPE_MAP) in the hourly table.
"""
import os
from datetime import timedelta

import pendulum
import psycopg2
from airflow.sdk import dag, get_current_context, task

try:
    from airflow.sdk.exceptions import AirflowFailException, AirflowSkipException
except ImportError:
    from airflow.exceptions import AirflowFailException, AirflowSkipException

DAY_FILTER = "started_at >= %s::date AND started_at < %s::date + 1"

# Raw labels differ between sources (synthetic batch: no_*, model output: NO-*).
# Gold stores ONE canonical label per concept; public.violations keeps the raw one.
TYPE_MAP = {
    "NO-Hardhat": "no_helmet",
    "NO-Safety Vest": "no_vest",
    "NO-Mask": "no_mask",
}
TYPE_CASE = (
    "CASE violation_type "
    + " ".join(f"WHEN '{raw}' THEN '{canon}'" for raw, canon in TYPE_MAP.items())
    + " ELSE violation_type END"
)


def get_conn():
    return psycopg2.connect(
        host=os.environ["SAFESITE_PG_HOST"],
        port=5432,
        dbname=os.environ["SAFESITE_PG_DB"],
        user=os.environ["SAFESITE_PG_USER"],
        password=os.environ["SAFESITE_PG_PASSWORD"],
    )


@dag(
    dag_id="gold_daily",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    params={"day": ""},
    tags=["safesite", "gold"],
)
def gold_daily():
    @task
    def resolve_day() -> str:
        ctx = get_current_context()
        requested = ctx["params"].get("day")
        if requested:
            return requested
        start = ctx.get("data_interval_start")
        if start is not None:
            return start.date().isoformat()
        return (ctx["run_after"].date() - timedelta(days=1)).isoformat()

    @task
    def check_sources(day: str) -> int:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM public.violations WHERE {DAY_FILTER}", (day, day))
                n = cur.fetchone()[0]
        finally:
            conn.close()
        if n == 0:
            raise AirflowSkipException(f"No violations on {day}: nothing to aggregate")
        return n

    @task
    def write_gold(day: str) -> None:
        conn = get_conn()
        try:
            with conn:  # one transaction: commit at the end, rollback on error
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM gold.violations_hourly WHERE hour >= %s::date AND hour < %s::date + 1",
                        (day, day),
                    )
                    cur.execute(
                        f"""
                        INSERT INTO gold.violations_hourly
                            (hour, camera_id, violation_type, violation_count, avg_confidence)
                        SELECT date_trunc('hour', started_at), camera_id, {TYPE_CASE},
                               COUNT(*), AVG(confidence)
                        FROM public.violations
                        WHERE {DAY_FILTER}
                        GROUP BY 1, 2, 3
                        """,
                        (day, day),
                    )
                    cur.execute("DELETE FROM gold.daily_summary WHERE day = %s::date", (day,))
                    cur.execute(
                        f"""
                        INSERT INTO gold.daily_summary
                            (day, camera_id, total_violations, tracked_violations)
                        SELECT %s::date, camera_id, COUNT(*), COUNT(track_id)
                        FROM public.violations
                        WHERE {DAY_FILTER}
                        GROUP BY camera_id
                        """,
                        (day, day, day),
                    )
        finally:
            conn.close()

    @task
    def quality_check(day: str) -> None:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM public.violations WHERE {DAY_FILTER}", (day, day))
                source = cur.fetchone()[0]
                cur.execute(
                    "SELECT COALESCE(SUM(violation_count), 0) FROM gold.violations_hourly "
                    "WHERE hour >= %s::date AND hour < %s::date + 1",
                    (day, day),
                )
                hourly = cur.fetchone()[0]
                cur.execute(
                    "SELECT COALESCE(SUM(total_violations), 0) FROM gold.daily_summary WHERE day = %s::date",
                    (day,),
                )
                daily = cur.fetchone()[0]
        finally:
            conn.close()
        if not (source == hourly == daily):
            raise AirflowFailException(
                f"Quality check failed for {day}: source={source}, hourly={hourly}, daily={daily}"
            )
        print(f"Quality check OK for {day}: {source} violations in source, hourly and daily gold")

    day = resolve_day()
    rows = check_sources(day)
    written = write_gold(day)
    checked = quality_check(day)
    rows >> written >> checked


gold_daily()
