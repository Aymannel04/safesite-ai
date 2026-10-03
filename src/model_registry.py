"""Resolve the model currently marked 'production' in the MLflow registry.

Inference code asks for an alias instead of hardcoding a checkpoint path, so
promoting a different model means moving the alias, not editing code.
"""
from pathlib import Path
from urllib.parse import urlparse

import mlflow
from mlflow import MlflowClient

TRACKING_URI = "sqlite:///mlflow.db"
MODEL_NAME = "safesite-ppe-detector"
DEFAULT_ALIAS = "production"


def get_model_path(alias=DEFAULT_ALIAS):
    mlflow.set_tracking_uri(TRACKING_URI)
    mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, alias)
    path = Path(urlparse(mv.source).path)
    if not path.exists():
        raise FileNotFoundError(
            f"Registry alias '{alias}' (version {mv.version}) points to {path}, which does not exist"
        )
    print(f"Model registry: alias '{alias}' -> version {mv.version} -> {path}")
    return str(path)
