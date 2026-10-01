import json
from datetime import datetime

from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

payload = {
    "camera_id": 1,
    "track_id": 99999,
    "violation_type": "NO-Mask",
    "confidence": 1.0,
    "started_at": datetime.now().isoformat(),
    "ended_at": datetime.now().isoformat(),
    "evidence_uri": None,
}

producer.send("events", value=payload)
producer.flush()
print(f"Sent test event: track_id={payload['track_id']}")
