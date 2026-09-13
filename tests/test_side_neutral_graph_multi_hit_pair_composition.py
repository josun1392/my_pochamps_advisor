from copy import deepcopy

from llm.advisor_detached_opponent_response_profile import materialize_detached_opponent_response_profile
from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import (
    materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair,
)
from llm.advisor_exact_action_pair_descriptive_metrics import (
    project_exact_immediate_action_pair_descriptive_metrics,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_mat_block_direct_damage_applicability_authority import (
    freeze_runtime_d0_mat_block_direct_damage_applicability_authority,
    freeze_runtime_d0_mat_block_incoming_bypass_authority,
)
from llm.advisor_runtime_d0_direct_heal_execution_authority import (
    freeze_runtime_d0_direct_heal_execution_authority,
)
from llm.advisor_runtime_d0_atomic_item_swap_status_execution_authority import (
    freeze_runtime_d0_atomic_item_swap_status_execution_authority,
)
from llm.advisor_runtime_d0_pivot_replacement_authority import (
    freeze_runtime_d0_pivot_replacement_authority,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context
from tests.test_detached_immediate_protection_response_pair import (
    _protect_action,
    _quick_guard_authority,
    _silk_interaction,
    _success,
)
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_detached_variable_two_to_five_hit_graph_immediate_move_pair import (
    _escalating_action,
    _opponent_variable,
    _variable_action,
)
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _ordinary_opponent(response_set):
    return next(
        row for row in response_set["actions"]
        if row["action_id"] == "opponent_attack:tackle"
    )


def test_own_graph_executes_natively_when_slower_than_ordinary_opponent():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(
        own_hp=100, opponent_hp=1,
    )
    own = _variable_action(d0, "bullet-seed", power=500)
    opponent = _ordinary_opponent(response_set)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "opponent_first"),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    order = pair["order_graphs"][0]
    assert order["action_order"] == "opponent_first"
    assert "first_action_leaf_set" in order and "first_action_graph" not in order
    executed = [
        outcome
        for transition in order["terminal_transitions"]
        if transition["second_action"]["state"] == "outcome_graph"
        for outcome in transition["second_action"]["outcomes"]
        if outcome["state"] == "executed"
    ]
    assert executed and all(
        outcome["second_action_graph"]["move_id"] == "bullet-seed"
        for outcome in executed
    )
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert ledger["status"] == "evaluable"
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert metrics["status"] == "resolved"


def test_opponent_graph_executes_natively_when_slower_than_ordinary_own_attack():
    _state, snapshot, d0, own, response_set, _orders = _inputs(
        own_hp=1, opponent_hp=100,
    )
    opponent = _opponent_variable(_ordinary_opponent(response_set), "rock-blast", power=500)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    order = pair["order_graphs"][0]
    assert order["action_order"] == "own_first"
    assert "first_action_leaf_set" in order and "first_action_graph" not in order
    executed = [
        outcome
        for transition in order["terminal_transitions"]
        for outcome in transition["second_action"].get("outcomes", ())
        if outcome["state"] == "executed"
    ]
    assert executed and all(
        outcome["second_action_graph"]["move_id"] == "rock-blast"
        for outcome in executed
    )


def test_live_response_profile_routes_known_opponent_graph_move_to_native_graph_pair():
    _state, snapshot, d0, own, response_set, _orders = _inputs(
        own_hp=1, opponent_hp=100,
    )
    source = _ordinary_opponent(response_set)
    opponent = _opponent_variable(source, "rock-blast", power=500)
    response_id = opponent["action_id"]
    response_set = deepcopy(response_set)
    response_set["actions"] = (opponent,)
    response_set["selectable_response_action_ids"] = (response_id,)
    if "response_action_ids" in response_set:
        response_set["response_action_ids"] = (response_id,)
    if "known_action_ids" in response_set:
        response_set["known_action_ids"] = (response_id,)
    order = _order(d0, own, opponent, "own_first")
    profile = materialize_detached_opponent_response_profile(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        response_set_authority=response_set,
        action_order_authorities={response_id: order},
    )
    assert profile["status"] == "evaluable", profile.get("reason")
    entry = profile["response_entries"][0]
    assert entry["pair"]["schema_version"] == "detached-variable-two-to-five-hit-graph-immediate-move-pair-v1"
    assert entry["pair"]["order_graphs"][0]["first_action_leaf_set"]
    assert any(
        outcome["second_action_graph"]["move_id"] == "rock-blast"
        for transition in entry["pair"]["order_graphs"][0]["terminal_transitions"]
        for outcome in transition["second_action"].get("outcomes", ())
        if outcome["state"] == "executed"
    )
    assert entry["exact_pair_outcome_ledger"]["status"] == "evaluable"
    assert entry["descriptive_metrics"]["status"] == "resolved"


def _protectable_graph(d0, move_id="bullet-seed", power=500):
    own = _variable_action(d0, move_id, power=power)
    own["move_metadata_authority"]["metadata"].update(
        protection_bypass=False, target="selected-pokemon", priority=0,
    )
    return own


def test_graph_protect_and_detect_block_before_native_graph_execution():
    for move_id in ("protect", "detect"):
        _state, snapshot, d0, _own, response_set, _orders = _inputs()
        own = _protectable_graph(d0)
        guard = _protect_action(d0, move_id)
        pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
            strategy_d0=d0,
            runtime_snapshot=snapshot,
            own_action=own,
            opponent_action=guard,
            action_order_authority=_order(d0, own, guard, "opponent_first"),
            opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        )
        assert pair["status"] == "evaluable", pair.get("reason")
        order = pair["order_graphs"][0]
        assert "first_action_leaf_set" in order and "first_action_graph" not in order
        assert len(order["terminal_transitions"]) == 1
        second = order["terminal_transitions"][0]["second_action"]
        assert second["state"] == "prevented_by_protection"
        assert "outcomes" not in second
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
        assert ledger["status"] == "evaluable"
        assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_graph_silk_trap_reactive_consequence_applies_once_before_block():
    _state, snapshot, d0, _own, response_set, _orders = _inputs()
    own = _escalating_action(d0, "triple-kick", accuracy=100)
    own["move_metadata_authority"]["metadata"].update(
        protection_bypass=False, target="selected-pokemon",
    )
    shield = _protect_action(d0, "silk-trap")
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=own,
        attacker=d0["active_owners"]["self"],
        target=d0["active_owners"]["opponent"],
    )
    assert contact["contact_state"] == "contact"
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact,
        silk_trap_reactive_interaction_authority=_silk_interaction(
            d0, move_id="triple-kick",
        ),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    order = pair["order_graphs"][0]
    assert len(order["terminal_transitions"]) == 1
    transition = order["terminal_transitions"][0]
    assert transition["second_action"]["state"] == "prevented_by_protection"
    leaf = transition["first_terminal_leaf"]
    effect = leaf["consequences"]["deterministic_stage_effect"]
    assert effect["stat"] == "speed" and effect["requested_delta"] == -1
    assert "second_action_graph" not in transition["second_action"]


