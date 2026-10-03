"""Backfill the v1 training run into MLflow as a baseline.

v1 (models/yolov8s_ppe_v1.pt) was trained before MLflow was introduced, so
its numbers are copied from docs/training_results_v1.md rather than measured
live. The run is tagged accordingly so nobody mistakes it for a tracked run.
"""
import mlflow

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("safesite-ppe-detection")


def main():
    with mlflow.start_run(run_name="ppe_v1_baseline"):
        mlflow.set_tag("source", "backfilled from docs/training_results_v1.md")

        mlflow.log_param("base_model", "yolov8s.pt")
        mlflow.log_param("epochs", 50)
        mlflow.log_param("imgsz", 640)
        mlflow.log_param("batch", 16)
        mlflow.log_param("dataset", "data/ppe_dataset/data.yaml")

        mlflow.log_metric("mAP50", 0.810)
        mlflow.log_metric("precision", 0.918)
        mlflow.log_metric("recall", 0.759)

        mlflow.log_artifact("models/yolov8s_ppe_v1.pt")
        print("v1 baseline logged to MLflow.")


if __name__ == "__main__":
    main()
