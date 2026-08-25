from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    LifecycleConfirmationBoundary, OPPONENT_RESPONSE_SET_SOURCE, USER_TRUST,
)
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import (
    freeze_runtime_d0_complete_opponent_response_set_authority,
)
from llm.advisor_runtime_d0_opponent_action_authority import (
    METADATA_SCHEMA_VERSION,
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


MOVES = ("tackle", "scratch", "growl", "tail-whip")


def _state():
    return create_unknown_bootstrap_battle_state("response-set", "self-a", "opponent-a")["state"]


def _owner(state, side):
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _metadata(move):
    category = "status" if move in {"growl", "tail-whip"} else "physical"
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": {"move_id": move, "category": category, "power": None if category == "status" else 40, "type": "normal", "accuracy": 100, "priority": 0}, "provenance": "repository_normalized_move_metadata_v1"}


def _observe_complete(state, usability=None):
    owner = _owner(state, "opponent")
    usability = usability or {move: {"status": "known_usable", "reason": None} for move in MOVES}
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": "response-set-1", "observation_sequence": 1, "planned_effect": "set_current_opponent_response_set", "trust": "user_confirmed_observation", **owner, "move_ids": list(MOVES), "move_usability": usability, "turn_number": 1}]}
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state"
    return result["projected_state"]


def _authority(state):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    actions = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={move: _metadata(move) for move in MOVES})
    return snapshot, d0, actions


def test_explicit_complete_response_set_composes_known_moves_and_usability():
    state = _observe_complete(_state(), {**{move: {"status": "known_usable", "reason": None} for move in MOVES}, "scratch": {"status": "known_unusable", "reason": "disabled"}})
    snapshot, d0, actions = _authority(state)
    result = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)

    assert result["status"] == "resolved"
    assert result["moveset_completeness"] == "complete"
    assert result["selectable_response_action_ids"] == ("opponent_attack:tackle", "opponent_attack:growl", "opponent_attack:tail-whip")
    assert result["actions"][1]["selectability"] == "not_selectable"
    assert "probability" not in repr(result)


def test_four_known_moves_without_explicit_completeness_and_partial_movesets_fail_closed():
    state = _state(); pokemon = state["opponent_side"]["pokemon"][0]
    pokemon["known_move_ids"] = list(MOVES)
    pokemon["known_move_ids_provenance"] = {move: {"event_kind": "used_move_observed", "trust": "user_confirmed_observation", "source_observation_id": move, "source_sequence": index} for index, move in enumerate(MOVES, 1)}
    snapshot, d0, actions = _authority(state)
    assert freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)["status"] == "incomplete"

    partial = _state(); partial["opponent_side"]["pokemon"][0]["known_move_ids"] = ["tackle"]
    partial["opponent_side"]["pokemon"][0]["known_move_ids_provenance"] = {"tackle": {"event_kind": "used_move_observed", "trust": "user_confirmed_observation", "source_observation_id": "t", "source_sequence": 1}}
    snapshot, d0, actions = _authority(partial)
    assert freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)["status"] == "incomplete"


def test_unknown_usability_and_binding_mismatch_fail_closed_without_transferring_state():
    complete = _observe_complete(_state())
    unknown = deepcopy(complete); unknown["opponent_side"]["pokemon"][0]["current_move_usability"].pop("scratch")
    snapshot, d0, actions = _authority(unknown)
    assert freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)["status"] == "incomplete"

    snapshot, d0, actions = _authority(complete)
    switched = deepcopy(complete); switched["opponent_side"]["pokemon"][0]["pokemon_id"] = "other"
    rejected = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=_snapshot(switched), opponent_known_move_authority=actions)
    assert rejected["status"] == "rejected"


def test_response_set_output_is_detached_and_requires_a_selectable_move():
    all_unusable = {move: {"status": "known_unusable", "reason": "disabled"} for move in MOVES}
    state = _observe_complete(_state(), all_unusable)
    snapshot, d0, actions = _authority(state)
    assert freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)["status"] == "incomplete"

    state = _observe_complete(_state())
    snapshot, d0, actions = _authority(state)
    result = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)
    state["opponent_side"]["pokemon"][0]["known_move_ids"].clear()
    assert len(result["actions"]) == 4 and result["known_action_ids"] == tuple(f"opponent_attack:{move}" for move in MOVES)


def test_production_observation_and_replay_plan_can_supply_the_explicit_authority():
    state = _state(); opponent = _owner(state, "opponent")
    boundary = LifecycleConfirmationBoundary(state["session_id"], {"opponent": opponent, "self": _owner(state, "self")})
    confirmed = boundary.confirm(
        event_kind="current_opponent_response_set_observed",
        payload={"move_ids": list(MOVES), "move_usability": {move: {"status": "known_usable", "reason": None} for move in MOVES}},
        session_id=state["session_id"], source=OPPONENT_RESPONSE_SET_SOURCE,
        trust=USER_TRUST, confirmed=True, side=opponent["side"], slot_index=opponent["slot_index"], pokemon_id=opponent["pokemon_id"], turn_number=1,
    )
    assert confirmed["status"] == "confirmed"
    plan = build_replay_plan(state, [confirmed["observation"]], canonical_move_resolver=lambda move: {"move_id": move})
    applied = project_atomic_transition(state, plan, state["session_id"])
    assert applied["status"] == "ready_with_projected_state"
    snapshot, d0, actions = _authority(applied["projected_state"])
    assert freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=actions)["status"] == "resolved"
