from __future__ import annotations

from copy import deepcopy

from advisor.damage.item_modifiers import M_LIFE_ORB, get_final_atk_item_modifier
from advisor.damage.q12 import Q12_ONE
from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    materialize_detached_fixed_two_hit_per_hit_predictive_leaves,
)
from llm.advisor_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import (
    materialize_detached_population_bomb_per_hit_accuracy_predictive_graph,
)
from llm.advisor_detached_variable_two_to_five_hit_per_hit_predictive_materialization import (
    materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves,
)
from llm.advisor_detached_escalating_three_hit_predictive_graph_materialization import (
    materialize_detached_escalating_three_hit_predictive_graph,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_life_orb_immediate_authority import (
    freeze_runtime_d0_life_orb_immediate_authority,
    materialize_detached_life_orb_recoil,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _inputs as _fixed_inputs
from tests.test_detached_opponent_response_profile import _inputs as _pair_inputs
from tests.test_detached_opponent_response_profile import _fixed_damage_inputs
from tests.test_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import _inputs as _population_inputs
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _inputs as _variable_inputs
from tests.test_detached_escalating_three_hit_predictive_graph_materialization import _inputs as _escalating_inputs
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


def _rebuild_variable(action, d0, snapshot):
    from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority

    action = _rebind_action(action, d0)
    return action, freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)


def _contact(d0, snapshot, action):
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    contact = deepcopy(contact)
    contact["status"] = "resolved"
    contact["contact_state"] = "contact"
    contact.pop("reason", None)
    return contact


def test_life_orb_uses_exact_canonical_q12_modifier_not_old_value():
    assert M_LIFE_ORB == 5324
    assert get_final_atk_item_modifier("life-orb", type_effectiveness_q12=Q12_ONE) == 5324
    assert get_final_atk_item_modifier("life-orb", type_effectiveness_q12=8192) != 5325


def test_strict_life_orb_authority_resolves_recoil_suppression_and_fail_closed():
    state, _snapshot, _d0, action, _response_set, _orders = _pair_inputs(own_hp=9)
    _set_active(state, "self", hp=9, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state)
    action = _rebind_action(action, d0)
    metadata = action["move_metadata_authority"]["metadata"]
    authority = freeze_runtime_d0_life_orb_immediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
        source_action=action, move_metadata=metadata, qualifying_damage=True,
    )
    assert authority["status"] == "resolved", authority
    assert authority["damage_modifier"]["fraction"] == {"numerator": 5324, "denominator": 4096}
    assert authority["recoil"]["recoil_damage"] == 10
    assert authority["recoil"]["post_hp"] == 0 and authority["recoil"]["fainted"] is True
    assert materialize_detached_life_orb_recoil(authority=authority)["hypothetical_fainted_authority"]["value"] is True

    _set_active(state, "self", hp=9, max_hp=100, ability="magic-guard")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    magic = freeze_runtime_d0_life_orb_immediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], source_action=action, move_metadata=metadata, qualifying_damage=True)
    assert magic["status"] == "resolved" and magic["outcome"] == "recoil_suppressed" and magic["recoil"]["suppressed_by"] == "magic-guard"

    _set_active(state, "self", ability="sheer-force")
    snapshot, d0 = _refresh(state); action = _rebind_action(action, d0)
    metadata = {**metadata, "move_id": "iron-head"}
    sheer_action = {**action, "action_id": "attack:iron-head", "identity": "iron-head"}
    sheer = freeze_runtime_d0_life_orb_immediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], source_action=sheer_action, move_metadata=metadata, qualifying_damage=True)
    assert sheer["status"] == "resolved" and sheer["recoil"]["suppressed_by"] == "sheer-force"

    unknown = deepcopy(state)
    unknown["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "unknown"
    snapshot, d0 = _refresh(unknown); action = _rebind_action(action, d0)
    assert freeze_runtime_d0_life_orb_immediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], source_action=action, move_metadata=action["move_metadata_authority"]["metadata"], qualifying_damage=True)["status"] == "incomplete"


