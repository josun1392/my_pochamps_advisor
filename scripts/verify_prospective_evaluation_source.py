"""Verify a separately prepared source seal; no battle or model execution."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from fractions import Fraction
import json
from advisor.learned_prospective_evaluation import ProspectiveEvaluationSource


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--readiness-sha256", required=True)
    args = parser.parse_args()
    source = ProspectiveEvaluationSource(args.manifest, args.sha256,
        readiness=args.readiness, readiness_sha256=args.readiness_sha256)
    source.verify_policy_bindings()
    points = list(source.points())
    if (len(points) != 1152 or len({p["point_key"] for p in points}) != 1152
            or len({p["case_id"] for p in points}) != 96
            or sum((p["mass"] for p in points), Fraction()) != 1):
        raise ValueError("prospective_finite_measure_mismatch")
    print(json.dumps({"status": "SEALED_SOURCE_CONTRACT_VERIFIED", "manifest_sha256": source.sha256,
        "cases": 96, "points_per_policy": len(points), "mass_sum": "1", "native_starts": 0,
        "model_forwards": 0, "terminal_evaluation_authorized": False}))


if __name__ == "__main__":
    main()
