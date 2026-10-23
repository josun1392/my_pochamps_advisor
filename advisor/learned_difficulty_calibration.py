"""Train-only frozen-parent difficulty measurement; no optimizer or curriculum.

Sampling, native retries and paired inference stay separate from policy inputs.
Unknown difficulty is a valid result: three tiers are never forced.
"""
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from advisor.learned_execution_alignment import content_hash, digest, masked_sample
from advisor.learned_training_operations import ProgressRetryMonitor

VERSION = "foundation-train-only-difficulty-calibration-v1"
RIVALS = ("max_power", "champions_heuristic", "tactical_heuristic", "previous",
          "historical", "league_s0", "league_anchor")
SEATS = ("p1", "p2")
ANALYSIS = {
    "case_cluster_unit": "initial_case_all_seats_and_rivals_retained_together",
    "bootstrap_seed": 2026102317, "resamples": 20000,
    "family": "all_21_pairwise_opponent_differences_Bonferroni_95_percent",
    "minimum_boundary_point_difference": .05,
    "tier_rule": "all_adjacent_cross_tier_pairs_positive_simultaneous_lower_bound_and_5pp_point_gap",
    "partition_selection": "sorted_parent_win_fraction_maximize_smallest_boundary_gap_no_forced_tiers",
    "truncation": "separate_censored_not_draw_or_loss_no_tiers_if_any",
    "use": "training_only_opponent_difficulty_not_generalization_or_final_selection",
}


def game_slots(cases):
    if len(cases) != 128 or len({r["index"] for r in cases}) != 128:
        raise ValueError("exact_128_distinct_calibration_cases_required")
    return [{"case": c["index"], "scenario_sha256": c["scenario_SHA256"],
             "seat": seat, "rival": rival}
            for c in cases for rival in RIVALS for seat in SEATS]


def sample_seed(slot):
    return int.from_bytes(sha256((VERSION + ":" + content_hash(slot)).encode()).digest()[:8], "big")


class PublicSampler:
    """Own public inference only, reproducible sampling without model updates."""
    def __init__(self, infer, slot):
        self.infer, self.seed = infer, sample_seed(slot)
        self.rng = np.random.default_rng(self.seed)
        self.pending = []
        self.ordinal = 0

    def __call__(self, view):
        proof = dict(self.infer(view))
        uniform = float(self.rng.random())
        action = masked_sample(proof["action_probabilities"], view["action_mask"], uniform)
        proof.update(action_index=action, native_choice=view["choices"][action])
        self.pending.append({"ordinal": self.ordinal, "sampling_seed": self.seed,
            "uniform": uniform, "revision": view["revision"], "action": action,
            "native_choice": view["choices"][action], "mask": list(view["action_mask"]),
            "probabilities": proof["action_probabilities"], "value": proof["discounted_return_estimate"]})
        self.ordinal += 1
        return proof


class PublicRetryAudit:
    """Reuse the native-progress guard, including wait steps. Never repair a choice."""
    def __init__(self, case):
        self.case = case
        self.monitor = ProgressRetryMonitor()
        self.steps = self.rejections = 0

    def observe(self, event):
        self.steps += 1
        before, result = event["before"], event["result"]
        identity = next(iter(before.values()))["episode_id"]
        for side, action in event["actions"].items():
            if type(action) is not int or not 0 <= action < 35 or not before[side]["action_mask"][action]:
                raise ValueError("calibration_mask_illegal_choice")
        records = []
        if result["action_rejected"]:
            self.rejections += 1
            records = [{"episode_id": identity, "episode_case": self.case,
                "revision_before": next(iter(before.values()))["revision"],
                "native_decisions": result["decisions"],
                "before": {side: {"action_index": event["actions"][side],
                                   "action_mask": view["action_mask"]} for side, view in before.items()}}]
        progress = [{"episode_identity": {"case_index": self.case},
                     "native_progress": {"episode_id": identity, "native_decisions": result["decisions"]}}]
        # Immediate unresolved-request guard. The owner separately checks rate
        # across games in 512-attempt blocks, not a denominator of one per call.
        alerts = self.monitor.inspect(records, [], 512, progress=progress)
        if alerts:
            raise ValueError("calibration_native_progress_alert:" + json.dumps(alerts))
        return self.monitor.statistics()


class AttemptRateGuard:
    def __init__(self):
        self.attempts = self.rejections = 0

    def observe(self, rejected):
        self.attempts += 1
        self.rejections += int(rejected)
        if self.attempts == 512:
            if self.rejections > .01 * 512:
                raise ValueError("calibration_interval_retry_rate_above_one_percent")
            self.attempts = self.rejections = 0


