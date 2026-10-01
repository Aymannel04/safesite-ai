"""
Reprocesses events from the dead-letter file (data/dead_letter/events.jsonl),
written by event_consumer.py when it gives up retrying a failed POST. Run
this once the underlying problem (e.g. database downtime) is resolved.

Successfully replayed events are removed from the file; any that still fail
are written back, so this is safe to re-run.
"""

import json
from pathlib import Path

import requests

API_URL = "http://localhost:8000/violations"
DEAD_LETTER_PATH = Path("data/dead_letter/events.jsonl")


def main():
    if not DEAD_LETTER_PATH.exists():
        print("No dead-letter file found - nothing to replay.")
        return

    with open(DEAD_LETTER_PATH) as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("Dead-letter file is empty - nothing to replay.")
        return

    print(f"Found {len(lines)} dead-lettered event(s). Replaying...")

    still_failing = []

    for line in lines:
        payload = json.loads(line)
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"Replayed track {payload['track_id']} successfully")
        else:
            print(f"Track {payload['track_id']} still failing (status {response.status_code})")
            still_failing.append(line)

    with open(DEAD_LETTER_PATH, "w") as f:
        for line in still_failing:
            f.write(line + "\n")

    print(f"Done. {len(lines) - len(still_failing)} recovered, {len(still_failing)} still pending.")


if __name__ == "__main__":
    main()
