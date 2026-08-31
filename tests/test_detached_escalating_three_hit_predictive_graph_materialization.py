from copy import deepcopy

import pytest

from llm.advisor_detached_escalating_three_hit_predictive_graph_materialization import (
    materialize_detached_escalating_three_hit_predictive_graph,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import (
    freeze_runtime_d0_escalating_three_hit_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _sturdy
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _owner, _state


def _inputs(*, move_id="triple-axel", accuracy=100, target_hp=100, ability=None, item=None):
    state = _state(); target = state["opponent_side"]["pokemon"][0]
    target.update(current_hp=target_hp, max_hp=target_hp, fainted=False)
    attacker = state["self_side"]["pokemon"][0]; attacker["current_ability"] = ability or attacker.get("current_ability")
    if item: attacker["known_item"] = item; attacker.setdefault("known_item_provenance", {})["status"] = "known"
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    power, move_type = {"triple-axel": (20, "ice"), "triple-kick": (10, "fighting")}[move_id]
    metadata = {"move_id": move_id, "category": "physical", "power": power, "type": move_type, "accuracy": accuracy, "priority": 0, "min_hits": 3, "max_hits": 3, "bp_escalation": True, "multiaccuracy": True}
    move_authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(own), "active_attacker": deepcopy(own)}
    action = {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": move_authority}
    execution = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    return state, snapshot, d0, action, execution, own, foe


@pytest.mark.parametrize(("move_id", "powers"), [("triple-axel", [20, 40, 60]), ("triple-kick", [10, 20, 30])])
def test_escalating_moves_preserve_exact_ordered_powers_and_full_path_mass(move_id, powers):
    state, snapshot, d0, action, execution, _own, _foe = _inputs(move_id=move_id); before = deepcopy(snapshot)
    result = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    landed = [edge["hit_outcome"]["ordered_hit"] for edge in result["terminal_leaf_edges"] if edge["hit_outcome"]["outcome"] == "hit"]
    assert {row["base_power"] for row in landed if row["hit_index"] == 1} == {powers[0]}
    assert {row["base_power"] for row in landed if row["hit_index"] == 2} == {powers[1]}
    assert {row["base_power"] for row in landed if row["hit_index"] == 3} == {powers[2]}
    assert all(row["roll_index"] in range(16) for row in landed)
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_per_hit_miss_terminates_without_erasing_prior_landed_consequences():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=50, target_hp=1000)
    result = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    first_miss = next(edge for edge in result["terminal_leaf_edges"] if edge["from_node_id"].startswith("hit:1/") and edge["hit_outcome"]["outcome"] == "miss")
    assert first_miss["conditional_probability"] == {"numerator": 1, "denominator": 2}
    assert first_miss["terminal_consequences"]["landed_hit_count"] == 0
    later_miss = [edge for edge in result["terminal_leaf_edges"] if edge["from_node_id"].startswith("hit:2/") and edge["hit_outcome"]["outcome"] == "miss"]
    assert later_miss and all(edge["terminal_consequences"]["landed_hit_count"] == 1 for edge in later_miss)


def test_early_ko_and_sturdy_saved_first_hit_then_later_hit_ko_stop_the_graph():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(target_hp=1)
    ko = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert ko["status"] == "evaluable" and all(edge["hit_outcome"].get("ordered_hit", {}).get("hit_index") == 1 for edge in ko["terminal_leaf_edges"])

    _state1, snapshot, d0, action, execution, own, foe = _inputs(target_hp=10)
    saved = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, sturdy_survival_authority=_sturdy(d0, own, foe, hp=10))
    first = [edge for edge in saved["terminal_leaf_edges"] if edge["from_node_id"].startswith("hit:1/")]
    assert first and any(edge["hit_outcome"]["ordered_hit"]["post_hp"] == 1 and edge["hit_outcome"]["ordered_hit"]["sturdy_applied"] for edge in first)
    assert any(edge.get("terminal_reason") == "target_fainted" and edge["hit_outcome"].get("ordered_hit", {}).get("hit_index") == 2 for edge in saved["terminal_leaf_edges"])


def test_stale_or_tampered_authority_rejects():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs()
    bad = deepcopy(execution); bad["per_hit_power_execution"]["hits"][2]["base_power"] = 59
    assert materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=bad)["status"] == "rejected"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 1; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=stale, action=action, execution_authority=execution)["status"] == "rejected"


def test_loaded_dice_removes_later_accuracy_branches_without_count_expansion():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=50, target_hp=1000, item="loaded-dice")
    result = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    misses = [edge for edge in result["terminal_leaf_edges"] if edge["hit_outcome"]["outcome"] == "miss"]
    assert len(misses) == 1 and misses[0]["terminal_consequences"]["landed_hit_count"] == 0
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
