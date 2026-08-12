from llm.advisor_candidate_contract import evaluate_move_candidate
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import TAILWIND_SOURCE, TRICK_ROOM_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _snapshot(projection):
    return build_turn_snapshot_from_battle_input({
        "pokemon": {"my_active": {"slot_index": 0, "name_en": "pikachu", "name_ko": "Pikachu"}, "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "Eevee"}},
        "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}},
        "current_state_session_id": "s", "runtime_advice_state": projection,
    }).to_dict()["current_state"]


def _action_input(current):
    return {
        "final_stat_context": {"current_final_stats": [
            {"side": "self", "stat": "speed", "value": 100, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
            {"side": "opponent", "stat": "speed", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
        ]},
        "condition_context": {"current_conditions": [{"side": side, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"} for side in ("self", "opponent")]},
        "opponent_selected_move": {"move_id": "scratch"}, "field_state_context": current["field_state_context"],
    }


def _apply(manager, boundary, status):
    confirmation = boundary.confirm(event_kind="trick_room_field_observed", payload={"status": status}, session_id="s", source=TRICK_ROOM_SOURCE, trust=USER_TRUST, confirmed=True)
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _apply_inactive_tailwind(manager, boundary, side):
    confirmation = boundary.confirm(event_kind="tailwind_side_condition_observed", payload={"status": "inactive"}, session_id="s", source=TAILWIND_SOURCE, trust=USER_TRUST, confirmed=True, side=side)
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def test_only_explicit_global_trick_room_observation_reaches_canonical_action_order():
    manager = _manager()
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    initial = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert initial["field"]["trick_room"] == {"status": "unknown"}
    assert _snapshot(initial)["field_state_context"]["trick_room"] == {"status": "unknown", "provenance": "unknown"}
    _apply_inactive_tailwind(manager, boundary, "self"); _apply_inactive_tailwind(manager, boundary, "opponent")
    _apply(manager, boundary, "active")
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    current = _snapshot(projection)
    assert current["field_state_context"]["trick_room"] == {"status": "known_active", "provenance": "trusted_observed_current"}
    repository = {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    result = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=_action_input(current), repositories=repository)
    assert result["action_order"]["status"] == "acts_first"
    assert result["action_order"]["trick_room"] == "active"


def test_trick_room_observation_is_global_and_inactive_preserves_normal_speed_order():
    manager = _manager()
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    _apply_inactive_tailwind(manager, boundary, "self"); _apply_inactive_tailwind(manager, boundary, "opponent")
    _apply(manager, boundary, "inactive")
    current = _snapshot(build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"])
    assert current["field_state_context"]["trick_room"] == {"status": "known_inactive", "provenance": "trusted_observed_current"}
    repository = {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    assert evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=_action_input(current), repositories=repository)["action_order"]["status"] == "acts_second"
