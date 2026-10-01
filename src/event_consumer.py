"""
Event consumer: subscribes to the Kafka `events` topic and persists each
violation event to the database via the existing FastAPI endpoint.

This is the piece that decouples the CV pipeline (inference_service.py)
from the API's availability. inference_service.py can keep running and
publishing events even if this consumer, or the API itself, is temporarily
down or restarting - Kafka holds the events safely until this consumer
catches back up (see Day 15's offset-persistence test for why that's true).

Day 20 reliability fix: this used to rely on Kafka's default auto-commit,
which advances the offset the moment a message is handed to the consumer's
loop - regardless of whether the POST to the API actually succeeded. A
reliability test (killing Postgres mid-stream) proved this silently lost
violations: the API returned 500, the consumer printed it and moved on, and
the offset still advanced, so Kafka never redelivered that message. Fixed
by disabling auto-commit, retrying failed POSTs a few times, and if still
failing, writing the event to a local dead-letter file before committing -
so a failure is recorded and recoverable instead of silently vanishing.
"""

import json
import time
from pathlib import Path

import requests
from kafka import KafkaConsumer

KAFKA_BROKER = "localhost:9092"
EVENTS_TOPIC = "events"
API_URL = "http://localhost:8000/violations"
CONSUMER_GROUP = "event-consumer-group"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
DEAD_LETTER_PATH = Path("data/dead_letter/events.jsonl")

DEAD_LETTER_PATH.parent.mkdir(parents=True, exist_ok=True)

consumer = KafkaConsumer(
    EVENTS_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    group_id=CONSUMER_GROUP,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest",
    enable_auto_commit=False,
)


def post_with_retries(payload):
    """Tries the POST up to MAX_RETRIES times. Returns True on success,
    False if it never succeeded."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(API_URL, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"Track {payload['track_id']} | {payload['violation_type']} | POST status 200")
                return True
            print(f"Attempt {attempt}/{MAX_RETRIES} failed: POST status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS)

    return False


def write_to_dead_letter(payload):
    with open(DEAD_LETTER_PATH, "a") as f:
        f.write(json.dumps(payload) + "\n")
    print(f"Gave up after {MAX_RETRIES} attempts - wrote to {DEAD_LETTER_PATH}")


def main():
    print(f"Listening on '{EVENTS_TOPIC}'...")
    for message in consumer:
        payload = message.value

        success = post_with_retries(payload)
        if not success:
            write_to_dead_letter(payload)

        # Only commit once we've either succeeded or given up and safely
        # recorded the failure - never commit silently on an unhandled error.
        consumer.commit()


if __name__ == "__main__":
    main()
