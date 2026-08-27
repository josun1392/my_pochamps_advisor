from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_iron_head_flinch_authority,
    freeze_runtime_strategy_d0,
)
from tests.test_runtime_d0_native_damage_context import _state as _native_state


def _owner(state, side="self"):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _state(session="runtime-iron-head-flinch"):
    state = _native_state(session)
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["current_ability"] = "pressure"
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    target = state["opponent_side"]["pokemon"][0]
    target["condition"] = None
    target["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
    target["known_item"] = None
    target["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
    state["substitute_state_context"] = {"schema_version": "detached-substitute-state-v1", "session_id": state["session_id"], "provenance": "trusted_current_substitute_authority_v1", "states": [{"owner": _owner(state), "state": "known_inactive", "substitute_hp": None}, {"owner": _owner(state, "opponent"), "state": "known_inactive", "substitute_hp": None}]}
    return state


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _move(**overrides):
    move = {"move_id": "iron-head", "category": "physical", "power": 80, "target": "selected-pokemon", "effect_chance": 30, "ailment": "flinch"}
    move.update(overrides)
    return move


def _resolve(state, move=None):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return freeze_runtime_d0_iron_head_flinch_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move() if move is None else move)


def test_runtime_freezes_exact_iron_head_flinch_authority_without_mutating_state():
    state = _state(); original = deepcopy(state)
    result = _resolve(state)
    assert result["status"] == "resolved"
    assert result["capability_resolution"]["probability"] == {"numerator": 30, "denominator": 100}
    assert result["target_substitute_authority"] == {"status": "known", "state": "known_inactive"}
    assert state == original


def test_metadata_modifier_and_stale_bindings_fail_closed():
    assert _resolve(_state(), _move(effect_chance=20))["status"] == "unsupported"
    cloak = _state()
    cloak["opponent_side"]["pokemon"][0].update(known_item="covert-cloak", known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"})
    assert _resolve(cloak)["status"] == "unsupported"
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    state["opponent_side"]["pokemon"][0]["current_hp"] -= 1
    assert freeze_runtime_d0_iron_head_flinch_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move())["status"] == "rejected"
