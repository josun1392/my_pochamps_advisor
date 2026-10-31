"""Execute only a frozen protocol smoke plan; sealed evaluation is unavailable."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from copy import deepcopy
import json
import os
from time import monotonic
import traceback
import numpy as np
import torch
from advisor.learned_execution_alignment import durable_json
from advisor.learned_prospective_evaluation import ProspectiveEvaluationSource, file_sha
from advisor.learned_prospective_runner import (ProtocolRunner, protocol_points, FOUNDATION, CANDIDATE,
    inference_public_view, execution_identity)
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_policy import LearnedPolicy
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_response_predictor import public_input
from advisor.learning_resources import WindowsJob, enforce_local_network_only
from advisor.showdown_environment import ShowdownEnvironment

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def append(path, row):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, allow_nan=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def forbidden(*args, **kwargs):
    raise RuntimeError("runner_smoke_training_optimizer_or_model_save_forbidden")


def identity(actor):
    policy = actor.model.policy
    return {"parameters": tensor_digest(policy.state_dict()), "Adam": optimizer_digest(policy),
            "Adam_clock": optimizer_clock(policy)}


def execute(plan, plan_sha256):
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=12)
    enforce_local_network_only()
    started = monotonic()
    if (plan.get("schema_version") != "prospective-admission-runner-smoke-plan-v1"
            or plan.get("scope") != "protocol_only" or plan.get("native_starts_max") != 36
            or plan.get("base_games") != 24 or plan.get("replay_games") != 12
            or plan.get("resources") != {"CPU_percent": 50, "RAM_MiB": 12288, "workers": 1, "GPU": False}):
        raise ValueError("runner_protocol_plan_mismatch")
    out = Path(plan["output"])
    out.mkdir(parents=True, exist_ok=True)
    if (out / "execution_complete.json").exists():
        raise ValueError("protocol_already_complete_no_duplicate_execution")
    for name, expected in plan["source_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or file_sha(path) != expected:
            raise ValueError("runner_source_changed:" + name)
    for path, expected in plan["immutable_files"].items():
        if file_sha(path) != expected:
            raise ValueError("runner_input_changed:" + path)
    rm = read(plan["runtime_manifest"])
    for name, expected in rm["files"].items():
        if file_sha(Path(rm["root"]) / name) != expected:
            raise ValueError("runner_runtime_changed:" + name)
    source = ProspectiveEvaluationSource(plan["source_manifest"], plan["source_manifest_sha256"],
        readiness=plan["readiness"], readiness_sha256=plan["readiness_sha256"])
    source.verify_policy_bindings()
    from sb3_contrib import MaskablePPO
    for name in ("learn", "train", "collect_rollouts", "save"):
        setattr(MaskablePPO, name, forbidden)
    torch.optim.Adam.step = forbidden
    torch.set_num_threads(1)
    actors = {name: LearnedPolicy(binding["path"], plan["catalog"], expected_model_id=binding["sha256"])
              for name, binding in plan["models"].items()}
    for actor in actors.values():
        if "masked_temperature" in actor.metadata or getattr(actor.model, "masked_temperature", None):
            raise ValueError("protocol_requires_original_T1_policy")
        actor.model.policy.set_training_mode(False)
        actor.model.learn = actor.model.train = actor.model.save = forbidden
        actor.model.policy.optimizer.step = forbidden
    before = {name: identity(a) for name, a in actors.items()}
    initial = out / "model_initial_identity.json"
    if initial.exists():
        if read(initial) != before:
            raise ValueError("runner_initial_model_identity_changed")
    else:
        durable_json(initial, before)
    runner = ProtocolRunner(source, out / "games", plan["checkout"], plan["catalog"],
                            actors[CANDIDATE].model_id)
    points = list(protocol_points(source))
    order = [(p, name, "base") for p in points for name in (FOUNDATION, CANDIDATE)]
    order += [(p, FOUNDATION, "replay") for p in points]
    rows = []
    originals = {}
    failed_intents = plan.get("preserved_failed_intents", [])
    exact_replays = orphan_replays = 0
    for point, label, purpose in order:
        if monotonic() - started > 1200:
            raise TimeoutError("protocol_overall_wall_limit")
        actor = actors[label]
        failed = next((f for f in failed_intents if execution_identity(point, actor.model_id, purpose) == f["failed_identity"]), None)
        if failed:
            intent = Path(failed["intent_path"])
            if (file_sha(intent) != failed["intent_SHA256"]
                    or file_sha(failed["failure_path"]) != failed["failure_SHA256"]
                    or read(intent)["identity"] != failed["failed_identity"]):
                raise ValueError("preserved_failure_identity_changed")
            rows.append({"point_key": point["point_key"], "label": label, "purpose": purpose,
                         "status": "ORIGINAL_FAILED_INTENT_NOT_REEXECUTED"})
            continue
        rival = (point["opponent"] if point["opponent"] != "frozen_v4_reference"
                 else actors["frozen_v4_reference"])
        expected_sides = {label: point["seat"]}
        if not isinstance(rival, str):
            expected_sides["frozen_v4_reference"] = "opponent" if point["seat"] == "self" else "self"
        inference_counts = {key: 0 for key in expected_sides}
        old_infer = {}
        for key, side in expected_sides.items():
            target = actors[key]
            original = target.infer
            old_infer[key] = original

            def checked(view, original=original, side=side, key=key):
                if view["side"] != side:
                    raise ValueError("runner_policy_wrong_player_seat")
                public = inference_public_view(view)
                proof = original(public)
                mask = np.asarray(public["action_mask"], bool)
                probabilities = np.asarray(proof["action_probabilities"])
                if (proof["model_id"] != actors[key].model_id
                        or proof["action_index"] != int(probabilities.argmax())
                        or not mask[proof["action_index"]] or np.any(probabilities[~mask] != 0)):
                    raise ValueError("runner_not_T1_masked_argmax")
                inference_counts[key] += 1
                return proof

            target.infer = checked
        old_baseline = VisibleBaseline.act

        def checked_baseline(baseline, view):
            if view["side"] == point["seat"]:
                raise ValueError("runner_baseline_wrong_seat")
            result = old_baseline(baseline, inference_public_view(view))
            if not view["action_mask"][result]:
                raise ValueError("runner_baseline_illegal_action")
            return result

        VisibleBaseline.act = checked_baseline
        old_reset = ShowdownEnvironment.reset
        physical_starts = []

        def checked_reset(env, scenario, **kwargs):
            from advisor.learned_encoder import fingerprint
            if kwargs or fingerprint(scenario) != fingerprint(point["scenario"]) or physical_starts:
                raise ValueError("runner_reset_sealed_changed_or_duplicate")
            marker = {"point_key": point["point_key"], "model_id": actor.model_id, "purpose": purpose,
                      "native_start": True}
            append(out / "physical_native_starts.jsonl", marker)
            physical_starts.append(marker)
            return old_reset(env, scenario, **kwargs)

        ShowdownEnvironment.reset = checked_reset
        try:
            payload, newly_run = runner.run(point, label, actor, rival, purpose=purpose)
        finally:
            ShowdownEnvironment.reset = old_reset
            VisibleBaseline.act = old_baseline
            for key, original in old_infer.items():
                actors[key].infer = original
        if newly_run and (len(physical_starts) != 1 or not inference_counts[label]):
            raise ValueError("runner_missing_real_execution")
        if purpose == "base":
            originals[point["point_key"], label] = payload
        else:
            original = originals.get((point["point_key"], FOUNDATION))
            if original is None:
                if not any(f["failed_identity"] == execution_identity(point, actor.model_id, "base") for f in failed_intents):
                    raise ValueError("runner_unexpected_missing_replay_base")
                orphan_replays += 1
            else:
                if (payload["record"] != original["record"]
                        or payload["trace"]["public_trace_sha256"] != original["trace"]["public_trace_sha256"]):
                    raise ValueError("runner_same_seed_replay_mismatch")
                exact_replays += 1
        rows.append({"point_key": point["point_key"], "label": label, "purpose": purpose,
                     "return": payload["record"]["return"], "trace": payload["trace"]["public_trace_sha256"],
                     "inference_counts": inference_counts, "newly_run": newly_run, "valid_terminal": payload["valid_terminal"]})
        append(out / "progress.jsonl", {"completed_cells": len(rows), "last": rows[-1],
                                       "elapsed_seconds": monotonic() - started, "resources": job.usage()})
    after = {name: identity(a) for name, a in actors.items()}
    if before != after:
        raise ValueError("runner_model_or_Adam_changed")
    durable_json(out / "model_final_identity.json", after)
    receipts = list((out / "games").glob("result_*.json"))
    physical = [json.loads(s) for s in (out / "physical_native_starts.jsonl").read_text().splitlines()]
    failures = len(failed_intents)
    missing_bases = sum(f["failed_identity"]["purpose"] == "base" for f in failed_intents)
    missing_foundation_bases = sum(f["failed_identity"]["purpose"] == "base" and
        f["failed_identity"]["model_sha256"] == actors[FOUNDATION].model_id for f in failed_intents)
    if (len(rows) != 36 or len(receipts) != 36 - failures or len(physical) != 36
            or exact_replays != 12 - missing_foundation_bases or orphan_replays != missing_foundation_bases):
        raise ValueError("runner_missing_or_extra_execution")
    payloads = [read(path)["payload"] for path in receipts]
    coverage = {(p["label"], p["point"]["seat"], p["point"]["opponent"]) for p in payloads if p["valid_terminal"]}
    expected_coverage = {(label, seat, rival) for label in (FOUNDATION, CANDIDATE)
                         for seat in ("self", "opponent") for rival in source.manifest["opponent_order"]}
    for path, expected in plan["immutable_files"].items():
        if file_sha(path) != expected:
            raise ValueError("runner_original_input_changed:" + path)
    for name, expected in rm["files"].items():
        if file_sha(Path(rm["root"]) / name) != expected:
            raise ValueError("runner_runtime_changed_after_smoke:" + name)
    summary = {"status": "PROTOCOL_SMOKE_PASSED" if coverage == expected_coverage else "BOUNDED_FIX_REQUIRED", "plan_sha256": plan_sha256,
        "native_starts": len(physical), "stored_results": len(receipts),
        "valid_terminal_results": sum(p["valid_terminal"] for p in payloads),
        "truncated_results": sum(p["record"]["truncated"] for p in payloads), "terminal_coverage_cells": len(coverage),
        "base_games": 24 - missing_bases,
        "exact_replays": exact_replays, "replays_without_base_not_relabelled": orphan_replays,
        "preserved_failed_starts": failures,
        "sealed_case_model_forwards": 0, "sealed_case_steps": 0, "sealed_case_terminal_games": 0,
        "PPO": 0, "Adam_updates": 0, "model_promotion": False, "models_and_Adam_unchanged": True,
        "rows": rows, "runtime_files_verified": len(rm["files"]), "resources": job.usage(),
        "elapsed_seconds": monotonic() - started, "no_strength_claim": True}
    durable_json(out / "execution_complete.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    if file_sha(args.plan) != args.sha256:
        raise ValueError("runner_plan_hash_mismatch")
    plan = read(args.plan)
    try:
        execute(plan, args.sha256)
    except BaseException as error:
        path = Path(plan["output"]) / ("failure_" + plan.get("revision", "initial") + ".json")
        if not path.exists():
            durable_json(path, {"error": repr(error), "traceback": traceback.format_exc(),
                                "automatic_restart": False, "PPO": 0})
        raise


if __name__ == "__main__":
    main()
