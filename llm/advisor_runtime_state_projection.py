"""Provider-safe, detached projection of one validated runtime battle state."""
from copy import deepcopy
import json

from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION,
    is_unknown_battle_fact,
    state_fingerprint,
    validate_battle_state_unknown_markers,
)


RUNTIME_ADVICE_STATE_VERSION = "runtime-advice-state-v1"


def build_runtime_advice_state_projection(runtime_state):
    """Map a battle-state-v1 snapshot to advice facts without inference or I/O."""
    try:
        if not _valid_runtime_state(runtime_state):
            return _failure("invalid_runtime_state")
        session_id = runtime_state["session_id"]
        projected = {
            "schema_version": RUNTIME_ADVICE_STATE_VERSION,
            "session_id": session_id,
            "self": {"active_pokemon": _active_pokemon(runtime_state, "self_side")},
            "opponent": {"active_pokemon": _active_pokemon(runtime_state, "opponent_side")},
            "field": {
                "weather": _fact(runtime_state["field"]["weather"], known_absence=True),
                "terrain": _fact(runtime_state["field"]["terrain"], known_absence=True),
                "self_side_conditions": _fact(runtime_state["self_side"]["side_conditions"], known_absence=True),
                "opponent_side_conditions": _fact(runtime_state["opponent_side"]["side_conditions"], known_absence=True),
                "tailwind": {"self": _observed_tailwind_fact(runtime_state["self_side"]), "opponent": _observed_tailwind_fact(runtime_state["opponent_side"])},
                "trick_room": _observed_trick_room_fact(runtime_state["field"]),
                "same_turn_events": _same_turn_events(runtime_state),
                "first_end_of_turn_phases": _first_end_of_turn_phases(runtime_state),
            },
        }
        if not _json_safe(projected):
            return _failure("invalid_runtime_state")
        return {
            "status": "runtime_projection_ready",
            "session_id": session_id,
            "runtime_advice_state": deepcopy(projected),
            "runtime_fingerprint": state_fingerprint(runtime_state),
        }
    except Exception:
        return _failure("runtime_projection_failed")


def normalize_runtime_advice_state_projection(value, expected_session_id):
    """Validate and detach the projection handoff stored in structured battle input."""
    if not isinstance(value, dict) or not isinstance(expected_session_id, str) or not expected_session_id:
        raise ValueError("invalid_runtime_advice_state")
    if value.get("schema_version") != RUNTIME_ADVICE_STATE_VERSION or value.get("session_id") != expected_session_id:
        raise ValueError("invalid_runtime_advice_state")
    if set(value) != {"schema_version", "session_id", "self", "opponent", "field"}:
        raise ValueError("invalid_runtime_advice_state")
    for side in ("self", "opponent"):
        container = value.get(side)
        active = container.get("active_pokemon") if isinstance(container, dict) else None
        if not isinstance(active, dict) or set(active) != {"pokemon_id", "current_hp", "max_hp", "fainted", "condition", "item"}:
            raise ValueError("invalid_runtime_advice_state")
        if not isinstance(active.get("pokemon_id"), str) or not active["pokemon_id"]:
            raise ValueError("invalid_runtime_advice_state")
        if not all(_valid_request_fact(active[name]) for name in ("current_hp", "max_hp", "fainted", "condition", "item")):
            raise ValueError("invalid_runtime_advice_state")
    field = value.get("field")
    if not isinstance(field, dict) or set(field) != {"weather", "terrain", "self_side_conditions", "opponent_side_conditions", "tailwind", "trick_room", "same_turn_events", "first_end_of_turn_phases"}:
        raise ValueError("invalid_runtime_advice_state")
    if not all(_valid_request_fact(field[name]) for name in ("weather", "terrain", "self_side_conditions", "opponent_side_conditions", "trick_room")) or not _valid_tailwind(field.get("tailwind")) or not _valid_same_turn_events(field.get("same_turn_events"), expected_session_id) or not _valid_first_end_of_turn_phases(field.get("first_end_of_turn_phases"), expected_session_id):
        raise ValueError("invalid_runtime_advice_state")
    return deepcopy(value)


def _active_pokemon(state, side_name):
    side = state[side_name]
    active = side["pokemon"][side["active_slot_index"]]
    return {
        "pokemon_id": active["pokemon_id"],
        "current_hp": _fact(active["current_hp"]),
        "max_hp": _fact(active["max_hp"]),
        "fainted": _fact(active["fainted"]),
        "condition": _fact(active["condition"], known_absence=True),
        "item": _fact(active["known_item"], known_absence=True),
    }


