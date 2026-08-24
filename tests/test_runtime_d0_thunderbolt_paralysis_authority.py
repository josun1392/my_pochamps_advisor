from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_probabilistic_target_stage_effect_authority,
    freeze_runtime_d0_thunderbolt_paralysis_authority,
    freeze_runtime_strategy_d0,
)
from tests.test_runtime_d0_native_damage_context import _state as _native_state


def _owner(state, side="self"):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _state(session="runtime-thunderbolt-paralysis"):
    state = _native_state(session)
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["current_ability"] = "pressure"
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    target = state["opponent_side"]["pokemon"][0]
    target["condition"] = None
    target["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
    target["current_type"] = ["water"]
    target["known_item"] = None
    target["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
    state["substitute_state_context"] = {"schema_version": "detached-substitute-state-v1", "session_id": state["session_id"], "provenance": "trusted_current_substitute_authority_v1", "states": [{"owner": _owner(state), "state": "known_inactive", "substitute_hp": None}, {"owner": _owner(state, "opponent"), "state": "known_inactive", "substitute_hp": None}]}
    return state


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _d0(state):
    snapshot = _snapshot(state)
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))


def _move(**overrides):
    move = {"move_id": "thunderbolt", "category": "special", "power": 90, "target": "selected-pokemon", "effect_chance": 10, "ailment": "paralysis"}
    move.update(overrides)
    return move


def _resolve(state, move=None):
    snapshot, d0 = _d0(state)
    return freeze_runtime_d0_thunderbolt_paralysis_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move() if move is None else move)


def _sheer_force(state, status="applicable"):
    state["self_side"]["pokemon"][0]["current_ability"] = "sheer-force"
    state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state["session_id"], "source": {key: _owner(state)[key] for key in ("side", "slot_index", "pokemon_id")}, "ability_id": "sheer-force", "status": status}


def _shield_dust(state, status="affecting"):
    state["opponent_side"]["pokemon"][0]["current_ability"] = "shield-dust"
    state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state["session_id"], "source": {key: _owner(state, "opponent")[key] for key in ("side", "slot_index", "pokemon_id")}, "target": {key: _owner(state)[key] for key in ("side", "slot_index", "pokemon_id")}, "status": status}


def test_runtime_projects_strict_condition_exact_types_and_substitute_for_eligible_thunderbolt():
    result = _resolve(_state())
    assert result["status"] == "resolved"
    assert result["capability_resolution"]["probability"] == {"numerator": 10, "denominator": 100}
    assert result["source_authority"]["target_condition"] == {"status": "known_none"}
    assert result["target_type_authority"] == {"status": "known", "values": ["water"]}
    assert result["target_substitute_authority"] == {"status": "known", "state": "known_inactive"}


def test_condition_type_and_suppressors_preserve_resolved_zero_probability():
    condition = _state(); target = condition["opponent_side"]["pokemon"][0]; target["condition"] = "burn"; target["condition_provenance"]["condition"] = "burn"
    electric = _state(); electric["opponent_side"]["pokemon"][0]["current_type"] = ["electric"]
    sheer = _state(); _sheer_force(sheer)
    dust = _state(); _shield_dust(dust)
    cloak = _state(); cloak["opponent_side"]["pokemon"][0].update(known_item="covert-cloak", known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"})
    assert _resolve(condition)["capability_resolution"]["ineligible_by"] == ("target_condition",)
    assert _resolve(electric)["capability_resolution"]["ineligible_by"] == ("target_types",)
    assert _resolve(sheer)["capability_resolution"]["suppressed_by"] == ("attacker_ability",)
    assert _resolve(dust)["capability_resolution"]["suppressed_by"] == ("target_ability",)
    assert _resolve(cloak)["capability_resolution"]["suppressed_by"] == ("target_item",)


def test_unknown_source_substitute_and_limbers_unsupported_contract_fail_closed():
    unknown_condition = _state(); unknown_condition["opponent_side"]["pokemon"][0].pop("condition_provenance")
    unknown_type = _state(); unknown_type["opponent_side"]["pokemon"][0]["current_type"] = {"knowledge": "unknown"}; unknown_type["opponent_side"]["pokemon"][0].pop("current_type_provenance", None)
    unknown_substitute = _state(); unknown_substitute["substitute_state_context"]["states"][1] = {"owner": _owner(unknown_substitute, "opponent"), "state": "unknown", "substitute_hp": None}
    limber = _state(); limber["opponent_side"]["pokemon"][0]["current_ability"] = "limber"
    assert _resolve(unknown_condition)["status"] == "incomplete" and _resolve(unknown_condition)["reason"] == "target_current_condition_unknown"
    assert _resolve(unknown_type)["status"] == "incomplete" and _resolve(unknown_type)["reason"] == "target_types_unknown"
    assert _resolve(unknown_substitute)["status"] == "incomplete" and _resolve(unknown_substitute)["reason"] == "target_substitute_unknown"
    assert _resolve(limber)["status"] == "unsupported"


def test_stale_identity_move_and_existing_target_stage_adapter_remain_isolated():
    state = _state(); snapshot, d0 = _d0(state)
    state["opponent_side"]["pokemon"][0]["current_type"] = ["electric"]
    assert freeze_runtime_d0_thunderbolt_paralysis_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move())["status"] == "rejected"
    assert freeze_runtime_d0_thunderbolt_paralysis_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_metadata=_move())["status"] == "rejected"
    assert freeze_runtime_d0_thunderbolt_paralysis_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "thunderbolt"})["status"] == "incomplete"
    original = deepcopy(state)
    fresh = _snapshot(state); fresh_d0 = freeze_runtime_strategy_d0(runtime_snapshot=fresh, decision_owner=_owner(state))
    shadow = freeze_runtime_d0_probabilistic_target_stage_effect_authority(strategy_d0=fresh_d0, runtime_snapshot=fresh, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "shadow-ball", "category": "special", "power": 80, "target": "selected-pokemon", "effect_chance": 20, "stat_changes": [{"stat": "special-defense", "change": -1}]})
    assert state == original and shadow["status"] == "resolved"
