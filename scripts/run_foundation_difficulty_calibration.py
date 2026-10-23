"""Detached, receipt-bound train-only calibration, never PPO or automatic restart."""
import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learned_difficulty_calibration import (
    VERSION, RIVALS, ANALYSIS, PublicSampler, PublicRetryAudit, AttemptRateGuard, game_slots, audit_receipts, analyze,
)
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, process_alive, enforce_local_network_only
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append(path, row):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def verify_plan(path):
    from advisor.learned_training_subset import NativeTrainingSubset
    from advisor.learned_encoder import fingerprint
    p = read(path)
    if (p["schema_version"] != VERSION or p["games"] != 1792 or p["new_PPO_transitions"] != 0
            or p["automatic_restarts"] != 0 or p["analysis"] != ANALYSIS
            or p["engine_commit"] != SHOWDOWN_COMMIT or p["format_id"] != FORMAT_ID
            or p["resources"] != {"workers": 1, "cpu_percent": 50, "memory_mib": 12288,
                                  "device": "cpu", "max_runtime_seconds": 3600}):
        raise ValueError("unapproved_calibration_contract")
    for name, sha in p["immutable_files"].items():
        if digest(name) != sha:
            raise ValueError("calibration_input_mutated:" + name)
    for name, sha in p["source_sha256"].items():
        if __import__("hashlib").sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != sha:
            raise ValueError("calibration_source_mutated:" + name)
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != p["source_commit"]:
        raise ValueError("calibration_source_commit_changed")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=p["checkout"], text=True).strip() != SHOWDOWN_COMMIT:
        raise ValueError("calibration_engine_pin_changed")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=p["checkout"], text=True).strip():
        raise ValueError("calibration_engine_dirty")
    grant, proposal = read(p["authorization_path"]), read(p["proposal_path"])
    if (grant.get("approved_additional_calibration_games") != 1792
            or grant.get("approved_calibration_PPO_transitions") != 0
            or grant.get("original_final_evaluation_budget_untouched") != 5760
            or grant.get("proposal_sha256") != digest(p["proposal_path"])
            or p["parent"] != {"path": proposal["parent_path"], "sha256": proposal["parent_SHA256"]}
            or p["rivals"] != proposal["pool"] or list(p["rivals"]) != list(RIVALS)
            or proposal["casebank_SHA256"] != digest(p["cases_path"])):
        raise ValueError("calibration_user_authorization_binding")
    if digest(p["parent"]["path"]) != p["parent"]["sha256"]:
        raise ValueError("calibration_parent_mutated")
    for rival in p["rivals"].values():
        if "model_path" in rival and digest(rival["model_path"]) != rival["model_SHA256"]:
            raise ValueError("calibration_rival_mutated")
    subset = NativeTrainingSubset(p["training_subset"], p["training_subset_sha256"])
    cases = read(p["cases_path"])["cases"]
    game_slots(cases)
    for case in cases:
        if subset("train", case["index"]) != case["scenario"] or fingerprint(case["scenario"]) != case["scenario_SHA256"]:
            raise ValueError("calibration_train_only_case_changed")
    return p, cases


def compact_view(view):
    """Own request and incremental public events, no native truth. Initial full view below."""
    return {**{k: v for k,v in view.items() if k not in ("state", "public_history", "projection_coverage")},
            "state_sha256": content_hash(view["state"]), "public_history_sha256": content_hash(view["public_history"])}


