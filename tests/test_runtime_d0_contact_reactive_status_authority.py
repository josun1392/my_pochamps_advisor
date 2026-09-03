from __future__ import annotations

from copy import deepcopy
from fractions import Fraction

from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_contact_reactive_status_authority import (
    contact_reactive_status_branches,
    freeze_runtime_d0_contact_reactive_status_authority,
    materialize_detached_contact_reactive_status,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_escalating_three_hit_predictive_graph_materialization import _inputs as _escalating_inputs
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _inputs as _fixed_inputs
from tests.test_detached_opponent_response_profile import _inputs as _pair_inputs
from tests.test_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import _inputs as _population_inputs
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _inputs as _variable_inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _refresh(state):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return snapshot, d0


def _owner(state, side):
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _set_active(state, side, *, ability=None, condition=None, types=None, item_marker="unchanged", hp=None):
    row = state[f"{side}_side"]["pokemon"][0]
    if ability is not None:
        row["current_ability"] = ability
    if condition is not None:
        row["condition"] = condition
        row["condition_provenance"]["condition"] = condition
    if types is not None:
        row["current_type"] = list(types)
    if item_marker != "unchanged":
        row["known_item"] = item_marker
        row["known_item_provenance"]["status"] = "known" if isinstance(item_marker, str) else "known_absent"
    if hp is not None:
        row["current_hp"] = hp
        row["fainted"] = hp == 0


def _contact(d0, snapshot, action, *, force_contact=False):
    result = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    if force_contact:
        result = deepcopy(result)
        result["status"] = "resolved"
        result["contact_state"] = "contact"
        result.pop("reason", None)
    return result


def _source_hit(action, *, damage=1, routing="target", index=1):
    return {"source_action_id": action["action_id"], "source_move_id": action["identity"], "hit_index": index, "actual_damage": damage, "target_routing": routing}


def _rebind_action(action, d0):
    action = deepcopy(action)
    authority = action["move_metadata_authority"]
    authority["session_id"] = d0["session_id"]
    authority["source_runtime_fingerprint"] = d0["source_runtime_fingerprint"]
    authority["source_branch_fingerprint"] = d0["strategy_preview_fingerprint"]
    authority["decision_owner"] = d0["decision_owner"]
    authority["active_attacker"] = d0["decision_owner"]
    return action


def test_static_flame_body_and_poison_point_resolve_exact_activation_branches():
    cases = (
        ("static", "paralysis"),
        ("flame-body", "burn"),
        ("poison-point", "poison"),
    )
    for ability, condition in cases:
        state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
        _set_active(state, "opponent", ability=ability)
        snapshot, d0 = _refresh(state)
        action = _rebind_action(action, d0)
        authority = freeze_runtime_d0_contact_reactive_status_authority(
            strategy_d0=d0, runtime_snapshot=snapshot,
            attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"],
            source_action=action, contact_authority=_contact(d0, snapshot, action),
            source_hit=_source_hit(action),
        )
        assert authority["status"] == "resolved", authority
        assert authority["outcome"] == "applies"
        assert authority["attempted_condition"] == condition
        assert authority["activation_probability"] == {"numerator": 3, "denominator": 10}
        assert authority["no_activation_probability"] == {"numerator": 7, "denominator": 10}
        branches = contact_reactive_status_branches(authority=authority)
        assert [row["factor"] for row in branches] == [Fraction(3, 10), Fraction(7, 10)]
        overlay = materialize_detached_contact_reactive_status(authority=authority, branch="activation")
        assert overlay["transition_applied"] is True
        assert overlay["hypothetical_condition_authority"]["condition"] == condition


def test_effect_spore_resolves_its_four_canonical_exact_outcomes():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
    _set_active(state, "opponent", ability="effect-spore")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    authority = freeze_runtime_d0_contact_reactive_status_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"],
        defender=d0["active_owners"]["opponent"], source_action=action,
        contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action),
    )
    assert authority["status"] == "resolved", authority
    assert authority["outcome"] == "applies" and authority["reactive_ability"] == "effect-spore"
    branches = contact_reactive_status_branches(authority=authority)
    assert [(row["branch"], row["factor"]) for row in branches] == [
        ("sleep", Fraction(11, 100)), ("paralysis", Fraction(1, 10)),
        ("poison", Fraction(9, 100)), ("none", Fraction(7, 10)),
    ]
    assert sum(row["factor"] for row in branches) == 1
    sleep = materialize_detached_contact_reactive_status(authority=authority, branch="sleep")
    assert sleep["transition_applied"] is True and sleep["cancels_remaining_hits"] is True
    assert sleep["hypothetical_condition_authority"]["condition"] == "sleep"
    for branch in ("paralysis", "poison"):
        overlay = materialize_detached_contact_reactive_status(authority=authority, branch=branch)
        assert overlay["transition_applied"] is True and overlay["cancels_remaining_hits"] is False
    assert materialize_detached_contact_reactive_status(authority=authority, branch="none")["transition_applied"] is False


