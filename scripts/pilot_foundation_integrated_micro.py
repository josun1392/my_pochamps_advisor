"""Fail-closed public teacher coverage gate, no native or learning on abstention.

This coordinator intentionally has no old checkpoint-search label import. A
conditional surrogate is not promoted to a public native teacher. The optional
trainer consumer is tested separately; a failed gate cannot launch PPO/eval.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
from hashlib import sha256
import json
from time import perf_counter

from advisor.learned_action_search_teacher import PublicInformationSearchTeacher, PUBLIC_VERSION
from advisor.learning_resources import atomic_json


class MicroLedger:
    """One append-only reservation ledger; failures do not refund an attempt.

    Single coordinator only. No automatic restart or parallel writers. Each
    reservation is fsynced before the corresponding irreversible action.
    """
    LIMITS = {"TRAIN_start": 1024, "transition": 16384, "Adam": 256, "evaluation_start": 256}

    def __init__(self, path):
        self.path = Path(path)
        self.counts = Counter()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self.counts[row["budget"]] += row["count"]
            if any(self.counts[k] > v for k, v in self.LIMITS.items()):
                raise ValueError("existing_micro_budget_violation")

    def reserve(self, kind, count):
        import os
        budget = "Adam" if kind.endswith("_Adam") else kind
        if budget not in self.LIMITS or type(count) is not int or count < 1:
            raise ValueError("invalid_micro_reservation")
        if self.counts[budget] + count > self.LIMITS[budget]:
            raise ValueError("micro_budget_exhausted")
        row = {"ordinal": sum(self.counts.values()), "kind": kind, "budget": budget, "count": count}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.counts[budget] += count


def coverage(public_views, teacher, *, policy_id, learning_step):
    from advisor.learned_action_search_teacher import validate_public_teacher_target
    reasons, diagnostics = Counter(), Counter()
    identities = set()
    supported = 0
    for view in public_views:
        identity = (view["episode_id"], view["revision"], view["side"])
        if identity in identities:
            raise ValueError("duplicate_teacher_coverage_decision")
        identities.add(identity)
        result = teacher.assess(view, policy_id=policy_id, learning_step=learning_step)
        target = validate_public_teacher_target(result, view, policy_id=policy_id, learning_step=learning_step)
        supported += target is not None
        reasons[result.get("reason", "supported")] += 1
        detail = result.get("diagnostic", {})
        diagnostics["surrogate_compared_decisions"] += detail.get("compared_candidates", 0) >= 2
        diagnostics["unknown_response_availability"] += detail.get("unknown_response_availability", 0)
    return {"schema_version": PUBLIC_VERSION, "decisions": len(identities), "supported_targets": supported,
        "coverage_fraction": supported / len(identities) if identities else 0.,
        "abstention_reasons": dict(reasons), "diagnostics": dict(diagnostics),
        "status": "PUBLIC_TEACHER_COVERAGE_BLOCKED" if not supported else "REQUIRES_PRELEARNING_NATIVE_GATE",
        "learning_allowed": False, "native_starts": 0, "new_transitions": 0, "optimizer_updates": 0,
        "scope": "preserved_TRAIN_views_only_not_new_native_evidence_or_independent_evaluation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("coverage_receipt_already_exists_do_not_duplicate")
    started = perf_counter()
    config = json.loads(args.contract.read_text(encoding="utf-8"))
    if (config.get("schema_version") != "foundation-public-teacher-coverage-plan-v1"
            or config.get("source_purpose") != "preserved_TRAIN_only"
            or config.get("row_rule") != "all_public_before_in_file_order"
            or config.get("native_starts") != 0 or config.get("optimizer_updates") != 0):
        raise ValueError("unfrozen_teacher_coverage_contract")
    path = Path(config["public_decisions"])
    payload = path.read_bytes()
    digest = sha256(payload).hexdigest()
    if digest != config["public_decisions_SHA256"]:
        raise ValueError("public_teacher_source_changed")
    # Do not use selected actions, outcome, native state or GAE as teacher input.
    views = [json.loads(line)["public_before"] for line in payload.decode("utf-8").splitlines()]
    if not 1 <= len(views) <= 2048:
        raise ValueError("bounded_preserved_coverage_required")
    teacher = PublicInformationSearchTeacher(catalog=config["catalog"], checkout=config["checkout"])
    result = coverage(views, teacher, policy_id=config["policy_id"], learning_step=config["learning_step"])
    result.update(source_SHA256=digest, contract_SHA256=sha256(args.contract.read_bytes()).hexdigest(),
        wall_seconds=perf_counter()-started)
    atomic_json(args.output, result)
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
