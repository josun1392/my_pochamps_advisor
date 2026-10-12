"""Owned, bounded desktop worker using the established learning/evaluation code."""

from hashlib import sha256
import os
import sys
from time import time
import traceback

from trainer_app.runtime import (
    ROOT,
    read_json,
    runtime_environment,
    safe_user_path,
    validate_limits,
)
from advisor.learning_resources import WindowsJob, atomic_json, RuntimeLimit


def verify_payload():
    manifest = ROOT / "trainer_payload.json"
    if not manifest.exists():
        if getattr(sys, "frozen", False):
            raise ValueError("Packaged runtime manifest missing.")
        return
    for name, digest in read_json(manifest)["files"].items():
        path = ROOT / name
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Packaged runtime identity mismatch: {name}")


def execute(path, *, resume=False, evaluate=False):
    path = safe_user_path(path)
    config = read_json(path / "config.json")
    log = (path / "worker.log").open("a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = log
    os.environ.update(runtime_environment())

    def publish(event):
        atomic_json(
            path / "desktop_status.json",
            {
                "schema_version": "pokeadvice-desktop-status-v1",
                "pid": os.getpid(),
                "updated": time(),
                **event,
            },
        )

    publish({"phase": "preparing"})
    outer_budget = None
    try:
        validate_limits(config)
        # Serialize all workers in this user registry; OS releases the lock on crash.
        import msvcrt

        lock = (path.parent / "worker.lock").open("a+b")
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        if resume or evaluate:
            (path / "STOP").unlink(missing_ok=True)
        outer_budget = RuntimeLimit(path, config["max_runtime_seconds"])
        job = WindowsJob(
            memory_mib=config["memory_mib"],
            cpu_percent=config["cpu_percent"],
            active_process_limit=max(12, config["envs"] * 4 + 8),
        )
        if job.inherited_job:
            raise RuntimeError(
                "Worker inherited a launcher job; independent lifetime not verified. Launch the app directly from Windows Explorer."
            )
        atomic_json(
            path / "ownership.json",
            {
                "pid": os.getpid(),
                "inherited_job": False,
                "own_job": True,
                "started": time(),
                "gui_lifetime_required": False,
            },
        )
        verify_payload()
        from scripts.train_showdown_autonomous import (
            run,
            validate_config,
            training_config_fingerprint,
        )
        from advisor.showdown_bridge import ShowdownBridge
        from advisor.learned_policy import LearnedPolicy
        from advisor.learning_resources import enforce_local_network_only

        enforce_local_network_only()
        if sys.platform == "win32" and getattr(sys, "frozen", False):
            import ctypes

            ctypes.windll.kernel32.SetDllDirectoryW(None)

        validate_config(config)
        training_config_fingerprint(config)
        from pathlib import Path

        if not (Path(config["checkout"]) / ".git").exists():
            raise ValueError(
                "Pinned Showdown engine directory is missing or is not a native checkout."
            )
        ShowdownBridge(config["checkout"])._verify_checkout()
        for source in (
            config.get("previous_model"),
            config["experiments"][0].get("initial_model"),
            config["experiments"][0].get("historical_model"),
        ):
            if source:
                model = LearnedPolicy(source, config["catalog"])
                if (
                    source == config["experiments"][0].get("initial_model")
                    and model.encoder.version
                    != config["experiments"][0]["encoder_version"]
                ):
                    raise ValueError(
                        "Initial checkpoint encoder incompatible; choose a V3 full-catalog binding."
                    )
        if evaluate:
            evaluate_validation(path, config, publish, job)
        else:
            state = run(
                config,
                path,
                resume=resume,
                require_detached=True,
                event_callback=publish,
                resource_job=job,
            )
            publish(
                {
                    "phase": "completed",
                    "status": state["status"],
                    "transitions": state["transitions"],
                    "completed_battles": state["completed_battles"],
                    "resources": state["resources"],
                }
            )
    except BaseException as error:
        traceback.print_exc()
        atomic_json(
            path / "desktop_failure.json",
            {
                "error": type(error).__name__,
                "message": str(error),
                "updated": time(),
                "recovery": "Resume the saved run from its latest completed model/optimizer checkpoint; interrupted native rollouts restart.",
            },
        )
        publish({"phase": "failed", "message": str(error)})
        return 1
    finally:
        if outer_budget:
            outer_budget.finished.set()
    return 0


def evaluate_validation(path, config, publish, job):
    from scripts.evaluate_showdown_policy import evaluate
    from advisor.learned_policy import LearnedPolicy
    from advisor.learning_resources import enforce_local_network_only

    state = read_json(path / "state.json")
    best = state.get("best")
    if not best:
        raise ValueError("No validated retained model to evaluate.")
    if (path / "STOP").exists():
        (path / "STOP").unlink()
    budget = RuntimeLimit(path, min(config["max_runtime_seconds"], 1800))
    network = enforce_local_network_only()
    try:
        rivals = {
            name: LearnedPolicy(config["previous_model"], config["catalog"])
            if name == "previous"
            else name
            for name in config["evaluation_opponents"]
        }
        publish(
            {
                "phase": "evaluating",
                "transitions": state["transitions"],
                "completed_battles": state["completed_battles"],
            }
        )
        report = evaluate(
            config["checkout"],
            config["catalog"],
            {"best": LearnedPolicy(best, config["catalog"])},
            cases=config["validation_cases"],
            offset=config["validation_offset"],
            curriculum_version=config["curriculum_version"],
            rivals=rivals,
            stopping=budget.stopping,
            tactical_diagnostics=True,
            progress=lambda records: publish(
                {
                    "phase": "evaluating",
                    "evaluation_battles": len(records),
                    "resources": job.usage(),
                }
            ),
        )
        atomic_json(path / "manual_validation.json", report)
        publish(
            {
                "phase": "completed",
                "status": "validation_complete",
                "network": network,
                "resources": job.usage(),
            }
        )
    except TimeoutError:
        if not budget.stopping():
            raise
        publish({"phase": "completed", "status": "validation_stopped"})
    finally:
        budget.finished.set()
