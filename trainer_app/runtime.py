"""Lightweight desktop run ownership and file contracts (no model imports)."""

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from time import time
from uuid import uuid4

from advisor.learning_resources import atomic_json, process_alive

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
VERSION = "pokeadvice-desktop-trainer-v1"


def read_json(path, default=None):
    try:
        p = Path(path)
        if p.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("oversized_desktop_state")
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if default is None else default


def data_root():
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PokeAdviceAITrainer"


def safe_user_path(path):
    path = Path(path).resolve()
    forbidden = ROOT.parent if getattr(sys, "frozen", False) else ROOT
    if (
        path == forbidden
        or forbidden in path.parents
        or any((p / ".git").exists() for p in (path, *path.parents))
    ):
        raise ValueError(
            "Training data must be outside the application and source repositories."
        )
    return path


def default_engine():
    packaged = ROOT / "runtime/showdown"
    return (
        packaged
        if packaged.exists()
        else Path(os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT", ""))
    )


def runtime_environment():
    env = os.environ.copy()
    bins = ROOT / "runtime/bin"
    if bins.exists():
        env["PATH"] = str(bins) + os.pathsep + env.get("PATH", "")
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
        PYTHONIOENCODING="utf-8",
    )
    # A long-lived new frozen interpreter must reset the bootloader lifetime.
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    env.pop("QT_QPA_PLATFORM", None)
    return env


def model_choices():
    directory = ROOT / "models/showdown_full_mc_study_v1/catalog_bindings"
    return {
        name: directory / name / "model.zip"
        for name in ("ppo2477", "v4", "control", "v3")
    }


def make_config(options, engine):
    versions = {
        "full_mc": "showdown-learning-curriculum-v8",
        "species_disjoint": "showdown-learning-curriculum-v7",
    }
    if options["domain"] not in versions:
        raise ValueError("unsupported_desktop_domain")
    models = model_choices()
    seed = int(options.get("seed", 51061))
    envs = int(options.get("envs", 8))
    rollout = envs * 128
    steps = int(options.get("steps", 262144))
    interval = int(options.get("checkpoint_steps", 8192))
    source = options.get("initial_model")
    experiment = {
        "seed": seed,
        "name": "desktop_run",
        "steps": steps,
        "encoder_version": "showdown-learned-observation-v3",
        "learning_rate": 0.00005,
        "ent_coef": 0.01,
        "warmstart_decisions": 0,
        "fresh_optimizer": bool(options.get("fresh_optimizer", False)),
        "historical_model": str(models["v3"]),
        "opponents": [
            "max_power",
            "champions_heuristic",
            "tactical_heuristic",
            "previous",
            "historical",
        ],
    }
    if source:
        experiment["initial_model"] = str(Path(source).resolve())
    if steps % rollout or interval % rollout:
        raise ValueError(
            f"Transitions/evaluation interval must be multiples of {rollout}."
        )
    config = {
        "schema_version": "showdown-autonomous-training-v1",
        "checkout": str(Path(engine).resolve()),
        "catalog": str(ROOT / "models/showdown_mc_domain_v1/catalog.json"),
        "previous_model": str(models["v4"]),
        "curriculum_version": versions[options["domain"]],
        "max_runtime_seconds": int(options.get("runtime_seconds", 7200)),
        "envs": envs,
        "vector_backend": "subproc",
        "cpu_threads": int(options.get("cpu_threads", 4)),
        "memory_mib": int(options.get("memory_mib", 12288)),
        "cpu_percent": float(options.get("cpu_percent", 50)),
        "validation_cases": int(options.get("validation_cases", 32)),
        "validation_offset": int(
            options.get("validation_offset", 10000000 + seed * 10)
        ),
        "evaluation_opponents": [
            "max_power",
            "champions_heuristic",
            "tactical_heuristic",
            "previous",
        ],
        "checkpoint_steps": interval,
        "plateau_patience": int(options.get("plateau_patience", 4)),
        "final_test_cases": 0,
        "collect_tactical_metrics": True,
        "device": "cpu",
        "experiments": [experiment],
    }
    validate_limits(config)
    return config


