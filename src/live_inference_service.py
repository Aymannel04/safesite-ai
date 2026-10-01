"""
Live ingestion + inference service: reads a live RTSP stream (a real or
simulated camera), runs YOLO+ByteTrack continuously, and closes out each
track's violation episode once that track hasn't been seen for
TRACK_TIMEOUT frames - i.e., the person has left the scene or tracking
lost them. Closed episodes are published to the Kafka `events` topic,
same downstream contract as the offline inference_service.py (Day 14/16).

Day 19: also archives to the data lake (LocalStack S3, bucket
safesite-datalake), same bronze/silver concept as inference_service.py.
Since a live stream never "finishes" the way a batch file does, there's no
single end-of-run moment to archive everything at once - instead, each
track is archived individually the moment it closes: bronze gets every
closed track's raw per-frame data regardless of outcome (the complete
record, in case episode-detection logic ever needs to be reprocessed),
silver gets only the tracks that actually qualified as violations.

Design difference from inference_service.py: that script processes a
finite file, so it can wait until the entire video is read before
evaluating any track. A live camera stream never ends, so each track must
be evaluated and closed out individually, the moment we're confident it's
actually gone.

Known simplification: evidence frame extraction (saving a jpg per episode,
as inference_service.py does) isn't implemented yet here, since that
requires buffering frames from a live stream rather than seeking into a
file - evidence_uri is left null for now. Timestamps use real wall-clock
time (datetime.now()) at the moment the track closes, which is correct for
a genuinely live feed, unlike the synthesized timestamps batch processing
needed.
"""

import json
from collections import defaultdict
from datetime import datetime

import boto3
from kafka import KafkaProducer
from ultralytics import YOLO

from src.episodes import evaluate_track

MODEL_PATH = "models/yolov8s_ppe_v1.pt"
RTSP_URL = "rtsp://localhost:8554/camera1"
KAFKA_BROKER = "localhost:9092"
EVENTS_TOPIC = "events"
CAMERA_ID = 1
TRACK_TIMEOUT = 60  # frames (~2s at 30fps) a track can go unseen before being closed out

S3_ENDPOINT = "http://localhost:4566"
S3_BUCKET = "safesite-datalake"


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def archive_to_s3(s3, key, data):
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(data).encode("utf-8"))


def main():
    model = YOLO(MODEL_PATH)
    s3 = get_s3_client()
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")

    track_buffers = defaultdict(list)  # track_id -> list of (frame_idx, label)
    last_seen = {}  # track_id -> frame_idx it was last seen in

    results = model.track(source=RTSP_URL, tracker="bytetrack.yaml", stream=True, verbose=False)

    print("Live inference started. Press Ctrl+C to stop.")

    for frame_idx, result in enumerate(results):
        if result.boxes.id is not None:
            for box in result.boxes:
                track_id = int(box.id.item())
                class_name = result.names[int(box.cls.item())]
                label = class_name if class_name.startswith("NO-") else None

                track_buffers[track_id].append((frame_idx, label))
                last_seen[track_id] = frame_idx

        stale_ids = [tid for tid, seen_at in last_seen.items() if frame_idx - seen_at > TRACK_TIMEOUT]

        for track_id in stale_ids:
            frames = track_buffers.pop(track_id)
            del last_seen[track_id]

            archive_to_s3(s3, f"bronze/{run_id}/track_{track_id}.json", frames)

            episode = evaluate_track(track_id, frames)
            if episode:
                archive_to_s3(s3, f"silver/{run_id}/track_{track_id}.json", episode)

                now = datetime.now().isoformat()
                payload = {
                    "camera_id": CAMERA_ID,
                    "track_id": episode["track_id"],
                    "violation_type": episode["violation_type"],
                    "confidence": episode["majority_fraction"],
                    "started_at": now,
                    "ended_at": now,
                    "evidence_uri": None,
                }
                producer.send(EVENTS_TOPIC, value=payload)
                print(f"Closed track {track_id} -> Published: {episode['violation_type']}")


if __name__ == "__main__":
    main()
