"""Runtime Water Gun authority is a strict incomplete boundary until stats exist."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_strategy_d0,
    freeze_runtime_water_gun_predictive_input,
)
from llm.advisor_substitute import update_substitute_state_context


def _state(session: str = "runtime-water-gun") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    attacker, target = state["self_side"]["pokemon"][0], state["opponent_side"]["pokemon"][0]
    attacker.update(current_level=50, current_type=["water"])
    attacker["current_level_provenance"] = {"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    for pokemon, types in ((attacker, ["water"]), (target, ["fire"])):
        pokemon["current_type"] = types
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    target_owner = _owner(state, "opponent")
    state["substitute_state_context"] = update_substitute_state_context(
        context=None, session_id=session, owner=target_owner, state="known_inactive", substitute_hp=None,
        provenance="runtime_observed_substitute_state_v1",
    )
    return state


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _owner(state: dict, side: str = "self") -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def test_runtime_water_gun_boundary_freezes_known_d0_fields_but_never_infers_final_stats() -> None:
    state = _state(); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="water-gun",
    )
    snapshot["state"]["self_side"]["pokemon"][0]["current_level"] = 1

    assert result["status"] == "incomplete"
    assert result["authority_fields"]["attacker_level"]["value"] == 50
    assert result["authority_fields"]["target_hp"]["value"] == {"current_hp": 100, "max_hp": 100}
    assert result["authority_fields"]["attacker_current_type"]["value"] == ["water"]
    assert result["authority_fields"]["substitute"]["state"] == "known_inactive"
    assert result["authority_fields"]["attacker_final_special_attack"] == {"status": "unknown", "reason": "runtime_final_special_attack_untracked"}
    assert "runtime_snapshot_damage_input_unavailable" in result["missing_authority"]


def test_runtime_water_gun_boundary_rejects_stale_foreign_and_wrong_move_inputs() -> None:
    state = _state(); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    advanced = deepcopy(state); advanced["last_applied_observation_sequence"] = 1

    assert freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=_snapshot(advanced), attacker=_owner(state), target=_owner(state, "opponent"), move_id="water-gun",
    )["status"] == "rejected"
    assert freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="surf",
    )["reason"] == "unsupported_predictive_move"
    assert freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_id="water-gun",
    )["reason"] == "runtime_predictive_identity_mismatch"


def test_runtime_water_gun_boundary_keeps_unknown_substitute_and_weather_unknown() -> None:
    state = _state(); state.pop("substitute_state_context")
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="water-gun",
    )

    assert result["authority_fields"]["substitute"] == {"status": "unknown", "reason": "runtime_substitute_unknown"}
    assert result["authority_fields"]["weather"] == {"status": "unknown", "reason": "runtime_weather_unknown"}
    assert "substitute" in result["missing_authority"]
