from llm.advisor_candidate_contract import evaluate_move_candidate
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import TAILWIND_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _confirm(boundary, side, status):
    return boundary.confirm(
        event_kind="tailwind_side_condition_observed", payload={"status": status},
        session_id="s", source=TAILWIND_SOURCE, trust=USER_TRUST, confirmed=True, side=side,
    )


def _apply(manager, boundary, side, status):
    assert manager.admit_confirmation("s", _confirm(boundary, side, status))["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _snapshot(projection):
    return build_turn_snapshot_from_battle_input({
        "pokemon": {
            "my_active": {"slot_index": 0, "name_en": "pikachu", "name_ko": "Pikachu"},
            "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "Eevee"},
        },
        "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}},
        "current_state_session_id": "s", "runtime_advice_state": projection,
        "field_state_context": {"trick_room": {"status": "unknown", "provenance": "unknown"}},
    }).to_dict()["current_state"]


def _action_input(current):
    return {
        "final_stat_context": {"current_final_stats": [
            {"side": "self", "stat": "speed", "value": 100, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
            {"side": "opponent", "stat": "speed", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
        ]},
        "condition_context": {"current_conditions": [
            {"side": side, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}
            for side in ("self", "opponent")
        ]},
        "opponent_selected_move": {"move_id": "scratch"}, "field_state_context": current["field_state_context"],
    }


def test_only_confirmed_reducer_tailwind_reaches_action_order_and_preserves_trick_room_unknown():
    manager = _manager()
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    _apply(manager, boundary, "self", "active")
    first_projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    first_current = _snapshot(first_projection)
    tailwind = first_current["field_state_context"]["tailwind"]
    assert tailwind["self"] == {"status": "known_active", "provenance": "trusted_observed_current"}
    assert tailwind["opponent"] == {"status": "unknown", "provenance": "unknown"}
    assert first_current["field_state_context"]["trick_room"] == {"status": "unknown", "provenance": "unknown"}
    repository = {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    incomplete = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=_action_input(first_current), repositories=repository)
    assert incomplete["action_order"]["missing_inputs"] == ["opponent_tailwind"]
    _apply(manager, boundary, "opponent", "inactive")
    second_projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    second_current = _snapshot(second_projection)
    assert second_current["field_state_context"]["tailwind"]["opponent"]["status"] == "known_inactive"
    assert second_current["field_state_context"]["trick_room"] == {"status": "unknown", "provenance": "unknown"}
    assert evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=_action_input(second_current), repositories=repository)["action_order"]["missing_inputs"] == ["trick_room"]


def test_unconfirmed_or_fixture_tailwind_never_projects_as_current_authority():
    manager = _manager()
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert projection["field"]["tailwind"] == {"self": {"status": "unknown"}, "opponent": {"status": "unknown"}}
