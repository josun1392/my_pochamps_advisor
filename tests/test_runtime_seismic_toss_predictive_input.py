from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_seismic_toss_predictive_input,
    freeze_runtime_strategy_d0,
)


def _state(session: str = "runtime-seismic") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False)
    target = state["opponent_side"]["pokemon"][0]
    target["current_type"] = ["water"]
    target["current_type_provenance"] = {
        "event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1,
    }
    return state


def _snapshot(state: dict) -> dict:
    return {
        "status": "runtime_snapshot_ready", "session_id": state["session_id"],
        "state": deepcopy(state), "state_fingerprint": state_fingerprint(state),
    }


def _owner(state: dict, side: str = "self") -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def test_runtime_seismic_producer_freezes_known_hp_type_but_keeps_untracked_level_and_substitute_incomplete() -> None:
    state = _state(); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))

    result = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="seismic-toss",
    )
    snapshot["state"]["opponent_side"]["pokemon"][0]["current_type"] = ["ghost"]

    assert result["status"] == "incomplete"
    assert result["target_hp_authority"] == {"status": "known", "current_hp": 100, "max_hp": 100}
    assert result["target_type_authority"]["value"] == ["water"]
    assert result["missing_authority"] == ["attacker_level_runtime_untracked", "substitute_state_unknown"]
    assert "observed" not in result["provenance"]


def test_runtime_seismic_producer_rejects_stale_foreign_or_unsupported_bindings() -> None:
    state = _state(); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    advanced = deepcopy(state); advanced["last_applied_observation_sequence"] = 1

    assert freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=_snapshot(advanced), attacker=_owner(state), target=_owner(state, "opponent"), move_id="seismic-toss",
    )["status"] == "rejected"
    assert freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="night-shade",
    )["reason"] == "unsupported_predictive_move"
    assert freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_id="seismic-toss",
    )["reason"] == "runtime_predictive_identity_mismatch"


def test_runtime_seismic_producer_is_side_neutral_and_preserves_unknown_target_type() -> None:
    state = _state(); state["self_side"]["pokemon"][0]["current_type"] = {"knowledge": "unknown"}
    state["self_side"]["pokemon"][0]["current_type_provenance"] = None
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "opponent"))

    result = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_id="seismic-toss",
    )

    assert result["status"] == "incomplete"
    assert result["target_type_authority"] == {"status": "unknown", "reason": "target_type_unknown"}
    assert result["attacker"] == _owner(state, "opponent")
