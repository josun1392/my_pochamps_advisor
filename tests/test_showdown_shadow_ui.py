"""Offline native engine → captured strategy → existing Qt explanation panel."""
from copy import deepcopy
import json
import os
import pytest
from PySide6.QtWidgets import QApplication
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_ui_detached_strategy_bridge import run_current_ui_detached_strategy
from llm.advisor_showdown_shadow import valid_shadow_evidence
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state
from tests.test_ui_detached_strategy_bridge import _RuntimeManager, _selection_builder
from ui.strategy_explanation_presentation import present_strategy_explanation
from ui.widgets.llm_advice_panel import LLMAdvicePanel


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def setup():
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": 150, "max_hp": 185, "fainted": False}
    snapshot = snapshot_from_state(state)
    original = _selection_builder(move="air-slash")
    def builder(capture, runtime):
        result = original(capture, runtime)
        result["recommendation_request"]["candidate_comparisons"].append({"move": "protect", "eligibility": "eligible"})
        result["evidence_bundle"]["switch_candidates"] = [{"target_pokemon_id": "garchomp", "selectable": True, "availability_supportability": "complete", "legality_supportability": "complete"}]
        return result
    context = {"schema_version": "showdown-shadow-config-v1", "scenarios": fixture_scenarios(), "seeds": [[7, 11, 17, n] for n in range(16)]}
    for scenario in context["scenarios"]: scenario["choices"]["opponent"] = "move 2"
    return snapshot, builder, context


def run(snapshot, builder, **kwargs):
    return run_current_ui_detached_strategy(runtime_session_manager=_RuntimeManager([snapshot, snapshot]),
        captured_session_id=snapshot["session_id"], selection_cycle_builder=builder, **kwargs)


def test_native_shadow_changes_only_separate_explanation_evidence(worker):
    snapshot, builder, context = setup()
    before = deepcopy((snapshot, context))
    baseline = run(snapshot, builder)
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)
    assert result["status"] == "resolved", result
    for key in ("orchestration", "exact_outcome_ledgers", "descriptive_metrics", "opponent_response_profiles", "execution_coverage"):
        assert result[key] == baseline[key]
    evidence = result["explanation"]["sampled_simulation"]
    assert evidence["status"] == "evaluated", evidence
    assert valid_shadow_evidence(evidence, result["explanation"])
    assert len(evidence["scenarios"]) == 4
    assert all(len(s["candidates"]) == 3 for s in evidence["scenarios"])
    assert all(c["status"] == "evaluated" for s in evidence["scenarios"] for c in s["candidates"])
    app = QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted = []
    panel.advice_requested.connect(lambda: emitted.append(True))
    assert panel.set_strategy_explanation(result["explanation"])["status"] == "resolved"
    assert "정확 확률 아님" in panel.output_edit.toPlainText()
    assert "기존 추천 순위는 유지" in panel.output_edit.toPlainText()
    assert "평균 남은 팀 HP" in panel.output_edit.toPlainText()
    assert emitted == []
    assert (snapshot, context) == before
    stripped = deepcopy(result["explanation"])
    stripped.pop("sampled_simulation")
    stripped.pop("source_runtime_fingerprint")
    assert stripped == baseline["explanation"]


def test_state_change_discards_shadow_with_existing_strategy_result(worker):
    snapshot, builder, context = setup()
    changed = deepcopy(snapshot["state"])
    changed["self_side"]["pokemon"][0]["current_hp"] -= 1
    result = run_current_ui_detached_strategy(runtime_session_manager=_RuntimeManager([snapshot, snapshot_from_state(changed)]),
        captured_session_id=snapshot["session_id"], selection_cycle_builder=builder,
        showdown_context=context, showdown_bridge=worker)
    assert result["status"] == "stale"
    assert "explanation" not in result


@pytest.mark.parametrize("mutate", [
    lambda s: s.update(session_id="foreign"),
    lambda s: s.update(source_runtime_fingerprint="stale"),
    lambda s: s.update(interpretation="exact_probability"),
    lambda s: s["scenarios"][0]["candidates"][0].update(candidate_id="attack:invented"),
    lambda s: s["scenarios"][0]["candidates"][0].update(opponent_new_faint_samples=100),
    lambda s: s["scenarios"][0]["candidates"][0].update(mean_self_team_hp=float("nan")),
])
def test_sampled_evidence_cannot_masquerade_as_current_exact_evidence(worker, mutate):
    snapshot, builder, context = setup()
    explanation = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)["explanation"]
    mutate(explanation["sampled_simulation"])
    assert present_strategy_explanation(explanation=explanation)["status"] == "rejected"


def test_unavailable_shadow_keeps_original_recommendation():
    snapshot, builder, context = setup()
    result = run(snapshot, builder, showdown_context=context)
    baseline = run(snapshot, builder)
    assert result["status"] == "resolved"
    assert result["orchestration"] == baseline["orchestration"]
    assert result["explanation"]["sampled_simulation"]["status"] == "rejected"


def test_runtime_rollback_stops_native_process_and_preserves_truth_and_ranking():
    from ui.main_window import MainWindow
    from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    app = QApplication.instance() or QApplication([])
    snapshot, builder, context = setup()
    owner = BattleObservationRuntimeSessionManager.create(snapshot["session_id"], snapshot["state"])["manager"]
    before = owner.capture_runtime_state_snapshot(snapshot["session_id"])
    window = MainWindow()
    window._observation_runtime_session_manager = owner
    try:
        assert window._showdown_shadow_worker is None
        baseline = run(snapshot, builder)
        window.configure_showdown_shadow(checkout=checkout, context=context)
        enabled = run(snapshot, builder, showdown_context=window._showdown_shadow_context,
            showdown_bridge=window._showdown_shadow_worker)
        assert enabled["explanation"]["sampled_simulation"]["status"] == "evaluated"
        process = window._showdown_shadow_worker._process
        assert process is not None and process.poll() is None
        window.configure_showdown_shadow()
        assert process.poll() is not None
        assert window._showdown_shadow_context is None and window._showdown_shadow_worker is None
        rolled_back = run(snapshot, builder, showdown_context=window._showdown_shadow_context,
            showdown_bridge=window._showdown_shadow_worker)
        assert rolled_back == baseline
        assert owner.capture_runtime_state_snapshot(snapshot["session_id"]) == before
        assert owner.read_applied_ledger() == {}
    finally:
        window.close()


def test_cli_opt_in_is_explicit_and_preserves_qt_arguments(monkeypatch, tmp_path):
    import main
    config = tmp_path / "hypotheses.json"
    config.write_text(json.dumps(setup()[2]), encoding="utf-8")
    calls = []
    class App:
        def __init__(self, args): calls.append(args)
        def exec(self): return 0
    class Window:
        def configure_showdown_shadow(self, **kwargs): calls.append(kwargs)
        def show(self): pass
    monkeypatch.setattr(main, "QApplication", App)
    monkeypatch.setattr(main, "MainWindow", Window)
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--showdown-shadow", str(config), "--showdown-checkout", "engine", "-platform", "offscreen"])
    assert main.main() == 0
    assert calls[0] == ["main.py", "-platform", "offscreen"]
    assert calls[1]["context"]["schema_version"] == "showdown-shadow-config-v1"