def test_graph_quick_guard_not_applicable_executes_native_graph_and_missing_fails_closed():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    own = _protectable_graph(d0)
    guard = _protect_action(d0, "quick-guard")
    authority = _quick_guard_authority(d0, snapshot, own, blocked=False)
    assert authority["status"] == "resolved" and authority["outcome"] == "not_applicable"
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=guard,
        action_order_authority=_order(d0, own, guard, "opponent_first"),
        quick_guard_priority_applicability_authority=authority,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    outcomes = pair["order_graphs"][0]["terminal_transitions"][0]["second_action"]["outcomes"]
    assert any(
        row.get("second_action_graph", {}).get("move_id") == "bullet-seed"
        for row in outcomes if row["state"] == "executed"
    )
    missing = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=guard,
        action_order_authority=_order(d0, own, guard, "opponent_first"),
    )
    assert missing["status"] == "incomplete"


def test_graph_mat_block_applicable_blocks_without_native_graph_branches():
    _state, snapshot, d0, _own, response_set, _orders = _inputs()
    own = _protectable_graph(d0)
    guard = _protect_action(d0, "mat-block")
    opponent = d0["active_owners"]["opponent"]
    eligibility = {
        "status": "resolved",
        "schema_version": "runtime-d0-mat-block-active-entry-eligibility-authority-v1",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "mat_block_user": deepcopy(opponent),
        "mat_block_action_id": guard["action_id"],
        "mat_block_move_id": "mat-block",
        "active_entry_token": "entry-1",
        "eligibility": "eligible",
    }
    bypass = freeze_runtime_d0_mat_block_incoming_bypass_authority(
        strategy_d0=d0,
        incoming_actor=d0["active_owners"]["self"],
        incoming_action=own,
        frozen_move_metadata=own["move_metadata_authority"]["metadata"],
    )
    applicability = freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=eligibility,
        bypass_authority=bypass,
        incoming_action={
            "action_id": own["action_id"],
            "move_id": own["identity"],
            "category": own["move_metadata_authority"]["metadata"]["category"],
        },
        protected_recipients=(opponent,),
    )
    assert applicability["status"] == "resolved" and applicability["outcome"] == "applies"
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=guard,
        action_order_authority=_order(d0, own, guard, "opponent_first"),
        mat_block_direct_damage_applicability_authority=applicability,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    transition = pair["order_graphs"][0]["terminal_transitions"][0]
    assert transition["second_action"]["state"] == "prevented_by_mat_block"
    assert "outcomes" not in transition["second_action"]


