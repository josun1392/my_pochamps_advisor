from __future__ import annotations

from copy import deepcopy

from llm.advisor_detached_escalating_three_hit_predictive_graph_materialization import (
    materialize_detached_escalating_three_hit_predictive_graph,
)
from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    materialize_detached_fixed_two_hit_per_hit_predictive_leaves,
)
from llm.advisor_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import (
    materialize_detached_population_bomb_per_hit_accuracy_predictive_graph,
)
from llm.advisor_detached_variable_two_to_five_hit_per_hit_predictive_materialization import (
    materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves,
)
from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_contact_reactive_damage_authority import (
    freeze_runtime_d0_contact_reactive_damage_authority,
    materialize_detached_contact_reactive_damage,
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


def _set_active(state, side, *, hp=None, max_hp=None, ability=None, item_marker="unchanged"):
    row = state[f"{side}_side"]["pokemon"][0]
    if max_hp is not None:
        row["max_hp"] = max_hp
    if hp is not None:
        row["current_hp"] = hp
        row["fainted"] = hp == 0
    if ability is not None:
        row["current_ability"] = ability
    if item_marker != "unchanged":
        row["known_item"] = item_marker
        row["known_item_provenance"]["status"] = "known" if isinstance(item_marker, str) else "known_absent"


def _contact(d0, snapshot, action, *, force_contact=False):
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    if force_contact:
        contact = deepcopy(contact)
        contact["status"] = "resolved"
        contact["contact_state"] = "contact"
        contact.pop("reason", None)
    return contact


def _source_hit(action, *, damage=1, routing="target", index=1):
    return {"source_action_id": action["action_id"], "source_move_id": action["identity"], "hit_index": index, "actual_damage": damage, "target_routing": routing}


def test_contact_reactive_authority_resolves_exact_sources_damage_and_order():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs(own_hp=80)
    _set_active(state, "self", hp=80, max_hp=80)
    _set_active(state, "opponent", ability="rough-skin", item_marker="rocky-helmet")
    snapshot, d0 = _refresh(state)
    action = deepcopy(action)
    action["move_metadata_authority"]["session_id"] = d0["session_id"]
    action["move_metadata_authority"]["source_runtime_fingerprint"] = d0["source_runtime_fingerprint"]
    action["move_metadata_authority"]["source_branch_fingerprint"] = d0["strategy_preview_fingerprint"]
    action["move_metadata_authority"]["decision_owner"] = d0["decision_owner"]
    result = freeze_runtime_d0_contact_reactive_damage_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"],
        source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action),
    )
    assert result["status"] == "resolved", result
    assert result["outcome"] == "applies"
    assert [(row["source_kind"], row["damage_fraction"], row["pre_hp"], row["reactive_damage"], row["post_hp"]) for row in result["ordered_sources"]] == [
        ("rough-skin", {"numerator": 1, "denominator": 8}, 80, 10, 70),
        ("rocky-helmet", {"numerator": 1, "denominator": 6}, 70, 13, 57),
    ]
    overlay = materialize_detached_contact_reactive_damage(authority=result)
    assert overlay["status"] == "resolved" and overlay["hypothetical_hp_authority"]["current_hp"] == 57


