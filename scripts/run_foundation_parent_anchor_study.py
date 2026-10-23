"""One bounded, detached four-arm training/evaluation owner; no crash restart.

Start from an independently owned Windows desktop process with --owned.
Plans/configs/cases must already be immutable and preflighted before learning.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, process_alive, enforce_local_network_only
from advisor.learned_execution_alignment import digest, content_hash, durable_json, sampling_rng, masked_sample
from advisor import learned_anchor_study as anchor_study
from advisor.learned_team_scale import checkpoint_alerts


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append(path, row):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"utc": utc(), **row}, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def checkpoint_integrity(path, expected_sha, expected_clock):
    import io
    import zipfile
    import torch
    if digest(path) != expected_sha:
        raise ValueError("anchor_checkpoint_SHA_mismatch")
    def finite(value):
        if torch.is_tensor(value):
            return bool(torch.isfinite(value).all())
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return all(finite(v) for v in value)
        return True
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("anchor_checkpoint_CRC")
        optimizer = torch.load(io.BytesIO(archive.read("policy.optimizer.pth")), map_location="cpu", weights_only=True)
        parameters = torch.load(io.BytesIO(archive.read("policy.pth")), map_location="cpu", weights_only=True)
        clocks = {int(v["step"]) for v in optimizer["state"].values() if "step" in v}
        if not finite([optimizer, parameters]) or clocks != {expected_clock}:
            raise ValueError("anchor_checkpoint_nonfinite_or_Adam")
    return {"sha256": expected_sha, "CRC": "pass", "policy_Adam_finite": True, "Adam": expected_clock}


class FrozenCase:
    def __init__(self, row, identity):
        self.row, self.identity = row, identity
    def __call__(self, split, index):
        if split != "validation" or index != self.row["index"]:
            raise ValueError("frozen_anchor_case_access")
        return deepcopy(self.row["scenario"])


def train_arms(plan_path, job, limit, resume, *, study=anchor_study):
    from scripts.train_showdown_autonomous import run, validate_config
    plan, configs = study.verify_plan(plan_path)
    out = Path(plan["output"])
    state_path = out/"campaign_state.json"
    if state_path.exists() and not resume:
        raise ValueError("existing_anchor_campaign_requires_explicit_resume")
    state = read(state_path) if state_path.exists() else {"plan_sha256": digest(plan_path), "completed": {}}
    if state["plan_sha256"] != digest(plan_path):
        raise ValueError("anchor_resume_plan_changed")
    evaluation_native_ids = {r["native_identity"] for r in read(plan["cases_path"])["cases"]}
    for arm in plan["arms"]:
        key = arm["key"]
        if key in state["completed"]:
            bound = state["completed"][key]
            checkpoint_integrity(bound["path"], bound["sha256"],
                study.endpoint_clock(key, read(Path(bound["path"]).with_suffix(".json"))) if hasattr(study, "endpoint_clock") else 34816)
            continue
        if limit.stopping():
            atomic_json(state_path, {**state, "status": "stopped", "utc": utc()})
            return None
        study.verify_plan(plan_path)
        config = configs[key]
        validate_config(config)
        run_out = Path(arm["run"])
        run_out.mkdir(parents=True, exist_ok=True)
        state.update(status="training", arm=key, utc=utc())
        atomic_json(state_path, state)
        previous, final = None, None
        seen, last_publish = set(), 0.
        def observe(event):
            nonlocal previous, final, last_publish
            if time.monotonic()-last_publish >= 5 or event["phase"] in ("checkpoint_committed", "evaluating"):
                atomic_json(out/"progress.json", {**event, "phase_owner": "training", "arm": key,
                    "utc": utc(), "pid": os.getpid(), "completed_arms": list(state["completed"]),
                    "resources": job.usage()})
                last_publish = time.monotonic()
            if limit.stopping():
                (run_out/"STOP").touch()
            path = event.get("checkpoint")
            if event["phase"] != "checkpoint_committed" or not path or path in seen:
                return
            seen.add(path)
            metadata = read(Path(path).with_suffix(".json"))
            current = read(run_out/"state.json")
            if hasattr(study, "verify_initial_checkpoint") and current["trained_rollout_transitions"] == 0:
                proof = study.verify_initial_checkpoint(path, key, plan, config)
                append(out/"initial_checkpoint_proofs.jsonl", {"arm": key, **proof})
            for episode in read(Path(path).parent/"episodes.json")["episodes"]:
                identity = episode["episode_identity"]
                native = content_hash({"teams": identity["team_sha256"],
                    "preview": identity["preview"], "seed": identity["native_seed"]})
                if native in evaluation_native_ids or identity["split"] != "train":
                    raise ValueError("anchor_train_evaluation_native_identity_overlap")
            alerts = checkpoint_alerts(metadata, current, previous) + event.get("operational_alerts", [])
            row = {"arm": key, "path": path, "sha256": digest(path), "trained": current["trained_rollout_transitions"],
                "collected": current["transitions"], "optimizer_steps": metadata["optimizer_steps"],
                "battles": current["completed_battles"], "ppo": metadata.get("training_metrics", {}).get("ppo", {}),
                "resources": job.usage(), "alerts": alerts}
            append(out/"checkpoint_monitor.jsonl", row)
            if alerts:
                atomic_json(out/"monitor_alert.json", row)
                (run_out/"STOP").touch()
            previous = row
            if current["trained_rollout_transitions"] == 65536:
                final = row
        result = run(config, run_out, resume=resume and (run_out/"state.json").exists(),
                     require_detached=True, event_callback=observe, resource_job=job)
        if result["status"] != "complete" or result["trained_rollout_transitions"] != 65536:
            atomic_json(state_path, {**state, "status": "stopped", "utc": utc()})
            return None
        if final is None:
            # A crash after a final durable checkpoint may leave no callback on
            # explicit resume. Bind by SHA, never by best validation score.
            matches = [p for p in (run_out/"experiment_00").glob("*/model.zip")
                       if digest(p) == result["latest_model_sha256"]]
            if len(matches) != 1:
                raise ValueError("missing_fixed_endpoint_receipt")
            final = {"path": str(matches[0]), "sha256": digest(matches[0])}
        proof = checkpoint_integrity(final["path"], final["sha256"],
            study.endpoint_clock(key, read(Path(final["path"]).with_suffix(".json"))) if hasattr(study, "endpoint_clock") else 34816)
        metadata = read(Path(final["path"]).with_suffix(".json"))
        if metadata.get("parent_policy_anchor") != config["experiments"][0].get("parent_policy_anchor"):
            raise ValueError("anchor_endpoint_objective_changed")
        state["completed"][key] = {**final, "integrity": proof,
            "state_sha256": digest(run_out/"state.json"), "metadata_sha256": digest(Path(final["path"]).with_suffix(".json"))}
        atomic_json(state_path, state)
        gc.collect()
    state.update(status="training_complete", utc=utc(), resources=job.usage())
    atomic_json(state_path, state)
    return state


def evaluate_all(plan_path, state, job, limit, *, study=anchor_study):
    import numpy as np
    import torch
    from advisor.learned_policy import LearnedPolicy
    from scripts.evaluate_showdown_policy import evaluate
    plan, configs = study.verify_plan(plan_path)
    out = Path(plan["output"])
    config = next(iter(configs.values()))
    torch.set_num_threads(1)
    cases = read(plan["cases_path"])["cases"]
    slots = study.game_slots(cases)
    if len(slots) != plan["evaluation_games"]:
        raise ValueError("frozen_evaluation_game_budget_mismatch")
    case_lookup = {(r["scope"], r["index"]): r for r in cases}
    bindings = {"parent": {"path": plan["parent_path"], "sha256": plan["parent_sha256"]}, **state["completed"]}
    frozen = out/"frozen_endpoint_models.json"
    if frozen.exists():
        if read(frozen) != bindings:
            raise ValueError("anchor_evaluation_model_identity_changed")
    else:
        durable_json(frozen, bindings)
    models = {key: LearnedPolicy(b["path"], config["catalog"], expected_model_id=b["sha256"]) for key,b in bindings.items()}
    rivals = {r: r for r in ("champions_heuristic", "tactical_heuristic")}
    e = config["experiments"][0]
    rivals["league_anchor"] = LearnedPolicy(e["frozen_opponents"]["league_anchor"], config["catalog"],
        expected_model_id=e["frozen_opponent_ids"]["league_anchor"])
    sealed = out/"sealed"
    sealed.mkdir(exist_ok=True)
    # Actual destination durable-write preflight BEFORE any battle.
    probe = sealed/"storage_preflight.json"
    if not probe.exists():
        durable_json(probe, {"plan_sha256": digest(plan_path), "purpose": "destination_write_read_preflight"})
    if read(probe)["plan_sha256"] != digest(plan_path):
        raise ValueError("anchor_receipt_storage_binding")
    ledger = out/"evaluation_ledger.jsonl"
    events = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    started = {r["index"] for r in events if r["phase"] == "game_started"}
    committed = {r["index"] for r in events if r["phase"] == "game_committed"}
    done, rows = set(), []
    for index, slot in enumerate(slots):
        path = sealed/f"game_{index:04d}.json"
        if path.exists():
            receipt = read(path)
            if (receipt["slot"] != slot or content_hash(receipt["record"]) != receipt["record_sha256"]
                    or receipt["model_sha256"] != bindings[slot["policy"]]["sha256"]):
                raise ValueError("anchor_receipt_corrupt")
            done.add(index)
            rows.append(receipt)
    if started-done or committed != done or len(events) != 2*len(done):
        raise ValueError("uncertain_started_game_no_automatic_reexecution")
    initial_done, launch_start = len(done), time.monotonic()
    for index, slot in enumerate(slots):
        if index in done:
            continue
        if limit.stopping():
            atomic_json(out/"evaluation_status.json", {"status": "stopped", "completed": len(done), "utc": utc()})
            return None
        player = models[slot["policy"]]
        original = player.infer
        rng = sampling_rng(slot["scope"],slot["case"],slot["seat"],slot["rival"],slot["mode"]) if slot["mode"] != "argmax" else None
        diagnostic = {"decisions": 0, "nonwait": 0, "parent_KL_sum": 0., "parent_argmax_changed": 0,
            "parent_choice_probability_sum": 0., "entropy_sum": 0., "sample_nonargmax": 0}
        def infer(view):
            proof = original(view)
            if not view["action_mask"][26]:
                reference = proof if slot["policy"] == "parent" else models["parent"].infer(view)
                p = np.asarray(proof["action_probabilities"], dtype=float)
                q = np.asarray(reference["action_probabilities"], dtype=float)
                positive = q > 0
                diagnostic["nonwait"] += 1
                diagnostic["parent_KL_sum"] += float(np.sum(q[positive]*(np.log(q[positive])-np.log(p[positive].clip(1e-30)))))
                diagnostic["parent_argmax_changed"] += int(proof["action_index"] != reference["action_index"])
                diagnostic["parent_choice_probability_sum"] += float(p[reference["action_index"]])
                diagnostic["entropy_sum"] += float(-np.sum(p[p>0]*np.log(p[p>0])))
                if "initial_public_comparison" not in diagnostic:
                    diagnostic["initial_public_comparison"] = {
                        "feature_sha256": __import__("hashlib").sha256(player.encoder.encode(view).tobytes()).hexdigest(),
                        "legal_mask": view["action_mask"], "probabilities": p.tolist(), "parent_probabilities": q.tolist(),
                        "value": proof["discounted_return_estimate"], "parent_value": reference["discounted_return_estimate"],
                        "scope": "first_nonwait_public_state_check_cross_model_feature_SHA_before_pairing"}
            diagnostic["decisions"] += 1
            if rng is not None:
                action = masked_sample(proof["action_probabilities"], view["action_mask"], rng.random())
                diagnostic["sample_nonargmax"] += int(action != proof["action_index"])
                proof["action_index"], proof["native_choice"] = action, view["choices"][action]
            return proof
        append(ledger, {"phase": "game_started", "index": index, "slot_sha256": content_hash(slot)})
        def receipt(records):
            if len(records) != 1:
                raise ValueError("anchor_single_native_receipt_required")
            record = records[0]
            case = case_lookup[(slot["scope"], slot["case"])]["scenario"]
            if (record["canonical_scenario_sha256"] != slot["scenario_sha256"]
                    or record["candidate_seat"] != slot["seat"]
                    or record["initial_native_seed"] != case.get("seed")
                    or record["policy"] != slot["policy"] or record["opponent"] != slot["rival"]):
                raise ValueError("frozen_native_receipt_case_seat_seed_or_policy_mismatch")
            row = {"slot": slot, "record": records[0], "record_sha256": content_hash(records[0]),
                "execution_diagnostic": diagnostic, "model_sha256": bindings[slot["policy"]]["sha256"],
                "plan_sha256": digest(plan_path), "source_commit": plan["source_commit"],
                "comparison_scope": "same_visited_own_public_state_not_optimal_actions"}
            path = sealed/f"game_{index:04d}.json"
            durable_json(path, row)
            if read(path) != row:
                raise ValueError("anchor_receipt_readback")
            append(ledger, {"phase": "game_committed", "index": index, "receipt_sha256": digest(path)})
            done.add(index)
            rows.append(row)
        player.infer = infer
        try:
            evaluate(config["checkout"], config["catalog"], {slot["policy"]: player}, split="validation", cases=1,
                offset=slot["case"], curriculum_version=config["curriculum_version"], rivals={slot["rival"]: rivals[slot["rival"]]},
                case_provider=FrozenCase(case_lookup[(slot["scope"],slot["case"])], digest(plan_path)),
                candidate_seat=slot["seat"], seat_contract="own_team_preserving_native_seats_v1",
                tactical_diagnostics=True, progress=receipt)
        finally:
            player.infer = original
        if index not in done:
            raise ValueError("native_game_without_durable_receipt")
        if len(done)%8 == 0:
            atomic_json(out/"evaluation_status.json", {"status": "running_sealed", "pid": os.getpid(), "utc": utc(),
                "completed": len(done), "remaining": len(slots)-len(done), "target": len(slots),
                "games_per_second": (len(done)-initial_done)/max(1,time.monotonic()-launch_start), "resources": job.usage()})
    study.verify_plan(plan_path)
    for bound in bindings.values():
        if digest(bound["path"]) != bound["sha256"]:
            raise ValueError("anchor_model_mutated")
    result = study.analyze(rows, cases)
    result.update(plan_sha256=digest(plan_path), trained_transitions=262144,
        resources=job.usage(), evaluation_seconds=time.monotonic()-launch_start,
        rows=[{"slot":r["slot"], "record_sha256":r["record_sha256"]} for r in rows])
    durable_json(out/"analysis.json", result)
    atomic_json(out/"evaluation_status.json", {"status": "complete", "completed": len(rows), "target":plan["evaluation_games"],
        "utc":utc(), "analysis_sha256":digest(out/"analysis.json"), "no_model_promotion":True})
    return result


def main(*, study=anchor_study):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--owned", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not args.owned:
        raise RuntimeError("launch_from_independent_desktop_owned_process_required")
    plan = read(args.plan)
    # Historical owner defaults are unchanged. A study adapter can predeclare a
    # bounded, measured evaluation allowance without changing PPO resources.
    study.verify_plan(args.plan)
    out = Path(plan["output"])
    control = out/"control.json"
    if control.exists() and process_alive(read(control)["pid"]):
        raise RuntimeError("anchor_study_already_running")
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=24)
    if job.inherited_job:
        raise RuntimeError("anchor_owner_inherited_launcher_job")
    network = enforce_local_network_only()
    atomic_json(control,{"pid":os.getpid(),"parent_pid":os.getppid(),"started_utc":utc(),
        "inherited_job":False,"own_job":True,"cpu_percent":50,"memory_mib":12288,"workers":4,
        "automatic_restarts":0,"plan_sha256":digest(args.plan)})
    outer = RuntimeLimit(out, getattr(study, "OVERALL_SECONDS", 7200))
    training_limit = RuntimeLimit(out, 3600)
    evaluation_limit = None
    try:
        state = train_arms(args.plan,job,training_limit,args.resume,study=study)
        training_limit.finished.set()
        if state is None or outer.stopping():
            return
        evaluation_limit = RuntimeLimit(out,getattr(study, "EVALUATION_SECONDS", 3600))
        result = evaluate_all(args.plan,state,job,evaluation_limit,study=study)
        if result is None:
            return
        durable_json(out/"execution_complete.json",{"status":"complete_pending_independent_closure_audit",
            "utc":utc(),"trained_transitions":262144,"evaluation_games":plan["evaluation_games"],"network":network,
            "analysis_sha256":digest(out/"analysis.json"),"resources":job.usage(),"no_model_promotion":True})
    except BaseException as error:
        atomic_json(out/"failure.json",{"utc":utc(),"type":type(error).__name__,"message":str(error),
            "automatic_restart":False,"checkpoint_recovery_requires_diagnosis":True})
        raise
    finally:
        training_limit.finished.set()
        outer.finished.set()
        if evaluation_limit is not None:
            evaluation_limit.finished.set()


if __name__ == "__main__":
    main()