def calibrate(path, job, limit, *, resume=False):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
    from scripts.run_foundation_parent_anchor_study import checkpoint_integrity, FrozenCase
    from scripts.evaluate_showdown_policy import evaluate
    p, cases = verify_plan(path)
    out, plan_sha = Path(p["output"]), digest(path)
    slots = game_slots(cases)
    for name in ("receipts", "decisions"):
        (out / name).mkdir(exist_ok=True)
    probe = out / "receipts" / "storage_preflight.json"
    if not probe.exists():
        durable_json(probe, {"plan_sha256": plan_sha})
    if read(probe) != {"plan_sha256": plan_sha}:
        raise ValueError("calibration_destination_binding")
    rows = audit_receipts(out, slots, plan_sha)
    if rows and not resume:
        raise ValueError("calibration_existing_results_require_explicit_resume")
    if (out / "execution_complete.json").exists():
        raise ValueError("calibration_already_completed_no_duplicate_launch")
    torch.set_num_threads(1)
    proof = checkpoint_integrity(p["parent"]["path"], p["parent"]["sha256"], 32768)
    player = LearnedPolicy(p["parent"]["path"], p["catalog"], expected_model_id=p["parent"]["sha256"])
    before = {"parameters": tensor_digest(player.model.policy.state_dict()),
              "Adam": optimizer_digest(player.model.policy)}
    if before != p["parent_semantic_identity"]:
        raise ValueError("calibration_parent_semantic_identity")
    initial_path = out / "initial_identity.json"
    initial = {"checkpoint": proof, **before, "plan_sha256": plan_sha}
    if initial_path.exists():
        if read(initial_path) != initial:
            raise ValueError("calibration_initial_identity_changed")
    else:
        durable_json(initial_path, initial)
    rivals = {name: name if "model_path" not in binding else LearnedPolicy(
        binding["model_path"], p["catalog"], expected_model_id=binding["model_SHA256"])
        for name,binding in p["rivals"].items()}
    rival_before = {name: tensor_digest(r.model.policy.state_dict()) for name,r in rivals.items() if not isinstance(r,str)}
    case_lookup = {c["index"]: c for c in cases}
    launch_start, initial_done = time.monotonic(), len(rows)
    ledger = out / "game_ledger.jsonl"
    rate_guard = AttemptRateGuard()
    for index in range(len(rows), len(slots)):
        if limit.stopping():
            atomic_json(out / "status.json", {"status": "stopped", "games": len(rows), "target":1792, "utc":utc()})
            return None
        slot = slots[index]
        sampler = PublicSampler(player.infer, slot)
        audit = PublicRetryAudit(slot["case"])
        decisions = out / "decisions" / f"game_{index:04d}.jsonl.gz"
        append(ledger, {"phase": "game_started", "index": index, "slot_sha256": content_hash(slot)})
        original = player.infer
        started = time.monotonic()
        with decisions.open("xb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
                def observe(event):
                    if len(sampler.pending) != 1:
                        raise ValueError("calibration_sampling_transition_join")
                    row = {"ordinal": audit.steps, "candidate": sampler.pending.pop(),
                        "before": {s: compact_view(v) for s,v in event["before"].items()},
                        "actions": event["actions"], "result": event["result"],
                        "after": {s: compact_view(v) for s,v in event["after"].items()}}
                    if audit.steps == 0:
                        row["initial_public_views"] = event["before"]
                    try:
                        statistics = audit.observe(event)
                        rate_guard.observe(event["result"]["action_rejected"])
                    except BaseException as error:
                        row["audit_error"] = str(error)
                        stream.write((json.dumps(row, allow_nan=False) + "\n").encode())
                        stream.flush()
                        raw.flush()
                        os.fsync(raw.fileno())
                        raise
                    row["ordinal"] = audit.steps - 1
                    if event["result"]["action_rejected"]:
                        row["retry_statistics"] = statistics
                    stream.write((json.dumps(row, allow_nan=False) + "\n").encode())
                    if event["result"]["action_rejected"]:
                        stream.flush()
                    if limit.stopping():
                        raise TimeoutError("calibration_stop_or_deadline_no_automatic_replay")
                player.infer = sampler
                try:
                    result = evaluate(p["checkout"], p["catalog"], {"parent": player},
                        split="validation", cases=1, offset=slot["case"],
                        curriculum_version="showdown-learning-curriculum-v8",
                        rivals={slot["rival"]: rivals[slot["rival"]]},
                        case_provider=FrozenCase(case_lookup[slot["case"]], plan_sha),
                        candidate_seat=slot["seat"], tactical_diagnostics=True,
                        transition_observer=observe, stopping=limit.stopping)
                finally:
                    player.infer = original
            raw.flush()
            os.fsync(raw.fileno())
        record = result["records"][0]
        if (record["canonical_scenario_sha256"] != slot["scenario_sha256"]
                or record["candidate_seat"] != slot["seat"] or record["opponent"] != slot["rival"]
                or record["initial_native_seed"] != case_lookup[slot["case"]]["scenario"]["seed"]
                or record["decisions"] != audit.steps or record["native_choice_rejections"] != audit.rejections
                or sampler.pending):
            raise ValueError("calibration_native_receipt_identity")
        row = {"slot":slot, "plan_sha256":plan_sha, "record":record, "record_sha256":content_hash(record),
               "decisions_path":str(decisions), "decisions_sha256":digest(decisions),
               "sampling_seed":sampler.seed, "wall_seconds":time.monotonic()-started,
               "retry_statistics":audit.monitor.statistics(), "model_sha256":p["parent"]["sha256"]}
        receipt = out / "receipts" / f"game_{index:04d}.json"
        durable_json(receipt, row)
        if read(receipt) != row:
            raise ValueError("calibration_receipt_readback")
        append(ledger, {"phase":"game_committed", "index":index, "receipt_sha256":digest(receipt)})
        rows.append(row)
        # Resource/progress only: no strength results used by a running trainer.
        if len(rows) % 8 == 0:
            atomic_json(out / "status.json", {"status":"running", "pid":os.getpid(), "utc":utc(),
                "games":len(rows), "target":1792, "remaining":1792-len(rows),
                "games_per_second":(len(rows)-initial_done)/max(1,time.monotonic()-launch_start),
                "wall_seconds":time.monotonic()-launch_start, "resources":job.usage(),
                "new_PPO_transitions":0})
    verified = audit_receipts(out, slots, plan_sha)
    if len(verified) != 1792:
        raise ValueError("calibration_final_game_budget")
    after = {"parameters":tensor_digest(player.model.policy.state_dict()),
             "Adam":optimizer_digest(player.model.policy)}
    if after != before or rival_before != {name:tensor_digest(r.model.policy.state_dict()) for name,r in rivals.items() if not isinstance(r,str)}:
        raise ValueError("calibration_frozen_model_or_Adam_mutated")
    verify_plan(path)
    analysis = analyze(verified, cases)
    durable_json(out / "analysis.json", analysis)
    durable_json(out / "execution_complete.json", {"status":"complete_pending_independent_closure_audit",
        "utc":utc(), "games":1792, "new_PPO_transitions":0, "before":before, "after":after,
        "analysis_sha256":digest(out/"analysis.json"), "wall_seconds":time.monotonic()-launch_start,
        "resources":job.usage(), "automatic_restarts":0})
    atomic_json(out / "status.json", {"status":"complete", "games":1792, "target":1792, "utc":utc()})
    return analysis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--owned", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    p, _ = verify_plan(args.plan)
    out = Path(p["output"])
    if not args.owned:
        raise ValueError("calibration_independent_owned_process_required")
    if (out/"control.json").exists() and process_alive(read(out/"control.json")["pid"]):
        raise ValueError("calibration_owner_already_running")
    if any((out/f).exists() for f in ("failure.json","watchdog.json","STOP")):
        raise ValueError("calibration_failure_requires_diagnosis_no_automatic_restart")
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=12)
    if job.inherited_job:
        raise ValueError("calibration_owner_inherited_launcher_job")
    network = enforce_local_network_only()
    atomic_json(out/"control.json", {"pid":os.getpid(), "parent_pid":os.getppid(), "started_utc":utc(),
        "inherited_job":False, "own_job":True, "plan_sha256":digest(args.plan),
        "resources":p["resources"], "automatic_restarts":0})
    limit = RuntimeLimit(out, 3600)
    try:
        calibrate(args.plan, job, limit, resume=args.resume)
    except BaseException as error:
        atomic_json(out/"failure.json", {"utc":utc(), "type":type(error).__name__, "message":str(error),
            "automatic_restart":False, "uncertain_games_must_not_be_replayed":True, "network":network})
        raise
    finally:
        limit.finished.set()


if __name__ == "__main__":
    main()