def test_effect_spore_immunities_and_prevented_outcomes_keep_exact_mass():
    for types, ability, item in ((["grass"], "pressure", None), (["normal"], "overcoat", None), (["normal"], "pressure", "safety-goggles")):
        state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
        _set_active(state, "opponent", ability="effect-spore")
        _set_active(state, "self", types=types, ability=ability, item_marker=item)
        snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
        authority = freeze_runtime_d0_contact_reactive_status_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"],
            source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action),
        )
        assert authority["outcome"] == "not_applicable", authority
        assert contact_reactive_status_branches(authority=authority)[0]["overlay"]["transition_applied"] is False

    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
    _set_active(state, "opponent", ability="effect-spore")
    _set_active(state, "self", types=["steel"], condition="burn")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    authority = freeze_runtime_d0_contact_reactive_status_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"],
        source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action),
    )
    overlays = {branch: materialize_detached_contact_reactive_status(authority=authority, branch=branch) for branch in ("sleep", "paralysis", "poison", "none")}
    assert [overlays[key]["probability"] for key in overlays] == [
        {"numerator": 11, "denominator": 100}, {"numerator": 1, "denominator": 10},
        {"numerator": 9, "denominator": 100}, {"numerator": 7, "denominator": 10},
    ]
    assert all(overlay["transition_applied"] is False for overlay in overlays.values())


def test_effect_spore_unknown_immunity_authority_fails_closed():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
    _set_active(state, "opponent", ability="effect-spore")
    state["self_side"]["pokemon"][0]["known_item"] = None
    state["self_side"]["pokemon"][0]["known_item_provenance"] = {"status": "unknown"}
    _snapshot, d0 = _refresh(state)
    assert d0["status"] == "rejected"


def test_activation_branch_preserves_no_transition_for_already_statused_and_immunity_without_renormalizing():
    cases = (
        ("static", "none", ["electric"], "attacker_electric_type_immune"),
        ("flame-body", "none", ["fire"], "attacker_fire_type_immune"),
        ("poison-point", "none", ["steel"], "attacker_poison_or_steel_type_immune"),
        ("static", "burn", ["normal"], "attacker_already_statused"),
    )
    for ability, current_condition, types, reason in cases:
        state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
        _set_active(state, "opponent", ability=ability)
        _set_active(state, "self", condition=current_condition, types=types)
        snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
        authority = freeze_runtime_d0_contact_reactive_status_authority(
            strategy_d0=d0, runtime_snapshot=snapshot,
            attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"],
            source_action=action, contact_authority=_contact(d0, snapshot, action),
            source_hit=_source_hit(action),
        )
        assert authority["status"] == "resolved", authority
        assert authority["blocked_reason"] == reason
        activation = materialize_detached_contact_reactive_status(authority=authority, branch="activation")
        assert activation["probability"] == {"numerator": 3, "denominator": 10}
        assert activation["transition_applied"] is False
        assert activation["blocked_reason"] == reason


