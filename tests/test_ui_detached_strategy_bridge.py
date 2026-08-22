from copy import deepcopy

from PySide6.QtWidgets import QApplication

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_ui_detached_strategy_bridge import run_current_ui_detached_strategy
from ui.widgets.llm_advice_panel import LLMAdvicePanel


class _RuntimeManager:
    def __init__(self, snapshots: list[dict]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def capture_runtime_state_snapshot(self, session_id: str) -> dict:
        value = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return deepcopy(value) if session_id == value["session_id"] else {"status": "stale_session"}


def _state(session: str = "ui-bridge") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "active", "opponent")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=90, max_hp=100, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
    state["self_side"]["pokemon"][1] = {
        "pokemon_id": "ready-bench", "current_hp": 70, "max_hp": 100, "fainted": False,
        "condition": {"knowledge": "unknown"}, "known_item": {"knowledge": "unknown"},
        "current_type": {"knowledge": "unknown"}, "current_ability": {"knowledge": "unknown"},
        "toxic_progression": {"knowledge": "unknown"},
    }
    state["self_side"]["pokemon"][2] = {
        **deepcopy(state["self_side"]["pokemon"][1]), "pokemon_id": "unknown-bench",
        "current_hp": {"knowledge": "unknown"}, "max_hp": {"knowledge": "unknown"}, "fainted": {"knowledge": "unknown"},
    }
    return state


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _owner(state: dict) -> dict:
    return {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": "active"}


def _selection_builder(*, selection_partial: bool = False, include_incomplete_switch: bool = False):
    def build(capture: dict, _runtime_snapshot: dict) -> dict:
        owner = capture["active_owner"]
        switches = [
            {"target_pokemon_id": "ready-bench", "selectable": True, "availability_supportability": "complete", "legality_supportability": "complete"},
            {"target_pokemon_id": "unknown-bench", "selectable": False, "availability_supportability": "insufficient_context", "legality_supportability": "not_applicable"},
        ]
        if include_incomplete_switch:
            switches[1] = {**switches[1], "selectable": True, "availability_supportability": "complete", "legality_supportability": "complete"}
        elif not selection_partial:
            switches = switches[:1]
        return {
            "status": "ready", "_runtime_d0_selection_capture": deepcopy(capture),
            "_combined_action_turn_snapshot": {"battle_state": {"active_player": {"slot_index": owner["slot_index"], "species_id": owner["pokemon_id"]}}, "current_state": {"current_state_session_id": owner["session_id"]}},
            "recommendation_request": {"candidate_comparisons": [{"move": "tackle", "eligibility": "eligible"}]},
            "evidence_bundle": {"switch_candidates": switches},
        }
    return build


def test_runtime_bridge_runs_switch_and_incomplete_attack_then_presents_without_provider() -> None:
    state = _state(); manager = _RuntimeManager([_snapshot(state), _snapshot(state)])
    before = deepcopy(manager._snapshots)

    result = run_current_ui_detached_strategy(
        runtime_session_manager=manager, captured_session_id=state["session_id"],
        selection_cycle_builder=_selection_builder(),
    )
    app = QApplication.instance() or QApplication([]); panel = LLMAdvicePanel(); emitted = []
    panel.advice_requested.connect(lambda: emitted.append(True))
    presentation = panel.set_strategy_explanation(result["explanation"])

    candidates = {row["candidate_id"]: row for row in result["explanation"]["candidates"]}
    assert result["status"] == "resolved" and result["execution_coverage"]["current_predictive_execution_authority"] == 1
    assert candidates["manual_switch:ready-bench"]["evidence_class"] == "exact_outcome"
    assert candidates["attack:tackle"]["evidence_class"] == "incomplete"
    assert candidates["attack:tackle"]["incomplete_reason"] == "exact_damage_unknown"
    assert presentation["status"] == "resolved" and "Ready Bench" in panel.output_edit.toPlainText()
    assert emitted == [] and manager._snapshots == before


def test_runtime_bridge_preserves_partial_selection_and_incomplete_switch() -> None:
    state = _state(); manager = _RuntimeManager([_snapshot(state), _snapshot(state)])

    result = run_current_ui_detached_strategy(
        runtime_session_manager=manager, captured_session_id=state["session_id"], decision_owner=_owner(state),
        selection_cycle_builder=_selection_builder(selection_partial=True),
    )

    candidates = {row["candidate_id"]: row for row in result["explanation"]["candidates"]}
    assert result["status"] == "resolved"
    assert result["explanation"]["overall_status"] == "selection_incomplete"
    assert "manual_switch:unknown-bench" not in candidates
    assert result["selection_completeness"]["candidate_set"] == "partial"

    complete_selection = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state), _snapshot(state)]), captured_session_id=state["session_id"],
        decision_owner=_owner(state), selection_cycle_builder=_selection_builder(include_incomplete_switch=True),
    )
    complete_candidates = {row["candidate_id"]: row for row in complete_selection["explanation"]["candidates"]}
    assert complete_candidates["manual_switch:unknown-bench"]["evidence_class"] == "incomplete"
    assert complete_candidates["manual_switch:unknown-bench"]["incomplete_reason"] == "incoming_state_unavailable"


def test_runtime_bridge_rejects_stale_result_and_selection_d0_mismatch() -> None:
    state = _state(); advanced = deepcopy(state); advanced["last_applied_observation_sequence"] = 1
    stale = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state), _snapshot(advanced)]), captured_session_id=state["session_id"],
        decision_owner=_owner(state), selection_cycle_builder=_selection_builder(),
    )
    bad = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state)] * 2), captured_session_id=state["session_id"],
        decision_owner=_owner(state), selection_cycle_builder=lambda capture, snapshot: {**_selection_builder()(capture, snapshot), "_runtime_d0_selection_capture": {**capture, "source_runtime_fingerprint": "foreign"}},
    )

    assert stale == {"status": "stale", "schema_version": "ui-detached-strategy-bridge-result-v1", "reason": "runtime_state_changed_strategy_result_discarded"}
    assert bad["status"] == "rejected" and bad["reason"] == "selection_cycle_runtime_d0_mismatch"


def test_runtime_bridge_handles_no_selectable_actions_without_provider() -> None:
    state = _state()
    def no_actions(capture: dict, _runtime_snapshot: dict) -> dict:
        owner = capture["active_owner"]
        return {
            "status": "ready", "_runtime_d0_selection_capture": deepcopy(capture),
            "_combined_action_turn_snapshot": {"battle_state": {"active_player": {"slot_index": owner["slot_index"], "species_id": owner["pokemon_id"]}}, "current_state": {"current_state_session_id": owner["session_id"]}},
            "recommendation_request": {"candidate_comparisons": []}, "evidence_bundle": {"switch_candidates": []},
        }
    result = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state), _snapshot(state)]), captured_session_id=state["session_id"],
        decision_owner=_owner(state), selection_cycle_builder=no_actions,
    )

    assert result["status"] == "resolved"
    assert result["explanation"]["candidates"] == []
