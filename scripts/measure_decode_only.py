"""
Measures raw OpenCV decode throughput against the RTSP stream, with no
model inference at all - isolates whether video decoding itself is the
bottleneck, separate from YOLO.
"""

import time
import cv2

RTSP_URL = "rtsp://localhost:8554/camera1"
SOURCE_FPS = 29.97
TEST_DURATION_SECONDS = 30

cap = cv2.VideoCapture(RTSP_URL)

start = time.time()
frame_count = 0

while time.time() - start < TEST_DURATION_SECONDS:
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

cap.release()

elapsed = time.time() - start
effective_fps = frame_count / elapsed
pct_of_realtime = (effective_fps / SOURCE_FPS) * 100

print(f"Elapsed: {elapsed:.2f}s")
print(f"Frames decoded: {frame_count}")
print(f"Effective decode rate: {effective_fps:.2f} fps")
print(f"Percent of real-time: {pct_of_realtime:.1f}%")