def test_contact_reactive_authority_covers_helmet_iron_barbs_no_effect_and_fail_closed_inputs():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs(own_hp=81)
    _set_active(state, "self", hp=81, max_hp=81)
    _set_active(state, "opponent", ability="iron-barbs", item_marker="rocky-helmet")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    result = freeze_runtime_d0_contact_reactive_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"], source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action))
    assert [row["reactive_damage"] for row in result["ordered_sources"]] == [10, 13]
    assert result["post_hp"] == 58

    _set_active(state, "opponent", ability="pressure", item_marker=None)
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    none = freeze_runtime_d0_contact_reactive_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"], source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action))
    assert none["status"] == "resolved" and none["outcome"] == "no_reactive_source"

    unknown_item = deepcopy(state)
    unknown_item["opponent_side"]["pokemon"][0]["known_item_provenance"]["status"] = "unknown"
    snapshot, d0 = _refresh(unknown_item); action = _rebind_action(action, d0)
    assert freeze_runtime_d0_contact_reactive_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"], source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action))["status"] == "incomplete"

    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 1; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert freeze_runtime_d0_contact_reactive_damage_authority(strategy_d0=d0, runtime_snapshot=stale, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"], source_action=action, contact_authority=_contact(d0, snapshot, action), source_hit=_source_hit(action))["status"] == "rejected"


def test_contact_reactive_applicability_miss_noncontact_and_substitute_do_not_trigger():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs(own_hp=80, own_move="water-gun")
    _set_active(state, "self", hp=80, max_hp=80)
    _set_active(state, "opponent", ability="rough-skin", item_marker="rocky-helmet")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    non_contact = deepcopy(_contact(d0, snapshot, action, force_contact=True))
    non_contact["contact_state"] = "non_contact"
    non = freeze_runtime_d0_contact_reactive_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"], source_action=action, contact_authority=non_contact, source_hit=_source_hit(action))
    assert non["status"] == "resolved" and non["outcome"] == "not_applicable"

    contact_action = deepcopy(action); contact_action["identity"] = "tackle"; contact_action["action_id"] = "attack:tackle"
    contact_action["move_metadata_authority"]["candidate_id"] = "attack:tackle"
    contact_action["move_metadata_authority"]["move_id"] = "tackle"
    contact_action["move_metadata_authority"]["metadata"]["move_id"] = "tackle"
    contact_action["move_metadata_authority"]["metadata"]["category"] = "physical"
    contact_action["move_metadata_authority"]["metadata"]["type"] = "normal"
    sub = freeze_runtime_d0_contact_reactive_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], defender=d0["active_owners"]["opponent"], source_action=contact_action, contact_authority=_contact(d0, snapshot, contact_action, force_contact=True), source_hit=_source_hit(contact_action, routing="substitute"))
    assert sub["status"] == "resolved" and sub["outcome"] == "not_applicable" and sub["reason"] == "source_hit_contacted_substitute_not_holder"


def test_single_hit_pair_materializes_reactive_self_faint_and_ledger_metrics():
    state, _snapshot, _d0, own_action, response_set, _orders = _pair_inputs(own_hp=10, opponent_hp=100)
    _set_active(state, "self", hp=10, max_hp=80)
    _set_active(state, "opponent", ability="rough-skin", item_marker=None)
    snapshot, d0 = _refresh(state); own_action = _rebind_action(own_action, d0)
    opponent_action = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:water-gun")
    opponent_action = _rebind_opponent_action(opponent_action, d0)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action, action_order_authority=_order(d0, own_action, opponent_action, "own_first"))
    assert pair["status"] == "evaluable", pair.get("reason")
    assert any(row["first_action_leaf"]["consequences"]["self_fainted"] is True for row in pair["terminal_branches"])
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["status"] == "resolved"


def test_fixed_two_hit_contact_reactive_damage_carries_attacker_hp_and_stops_on_self_faint():
    state, snapshot, d0, action, execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
    _set_active(state, "self", hp=15, max_hp=80)
    _set_active(state, "opponent", ability="rough-skin", item_marker=None)
    snapshot, d0 = _refresh(state)
    action, execution = _rebuild_fixed(action, d0, snapshot)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
    assert result["status"] == "evaluable", result.get("reason")
    assert all(leaf["consequences"]["self_fainted"] is True for leaf in result["terminal_leaves"])
    assert all(len(leaf["ordered_hits"]) == 2 for leaf in result["terminal_leaves"])
    assert all(leaf["ordered_hits"][0]["attacker_post_reactive_hp"] == 5 and leaf["ordered_hits"][1]["attacker_post_reactive_hp"] == 0 for leaf in result["terminal_leaves"])

    _set_active(state, "self", hp=20, max_hp=80)
    _set_active(state, "opponent", ability="rough-skin", item_marker="rocky-helmet")
    snapshot, d0 = _refresh(state); action, execution = _rebuild_fixed(action, d0, snapshot)
    stopped = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
    assert stopped["status"] == "evaluable", stopped.get("reason")
    assert all(len(leaf["ordered_hits"]) == 1 and leaf["consequences"]["terminal_reason"] == "attacker_fainted_from_contact_reactive_damage" for leaf in stopped["terminal_leaves"])