def test_noncontact_miss_substitute_and_unknown_authority_fail_closed_or_do_not_trigger():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs()
    _set_active(state, "opponent", ability="static")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    non_contact = deepcopy(_contact(d0, snapshot, action))
    non_contact["contact_state"] = "non_contact"
    result = freeze_runtime_d0_contact_reactive_status_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"],
        defender=d0["active_owners"]["opponent"], source_action=action,
        contact_authority=non_contact, source_hit=_source_hit(action),
    )
    assert result["outcome"] == "not_applicable"
    for damage, routing in ((0, "target"), (1, "substitute")):
        no = freeze_runtime_d0_contact_reactive_status_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"],
            defender=d0["active_owners"]["opponent"], source_action=action,
            contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action, damage=damage, routing=routing),
        )
        assert no["status"] == "resolved" and no["outcome"] == "not_applicable"

    assert freeze_runtime_d0_contact_reactive_status_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"],
        defender=d0["active_owners"]["opponent"], source_action=action,
        contact_authority=None, source_hit=_source_hit(action),
    )["status"] == "incomplete"


def test_pair_first_actor_static_status_is_non_retroactive_and_serialized():
    state, snapshot, d0, own_action, response_set, _orders = _pair_inputs()
    _set_active(state, "opponent", ability="static")
    snapshot, d0 = _refresh(state)
    own_action = _rebind_action(own_action, d0)
    opponent_action = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:water-gun")
    opponent_action = deepcopy(opponent_action)
    opponent_action["session_id"] = d0["session_id"]
    opponent_action["source_runtime_fingerprint"] = d0["source_runtime_fingerprint"]
    opponent_action["source_branch_fingerprint"] = d0["strategy_preview_fingerprint"]
    opponent_action["decision_owner"] = d0["decision_owner"]
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action,
        opponent_action=opponent_action, action_order_authority=_order(d0, own_action, opponent_action, "own_first"),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert any(branch["first_action_leaf"]["consequences"]["contact_reactive_status"]["branch"] == "activation" for branch in pair["terminal_branches"])
    assert all(branch["second_action"]["state"] == "executed" for branch in pair["terminal_branches"])
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")

    forged = deepcopy(pair)
    branch = next(row for row in forged["terminal_branches"] if row["first_action_leaf"]["consequences"]["contact_reactive_status"]["branch"] == "activation")
    branch["first_action_leaf"]["consequences"]["contact_reactive_status"]["overlay"]["probability"] = {"numerator": 4, "denominator": 10}
    rejected = normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "pair_final_contact_reactive_status_consequence_invalid"


def test_fixed_two_hit_static_paralysis_persists_but_does_not_cancel_second_hit():
    state, snapshot, d0, action, execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
    _set_active(state, "opponent", ability="static")
    snapshot, d0 = _refresh(state)
    from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
    from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves

    action = _rebind_action(action, d0)
    execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution,
        contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True),
    )
    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert any(
        leaf["ordered_hits"][0]["contact_reactive_status"]["branch"] == "activation"
        and leaf["ordered_hits"][0]["attacker_post_reactive_condition"] == "paralysis"
        and len(leaf["ordered_hits"]) == 2
        and leaf["ordered_hits"][1]["contact_reactive_status"]["overlay"]["transition_applied"] is False
        and leaf["ordered_hits"][1]["contact_reactive_status"]["overlay"]["blocked_reason"] == "attacker_already_statused"
        for leaf in result["terminal_leaves"]
    )


