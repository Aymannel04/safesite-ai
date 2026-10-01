"""
Measures the live pipeline's actual processing rate against the camera's
real frame rate, to determine whether the model is keeping up with a live
feed in real time or falling behind it.
"""

import time

from ultralytics import YOLO

MODEL_PATH = "models/yolov8s_ppe_v1.pt"
RTSP_URL = "rtsp://localhost:8554/camera1"
SOURCE_FPS = 29.97
TEST_DURATION_SECONDS = 30

model = YOLO(MODEL_PATH)
results = model.track(source=RTSP_URL, tracker="bytetrack.yaml", stream=True, verbose=False, device=0)

start = time.time()
frame_count = 0

for result in results:
    frame_count += 1
    elapsed = time.time() - start
    if elapsed >= TEST_DURATION_SECONDS:
        break

elapsed = time.time() - start
effective_fps = frame_count / elapsed
expected_frames = elapsed * SOURCE_FPS
pct_of_realtime = (effective_fps / SOURCE_FPS) * 100

print(f"Elapsed: {elapsed:.2f}s")
print(f"Frames processed: {frame_count}")
print(f"Effective processing rate: {effective_fps:.2f} fps")
print(f"Source rate: {SOURCE_FPS} fps")
print(f"Percent of real-time: {pct_of_realtime:.1f}%")
print(f"Frames the source produced in this time (approx): {expected_frames:.0f}")
print(f"Frames behind (negative means ahead/keeping up): {expected_frames - frame_count:.0f}")