def test_single_hit_pair_life_orb_recoil_self_faint_and_target_ko_are_nonretroactive():
    state, _snapshot, _d0, own_action, response_set, _orders = _pair_inputs(own_hp=10, opponent_hp=1)
    _set_active(state, "self", hp=10, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state); own_action = _rebind_action(own_action, d0)
    opponent_action = _rebind_opponent_action(next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:water-gun"), d0)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action, action_order_authority=_order(d0, own_action, opponent_action, "own_first"))
    assert pair["status"] == "evaluable", pair.get("reason")
    assert any(row["first_action_leaf"]["consequences"]["target_ko"] is True and row["first_action_leaf"]["consequences"]["self_fainted"] is True and row["second_action"]["state"] == "cancelled_due_to_faint" for row in pair["terminal_branches"])


def test_fixed_two_hit_life_orb_recoils_once_after_completed_move_not_between_hits():
    state, snapshot, d0, action, execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
    _set_active(state, "self", hp=25, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state); action, execution = _rebuild_fixed(action, d0, snapshot)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable", result.get("reason")
    hit_leaves = [leaf for leaf in result["terminal_leaves"] if leaf["hit_state"] == "hit"]
    assert hit_leaves and all(len(leaf["ordered_hits"]) == 2 for leaf in hit_leaves)
    assert {leaf["consequences"]["own_final_hp"] for leaf in hit_leaves} == {15}
    assert all(leaf["consequences"]["life_orb"]["authority"]["recoil"]["recoil_damage"] == 10 for leaf in hit_leaves)


def test_variable_and_population_bomb_life_orb_recoil_once_preserves_mass():
    state, _snapshot, _d0, action, _execution, _own, _foe = _variable_inputs(power=1, target_hp=1000)
    _set_active(state, "self", hp=35, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state); action, execution = _rebuild_variable(action, d0, snapshot)
    variable = materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert variable["status"] == "evaluable", variable.get("reason")
    assert variable["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    terminal = [edge for edge in variable["terminal_leaf_edges"] if edge["terminal"]]
    assert terminal and all(edge["terminal_consequences"]["own_final_hp"] == 25 for edge in terminal)

    state, _snapshot, _d0, action, execution, _own, _foe = _population_inputs(accuracy=100, power=1, target_hp=1000, item="life-orb")
    _set_active(state, "self", hp=35, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state)
    action = _rebind_action(action, d0)
    from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority

    execution = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    population = materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert population["status"] == "evaluable", population.get("reason")
    assert population["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    terminal = [edge for edge in population["terminal_leaf_edges"] if edge["terminal"] and edge["terminal_consequences"]["landed_hit_count"] > 0]
    assert terminal and all(edge["terminal_consequences"]["life_orb"]["authority"]["recoil"]["recoil_damage"] == 10 for edge in terminal)


def test_escalating_three_hit_life_orb_recoil_once_after_terminal_path():
    state, _snapshot, _d0, action, _execution, _own, _foe = _escalating_inputs(accuracy=100, target_hp=1000, item="life-orb")
    _set_active(state, "self", hp=35, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state)
    action = _rebind_action(action, d0)
    from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import freeze_runtime_d0_escalating_three_hit_execution_authority

    execution = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    result = materialize_detached_escalating_three_hit_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution)
    assert result["status"] == "evaluable", result.get("reason")
    terminal = [edge for edge in result["terminal_leaf_edges"] if edge["terminal"]]
    assert terminal and all(edge["terminal_consequences"]["own_final_hp"] == 25 for edge in terminal)
    assert all(edge["terminal_consequences"]["life_orb"]["authority"]["recoil"]["recoil_damage"] == 10 for edge in terminal)


def test_fixed_damage_successful_hit_gets_life_orb_recoil_without_damage_boost():
    state, snapshot, d0, own_action, opponent_action, order = _fixed_damage_inputs(own_first=True, own_hp=10, opponent_hp=100)
    _set_active(state, "self", hp=10, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state)
    own_action = _rebind_action(own_action, d0)
    opponent_action = _rebind_opponent_action(opponent_action, d0)
    order = {**order, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_actor": d0["active_owners"]["self"], "opponent_actor": d0["active_owners"]["opponent"]}
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action, action_order_authority=order)
    assert pair["status"] == "evaluable", pair.get("reason")
    first = pair["terminal_branches"][0]["first_action_leaf"]
    assert first["consequences"]["damage"] == 50
    assert first["consequences"]["own_final_hp"] == 0
    assert first["consequences"]["life_orb"]["authority"]["damage_modifier"]["applies"] is False
    assert pair["terminal_branches"][0]["second_action"]["state"] == "cancelled_due_to_faint"


def test_contact_reactive_damage_feeds_life_orb_recoil_without_hp_reset():
    state, _snapshot, _d0, action, _execution, _own, _foe = _fixed_inputs(power=1, target_hp=1000)
    _set_active(state, "self", hp=30, max_hp=100, item_marker="life-orb")
    _set_active(state, "opponent", ability="rough-skin", item_marker=None)
    snapshot, d0 = _refresh(state); action, execution = _rebuild_fixed(action, d0, snapshot)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_authority=execution, contact_reactive_contact_authority=_contact(d0, snapshot, action))
    assert result["status"] == "evaluable", result.get("reason")
    hit_leaf = next(leaf for leaf in result["terminal_leaves"] if leaf["hit_state"] == "hit")
    assert hit_leaf["ordered_hits"][0]["attacker_post_reactive_hp"] == 18
    assert hit_leaf["ordered_hits"][1]["attacker_post_reactive_hp"] == 6
    assert hit_leaf["consequences"]["own_final_hp"] == 0
    assert hit_leaf["consequences"]["life_orb"]["authority"]["recoil"]["pre_hp"] == 6


def test_life_orb_pair_ledger_rejects_forged_recoil_provenance():
    state, _snapshot, d0, own_action, opponent_action, order = _fixed_damage_inputs(own_first=True, own_hp=10, opponent_hp=100)
    _set_active(state, "self", hp=10, max_hp=100, item_marker="life-orb")
    snapshot, d0 = _refresh(state)
    own_action = _rebind_action(own_action, d0)
    opponent_action = _rebind_opponent_action(opponent_action, d0)
    order = {**order, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_actor": d0["active_owners"]["self"], "opponent_actor": d0["active_owners"]["opponent"]}
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own_action,
        opponent_action=opponent_action,
        action_order_authority=order,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"

    forged_modifier = deepcopy(pair)
    for consequence in _life_orb_consequences(forged_modifier):
        consequence["authority"]["damage_modifier"]["modifier_q12"] = 5325
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged_modifier)["reason"] == "pair_final_life_orb_consequence_invalid"

    forged_recoil = deepcopy(pair)
    for consequence in _life_orb_consequences(forged_recoil):
        consequence["authority"]["recoil"]["recoil_damage"] = 9
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged_recoil)["reason"] == "pair_final_life_orb_consequence_invalid"

    forged_suppression = deepcopy(pair)
    for consequence in _life_orb_consequences(forged_suppression):
        consequence["authority"]["recoil"]["suppressed_by"] = "forged-force"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged_suppression)["reason"] == "pair_final_life_orb_consequence_invalid"


def _life_orb_consequences(pair):
    consequences = [
        row["first_action_leaf"]["consequences"]["life_orb"]
        for row in pair["terminal_branches"]
        if row["first_action_leaf"]["consequences"].get("life_orb", {}).get("outcome") == "recoiled"
    ]
    assert consequences
    return consequences