def test_fixed_two_hit_effect_spore_sleep_cancels_only_the_remaining_hits():
    state, snapshot, d0, action, execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
    _set_active(state, "opponent", ability="effect-spore")
    _set_active(state, "self", ability="guts")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
    from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
    execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution,
        contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True),
    )
    assert result["status"] == "evaluable", result.get("reason")
    sleeping = [leaf for leaf in result["terminal_leaves"] if leaf["ordered_hits"][0]["contact_reactive_status"]["branch"] == "sleep"]
    assert sleeping and all(len(leaf["ordered_hits"]) == 1 and leaf["consequences"]["terminal_reason"] == "effect_spore_sleep_cancels_remaining_hits" for leaf in sleeping)
    assert any(
        leaf["ordered_hits"][0]["contact_reactive_status"]["branch"] in {"paralysis", "poison"}
        and len(leaf["ordered_hits"]) == 2
        and leaf["ordered_hits"][1]["guts_status_attack_ability"]["outcome"] == "applicable"
        and leaf["ordered_hits"][1]["guts_status_attack_ability"]["attacker_condition"] == leaf["ordered_hits"][0]["contact_reactive_status"]["branch"]
        for leaf in result["terminal_leaves"]
    )
    assert any(
        leaf["ordered_hits"][0]["contact_reactive_status"]["branch"] == "none" and len(leaf["ordered_hits"]) == 2
        for leaf in result["terminal_leaves"]
    )


def test_effect_spore_prevented_sleep_keeps_its_exact_branch_and_continues():
    from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
    from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
    for ability in ("insomnia", "vital-spirit"):
        state, snapshot, d0, action, _execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
        _set_active(state, "opponent", ability="effect-spore")
        _set_active(state, "self", ability=ability)
        snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
        execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
        result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
            strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution,
            contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True),
        )
        assert result["status"] == "evaluable", result.get("reason")
        sleep = [leaf for leaf in result["terminal_leaves"] if leaf["ordered_hits"][0]["contact_reactive_status"]["branch"] == "sleep"]
        assert sleep and all(
            leaf["ordered_hits"][0]["contact_reactive_status"]["overlay"]["probability"] == {"numerator": 11, "denominator": 100}
            and leaf["ordered_hits"][0]["contact_reactive_status"]["overlay"]["transition_applied"] is False
            and len(leaf["ordered_hits"]) == 2
            for leaf in sleep
        )


def test_effect_spore_overcoat_and_safety_goggles_remain_evaluable_in_the_hit_pipeline():
    from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
    from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
    for ability, item in (("overcoat", "unchanged"), ("pressure", "safety-goggles")):
        state, snapshot, d0, action, _execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
        _set_active(state, "opponent", ability="effect-spore")
        _set_active(state, "self", ability=ability, item_marker=item)
        snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
        execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
        result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
            strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution,
            contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True),
        )
        assert result["status"] == "evaluable", result.get("reason")
        assert all(hit["contact_reactive_status"]["branch"] == "not_applicable" for leaf in result["terminal_leaves"] for hit in leaf["ordered_hits"])


def test_effect_spore_ledger_rejects_forged_mass_cancellation_transition_and_hit_binding():
    from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
    from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import _contact_reactive_status as pair_status_valid
    from llm.advisor_variable_two_to_five_hit_graph_shared_pair_ledger import _contact_reactive_status as graph_status_valid

    state, snapshot, d0, action, _execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
    _set_active(state, "opponent", ability="effect-spore")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution,
        contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True),
    )
    status = next(leaf["ordered_hits"][0]["contact_reactive_status"] for leaf in result["terminal_leaves"] if leaf["ordered_hits"][0]["contact_reactive_status"]["branch"] == "sleep")
    assert pair_status_valid(status) and graph_status_valid(status)
    for mutate in (
        lambda row: row["authority"]["effect_spore_outcomes"][0].update(probability={"numerator": 12, "denominator": 100}),
        lambda row: row["overlay"].update(cancels_remaining_hits=False),
        lambda row: row["overlay"]["hypothetical_condition_authority"].update(condition="poison"),
        lambda row: row["authority"]["source_hit"].update(hit_index=2),
    ):
        forged = deepcopy(status)
        mutate(forged)
        assert not pair_status_valid(forged)
        assert not graph_status_valid(forged)


