import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "frames-json",
    group_id="frames-test-group",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest",
)

for message in consumer:
    print(f"Received: {message.value}")
