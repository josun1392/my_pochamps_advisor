from copy import deepcopy

from llm.advisor_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import (
    materialize_detached_population_bomb_per_hit_accuracy_predictive_graph,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import (
    freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _focus_sash
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _sturdy
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _owner, _state


def _inputs(*, accuracy=100, power=20, target_hp=100, ability=None, item=None):
    state = _state()
    target = state["opponent_side"]["pokemon"][0]
    target.update(current_hp=target_hp, max_hp=max(target_hp, 100), fainted=False)
    attacker = state["self_side"]["pokemon"][0]
    if ability is not None:
        attacker["current_ability"] = ability
    if item is not None:
        attacker["known_item"] = item
        attacker.setdefault("known_item_provenance", {})["status"] = "known"
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    metadata = {"move_id": "population-bomb", "category": "physical", "power": power, "type": "normal", "accuracy": accuracy, "priority": 0, "min_hits": 10, "max_hits": 10, "multiaccuracy": True}
    move_authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": "attack:population-bomb", "move_id": "population-bomb", "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(own), "active_attacker": deepcopy(own)}
    action = {"action_id": "attack:population-bomb", "action_type": "attack", "identity": "population-bomb", "move_metadata_authority": move_authority}
    execution = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    return state, snapshot, d0, action, execution, own, foe


def test_first_miss_and_later_miss_are_explicit_terminal_attempt_paths_without_mutation():
    state, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=50, power=1, target_hp=1000)
    before = deepcopy(snapshot)
    result = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    first_miss = next(edge for edge in result["terminal_leaf_edges"] if edge["from_node_id"].startswith("attempt:1/") and edge["attempt_outcome"]["outcome"] == "miss")
    assert first_miss["conditional_probability"] == {"numerator": 1, "denominator": 2}
    assert first_miss["terminal_consequences"]["landed_hit_count"] == 0
    assert any(edge["from_node_id"].startswith("attempt:2/") and edge["attempt_outcome"]["outcome"] == "miss" and edge["terminal_consequences"]["landed_hit_count"] == 1 for edge in result["terminal_leaf_edges"])
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 1000


def test_ten_landed_attempts_keep_ordered_crit_roll_identity_and_stop_at_limit():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=100, power=1, target_hp=1000)
    result = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable", result.get("reason")
    tenth = [edge for edge in result["terminal_leaf_edges"] if edge.get("terminal_reason") == "maximum_ten_attempts_reached"]
    assert tenth and all(edge["attempt_outcome"]["ordered_hit"]["attempt_index"] == 10 and edge["attempt_outcome"]["ordered_hit"]["roll_index"] in range(16) for edge in tenth)
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_sharpness_applies_to_every_population_bomb_hit_without_changing_graph_mass():
    def graph(ability):
        _state0, snapshot, d0, action, execution, _own, _foe = _inputs(
            accuracy=100, power=20, target_hp=1000, ability=ability,
        )
        return materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(
            strategy_d0=d0, runtime_snapshot=snapshot, action=action,
            execution_authority=execution,
        )

    baseline, sharpness = graph("pressure"), graph("sharpness")
    assert baseline["status"] == sharpness["status"] == "evaluable"
    assert baseline["terminal_probability_mass"] == sharpness["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}

    def rolls(result):
        return {
            (hit["attempt_index"], hit["critical_state"], hit["roll_index"]): hit["raw_damage"]
            for edge in result["terminal_leaf_edges"]
            if edge["attempt_outcome"]["outcome"] == "hit"
            for hit in (edge["attempt_outcome"]["ordered_hit"],)
        }

    baseline_rolls, sharpness_rolls = rolls(baseline), rolls(sharpness)
    assert baseline_rolls.keys() == sharpness_rolls.keys()
    assert {key[0] for key in sharpness_rolls} == set(range(1, 11))
    assert all(sharpness_rolls[key] > baseline_rolls[key] for key in baseline_rolls)


def test_early_ko_and_sturdy_saved_first_hit_then_later_ko_terminate_the_attempt_graph():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=100, power=500, target_hp=10)
    ko = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert ko["status"] == "evaluable" and all(edge["attempt_outcome"].get("ordered_hit", {}).get("attempt_index") == 1 for edge in ko["terminal_leaf_edges"])

    _state1, snapshot, d0, action, execution, own, foe = _inputs(accuracy=100, power=500, target_hp=100)
    saved = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, sturdy_survival_authority=_sturdy(d0, own, foe))
    first = [edge for edge in saved["terminal_leaf_edges"] if edge["from_node_id"].startswith("attempt:1/")]
    assert first and all(edge["attempt_outcome"]["ordered_hit"]["post_hp"] == 1 and edge["attempt_outcome"]["ordered_hit"]["sturdy_applied"] for edge in first)
    assert any(edge.get("terminal_reason") == "target_fainted" and edge["attempt_outcome"]["ordered_hit"]["attempt_index"] == 2 for edge in saved["terminal_leaf_edges"])


def test_focus_sash_consumes_on_first_population_bomb_hit_and_next_hit_can_ko():
    _state0, snapshot, d0, action, execution, own, foe = _inputs(accuracy=100, power=500, target_hp=100)
    saved = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        execution_authority=execution,
        focus_sash_survival_authority=_focus_sash(d0, own, foe, action),
    )
    assert saved["status"] == "evaluable", saved.get("reason")
    assert saved["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    first = [edge for edge in saved["terminal_leaf_edges"] if edge["from_node_id"].startswith("attempt:1/")]
    assert first and all(edge["attempt_outcome"]["ordered_hit"]["post_hp"] == 1 and edge["attempt_outcome"]["ordered_hit"]["focus_sash_applied"] for edge in first)
    assert any(edge.get("terminal_reason") == "target_fainted" and edge["attempt_outcome"]["ordered_hit"]["attempt_index"] == 2 and edge["terminal_consequences"]["focus_sash"]["state"] == "consumed" for edge in saved["terminal_leaf_edges"])


def test_stale_or_foreign_authority_rejects():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs()
    bad = deepcopy(execution); bad["maximum_attempt_execution"]["maximum_attempts"] = 9
    assert materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=bad)["status"] == "rejected"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 1; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=stale, action=action, execution_authority=execution)["status"] == "rejected"


def test_skill_link_and_loaded_dice_use_one_initial_accuracy_then_guaranteed_planned_hits():
    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=50, power=1, target_hp=1000, ability="skill-link")
    result = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable"
    assert len(result["terminal_leaf_roots"]) == 1
    misses = [edge for edge in result["terminal_leaf_edges"] if edge["attempt_outcome"]["outcome"] == "miss"]
    assert len(misses) == 1 and misses[0]["terminal_consequences"]["landed_hit_count"] == 0
    assert all(edge["attempt_outcome"]["outcome"] != "miss" or edge["from_node_id"].startswith("attempt:1/") for edge in result["terminal_leaf_edges"])

    _state0, snapshot, d0, action, execution, _own, _foe = _inputs(accuracy=100, power=1, target_hp=1000, ability="skill-link", item="loaded-dice")
    result = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable" and result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    roots = result["terminal_leaf_roots"]
    assert [root["selected_hit_count"] for root in roots] == list(range(4, 11))
    assert all(root["probability"] == {"numerator": 1, "denominator": 7} for root in roots)
    assert not [edge for edge in result["terminal_leaf_edges"] if edge["attempt_outcome"]["outcome"] == "miss"]
