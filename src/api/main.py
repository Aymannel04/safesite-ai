"""FastAPI application exposing violation data."""
import logging
import os
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

app = FastAPI(title="SafeSite AI API")


class Violation(BaseModel):
    id: int
    camera_id: int
    violation_type: str
    confidence: float
    started_at: datetime


class ViolationCreate(BaseModel):
    camera_id: int
    violation_type: str
    confidence: float = Field(ge=0, le=1)
    started_at: datetime


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


@app.get("/violations", response_model=list[Violation])
def list_violations(camera_id: Optional[int] = None, violation_type: Optional[str] = None, limit: int = 20):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT id, camera_id, violation_type, confidence, started_at FROM violations WHERE 1=1"
    params = []
    if camera_id is not None:
        query += " AND camera_id = %s"
        params.append(camera_id)
    if violation_type is not None:
        query += " AND violation_type = %s"
        params.append(violation_type)
    query += " ORDER BY started_at DESC LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.post("/violations", response_model=Violation)
def create_violation(violation: ViolationCreate):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        INSERT INTO violations (camera_id, violation_type, confidence, started_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id, camera_id, violation_type, confidence, started_at
        """,
        (violation.camera_id, violation.violation_type, violation.confidence, violation.started_at),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return row


@app.get("/stats/daily")
def daily_stats():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT DATE_TRUNC('day', started_at) AS day, COUNT(*) AS count
        FROM violations
        GROUP BY day
        ORDER BY day DESC
        LIMIT 30
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
