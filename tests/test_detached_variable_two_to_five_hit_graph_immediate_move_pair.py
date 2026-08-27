from copy import deepcopy

import pytest

from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair
from tests.test_detached_opponent_response_profile import _equal_speed_order, _inputs, _metadata
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _sturdy
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _variable_action(d0, move_id="bullet-seed", power=25):
    authority = deepcopy(_metadata(move_id))
    authority["metadata"].update({"min_hits": 2, "max_hits": 5, "power": power, "type": "grass" if move_id == "bullet-seed" else "rock"})
    authority.update({"candidate_id": f"attack:{move_id}", "active_attacker": d0["decision_owner"], "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]})
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


def _population_bomb_action(d0, power=500, accuracy=100):
    authority = deepcopy(_metadata("population-bomb"))
    authority["metadata"].update({"min_hits": 10, "max_hits": 10, "multiaccuracy": True, "power": power, "type": "normal", "accuracy": accuracy})
    authority.update({"candidate_id": "attack:population-bomb", "active_attacker": d0["decision_owner"], "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]})
    return {"action_id": "attack:population-bomb", "action_type": "attack", "identity": "population-bomb", "move_metadata_authority": authority}


def _escalating_action(d0, move_id="triple-axel", accuracy=100):
    authority = deepcopy(_metadata(move_id))
    power, move_type = {"triple-axel": (20, "ice"), "triple-kick": (10, "fighting")}[move_id]
    authority["metadata"].update({"min_hits": 3, "max_hits": 3, "bp_escalation": True, "multiaccuracy": False, "power": power, "type": move_type, "accuracy": accuracy})
    authority.update({"candidate_id": f"attack:{move_id}", "active_attacker": d0["decision_owner"], "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]})
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


def _opponent_variable(action, move_id="rock-blast", power=25):
    value = deepcopy(action); value["action_id"] = f"opponent_attack:{move_id}"; value["move_id"] = move_id
    value["metadata_authority"] = _metadata(move_id); value["metadata_authority"]["metadata"].update({"min_hits": 2, "max_hits": 5, "power": power, "type": "rock" if move_id == "rock-blast" else "grass"})
    return value


@pytest.mark.parametrize("move_id", ["bullet-seed", "rock-blast"])
def test_variable_first_action_graph_attaches_surviving_second_action_without_flattening(move_id):
    state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=100)
    own = _variable_action(d0, move_id); opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    before = deepcopy(snapshot)
    result = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent, "own_first"))
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    graph = result["order_graphs"][0]
    assert graph["first_action_graph"]["terminal_leaf_representation"].startswith("exact_root_to_terminal_path_graph")
    assert any(row["second_action"]["state"] == "outcome_graph" for row in graph["terminal_transitions"])
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_early_ko_cancels_second_and_opponent_first_is_actor_neutral():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(own_hp=1, opponent_hp=1)
    own = _variable_action(d0, "bullet-seed", power=500); opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    cancelled = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent, "own_first"))
    assert cancelled["status"] == "evaluable"
    assert all(row["second_action"]["state"] == "cancelled_due_to_faint" for row in cancelled["order_graphs"][0]["terminal_transitions"])

    opponent_variable = _opponent_variable(opponent, "rock-blast", power=500)
    own_again = _variable_action(d0)
    opponent_first = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_again, opponent_action=opponent_variable, action_order_authority=_order(d0, own_again, opponent_variable, "opponent_first"))
    assert opponent_first["status"] == "evaluable", opponent_first.get("reason")
    assert opponent_first["order_graphs"][0]["provenance"]["root_predictive_authority"]["hypothetical"] is True


def test_sturdy_saved_early_hit_and_later_hit_ko_remain_in_first_action_graph():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=100)
    own = _variable_action(d0, "bullet-seed", power=500)
    opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    result = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
        first_action_sturdy_survival_authority=_sturdy(d0, d0["active_owners"]["self"], d0["active_owners"]["opponent"]),
    )
    assert result["status"] == "evaluable", result.get("reason")
    first = result["order_graphs"][0]["first_action_graph"]
    first_edges = [row for row in first["terminal_leaf_edges"] if row["ordered_hit"]["hit_index"] == 1]
    assert first_edges and all(row["ordered_hit"]["post_hp"] == 1 and row["ordered_hit"]["sturdy_applied"] for row in first_edges)
    assert any(row["ordered_hit"]["hit_index"] == 2 and row["terminal"] for row in first["terminal_leaf_edges"])
    assert all(row["second_action"]["state"] == "cancelled_due_to_faint" for row in result["order_graphs"][0]["terminal_transitions"])


def test_equal_speed_composes_both_variable_first_orders_without_eager_flattening():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(equal_speed=True, own_hp=1, opponent_hp=1)
    own = _variable_action(d0, "bullet-seed", power=500)
    opponent = _opponent_variable(next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle"), "rock-blast", power=500)
    result = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_equal_speed_order(d0, own, opponent))
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {row["action_order"] for row in result["order_graphs"]} == {"own_first", "opponent_first"}
    assert all(row["first_action_graph"]["terminal_leaf_representation"].startswith("exact_root_to_terminal_path_graph") for row in result["order_graphs"])


def test_population_bomb_graph_attaches_miss_or_ko_terminal_sources_without_flattening():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    own = _population_bomb_action(d0, power=500, accuracy=50)
    opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    result = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent, "own_first"))
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    transitions = result["order_graphs"][0]["terminal_transitions"]
    assert any(row["ordered_terminal_hit"] is None and row["second_action"]["state"] == "outcome_graph" for row in transitions)
    assert any(row["ordered_terminal_hit"] is not None and row["second_action"]["state"] == "cancelled_due_to_faint" for row in transitions)


@pytest.mark.parametrize("move_id", ["triple-axel", "triple-kick"])
def test_escalating_three_hit_graphs_attach_miss_or_landed_terminal_sources(move_id):
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=100)
    own = _escalating_action(d0, move_id, accuracy=50)
    opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    result = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent, "own_first"))
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    transitions = result["order_graphs"][0]["terminal_transitions"]
    assert any(row["ordered_terminal_hit"] is None and row["second_action"]["state"] == "outcome_graph" for row in transitions)
    assert any(row["ordered_terminal_hit"] is not None and row["ordered_terminal_hit"]["base_power"] in {20, 40, 60, 10, 30} for row in transitions)
