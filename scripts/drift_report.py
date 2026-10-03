"""Compare the detection distribution of two cameras (bronze layer).

Reference vs current, using two measures:
  - KS test on boxes-per-frame (continuous signal)
  - PSI on the mix of box types (violation class vs everything else)

Limits: bronze only keeps label for NO-* classes (everything else is None),
and frames with no tracked box are absent, so per-frame counts only cover
frames with at least one tracked box. Frames of one video are autocorrelated,
so KS p-values are optimistic; treat them as a signal, not proof.
"""
import argparse
import json

import boto3
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

S3_ENDPOINT = "http://localhost:4566"
S3_BUCKET = "safesite-datalake"
EPS = 1e-4
OTHER = "other (non-violation box)"


def load_bronze(s3, camera_id):
    prefix = f"bronze/camera_id={camera_id}/"
    contents = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix).get("Contents", [])
    keys = sorted(o["Key"] for o in contents)
    if not keys:
        raise SystemExit(f"No bronze data for camera {camera_id}")
    body = s3.get_object(Bucket=S3_BUCKET, Key=keys[-1])["Body"].read()
    df = pd.DataFrame(json.loads(body), columns=["frame", "track_id", "label"])
    print(f"camera {camera_id}: {keys[-1]} ({len(df)} boxes)")
    return df


def boxes_per_frame(df):
    return df.groupby("frame").size()


def type_mix(df):
    return df["label"].fillna(OTHER).value_counts(normalize=True)


def psi(ref_mix, cur_mix):
    cats = sorted(set(ref_mix.index) | set(cur_mix.index))
    r = ref_mix.reindex(cats, fill_value=0).clip(lower=EPS)
    c = cur_mix.reindex(cats, fill_value=0).clip(lower=EPS)
    return float(((c - r) * np.log(c / r)).sum())


def verdict(value):
    if value < 0.1:
        return "stable"
    if value < 0.25:
        return "watch"
    return "DRIFT"


def compare(title, ref, cur):
    ks = ks_2samp(boxes_per_frame(ref), boxes_per_frame(cur))
    score = psi(type_mix(ref), type_mix(cur))
    print(f"\n== {title} ==")
    print(f"boxes/frame  mean {boxes_per_frame(ref).mean():.2f} -> {boxes_per_frame(cur).mean():.2f} | KS D={ks.statistic:.3f}, p={ks.pvalue:.4g}")
    print(f"violation share  {ref['label'].notna().mean():.3f} -> {cur['label'].notna().mean():.3f}")
    print("type mix (ref | cur):")
    mix = pd.concat([type_mix(ref).rename("ref"), type_mix(cur).rename("cur")], axis=1).fillna(0)
    print(mix.round(3).to_string())
    print(f"PSI on type mix = {score:.3f} -> {verdict(score)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=int, default=2)
    parser.add_argument("--current", type=int, default=3)
    args = parser.parse_args()

    s3 = boto3.client(
        "s3", endpoint_url=S3_ENDPOINT, aws_access_key_id="test",
        aws_secret_access_key="test", region_name="us-east-1",
    )
    ref = load_bronze(s3, args.reference)
    cur = load_bronze(s3, args.current)

    compare(f"sanity: camera {args.current} vs itself (expect PSI 0, KS D 0)", cur, cur)
    compare(f"camera {args.reference} (reference) vs camera {args.current} (current)", ref, cur)


if __name__ == "__main__":
    main()
