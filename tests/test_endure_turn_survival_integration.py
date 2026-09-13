from copy import deepcopy

from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_endure_turn_survival_authority import (
    apply_endure_turn_survival_to_hit,
    freeze_runtime_d0_endure_turn_survival_authority,
    materialize_detached_endure_turn_context,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import materialize_detached_fixed_two_hit_per_hit_predictive_leaves
from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority
from tests.test_runtime_d0_native_damage_context import _state
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _inputs
from tests.test_detached_variable_two_to_five_hit_per_hit_predictive_materialization import _inputs as _graph_inputs
from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import _variable_action_graph
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from tests.test_detached_immediate_protection_response_pair import _inputs as _pair_inputs, _own_action, _order


def _owner(state, side="self"):
    row = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": row["pokemon_id"]}


def _record(state, owner, move_id="tackle"):
    plan = {"session_id": state["session_id"], "status":"planned", "conflicts":[], "replay_policy_version":"v1", "ordered_steps":[{"observation_id":"endure-history", "observation_sequence":1, "planned_effect":"record_executed_move", "trust":"user_confirmed_observation", **owner, "turn_number":1, "move_id":move_id, "source_action_id":f"attack:{move_id}"}]}
    return project_atomic_transition(state, plan, state["session_id"])["projected_state"]


def _endure_inputs(side="self"):
    state = _state(f"endure-{side}")
    owner = _owner(state, side)
    state = _record(state, owner)
    snapshot = {"status":"runtime_snapshot_ready", "session_id":state["session_id"], "state":deepcopy(state), "state_fingerprint":state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    action = {"action_id":f"attack:{side}:endure", "action_type":"attack", "identity":"endure", "metadata_authority":{"status":"resolved", "metadata":{"move_id":"endure", "category":"status", "target":"user", "accuracy":None}}}
    return snapshot, d0, owner, action


def test_endure_authority_requires_exact_nonconsecutive_history_and_is_side_neutral():
    for side in ("self", "opponent"):
        snapshot, d0, owner, action = _endure_inputs(side)
        before = deepcopy(snapshot)
        authority = freeze_runtime_d0_endure_turn_survival_authority(strategy_d0=d0, runtime_snapshot=snapshot, endure_user=owner, endure_action=action)
        assert authority["status"] == "resolved", authority
        context = materialize_detached_endure_turn_context(authority=authority)
        assert context["status"] == "resolved"
        assert context["endure_user"] == owner
        assert snapshot == before
    state = _state("endure-no-history")
    owner = _owner(state)
    snapshot = {"status":"runtime_snapshot_ready", "session_id":state["session_id"], "state":deepcopy(state), "state_fingerprint":state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    missing = freeze_runtime_d0_endure_turn_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, endure_user=owner,
        endure_action={"action_id":"attack:self:endure", "action_type":"attack", "identity":"endure", "metadata_authority":{"status":"resolved", "metadata":{"move_id":"endure", "category":"status", "target":"user", "accuracy":None}}},
    )
    assert missing["status"] == "incomplete"


def test_endure_clamps_only_lethal_terminal_hp_and_preserves_raw_damage():
    snapshot, d0, owner, action = _endure_inputs()
    authority = freeze_runtime_d0_endure_turn_survival_authority(strategy_d0=d0, runtime_snapshot=snapshot, endure_user=owner, endure_action=action)
    context = materialize_detached_endure_turn_context(authority=authority)
    lethal = apply_endure_turn_survival_to_hit(context=context, target=owner, hp_before=37, raw_damage=80, actual_damage=37, source_hit={"move_id":"tackle"})
    assert lethal["post_hp"] == 1 and lethal["actual_damage"] == 36
    assert lethal["survival"]["raw_damage"] == 80
    nonlethal = apply_endure_turn_survival_to_hit(context=context, target=owner, hp_before=37, raw_damage=12, actual_damage=12, source_hit={"move_id":"tackle"})
    assert nonlethal["post_hp"] == 25 and nonlethal["survival"]["outcome"] == "not_triggered"


def test_endure_context_persists_across_both_fixed_hits_without_item_consumption():
    state, snapshot, d0, attack, execution, attacker, target = _inputs(power=500, target_hp=100)
    endure_action = {"action_id":"attack:opponent:endure", "action_type":"attack", "identity":"endure", "metadata_authority":{"status":"resolved", "metadata":{"move_id":"endure", "category":"status", "target":"user", "accuracy":None}}}
    # Seed exact non-protection history for the target-side Endure user.
    seeded = _record(deepcopy(snapshot["state"]), target)
    seeded_snapshot = {"status":"runtime_snapshot_ready", "session_id":seeded["session_id"], "state":seeded, "state_fingerprint":state_fingerprint(seeded)}
    seeded_d0 = freeze_runtime_strategy_d0(runtime_snapshot=seeded_snapshot, decision_owner=attacker)
    rebound_action = {**attack, "move_metadata_authority": {**attack["move_metadata_authority"], "session_id": seeded_d0["session_id"], "source_runtime_fingerprint": seeded_d0["source_runtime_fingerprint"], "source_branch_fingerprint": seeded_d0["strategy_preview_fingerprint"], "decision_owner": attacker, "active_attacker": attacker}}
    rebound_execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(strategy_d0=seeded_d0, runtime_snapshot=seeded_snapshot, action=rebound_action)
    authority = freeze_runtime_d0_endure_turn_survival_authority(strategy_d0=seeded_d0, runtime_snapshot=seeded_snapshot, endure_user=target, endure_action=endure_action)
    context = materialize_detached_endure_turn_context(authority=authority)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(strategy_d0=seeded_d0, runtime_snapshot=seeded_snapshot, action=rebound_action, execution_authority=rebound_execution, endure_turn_context=context)
    assert result["status"] == "evaluable", result
    assert result["terminal_probability_mass"] == {"numerator":1,"denominator":1}
    assert all(len(leaf["ordered_hits"]) == 2 for leaf in result["terminal_leaves"])
    assert all(leaf["ordered_hits"][0]["post_hp"] == 1 and leaf["ordered_hits"][1]["post_hp"] == 1 for leaf in result["terminal_leaves"])
    assert all(leaf["consequences"]["target_ko"] is False for leaf in result["terminal_leaves"])


def test_endure_context_preserves_native_graph_and_keeps_target_alive_per_hit():
    state, snapshot, d0, action, _execution, attacker, target = _graph_inputs(move_id="bullet-seed", power=500)
    seeded = _record(deepcopy(snapshot["state"]), target)
    seeded_snapshot = {"status":"runtime_snapshot_ready", "session_id":seeded["session_id"], "state":seeded, "state_fingerprint":state_fingerprint(seeded)}
    seeded_d0 = freeze_runtime_strategy_d0(runtime_snapshot=seeded_snapshot, decision_owner=attacker)
    rebound = {**action, "move_metadata_authority": {**action["move_metadata_authority"], "session_id": seeded_d0["session_id"], "source_runtime_fingerprint": seeded_d0["source_runtime_fingerprint"], "source_branch_fingerprint": seeded_d0["strategy_preview_fingerprint"], "decision_owner": attacker, "active_attacker": attacker}}
    endure = {"action_id":"opponent_attack:endure", "action_type":"attack", "identity":"endure", "metadata_authority":{"status":"resolved", "metadata":{"move_id":"endure", "category":"status", "target":"user", "accuracy":None}}}
    authority = freeze_runtime_d0_endure_turn_survival_authority(strategy_d0=seeded_d0, runtime_snapshot=seeded_snapshot, endure_user=target, endure_action=endure)
    context = materialize_detached_endure_turn_context(authority=authority)
    graph = _variable_action_graph(strategy_d0=seeded_d0, runtime_snapshot=seeded_snapshot, actor=attacker, target=target, metadata_authority=rebound["move_metadata_authority"], sturdy_survival_authority=None, focus_sash_survival_authority=None, endure_turn_context=context)
    assert graph["status"] == "evaluable", graph
    assert graph["terminal_probability_mass"] == {"numerator":1,"denominator":1}
    assert all(edge.get("terminal_consequences", {}).get("target_final_hp", 1) != 0 for edge in graph["terminal_leaf_edges"] if edge.get("terminal") is True)
    opponent_endure = {
        "status":"resolved", "schema_version":"runtime-d0-opponent-known-move-action-authority-v1",
        "action_id":"opponent_attack:endure", "action_type":"attack", "move_id":"endure",
        "opponent_actor":target, "target_owner":attacker,
        "session_id":seeded_d0["session_id"], "source_runtime_fingerprint":seeded_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint":seeded_d0["strategy_preview_fingerprint"], "decision_owner":seeded_d0["decision_owner"],
        "metadata_authority":{"status":"resolved", "move_id":"endure", "metadata":{"move_id":"endure", "category":"status", "target":"user", "accuracy":None, "priority":4}},
        "usability":{"status":"known_usable"}, "selectability":"selectable",
    }
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=seeded_d0, runtime_snapshot=seeded_snapshot, own_action=rebound, opponent_action=opponent_endure,
        action_order_authority=_order(seeded_d0, rebound, opponent_endure, "opponent_first"),
        endure_turn_survival_authority=authority,
    )
    assert pair["status"] == "evaluable", pair
    assert pair["terminal_probability_mass"] == {"numerator":1,"denominator":1}
    assert pair["order_graphs"][0]["second_action_graph"]["terminal_probability_mass"] == {"numerator":1,"denominator":1}


def test_endure_first_keeps_the_attack_real_but_clamps_a_lethal_ordinary_leaf():
    state, _snapshot0, d0_0, *_ = _pair_inputs()
    endure_user = d0_0["active_owners"]["opponent"]
    state = _record(state, endure_user)
    # Endure does not require full HP.  One HP makes the normal attack's raw
    # lethal branch and the resulting clamp unambiguous.
    state["opponent_side"]["pokemon"][0]["current_hp"] = 1
    snapshot = {"status":"runtime_snapshot_ready", "session_id":state["session_id"], "state":state, "state_fingerprint":state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0_0["active_owners"]["self"])
    attack = _own_action(d0, "tackle")
    endure = {
        "status":"resolved", "schema_version":"runtime-d0-opponent-known-move-action-authority-v1",
        "action_id":"opponent_attack:endure", "action_type":"attack", "move_id":"endure",
        "opponent_actor":d0["active_owners"]["opponent"], "target_owner":d0["active_owners"]["self"],
        "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"],
        "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"],
        "metadata_authority":{"status":"resolved", "move_id":"endure", "metadata":{"move_id":"endure", "category":"status", "target":"user", "accuracy":None, "priority":4}},
        "usability":{"status":"known_usable"}, "selectability":"selectable",
    }
    authority = freeze_runtime_d0_endure_turn_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, endure_user=d0["active_owners"]["opponent"], endure_action=endure,
    )
    before = deepcopy(snapshot)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=attack, opponent_action=endure,
        action_order_authority=_order(d0, attack, endure, "opponent_first"),
        endure_turn_survival_authority=authority,
    )
    assert pair["status"] == "evaluable", pair
    assert pair["terminal_probability_mass"] == {"numerator":1, "denominator":1}
    leaf = pair["terminal_branches"][0]["second_action"]["leaf"]
    assert leaf["consequences"]["target_final_hp"] == 1
    assert leaf["consequences"]["target_ko"] is False
    assert leaf["consequences"]["post_hit"]["raw_damage"] > 0
    assert leaf["consequences"]["post_hit"]["endure_turn_survival"]["outcome"] == "applied"
    assert leaf["consequences"]["focus_sash_survival"]["outcome"] == "not_applicable"
    assert snapshot == before


def test_selected_endure_setup_owns_no_pending_attack_probability_or_execution():
    snapshot, d0, owner, action = _endure_inputs("self")
    authority = freeze_runtime_d0_endure_turn_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, endure_user=owner, endure_action=action,
    )
    before = deepcopy(snapshot)
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=owner,
        target=d0["active_owners"]["opponent"],
        move_metadata=action["metadata_authority"]["metadata"],
        family_authorities={"endure_turn_survival_authority":authority},
    )
    assert result["status"] == "resolved", result
    assert result["execution_family"] == "endure_turn_survival"
    assert result["paths"][0]["probability"] == {"numerator":1, "denominator":1}
    assert result["paths"][0]["pending_action_executed"] is False
    assert result["paths"][0]["endure_turn_context"]["endure_user"] == owner
    assert snapshot == before