def _opponent_recover(d0):
    actor = d0["active_owners"]["opponent"]
    target = d0["active_owners"]["self"]
    metadata = {
        "move_id": "recover",
        "category": "status",
        "target": "self",
        "priority": 0,
        "accuracy": None,
        "power": None,
    }
    return {
        "status": "resolved",
        "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": "opponent_attack:recover",
        "action_type": "attack",
        "move_id": "recover",
        "identity": "recover",
        "opponent_actor": deepcopy(actor),
        "target_owner": deepcopy(target),
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "metadata_authority": {
            "status": "resolved",
            "move_id": "recover",
            "metadata": metadata,
        },
        "usability": {"status": "known_usable"},
        "selectability": "selectable",
    }


def _direct_heal_authority(d0, snapshot, action):
    return freeze_runtime_d0_direct_heal_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=d0["active_owners"]["opponent"],
    )


def test_heal_first_then_graph_consumes_exact_healed_hp():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=20)
    own = _protectable_graph(d0, power=1)
    heal = _opponent_recover(d0)
    authority = _direct_heal_authority(d0, snapshot, heal)
    assert authority["status"] == "resolved"
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=heal,
        action_order_authority=_order(d0, own, heal, "opponent_first"),
        direct_heal_execution_authorities={heal["action_id"]: authority},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    transition = pair["order_graphs"][0]["terminal_transitions"][0]
    assert transition["first_terminal_leaf"]["consequences"]["direct_heal"]["post_hp"] == 70
    graph = transition["second_action"]["outcomes"][0]["second_action_graph"]
    roots = [
        node for node in graph["terminal_leaf_nodes"]
        if node["completed_hit_count"] == 0
    ]
    assert roots and all(node["target_hp"] == 70 for node in roots)


