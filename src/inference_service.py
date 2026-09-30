"""
CV integration: runs detection + tracking on a video, converts the raw
per-frame output into deduplicated violation episodes (src/episodes.py),
saves one evidence frame per episode, and publishes each as a Violation
event (matching docs/contracts.md, Violation Event Contract v1) onto the
Kafka `events` topic.

Design change (Day 16): this used to POST directly to the API. It now
publishes to Kafka instead, so the CV pipeline never blocks on or depends
on the API being up. A separate consumer (src/event_consumer.py) reads
from `events` and does the actual POST - see that file's docstring for why.

Known simplification: this is offline batch processing, not a live stream,
so timestamps are synthesized from the script's start time + frame offset
(frame_idx / fps), not real wall-clock capture times. Live timestamps
arrive later in Week 3 when ingestion reads a real/simulated camera stream.
"""

import json
import os
from datetime import datetime, timedelta

import cv2
from kafka import KafkaProducer
from ultralytics import YOLO

from src.episodes import detect_episodes

MODEL_PATH = "models/yolov8s_ppe_v1.pt"
VIDEO_PATH = "data/samples/test_video.mp4"
KAFKA_BROKER = "localhost:9092"
EVENTS_TOPIC = "events"
EVIDENCE_DIR = "data/evidence"
CAMERA_ID = 1

os.makedirs(EVIDENCE_DIR, exist_ok=True)


def run_detection_and_tracking():
    model = YOLO(MODEL_PATH)
    results = model.track(source=VIDEO_PATH, tracker="bytetrack.yaml", stream=True, verbose=False)

    detections = []
    for frame_idx, result in enumerate(results):
        if result.boxes.id is None:
            continue
        for box in result.boxes:
            track_id = int(box.id.item())
            class_name = result.names[int(box.cls.item())]
            label = class_name if class_name.startswith("NO-") else None
            detections.append((frame_idx, track_id, label))

    return detections


def save_evidence_frame(video_path, frame_idx, track_id):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    path = f"{EVIDENCE_DIR}/track{track_id}_frame{frame_idx}.jpg"
    cv2.imwrite(path, frame)
    return path


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("Running detection + tracking...")
    detections = run_detection_and_tracking()
    print(f"Collected {len(detections)} raw detections")

    episodes = detect_episodes(detections)
    print(f"Detected {len(episodes)} violation episodes")

    run_start_time = datetime.now()

    for ep in episodes:
        mid_frame = (ep["start_frame"] + ep["end_frame"]) // 2
        evidence_path = save_evidence_frame(VIDEO_PATH, mid_frame, ep["track_id"])

        started_at = run_start_time + timedelta(seconds=ep["start_frame"] / fps)
        ended_at = run_start_time + timedelta(seconds=ep["end_frame"] / fps)

        payload = {
            "camera_id": CAMERA_ID,
            "track_id": ep["track_id"],
            "violation_type": ep["violation_type"],
            "confidence": ep["majority_fraction"],
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "evidence_uri": evidence_path,
        }

        producer.send(EVENTS_TOPIC, value=payload)
        print(f"Published: Track {ep['track_id']} | {ep['violation_type']}")

    producer.flush()


if __name__ == "__main__":
    main()
