"""Seed the database with extra cameras and bulk fake violations."""
import logging
import os
import random
from datetime import datetime, timedelta

import psycopg2
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

VIOLATION_TYPES = ["no_helmet", "no_vest", "no_gloves"]


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def seed_cameras(cur):
    cameras = [
        ("Entrance Camera 2", "Zone B - Loading Dock"),
        ("Entrance Camera 3", "Zone C - Warehouse Floor"),
    ]
    for name, location in cameras:
        cur.execute(
            "INSERT INTO cameras (name, location) VALUES (%s, %s)",
            (name, location),
        )
    logging.info("Seeded extra cameras")


def seed_violations(cur, n=5000):
    cur.execute("SELECT id FROM cameras")
    camera_ids = [row[0] for row in cur.fetchall()]
    now = datetime.now()

    for _ in range(n):
        camera_id = random.choice(camera_ids)
        violation_type = random.choice(VIOLATION_TYPES)
        confidence = round(random.uniform(0.5, 0.99), 2)
        started_at = now - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        cur.execute(
            """
            INSERT INTO violations (camera_id, violation_type, confidence, started_at)
            VALUES (%s, %s, %s, %s)
            """,
            (camera_id, violation_type, confidence, started_at),
        )
    logging.info(f"Seeded {n} fake violations")


def main():
    conn = get_connection()
    cur = conn.cursor()
    seed_cameras(cur)
    conn.commit()
    seed_violations(cur, n=5000)
    conn.commit()
    cur.close()
    conn.close()
    logging.info("Done seeding database")


if __name__ == "__main__":
    main()