def test_effect_spore_sleep_cancels_variable_population_bomb_and_triple_hit_graphs():
    cases = []
    state, _snapshot, _d0, action, _execution, _own, _foe = _variable_inputs(power=1, target_hp=1000)
    cases.append(("variable", state, action))
    state, _snapshot, _d0, action, _execution, _own, _foe = _population_inputs(accuracy=100, power=1, target_hp=1000)
    cases.append(("population", state, action))
    state, _snapshot, _d0, action, _execution, _own, _foe = _escalating_inputs(accuracy=100, target_hp=1000)
    cases.append(("triple", state, action))
    for name, state, action in cases:
        _set_active(state, "opponent", ability="effect-spore")
        snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
        if name == "variable":
            from llm.advisor_detached_variable_two_to_five_hit_per_hit_predictive_materialization import materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves
            from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority
            result = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action), contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
        elif name == "population":
            from llm.advisor_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import materialize_detached_population_bomb_per_hit_accuracy_predictive_graph
            from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority
            result = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action), contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
        else:
            from llm.advisor_detached_escalating_three_hit_predictive_graph_materialization import materialize_detached_escalating_three_hit_predictive_graph
            from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import freeze_runtime_d0_escalating_three_hit_execution_authority
            result = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action), contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
        assert result["status"] == "evaluable", result.get("reason")
        assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert any(edge.get("terminal_reason") == "effect_spore_sleep_cancels_remaining_hits" for edge in result["terminal_leaf_edges"]), name


def test_supported_multihit_graphs_branch_contact_status_without_renormalizing_or_resetting_hp():
    cases = []
    state, _snapshot, _d0, action, _execution, _own, _foe = _variable_inputs(power=1, target_hp=1000)
    cases.append(("variable", state, action))
    state, _snapshot, _d0, action, _execution, _own, _foe = _population_inputs(accuracy=100, power=1, target_hp=1000)
    cases.append(("population", state, action))
    state, _snapshot, _d0, action, _execution, _own, _foe = _escalating_inputs(accuracy=100, target_hp=1000)
    cases.append(("escalating", state, action))

    for name, state, action in cases:
        _set_active(state, "self", ability="guts", hp=80)
        _set_active(state, "opponent", ability="static", item_marker="rocky-helmet")
        snapshot, d0 = _refresh(state)
        action = _rebind_action(action, d0)
        if name == "population":
            from llm.advisor_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import materialize_detached_population_bomb_per_hit_accuracy_predictive_graph
            from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority
            execution = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
            result = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
            hits = [edge["attempt_outcome"]["ordered_hit"] for edge in result["terminal_leaf_edges"] if edge["terminal"] and edge["attempt_outcome"].get("ordered_hit")]
        elif name == "escalating":
            from llm.advisor_detached_escalating_three_hit_predictive_graph_materialization import materialize_detached_escalating_three_hit_predictive_graph
            from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import freeze_runtime_d0_escalating_three_hit_execution_authority
            execution = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
            result = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
            hits = [edge["hit_outcome"]["ordered_hit"] for edge in result["terminal_leaf_edges"] if edge["terminal"] and edge["hit_outcome"].get("ordered_hit")]
        else:
            from llm.advisor_detached_variable_two_to_five_hit_per_hit_predictive_materialization import materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves
            from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority
            execution = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
            result = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
            hits = [edge["ordered_hit"] for edge in result["terminal_leaf_edges"] if edge["terminal"]]

        assert result["status"] == "evaluable", result.get("reason")
        assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert any(hit["contact_reactive_status"]["branch"] == "activation" for hit in hits)
        assert any(hit["contact_reactive_damage"]["ordered_sources"][0]["source_kind"] == "rocky-helmet" for hit in hits)
        assert any(
            hit.get("hit_index", 0) > 1
            and hit.get("guts_status_attack_ability", {}).get("outcome") == "applicable"
            and hit["guts_status_attack_ability"]["attacker_condition"] == "paralysis"
            and hit["guts_status_attack_ability"]["condition_source"] == "detached_path_local_attacker_condition_v1"
            and hit["guts_status_attack_ability"]["modifier_q12"] == 6144
            for hit in hits
        ), name