def test_graph_first_then_surviving_healer_heals_afterward():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=80)
    own = _protectable_graph(d0, power=1)
    heal = _opponent_recover(d0)
    authority = _direct_heal_authority(d0, snapshot, heal)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=heal,
        action_order_authority=_order(d0, own, heal, "own_first"),
        direct_heal_execution_authorities={heal["action_id"]: authority},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    executed = [
        outcome
        for transition in pair["order_graphs"][0]["terminal_transitions"]
        for outcome in transition["second_action"].get("outcomes", ())
        if outcome["state"] == "executed"
    ]
    assert executed
    for outcome in executed:
        leaf = outcome["second_action_terminal_leaves"][0]
        heal_result = leaf["consequences"]["direct_heal"]
        assert heal_result["post_hp"] >= heal_result["pre_hp"]
        assert heal_result["post_hp"] == min(heal_result["max_hp"], heal_result["pre_hp"] + heal_result["max_hp"] // 2)


def test_graph_ko_cancels_later_direct_heal():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    own = _protectable_graph(d0, power=500)
    heal = _opponent_recover(d0)
    authority = _direct_heal_authority(d0, snapshot, heal)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=heal,
        action_order_authority=_order(d0, own, heal, "own_first"),
        direct_heal_execution_authorities={heal["action_id"]: authority},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert all(
        transition["second_action"]["state"] == "cancelled_due_to_faint"
        for transition in pair["order_graphs"][0]["terminal_transitions"]
    )


def _itemized_inputs(*, own_item, opponent_item, own_hp=100, opponent_hp=100):
    state, snapshot, d0, _own, response_set, _orders = _inputs(
        own_hp=own_hp, opponent_hp=opponent_hp,
    )
    state["self_side"]["pokemon"][0]["known_item"] = own_item
    state["opponent_side"]["pokemon"][0]["known_item"] = opponent_item
    state["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known" if own_item is not None else "known_absent"
    state["opponent_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known" if opponent_item is not None else "known_absent"
    snapshot = {
        **snapshot,
        "state": state,
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=d0["active_owners"]["self"],
    )
    return state, snapshot, d0


def _opponent_swap(d0, move_id="trick"):
    actor = d0["active_owners"]["opponent"]
    target = d0["active_owners"]["self"]
    metadata = {
        "move_id": move_id,
        "category": "status",
        "type": "psychic" if move_id == "trick" else "dark",
        "accuracy": 100,
        "priority": 0,
        "target": "selected-pokemon",
        "contact": False,
    }
    return {
        "status": "resolved",
        "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": f"opponent_attack:{move_id}",
        "action_type": "attack",
        "move_id": move_id,
        "identity": move_id,
        "opponent_actor": deepcopy(actor),
        "target_owner": deepcopy(target),
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "metadata_authority": {
            "status": "resolved",
            "move_id": move_id,
            "metadata": metadata,
        },
        "usability": {"status": "known_usable"},
        "selectability": "selectable",
    }


def _swap_authority(d0, snapshot, action):
    actor, target = d0["active_owners"]["opponent"], d0["active_owners"]["self"]
    applicability = {
        "status": "resolved",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "actor": deepcopy(actor),
        "target": deepcopy(target),
        "action_id": action["action_id"],
        "move_id": action["move_id"],
        "outcome": "ordinary",
    }
    return freeze_runtime_d0_atomic_item_swap_status_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        execution_applicability_authority=applicability,
    )


def test_trick_first_graph_consumes_exact_swapped_life_orb_state():
    _state, snapshot, d0 = _itemized_inputs(
        own_item="focus-sash", opponent_item=None,
    )
    own = _protectable_graph(d0, power=500)
    trick = _opponent_swap(d0, "trick")
    authority = _swap_authority(d0, snapshot, trick)
    assert authority["status"] == "resolved" and authority["outcome"] == "executed_swap"
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=trick,
        action_order_authority=_order(d0, own, trick, "opponent_first"),
        atomic_item_swap_status_execution_authorities={trick["action_id"]: authority},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    graph = pair["order_graphs"][0]["terminal_transitions"][0]["second_action"]["outcomes"][0]["second_action_graph"]
    first_hit_edges = [
        edge for edge in graph["terminal_leaf_edges"]
        if edge.get("ordered_hit", {}).get("hit_index") == 1
    ]
    assert first_hit_edges
    assert all(edge["ordered_hit"].get("focus_sash_applied") is True for edge in first_hit_edges)


def test_graph_first_then_switcheroo_does_not_retroactively_change_graph():
    _state, snapshot, d0 = _itemized_inputs(
        own_item="focus-sash", opponent_item=None,
    )
    own = _protectable_graph(d0, power=1)
    swap = _opponent_swap(d0, "switcheroo")
    authority = _swap_authority(d0, snapshot, swap)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=swap,
        action_order_authority=_order(d0, own, swap, "own_first"),
        atomic_item_swap_status_execution_authorities={swap["action_id"]: authority},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    first_graph = pair["order_graphs"][0]["first_action_graph"]
    first_hit_edges = [
        edge for edge in first_graph["terminal_leaf_edges"]
        if edge.get("ordered_hit", {}).get("hit_index") == 1
    ]
    assert first_hit_edges
    assert all(edge["ordered_hit"].get("focus_sash_applied") is False for edge in first_hit_edges)
    second_leaves = [
        outcome["second_action_terminal_leaves"][0]
        for transition in pair["order_graphs"][0]["terminal_transitions"]
        for outcome in transition["second_action"].get("outcomes", ())
        if outcome["state"] == "executed"
    ]
    assert second_leaves
    for leaf in second_leaves:
        swap_transition = leaf["consequences"]["atomic_item_swap_status"]
        assert swap_transition["actor_item_after"]["item"] == "focus-sash"
        assert swap_transition["target_item_after"]["item"] is None


def _opponent_status_special(d0, move_id):
    types = {"taunt": "dark", "encore": "normal", "disable": "normal"}
    actor, target = d0["active_owners"]["opponent"], d0["active_owners"]["self"]
    metadata = {
        "move_id": move_id,
        "category": "status",
        "type": types[move_id],
        "accuracy": 100,
        "priority": 0,
        "target": "selected-pokemon",
        "contact": False,
    }
    return {
        "status": "resolved",
        "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": f"opponent_attack:{move_id}",
        "action_type": "attack",
        "move_id": move_id,
        "identity": move_id,
        "opponent_actor": deepcopy(actor),
        "target_owner": deepcopy(target),
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "metadata_authority": {
            "status": "resolved",
            "move_id": move_id,
            "metadata": metadata,
        },
        "usability": {"status": "known_usable"},
        "selectability": "selectable",
    }


def _status_application(d0, action, own, *, outcome=None):
    move_id = action["move_id"]
    base = {
        "status": "resolved",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "actor": deepcopy(d0["active_owners"]["opponent"]),
        "target": deepcopy(d0["active_owners"]["self"]),
        "action_id": action["action_id"],
        "move_id": move_id,
    }
    if move_id == "taunt":
        return {
            **base,
            "schema_version": "detached-taunt-action-restriction-v1",
            "outcome": outcome or "applied",
            "reason": "taunt_applied",
            "remaining_target_turns": 3,
        }
    if move_id == "encore":
        return {
            **base,
            "schema_version": "detached-encore-action-restriction-v1",
            "outcome": outcome or "applicable",
            "reason": "encore_applicable",
            "locked_move_id": own["identity"],
            "locked_move_metadata": deepcopy(own["move_metadata_authority"]["metadata"]),
            "last_used_execution_id": "used:bullet-seed",
            "remaining_target_turns": 3,
        }
    return {
        **base,
        "schema_version": "detached-disable-action-restriction-v1",
        "outcome": outcome or "applicable",
        "reason": "disable_applicable",
        "disabled_move_id": own["identity"],
        "last_used_execution_id": "used:bullet-seed",
        "remaining_target_turns": 4,
    }


def test_taunt_first_does_not_restrict_later_damaging_graph():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    own = _protectable_graph(d0, power=500)
    taunt = _opponent_status_special(d0, "taunt")
    app = _status_application(d0, taunt, own)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=taunt,
        action_order_authority=_order(d0, own, taunt, "opponent_first"),
        taunt_application_authorities={taunt["action_id"]: app},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    outcomes = pair["order_graphs"][0]["terminal_transitions"][0]["second_action"]["outcomes"]
    assert any(
        row.get("second_action_graph", {}).get("move_id") == "bullet-seed"
        for row in outcomes if row["state"] == "executed"
    )
    missing = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=taunt,
        action_order_authority=_order(d0, own, taunt, "opponent_first"),
    )
    assert missing["status"] == "incomplete"


def test_encore_first_forces_exact_graph_execution_without_flattening():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    own = _protectable_graph(d0, power=500)
    encore = _opponent_status_special(d0, "encore")
    app = _status_application(d0, encore, own)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=encore,
        action_order_authority=_order(d0, own, encore, "opponent_first"),
        encore_application_authorities={encore["action_id"]: app},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    outcome = pair["order_graphs"][0]["terminal_transitions"][0]["second_action"]["outcomes"][0]
    assert outcome["state"] == "executed"
    assert outcome["second_action_graph"]["move_id"] == "bullet-seed"
    assert outcome["forced_execution_action"]["execution_move_id"] == "bullet-seed"


def test_disable_first_restricts_pending_graph_without_executing_native_graph():
    _state, snapshot, d0, _own, response_set, _orders = _inputs()
    own = _protectable_graph(d0, power=500)
    disable = _opponent_status_special(d0, "disable")
    app = _status_application(d0, disable, own)
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=disable,
        action_order_authority=_order(d0, own, disable, "opponent_first"),
        disable_application_authorities={disable["action_id"]: app},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    outcome = pair["order_graphs"][0]["terminal_transitions"][0]["second_action"]["outcomes"][0]
    assert "second_action_graph" not in outcome
    leaf = outcome["second_action_terminal_leaves"][0]
    assert leaf["consequences"]["execution_failure"] == "disable_action_restriction"


def test_graph_first_completes_before_later_status_special_application():
    for move_id, field in (
        ("taunt", "taunt_application_authorities"),
        ("encore", "encore_application_authorities"),
        ("disable", "disable_application_authorities"),
    ):
        _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=80)
        own = _protectable_graph(d0, power=1)
        special = _opponent_status_special(d0, move_id)
        app = _status_application(
            d0,
            special,
            own,
            outcome="failed" if move_id == "encore" else "canonical_failure" if move_id == "disable" else "applied",
        )
        pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
            strategy_d0=d0,
            runtime_snapshot=snapshot,
            own_action=own,
            opponent_action=special,
            action_order_authority=_order(d0, own, special, "own_first"),
            **{field: {special["action_id"]: app}},
        )
        assert pair["status"] == "evaluable", (move_id, pair.get("reason"))
        assert pair["order_graphs"][0]["first_action_graph"]["move_id"] == "bullet-seed"
        second = [
            outcome
            for transition in pair["order_graphs"][0]["terminal_transitions"]
            for outcome in transition["second_action"].get("outcomes", ())
            if outcome["state"] == "executed"
        ]
        assert second
        assert all(
            outcome["second_action_terminal_leaves"][0]["consequences"].get(f"{move_id}_application") is not None
            for outcome in second
        )