def audit_receipts(output, slots, plan_sha256):
    """Never replay an uncertain started game; all durable bindings must match."""
    out = Path(output)
    ledger = out / "game_ledger.jsonl"
    events = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    if len(events) % 2:
        raise ValueError("uncertain_started_game_no_automatic_reexecution")
    rows = []
    for i in range(len(events) // 2):
        a, b = events[2*i:2*i+2]
        path = out / "receipts" / f"game_{i:04d}.json"
        if (a != {"phase": "game_started", "index": i, "slot_sha256": content_hash(slots[i])}
                or b.get("phase") != "game_committed" or b.get("index") != i
                or b.get("receipt_sha256") != digest(path)):
            raise ValueError("calibration_ledger_corrupt")
        row = json.loads(path.read_text(encoding="utf-8"))
        if (row["slot"] != slots[i] or row["plan_sha256"] != plan_sha256
                or content_hash(row["record"]) != row["record_sha256"]
                or digest(row["decisions_path"]) != row["decisions_sha256"]):
            raise ValueError("calibration_receipt_corrupt")
        rows.append(row)
    if len(list((out / "receipts").glob("game_*.json"))) != len(rows):
        raise ValueError("calibration_receipt_outside_ledger")
    return rows


def analyze(rows, cases):
    slots = game_slots(cases)
    if len(rows) != len(slots) or [r["slot"] for r in rows] != slots:
        raise ValueError("incomplete_or_duplicate_calibration")
    lookup = {(r["slot"]["case"], r["slot"]["seat"], r["slot"]["rival"]): r["record"] for r in rows}
    summary, matrix = {}, []
    for rival in RIVALS:
        records = [lookup[(c["index"], s, rival)] for c in cases for s in SEATS]
        counts = Counter("truncated" if r["truncated"] else "win" if r["winner"] == "self"
                         else "loss" if r["winner"] == "opponent" else "draw" for r in records)
        summary[rival] = {k: counts[k] for k in ("win", "loss", "draw", "truncated")}
        summary[rival]["games"] = len(records)
        summary[rival]["win_fraction_before_cap"] = counts["win"] / len(records)
        summary[rival]["native_rejections"] = sum(r["native_choice_rejections"] for r in records)
        matrix.append([np.mean([lookup[(c["index"], s, rival)]["winner"] == "self"
                               and not lookup[(c["index"], s, rival)]["truncated"] for s in SEATS]) for c in cases])
    matrix = np.asarray(matrix)
    draws = np.random.default_rng(ANALYSIS["bootstrap_seed"]).integers(0, len(cases), (ANALYSIS["resamples"], len(cases)))
    bootstrap = matrix[:, draws].mean(axis=2)
    alpha = .05 / 21 / 2
    pairs, intervals = [], {}
    for a, b in combinations(range(7), 2):
        point = float(matrix[a].mean() - matrix[b].mean())
        low, high = np.quantile(bootstrap[a] - bootstrap[b], [alpha, 1-alpha]).tolist()
        intervals[(a, b)], intervals[(b, a)] = (point, low, high), (-point, -high, -low)
        pairs.append({"a": RIVALS[a], "b": RIVALS[b], "a_minus_b": point,
                      "case_cluster_95": np.quantile(bootstrap[a]-bootstrap[b], [.025, .975]).tolist(),
                      "simultaneous_family95": [low, high]})
    order = sorted(range(7), key=lambda i: (-matrix[i].mean(), i))
    candidates = []
    no_truncation = not any(v["truncated"] for v in summary.values())
    for i in range(1, 6):
        for j in range(i+1, 7):
            groups = (order[:i], order[i:j], order[j:])
            boundaries = [intervals[(a,b)] for left,right in zip(groups, groups[1:]) for a in left for b in right]
            if no_truncation and all(p >= .05 and lo > 0 for p,lo,hi in boundaries):
                candidates.append((min(p for p,lo,hi in boundaries), groups))
    candidates.sort(key=lambda x: -x[0])
    tiers = ({name: [RIVALS[i] for i in group] for name,group in zip(("easy","middle","strong"), candidates[0][1])}
             if candidates else None)
    return {"schema_version": VERSION, "analysis_contract": ANALYSIS, "games": len(rows),
            "independent_case_clusters": len(cases), "summary": summary, "paired": pairs,
            "three_tiers_supported": tiers is not None, "tiers": tiers,
            "difficulty_order_descriptive_only": [RIVALS[i] for i in order],
            "new_PPO_transitions": 0, "no_model_promotion": True,
            "limits": "one_frozen_parent_one_sampling_stream_per_seat_training256_only_not_seed_population_or_generalization"}
