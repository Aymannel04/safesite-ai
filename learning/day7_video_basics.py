"""Day 7: video fundamentals - read frames, sample, measure cost."""
import logging
import os
import time

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

VIDEO_PATH = "data/samples/test_video.mp4"
OUTPUT_DIR = "data/samples/frames"


def inspect_video(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps else 0
    logging.info(f"FPS: {fps}, frames: {frame_count}, resolution: {width}x{height}, duration: {duration:.1f}s")
    cap.release()


def extract_one_frame_per_second(path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps)
    frame_num = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_num % frame_interval == 0:
            out_path = os.path.join(output_dir, f"frame_{saved:03d}.jpg")
            cv2.imwrite(out_path, frame)
            saved += 1
        frame_num += 1

    cap.release()
    logging.info(f"Saved {saved} frames (1 per second)")


def measure_resolution_cost(path):
    for scale_name, scale in [("full", 1.0), ("half", 0.5)]:
        cap = cv2.VideoCapture(path)
        start = time.time()
        count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if scale != 1.0:
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            count += 1
        elapsed = time.time() - start
        cap.release()
        logging.info(f"{scale_name} resolution: processed {count} frames in {elapsed:.2f}s ({count/elapsed:.1f} fps)")


def main():
    inspect_video(VIDEO_PATH)
    extract_one_frame_per_second(VIDEO_PATH, OUTPUT_DIR)
    measure_resolution_cost(VIDEO_PATH)


if __name__ == "__main__":
    main()
