import json
import time
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

for i in range(5):
    message = {"frame_id": i, "camera_id": 1, "timestamp": time.time()}
    producer.send("frames-json", value=message)
    print(f"Sent: {message}")
    time.sleep(1)

producer.flush()