def validate_limits(config):
    """Cheap checks before imports or creating a hard resource job."""
    if config.get("schema_version") != "showdown-autonomous-training-v1" or config.get(
        "curriculum_version"
    ) not in {"showdown-learning-curriculum-v7", "showdown-learning-curriculum-v8"}:
        raise ValueError("unsupported_desktop_domain_contract")
    experiments = config.get("experiments", [])
    if (
        len(experiments) != 1
        or experiments[0].get("encoder_version") != "showdown-learned-observation-v3"
    ):
        raise ValueError("unsupported_desktop_model_contract")
    for name, low, high in (
        ("envs", 1, 8),
        ("cpu_threads", 1, 8),
        ("memory_mib", 1024, 16384),
        ("max_runtime_seconds", 60, 21600),
        ("validation_cases", 1, 64),
    ):
        if type(config.get(name)) is not int or not low <= config[name] <= high:
            raise ValueError("unsafe_desktop_" + name)
    if (
        type(config.get("cpu_percent")) not in (int, float)
        or not 1 <= config["cpu_percent"] <= 75
    ):
        raise ValueError("unsafe_desktop_cpu_percent")
    minimum_memory = 2048 + 1024 * config["envs"]
    if config["memory_mib"] < minimum_memory:
        raise ValueError(
            f"This desktop preset requires at least {minimum_memory} MiB for {config['envs']} workers."
        )
    if config.get("device") != "cpu" or config.get("final_test_cases") != 0:
        raise ValueError("Desktop supports bounded CPU validation-only runs")


def busy_run(root):
    return next(
        (
            p
            for p in Path(root).glob("*")
            if p.is_dir() and (p / "desktop.json").exists() and worker_alive(p)
        ),
        None,
    )


def new_run(root, config):
    root = safe_user_path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / (time_name() + "_" + uuid4().hex[:8])
    path.mkdir()
    atomic_json(path / "config.json", config)
    atomic_json(
        path / "desktop.json",
        {
            "schema_version": VERSION,
            "created": time(),
            "run_id": path.name,
            "catalog_sha256": sha256(Path(config["catalog"]).read_bytes()).hexdigest(),
            "validation_only": True,
            "production_policy_changed": False,
        },
    )
    return path


def time_name():
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def launch_worker(path, *, resume=False, evaluate=False):
    path = safe_user_path(path)
    if busy_run(path.parent):
        raise ValueError(
            "An owned worker is already running; stop it before starting another."
        )
    if not (path / "config.json").is_file():
        raise ValueError("Missing run configuration.")
    if not getattr(sys, "frozen", False):
        command = [sys.executable, str(ROOT / "scripts/pokeadvice_ai_trainer.py")]
    else:
        command = [sys.executable]
    command += (
        ["--worker", str(path)]
        + (["--resume"] if resume else [])
        + (["--evaluate"] if evaluate else [])
    )
    flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_BREAKAWAY_FROM_JOB
    )
    with (path / "launcher.log").open("ab", buffering=0) as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=runtime_environment(),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            close_fds=True,
            creationflags=flags,
        )
    atomic_json(
        path / "launch.json",
        {
            "pid": process.pid,
            "started": time(),
            "mode": "evaluation" if evaluate else "resume" if resume else "training",
        },
    )
    return process.pid


def worker_alive(path):
    status = read_json(Path(path) / "desktop_status.json")
    launch = read_json(Path(path) / "launch.json")
    pid = status.get("pid")
    # New launch may still be importing before its first status write.
    if launch.get("started", 0) > status.get("updated", 0):
        pid = launch.get("pid")
    return bool(pid and process_alive(pid))


def stop_run(path):
    path = safe_user_path(path)
    if not (path / "desktop.json").exists():
        raise ValueError("Not a desktop-owned run.")
    (path / "STOP").touch()


def snapshot(path):
    path = Path(path)
    state = read_json(path / "state.json")
    heartbeat = read_json(path / "desktop_status.json")
    alive = worker_alive(path)
    phase = heartbeat.get("phase", "preparing")
    if alive and (path / "STOP").exists():
        phase = "stopping"
    elif not alive and phase in {"preparing", "running", "evaluating", "stopping"}:
        phase = (
            "completed" if state.get("status") in {"complete", "stopped"} else "failed"
        )
    resources = heartbeat.get("resources", state.get("resources", {}))
    return {
        "phase": phase,
        "alive": alive,
        "state": state,
        "heartbeat": heartbeat,
        "transitions": max(
            heartbeat.get("transitions", 0), state.get("transitions", 0)
        ),
        "battles": max(
            heartbeat.get("completed_battles", 0), state.get("completed_battles", 0)
        ),
        "resources": resources,
    }


def export_best(path, destination):
    state = read_json(Path(path) / "state.json")
    source = state.get("best")
    if not source:
        raise ValueError("No non-truncated validation-best checkpoint yet.")
    destination = safe_user_path(destination)
    if destination.exists():
        raise ValueError("Choose a new export folder; existing models are preserved.")
    destination.mkdir(parents=True)
    source = Path(source)
    for suffix in (".zip", ".json"):
        shutil.copyfile(source.with_suffix(suffix), destination / ("model" + suffix))
    if (source.parent / "validation.json").exists():
        shutil.copyfile(
            source.parent / "validation.json", destination / "validation.json"
        )
    return destination
