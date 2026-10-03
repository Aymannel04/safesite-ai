"""Register the v1 baseline and the demo run in the MLflow Model Registry.

v1 gets the alias 'production' (it is the checkpoint inference currently
uses); the 5-epoch demo run gets 'candidate'. Run once: every execution
creates new versions.
"""
import mlflow
from mlflow import MlflowClient

mlflow.set_tracking_uri("sqlite:///mlflow.db")
client = MlflowClient()

MODEL_NAME = "safesite-ppe-detector"
EXPERIMENT = "safesite-ppe-detection"


def find_run(run_name):
    exp = client.get_experiment_by_name(EXPERIMENT)
    runs = client.search_runs(
        [exp.experiment_id], filter_string=f"tags.mlflow.runName = '{run_name}'"
    )
    assert len(runs) == 1, f"expected 1 run named {run_name}, found {len(runs)}"
    return runs[0]


def register(run_name, artifact_name, alias):
    run = find_run(run_name)
    mv = client.create_model_version(
        name=MODEL_NAME,
        source=f"{run.info.artifact_uri}/{artifact_name}",
        run_id=run.info.run_id,
    )
    client.set_registered_model_alias(MODEL_NAME, alias, mv.version)
    print(f"{run_name} -> version {mv.version}, alias '{alias}'")


def main():
    register("ppe_v1_baseline", "yolov8s_ppe_v1.pt", "production")
    register("ppe_mlflow_demo", "best.pt", "candidate")


if __name__ == "__main__":
    main()
