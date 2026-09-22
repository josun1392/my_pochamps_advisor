from pathlib import Path

def test_strategy_bridge_freezes_existing_fixed_two_hit_owner_pre_observation():
    source=Path("llm/advisor_ui_detached_strategy_bridge.py").read_text(encoding="utf-8")
    assert "fixed_two_hit_predictions = _project_fixed_two_hit_predictions" in source
    assert "freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority" in source
    assert "materialize_detached_fixed_two_hit_per_hit_predictive_leaves" in source
    assert 'action.get("identity") not in {"double-hit", "double-kick"}' in source
    assert '"fixed_two_hit_predictions": deepcopy(fixed_two_hit_predictions)' in source

def test_ui_exposes_only_observable_fixed_two_hit_facts_and_retires_stale_history():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    start=source.index("def _open_fixed_two_hit_result_confirmation")
    end=source.index("def _resolve_pending_confusion_actor",start)
    method=source[start:end]
    assert "Observed action result" in method
    assert "Observed landed hit count" in method
    assert "Target HP after hit" in method
    assert "Observed terminal cause" in method
    assert "roll_index" not in method
    assert "branch_fingerprint" not in method
    assert "source graph node" not in method.lower()
    assert "QInputDialog.getText" not in method
    assert 'row.get("payload", {}).get("source_action_id") == retained.get("source_action_id")' in method
    assert source.count("self._historical_multi_hit_predictions = {}") >= 7

def test_parent_and_children_are_evidence_only_not_reducer_effects():
    lifecycle=Path("llm/advisor_lifecycle_confirmation.py").read_text(encoding="utf-8")
    replay=Path("llm/advisor_replay_policy.py").read_text(encoding="utf-8")
    assert '"multi_hit_action_result_observed", "multi_hit_ordered_hit_observed"' in lifecycle
    assert "multi_hit_action_result_observed" not in replay.split("_EFFECTS",1)[1].split("}",1)[0]
    assert "multi_hit_ordered_hit_observed" not in replay.split("_EFFECTS",1)[1].split("}",1)[0]

def test_later_graph_families_remain_unsupported_in_v1():
    source=Path("llm/advisor_multi_hit_graph_reconciliation.py").read_text(encoding="utf-8")
    assert 'FAMILY="fixed_two_hit"' in source
    assert '"unsupported_multi_hit_family"' in source
    assert "variable_two_to_five" not in source
    assert "population_bomb" not in source
