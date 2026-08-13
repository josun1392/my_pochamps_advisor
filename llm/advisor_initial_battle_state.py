"""Identity-only, detached unknown bootstrap state factory."""
from copy import deepcopy

from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, make_unknown_battle_fact


def create_unknown_bootstrap_battle_state(session_id, self_identity, opponent_identity):
    """Create battle-state-v1 without inferring unconfirmed battle facts."""
    self_id = _identity(self_identity)
    opponent_id = _identity(opponent_identity)
    if not isinstance(session_id, str) or not session_id or self_id is None or opponent_id is None:
        return {"status": "invalid_initial_state", "session_id": None, "state": None}
    state = {
        "state_version": STATE_MODEL_VERSION,
        "session_id": session_id,
        "self_side": _side(self_id),
        "opponent_side": _side(opponent_id),
        "field": {"weather": make_unknown_battle_fact(), "terrain": make_unknown_battle_fact(), "trick_room_status": make_unknown_battle_fact()},
        "last_applied_observation_sequence": None,
    }
    return {"status": "initial_state_ready", "session_id": session_id, "state": deepcopy(state)}


def _identity(value):
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict) and set(value) == {"pokemon_id"} and isinstance(value.get("pokemon_id"), str) and value["pokemon_id"]:
        return value["pokemon_id"]
    return None


def _side(pokemon_id):
    return {
        "active_slot_index": 0,
        "pokemon": {0: {
            "pokemon_id": pokemon_id,
            "current_hp": make_unknown_battle_fact(),
            "max_hp": make_unknown_battle_fact(),
            "fainted": make_unknown_battle_fact(),
            "current_type": make_unknown_battle_fact(),
            "condition": make_unknown_battle_fact(),
            "known_item": make_unknown_battle_fact(),
        }},
        "side_conditions": make_unknown_battle_fact(),
        "tailwind_status": make_unknown_battle_fact(),
    }
