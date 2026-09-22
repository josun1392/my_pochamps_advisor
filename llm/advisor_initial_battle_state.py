"""Identity-only, detached unknown bootstrap state factory."""
from copy import deepcopy

from llm.advisor_battle_state_context import normalize_user_confirmed_battle_format
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, make_unknown_battle_fact


def create_unknown_bootstrap_battle_state(session_id, self_identity, opponent_identity, *, battle_format=None, self_roster=None, opponent_roster=None):
    """Create battle-state-v1 without inferring unconfirmed battle facts."""
    self_id = _identity(self_identity)
    opponent_id = _identity(opponent_identity)
    self_roster_ids = _roster_identities(self_roster, self_id)
    opponent_roster_ids = _roster_identities(opponent_roster, opponent_id)
    if not isinstance(session_id, str) or not session_id or self_id is None or opponent_id is None or self_roster_ids is None or opponent_roster_ids is None:
        return {"status": "invalid_initial_state", "session_id": None, "state": None}
    state = {
        "state_version": STATE_MODEL_VERSION,
        "session_id": session_id,
        "self_side": _side(self_roster_ids),
        "opponent_side": _side(opponent_roster_ids),
        "field": {"weather": make_unknown_battle_fact(), "terrain": make_unknown_battle_fact(), "battle_format": make_unknown_battle_fact(), "trick_room_status": make_unknown_battle_fact(), "magic_room_status": make_unknown_battle_fact(), "gravity_status": make_unknown_battle_fact()},
        "last_applied_observation_sequence": None,
    }
    if battle_format is not None:
        try:
            value = normalize_user_confirmed_battle_format(battle_format)
        except ValueError:
            return {"status": "invalid_initial_state", "session_id": session_id, "state": None}
        state["field"]["battle_format"] = value["battle_format"]
        state["field"]["battle_format_provenance"] = {"event_kind": "session_battle_format_initialized", "source": value["source"], "trust": "user_confirmed_observation"}
    return {"status": "initial_state_ready", "session_id": session_id, "state": deepcopy(state)}


def _identity(value):
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict) and set(value) == {"pokemon_id"} and isinstance(value.get("pokemon_id"), str) and value["pokemon_id"]:
        return value["pokemon_id"]
    return None


def _roster_identities(value, active_id):
    if value is None:
        return {0: active_id}
    if not isinstance(value, dict):
        return None
    rows = {}
    for slot, pokemon_id in value.items():
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
            return None
        rows[slot] = pokemon_id
    return rows if rows.get(0) == active_id else None


def _pokemon(pokemon_id):
    return {
        "pokemon_id": pokemon_id,
        "current_level": make_unknown_battle_fact(),
        "current_final_stats": {},
        "current_hp": make_unknown_battle_fact(),
        "max_hp": make_unknown_battle_fact(),
        "fainted": make_unknown_battle_fact(),
        "current_type": make_unknown_battle_fact(),
        "current_ability": make_unknown_battle_fact(),
        "current_crit_volatiles": make_unknown_battle_fact(),
        "toxic_progression": make_unknown_battle_fact(),
        "condition": make_unknown_battle_fact(),
        "healing_prevented_status": make_unknown_battle_fact(),
        "known_item": make_unknown_battle_fact(),
        "locked_on_state": make_unknown_battle_fact(),
    }


def _side(roster_ids):
    return {
        "active_slot_index": 0,
        "pokemon": {slot: _pokemon(pokemon_id) for slot, pokemon_id in roster_ids.items()},
        "side_conditions": make_unknown_battle_fact(),
        "tailwind_status": make_unknown_battle_fact(),
    }
