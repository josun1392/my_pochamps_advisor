from copy import deepcopy

from PySide6.QtWidgets import QApplication

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_substitute import update_substitute_state_context
from llm.advisor_ui_detached_strategy_bridge import run_current_ui_detached_strategy
import llm.advisor_ui_detached_strategy_bridge as bridge_subject
from tests.test_runtime_direct_damage_modifier_authority import _apply as _apply_direct_state, _base as _direct_base, _confirmations as _direct_confirmations
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


def _selection_builder(*, selection_partial: bool = False, include_incomplete_switch: bool = False, move: str = "tackle"):
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
            "recommendation_request": {"candidate_comparisons": [{"move": move, "eligibility": "eligible"}]},
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
    assert result["exact_outcome_ledgers"]["manual_switch:ready-bench"]["status"] == "evaluable"
    assert result["descriptive_metrics"]["manual_switch:ready-bench"]["target"]["status"] == "not_applicable"
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


def test_runtime_bridge_keeps_live_seismic_toss_visible_when_runtime_predictive_fields_are_incomplete() -> None:
    state = _state()
    result = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state), _snapshot(state)]), captured_session_id=state["session_id"],
        selection_cycle_builder=_selection_builder(move="seismic-toss"),
    )

    candidates = {row["candidate_id"]: row for row in result["explanation"]["candidates"]}
    assert result["status"] == "resolved"
    assert candidates["attack:seismic-toss"]["evidence_class"] == "incomplete"
    assert candidates["attack:seismic-toss"]["incomplete_reason"] == "exact_damage_unknown"


def test_runtime_bridge_routes_exact_runtime_seismic_toss_to_deterministic_presentation() -> None:
    state = _state()
    state["self_side"]["pokemon"][0].update(
        current_level=50,
        current_level_provenance={"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1},
    )
    target = state["opponent_side"]["pokemon"][0]
    target.update(current_hp=42, max_hp=100, current_type=["water"])
    target["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    opponent = {"session_id": state["session_id"], "side": "opponent", "slot_index": 0, "pokemon_id": "opponent"}
    state["substitute_state_context"] = update_substitute_state_context(
        context=None, session_id=state["session_id"], owner=opponent, state="known_inactive", substitute_hp=None,
        provenance="runtime_observed_substitute_state_v1",
    )
    result = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state), _snapshot(state)]), captured_session_id=state["session_id"],
        selection_cycle_builder=_selection_builder(move="seismic-toss"),
    )
    app = QApplication.instance() or QApplication([]); panel = LLMAdvicePanel(); emitted = []
    panel.advice_requested.connect(lambda: emitted.append(True))
    panel.set_strategy_explanation(result["explanation"])
    candidates = {row["candidate_id"]: row for row in result["explanation"]["candidates"]}

    assert result["status"] == "resolved"
    assert candidates["attack:seismic-toss"]["evidence_class"] == "exact_outcome"
    assert candidates["attack:seismic-toss"]["guaranteed_facts"]["guaranteed_opponent_fainted"] is True
    assert "Seismic Toss" in panel.output_edit.toPlainText()
    assert emitted == []


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


def test_runtime_bridge_projects_d0_metadata_to_live_ledgers_and_metrics() -> None:
    base = _direct_base()
    state = _apply_direct_state(
        base,
        _direct_confirmations(
            base, attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"},
            attacker_ability="pressure", target_ability="pressure",
        ),
    )
    # Water Gun has a partial exact-roll KO chance here, while Tackle has none;
    # neither candidate has a guaranteed KO.
    state["opponent_side"]["pokemon"][0]["current_hp"] = 52
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["stat_stages"].update(accuracy=0, evasion=0)
        pokemon["current_crit_volatiles"] = []
        pokemon["current_crit_volatiles_provenance"] = {
            "event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 2,
        }
    target_owner = {"session_id": state["session_id"], "side": "opponent", "slot_index": 0, "pokemon_id": "target"}
    state["substitute_state_context"] = update_substitute_state_context(
        context=None, session_id=state["session_id"], owner=target_owner,
        state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1",
    )

    metadata = {
        "tackle": {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100},
        "water-gun": {"move_id": "water-gun", "category": "special", "power": 40, "type": "water", "accuracy": 100},
    }

    def builder(capture: dict, _runtime_snapshot: dict) -> dict:
        owner = capture["active_owner"]
        return {
            "status": "ready", "_runtime_d0_selection_capture": deepcopy(capture),
            "_combined_action_turn_snapshot": {"battle_state": {"active_player": {"slot_index": owner["slot_index"], "species_id": owner["pokemon_id"]}}, "current_state": {"current_state_session_id": owner["session_id"]}},
            "recommendation_request": {"candidate_comparisons": [{"slot_index": index, "move": move, "eligibility": "eligible"} for index, move in enumerate(metadata)]},
            "evidence_bundle": {"candidates": [{"slot_index": index, "move": move, "canonical_move_metadata": value} for index, (move, value) in enumerate(metadata.items())], "switch_candidates": []},
        }

    result = run_current_ui_detached_strategy(
        runtime_session_manager=_RuntimeManager([_snapshot(state), _snapshot(state)]),
        captured_session_id=state["session_id"], selection_cycle_builder=builder,
    )
    ledgers, metrics = result["exact_outcome_ledgers"], result["descriptive_metrics"]
    assert result["status"] == "resolved"
    assert set(ledgers) == set(metrics) == {"attack:tackle", "attack:water-gun"}
    assert all(ledger.get("terminal_probability_mass") == {"numerator": 1, "denominator": 1} for ledger in ledgers.values())
    assert all(len(ledger["terminal_leaves"]) == 32 for ledger in ledgers.values())
    assert all(metric["status"] == "resolved" for metric in metrics.values())
    assert result["orchestration"]["ranking"]["pairwise_matrix"][0]["reason"] == "higher_exact_target_ko_probability"
    assert result["explanation"]["probability_aware_decisions"][0]["rule"] == "higher_target_ko_probability"


def test_response_profile_live_projection_composes_each_selectable_own_attack(monkeypatch) -> None:
    d0 = {"session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "preview", "decision_owner": {"session_id": "s", "side": "self"}}
    selection = {"actions": ({"action_id": "attack:left", "action_type": "attack", "selection": "selectable"}, {"action_id": "attack:right", "action_type": "attack", "selection": "selectable"})}
    seen = []
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_opponent_known_move_action_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_complete_opponent_response_set_authority", lambda **_: {"status": "resolved", "selectable_response_action_ids": ("opponent_attack:a",), "actions": ({"action_id": "opponent_attack:a"},)})
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_action_order_authority", lambda **kwargs: seen.append(kwargs["own_action"]["action_id"]) or {"status": "resolved"})
    monkeypatch.setattr(bridge_subject, "materialize_detached_opponent_response_profile", lambda **kwargs: {"status": "evaluable", "own_action_id": kwargs["own_action"]["action_id"]})
    projected = bridge_subject._project_live_opponent_response_profiles(strategy_d0=d0, runtime_snapshot={}, selection=selection, canonical_move_metadata_authorities={"a": {"status": "resolved"}})
    assert set(projected) == {"attack:left", "attack:right"} and seen == ["attack:left", "attack:right"]
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_opponent_known_move_action_authority", lambda **_: {"status": "incomplete", "reason": "known_moves_unknown"})
    unavailable = bridge_subject._project_live_opponent_response_profiles(strategy_d0=d0, runtime_snapshot={}, selection=selection, canonical_move_metadata_authorities={"a": {"status": "resolved"}})
    assert all(value["status"] == "incomplete" for value in unavailable.values())
