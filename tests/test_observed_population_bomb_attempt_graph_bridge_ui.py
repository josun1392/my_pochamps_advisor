from copy import deepcopy
from pathlib import Path

from llm.advisor_ui_detached_strategy_bridge import _project_population_bomb_predictions
from llm.advisor_population_bomb_attempt_graph_reconciliation import retain_historical_population_bomb_prediction
from tests.test_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import _inputs


def test_bridge_projects_real_population_bomb_attempt_graph():
    _state,snapshot,d0,action,_execution,_own,_foe=_inputs(accuracy=100,power=500,target_hp=1)
    action=deepcopy(action);action["selection"]="selectable"
    result=_project_population_bomb_predictions(
        strategy_d0=d0,runtime_snapshot=snapshot,selection={"actions":(action,)},
        live_attacks={"sturdy_survival_authorities":{},"focus_sash_survival_authorities":{}},
    )
    assert action["action_id"] in result,result
    artifact=result[action["action_id"]]
    assert artifact["schema_version"]=="detached-population-bomb-per-hit-accuracy-predictive-graph-materialization-v1"
    assert artifact["move_id"]=="population-bomb"
    assert artifact["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    retained=retain_historical_population_bomb_prediction(
        predictive_artifact=artifact,turn_number=1,decision_point="decision:1:self",source_action_id=action["action_id"])
    assert retained["status"]=="resolved",retained


def test_bridge_real_modifier_plans_validate_without_recalculation():
    for ability,item,kind in (
        ("skill-link",None,"single_accuracy_then_fixed_guaranteed_hits"),
        ("skill-link","loaded-dice","single_accuracy_then_uniform_guaranteed_hits"),
    ):
        _state,snapshot,d0,action,_execution,_own,_foe=_inputs(accuracy=100,power=500,target_hp=1,ability=ability,item=item)
        action=deepcopy(action);action["selection"]="selectable"
        result=_project_population_bomb_predictions(
            strategy_d0=d0,runtime_snapshot=snapshot,selection={"actions":(action,)},
            live_attacks={"sturdy_survival_authorities":{},"focus_sash_survival_authorities":{}},
        )
        artifact=result[action["action_id"]]
        retained=retain_historical_population_bomb_prediction(
            predictive_artifact=artifact,turn_number=1,decision_point="decision:1:self",source_action_id=action["action_id"])
        assert retained["status"]=="resolved",retained
        plans={r["modifier_execution_plan"] for r in artifact["terminal_leaf_roots"]}
        assert plans=={kind}


def test_population_bomb_ui_collects_attempt_facts_only_and_reuses_lifecycle_store():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    start=source.index("def _open_population_bomb_result_confirmation")
    end=source.index("def _resolve_pending_confusion_actor",start)
    method=source[start:end]
    assert 'retained.get("family") != "population_bomb_attempt_graph"' in method
    assert "Observed attempt count" in method
    assert "outcome" in method
    assert "Target HP after landed hit" in method
    assert "Observed terminal cause" in method
    for forbidden in ("graph root id","node id","edge id","planned count","roll index","predictive fingerprint"):
        assert forbidden not in method.lower()
    assert 'strategy_result.get("population_bomb_predictions")' in source
    assert "retain_historical_population_bomb_prediction" in source
    assert source.count("self._historical_multi_hit_predictions = {}") >= 6


def test_fixed_and_variable_ui_family_filters_remain_explicit():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    fixed_start=source.index("def _open_fixed_two_hit_result_confirmation")
    variable_start=source.index("def _open_variable_two_to_five_hit_result_confirmation")
    pop_start=source.index("def _open_population_bomb_result_confirmation")
    fixed=source[fixed_start:variable_start];variable=source[variable_start:pop_start]
    assert 'retained.get("family") != "fixed_two_hit"' in fixed
    assert 'retained.get("family") != "variable_two_to_five"' in variable
