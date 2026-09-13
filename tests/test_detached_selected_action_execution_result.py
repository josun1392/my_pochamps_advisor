from copy import deepcopy
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from tests.test_direct_heal_move_family import _inputs
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _inputs as _graph_inputs
from tests.test_atomic_item_swap_status_execution_authority import _inputs as _swap_inputs
from tests.test_detached_immediate_protection_response_pair import _inputs as _protection_inputs, _own_action, _protect_action, _success, _spiky_damage_authority, _silk_interaction, _kings_interaction, _obstruct_interaction
from llm.advisor_runtime_d0_atomic_item_swap_status_execution_authority import freeze_runtime_d0_atomic_item_swap_status_execution_authority
from llm.advisor_champions_gated_selected_action_execution import execute_gated_selected_action, consume_deferred_protection_setup


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


def test_gated_handoff_uses_selected_action_probability_only_and_detached_heal_state():
    snapshot, d0, actor, action = _inputs(101, 301)
    target = d0["active_owners"]["opponent"]
    root = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor)
    before = deepcopy(snapshot)
    result = execute_gated_selected_action(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        metadata_authority=action["move_metadata_authority"],
        extension_authorities={"direct_heal_execution_authorities": {action["action_id"]: root}},
    )
    assert result["status"] == "resolved", result
    path = result["paths"][0]
    assert path["probability"] == {"numerator": 1, "denominator": 1}
    assert path["post_action_runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"] == 252
    assert snapshot == before


def test_gated_protection_setup_keeps_pending_attack_unexecuted():
    _state, snapshot, d0, _unused, _responses, _orders = _protection_inputs()
    pending, protect = _own_action(d0, "tackle"), _protect_action(d0, "protect")
    result = execute_gated_selected_action(
        strategy_d0=d0, runtime_snapshot=snapshot, action=protect,
        actor=d0["active_owners"]["opponent"], target=d0["active_owners"]["self"],
        metadata_authority=protect["metadata_authority"], pending_action=pending,
        pending_metadata_authority=pending["move_metadata_authority"],
        extension_authorities={"opponent_protection_success_authority": _success(d0["active_owners"]["opponent"])},
    )
    assert result["status"] == "resolved", result
    path = result["paths"][0]["selected_action_path"]
    assert path["pending_action_executed"] is False
    assert path["protection_setup"]["pending_action_context"]["action_id"] == pending["action_id"]


def test_deferred_spiky_reactive_damage_is_not_applied_until_pending_action_attempts():
    _state, snapshot, d0, _unused, _responses, _orders = _protection_inputs()
    pending, shield = _own_action(d0, "tackle"), _protect_action(d0, "spiky-shield")
    damage, contact = _spiky_damage_authority(d0, snapshot, pending)
    setup = execute_gated_selected_action(
        strategy_d0=d0, runtime_snapshot=snapshot, action=shield,
        actor=d0["active_owners"]["opponent"], target=d0["active_owners"]["self"],
        metadata_authority=shield["metadata_authority"], pending_action=pending,
        pending_metadata_authority=pending["move_metadata_authority"],
        extension_authorities={"opponent_protection_success_authority": _success(d0["active_owners"]["opponent"]), "incoming_contact_authority": contact, "spiky_shield_reactive_damage_authority": damage},
    )
    assert setup["status"] == "resolved", setup
    setup_path = setup["paths"][0]["selected_action_path"]
    assert setup_path["post_action_runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"] == 100
    consumed = consume_deferred_protection_setup(
        setup_path=setup_path, pending_action=pending, pending_metadata_authority=pending["move_metadata_authority"],
        pending_branch_snapshot=snapshot, selected_path={"post_action_runtime_snapshot": snapshot, "final_hp": {"self": 100, "opponent": 100}},
    )
    assert consumed["status"] == "resolved"
    assert consumed["selected_path"]["final_hp"]["self"] == 88


def test_deferred_stage_shields_apply_only_after_pending_contact_attempt():
    _state, snapshot, d0, _unused, _responses, _orders = _protection_inputs()
    pending = _own_action(d0, "tackle")
    for move, field, stat, resolution in (("silk-trap", "silk_trap_reactive_interaction_authority", "speed", _silk_interaction(d0)), ("kings-shield", "kings_shield_reactive_interaction_authority", "attack", _kings_interaction(d0)), ("obstruct", "obstruct_reactive_interaction_authority", "defense", _obstruct_interaction(d0))):
        shield = _protect_action(d0, move)
        setup = execute_gated_selected_action(strategy_d0=d0, runtime_snapshot=snapshot, action=shield, actor=d0["active_owners"]["opponent"], target=d0["active_owners"]["self"], metadata_authority=shield["metadata_authority"], pending_action=pending, pending_metadata_authority=pending["move_metadata_authority"], extension_authorities={"opponent_protection_success_authority": _success(d0["active_owners"]["opponent"]), field: resolution})
        assert setup["status"] == "resolved", setup
        path = setup["paths"][0]["selected_action_path"]
        assert path["post_action_runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["stat_stages"][stat] == 0
        consumed = consume_deferred_protection_setup(setup_path=path, pending_action=pending, pending_metadata_authority=pending["move_metadata_authority"], pending_branch_snapshot=snapshot, selected_path={"post_action_runtime_snapshot": snapshot, "final_hp": {"self": 100, "opponent": 100}})
        assert consumed["status"] == "resolved", consumed
        assert consumed["selected_path"]["post_action_runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["stat_stages"][stat] == resolution["resulting_delta"]
