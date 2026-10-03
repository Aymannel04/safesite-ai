"""Quick demo training run wrapped with MLflow experiment tracking.

Day 22: wires Ultralytics YOLO training into MLflow so future training runs
(different hyperparameters, different datasets) can be logged and compared
systematically. This specific run uses a deliberately small epoch count -
the goal is to prove the tracking integration works end-to-end, not to beat
the real v1 checkpoint (models/yolov8s_ppe_v1.pt, 50 epochs). Real
model-improvement experiments are deferred to later in the project.

Note: all logic lives under main() behind an __main__ guard because PyTorch
DataLoader workers re-import this file (Python 3.14 uses 'forkserver'); without
the guard every worker would re-run the whole training.
"""
from pathlib import Path

import mlflow
from ultralytics import YOLO, settings

DATA_YAML = "data/ppe_dataset/data.yaml"
BASE_MODEL = "yolov8s.pt"
EPOCHS = 5
IMGSZ = 640
BATCH = 16
RUN_NAME = "ppe_mlflow_demo"


def main():
    # We log manually below, so turn off Ultralytics' built-in MLflow hook
    # (otherwise every run is logged twice, in two different experiments).
    settings.update({"mlflow": False})

    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("safesite-ppe-detection")

    with mlflow.start_run(run_name=RUN_NAME):
        mlflow.log_param("base_model", BASE_MODEL)
        mlflow.log_param("epochs", EPOCHS)
        mlflow.log_param("imgsz", IMGSZ)
        mlflow.log_param("batch", BATCH)
        mlflow.log_param("dataset", DATA_YAML)

        model = YOLO(BASE_MODEL)
        model.train(
            data=DATA_YAML,
            epochs=EPOCHS,
            imgsz=IMGSZ,
            batch=BATCH,
            device=0,
            project="runs/detect",
            name=RUN_NAME,
        )
        save_dir = Path(model.trainer.save_dir)

        metrics = model.val()
        results_dict = metrics.results_dict
        mlflow.log_metric("mAP50", results_dict["metrics/mAP50(B)"])
        mlflow.log_metric("mAP50-95", results_dict["metrics/mAP50-95(B)"])
        mlflow.log_metric("precision", results_dict["metrics/precision(B)"])
        mlflow.log_metric("recall", results_dict["metrics/recall(B)"])

        mlflow.log_artifact(str(save_dir / "weights" / "best.pt"))

        print("Training complete. Logged to MLflow.")


if __name__ == "__main__":
    main()
