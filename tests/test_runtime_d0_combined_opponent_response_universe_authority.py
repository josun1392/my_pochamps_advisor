from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import OPPONENT_RESPONSE_SET_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_combined_opponent_response_universe_authority import (
    freeze_runtime_d0_combined_opponent_response_universe_authority,
)
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import (
    freeze_runtime_d0_complete_opponent_response_set_authority,
)
from llm.advisor_runtime_d0_opponent_action_authority import (
    METADATA_SCHEMA_VERSION,
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_d0_opponent_switch_response_authority import (
    freeze_runtime_d0_opponent_switch_response_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


MOVES = ("tackle", "scratch", "growl", "tail-whip")


def _state():
    state = create_unknown_bootstrap_battle_state("combined", "self", "opponent")["state"]
    bench = deepcopy(state["opponent_side"]["pokemon"][0]); bench["pokemon_id"] = "bench"
    state["opponent_side"]["pokemon"][1] = bench
    return state


def _owner(state, side):
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _metadata(move):
    category = "status" if move in {"growl", "tail-whip"} else "physical"
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": {"move_id": move, "category": category, "power": None if category == "status" else 40, "type": "normal", "accuracy": 100, "priority": 0}, "provenance": "repository_normalized_move_metadata_v1"}


def _observed(state, *, usability=None, permission="permitted"):
    usability = usability or {move: {"status": "known_usable", "reason": None} for move in MOVES}
    owner = _owner(state, "opponent")
    boundary = LifecycleConfirmationBoundary(state["session_id"], {"self": _owner(state, "self"), "opponent": owner})
    confirmed = boundary.confirm(
        event_kind="current_opponent_response_set_observed",
        payload={"move_ids": list(MOVES), "move_usability": usability},
        session_id=state["session_id"], source=OPPONENT_RESPONSE_SET_SOURCE, trust=USER_TRUST,
        confirmed=True, side="opponent", slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], turn_number=1,
    )
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": "moves", "observation_sequence": 1, "planned_effect": "set_current_opponent_response_set", "trust": "user_confirmed_observation", **owner, "move_ids": list(MOVES), "move_usability": usability, "turn_number": 1}]}
    result = project_atomic_transition(state, plan, state["session_id"])
    assert confirmed["status"] == "confirmed" and result["status"] == "ready_with_projected_state"
    current = result["projected_state"]
    current["opponent_side"]["current_opponent_switch_response_set"] = {
        "schema_version": "current-opponent-switch-response-set-v1", "permission": permission,
        "target_set_completeness": "complete", "targets": [{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}],
        "active_owner": owner,
        "provenance": {"event_kind": "current_opponent_switch_response_set_observed", "trust": "user_confirmed_observation", "source_sequence": 1, "turn_number": 1},
    }
    return current


def _authorities(state):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={move: _metadata(move) for move in MOVES})
    moves = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    switches = freeze_runtime_d0_opponent_switch_response_authority(strategy_d0=d0, runtime_snapshot=snapshot)
    return snapshot, d0, moves, switches


def _combined(snapshot, d0, moves, switches):
    return freeze_runtime_d0_combined_opponent_response_universe_authority(strategy_d0=d0, runtime_snapshot=snapshot, move_response_authority=moves, switch_response_authority=switches)


def test_complete_move_and_switch_universe_preserves_kind_and_order():
    snapshot, d0, moves, switches = _authorities(_observed(_state()))
    result = _combined(snapshot, d0, moves, switches)
    assert result["status"] == "resolved"
    assert result["universe_state"] == "complete_with_selectable_responses"
    assert result["selectable_response_action_ids"][-1] == "opponent_switch:combined:1:bench"
    assert [action["response_kind"] for action in result["actions"]] == ["move", "move", "move", "move", "switch"]
    assert result["response_probability"] == "not_modeled"


def test_blocked_switching_is_a_complete_move_only_universe():
    snapshot, d0, moves, switches = _authorities(_observed(_state(), permission="blocked"))
    result = _combined(snapshot, d0, moves, switches)
    assert result["status"] == "resolved"
    assert result["universe_state"] == "complete_with_selectable_responses"
    assert all(action["response_kind"] == "move" for action in result["actions"][:-1])
    assert result["switch_dimension"]["selectable_response_action_ids"] == ()


def test_complete_zero_selectable_moves_can_form_switch_only_or_zero_universe():
    unusable = {move: {"status": "known_unusable", "reason": "disabled"} for move in MOVES}
    snapshot, d0, moves, switches = _authorities(_observed(_state(), usability=unusable))
    switch_only = _combined(snapshot, d0, moves, switches)
    assert moves["status"] == "incomplete" and moves["reason"] == "no_currently_selectable_opponent_response"
    assert switch_only["status"] == "resolved"
    assert switch_only["universe_state"] == "complete_with_selectable_responses"
    assert switch_only["selectable_response_action_ids"] == ("opponent_switch:combined:1:bench",)

    snapshot, d0, moves, switches = _authorities(_observed(_state(), usability=unusable, permission="blocked"))
    zero = _combined(snapshot, d0, moves, switches)
    assert zero["status"] == "resolved"
    assert zero["universe_state"] == "complete_zero_response_universe"
    assert zero["selectable_response_action_ids"] == ()


def test_unknown_or_partial_dimensions_and_mismatches_fail_closed():
    snapshot, d0, moves, switches = _authorities(_observed(_state()))
    unknown_switch = deepcopy(switches); unknown_switch["status"] = "incomplete"; unknown_switch["reason"] = "opponent_switch_permission_unknown"
    assert _combined(snapshot, d0, moves, unknown_switch)["status"] == "incomplete"

    partial_moves = deepcopy(moves); partial_moves["status"] = "incomplete"; partial_moves["reason"] = "opponent_moveset_completeness_unknown"
    assert _combined(snapshot, d0, partial_moves, switches)["status"] == "incomplete"

    mismatched = deepcopy(moves); mismatched["source_runtime_fingerprint"] = "other"
    assert _combined(snapshot, d0, mismatched, switches)["status"] == "rejected"

    stale = deepcopy(snapshot); stale["state"]["last_applied_observation_sequence"] = 2; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert _combined(stale, d0, moves, switches)["status"] == "rejected"
