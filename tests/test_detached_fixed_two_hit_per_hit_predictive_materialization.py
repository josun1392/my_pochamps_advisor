from copy import deepcopy
from fractions import Fraction

from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _owner, _state


def _inputs(*, move_id="double-hit", power=40, accuracy=100, target_hp=100):
    state = _state(); target = state["opponent_side"]["pokemon"][0]
    target["current_hp"] = target_hp; target["max_hp"] = max(100, target_hp); target["fainted"] = False
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    metadata = {"move_id": move_id, "category": "physical", "power": power, "type": "normal" if move_id == "double-hit" else "fighting", "accuracy": accuracy, "priority": 0, "min_hits": 2, "max_hits": 2}
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own, "active_attacker": own}
    action = {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}
    execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    return state, snapshot, d0, action, execution, own, foe


def _sturdy(d0, own, foe, hp=100):
    return {"status": "ready", "schema_version": "detached-switch-in-sturdy-survival-authority-v1", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own, "defender": foe, "attacker": own, "post_entry_hp": hp, "maximum_hp": hp, "provenance": "test"}


def test_double_hit_and_double_kick_materialize_ordered_independent_hit_leaves_without_mutation():
    for move in ("double-hit", "double-kick"):
        state, snapshot, d0, action, execution, own, foe = _inputs(move_id=move); before = deepcopy(snapshot)
        result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
        assert result["status"] == "evaluable", result.get("reason")
        assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert len(result["terminal_leaves"]) == 2 * 16 * 2 * 16
        assert all(len(leaf["ordered_hits"]) == 2 for leaf in result["terminal_leaves"])
        assert all(leaf["ordered_hits"][0]["roll_index"] in range(16) and leaf["ordered_hits"][1]["roll_index"] in range(16) for leaf in result["terminal_leaves"])
        assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_first_hit_ko_stops_second_hit_and_sturdy_first_hit_survival_allows_second_hit_to_ko():
    _state0, snapshot, d0, action, execution, own, foe = _inputs(power=500, target_hp=10)
    stopped = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert stopped["status"] == "evaluable"
    assert all(len(leaf["ordered_hits"]) == 1 and leaf["consequences"]["target_ko"] is True for leaf in stopped["terminal_leaves"])

    _state1, snapshot, d0, action, execution, own, foe = _inputs(power=500)
    saved = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, sturdy_survival_authority=_sturdy(d0, own, foe))
    assert saved["status"] == "evaluable"
    assert all(leaf["ordered_hits"][0]["post_hp"] == 1 and leaf["ordered_hits"][0]["sturdy_applied"] for leaf in saved["terminal_leaves"])
    assert all(len(leaf["ordered_hits"]) == 2 and leaf["consequences"]["target_ko"] is True for leaf in saved["terminal_leaves"])


def test_nonlethal_first_hit_and_miss_do_not_fabricate_or_consume_sturdy():
    _state0, snapshot, d0, action, execution, own, foe = _inputs(power=40)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, sturdy_survival_authority=_sturdy(d0, own, foe))
    assert result["status"] == "evaluable"
    assert all(not leaf["ordered_hits"][0]["sturdy_applied"] for leaf in result["terminal_leaves"])
    assert all(not leaf["ordered_hits"][1]["sturdy_applied"] for leaf in result["terminal_leaves"])

    _state1, snapshot, d0, action, execution, own, foe = _inputs(accuracy=50)
    missed = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, sturdy_survival_authority=_sturdy(d0, own, foe))
    miss = next(leaf for leaf in missed["terminal_leaves"] if leaf["hit_state"] == "miss")
    assert miss["probability"] == {"numerator": 1, "denominator": 2}
    assert miss["ordered_hits"] == () and miss["consequences"]["sturdy"]["state"] == "ready_or_not_applicable"


def test_invalid_or_stale_execution_authority_rejects_without_falling_back_to_aggregate_damage():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs()
    bad = deepcopy(execution); bad["hit_count"] = 3
    assert materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=bad)["status"] == "rejected"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 1; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=stale, action=action, execution_authority=execution)["status"] == "rejected"
