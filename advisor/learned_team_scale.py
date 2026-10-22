"""Matched team-population study contracts; no policy or optimizer ownership."""
from hashlib import sha256
import json
from pathlib import Path

VERSION = "foundation-matched-team-scale-study-v1"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def require_matched_configs(configs, parent_sha256):
    """Only population, repetition seed and descriptive arm name may differ."""
    if len(configs) != 4:
        raise ValueError("two_populations_two_continuations_required")
    canonical = None
    seeds = {}
    for arm, config in configs:
        population = arm[0]
        if population not in ("A", "B"):
            raise ValueError("invalid_team_scale_arm")
        if len(config["experiments"]) != 1:
            raise ValueError("single_experiment_per_owned_run_required")
        value = json.loads(json.dumps(config))
        experiment = value["experiments"][0]
        seed = experiment.pop("seed")
        experiment.pop("name")
        if experiment.get("initial_model_id") != parent_sha256 or experiment.get("fresh_optimizer") is not False:
            raise ValueError("matched_parent_and_restored_Adam_required")
        if value.get("envs") != 4 or value.get("cpu_percent") != 50 or value.get("memory_mib") != 12288:
            raise ValueError("matched_safe_resources_required")
        if experiment.get("steps") != 262144 or value.get("transition_budget_scope") != "trained_rollouts_v1":
            raise ValueError("exact_trained_transition_budget_required")
        value.pop("training_subset")
        value.pop("training_subset_sha256")
        if canonical is None:
            canonical = value
        if value != canonical:
            raise ValueError("non_population_training_difference")
        seeds.setdefault(population, []).append(seed)
    if len(set(seeds.get("A", []))) != 2 or sorted(seeds.get("A", [])) != sorted(seeds.get("B", [])):
        raise ValueError("paired_distinct_continuation_seeds_required")
    return {"trained_transitions": 1048576, "continuation_seeds": sorted(seeds["A"]),
            "seed_scope": "two_continuations_of_one_parent_not_fresh_initialization_replications"}


def verify_plan(path):
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    if plan.get("schema_version") != VERSION or plan.get("automatic_restarts") != 0:
        raise ValueError("unverified_study_or_restart_contract")
    root = Path(plan["source_root"])
    for name, expected in plan["source_sha256"].items():
        actual = sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError("study_source_changed:" + name)
    for name, expected in plan["immutable_files"].items():
        if digest(name) != expected:
            raise ValueError("study_artifact_changed:" + name)
    configs = [(arm["key"], json.loads(Path(arm["config"]).read_text())) for arm in plan["arms"]]
    require_matched_configs(configs, plan["parent_sha256"])
    return plan, dict(configs)


def checkpoint_alerts(metadata, state, previous):
    """Operational alarms only, never win-rate selection or reward shaping."""
    ppo = metadata.get("training_metrics", {}).get("ppo", {})
    alerts = []
    if ppo.get("train/approx_kl", 0) > .1:
        alerts.append("KL_above_0.1")
    if previous is not None and state["trained_rollout_transitions"] < previous["trained"]:
        alerts.append("trained_counter_regression")
    ended = metadata.get("episode_outcomes_this_checkpoint", {})
    if sum(ended.values()) and ended.get("truncated", 0) / sum(ended.values()) > .01:
        alerts.append("interval_truncations_above_1pct")
    return alerts
