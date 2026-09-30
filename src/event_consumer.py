"""
Event consumer: subscribes to the Kafka `events` topic and persists each
violation event to the database via the existing FastAPI endpoint.

This is the piece that decouples the CV pipeline (inference_service.py)
from the API's availability. inference_service.py can keep running and
publishing events even if this consumer, or the API itself, is temporarily
down or restarting - Kafka holds the events safely until this consumer
catches back up (see Day 15's offset-persistence test for why that's true).
"""

import json

import requests
from kafka import KafkaConsumer

KAFKA_BROKER = "localhost:9092"
EVENTS_TOPIC = "events"
API_URL = "http://localhost:8000/violations"
CONSUMER_GROUP = "event-consumer-group"

consumer = KafkaConsumer(
    EVENTS_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    group_id=CONSUMER_GROUP,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest",
)


def main():
    print(f"Listening on '{EVENTS_TOPIC}'...")
    for message in consumer:
        payload = message.value
        response = requests.post(API_URL, json=payload)
        print(f"Track {payload['track_id']} | {payload['violation_type']} | POST status {response.status_code}")


if __name__ == "__main__":
    main()
