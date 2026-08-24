from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    freeze_runtime_d0_probabilistic_self_stage_effect_authority,
    freeze_runtime_strategy_d0,
)
from tests.test_runtime_d0_native_damage_context import _state as _native_state


def _state(session="runtime-probabilistic-self-stage"):
    state = _native_state(session)
    attacker = state["self_side"]["pokemon"][0]
    attacker["stat_stages"] = {"attack": 0}
    attacker["current_ability"] = "pressure"
    attacker["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    return state


def _owner(state, side="self"):
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _d0(state):
    snapshot = _snapshot(state)
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))


def _move(**overrides):
    move = {
        "move_id": "metal-claw", "category": "physical", "power": 50,
        "effect_chance": 10, "stat_changes": [{"stat": "attack", "change": 1}],
    }
    move.update(overrides)
    return move


def _sheer_force(state, status="applicable"):
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["current_ability"] = "sheer-force"
    pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["ability_applicability_context"] = {
        "schema_version": "ability-applicability-context-v1", "session_id": state["session_id"],
        "source": {key: _owner(state)[key] for key in ("side", "slot_index", "pokemon_id")},
        "ability_id": "sheer-force", "status": status,
    }


def _resolve(state, move=None):
    snapshot, d0 = _d0(state)
    return freeze_runtime_d0_probabilistic_self_stage_effect_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state),
        target=_owner(state, "opponent"), move_metadata=_move() if move is None else move,
    )


def test_runtime_projects_metal_claw_capability_and_exact_zero_or_nonzero_attack_stage():
    zero = _resolve(_state())
    nonzero_state = _state(); nonzero_state["self_side"]["pokemon"][0]["stat_stages"] = {"attack": 3}
    nonzero = _resolve(nonzero_state)
    assert zero["status"] == "resolved" and zero["capability_resolution"]["probability"] == {"numerator": 10, "denominator": 100}
    assert zero["current_attack_stage"] == {"status": "known", "value": 0, "provenance": "runtime_battle_state_v1"}
    assert nonzero["current_attack_stage"]["value"] == 3


def test_sheer_force_and_capability_fail_closed_semantics_survive_runtime_projection():
    suppressed_state = _state(); _sheer_force(suppressed_state)
    suppressed = _resolve(suppressed_state)
    unknown_state = _state(); _sheer_force(unknown_state, "unknown")
    unknown = _resolve(unknown_state)
    serene_state = _state(); serene_state["self_side"]["pokemon"][0]["current_ability"] = "serene-grace"
    serene_state["self_side"]["pokemon"][0]["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    serene = _resolve(serene_state)
    missing = _resolve(_state())
    missing_state = _state()
    missing_state["self_side"]["pokemon"][0].pop("current_ability")
    missing_state["self_side"]["pokemon"][0].pop("current_ability_provenance")
    missing = _resolve(missing_state)
    assert suppressed["status"] == "resolved" and suppressed["capability_resolution"]["suppressed"] is True
    assert suppressed["capability_resolution"]["probability"] == {"numerator": 0, "denominator": 100}
    assert unknown["status"] == "incomplete" and unknown["reason"] == "sheer_force_applicability_unknown"
    assert serene["status"] == "unsupported"
    assert missing["status"] == "incomplete" and missing["reason"] == "attacker_ability_unknown"


def test_attack_stage_unknown_stale_and_identity_move_mismatches_fail_closed_without_mutation():
    state = _state(); state["self_side"]["pokemon"][0].pop("stat_stages")
    incomplete = _resolve(state)
    assert incomplete["status"] == "incomplete" and incomplete["reason"] == "attacker_attack_stage_unknown"
    state = _state(); snapshot, d0 = _d0(state)
    resolved = freeze_runtime_d0_probabilistic_self_stage_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move())
    state["self_side"]["pokemon"][0]["stat_stages"]["attack"] = 6
    stale = freeze_runtime_d0_probabilistic_self_stage_effect_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=_move())
    assert resolved["current_attack_stage"]["value"] == 0 and stale["status"] == "rejected"
    assert freeze_runtime_d0_probabilistic_self_stage_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_metadata=_move())["status"] == "rejected"
    assert freeze_runtime_d0_probabilistic_self_stage_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "metal-claw"})["status"] == "incomplete"


def test_native_damage_is_independent_and_runtime_adapter_does_not_mutate_state():
    state = _state(); original = deepcopy(state)
    result = _resolve(state)
    snapshot, d0 = _d0(state)
    native = build_runtime_d0_native_damage_context(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"),
        move_metadata={"move_id": "water-gun", "category": "special", "power": 40, "type": "water"},
    )
    assert result["status"] == "resolved" and state == original
    assert "probabilistic_self_stage" not in native