def _opponent_pivot(d0, move_id="u-turn"):
    actor, target = d0["active_owners"]["opponent"], d0["active_owners"]["self"]
    metadata = {
        "move_id": move_id,
        "category": "physical" if move_id != "volt-switch" else "special",
        "power": 70,
        "type": "bug" if move_id == "u-turn" else "electric" if move_id == "volt-switch" else "water",
        "accuracy": 100,
        "priority": 0,
        "target": "selected-pokemon",
        "contact": move_id == "u-turn",
        "protection_bypass": False,
    }
    return {
        "status": "resolved",
        "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": f"opponent_attack:{move_id}",
        "action_type": "attack",
        "move_id": move_id,
        "identity": move_id,
        "opponent_actor": deepcopy(actor),
        "target_owner": deepcopy(target),
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "metadata_authority": {
            "status": "resolved",
            "move_id": move_id,
            "metadata": metadata,
        },
        "usability": {"status": "known_usable"},
        "selectability": "selectable",
    }


def _pivot_snapshot(*, bench_count):
    state, snapshot, d0, _own, response_set, _orders = _inputs(own_hp=100, opponent_hp=100)
    active = state["opponent_side"]["pokemon"][0]
    state["switch_hazard_context"] = {
        "schema_version": "switch-hazard-context-v2",
        "session_id": state["session_id"],
        "affected_side": "opponent",
        "stealth_rock": "absent",
        "spikes_layers": 0,
        "toxic_spikes_layers": 0,
        "sticky_web": "absent",
    }
    for slot in range(1, bench_count + 1):
        state["opponent_side"]["pokemon"][slot] = {
            **deepcopy(active),
            "pokemon_id": f"opponent-bench-{slot}",
            "current_hp": 100,
            "max_hp": 100,
            "fainted": False,
        }
        owner = {
            "session_id": state["session_id"],
            "side": "opponent",
            "slot_index": slot,
            "pokemon_id": f"opponent-bench-{slot}",
        }
        state["substitute_state_context"] = update_substitute_state_context(
            context=state.get("substitute_state_context"),
            session_id=state["session_id"],
            owner=owner,
            state="known_inactive",
            substitute_hp=None,
            provenance="runtime_observed_substitute_state_v1",
        )
    snapshot = {
        **snapshot,
        "state": state,
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner={
            "session_id": state["session_id"],
            "side": "self",
            "slot_index": 0,
            "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"],
        },
    )
    return state, snapshot, d0


