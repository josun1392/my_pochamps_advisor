"""Reproducible offline real-UI proof and native strategic evaluation benchmark."""
from __future__ import annotations
import argparse
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_showdown_shadow import evaluate_current_showdown_shadow
from llm.advisor_showdown_strategy_evaluation import experimental_ranking
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state
from ui.main_window import MainWindow


def configuration(*, seeds=16, horizon=32):
    context = {"schema_version": "showdown-shadow-config-v2", "scenarios": fixture_scenarios(),
        "seeds": [[7, 11, 17, n] for n in range(seeds)],
        "rollout_policy": {"schema_version": "showdown-rollout-policy-v1", "policy": "showdown-random-player", "max_decisions": horizon,
            "self": {"move_probability": 1, "mega_probability": 0}, "opponent": {"move_probability": 1, "mega_probability": 0}}}
    for scenario in context["scenarios"]:
        scenario["hypothetical_active_hp"] = {"self": 155, "opponent": 147}
        scenario["opponent_actions"] = [{"action_id": "bullet-punch", "choice": "move 1"}, {"action_id": "swords-dance", "choice": "move 2"}]
    return context


def demo_window():
    window = MainWindow()
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": 150, "max_hp": 185, "fainted": False}
    snapshot = snapshot_from_state(state)
    manager = BattleObservationRuntimeSessionManager.create(snapshot["session_id"], state)["manager"]
    window._observation_runtime_session_manager = manager
    for column, name in (("team_my", "charizard"), ("team_enemy", "scizor")):
        window._slot_panel(column, 0).set_pokemon(window.repo.get(name))
        window.selected_slots[column] = 0
    own = window._slot_panel("team_my", 0)
    own.selected_moves = [window.move_repo.get("flamethrower"), window.move_repo.get("air-slash"), window.move_repo.get("protect"), None]
    own.selected_move_index = 0
    window._slot_panel("team_my", 1).set_pokemon(window.repo.get("garchomp"))
    return window, manager, snapshot


def wait(app, window):
    start = perf_counter()
    while window._showdown_evaluation_thread is not None and perf_counter() - start < 15:
        app.processEvents()
    assert window._showdown_evaluation_thread is None, "native UI evaluation timed out"


def verify(checkout, *, iterations=5, seeds=16, horizon=32):
    app = QApplication.instance() or QApplication([])
    window, manager, snapshot = demo_window()
    context = configuration(seeds=seeds, horizon=horizon)
    before = manager.capture_runtime_state_snapshot(snapshot["session_id"])
    try:
        window._start_deterministic_strategy_analysis()
        default_text = window.center_column.llm_advice_panel.output_edit.toPlainText()
        window.configure_showdown_shadow(checkout=checkout, context=context, experimental_ranking=True)
        started = perf_counter()
        window._start_deterministic_strategy_analysis()
        dispatch_ms = (perf_counter() - started) * 1000
        worker = window._showdown_evaluation_worker
        assert worker is not None, "actual selection producer did not dispatch native UI evaluation"
        job = deepcopy(worker.job)
        wait(app, window)
        cold_ui_ms = (perf_counter() - started) * 1000
        explanation = deepcopy(window._showdown_displayed_explanation)
        assert explanation["sampled_simulation"]["status"] == "evaluated", explanation["sampled_simulation"]
        assert "한도 내 표본 승리비율" in window.center_column.llm_advice_panel.output_edit.toPlainText()
        timings, latest = [], None
        for _ in range(iterations):
            started = perf_counter()
            latest = evaluate_current_showdown_shadow(runtime_snapshot=job["runtime_snapshot"], selection=job["selection"],
                context=job["context"], bridge=window._showdown_shadow_worker)
            timings.append((perf_counter() - started) * 1000)
            normalized, original = deepcopy(latest), deepcopy(explanation["sampled_simulation"])
            for result in (normalized, original):
                for row in result["scenarios"]: row.pop("root_checkpoint_fingerprint", None)
            assert normalized == original, "seeded strategic evidence changed"
        rank = experimental_ranking(evidence=latest, explanation=explanation, enabled=True)
        assert rank["status"] == "evaluated", rank
        summary = [{"hypothesis": s["hypothesis_id"], "opponent_action": s["opponent_action_id"],
            "candidates": [{k: c[k] for k in ("candidate_id", "sample_count", "self_win_samples", "opponent_win_samples", "draw_samples", "truncated_samples", "mean_outcome_value")} for c in s["candidates"]]} for s in latest["scenarios"]]
        window.configure_showdown_shadow()
        window._start_deterministic_strategy_analysis()
        assert window.center_column.llm_advice_panel.output_edit.toPlainText() == default_text
        assert manager.capture_runtime_state_snapshot(snapshot["session_id"]) == before
        assert manager.read_applied_ledger() == {}
        return {"status": "verified", "scenarios": len(latest["scenarios"]), "candidates": len(job["selection"]["actions"]),
            "seeds_per_cell": seeds, "max_decisions": horizon, "samples": len(latest["scenarios"]) * len(job["selection"]["actions"]) * seeds,
            "iterations": iterations, "native_warm_p50_ms": statistics.median(timings),
            "native_warm_p95_ms": sorted(timings)[min(len(timings) - 1, int(len(timings) * .95))],
            "ui_dispatch_ms": dispatch_ms, "cold_ui_end_to_end_ms": cold_ui_ms,
            "reproducible": True, "runtime_immutable": True, "rollback_default_equal": True,
            "default_policy_changed": False, "experimental_ranking": rank, "conditional_results": summary}
    finally:
        window.configure_showdown_shadow()
        wait(app, window)
        window.close()
        app.processEvents()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--showdown-checkout", type=Path)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--horizon", type=int, default=32)
    parser.add_argument("--export-demo", type=Path, help="write explicit hypothetical demo config, without importing observations")
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100 or not 1 <= args.seeds <= 64 or not 1 <= args.horizon <= 128: parser.error("invalid bounded benchmark parameters")
    if args.seeds * args.horizon * 32 > 32768: parser.error("demo rollout budget exceeded")
    if args.export_demo:
        args.export_demo.write_text(json.dumps(configuration(seeds=args.seeds, horizon=args.horizon), indent=2), encoding="utf-8")
    if args.showdown_checkout:
        with redirect_stdout(io.StringIO()):
            result = verify(args.showdown_checkout, iterations=args.iterations, seeds=args.seeds, horizon=args.horizon)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    elif not args.export_demo: parser.error("a checkout or explicit demo export path is required")


if __name__ == "__main__": main()
