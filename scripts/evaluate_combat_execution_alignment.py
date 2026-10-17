"""One immutable execution-mode study; no optimizer or production operations."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import os
import subprocess
from time import perf_counter, time
import numpy as np
import torch
from advisor.learned_execution_alignment import (
    VERSION, content_hash, digest, durable_json, game_slots, masked_sample, sampling_rng, verify_record,
)
from advisor.learned_encoder import fingerprint
from advisor.learned_policy import LearnedPolicy
from advisor.learned_training_operations import CompletedRollouts, RetryMonitor, TrainingJournal, read_journal
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only, process_alive
import scripts.evaluate_showdown_policy as evaluator

ROOT = Path(__file__).resolve().parents[1]
WORKER = {}


class FrozenCaseProvider:
    def __init__(self, case):
        self.case = case
        self.identity = {"schema_version": VERSION, "scope": case["scope"],
                         "index": case["index"], "scenario_sha256": case["scenario_sha256"]}

    def __call__(self, split, index):
        if split != "validation" or index != self.case["index"]:
            raise ValueError("frozen_study_case_access_mismatch")
        return deepcopy(self.case["scenario"])


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_plan(plan):
    if plan["schema_version"] != VERSION or plan["battle_budget"] != 6144 or len(plan["cases"]) != 256:
        raise ValueError("unsupported_execution_study_plan")
    for name, expected in plan["source_sha256"].items():
        actual = __import__("hashlib").sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError("study_source_identity_changed:" + name)
    for model in plan["models"].values():
        if digest(model["path"]) != model["sha256"]:
            raise ValueError("study_model_sha_mismatch")
    if digest(plan["catalog"]) != plan["catalog_sha256"]:
        raise ValueError("study_catalog_sha_mismatch")
    if subprocess.check_output(["git", "-C", plan["checkout"], "rev-parse", "HEAD"], text=True).strip() != plan["engine_commit"]:
        raise ValueError("study_native_commit_mismatch")
    for case in plan["cases"]:
        if fingerprint(case["scenario"]) != case["scenario_sha256"]:
            raise ValueError("frozen_case_changed")


def initialize(plan_path, output, deadline):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    plan = read(plan_path)
    verify_plan(plan)
    network = enforce_local_network_only()
    policies = {name: LearnedPolicy(model["path"], plan["catalog"], expected_model_id=model["sha256"])
                for name, model in plan["models"].items()}
    WORKER.update(plan=plan, output=Path(output), deadline=deadline, policies=policies, network=network)


def chunk_worker(chunk):
    plan, output, policies = WORKER["plan"], WORKER["output"], WORKER["policies"]
    directory = output / "chunks" / chunk["id"]
    directory.mkdir(parents=True, exist_ok=True)
    slots = game_slots(chunk["cases"])
    existing = {index: verify_record(directory / f"game_{index:03d}.json", slot)
        for index, slot in enumerate(slots) if (directory / f"game_{index:03d}.json").exists()}
    for path in (directory / "operations").glob("launch_*.jsonl"):
        for event in read_journal(path)["records"]:
            if event["phase"] == "game_started" and event["observed"]["slot_index"] not in existing:
                raise ValueError("uncertain_game_consumption_no_automatic_replay:" + str(path))
    journal = TrainingJournal(directory, {"completed_battles": len(existing), "trained_rollout_transitions": 0})
    ledger = CompletedRollouts()
    records = dict(existing)
    cases = {(case["scope"], case["index"]): case for case in chunk["cases"]}
    last_progress = 0.
    observed_steps = 0
    current = {}
    retries = []
    base_env = evaluator.ShowdownEnvironment

    class ObservedEnvironment(base_env):
        def step(self, actions, *, revision):
            nonlocal observed_steps, last_progress
            if time() >= WORKER["deadline"]:
                raise TimeoutError("execution_study_hard_deadline_approaching")
            before = {side: self.observation(side) for side in actions}
            for side, action in actions.items():
                if not 0 <= action < 35 or not before[side]["action_mask"][action]:
                    raise ValueError("study_actor_mask_illegal_action")
            result = super().step(actions, revision=revision)
            observed_steps += 1
            if result["action_rejected"]:
                retries.append({"episode_id": before["self"]["episode_id"], "episode_case": current["case"],
                    "revision_before": revision, "revision_after": result["revision"],
                    "native_decisions": result["decisions"],
                    "before": {side: {"action_index": int(action), "action_mask": view["action_mask"],
                        "choice": view["choices"][action], "request_state": view["request_state"]}
                        for side, view in before.items() for action in [actions[side]]},
                    "after": {side: {"action_mask": self.observation(side)["action_mask"],
                        "request_state": self.observation(side)["request_state"]} for side in actions},
                    "cause": "private_native_cause_not_inferred"})
            if time() - last_progress >= 2:
                journal.append("running", slot=current, observed_native_decisions=observed_steps,
                               completed_games_with_durable_record=len(records))
                last_progress = time()
            return result

    evaluator.ShowdownEnvironment = ObservedEnvironment
    try:
        for index, slot in enumerate(slots):
            if index in records:
                continue
            if (output / "STOP").exists() or time() >= WORKER["deadline"]:
                journal.append("launch_end", status="stopped_between_games")
                return {"chunk": chunk["id"], "complete": False, "completed": len(records)}
            current = slot
            player = policies[slot["policy"]]
            rival = policies[slot["rival"]]
            rng = sampling_rng(slot["scope"], slot["case"], slot["seat"], slot["rival"], slot["mode"]) if slot["mode"] != "argmax" else None
            original = player.infer
            behavior = {"nonwait": 0, "multiple_legal": 0, "entropy_sum": 0., "sampled_nonargmax": 0,
                        "inference_seconds": 0.}
            retries = []

            def infer(view):
                started = perf_counter()
                proof = original(view)
                behavior["inference_seconds"] += perf_counter() - started
                probabilities = np.asarray(proof["action_probabilities"], dtype=float)
                if not view["action_mask"][26]:
                    behavior["nonwait"] += 1
                    behavior["multiple_legal"] += int(sum(view["action_mask"]) > 1)
                    positive = probabilities[probabilities > 0]
                    behavior["entropy_sum"] += float(-np.sum(positive * np.log(positive)))
                if rng is not None:
                    action = masked_sample(probabilities, view["action_mask"], rng.random())
                    if not view["action_mask"][26]:
                        behavior["sampled_nonargmax"] += int(action != proof["action_index"])
                    proof["action_index"], proof["native_choice"] = action, view["choices"][action]
                return proof

            journal.append("game_started", slot_index=index, slot=slot)
            started = perf_counter()

            def persist_result(result_records):
                if len(result_records) != 1:
                    raise ValueError("one_native_game_receipt_required")
                record = result_records[0]
                record.update(study_slot=slot, execution_behavior=behavior, public_retry_records=retries,
                              study_wall_seconds=perf_counter() - started,
                              frozen_model_sha256=plan["models"][slot["policy"]]["sha256"],
                              frozen_rival_sha256=plan["models"][slot["rival"]]["sha256"])
                envelope = {"slot": slot, "record": record, "record_sha256": content_hash(record)}
                durable_json(directory / f"game_{index:03d}.json", envelope)
                records[index] = record
                journal.publish({"completed_battles": len(records), "trained_rollout_transitions": ledger.transitions})
                journal.append("game_completed", slot_index=index, record_sha256=envelope["record_sha256"])

            player.infer = infer
            try:
                case = cases[(slot["scope"], slot["case"])]
                result = evaluator.evaluate(plan["checkout"], plan["catalog"], {slot["policy"]: player},
                    cases=1, offset=slot["case"], curriculum_version="showdown-learning-curriculum-v8",
                    rivals={slot["rival"]: rival}, candidate_seat=slot["seat"], tactical_diagnostics=True,
                    case_provider=FrozenCaseProvider(case), progress=persist_result)
            finally:
                player.infer = original
            if index not in records or result["records"][0] != records[index]:
                raise ValueError("native_receipt_and_evaluation_result_disagree")
        known = [record for record in records.values() if not record.get("administrative_unknown", False)]
        retry_rows = [row for record in known for row in record["public_retry_records"]]
        alerts = RetryMonitor().inspect(retry_rows, [], sum(record["decisions"] for record in known))
        if sum(record["truncated"] for record in known) > .01 * len(known):
            alerts.append({"reason": "native_truncation_rate_above_one_percent"})
        if alerts:
            (output / "STOP").touch()
        for name, policy in policies.items():
            if digest(plan["models"][name]["path"]) != policy.model_id:
                raise ValueError("model_artifact_changed_during_study")
            clocks = [int(state["step"]) for state in policy.model.policy.optimizer.state.values()]
            if max(clocks, default=0) != plan["models"][name]["optimizer_steps"]:
                raise ValueError("optimizer_clock_changed_in_inference_study")
        summary = {"chunk": chunk["id"], "complete": True, "completed": len(records), "alerts": alerts,
            "durable_known_outcomes": len(known), "administrative_unknown_consumptions": len(records) - len(known),
            "plan_sha256": WORKER["plan_sha256"] if "plan_sha256" in WORKER else content_hash(plan),
            "game_hashes": {f"game_{index:03d}.json": digest(directory / f"game_{index:03d}.json") for index in records},
            "PPO_updates": ledger.transitions, "network": WORKER["network"]}
        durable_json(directory / "COMMITTED.json", summary)
        journal.append("launch_end", status="complete", alerts=alerts)
        return {key: value for key, value in summary.items() if key != "game_hashes"}
    except BaseException as error:
        (output / "STOP").touch()
        journal.append("launch_failed", error=type(error).__name__, message=str(error), completed=len(records))
        raise
    finally:
        evaluator.ShowdownEnvironment = base_env


def run(plan_path, output, *, resume=False, max_chunks=None):
    if max_chunks is not None and not 1 <= max_chunks <= 32:
        raise ValueError("bounded_study_chunk_limit_required")
    output = Path(output).resolve()
    plan = read(plan_path)
    verify_plan(plan)
    output.mkdir(exist_ok=True, parents=True)
    plan_sha = digest(plan_path)
    lock = output / "run.lock"
    if lock.exists():
        if process_alive(read(lock)["pid"]):
            raise RuntimeError("execution_study_already_running")
        if not resume:
            raise RuntimeError("stale_study_lock_requires_explicit_resume")
        lock.unlink()
    durable_json(lock, {"pid": os.getpid(), "plan_sha256": plan_sha})
    timer = None
    journal = None
    started = perf_counter()
    try:
        state_path = output / "state.json"
        if state_path.exists():
            if not resume:
                raise ValueError("existing_study_requires_resume")
            state = read(state_path)
            if state["plan_sha256"] != plan_sha:
                raise ValueError("resume_study_plan_changed")
            if (output / "STOP").exists():
                raise ValueError("study_stop_requires_review_not_automatic_clear")
        else:
            if resume:
                raise ValueError("resume_study_state_missing")
            state = {"schema_version": VERSION, "plan_sha256": plan_sha, "first_launch_unix": time(),
                     "completed_battles": 0, "trained_rollout_transitions": 0, "transitions": 0, "launches": 0}
        remaining = 3570 - (time() - state["first_launch_unix"])
        if remaining <= 0:
            raise TimeoutError("cumulative_study_hour_exhausted")
        job = WindowsJob(cpu_percent=50, memory_mib=12288, active_process_limit=24)
        network = enforce_local_network_only()
        timer = RuntimeLimit(output, remaining)
        journal = TrainingJournal(output, state)
        state["launches"] += 1
        state["status"] = "running"
        atomic_json(state_path, state)
        pending = []
        committed = []
        for chunk in plan["chunks"]:
            path = output / "chunks" / chunk["id"] / "COMMITTED.json"
            if path.exists():
                data = read(path)
                if data["plan_sha256"] != content_hash(plan) or data["alerts"]:
                    raise ValueError("committed_chunk_identity_or_safety_failure")
                for name, expected in data["game_hashes"].items():
                    if digest(path.parent / name) != expected:
                        raise ValueError("committed_game_hash_mismatch")
                committed.append(data)
            else:
                pending.append(chunk)
        selected = pending[:max_chunks] if max_chunks is not None else pending
        with ProcessPoolExecutor(max_workers=4, initializer=initialize,
                initargs=(str(plan_path), str(output), state["first_launch_unix"] + 3570)) as pool:
            futures = [pool.submit(chunk_worker, chunk) for chunk in selected]
            for future in as_completed(futures):
                result = future.result()
                if result["complete"]:
                    committed.append(result)
                state["completed_battles"] = sum(row["completed"] for row in committed)
                state["resources"] = job.usage()
                state["launch_wall_seconds"] = perf_counter() - started
                atomic_json(state_path, state)
                journal.publish(state)
                journal.append("chunk_committed", result=result, resources=state["resources"])
                print(json.dumps({"completed_battles": state["completed_battles"], "chunk": result["chunk"],
                                  "resources": state["resources"]}), flush=True)
        state["status"] = "complete" if state["completed_battles"] == 6144 else "stopped"
        state["launch_wall_seconds"] = perf_counter() - started
        state["resources"] = job.usage()
        state["network"] = network
        atomic_json(state_path, state)
        journal.publish(state)
        journal.append("launch_end", status=state["status"], resources=state["resources"])
        return state
    except BaseException as error:
        if journal is not None:
            journal.append("launch_failed", error=type(error).__name__, message=str(error))
        raise
    finally:
        if timer is not None:
            timer.finished.set()
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-chunks", type=int)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.plan, arguments.output, resume=arguments.resume, max_chunks=arguments.max_chunks)))
