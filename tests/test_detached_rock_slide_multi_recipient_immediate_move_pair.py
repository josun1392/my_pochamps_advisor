"""Focused nested-pair coverage for the frozen Rock Slide recipient DAG."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_detached_rock_slide_multi_recipient_immediate_move_pair import (
    materialize_detached_rock_slide_multi_recipient_immediate_move_pair,
)
from llm.advisor_runtime_d0_doubles_action_target_set_authority import (
    freeze_runtime_d0_doubles_action_target_set_authority,
)
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import (
    freeze_runtime_d0_multi_recipient_action_execution_scope_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _equal_speed_order, _metadata
from tests.test_detached_rock_slide_multi_recipient_predictive_graph_materialization import _inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _opponent_action(d0, move_id="tackle"):
    return {
        "status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": f"opponent_attack:{move_id}", "move_id": move_id,
        "selectability": "selectable", "usability": {"status": "known_usable"},
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "opponent_actor": deepcopy(d0["active_owners"]["opponent"]),
        "target_owner": deepcopy(d0["active_owners"]["self"]),
        "metadata_authority": _metadata(move_id),
    }


def _pair(*, accuracy=100, target_hp=100, order="own_first", move_id="tackle"):
    _state, snapshot, d0, action, scope = _inputs(accuracy=accuracy, target_hp=target_hp)
    opponent = _opponent_action(d0, move_id)
    authority = _equal_speed_order(d0, action, opponent) if order == "unresolved_tie" else _order(d0, action, opponent, order)
    return materialize_detached_rock_slide_multi_recipient_immediate_move_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent,
        action_order_authority=authority, execution_scope_authority=scope,
    )


def _high_hp_rock_slide_inputs():
    state, _snapshot, _d0, action, _scope = _inputs(accuracy=100)
    state["self_side"]["pokemon"][0].update(current_hp=200, max_hp=200)
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"]})
    move = deepcopy(action["move_metadata_authority"])
    move.update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=deepcopy(d0["decision_owner"]), active_attacker=deepcopy(d0["decision_owner"]))
    action = {**action, "move_metadata_authority": move}
    targets = freeze_runtime_d0_doubles_action_target_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, acting_owner=d0["decision_owner"], decision_point="turn:1")
    scope = freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=targets)
    return snapshot, d0, action, scope


def test_rock_slide_first_attaches_second_action_to_exact_terminal_source_without_changing_recipients():
    pair = _pair(order="own_first")
    assert pair["status"] == "evaluable", pair.get("reason")
    transition = pair["order_graphs"][0]["terminal_transitions"][0]
    assert transition["second_action"]["state"] == "outcome_ledger"
    assert transition["second_action"]["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert transition["rock_slide_terminal_source"]["terminal_edge_id"] == transition["first_terminal_source_id"]
    assert len(transition["recipient_vector"]["ordered_recipient_states"]) == 2
    assert transition["path_probability_factorization"]["order_weighted_source_probability"] == transition["incoming_path_probability"]
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_rock_slide_first_cancels_exact_fainted_pending_actor_without_second_execution():
    pair = _pair(accuracy=100, target_hp=1, order="own_first")
    assert pair["status"] == "evaluable", pair.get("reason")
    transitions = pair["order_graphs"][0]["terminal_transitions"]
    assert transitions
    assert {row["second_action"]["state"] for row in transitions} == {"cancelled_due_to_faint"}
    assert all(row["second_action"]["conditional_probability"] == {"numerator": 1, "denominator": 1} for row in transitions)
    assert all(row["pending_actor"] == row["recipient_vector"]["ordered_recipient_states"][0]["owner"] for row in transitions)


def test_opponent_first_uses_actor_overlay_and_equal_speed_keeps_two_half_roots():
    snapshot, d0, action, scope = _high_hp_rock_slide_inputs()
    opponent = _opponent_action(d0, "seismic-toss")
    second = materialize_detached_rock_slide_multi_recipient_immediate_move_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent,
        action_order_authority=_order(d0, action, opponent, "opponent_first"), execution_scope_authority=scope,
    )
    assert second["status"] == "evaluable", second.get("reason")
    transition = second["order_graphs"][0]["terminal_transitions"][0]
    assert transition["second_action"]["state"] == "rock_slide_graph"
    assert transition["second_action"]["rock_slide_graph"]["status"] == "evaluable"
    assert transition["recipient_vector"]["rock_slide_actor_state"]["owner"] == transition["pending_actor"]
    assert transition["path_probability_factorization"]["order_weighted_source_probability"]["numerator"] > 0

    tied = _pair(target_hp=1, order="unresolved_tie", move_id="seismic-toss")
    assert tied["status"] == "evaluable", tied.get("reason")
    assert {row["action_order"] for row in tied["order_graphs"]} == {"own_first", "opponent_first"}
    assert all(row["order_conditional_probability"] == {"numerator": 1, "denominator": 2} for row in tied["order_graphs"])
    assert tied["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_mismatched_frozen_scope_fails_closed():
    _state, snapshot, d0, action, scope = _inputs(accuracy=0)
    opponent = _opponent_action(d0)
    invalid = deepcopy(scope)
    invalid["recipients"] = tuple(reversed(invalid["recipients"]))
    pair = materialize_detached_rock_slide_multi_recipient_immediate_move_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent,
        action_order_authority=_order(d0, action, opponent, "own_first"), execution_scope_authority=invalid,
    )
    assert pair["status"] == "rejected"
