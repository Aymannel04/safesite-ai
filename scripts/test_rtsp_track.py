from ultralytics import YOLO

MODEL_PATH = "models/yolov8s_ppe_v1.pt"
RTSP_URL = "rtsp://localhost:8554/camera1"

model = YOLO(MODEL_PATH)
results = model.track(source=RTSP_URL, tracker="bytetrack.yaml", stream=True, verbose=False)

count = 0
for result in results:
    count += 1
    if count % 30 == 0:
        print(f"Processed {count} frames...")
    if count >= 150:
        break

print(f"Done. Processed {count} frames total.")
