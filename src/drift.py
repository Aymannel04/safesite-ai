"""Data drift measures between two cameras, computed on the bronze layer.

Two measures: a KS test on boxes-per-frame (continuous) and the PSI on the
mix of box types (violation class vs everything else).

Limits: bronze only keeps a label for NO-* classes (everything else is None),
frames with no tracked box are absent, and frames of one video are
autocorrelated, so KS p-values are optimistic. Drift means "the data changed,
go check", not "the model got worse".
"""
import json

import boto3
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

S3_ENDPOINT = "http://localhost:4566"
S3_BUCKET = "safesite-datalake"
EPS = 1e-4
OTHER = "other (non-violation box)"
PSI_WATCH = 0.1
PSI_DRIFT = 0.25


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def list_bronze_cameras(s3=None):
    s3 = s3 or get_s3_client()
    resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="bronze/camera_id=", Delimiter="/")
    prefixes = [p["Prefix"] for p in resp.get("CommonPrefixes", [])]
    return sorted(int(p.split("camera_id=")[1].rstrip("/")) for p in prefixes)


def load_bronze(camera_id, s3=None):
    """Latest bronze run of a camera, as a DataFrame (frame, track_id, label)."""
    s3 = s3 or get_s3_client()
    prefix = f"bronze/camera_id={camera_id}/"
    contents = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix).get("Contents", [])
    keys = sorted(o["Key"] for o in contents)
    if not keys:
        raise LookupError(f"No bronze data for camera {camera_id}")
    body = s3.get_object(Bucket=S3_BUCKET, Key=keys[-1])["Body"].read()
    df = pd.DataFrame(json.loads(body), columns=["frame", "track_id", "label"])
    return df, keys[-1]


def boxes_per_frame(df):
    return df.groupby("frame").size()


def type_mix(df):
    return df["label"].fillna(OTHER).value_counts(normalize=True)


def psi(ref_mix, cur_mix):
    cats = sorted(set(ref_mix.index) | set(cur_mix.index))
    r = ref_mix.reindex(cats, fill_value=0).clip(lower=EPS)
    c = cur_mix.reindex(cats, fill_value=0).clip(lower=EPS)
    return float(((c - r) * np.log(c / r)).sum())


def verdict(psi_value):
    if psi_value < PSI_WATCH:
        return "stable"
    if psi_value < PSI_DRIFT:
        return "watch"
    return "DRIFT"


def compare(ref, cur):
    ks = ks_2samp(boxes_per_frame(ref), boxes_per_frame(cur))
    score = psi(type_mix(ref), type_mix(cur))
    mix = pd.concat([type_mix(ref).rename("ref"), type_mix(cur).rename("cur")], axis=1).fillna(0)
    return {
        "ref_mean_boxes": float(boxes_per_frame(ref).mean()),
        "cur_mean_boxes": float(boxes_per_frame(cur).mean()),
        "ks_d": float(ks.statistic),
        "ks_p": float(ks.pvalue),
        "ref_violation_share": float(ref["label"].notna().mean()),
        "cur_violation_share": float(cur["label"].notna().mean()),
        "psi": score,
        "verdict": verdict(score),
        "mix": mix,
    }
