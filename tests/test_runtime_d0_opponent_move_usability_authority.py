from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_opponent_action_authority import (
    METADATA_SCHEMA_VERSION, compose_runtime_d0_opponent_move_usability,
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_d0_opponent_move_usability_authority import (
    freeze_runtime_d0_opponent_move_usability_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state() -> dict:
    return create_unknown_bootstrap_battle_state("opponent-usability", "self-a", "opponent-a")["state"]


def _owner(state: dict, side: str) -> dict:
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _metadata(move: str) -> dict:
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": {"move_id": move, "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}, "provenance": "repository_normalized_move_metadata_v1"}


def _known(state: dict, move: str = "tackle") -> None:
    pokemon = state["opponent_side"]["pokemon"][0]
    pokemon["known_move_ids"] = [move]
    pokemon["known_move_ids_provenance"] = {move: {"event_kind": "used_move_observed", "trust": "user_confirmed_observation", "source_observation_id": "used-1", "source_sequence": 1}}


def _action_and_d0(state: dict) -> tuple[dict, dict, dict]:
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    actions = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={"tackle": _metadata("tackle")})
    return snapshot, d0, actions["actions"][0]


def _observe(state: dict, status: str, reason=None, sequence: int = 2) -> dict:
    opponent = _owner(state, "opponent")
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": f"use-{sequence}", "observation_sequence": sequence, "planned_effect": "set_current_move_usability", "trust": "user_confirmed_observation", **opponent, "canonical_move_id": "tackle", "usability": status, "reason": reason, "turn_number": 1}]}
    projected = project_atomic_transition(state, plan, state["session_id"])
    assert projected["status"] == "ready_with_projected_state"
    return projected["projected_state"]


def test_explicit_current_observation_is_the_only_source_of_known_usable_or_unusable() -> None:
    state = _state(); _known(state)
    unknown_snapshot, unknown_d0, action = _action_and_d0(state)
    unknown = freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=unknown_d0, runtime_snapshot=unknown_snapshot, opponent_action=action)
    assert unknown["status"] == "incomplete" and unknown["usability"]["status"] == "unknown"

    usable_state = _observe(state, "known_usable")
    snapshot, d0, action = _action_and_d0(usable_state)
    usable = freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=action)
    assert usable["status"] == "resolved" and usable["usability"]["status"] == "known_usable" and usable["selectability"] == "selectable"
    composed = compose_runtime_d0_opponent_move_usability(opponent_action=action, usability_authority=usable)
    assert composed["selectability"] == "selectable" and composed["status"] == "resolved"

    unusable_state = _observe(state, "known_unusable", "disabled")
    snapshot, d0, action = _action_and_d0(unusable_state)
    unusable = freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=action)
    composed = compose_runtime_d0_opponent_move_usability(opponent_action=action, usability_authority=unusable)
    assert unusable["usability"]["status"] == "known_unusable"
    assert composed["selectability"] == "not_selectable" and composed["usability"]["reason"] == "disabled"


def test_usability_is_identity_and_latest_observation_bound_without_history_inference() -> None:
    state = _state()
    _known(state)
    current = _observe(state, "known_usable")
    snapshot, d0, action = _action_and_d0(current)
    assert freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=action)["status"] == "resolved"

    stale = deepcopy(current); stale["last_applied_observation_sequence"] = 3
    stale_snapshot, stale_d0, stale_action = _action_and_d0(stale)
    result = freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=stale_d0, runtime_snapshot=stale_snapshot, opponent_action=stale_action)
    assert result["status"] == "incomplete" and result["reason"] == "opponent_move_usability_observation_not_current"

    mismatched = deepcopy(action); mismatched["move_id"] = "scratch"
    assert freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=mismatched)["status"] == "rejected"
    changed = deepcopy(current); changed["opponent_side"]["pokemon"][0]["pokemon_id"] = "other"
    assert freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=d0, runtime_snapshot=_snapshot(changed), opponent_action=action)["status"] == "rejected"


def test_composition_keeps_unknown_incomplete_and_rejects_mismatched_authority() -> None:
    state = _state(); _known(state)
    snapshot, d0, action = _action_and_d0(state)
    unknown = freeze_runtime_d0_opponent_move_usability_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=action)
    composed = compose_runtime_d0_opponent_move_usability(opponent_action=action, usability_authority=unknown)
    assert composed["status"] == "resolved" and composed["selectability"] == "unknown"
    wrong = {**unknown, "move_id": "scratch"}
    rejected = compose_runtime_d0_opponent_move_usability(opponent_action=action, usability_authority=wrong)
    assert rejected["status"] == "rejected" and rejected["selectability"] == "unknown"
