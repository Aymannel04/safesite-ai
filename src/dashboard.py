"""
Streamlit dashboard for SafeSite AI - reads violations directly from
Postgres and displays them as a live, filterable view: KPI summary,
violations-over-time chart, violations-by-type chart, and a recent-events
table.

Run with: streamlit run src/dashboard.py
"""

import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

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
        "SELECT id, camera_id, violation_type, confidence, started_at FROM violations ORDER BY started_at DESC",
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
