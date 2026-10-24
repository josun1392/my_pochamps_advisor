"""One frozen temperature schedule comparison using existing native study owners."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from advisor import learned_anchor_study as paired
from advisor import learned_adam_study as adam
from advisor.learned_execution_alignment import digest
from advisor.learned_temperature import temperature_contract, validate_temperature, at_progress

VERSION = "foundation-masked-softmax-temperature-schedule-controlled-experiment-v1"
SEEDS = (110021, 111037)
POLICIES = ("parent", "A_110021", "B_110021", "A_111037", "B_111037")
RIVALS = paired.RIVALS
EVALUATION_SECONDS = 5400
OVERALL_SECONDS = 10800


def matched_configs(configs, parent_sha):
    if set(configs) != set(POLICIES[1:]):
        raise ValueError("temperature_four_paired_arms_required")
    common = None
    for key, config in configs.items():
        c = deepcopy(config)
        if (c.get("envs") != 4 or c.get("cpu_percent") != 50 or c.get("memory_mib") != 12288
                or c.get("device") != "cpu" or c.get("vector_backend") != "subproc"
                or c.get("transition_budget_scope") != "trained_rollouts_v1"
                or c.get("checkpoint_evaluation_mode") != "disabled_for_frozen_study_v1"
                or c.get("validation_selection_mode") != "diagnostic_fixed_budget_v1"
                or c.get("final_test_cases", 0) or c.get("checkpoint_steps") != 16384
                or len(c["experiments"]) != 1):
            raise ValueError("temperature_resource_or_evaluation_mismatch")
        e = c["experiments"][0]
        if (e.pop("seed") != int(key[2:]) or e.pop("name") != key or e.get("steps") != 65536
                or e.get("initial_model_id") != parent_sha or e.get("fresh_optimizer") is not False
                or e.pop("masked_temperature") != temperature_contract(key.startswith("B"))
                or e.get("parent_policy_anchor") is not None or e.get("opponent_schedule") is not None
                or e.get("warmstart_decisions", 0) or e.get("offline") or e.get("transfer_model")):
            raise ValueError("temperature_initialization_or_schedule_mismatch")
        if common is None:
            common = c
        elif common != c:
            raise ValueError("non_temperature_matched_difference")
    return {"trained_transitions": 262144, "per_arm": 65536, "seeds": list(SEEDS),
        "only_variable": "masked_training_softmax_temperature_schedule",
        "initialization": "same_Foundation_weights_and_restored_Adam_two_continuation_repetitions",
        "A": temperature_contract(False), "B": temperature_contract(True),
        "evaluation": "temperature1_masked_argmax_same_actual_cases_seats_rivals"}


def verify_plan(path):
    p = json.loads(Path(path).read_text(encoding="utf8"))
    if (p.get("schema_version") != VERSION or p.get("automatic_restarts") != 0
            or p.get("evaluation_games") != 5760 or p.get("training_seconds_ceiling") != 3600
            or p.get("evaluation_seconds_ceiling") != EVALUATION_SECONDS
            or p.get("overall_seconds_ceiling") != OVERALL_SECONDS):
        raise ValueError("invalid_temperature_study")
    for name, expected in p["source_sha256"].items():
        if sha256((Path(p["source_root"])/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
            raise ValueError("temperature_source_changed:"+name)
    for name, expected in p["immutable_files"].items():
        if digest(name) != expected:
            raise ValueError("temperature_input_changed:"+name)
    configs = {a["key"]: json.loads(Path(a["config"]).read_text()) for a in p["arms"]}
    if matched_configs(configs, p["parent_sha256"]) != p["training_contract"]:
        raise ValueError("temperature_study_config_changed")
    cases = json.loads(Path(p["cases_path"]).read_text())["cases"]
    if (len(cases) != 192 or sum(c["scope"] == "heldout" for c in cases) != 96
            or sum(c["scope"] == "train" for c in cases) != 96
            or len({c["native_identity"] for c in cases}) != 192
            or any(c.get("sampled") for c in cases)):
        raise ValueError("temperature_frozen_evaluation_mismatch")
    return p, configs


def game_slots(cases):
    if any(c.get("sampled") for c in cases):
        raise ValueError("temperature_argmax_only")
    return paired.game_slots(cases, policies=POLICIES)


def analyze(rows, cases, *, resamples=20000):
    result = paired.analyze(rows, cases, resamples=resamples, policies=POLICIES,
        seeds=SEEDS, arm_names=("A", "B"))
    result.update(primary="argmax heldout all-rival mean_seed(B-A)",
        sampling="none_all_games_masked_argmax_temperature1",
        scope_train_label="secondary_in_domain_teams_excluded_from_learner256_not_training_inputs",
        uncertainty="paired_case_clusters_keep_seats_rivals_and_repetitions_not_seed_population_CI")
    return result


def endpoint_clock(key, metadata):
    adam.endpoint_clock("A_"+key[2:], metadata)
    if (metadata.get("masked_temperature") != temperature_contract(key.startswith("B"))
            or metadata.get("temperature_state", {}).get("trained_transitions") != 65536
            or metadata["temperature_state"].get("inference_temperature") != 1):
        raise ValueError("temperature_final_progress_or_inference_mismatch")
    return metadata["optimizer_steps"]


def verify_initial_checkpoint(path, key, plan, config):
    import numpy as np
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
    from advisor.learned_temperature import TemperatureFoundationPPO, distribution_temperature
    source = LearnedPolicy(plan["parent_path"], config["catalog"], expected_model_id=plan["parent_sha256"])
    child = LearnedPolicy(path, config["catalog"], expected_model_id=digest(path))
    a, b = source.model, child.model
    if (type(b) is not TemperatureFoundationPPO or type(a.policy) is not type(b.policy)
            or tensor_digest(a.policy.state_dict()) != tensor_digest(b.policy.state_dict())
            or optimizer_digest(a.policy) != optimizer_digest(b.policy) or optimizer_clock(b.policy) != 32768
            or b.temperature_trained != 0 or b.masked_temperature != temperature_contract(key.startswith("B"))
            or b.num_timesteps != a.num_timesteps or b.gamma != a.gamma or b.gae_lambda != a.gae_lambda
            or float(b.lr_schedule(.5)) != float(a.lr_schedule(.5))):
        raise ValueError("temperature_initial_model_Adam_or_schedule_mismatch")
    maximum = dict(logits=0., probabilities=0., value=0.)
    x = torch.as_tensor(np.load(plan["public_probe_features"]))
    masks = np.load(plan["public_probe_masks"])
    a.policy.set_training_mode(False); b.policy.set_training_mode(False)
    with torch.no_grad():
        for start in range(0, len(x), 32):
            xx, mm = x[start:start+32], masks[start:start+32]
            va = a.policy(xx, action_masks=mm, deterministic=True)[1]
            da = a.policy.action_dist.distribution
            lp, pr = da.logits.clone(), da.probs.clone()
            vb = b.policy(xx, action_masks=mm, deterministic=True)[1]
            db = b.policy.action_dist.distribution
            for name, delta in (("logits", (lp-db.logits).abs().max()),
                                ("probabilities", (pr-db.probs).abs().max()), ("value", (va-vb).abs().max())):
                maximum[name] = max(maximum[name], float(delta))
    if any(maximum.values()):
        raise ValueError("temperature_initial_T1_output_mismatch")
    hyper = {"n_steps":128,"batch_size":128,"n_epochs":4,"n_envs":4,"gamma":1.,"gae_lambda":.95,
             "learning_rate":5e-5,"ent_coef":.01,"vf_coef":.5,"max_grad_norm":.5,"target_kl":.03,"zero_avoiding_beta":.001}
    if any(getattr(b,k) != v or getattr(a,k) != v for k,v in hyper.items()):
        raise ValueError("temperature_original_PPO_hyperparameter_changed")
    hot = {"temperature":1.5,"public_views":len(x),"argmax_changes":0,"value_max_difference":0.}
    with torch.no_grad():
        for start in range(0,len(x),32):
            xx,mm=x[start:start+32],masks[start:start+32]
            action,value,_=b.policy(xx,action_masks=mm,deterministic=True)
            with distribution_temperature(b.policy,1.5):
                hotaction,hotvalue,_=b.policy(xx,action_masks=mm,deterministic=True)
            hot['argmax_changes']+=int((action!=hotaction).sum())
            hot['value_max_difference']=max(hot['value_max_difference'],float((value-hotvalue).abs().max()))
    if hot['argmax_changes'] or hot['value_max_difference']:
        raise ValueError('temperature_initial_greedy_or_value_changed')
    return {"parameters_sha256": tensor_digest(b.policy.state_dict()), "Adam_sha256": optimizer_digest(b.policy),
        "Adam_clock": optimizer_clock(b.policy), "global_timesteps": b.num_timesteps,
        "public_views": len(x), "maximum_absolute_T1_output_difference": maximum,
        "actual_PPO_hyperparameters":hyper,"T15_vs_T1_proof":hot,
        "contract": b.masked_temperature, "initial_training_temperature": at_progress(b.masked_temperature, 0),
        "initial_inference_temperature": 1., "source_SHA": plan["parent_sha256"], "checkpoint_SHA": digest(path)}


def verify_sampling_checkpoint(path, config, trained):
    metadata = json.loads(Path(path).with_suffix('.json').read_text())
    contract = config['experiments'][0]['masked_temperature']
    if metadata['masked_temperature'] != contract or metadata['temperature_state']['trained_transitions'] != trained:
        raise ValueError('temperature_checkpoint_schedule_or_progress_mismatch')
    from advisor.learned_two_group_study import verify_sampling_checkpoint as verify_opponents
    return {**verify_opponents(path, config, trained), 'temperature': metadata['temperature_state']}


def evaluation_native_ids(cases):
    from advisor.learned_two_group_study import evaluation_native_ids as both_seats
    return both_seats(cases)


def evaluation_observer(output, slot):
    from advisor.learned_two_group_study import evaluation_observer as retry_guard
    return retry_guard(output, slot)
