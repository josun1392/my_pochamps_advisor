from copy import deepcopy
from pathlib import Path

from llm.advisor_ui_detached_strategy_bridge import _project_fixed_two_hit_predictions
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _inputs


def _project(move_id):
    _state,snapshot,d0,action,_execution,_own,_foe=_inputs(move_id=move_id)
    action=deepcopy(action);action["selection"]="selectable"
    result=_project_fixed_two_hit_predictions(
        strategy_d0=d0,runtime_snapshot=snapshot,
        selection={"actions":(action,)},live_attacks={},
    )
    return action,result


def test_bridge_freezes_existing_double_hit_and_double_kick_predictive_artifacts():
    for move_id in ("double-hit","double-kick"):
        action,result=_project(move_id)
        assert action["action_id"] in result, {"action": action, "result": result}
        artifact=result[action["action_id"]]
        assert artifact["schema_version"]=="detached-fixed-two-hit-per-hit-predictive-materialization-v1"
        assert artifact["move_id"]==move_id
        assert artifact["terminal_probability_mass"]=={"numerator":1,"denominator":1}


def test_ui_fixed_two_hit_confirmation_collects_only_observable_facts():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    start=source.index("def _open_fixed_two_hit_result_confirmation")
    end=source.index("def _resolve_pending_confusion_actor",start)
    method=source[start:end]
    assert "Observed action result" in method
    assert "Observed landed hit count" in method
    assert "Target HP after hit" in method
    assert "Observed terminal cause" in method
    for forbidden in ("graph fingerprint","terminal leaf","roll index","crit branch","source graph node"):
        assert forbidden not in method.lower()


def test_multi_hit_retention_retires_with_turn_session_switch_and_fresh_strategy():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    assert source.count("self._historical_multi_hit_predictions = {}") >= 6
    assert 'source_action_id=source_links[0]["source_action_id"] if source_links else action_id' in source
