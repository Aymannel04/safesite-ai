import time
import cv2

RTSP_URL = "rtsp://localhost:8554/camera1"

cap = cv2.VideoCapture(RTSP_URL)

if not cap.isOpened():
    print("Failed to open stream")
else:
    print("Stream opened successfully")

start = time.time()
frame_count = 0

while time.time() - start < 10:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        break
    frame_count += 1

cap.release()
print(f"Read {frame_count} frames in 10 seconds")
