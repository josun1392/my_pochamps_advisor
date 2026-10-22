"""Detached, bounded sequential composition of the existing source trainer.

No automatic crash restart, policy selection or evaluation-panel consumption.
Final paired evaluations are frozen in the plan and run on the next user turn.
"""
import argparse
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, process_alive
from advisor.learned_team_scale import verify_plan, checkpoint_alerts, digest


def utc():
    return datetime.now(timezone.utc).isoformat()


def launch(plan_path, *, resume=False, probe=False):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    output = Path(plan["output"])
    output.mkdir(exist_ok=True, parents=True)
    control = output / ("probe_control.json" if probe else "campaign_control.json")
    if control.exists() and process_alive(json.loads(control.read_text())["pid"]):
        raise RuntimeError("study_owner_already_alive_no_duplicate_launch")
    env = os.environ.copy()
    env.update(PYTHONPATH=str(Path(sys.prefix) / "Lib/site-packages"), PYTHONNOUSERSITE="1")
    command = [sys._base_executable, str(Path(__file__).resolve()), "--plan", str(plan_path), "--owned"]
    command += ["--resume"] if resume else []
    command += ["--probe"] if probe else []
    with (output / ("probe_process.log" if probe else "campaign_process.log")).open("ab", buffering=0) as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=log, close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if control.exists():
            proof = json.loads(control.read_text())
            if proof["pid"] == child.pid:
                if proof["inherited_job"]:
                    raise RuntimeError("study_inherited_launcher_job")
                return proof
        if child.poll() is not None:
            raise RuntimeError("study_launch_failed_see_process_log")
        time.sleep(.1)
    child.terminate()
    raise RuntimeError("study_launch_proof_timeout")


def run_owned(plan_path, *, resume=False, probe=False):
    plan_path = Path(plan_path).resolve()
    raw_plan = json.loads(plan_path.read_text())
    output = Path(raw_plan["output"])
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=24)
    if job.inherited_job:
        raise RuntimeError("study_lifetime_not_independent_of_launcher")
    proof = {"pid": os.getpid(), "launcher_pid": os.getppid(), "started_utc": utc(),
        "started_unix": time.time(), "inherited_job": False, "own_job": True,
        "plan_sha256": digest(plan_path), "cpu_percent": 50, "memory_mib": 12288,
        "automatic_restarts": 0, "max_wall_seconds": 60 if probe else raw_plan["max_wall_seconds"]}
    atomic_json(output / ("probe_control.json" if probe else "campaign_control.json"), proof)
    if probe:
        time.sleep(3)
        atomic_json(output / "probe_completed.json", {**proof, "completed_utc": utc(),
            "launcher_still_alive": process_alive(proof["launcher_pid"]), "resources": job.usage()})
        return
    limit = RuntimeLimit(output, raw_plan["max_wall_seconds"])
    try:
        plan, configs = verify_plan(plan_path)
        from scripts.train_showdown_autonomous import run, validate_config
        status_path = output / "campaign_state.json"
        if status_path.exists() and not resume:
            raise ValueError("existing_campaign_requires_explicit_resume")
        status = json.loads(status_path.read_text()) if status_path.exists() else {"completed": {}, "plan_sha256": digest(plan_path)}
        if status["plan_sha256"] != digest(plan_path):
            raise ValueError("campaign_resume_plan_mismatch")
        for arm in plan["arms"]:
            if arm["key"] in status["completed"]:
                continue
            if limit.stopping():
                status.update(status="stopped", updated_utc=utc())
                atomic_json(status_path, status)
                return
            verify_plan(plan_path)
            config = configs[arm["key"]]
            validate_config(config)
            run_output = Path(arm["run"])
            run_output.mkdir(parents=True, exist_ok=True)
            previous = None
            seen = set()
            last_publish = 0.
            status.update(status="running", arm=arm["key"], updated_utc=utc())
            atomic_json(status_path, status)

            def observe(event):
                nonlocal previous, last_publish
                if time.monotonic() - last_publish >= 5 or event["phase"] == "evaluating":
                    atomic_json(output / "progress.json", {**event, "arm": arm["key"],
                        "utc": utc(), "pid": os.getpid(), "completed_arms": list(status["completed"]),
                        "resources": job.usage()})
                    last_publish = time.monotonic()
                if limit.stopping():
                    (run_output / "STOP").touch()
                path = event.get("checkpoint")
                if event["phase"] != "evaluating" or not path or path in seen:
                    return
                seen.add(path)
                metadata = json.loads(Path(path).with_suffix(".json").read_text())
                state = json.loads((run_output / "state.json").read_text())
                alerts = checkpoint_alerts(metadata, state, previous)
                row = {"arm": arm["key"], "utc": utc(), "checkpoint": path,
                    "sha256": digest(path), "trained": state["trained_rollout_transitions"],
                    "collected": state["transitions"], "optimizer_steps": metadata["optimizer_steps"],
                    "battles": state["completed_battles"], "resources": job.usage(), "alerts": alerts,
                    "ppo": metadata.get("training_metrics", {}).get("ppo", {})}
                with (output / "checkpoint_monitor.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                if alerts:
                    atomic_json(output / "monitor_alert.json", row)
                    (run_output / "STOP").touch()
                previous = row

            result = run(config, run_output, resume=(resume and (run_output / "state.json").exists()),
                         require_detached=True, event_callback=observe, resource_job=job)
            if result["status"] != "complete" or result["trained_rollout_transitions"] != 262144:
                status.update(status="stopped", stopped_arm=arm["key"], updated_utc=utc())
                atomic_json(status_path, status)
                return
            if previous is None:
                raise ValueError("completed_arm_without_checkpoint_receipt")
            status["completed"][arm["key"]] = previous
            atomic_json(status_path, status)
            gc.collect()
        status.update(status="training_complete_evaluation_pending", updated_utc=utc(), resources=job.usage())
        atomic_json(status_path, status)
    except BaseException as error:
        atomic_json(output / "campaign_failure.json", {"utc": utc(), "type": type(error).__name__,
            "message": str(error), "automatic_restart": False, "recover_only_after_diagnosis": True})
        raise
    finally:
        limit.finished.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--owned", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.owned:
        run_owned(args.plan, resume=args.resume, probe=args.probe)
    else:
        print(json.dumps(launch(args.plan, resume=args.resume, probe=args.probe), indent=2))


if __name__ == "__main__":
    main()
