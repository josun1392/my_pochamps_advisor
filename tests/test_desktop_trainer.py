"""Separate desktop app contracts; real frozen process tests live in release QA."""

from hashlib import sha256
from pathlib import Path
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("sb3_contrib")
from PySide6.QtWidgets import QApplication
from trainer_app import runtime
from trainer_app.gui import TrainerWindow
from advisor.learning_resources import atomic_json


def test_desktop_defaults_and_holdout_boundary():
    options = {"domain": "full_mc", "initial_model": None}
    config = runtime.make_config(options, Path("engine"))
    assert config["envs"] == 8 and config["cpu_threads"] == 4
    assert config["cpu_percent"] == 50 and config["memory_mib"] == 12288
    assert config["device"] == "cpu" and config["final_test_cases"] == 0
    assert (
        config["collect_tactical_metrics"] and len(config["evaluation_opponents"]) == 4
    )
    from scripts.train_showdown_autonomous import validate_config

    validate_config(config)
    assert (
        runtime.make_config({**options, "domain": "species_disjoint"}, Path("engine"))[
            "curriculum_version"
        ]
        == "showdown-learning-curriculum-v7"
    )
    for bad in (
        {"domain": "unsupported"},
        {"steps": 1025},
        {"checkpoint_steps": 1025},
        {"memory_mib": 65536},
        {"cpu_percent": 100},
        {"envs": 9},
        {"runtime_seconds": 21601},
        {"memory_mib": 2048},
    ):
        with pytest.raises(ValueError):
            runtime.make_config({**options, **bad}, Path("engine"))


def test_only_one_owned_worker_per_registry(tmp_path, monkeypatch):
    path = runtime.new_run(
        tmp_path, runtime.make_config({"domain": "full_mc"}, Path("engine"))
    )
    monkeypatch.setattr(runtime, "worker_alive", lambda p: p == path)
    assert runtime.busy_run(tmp_path) == path
    with pytest.raises(ValueError, match="already running"):
        runtime.launch_worker(path)


def test_manual_incompatible_desktop_contract_fails_before_launch():
    config = runtime.make_config({"domain": "full_mc"}, Path("engine"))
    config["curriculum_version"] = "showdown-learning-curriculum-v6"
    with pytest.raises(ValueError, match="domain_contract"):
        runtime.validate_limits(config)
    config["curriculum_version"] = "showdown-learning-curriculum-v8"
    config["experiments"][0]["encoder_version"] = "showdown-learned-observation-v2"
    with pytest.raises(ValueError, match="model_contract"):
        runtime.validate_limits(config)


def test_data_location_protects_package_and_repositories(tmp_path):
    with pytest.raises(ValueError):
        runtime.safe_user_path(runtime.ROOT / "user_checkpoints")
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(ValueError):
        runtime.safe_user_path(repository / "runs")
    assert runtime.safe_user_path(tmp_path / "runs") == tmp_path / "runs"


def test_heartbeat_progress_and_crash_recovery_classification(tmp_path, monkeypatch):
    path = runtime.new_run(
        tmp_path, runtime.make_config({"domain": "full_mc"}, Path("engine"))
    )
    atomic_json(
        path / "state.json",
        {
            "status": "running",
            "transitions": 1024,
            "completed_battles": 71,
            "latest": "saved.zip",
        },
    )
    atomic_json(
        path / "desktop_status.json",
        {
            "phase": "running",
            "pid": 721,
            "updated": 10,
            "transitions": 1536,
            "completed_battles": 90,
        },
    )
    monkeypatch.setattr(runtime, "process_alive", lambda pid: True)
    assert runtime.snapshot(path)["transitions"] == 1536
    runtime.stop_run(path)
    assert runtime.snapshot(path)["phase"] == "stopping"
    monkeypatch.setattr(runtime, "process_alive", lambda pid: False)
    assert runtime.snapshot(path)["phase"] == "failed"
    atomic_json(path / "state.json", {"status": "stopped", "transitions": 1536})
    assert runtime.snapshot(path)["phase"] == "completed"


def test_export_preserves_existing_model_and_manifest(tmp_path):
    path = runtime.new_run(
        tmp_path / "runs", runtime.make_config({"domain": "full_mc"}, Path("engine"))
    )
    source = path / "model.zip"
    source.write_bytes(b"trusted-test-model")
    source.with_suffix(".json").write_text("{}")
    atomic_json(path / "state.json", {"best": str(source)})
    digest = sha256(source.read_bytes()).hexdigest()
    out = runtime.export_best(path, tmp_path / "exported")
    assert sha256((out / "model.zip").read_bytes()).hexdigest() == digest
    with pytest.raises(ValueError):
        runtime.export_best(path, out)
    assert sha256(source.read_bytes()).hexdigest() == digest


def test_gui_start_button_uses_worker_and_remains_responsive(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    launched = []
    monkeypatch.setattr(
        "trainer_app.gui.launch_worker",
        lambda path, **kwargs: launched.append((path, kwargs)),
    )
    window = TrainerWindow(tmp_path)
    try:
        window.show()
        app.processEvents()
        window.start.click()
        app.processEvents()
        assert len(launched) == 1 and window.run_path.exists()
        config = runtime.read_json(window.run_path / "config.json")
        assert config["envs"] == 8 and config["final_test_cases"] == 0
        assert runtime.read_json(tmp_path / "gui_status.json")["responsive_tick"]
        assert (
            "기본 배틀 추천"
            in window.centralWidget().layout().itemAt(1).widget().text()
        )
    finally:
        window.close()
        app.processEvents()
