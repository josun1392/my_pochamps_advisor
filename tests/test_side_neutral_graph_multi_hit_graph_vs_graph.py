from copy import deepcopy

from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import (
    materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from tests.test_detached_variable_two_to_five_hit_graph_immediate_move_pair import (
    _escalating_action,
)
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order
from tests.test_side_neutral_graph_multi_hit_pair_composition import (
    _inputs,
    _opponent_variable,
    _ordinary_opponent,
)


def test_graph_first_then_surviving_graph_second_preserves_nested_native_graph_exactly():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(
        own_hp=100, opponent_hp=1,
    )
    own = _escalating_action(d0, "triple-kick", accuracy=1)
    opponent = _opponent_variable(_ordinary_opponent(response_set), "rock-blast", power=1)
    before_snapshot = deepcopy(snapshot)
    before_d0 = deepcopy(d0)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    order = pair["order_graphs"][0]
    first = order["first_action_graph"]
    assert first["move_id"] == "triple-kick"
    assert first["terminal_leaf_representation"] == (
        "exact_root_to_terminal_escalating_three_hit_path_graph_no_final_state_aggregation"
    )
    executed = [
        outcome
        for transition in order["terminal_transitions"]
        for outcome in transition["second_action"].get("outcomes", ())
        if outcome["state"] == "executed"
    ]
    nested = [
        outcome["second_action_graph"]
        for outcome in executed
        if isinstance(outcome.get("second_action_graph"), dict)
    ]
    assert nested
    assert all(graph["move_id"] == "rock-blast" for graph in nested)
    assert all(
        graph["terminal_leaf_representation"]
        == "exact_root_to_terminal_path_graph_no_final_state_aggregation"
        for graph in nested
    )
    assert all("terminal_leaves" not in graph for graph in nested)
    assert any(
        transition["second_action"]["state"] == "cancelled_due_to_faint"
        for transition in order["terminal_transitions"]
    )
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert snapshot == before_snapshot
    assert d0 == before_d0
    for graph in nested:
        assert graph["attacker"] == d0["active_owners"]["opponent"]
        assert graph["target"] == d0["active_owners"]["self"]
        assert isinstance(graph["own_current_hp"], int)
        assert graph["attacker_condition"] == "none"
        assert graph["execution_authority"]["status"] == "resolved"
