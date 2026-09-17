from copy import deepcopy

import pytest

from llm.advisor_current_state_runtime_admission import (
    admit_current_state_observation,
    admit_current_state_observations,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _manager():
    state = create_unknown_bootstrap_battle_state("current-state-ui", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
    return BattleObservationRuntimeSessionManager.create("current-state-ui", state)["manager"]


@pytest.mark.parametrize(("event_kind", "payload", "side"), [
    ("current_type_observed", {"types": ["fire"]}, "self"),
    ("current_ability_observed", {"ability": "blaze"}, "self"),
    ("current_item_observed", {"status": "known", "item": "charcoal"}, "self"),
    ("stat_stage_observed", {"stat": "attack", "stage": 2}, "self"),
    ("current_final_combat_stat_observed", {"stat": "attack", "value": 222}, "self"),
    ("current_level_observed", {"level": 50}, "self"),
    ("current_battle_format_observed", {"battle_format": "singles"}, None),
])
def test_explicit_current_ui_fact_reaches_canonical_runtime(event_kind, payload, side):
    manager = _manager()
    result = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="current-state-ui",
        event_kind=event_kind, payload=payload, side=side, turn_number=1,
    )
    assert result["status"] == "resolved", result
    assert result["observation"]["trust"] == "user_confirmed_observation"
    assert manager.read_state()["state"]["last_applied_observation_sequence"] == 1


def test_field_snapshot_is_previewed_and_committed_as_one_authoritative_batch():
    manager = _manager()
    result = admit_current_state_observations(
        runtime_session_manager=manager, captured_session_id="current-state-ui", turn_number=1,
        observations=(
            {"event_kind": "current_weather_observed", "payload": {"weather": "rain"}},
            {"event_kind": "current_terrain_observed", "payload": {"terrain": "electric"}},
            {"event_kind": "current_side_conditions_observed", "payload": {"side_conditions": ["reflect", "tailwind"]}, "side": "self"},
            {"event_kind": "tailwind_side_condition_observed", "payload": {"status": "active"}, "side": "self"},
            {"event_kind": "current_side_conditions_observed", "payload": {"side_conditions": []}, "side": "opponent"},
        ),
    )
    assert result["status"] == "resolved", result
    state = manager.read_state()["state"]
    assert state["field"]["weather"] == "rain"
    assert state["field"]["terrain"] == "electric"
    assert state["self_side"]["side_conditions"] == ["reflect", "tailwind"]
    assert state["self_side"]["tailwind_status"] == "active"


def test_invalid_or_stale_current_fact_never_mutates_runtime():
    manager = _manager()
    before = deepcopy(manager.read_state())
    rejected = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="wrong-session",
        event_kind="current_type_observed", payload={"types": ["fire"]}, side="self", turn_number=1,
    )
    assert rejected["status"] == "rejected"
    rejected = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="current-state-ui",
        event_kind="current_item_observed", payload={"status": "known"}, side="self", turn_number=1,
    )
    assert rejected["status"] == "rejected"
    assert manager.read_state() == before


def test_unknown_ability_is_not_a_known_authoritative_ability_value():
    manager = _manager()
    result = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="current-state-ui",
        event_kind="current_ability_observed", payload={"ability": "unknown"}, side="self", turn_number=1,
    )
    assert result["status"] == "rejected"
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["current_ability"] == {"knowledge": "unknown"}


def test_exact_current_hp_admission_uses_the_authoritative_prior_hp():
    manager = _manager()
    result = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="current-state-ui",
        event_kind="exact_hp_transition_observed", payload={"hp_before": 80, "hp_after": 61},
        side="opponent", turn_number=1,
    )
    assert result["status"] == "resolved", result
    assert manager.read_state()["state"]["opponent_side"]["pokemon"][0]["current_hp"] == 61


def test_admitted_type_is_visible_to_frozen_d0_without_ui_object_aliasing():
    manager = _manager()
    payload = {"types": ["fire"]}
    assert admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="current-state-ui",
        event_kind="current_type_observed", payload=payload, side="self", turn_number=1,
    )["status"] == "resolved"
    payload["types"].append("water")
    snapshot = manager.capture_runtime_state_snapshot("current-state-ui")
    owner = {"session_id": "current-state-ui", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    assert d0["status"] == "resolved"
    assert d0["strategy_state"]["current_state"]["runtime_strategy_d0_authority"]["active"]["self"]["current_type"] == ["fire"]
