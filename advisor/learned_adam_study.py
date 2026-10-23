"""Frozen Adam-only continuation comparison; reuse native owner and statistics."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from advisor import learned_anchor_study as paired
from advisor.learned_execution_alignment import digest

VERSION = "foundation-fresh-versus-restored-adam-study-v1"
SEEDS = (98111, 98519)
POLICIES = ("parent", "A_98111", "B_98111", "A_98519", "B_98519")
RIVALS = paired.RIVALS


def matched_configs(configs, parent_sha):
    if set(configs) != set(POLICIES[1:]):
        raise ValueError("four_paired_Adam_arms_required")
    common = None
    for key, config in configs.items():
        c = deepcopy(config)
        if (c.get("envs") != 4 or c.get("cpu_percent") != 50 or c.get("memory_mib") != 12288
                or c.get("device") != "cpu" or c.get("vector_backend") != "subproc"
                or c.get("transition_budget_scope") != "trained_rollouts_v1"
                or c.get("checkpoint_evaluation_mode") != "disabled_for_frozen_study_v1"
                or c.get("validation_selection_mode") != "diagnostic_fixed_budget_v1"
                or c.get("final_test_cases", 0) or len(c["experiments"]) != 1):
            raise ValueError("Adam_study_resource_or_evaluation_contract")
        e = c["experiments"][0]
        if (e.pop("seed") != int(key[2:]) or e.pop("name") != key or e.get("steps") != 65536
                or e.get("initial_model_id") != parent_sha
                or e.pop("fresh_optimizer") is not key.startswith("B")
                or e.get("parent_policy_anchor") is not None
                or e.get("warmstart_decisions", 0) or e.get("offline") or e.get("transfer_model")):
            raise ValueError("Adam_study_initialization_or_objective_mismatch")
        if common is None:
            common = c
        elif common != c:
            raise ValueError("non_Adam_matched_training_difference")
    return {"trained_transitions": 262144, "per_arm": 65536, "seeds": list(SEEDS),
        "only_variable": "restored_Adam_vs_fresh_moments_variance_and_internal_clock",
        "initialization_scope": "two_stochastic_continuations_of_one_frozen_parent",
        "external_schedule": "same_global_parent_timesteps_constant_learning_rate"}


def verify_plan(path):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if (p.get("schema_version") != VERSION or p.get("automatic_restarts") != 0
            or p.get("evaluation_games") != 5760):
        raise ValueError("unrecognized_Adam_study")
    for name, expected in p["source_sha256"].items():
        if sha256((Path(p["source_root"])/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
            raise ValueError("Adam_study_source_changed:" + name)
    for name, expected in p["immutable_files"].items():
        if digest(name) != expected:
            raise ValueError("Adam_study_input_changed:" + name)
    configs = {arm["key"]: json.loads(Path(arm["config"]).read_text()) for arm in p["arms"]}
    if matched_configs(configs, p["parent_sha256"]) != p["training_contract"]:
        raise ValueError("Adam_study_contract_changed")
    cases = json.loads(Path(p["cases_path"]).read_text())["cases"]
    if (len(cases) != 192 or sum(c["scope"] == "heldout" for c in cases) != 96
            or sum(c["scope"] == "train" for c in cases) != 96
            or len({(c["scope"], c["index"]) for c in cases}) != 192
            or len({c["native_identity"] for c in cases}) != 192
            or any(c.get("sampled") for c in cases)):
        raise ValueError("Adam_study_frozen_panel_mismatch")
    return p, configs


def game_slots(cases):
    if any(c.get("sampled") for c in cases):
        raise ValueError("Adam_study_argmax_only")
    return paired.game_slots(cases, policies=POLICIES)


def analyze(rows, cases, *, resamples=20000):
    result = paired.analyze(rows, cases, resamples=resamples, policies=POLICIES,
        seeds=SEEDS, arm_names=("A", "B"))
    result.update(primary="argmax all-team all-rival mean_seed(B-A)",
        sampling="none_all_games_masked_argmax",
        multiplicity="overall_primary_heldout_required_confirmation_others_descriptive",
        uncertainty="paired_case_clusters_retain_both_seats_rivals_and_continuations_not_training_seed_population_CI")
    return result


def endpoint_clock(key, metadata):
    """Target-KL can reduce Adam updates; never invent missing optimizer steps."""
    clock = metadata["optimizer_steps"]
    initial = 0 if key.startswith("B") else 32768
    if (metadata.get("total_steps") != 1114112 or not initial < clock <= initial + 2048
            or metadata.get("parent_policy_anchor") is not None):
        raise ValueError("Adam_endpoint_clock_or_objective_mismatch")
    return clock


def verify_initial_checkpoint(path, key, plan, config):
    """Check the actual trainer-saved pre-update archive, before any learning."""
    import numpy as np
    import torch
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
    from advisor.learned_policy import LearnedPolicy

    source = LearnedPolicy(plan["parent_path"], config["catalog"], expected_model_id=plan["parent_sha256"])
    child = LearnedPolicy(path, config["catalog"], expected_model_id=digest(path))
    a, b = source.model, child.model
    pa, pb = tensor_digest(a.policy.state_dict()), tensor_digest(b.policy.state_dict())
    if pa != pb or type(a) is not type(b) or type(a.policy) is not type(b.policy):
        raise ValueError("Adam_initial_policy_changed")
    oa, ob = a.policy.optimizer.state_dict(), b.policy.optimizer.state_dict()
    if oa["param_groups"] != ob["param_groups"]:
        raise ValueError("Adam_initial_parameter_group_options_changed")
    fresh = key.startswith("B")
    if fresh:
        if ob["state"] or optimizer_clock(b.policy) != 0:
            raise ValueError("fresh_Adam_not_empty")
    elif optimizer_digest(a.policy) != optimizer_digest(b.policy) or optimizer_clock(b.policy) != 32768:
        raise ValueError("restored_Adam_not_exact")
    if (b.num_timesteps != a.num_timesteps or b.learning_rate != a.learning_rate
            or float(b.lr_schedule(.5)) != float(a.lr_schedule(.5))
            or b.gamma != a.gamma or b.gae_lambda != a.gae_lambda
            or getattr(b, "parent_policy_anchor", None) is not None):
        raise ValueError("Adam_external_schedule_or_objective_changed")
    maximum = dict(logits=0., probabilities=0., value=0.)
    x = torch.as_tensor(np.load(plan["public_probe_features"]))
    masks = np.load(plan["public_probe_masks"])
    a.policy.set_training_mode(False)
    b.policy.set_training_mode(False)
    with torch.no_grad():
        for start in range(0, len(x), 32):
            batch, mask = x[start:start+32], masks[start:start+32]
            va = a.policy(batch, action_masks=mask, deterministic=True)[1]
            da = a.policy.action_dist.distribution
            la, pr = da.logits.clone(), da.probs.clone()
            vb = b.policy(batch, action_masks=mask, deterministic=True)[1]
            db = b.policy.action_dist.distribution
            for name, delta in (("logits", (la-db.logits).abs().max()),
                                ("probabilities", (pr-db.probs).abs().max()),
                                ("value", (va-vb).abs().max())):
                maximum[name] = max(maximum[name], float(delta))
    if any(maximum.values()):
        raise ValueError("Adam_initial_output_mismatch")
    return {"parameters_sha256": pb, "Adam_sha256": optimizer_digest(b.policy),
        "Adam_clock": optimizer_clock(b.policy), "fresh": fresh, "param_groups_identical": True,
        "global_timesteps": b.num_timesteps, "public_views": len(x),
        "maximum_absolute_output_difference": maximum, "source_SHA": plan["parent_sha256"],
        "checkpoint_SHA": digest(path), "no_new_native_evaluation": True}
