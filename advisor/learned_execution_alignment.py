"""Frozen-policy execution diagnostics and paired case-cluster inference."""

from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4
import numpy as np

VERSION = "combat-execution-alignment-study-v1"
MODES = ("argmax", "sample0", "sample1")
POLICIES = ("candidate", "control")
SEATS = ("p1", "p2")
RIVALS = ("league_s0", "league_anchor")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def content_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def durable_json(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError("immutable_study_artifact:" + str(path))
    temporary = path.with_name(path.name + ".writing_" + uuid4().hex[:8])
    payload = json.dumps(value, indent=2, allow_nan=False).encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def sampling_rng(scope, case, seat, rival, mode):
    if mode not in MODES[1:]:
        raise ValueError("sampling_stream_required")
    identity = f"{VERSION}:{scope}:{case}:{seat}:{rival}:{mode}"
    return np.random.default_rng(int.from_bytes(sha256(identity.encode()).digest()[:8], "big"))


def masked_sample(probabilities, mask, uniform):
    probabilities = np.asarray(probabilities, dtype=np.float64)
    mask = np.asarray(mask, dtype=bool)
    if (probabilities.shape != (35,) or mask.shape != (35,) or not mask.any()
            or not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or np.any(probabilities[~mask] != 0) or abs(probabilities.sum() - 1) > 1e-5
            or not 0 <= uniform < 1):
        raise ValueError("invalid_masked_execution_distribution")
    cumulative = np.cumsum(probabilities / probabilities.sum())
    cumulative[np.flatnonzero(probabilities > 0)[-1]:] = 1.
    action = int(np.searchsorted(cumulative, uniform, side="right"))
    if not mask[action]:
        raise ValueError("sampled_mask_illegal_action")
    return action


def game_slots(cases):
    return [{"scope": case["scope"], "case": case["index"], "scenario_sha256": case["scenario_sha256"],
             "seat": seat, "rival": rival, "mode": mode, "policy": policy}
            for case in cases for seat in SEATS for rival in RIVALS for mode in MODES for policy in POLICIES]


def verify_record(path, slot):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data["slot"] != slot or content_hash(data["record"]) != data["record_sha256"]:
        raise ValueError("study_record_identity_or_hash_mismatch")
    if data["record"]["canonical_scenario_sha256"] != slot["scenario_sha256"]:
        raise ValueError("study_record_case_mismatch")
    return data["record"]


def cluster_analysis(records, *, bootstrap_seed=2026101703, resamples=20000):
    if len(records) != 6144:
        raise ValueError("incomplete_predeclared_study")
    lookup = {}
    for record in records:
        slot = record["study_slot"]
        key = tuple(slot[name] for name in ("scope", "case", "seat", "rival", "mode", "policy"))
        if key in lookup:
            raise ValueError("duplicate_study_observation")
        lookup[key] = record
    output = {}
    for scope in ("train", "validation"):
        cases = sorted({key[1] for key in lookup if key[0] == scope})
        if len(cases) != 128:
            raise ValueError("wrong_independent_case_cluster_count")
        draws = np.random.default_rng(bootstrap_seed).integers(0, 128, (resamples, 128))
        scope_result = {"case_clusters": 128, "strata": {}}
        for stratum in ("all", *RIVALS):
            rivals = RIVALS if stratum == "all" else (stratum,)
            values = {}
            for mode in ("argmax", "sampling"):
                streams = ("argmax",) if mode == "argmax" else MODES[1:]
                for policy in POLICIES:
                    matrix = [[lookup[(scope, case, seat, rival, stream, policy)]["winner"] == "self"
                        and not lookup[(scope, case, seat, rival, stream, policy)]["truncated"]
                        for seat in SEATS for rival in rivals for stream in streams] for case in cases]
                    values[mode + "_" + policy] = np.mean(matrix, axis=1)
            deltas = {mode: values[mode + "_candidate"] - values[mode + "_control"]
                      for mode in ("argmax", "sampling")}
            deltas["interaction"] = deltas["sampling"] - deltas["argmax"]
            estimates = {}
            for name, delta in deltas.items():
                samples = delta[draws].mean(axis=1)
                estimates[name] = {"estimate": float(delta.mean()),
                    "cluster_bootstrap_95": np.quantile(samples, [.025, .975]).tolist(),
                    "cluster_bootstrap_97_5": np.quantile(samples, [.0125, .9875]).tolist()}
            estimates["policy_win_fraction"] = {name: float(value.mean()) for name, value in values.items()}
            scope_result["strata"][stratum] = estimates
        output[scope] = scope_result
    primary = output["validation"]["strata"]["all"]
    anchor = output["validation"]["strata"]["league_anchor"]
    gates = {
        "positive_interaction_95_lower_above_zero": primary["interaction"]["cluster_bootstrap_95"][0] > 0,
        "interaction_point_at_least_5pp": primary["interaction"]["estimate"] >= .05,
        "sampling_noninferiority_95_lower_above_minus_5pp": primary["sampling"]["cluster_bootstrap_95"][0] > -.05,
        "sampling_anchor_simultaneous_lower_above_minus_5pp": anchor["sampling"]["cluster_bootstrap_97_5"][0] > -.05,
        "argmax_anchor_simultaneous_lower_above_minus_5pp": anchor["argmax"]["cluster_bootstrap_97_5"][0] > -.05,
        "sampling_superiority_95_lower_above_zero": primary["sampling"]["cluster_bootstrap_95"][0] > 0,
        "no_censored_native_outcomes": not any(record["truncated"] for record in records),
    }
    return {"schema_version": VERSION, "bootstrap_seed": bootstrap_seed, "resamples": resamples,
            "scopes": output, "gates": gates,
            "alignment_gate_pass": all(gates[name] for name in list(gates)[:4]) and gates["no_censored_native_outcomes"],
            "primary_metric": "native_win_before_fixed_256_decision_cap_not_unbounded_expected_return",
            "anchor_family": "two_validation_execution_mode_deltas_Bonferroni_two_sided_97.5_percent_each",
            "training_seed_count": 1, "sampling_streams_are_repeated_observations": True}
