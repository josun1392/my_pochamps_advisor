from copy import deepcopy

import pytest

from llm.advisor_detached_variable_two_to_five_hit_per_hit_predictive_materialization import materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves
from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _owner, _state


def _inputs(*, move_id="bullet-seed", power=25, accuracy=100, target_hp=100, attacker_ability=None, attacker_item=None):
    state = _state(); target = state["opponent_side"]["pokemon"][0]
    target["current_hp"] = target_hp; target["max_hp"] = max(100, target_hp); target["fainted"] = False
    attacker = state["self_side"]["pokemon"][0]
    if attacker_ability is not None: attacker["current_ability"] = attacker_ability
    if attacker_item is not None:
        attacker["known_item"] = attacker_item
        attacker["known_item_provenance"]["status"] = "known"
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    metadata = {"move_id": move_id, "category": "physical", "power": power, "type": "grass" if move_id == "bullet-seed" else "rock", "accuracy": accuracy, "priority": 0, "min_hits": 2, "max_hits": 5}
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own, "active_attacker": own}
    action = {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}
    execution = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    return state, snapshot, d0, action, execution, own, foe


def _sturdy(d0, own, foe, hp=100):
    return {"status": "ready", "schema_version": "detached-switch-in-sturdy-survival-authority-v1", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own, "defender": foe, "attacker": own, "post_entry_hp": hp, "maximum_hp": hp, "provenance": "test"}


@pytest.mark.parametrize("move_id", ["bullet-seed", "rock-blast"])
def test_variable_moves_materialize_exact_count_roots_and_ordered_per_hit_path_graph_without_mutation(move_id):
    state, snapshot, d0, action, execution, _own, _foe = _inputs(move_id=move_id); before = deepcopy(snapshot)
    result = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    roots = {row["selected_hit_count"]: row["probability"] for row in result["terminal_leaf_roots"] if row["selected_hit_count"] is not None}
    assert roots == {2: {"numerator": 7, "denominator": 20}, 3: {"numerator": 7, "denominator": 20}, 4: {"numerator": 3, "denominator": 20}, 5: {"numerator": 3, "denominator": 20}}
    assert {node["selected_hit_count"] for node in result["terminal_leaf_nodes"]} == {2, 3, 4, 5}
    assert all(1 <= edge["ordered_hit"]["hit_index"] <= edge["ordered_hit"]["selected_hit_count"] and edge["ordered_hit"]["roll_index"] in range(16) for edge in result["terminal_leaf_edges"])
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_early_ko_stops_scheduled_hits_and_sturdy_saved_first_hit_can_reach_later_hit_ko():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(power=500, target_hp=10)
    stopped = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert stopped["status"] == "evaluable"
    assert all(edge["ordered_hit"]["hit_index"] == 1 for edge in stopped["terminal_leaf_edges"])

    _state1, snapshot, d0, action, execution, own, foe = _inputs(power=500)
    saved = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, sturdy_survival_authority=_sturdy(d0, own, foe))
    assert saved["status"] == "evaluable"
    first = [edge for edge in saved["terminal_leaf_edges"] if edge["ordered_hit"]["hit_index"] == 1]
    assert first and all(edge["ordered_hit"]["post_hp"] == 1 and edge["ordered_hit"]["sturdy_applied"] for edge in first)
    assert any(edge["ordered_hit"]["hit_index"] == 2 and edge["terminal"] for edge in saved["terminal_leaf_edges"])


def test_miss_and_stale_or_wrong_authority_fail_closed():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=50)
    result = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    miss = next(row for row in result["terminal_leaf_roots"] if row["root_id"] == "miss")
    assert miss["probability"] == {"numerator": 1, "denominator": 2} and miss["consequences"]["sturdy"]["state"] == "ready_or_not_applicable"
    bad = deepcopy(execution); bad["hit_count_execution"]["root_mass"] = {"numerator": 1, "denominator": 2}
    assert materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=bad)["status"] == "rejected"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 1; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=stale, action=action, execution_authority=execution)["status"] == "rejected"


@pytest.mark.parametrize("kwargs, expected_counts", [
    ({"attacker_ability": "skill-link"}, {5}),
    ({"attacker_item": "loaded-dice"}, {4, 5}),
])
def test_exact_modifier_authority_flows_unchanged_into_existing_graph_materializer(kwargs, expected_counts):
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(**kwargs)
    result = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert execution["hit_count_modifier_authority"]["status"] == "resolved"
    assert result["status"] == "evaluable", result.get("reason")
    assert {row["selected_hit_count"] for row in result["terminal_leaf_roots"] if row["selected_hit_count"] is not None} == expected_counts
