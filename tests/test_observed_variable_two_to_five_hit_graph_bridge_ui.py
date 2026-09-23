from copy import deepcopy
from pathlib import Path

import pytest

from llm.advisor_ui_detached_strategy_bridge import _project_variable_two_to_five_hit_predictions
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _inputs


@pytest.mark.parametrize("move_id",["bullet-seed","rock-blast"])
def test_bridge_projects_real_variable_graph_for_supported_moves(move_id):
    _state,snapshot,d0,action,_execution,_own,_foe=_inputs(move_id=move_id,target_hp=1,power=500)
    action=deepcopy(action);action["selection"]="selectable"
    result=_project_variable_two_to_five_hit_predictions(
        strategy_d0=d0,runtime_snapshot=snapshot,selection={"actions":(action,)},
        live_attacks={"sturdy_survival_authorities":{},"focus_sash_survival_authorities":{}},
    )
    assert action["action_id"] in result, result
    artifact=result[action["action_id"]]
    assert artifact["schema_version"]=="detached-variable-two-to-five-hit-per-hit-predictive-materialization-v1"
    assert artifact["move_id"]==move_id
    assert artifact["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    assert {r["selected_hit_count"] for r in artifact["terminal_leaf_roots"] if r["selected_hit_count"] is not None}=={2,3,4,5}


def test_main_window_variable_multi_hit_ui_collects_observables_only_and_separates_family():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    fixed_start=source.index("def _open_fixed_two_hit_result_confirmation")
    variable_start=source.index("def _open_variable_two_to_five_hit_result_confirmation")
    fixed=source[fixed_start:variable_start]
    variable_end=source.index("def _resolve_pending_confusion_actor",variable_start)
    variable=source[variable_start:variable_end]
    assert 'retained.get("family") != "fixed_two_hit"' in fixed
    assert 'retained.get("family") != "variable_two_to_five"' in variable
    assert "Observed action result" in variable
    assert "Observed landed hit count" in variable
    assert "Target HP after hit" in variable
    assert "Observed terminal cause" in variable
    assert "Selected hit count was exhausted" in variable
    for forbidden in ("graph root id","node id","edge id","roll index","crit branch id","predictive artifact fingerprint"):
        assert forbidden not in variable.lower()


def test_variable_retention_reuses_existing_multi_hit_lifecycle_store_and_retirement():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'strategy_result.get("variable_two_to_five_hit_predictions")' in source
    assert "retain_historical_variable_two_to_five_prediction" in source
    assert source.count("self._historical_multi_hit_predictions = {}") >= 6
