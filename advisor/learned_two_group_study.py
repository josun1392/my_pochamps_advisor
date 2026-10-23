"""One predeclared curriculum experiment; reuse native owner and paired statistics."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from advisor import learned_anchor_study as paired
from advisor import learned_adam_study as adam
from advisor.learned_execution_alignment import digest, content_hash
from advisor.learned_opponent_curriculum import BASELINE, COMPETITIVE, stage_selection, two_group_schedule

VERSION = "foundation-two-group-opponent-curriculum-matched-v1"
SEEDS = (99221, 99222)
POLICIES = ("parent", "A_99221", "B_99221", "A_99222", "B_99222")
RIVALS = ("max_power", *COMPETITIVE)
EVALUATION_SECONDS = 5400
OVERALL_SECONDS = 9000


def matched_configs(configs, parent_sha):
    if set(configs) != set(POLICIES[1:]):
        raise ValueError("two_group_four_paired_arms_required")
    common = None
    for key, config in configs.items():
        c = deepcopy(config)
        if (c.get("envs") != 4 or c.get("cpu_percent") != 50 or c.get("memory_mib") != 12288
                or c.get("device") != "cpu" or c.get("vector_backend") != "subproc"
                or c.get("transition_budget_scope") != "trained_rollouts_v1"
                or c.get("checkpoint_evaluation_mode") != "disabled_for_frozen_study_v1"
                or c.get("validation_selection_mode") != "diagnostic_fixed_budget_v1"
                or c.get("final_test_cases", 0) or not c.get("collect_opponent_selections")
                or len(c["experiments"]) != 1 or c.get("checkpoint_steps") != 32768):
            raise ValueError("two_group_resources_or_fixed_budget_mismatch")
        e = c["experiments"][0]
        schedule = e.pop("opponent_schedule", None)
        if (e.pop("seed") != int(key[2:]) or e.pop("name") != key or e.get("steps") != 65536
                or e.get("initial_model_id") != parent_sha or e.get("fresh_optimizer") is not False
                or e.get("parent_policy_anchor") is not None or e.get("warmstart_decisions", 0)
                or e.get("offline") or e.get("transfer_model") or tuple(e.get("opponents", [])) != BASELINE
                or schedule != (two_group_schedule() if key.startswith("B") else None)):
            raise ValueError("two_group_initialization_or_sampler_mismatch")
        if common is None:
            common = c
        elif c != common:
            raise ValueError("non_opponent_schedule_training_difference")
    return {"trained_transitions":262144, "per_arm":65536, "seeds":list(SEEDS),
        "only_variable":"episode_opponent_slot_probabilities_and_predeclared_schedule",
        "initialization":"same_Foundation_parameters_and_exact_restored_Adam_two_stochastic_continuations",
        "A":"case_index_mod_original10_slots", "B":two_group_schedule()}


def game_slots(cases):
    for case in cases:
        rivals = case.get("rivals", [])
        if (case.get("sampled") or len(rivals) != 3 or len(set(rivals)) != 3
                or "max_power" not in rivals or set(rivals)-set(RIVALS)):
            raise ValueError("two_group_three_frozen_rivals_per_case_required")
    return paired.game_slots(cases, policies=POLICIES, rivals=RIVALS)


def verify_plan(path):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if (p.get("schema_version") != VERSION or p.get("launch_contract_frozen") is not True or p.get("automatic_restarts") != 0
            or p.get("evaluation_games") != 5760 or p.get("training_seconds_ceiling") != 3600
            or p.get("evaluation_seconds_ceiling") != EVALUATION_SECONDS
            or p.get("overall_seconds_ceiling") != OVERALL_SECONDS):
        raise ValueError("unrecognized_two_group_study")
    for name, expected in p["source_sha256"].items():
        if sha256((Path(p["source_root"])/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
            raise ValueError("two_group_source_changed:"+name)
    for name, expected in p["immutable_files"].items():
        if digest(name) != expected:
            raise ValueError("two_group_input_changed:"+name)
    import subprocess
    from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
    if (subprocess.check_output(["git","rev-parse","HEAD"],cwd=p["source_root"],text=True).strip()!=p["source_commit"]
            or subprocess.check_output(["git","rev-parse","HEAD"],cwd=p["checkout"],text=True).strip()!=SHOWDOWN_COMMIT
            or p["engine_commit"]!=SHOWDOWN_COMMIT or p["format"]!=FORMAT_ID):
        raise ValueError("two_group_source_or_native_pin_mismatch")
    configs = {a["key"]:json.loads(Path(a["config"]).read_text()) for a in p["arms"]}
    if matched_configs(configs,p["parent_sha256"]) != p["training_contract"]:
        raise ValueError("two_group_training_contract_changed")
    cases = json.loads(Path(p["cases_path"]).read_text())["cases"]
    if (len(cases) != 192 or len({r["native_identity"] for r in cases}) != 192
            or len({r["index"] for r in cases}) != 192
            or any(sum(c["scope"]==s for c in cases)!=96 for s in ("train","heldout"))
            or len(game_slots(cases)) != 5760):
        raise ValueError("two_group_frozen_panel_mismatch")
    for scope in ("train","heldout"):
        counts = Counter(r for c in cases if c["scope"]==scope for r in c["rivals"])
        if counts != Counter({"max_power":96, **dict.fromkeys(COMPETITIVE,32)}):
            raise ValueError("two_group_evaluation_opponent_balance_mismatch")
    return p,configs


def evaluation_native_ids(cases):
    from scripts.evaluate_showdown_policy import seat_scenario
    from advisor.learned_encoder import fingerprint
    values=set()
    for row in cases:
        for seat in ("p1","p2"):
            c=seat_scenario(row["scenario"],seat)
            values.add(content_hash({"teams":{k:fingerprint(v) for k,v in c["teams"].items()},
                                     "preview":c["preview"],"seed":c["seed"]}))
    return values


def verify_initial_checkpoint(path, key, plan, config):
    # Adam study's restored branch checks same archive tensors, optimizer moments,
    # internal clock, external schedule and exact public logits/probs/values.
    return adam.verify_initial_checkpoint(path,"A_"+key[2:],plan,config)


def endpoint_clock(key, metadata):
    return adam.endpoint_clock("A_"+key[2:],metadata)


def verify_sampling_checkpoint(path, config, trained):
    directory = Path(path).parent
    receipts = json.loads((directory/"opponent_selections.json").read_text())["receipts"]
    audit = json.loads((directory/"episodes.json").read_text())
    e = config["experiments"][0]
    ids = {"previous":config["previous_model_id"], "historical":e["historical_model_id"],
           **e["frozen_opponent_ids"]}
    points = receipts + [r["episode_identity"]["opponent_selection"] for r in audit["episodes"]]
    points += [r["episode_identity"]["opponent_selection"] for r in audit["pending"]]
    for r in points:
        selected,expected = stage_selection(e.get("opponent_schedule"),e["opponents"],r["case_index"],r["assigned_at_trained_transitions"])
        if (any(r[k] != v for k,v in expected.items()) or r["opponent_model_id"] != ids.get(selected)
                or not 0 <= r["assigned_at_trained_transitions"] <= trained
                or type(r["learner_steps"]) is not int or r["learner_steps"] < 0):
            raise ValueError("two_group_actual_sampler_or_policy_identity_mismatch")
    return {"trained":trained,"new_selection_receipts":len(receipts),"audit_points":len(points),
        "new_assignments_by_stage_opponent":dict(Counter(f"{r['stage']}:{r['opponent']}" for r in receipts)),
        "all_assignments_recomputed":True}


def evaluation_rivals(config):
    from advisor.learned_policy import LearnedPolicy
    e = config["experiments"][0]
    values = {r:r for r in ("max_power","champions_heuristic","tactical_heuristic")}
    bindings = {"previous":(config["previous_model"],config["previous_model_id"]),
                "historical":(e["historical_model"],e["historical_model_id"]),
                **{r:(p,e["frozen_opponent_ids"][r]) for r,p in e["frozen_opponents"].items()}}
    values.update({r:LearnedPolicy(path,config["catalog"],expected_model_id=sha) for r,(path,sha) in bindings.items()})
    return values


def evaluation_observer(output, slot):
    from advisor.learned_difficulty_calibration import PublicRetryAudit
    from scripts.run_foundation_parent_anchor_study import append
    audit = PublicRetryAudit(slot["case"])
    def observe(event):
        if event["result"]["action_rejected"]:
            append(Path(output)/"evaluation_public_rejections.jsonl", {"slot":slot,"public_transition":event})
        audit.observe(event)
    return observe


def analyze(rows, cases, *, resamples=20000):
    result = paired.analyze(rows,cases,resamples=resamples,policies=POLICIES,seeds=SEEDS,arm_names=("A","B"),rivals=RIVALS)
    groups = {}
    for name,rivals in (("easy",("max_power",)),("competitive",COMPETITIVE)):
        projected = [{**c,"rivals":[r for r in c["rivals"] if r in rivals]} for c in cases]
        filtered = [r for r in rows if r["slot"]["rival"] in rivals]
        groups[name] = paired.analyze(filtered,projected,resamples=resamples,policies=POLICIES,seeds=SEEDS,arm_names=("A","B"),rivals=rivals)
    def contrast(scope,name):
        return next(d for d in result["paired_differences"] if d["mode"]=="argmax" and d["scope"]==scope and d["rival"]=="all" and d["comparison"]==name)
    primary = contrast("heldout","mean_seed(B-A)")
    gates = {"heldout_paired95_lower_above_zero":primary["case_cluster_95"][0]>0,
        "both_continuation_directions_positive":all(contrast("heldout",f"B_{s}-A_{s}")["delta"]>0 for s in SEEDS),
        "overall_point_not_negative":contrast("all","mean_seed(B-A)")["delta"]>=0,
        "competitive_heldout_point_not_negative":next(d for d in groups["competitive"]["paired_differences"]
            if d["mode"]=="argmax" and d["scope"]=="heldout" and d["rival"]=="all"
            and d["comparison"]=="mean_seed(B-A)")["delta"]>=0,
        "no_truncated_native_outcomes":not any(r["record"]["truncated"] for r in rows)}
    result.update(primary="argmax heldout all-rival mean_seed(B-A)", opponent_groups=groups,
        sampling="all_frozen_argmax_no_extra_sampling_games",multiplicity="one_heldout_primary_others_descriptive",
        evaluation_weighting="one_third_easy_two_thirds_competitive_each_competitive_one_ninth_of_games",
        expansion_gates=gates, curriculum_expansion="GO" if all(gates.values()) else "NO_GO",
        no_model_promotion=True)
    return result
