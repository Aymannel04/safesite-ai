"""
Streamlit dashboard for SafeSite AI - reads violations directly from
Postgres and displays them as a live, filterable view: KPI summary,
violations-over-time chart, violations-by-type chart, and a recent-events
table.

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


@st.cache_data(ttl=10)
def load_violations():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    df = pd.read_sql_query(
        "SELECT id, camera_id, track_id, violation_type, confidence, started_at, evidence_uri FROM violations ORDER BY started_at DESC",
        conn,
    )
    conn.close()
    df["started_at"] = pd.to_datetime(df["started_at"])
    return df


df = load_violations()

st.title("SafeSite AI - PPE Compliance Dashboard")

# --- Sidebar filters ---
st.sidebar.header("Filters")

camera_options = ["All"] + sorted(df["camera_id"].unique().tolist())
selected_camera = st.sidebar.selectbox("Camera", camera_options)

type_options = ["All"] + sorted(df["violation_type"].unique().tolist())
selected_type = st.sidebar.selectbox("Violation type", type_options)

filtered = df.copy()
if selected_camera != "All":
    filtered = filtered[filtered["camera_id"] == selected_camera]
if selected_type != "All":
    filtered = filtered[filtered["violation_type"] == selected_type]

# --- KPI row ---
col1, col2, col3 = st.columns(3)
col1.metric("Total violations", len(filtered))
col2.metric("Unique violation types", filtered["violation_type"].nunique())
col3.metric("Average confidence", f"{filtered['confidence'].mean():.2f}" if len(filtered) else "N/A")

# --- Charts ---
st.subheader("Violations by type")
st.bar_chart(filtered["violation_type"].value_counts())

st.subheader("Violations over time")
timeline = filtered.set_index("started_at").resample("1min").size()
st.line_chart(timeline)

# --- Table ---
st.subheader("Recent violations")
st.dataframe(filtered.head(100), use_container_width=True)

# --- Evidence viewer ---
st.subheader("Evidence viewer")
if len(filtered) > 0:
    options = filtered.head(100).apply(
        lambda row: f"#{row['id']} | camera {row['camera_id']} | {row['violation_type']} | {row['started_at']}",
        axis=1,
    ).tolist()
    selected = st.selectbox("Pick a violation to inspect", options)
    selected_id = int(selected.split("|")[0].strip().lstrip("#"))
    row = filtered[filtered["id"] == selected_id].iloc[0]

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
