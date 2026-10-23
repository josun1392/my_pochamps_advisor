"""Frozen-parent KL matched study contracts and paired analysis; no PPO owner."""
from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
import numpy as np
from advisor.learned_execution_alignment import digest
from advisor.learned_parent_anchor import validate_anchor_contract

VERSION = "foundation-parent-policy-anchor-study-v1"
POLICIES = ("parent", "C_96031", "T_96031", "C_96032", "T_96032")
SEEDS = (96031, 96032)
RIVALS = ("champions_heuristic", "tactical_heuristic", "league_anchor")


def matched_configs(configs, parent_sha):
    if set(configs) != set(POLICIES[1:]):
        raise ValueError("four_paired_anchor_arms_required")
    common = None
    for key, config in configs.items():
        c = deepcopy(config)
        if (c.get("envs") != 4 or c.get("cpu_percent") != 50 or c.get("memory_mib") != 12288
                or c.get("device") != "cpu" or c.get("transition_budget_scope") != "trained_rollouts_v1"
                or len(c["experiments"]) != 1):
            raise ValueError("anchor_resource_or_accounting_mismatch")
        e = c["experiments"][0]
        if (e.pop("seed") != int(key[2:]) or e.pop("name") != key or e.get("steps") != 65536
                or e.get("initial_model_id") != parent_sha or e.get("fresh_optimizer") is not False):
            raise ValueError("anchor_initialization_or_budget_mismatch")
        anchor = e.pop("parent_policy_anchor", None)
        if key.startswith("T"):
            anchor = validate_anchor_contract(anchor)
            if anchor["coefficient"] != .01 or anchor["parent_model_sha256"] != parent_sha:
                raise ValueError("anchor_predeclared_coefficient_mismatch")
        elif anchor is not None:
            raise ValueError("anchor_control_must_be_historical_PPO")
        if common is None:
            common = c
        elif c != common:
            raise ValueError("non_anchor_matched_training_difference")
    return {"trained_transitions": 262144, "per_arm": 65536, "seeds": list(SEEDS),
        "initialization_scope": "two_continuations_from_one_parent_not_fresh_seed_replications"}


def verify_plan(path):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if p.get("schema_version") != VERSION or p.get("automatic_restarts") != 0:
        raise ValueError("unrecognized_anchor_study")
    from hashlib import sha256
    for name, expected in p["source_sha256"].items():
        if sha256((Path(p["source_root"])/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
            raise ValueError("anchor_study_source_changed:" + name)
    for name, expected in p["immutable_files"].items():
        if digest(name) != expected:
            raise ValueError("anchor_study_input_changed:" + name)
    configs = {arm["key"]: json.loads(Path(arm["config"]).read_text()) for arm in p["arms"]}
    if matched_configs(configs, p["parent_sha256"]) != p["training_contract"]:
        raise ValueError("anchor_study_contract_changed")
    return p, configs


def game_slots(cases, *, policies=POLICIES):
    slots = []
    for case in cases:
        modes = ["argmax"] + (["sample0", "sample1"] if case.get("sampled") else [])
        for mode in modes:
            rivals = RIVALS if mode == "argmax" else RIVALS[:1]
            for seat in ("p1", "p2"):
                for rival in rivals:
                    for policy in policies:
                        slots.append({"policy": policy, "scope": case["scope"], "case": case["index"],
                            "scenario_sha256": case["scenario_sha256"], "seat": seat,
                            "rival": rival, "mode": mode})
    return slots


def slot_key(slot):
    return tuple(slot[k] for k in ("scope", "case", "seat", "rival", "mode", "policy"))


def analyze(rows, cases, *, resamples=20000, policies=POLICIES, seeds=SEEDS, arm_names=("C", "T")):
    expected = {slot_key(s) for s in game_slots(cases, policies=policies)}
    lookup = {slot_key(r["slot"]): r["record"] for r in rows}
    if len(lookup) != len(rows) or set(lookup) != expected:
        raise ValueError("anchor_evaluation_duplicate_or_missing_slot")
    summaries, differences, retention = [], [], []
    control, treatment = arm_names
    def win(record):
        return float(record["winner"] == "self" and not record["truncated"])
    for mode in ("argmax", "sampling"):
        for scope in ("train", "heldout", "all"):
            keys = [k for k in lookup if (scope == "all" or k[0] == scope)
                    and ((k[4] == "argmax") == (mode == "argmax"))]
            if not keys:
                continue
            for rival in ("all", *RIVALS):
                pool = [k for k in keys if rival == "all" or k[3] == rival]
                if not pool:
                    continue
                clusters = sorted({k[:2] for k in pool})
                values = {}
                for policy in policies:
                    values[policy] = np.asarray([np.mean([win(lookup[k]) for k in pool
                        if k[:2] == cluster and k[-1] == policy]) for cluster in clusters])
                    for seat in ("all", "p1", "p2"):
                        records = [lookup[k] for k in pool if k[-1] == policy and (seat == "all" or k[2] == seat)]
                        counts = Counter("truncated" if r["truncated"] else
                            "win" if r["winner"] == "self" else "loss" if r["winner"] == "opponent" else "draw"
                            for r in records)
                        summaries.append({"mode": mode, "scope": scope, "rival": rival, "seat": seat,
                            "policy": policy, "games": len(records), "win_rate": counts["win"]/len(records),
                            **{k: counts[k] for k in ("win", "loss", "draw", "truncated")}})
                    matched = [(win(lookup[k[:-1]+("parent",)]), win(lookup[k]))
                               for k in pool if k[-1] == policy]
                    counts = Counter(matched)
                    retention.append({"mode": mode, "scope": scope, "rival": rival, "policy": policy,
                        "parent_win_retained": counts[(1., 1.)], "parent_win_lost": counts[(1., 0.)],
                        "new_win": counts[(0., 1.)], "neither_win": counts[(0., 0.)],
                        "interpretation": "paired_terminal_outcomes_not_optimal_action_labels"})
                draws = np.random.default_rng(2026102301).integers(len(clusters), size=(resamples, len(clusters)))
                contrasts = {f"{treatment}_{seed}-{control}_{seed}": values[f"{treatment}_{seed}"]-values[f"{control}_{seed}"] for seed in seeds}
                for policy in policies[1:]:
                    contrasts[policy+"-parent"] = values[policy]-values["parent"]
                contrasts[f"mean_seed({treatment}-{control})"] = np.mean([contrasts[f"{treatment}_{s}-{control}_{s}"] for s in seeds], axis=0)
                for name, delta in contrasts.items():
                    differences.append({"mode": mode, "scope": scope, "rival": rival, "comparison": name,
                        "delta": float(delta.mean()), "case_clusters": len(clusters),
                        "case_cluster_95": np.quantile(delta[draws].mean(1), [.025,.975]).tolist()})
    return {"games": len(rows), "summaries": summaries, "paired_differences": differences,
        "parent_win_retention_and_acquisition": retention, "resamples": resamples,
        "primary": f"argmax heldout all-rival mean_seed({treatment}-{control})",
        "uncertainty": "case_clusters_retain_seats_rivals_streams_and_repetitions_not_seed_population_CI",
        "sampling": "secondary_32clusters_Champions_two_shared_uniform_streams_not_extra_training_seeds",
        "multiplicity": "one_primary_all_other_contrasts_descriptive",
        "no_model_promotion": True}