def test_opponent_pivot_first_retargets_pending_graph_to_exact_incoming_active():
    _state, snapshot, d0 = _pivot_snapshot(bench_count=1)
    own = _protectable_graph(d0, power=1)
    pivot = _opponent_pivot(d0, "u-turn")
    replacement = freeze_runtime_d0_pivot_replacement_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        pivot_actor=d0["active_owners"]["opponent"],
        pivot_action=pivot,
        move_metadata=pivot["metadata_authority"]["metadata"],
    )
    assert replacement["status"] == "resolved"
    incoming = replacement["owner"]
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=pivot,
        action_order_authority=_order(d0, own, pivot, "opponent_first"),
        pivot_replacement_authorities={pivot["action_id"]: replacement},
        pivot_entry_authorities={pivot["action_id"]: replacement["entry_authority"]},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    transitions = pair["order_graphs"][0]["terminal_transitions"]
    pivoted = [row for row in transitions if isinstance(row.get("pivot_transition"), dict)]
    assert pivoted
    for row in pivoted:
        assert row["pivot_transition"]["resulting_active_owner"]["pokemon_id"] == incoming["pokemon_id"]
        graph = row["second_action"]["outcomes"][0]["second_action_graph"]
        assert graph["target"]["pokemon_id"] == incoming["pokemon_id"]


