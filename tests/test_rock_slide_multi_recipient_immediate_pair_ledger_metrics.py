"""Strict ledger/metric tests for nested Rock Slide immediate pairs."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_doubles_action_target_set_authority import freeze_runtime_d0_doubles_action_target_set_authority
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import freeze_runtime_d0_multi_recipient_action_execution_scope_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_rock_slide_multi_recipient_immediate_pair_descriptive_metrics import (
    project_rock_slide_multi_recipient_immediate_pair_descriptive_metrics,
)
from llm.advisor_rock_slide_multi_recipient_immediate_pair_outcome_ledger import (
    iter_rock_slide_multi_recipient_immediate_pair_terminal_rows,
    normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger,
)
from tests.test_detached_rock_slide_multi_recipient_immediate_move_pair import _high_hp_rock_slide_inputs, _opponent_action, _pair
from tests.test_detached_rock_slide_multi_recipient_predictive_graph_materialization import _inputs, _wide_guard_authority
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order
from llm.advisor_detached_rock_slide_multi_recipient_immediate_move_pair import materialize_detached_rock_slide_multi_recipient_immediate_move_pair


def _ledger(**kwargs):
    pair = _pair(target_hp=1, order="own_first", **kwargs)
    result = normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=pair)
    assert result["status"] == "evaluable", result.get("reason")
    return result


def test_rock_slide_first_nested_ledger_accounts_each_source_once_and_metrics_preserve_final_recipients():
    ledger = _ledger()
    branch = ledger["order_branches"][0]
    assert branch["order"] == "own_first"
    assert branch["conditional_terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    rows = iter_rock_slide_multi_recipient_immediate_pair_terminal_rows(ledger=ledger)
    assert not isinstance(rows, str)
    rows = tuple(rows)
    assert sum(row["probability"] for row in rows) == 1
    assert {row["second_action_state"] for row in rows} == {"cancelled_due_to_faint"}
    assert all(row["pending_actor_state"]["fainted"] for row in rows)
    metrics = project_rock_slide_multi_recipient_immediate_pair_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved", metrics.get("reason")
    assert metrics["pending_second_action"]["cancelled_due_to_faint_probability"] == {"numerator": 1, "denominator": 1}
    assert all(row["faint_probability"] == {"numerator": 1, "denominator": 1} for row in metrics["recipients"])
    assert metrics["joint_final_states"]["probability_mass"] == {"numerator": 1, "denominator": 1}


def test_nested_ledger_rejects_probability_duplicate_source_and_false_cancellation():
    pair = _pair(target_hp=1, order="own_first")
    bad_probability = deepcopy(pair)
    bad_probability["order_graphs"][0]["terminal_transitions"][0]["path_probability_factorization"]["order_probability"] = {"numerator": 1, "denominator": 2}
    assert normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=bad_probability)["status"] == "rejected"

    duplicate = deepcopy(pair)
    duplicate["order_graphs"][0]["terminal_transitions"] = (*duplicate["order_graphs"][0]["terminal_transitions"], duplicate["order_graphs"][0]["terminal_transitions"][0])
    assert normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=duplicate)["status"] == "rejected"

    non_faint = deepcopy(pair)
    vector = non_faint["order_graphs"][0]["terminal_transitions"][0]["recipient_vector"]
    vector["ordered_recipient_states"] = tuple({**row, "hp": 1, "fainted": False} if row["owner"] == non_faint["opponent_actor"] else row for row in vector["ordered_recipient_states"])
    assert normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=non_faint)["status"] == "rejected"


def test_nested_ledger_rejects_stale_vector_scope_provenance():
    pair = _pair(target_hp=1, order="own_first")
    stale = deepcopy(pair)
    stale["order_graphs"][0]["terminal_transitions"][0]["recipient_vector"]["frozen_execution_scope_authority"]["action_id"] = "attack:foreign"
    assert normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=stale)["status"] == "rejected"


def test_rock_slide_second_and_equal_speed_order_masses_are_exact():
    snapshot, d0, action, scope = _high_hp_rock_slide_inputs()
    opponent = _opponent_action(d0, "seismic-toss")
    second = materialize_detached_rock_slide_multi_recipient_immediate_move_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent,
        action_order_authority=_order(d0, action, opponent, "opponent_first"), execution_scope_authority=scope,
    )
    ledger = normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=second)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["order_branches"][0]["order"] == "opponent_first"

    state, _snapshot, _d0, action, _scope = _inputs(accuracy=100, target_hp=1)
    state["self_side"]["pokemon"][0].update(current_hp=1, max_hp=100)
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"]})
    move = deepcopy(action["move_metadata_authority"]); move.update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=deepcopy(d0["decision_owner"]), active_attacker=deepcopy(d0["decision_owner"]))
    action = {**action, "move_metadata_authority": move}
    targets = freeze_runtime_d0_doubles_action_target_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, acting_owner=d0["decision_owner"], decision_point="turn:1")
    scope = freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=targets)
    opponent = _opponent_action(d0, "seismic-toss")
    tie = materialize_detached_rock_slide_multi_recipient_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent, action_order_authority={**_order(d0, action, opponent, "own_first"), "order": "unresolved_tie", "order_engine": {"status": "speed_tie"}}, execution_scope_authority=scope)
    equal = normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=tie)
    assert equal["status"] == "evaluable", equal.get("reason")
    assert {row["order_probability"]["numerator"] for row in equal["order_branches"]} == {1}
    assert {row["order_probability"]["denominator"] for row in equal["order_branches"]} == {2}
    assert equal["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_wide_guard_nested_pair_ledger_preserves_prevention_provenance_and_equal_speed_metrics():
    _state, snapshot, d0, action, scope = _inputs(accuracy=100)
    opponent = _opponent_action(d0, "wide-guard")
    authority = _wide_guard_authority(d0, snapshot, action, scope)
    pair = materialize_detached_rock_slide_multi_recipient_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent, action_order_authority={**_order(d0, action, opponent, "own_first"), "order": "unresolved_tie", "order_engine": {"status": "speed_tie"}}, execution_scope_authority=scope, wide_guard_spread_applicability_authority=authority)
    ledger = normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    rows = tuple(iter_rock_slide_multi_recipient_immediate_pair_terminal_rows(ledger=ledger))
    assert sum(row["probability"] for row in rows) == 1
    protected = [row for row in rows if row["order"] == "opponent_first"]
    assert protected and all(all(state["hp"] == 100 and not state["fainted"] for state in row["ordered_recipient_states"]) for row in protected)
    metrics = project_rock_slide_multi_recipient_immediate_pair_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved", metrics.get("reason")
    assert metrics["joint_final_states"]["probability_mass"] == {"numerator": 1, "denominator": 1}

    malformed = deepcopy(pair)
    leaf = malformed["order_graphs"][1]["first_action"]["first_action_ledger"]["terminal_leaves"][0]
    leaf["wide_guard_spread_applicability_authority"] = {"status": "resolved"}
    assert normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=malformed)["status"] == "rejected"
