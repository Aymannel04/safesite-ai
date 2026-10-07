"""
Streamlit dashboard for SafeSite AI.

- Aggregates (KPIs, charts) come from the GOLD layer (Postgres schema `gold`, built nightly by the
  Airflow DAG gold_daily): one canonical label per violation type, same numbers as the SQL agent.
- The "Recent violations" table and the evidence viewer need event-level detail (track, confidence,
  evidence image) that gold no longer has, so they read the raw table `public.violations`.
- Data drift reads the bronze layer of the data lake (LocalStack S3).

Run with: streamlit run src/dashboard.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import drift  # noqa: E402

load_dotenv()

st.set_page_config(page_title="SafeSite AI Dashboard", layout="wide")


def connect():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


@st.cache_data(ttl=10)
def load_violations():
    """Raw events (audit and evidence)."""
    conn = connect()
    df = pd.read_sql_query(
        "SELECT id, camera_id, track_id, violation_type, confidence, started_at, evidence_uri FROM violations ORDER BY started_at DESC",
        conn,
    )
    conn.close()
    df["started_at"] = pd.to_datetime(df["started_at"])
    return df


@st.cache_data(ttl=30)
def load_gold():
    """Hourly aggregates with canonical violation types."""
    conn = connect()
    df = pd.read_sql_query(
        "SELECT hour, camera_id, violation_type, violation_count, avg_confidence, computed_at FROM gold.violations_hourly",
        conn,
    )
    conn.close()
    df["hour"] = pd.to_datetime(df["hour"])
    return df


df = load_violations()
gold = load_gold()

st.title("SafeSite AI - PPE Compliance Dashboard")

if gold.empty:
    st.warning("The gold layer is empty: run the Airflow DAG gold_daily first.")
    st.stop()

st.caption(f"Aggregates from the gold layer, last computed {gold['computed_at'].max():%Y-%m-%d %H:%M}")

# --- Sidebar filters ---
st.sidebar.header("Filters")

camera_options = ["All"] + sorted(gold["camera_id"].unique().tolist())
selected_camera = st.sidebar.selectbox("Camera", camera_options)

type_options = ["All"] + sorted(gold["violation_type"].unique().tolist())
selected_type = st.sidebar.selectbox("Violation type (aggregates)", type_options)

g = gold.copy()
raw = df.copy()
if selected_camera != "All":
    g = g[g["camera_id"] == selected_camera]
    raw = raw[raw["camera_id"] == selected_camera]
if selected_type != "All":
    g = g[g["violation_type"] == selected_type]

# --- KPI row (gold) ---
total = int(g["violation_count"].sum())
weighted = g.dropna(subset=["avg_confidence"])
avg_conf = (
    (weighted["avg_confidence"] * weighted["violation_count"]).sum() / weighted["violation_count"].sum()
    if len(weighted) and weighted["violation_count"].sum()
    else None
)
col1, col2, col3 = st.columns(3)
col1.metric("Total violations", total)
col2.metric("Unique violation types", g["violation_type"].nunique())
col3.metric("Average confidence", f"{avg_conf:.2f}" if avg_conf is not None else "N/A")

# --- Charts (gold) ---
st.subheader("Violations by type")
st.bar_chart(g.groupby("violation_type")["violation_count"].sum())

st.subheader("Violations per day")
st.line_chart(g.groupby(g["hour"].dt.floor("D"))["violation_count"].sum())

# --- Table (raw events) ---
st.subheader("Recent violations (raw events)")
st.caption(
    "Event-level detail read from public.violations: labels are shown as recorded (not normalised). "
    "The camera filter applies here; the type filter applies to the aggregates above only."
)
st.dataframe(raw.head(100), use_container_width=True)

# --- Evidence viewer ---
st.subheader("Evidence viewer")
if len(raw) > 0:
    options = raw.head(100).apply(
        lambda row: f"#{row['id']} | camera {row['camera_id']} | {row['violation_type']} | {row['started_at']}",
        axis=1,
    ).tolist()
    selected = st.selectbox("Pick a violation to inspect", options)
    selected_id = int(selected.split("|")[0].strip().lstrip("#"))
    row = raw[raw["id"] == selected_id].iloc[0]

    if pd.notna(row["evidence_uri"]) and os.path.exists(row["evidence_uri"]):
        track_label = int(row["track_id"]) if pd.notna(row["track_id"]) else "N/A"
        st.image(
            row["evidence_uri"],
            caption=f"Track {track_label} - {row['violation_type']} ({row['confidence']:.2f} confidence)",
            width=500,
        )
    else:
        st.info("No evidence image available for this violation (recorded before evidence tracking was fixed, or file missing).")
else:
    st.info("No violations match the current filters.")
# --- Data drift ---
st.subheader("Data drift between cameras")


@st.cache_data(ttl=30)
def cached_bronze(camera_id):
    df, _ = drift.load_bronze(camera_id)
    return df


try:
    bronze_cameras = drift.list_bronze_cameras()
except Exception as exc:
    bronze_cameras = []
    st.info(f"Data lake unavailable (is LocalStack running?): {exc}")

if len(bronze_cameras) >= 2:
    pick1, pick2 = st.columns(2)
    ref_cam = pick1.selectbox("Reference camera", bronze_cameras, index=0)
    cur_cam = pick2.selectbox("Current camera", bronze_cameras, index=1)
    result = drift.compare(cached_bronze(ref_cam), cached_bronze(cur_cam))

    k1, k2, k3 = st.columns(3)
    k1.metric("PSI on box-type mix", f"{result['psi']:.3f}", result["verdict"], delta_color="off", delta_arrow="off")
    k2.metric("Boxes/frame shift (KS D)", f"{result['ks_d']:.3f}")
    k3.metric(
        "Violation share",
        f"{result['cur_violation_share']:.1%}",
        f"reference {result['ref_violation_share']:.1%}",
        delta_color="off", delta_arrow="off",
    )
    st.dataframe(result["mix"].round(3), use_container_width=True)
    st.caption(
        "Drift means the data changed, not that the model got worse: confirming "
        "a degradation needs labeled images from the new scene. PSI: <0.1 stable, "
        "0.1-0.25 watch, >0.25 drift."
    )
elif not bronze_cameras:
    pass
else:
    st.info("Need bronze data for at least two cameras.")