def test_graph_first_then_opponent_pivot_executes_after_completed_graph():
    _state, snapshot, d0 = _pivot_snapshot(bench_count=1)
    own = _protectable_graph(d0, power=1)
    pivot = _opponent_pivot(d0, "u-turn")
    replacement = freeze_runtime_d0_pivot_replacement_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        pivot_actor=d0["active_owners"]["opponent"],
        pivot_action=pivot,
        move_metadata=pivot["metadata_authority"]["metadata"],
    )
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=pivot,
        action_order_authority=_order(d0, own, pivot, "own_first"),
        pivot_replacement_authorities={pivot["action_id"]: replacement},
        pivot_entry_authorities={pivot["action_id"]: replacement["entry_authority"]},
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["order_graphs"][0]["first_action_graph"]["move_id"] == "bullet-seed"
    executed = [
        outcome
        for transition in pair["order_graphs"][0]["terminal_transitions"]
        for outcome in transition["second_action"].get("outcomes", ())
        if outcome["state"] == "executed"
    ]
    assert executed
    assert any(outcome.get("second_action_pivot_transitions") for outcome in executed)


def test_opponent_pivot_zero_one_multiple_replacement_policy_is_preserved():
    results = {}
    for count in (0, 1, 2):
        _state, snapshot, d0 = _pivot_snapshot(bench_count=count)
        pivot = _opponent_pivot(d0, "u-turn")
        results[count] = freeze_runtime_d0_pivot_replacement_authority(
            strategy_d0=d0,
            runtime_snapshot=snapshot,
            pivot_actor=d0["active_owners"]["opponent"],
            pivot_action=pivot,
            move_metadata=pivot["metadata_authority"]["metadata"],
        )
    assert results[0]["status"] == "known_none"
    assert results[0]["reason"] == "pivot_no_exact_legal_replacement"
    assert results[1]["status"] == "resolved"
    assert results[2]["status"] == "incomplete"
    assert results[2]["reason"] == "opponent_pivot_replacement_choice_policy_required"