def _fact(value, *, known_absence=False):
    if is_unknown_battle_fact(value):
        return {"status": "unknown"}
    if known_absence and (value is None or value == []):
        return {"status": "known_absent"}
    return {"status": "known", "value": deepcopy(value)}


def _observed_tailwind_fact(side):
    status = side.get("tailwind_status") if isinstance(side, dict) else None
    provenance = side.get("tailwind_status_provenance") if isinstance(side, dict) else None
    if not isinstance(provenance, dict) or provenance.get("event_kind") != "tailwind_side_condition_observed" or provenance.get("trust") != "user_confirmed_observation":
        return {"status": "unknown"}
    if status not in {"active", "inactive"}:
        return {"status": "unknown"}
    return {"status": "known", "value": status}


def _observed_trick_room_fact(field):
    status = field.get("trick_room_status") if isinstance(field, dict) else None
    provenance = field.get("trick_room_status_provenance") if isinstance(field, dict) else None
    if not isinstance(provenance, dict) or provenance.get("event_kind") != "trick_room_field_observed" or provenance.get("trust") != "user_confirmed_observation":
        return {"status": "unknown"}
    if status not in {"active", "inactive"}:
        return {"status": "unknown"}
    return {"status": "known", "value": status}


def _valid_tailwind(value):
    return isinstance(value, dict) and set(value) == {"self", "opponent"} and all(
        _valid_request_fact(value[side]) and (value[side].get("status") != "known" or value[side].get("value") in {"active", "inactive"})
        for side in ("self", "opponent")
    )


def _same_turn_events(state):
    events = state.get("same_turn_event_context", []) if isinstance(state, dict) else []
    if not isinstance(events, list): return []
    return [deepcopy(event) for event in events if _valid_same_turn_event(event, state.get("session_id"))]


def _first_end_of_turn_phases(state):
    phases = state.get("first_end_of_turn_context", []) if isinstance(state, dict) else []
    if not isinstance(phases, list): return []
    return [deepcopy(phase) for phase in phases if _valid_first_end_of_turn_phase(phase, state.get("session_id"))]


def _valid_same_turn_events(value, session_id):
    return isinstance(value, list) and all(_valid_same_turn_event(item, session_id) for item in value)


def _valid_first_end_of_turn_phases(value, session_id):
    return isinstance(value, list) and all(_valid_first_end_of_turn_phase(item, session_id) for item in value)


def _valid_first_end_of_turn_phase(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    return isinstance(value, dict) and value.get("session_id") == session_id and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"


def _valid_same_turn_event(value, session_id):
    return isinstance(value, dict) and value.get("session_id") == session_id and value.get("predicate") in {"received_qualifying_direct_damage", "acted_earlier_this_turn", "lost_hp_this_turn"} and isinstance(value.get("occurred"), bool) and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("slot_index", "target_slot_index")) and value.get("side") in {"self", "opponent"} and value.get("target_side") in {"self", "opponent"} and all(isinstance(value.get(key), str) and value[key] for key in ("pokemon_id", "target_pokemon_id")) and isinstance(value.get("provenance"), dict) and value["provenance"].get("event_kind") == "same_turn_event_observed" and value["provenance"].get("trust") == "user_confirmed_observation"


def _valid_runtime_state(state):
    if not isinstance(state, dict) or state.get("state_version") != STATE_MODEL_VERSION:
        return False
    if not isinstance(state.get("session_id"), str) or not state["session_id"]:
        return False
    if not validate_battle_state_unknown_markers(state):
        return False
    for side_name in ("self_side", "opponent_side"):
        side = state.get(side_name)
        if not isinstance(side, dict) or not isinstance(side.get("active_slot_index"), int) or isinstance(side["active_slot_index"], bool):
            return False
        roster = side.get("pokemon")
        active = roster.get(side["active_slot_index"]) if isinstance(roster, dict) else None
        if not isinstance(active, dict) or not isinstance(active.get("pokemon_id"), str) or not active["pokemon_id"]:
            return False
    return isinstance(state.get("field"), dict)


def _valid_request_fact(value):
    if not isinstance(value, dict) or value.get("status") not in {"unknown", "known_absent", "known"}:
        return False
    if value["status"] == "known":
        return set(value) == {"status", "value"} and _json_safe(value["value"])
    return set(value) == {"status"}


def _json_safe(value):
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def _failure(status):
    return {"status": status, "session_id": None, "runtime_advice_state": None, "runtime_fingerprint": None}
