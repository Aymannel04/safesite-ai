"""Print a drift report between two cameras (logic lives in src/drift.py).

Run from the project root:  python3 -m scripts.drift_report --reference 2 --current 3
"""
import argparse

from src import drift


def print_report(title, result):
    print(f"\n== {title} ==")
    print(f"boxes/frame  mean {result['ref_mean_boxes']:.2f} -> {result['cur_mean_boxes']:.2f} | KS D={result['ks_d']:.3f}, p={result['ks_p']:.4g}")
    print(f"violation share  {result['ref_violation_share']:.3f} -> {result['cur_violation_share']:.3f}")
    print("type mix (ref | cur):")
    print(result["mix"].round(3).to_string())
    print(f"PSI on type mix = {result['psi']:.3f} -> {result['verdict']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=int, default=2)
    parser.add_argument("--current", type=int, default=3)
    args = parser.parse_args()

    s3 = drift.get_s3_client()
    ref, ref_key = drift.load_bronze(args.reference, s3)
    cur, cur_key = drift.load_bronze(args.current, s3)
    print(f"camera {args.reference}: {ref_key} ({len(ref)} boxes)")
    print(f"camera {args.current}: {cur_key} ({len(cur)} boxes)")

    print_report(f"sanity: camera {args.current} vs itself (expect PSI 0, KS D 0)", drift.compare(cur, cur))
    print_report(f"camera {args.reference} (reference) vs camera {args.current} (current)", drift.compare(ref, cur))


if __name__ == "__main__":
    main()
