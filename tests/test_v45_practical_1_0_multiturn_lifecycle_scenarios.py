"""Sanitized multi-turn practical-1.0 lifecycle and frozen-state scenarios."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CONDITION_APPLICATION_SOURCE,
    FAINT_SOURCE,
    FIRST_END_OF_TURN_SOURCE,
    HAZARD_STATE_SOURCE,
    SAME_TURN_EVENT_SOURCE,
    STAT_STAGE_SOURCE,
    SWITCH_SOURCE,
    TAILWIND_SOURCE,
    TRICK_ROOM_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot, build_turn_snapshot_from_battle_input


def _state(*, active="pikachu"):
    state = create_unknown_bootstrap_battle_state("s", active, "eevee")["state"]
    other = "raichu" if active == "pikachu" else "pikachu"
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = other
    state["self_side"]["pokemon"][1]["current_hp"] = 70
    state["self_side"]["pokemon"][1]["max_hp"] = 100
    return state


def _manager(*, active="pikachu", hp=None):
    state = _state(active=active)
    if hp is not None:
        state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=100, fainted=False)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary(*, active="pikachu"):
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": active}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _frozen(manager, *, turn, active):
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    return build_turn_snapshot_from_battle_input({
        "pokemon": {"my_active": {"slot_index": 0 if active == "pikachu" else 1, "name_en": active, "name_ko": active}, "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "eevee"}},
        "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}},
        "current_state_session_id": "s", "runtime_advice_state": projection,
    }, trusted_turn_context={"status": "available", "session_id": "s", "turn_number": turn, "source": "explicit_application_turn_state", "trust": "user_or_application_confirmed"}).to_dict()["current_state"]


def test_turn_scoped_event_and_phase_expire_without_mutating_the_prior_snapshot():
    manager, boundary = _manager(), _boundary()
    _apply(manager, boundary.confirm(event_kind="same_turn_event_observed", payload={"predicate": "received_qualifying_direct_damage", "occurred": True, "target_side": "opponent", "target_slot_index": 0, "target_pokemon_id": "eevee"}, session_id="s", source=SAME_TURN_EVENT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4))
    _apply(manager, boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4))
    turn_four = _frozen(manager, turn=4, active="pikachu")
    assert turn_four["turn_event_context"]["events"][0]["turn_number"] == 4
    assert turn_four["first_end_of_turn_phase_context"]["status"] == "reached"
    turn_five = _frozen(manager, turn=5, active="pikachu")
    assert turn_five["turn_event_context"]["events"] == []
    assert turn_five["first_end_of_turn_phase_context"]["status"] == "unknown"
    assert turn_four["first_end_of_turn_phase_context"]["status"] == "reached"


def test_side_tailwind_and_global_trick_room_persist_then_replace_without_aliasing():
    manager, boundary = _manager(), _boundary()
    for side, status in (("self", "active"), ("opponent", "inactive")):
        _apply(manager, boundary.confirm(event_kind="tailwind_side_condition_observed", payload={"status": status}, session_id="s", source=TAILWIND_SOURCE, trust=USER_TRUST, confirmed=True, side=side))
    _apply(manager, boundary.confirm(event_kind="trick_room_field_observed", payload={"status": "active"}, session_id="s", source=TRICK_ROOM_SOURCE, trust=USER_TRUST, confirmed=True))
    before = _frozen(manager, turn=4, active="pikachu")
    assert before["field_state_context"]["tailwind"]["self"]["status"] == "known_active"
    assert before["field_state_context"]["trick_room"]["status"] == "known_active"
    _apply(manager, boundary.confirm(event_kind="tailwind_side_condition_observed", payload={"status": "inactive"}, session_id="s", source=TAILWIND_SOURCE, trust=USER_TRUST, confirmed=True, side="self"))
    _apply(manager, boundary.confirm(event_kind="trick_room_field_observed", payload={"status": "inactive"}, session_id="s", source=TRICK_ROOM_SOURCE, trust=USER_TRUST, confirmed=True))
    after = _frozen(manager, turn=5, active="pikachu")
    assert after["field_state_context"]["tailwind"]["self"]["status"] == "known_inactive"
    assert after["field_state_context"]["trick_room"]["status"] == "known_inactive"
    assert before["field_state_context"]["tailwind"]["self"]["status"] == "known_active"


def test_identity_bound_condition_and_stage_do_not_follow_a_different_active_after_switch():
    manager, boundary = _manager(active="raichu"), _boundary(active="raichu")
    _apply(manager, boundary.confirm(event_kind="condition_applied_observed", payload={"condition": "burn"}, session_id="s", source=CONDITION_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="raichu", related_observation_id="observed-move"))
    _apply(manager, boundary.confirm(event_kind="stat_stage_observed", payload={"stat": "speed", "stage": -1}, session_id="s", source=STAT_STAGE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="raichu"))
    _apply(manager, boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "raichu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "pikachu"}, session_id="s", source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="raichu"))
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 1
    assert state["self_side"]["pokemon"][0]["condition"] == "burn"
    assert state["self_side"]["pokemon"][0]["stat_stages"] == {"speed": -1}
    frozen = _frozen(manager, turn=5, active="pikachu")
    assert frozen["runtime_advice_state"]["self"]["active_pokemon"]["pokemon_id"] == "pikachu"
    assert frozen["runtime_advice_state"]["self"]["active_pokemon"]["condition"] == {"status": "unknown"}


def test_hazard_replacement_persists_to_later_frozen_switch_authority():
    manager, boundary = _manager(), _boundary()
    present = {"stealth_rock": "present", "spikes_layers": 2, "toxic_spikes_layers": 1, "sticky_web": "present"}
    removed = {"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}
    _apply(manager, boundary.confirm(event_kind="switch_hazards_observed", payload=present, session_id="s", source=HAZARD_STATE_SOURCE, trust=USER_TRUST, confirmed=True, side="self"))
    _apply(manager, boundary.confirm(event_kind="switch_hazards_observed", payload=removed, session_id="s", source=HAZARD_STATE_SOURCE, trust=USER_TRUST, confirmed=True, side="self"))
    hazards = manager.read_state()["state"]["switch_hazard_context"]
    assert hazards == {"schema_version": "switch-hazard-context-v2", "session_id": "s", "affected_side": "self", **removed}
    frozen = build_request_start_recommendation_snapshot({"current_state_session_id": "s", "switch_hazard_context": hazards, "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=()).to_dict()["current_state"]
    assert frozen["switch_hazard_context"] == hazards
    hazards["spikes_layers"] = 3
    assert frozen["switch_hazard_context"]["spikes_layers"] == 0


def test_faint_terminal_rejects_later_owner_updates_without_contaminating_another_pokemon():
    manager, boundary = _manager(hp=0), _boundary()
    _apply(manager, boundary.confirm(event_kind="pokemon_faint_observed", payload={"cause_known": False}, session_id="s", source=FAINT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu"))
    later = boundary.confirm(event_kind="condition_applied_observed", payload={"condition": "burn"}, session_id="s", source=CONDITION_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", related_observation_id="later")
    assert manager.admit_confirmation("s", later)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "transition_invalid"
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["fainted"] is True
    assert state["self_side"]["pokemon"][1]["condition"] == {"knowledge": "unknown"}