def test_supported_multihit_graphs_carry_attacker_hp_and_terminate_without_renormalizing():
    cases = []
    state, snapshot, d0, action, execution, _own, _foe = _variable_inputs(power=1, target_hp=1000)
    cases.append(("variable", state, snapshot, d0, action, execution, materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves, "ordered_hit"))
    state, snapshot, d0, action, execution, _own, _foe = _population_inputs(accuracy=100, power=1, target_hp=1000)
    cases.append(("population", state, snapshot, d0, action, execution, materialize_detached_population_bomb_per_hit_accuracy_predictive_graph, "attempt_outcome"))
    state, snapshot, d0, action, execution, _own, _foe = _escalating_inputs(accuracy=100, target_hp=1000)
    cases.append(("escalating", state, snapshot, d0, action, execution, materialize_detached_escalating_three_hit_predictive_graph, "hit_outcome"))

    for _name, state, _snapshot, _d0, action, _execution, materialize, kind in cases:
        _set_active(state, "self", hp=10, max_hp=80)
        _set_active(state, "opponent", ability="rough-skin", item_marker=None)
        snapshot, d0 = _refresh(state)
        action = _rebind_action(action, d0)
        if action["identity"] == "population-bomb":
            from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority
            execution = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
        elif action["identity"] in {"triple-axel", "triple-kick"}:
            from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import freeze_runtime_d0_escalating_three_hit_execution_authority
            execution = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
        else:
            from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority
            execution = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
        result = materialize(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action, force_contact=True))
        assert result["status"] == "evaluable", result.get("reason")
        assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        terminal_edges = [edge for edge in result["terminal_leaf_edges"] if edge["terminal"]]
        assert terminal_edges and all(edge["terminal_reason"] == "attacker_fainted_from_contact_reactive_damage" for edge in terminal_edges)
        if kind == "ordered_hit":
            assert all(edge["ordered_hit"]["attacker_post_reactive_hp"] == 0 for edge in terminal_edges)
        elif kind == "attempt_outcome":
            assert all(edge["attempt_outcome"]["ordered_hit"]["attacker_post_reactive_hp"] == 0 for edge in terminal_edges)
        else:
            assert all(edge["hit_outcome"]["ordered_hit"]["attacker_post_reactive_hp"] == 0 for edge in terminal_edges)


def _rebind_action(action, d0):
    action = deepcopy(action)
    authority = action["move_metadata_authority"]
    authority["session_id"] = d0["session_id"]
    authority["source_runtime_fingerprint"] = d0["source_runtime_fingerprint"]
    authority["source_branch_fingerprint"] = d0["strategy_preview_fingerprint"]
    authority["decision_owner"] = d0["decision_owner"]
    authority["active_attacker"] = d0["decision_owner"]
    return action


def _rebind_opponent_action(action, d0):
    action = deepcopy(action)
    action["session_id"] = d0["session_id"]
    action["source_runtime_fingerprint"] = d0["source_runtime_fingerprint"]
    action["source_branch_fingerprint"] = d0["strategy_preview_fingerprint"]
    action["decision_owner"] = d0["decision_owner"]
    return action


def _rebuild_fixed(action, d0, snapshot):
    from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority

    action = _rebind_action(action, d0)
    return action, freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
