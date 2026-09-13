from copy import deepcopy
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from tests.test_direct_heal_move_family import _inputs
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _inputs as _graph_inputs
from tests.test_atomic_item_swap_status_execution_authority import _inputs as _swap_inputs
from llm.advisor_runtime_d0_atomic_item_swap_status_execution_authority import freeze_runtime_d0_atomic_item_swap_status_execution_authority


def test_direct_heal_selected_action_result_is_detached_and_has_no_gate_mass():
    snapshot, d0, actor, action = _inputs(101, 301)
    before = deepcopy(snapshot)
    authority = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor)
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor,
        target=d0["active_owners"]["opponent"], move_metadata=action["move_metadata_authority"]["metadata"],
        family_authorities={"direct_heal_execution_authority": authority},
    )
    assert result["status"] == "resolved"
    assert result["execution_family"] == "direct_heal"
    assert result["probability_owner"] == "selected_action_only"
    assert result["paths"][0]["probability"] == {"numerator": 1, "denominator": 1}
    assert result["paths"][0]["post_action_runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"] == 252
    assert snapshot == before


def test_selected_action_result_fails_closed_for_recognized_missing_family_authority():
    snapshot, d0, actor, action = _inputs(101, 301)
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor,
        target=d0["active_owners"]["opponent"], move_metadata=action["move_metadata_authority"]["metadata"],
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "direct_heal_execution_authority_missing"


def test_native_graph_keeps_native_terminal_sources_and_projects_each_terminal_state():
    _state, snapshot, d0, action, _execution, actor, target = _graph_inputs(move_id="bullet-seed")
    before = deepcopy(snapshot)
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata=action["move_metadata_authority"]["metadata"],
    )
    assert result["status"] == "resolved", result
    assert result["execution_family"] == "native_graph_multi_hit"
    assert result["terminal_representation"] == "native_graph_with_detached_terminal_state_projection"
    assert result["native_graph"]["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert result["paths"] and all("native_terminal_source" in path and path["post_action_state"]["status"] == "resolved" for path in result["paths"])
    assert snapshot == before


def test_atomic_swap_uses_existing_materializer_and_carries_both_path_local_items():
    _state, snapshot, d0, action, actor, target, applicability = _swap_inputs()
    authority = freeze_runtime_d0_atomic_item_swap_status_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        execution_applicability_authority=applicability,
    )
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata=action["move_metadata_authority"]["metadata"],
        family_authorities={"atomic_item_swap_execution_authority": authority},
    )
    assert result["status"] == "resolved", result
    state = result["paths"][0]["post_action_state"]
    assert state["active"]["self"]["hypothetical_item"]["value"] == "black-belt"
    assert state["active"]["opponent"]["hypothetical_item"]["value"] == "choice-scarf"
