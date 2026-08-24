from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_probabilistic_target_stage_effect_authority,
    freeze_runtime_d0_probabilistic_self_stage_effect_authority,
    freeze_runtime_strategy_d0,
)
from tests.test_runtime_d0_native_damage_context import _state as _native_state


def _owner(state, side="self"):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _state(session="runtime-probabilistic-target-stage"):
    state = _native_state(session)
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["current_ability"] = "pressure"
        pokemon["current_ability_provenance"] = {
            "event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1,
        }
    target = state["opponent_side"]["pokemon"][0]
    target["known_item"] = None
    target["known_item_provenance"] = {
        "event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1,
        "status": "known_absent",
    }
    state["substitute_state_context"] = {
        "schema_version": "detached-substitute-state-v1", "session_id": state["session_id"],
        "provenance": "trusted_current_substitute_authority_v1",
        "states": [
            {"owner": _owner(state), "state": "known_inactive", "substitute_hp": None},
            {"owner": _owner(state, "opponent"), "state": "known_inactive", "substitute_hp": None},
        ],
    }
    return state


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _d0(state):
    snapshot = _snapshot(state)
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))


def _move(**overrides):
    move = {
        "move_id": "shadow-ball", "category": "special", "power": 80, "target": "selected-pokemon",
        "effect_chance": 20, "stat_changes": [{"stat": "special-defense", "change": -1}],
    }
    move.update(overrides)
    return move


def _resolve(state, move=None):
    snapshot, d0 = _d0(state)
    return freeze_runtime_d0_probabilistic_target_stage_effect_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"),
        move_metadata=_move() if move is None else move,
    )


def _sheer_force(state, status="applicable"):
    attacker = state["self_side"]["pokemon"][0]
    attacker["current_ability"] = "sheer-force"
    state["ability_applicability_context"] = {
        "schema_version": "ability-applicability-context-v1", "session_id": state["session_id"],
        "source": {key: _owner(state)[key] for key in ("side", "slot_index", "pokemon_id")},
        "ability_id": "sheer-force", "status": status,
    }


def _shield_dust(state, status="affecting"):
    target = state["opponent_side"]["pokemon"][0]
    target["current_ability"] = "shield-dust"
    state["ability_interaction_context"] = {
        "schema_version": "ability-interaction-context-v1", "session_id": state["session_id"],
        "source": {key: _owner(state, "opponent")[key] for key in ("side", "slot_index", "pokemon_id")},
        "target": {key: _owner(state)[key] for key in ("side", "slot_index", "pokemon_id")},
        "status": status,
    }


def test_runtime_projects_shadow_ball_and_preserves_exact_target_special_defense_stages():
    zero = _resolve(_state())
    nonzero_state = _state(); nonzero_state["opponent_side"]["pokemon"][0]["stat_stages"]["special-defense"] = -3
    nonzero = _resolve(nonzero_state)

    assert zero["status"] == "resolved"
    assert zero["capability_resolution"]["probability"] == {"numerator": 20, "denominator": 100}
    assert zero["current_target_special_defense_stage"] == {"status": "known", "value": 0, "provenance": "runtime_battle_state_v1"}
    assert zero["target_substitute_authority"] == {"status": "known", "state": "known_inactive"}
    assert nonzero["current_target_special_defense_stage"]["value"] == -3


def test_runtime_projects_suppressors_and_exact_item_absence_without_neutral_fabrication():
    sheer = _state(); _sheer_force(sheer)
    dust = _state(); _shield_dust(dust)
    cloak = _state(); cloak["opponent_side"]["pokemon"][0].update(
        known_item="covert-cloak",
        known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"},
    )
    unknown_item = _state(); unknown_item["opponent_side"]["pokemon"][0].pop("known_item"); unknown_item["opponent_side"]["pokemon"][0].pop("known_item_provenance")

    assert _resolve(sheer)["capability_resolution"]["probability"] == {"numerator": 0, "denominator": 100}
    assert _resolve(dust)["capability_resolution"]["suppressed_by"] == ("target_ability",)
    assert _resolve(cloak)["capability_resolution"]["suppressed_by"] == ("target_item",)
    absent = _resolve(_state())
    assert absent["source_authority"]["target_item"] == {"status": "known_absent"}
    unknown = _resolve(unknown_item)
    assert unknown["status"] == "incomplete" and unknown["reason"] == "target_item_unknown"


def test_missing_source_or_stage_and_unknown_substitute_fail_closed():
    sheer_unknown = _state(); _sheer_force(sheer_unknown, "unknown")
    stage_unknown = _state(); stage_unknown["opponent_side"]["pokemon"][0].pop("stat_stages")
    substitute_unknown = _state(); substitute_unknown["substitute_state_context"]["states"][1] = {"owner": _owner(substitute_unknown, "opponent"), "state": "unknown", "substitute_hp": None}
    ability_unknown = _state(); ability_unknown["opponent_side"]["pokemon"][0].pop("current_ability"); ability_unknown["opponent_side"]["pokemon"][0].pop("current_ability_provenance")

    assert _resolve(sheer_unknown)["reason"] == "sheer_force_applicability_unknown"
    assert _resolve(stage_unknown)["reason"] == "target_special_defense_stage_unknown"
    assert _resolve(substitute_unknown)["reason"] == "target_substitute_unknown"
    assert _resolve(ability_unknown)["reason"] == "target_ability_unknown"


def test_substitute_active_is_exact_and_stale_identity_and_move_mismatches_reject():
    active = _state(); active["substitute_state_context"]["states"][1] = {"owner": _owner(active, "opponent"), "state": "known_active", "substitute_hp": 25}
    resolved = _resolve(active)
    assert resolved["status"] == "resolved"
    assert resolved["target_substitute_authority"] == {"status": "known", "state": "known_active", "substitute_hp": 25}

    state = _state(); snapshot, d0 = _d0(state)
    state["opponent_side"]["pokemon"][0]["stat_stages"]["special-defense"] = 6
    stale = freeze_runtime_d0_probabilistic_target_stage_effect_authority(
        strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move(),
    )
    assert stale["status"] == "rejected"
    assert freeze_runtime_d0_probabilistic_target_stage_effect_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_metadata=_move(),
    )["status"] == "rejected"
    assert freeze_runtime_d0_probabilistic_target_stage_effect_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "shadow-ball"},
    )["status"] == "incomplete"


def test_adapter_is_detached_and_existing_self_stage_adapter_stays_available():
    state = _state(); original = deepcopy(state)
    target = _resolve(state)
    self_state = _state(); self_state["self_side"]["pokemon"][0]["stat_stages"] = {"attack": 0}
    snapshot, d0 = _d0(self_state)
    self_effect = freeze_runtime_d0_probabilistic_self_stage_effect_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(self_state), target=_owner(self_state, "opponent"),
        move_metadata={"move_id": "metal-claw", "category": "physical", "power": 50, "effect_chance": 10, "stat_changes": [{"stat": "attack", "change": 1}]},
    )

    assert target["status"] == "resolved" and state == original
    assert self_effect["status"] == "resolved" and self_effect["capability_resolution"]["probability"] == {"numerator": 10, "denominator": 100}
