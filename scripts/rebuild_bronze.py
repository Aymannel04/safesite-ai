"""Rebuild the bronze/silver layers of the data lake from a video, WITHOUT Kafka or Postgres.

Why: LocalStack keeps its state in memory, so the lake is empty after a restart. The drift
module only needs bronze, and re-running inference_service.py would republish its events to
Kafka (duplicate violations in Postgres), so this script reuses only its detection and
S3-archiving functions.

Usage (from the repo root): python scripts/rebuild_bronze.py --camera-id 2 --video data/videos/camera2_site.mp4
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import inference_service as svc  # noqa: E402
from src.episodes import detect_episodes  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera-id", type=int, required=True)
    ap.add_argument("--video", required=True)
    args = ap.parse_args()

    svc.VIDEO_PATH = args.video  # run_detection_and_tracking() reads this module-level variable
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    s3 = svc.get_s3_client()  # creates the bucket if it is missing

    print(f"Detection + tracking on {args.video} ...")
    detections, _ = svc.run_detection_and_tracking()
    print(f"{len(detections)} raw detections")
    svc.archive_to_s3(s3, f"bronze/camera_id={args.camera_id}/run_id={run_id}/detections.json", detections)

    episodes = detect_episodes(detections)
    svc.archive_to_s3(s3, f"silver/camera_id={args.camera_id}/run_id={run_id}/episodes.json", episodes)
    print(f"{len(episodes)} episodes archived. No Kafka message sent, nothing written to Postgres.")


if __name__ == "__main__":
    main()
