from copy import deepcopy

from advisor.critical_hit_capabilities import resolve_critical_hit_capabilities
from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata
from llm.advisor_runtime_d0_sucker_punch_execution_applicability_authority import (
    freeze_runtime_d0_sucker_punch_execution_applicability_authority,
)
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_immediate_attack_vs_opponent_switch_action_pair import materialize_immediate_attack_vs_opponent_switch_action_pair
from llm.advisor_immediate_move_vs_move_action_pair import _materialize_protection_response_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger


def _inputs(*, category="physical", order="own_first", action_type="attack"):
    own = {"session_id": "sucker", "side": "self", "slot_index": 0, "pokemon_id": "self"}
    foe = {"session_id": "sucker", "side": "opponent", "slot_index": 0, "pokemon_id": "foe"}
    d0 = {"status": "resolved", "session_id": "sucker", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": own, "active_owners": {"self": own, "opponent": foe}}
    bindings = {"session_id": "sucker", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own}
    own_meta = {"status": "resolved", **bindings, "metadata": {"move_id": "sucker-punch", "category": "physical", "power": 70, "type": "dark", "accuracy": 100, "priority": 1}}
    move_id = "tackle" if category == "physical" else "water-gun" if category == "special" else "protect"
    target = {"action_id": f"opponent:{move_id}", "action_type": action_type, "move_id": move_id}
    target_meta = {"status": "resolved", **bindings, "metadata": {"move_id": move_id, "category": category, "power": 40 if category != "status" else 0, "type": "normal", "accuracy": 100, "priority": 0}}
    order_auth = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": order, **bindings, "own_action_id": "attack:sucker-punch", "opponent_action_id": target["action_id"], "own_actor": own, "opponent_actor": foe}
    return d0, {"action_id": "attack:sucker-punch", "action_type": "attack", "identity": "sucker-punch"}, own_meta, target, target_meta, order_auth, order


def _freeze(**changes):
    d0, own, own_meta, target, target_meta, order_auth, order = _inputs(**changes)
    return freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=target, target_move_metadata_authority=target_meta, action_order_authority=order_auth, order=order)


def test_canonical_sucker_punch_metadata_and_contact_are_admitted():
    result = _freeze()
    assert result["status"] == "applies"
    assert result["canonical_move_metadata"] == {"move_id": "sucker-punch", "category": "physical", "power": 70, "type": "dark", "accuracy": 100, "priority": 1}
    contact = canonical_move_contact_metadata("sucker-punch")
    assert contact["status"] == "resolved" and contact["move_id"] == "sucker-punch" and contact["contact_state"] == "contact"


def test_physical_and_special_selected_target_attacks_apply_before_they_act():
    assert _freeze(category="physical")["status"] == "applies"
    assert _freeze(category="special")["status"] == "applies"


def test_status_switch_and_already_acted_are_deterministic_conditional_failures():
    status = _freeze(category="status", action_type="status")
    assert status["status"] == "not_applicable" and status["reason"] == "sucker_punch_target_not_readying_attack"
    d0, own, own_meta, _target, _target_meta, order_auth, order = _inputs()
    switch = {"action_id": "opponent:switch", "action_type": "manual_switch"}
    order_auth = deepcopy(order_auth); order_auth["opponent_action_id"] = switch["action_id"]
    switched = freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=switch, target_move_metadata_authority=None, action_order_authority=order_auth, order=order)
    assert switched["status"] == "not_applicable" and switched["reason"] == "sucker_punch_target_not_readying_attack"
    late = _freeze(order="opponent_first")
    assert late["status"] == "not_applicable" and late["reason"] == "sucker_punch_target_already_acted" and late["target_already_acted"] is True


def test_forged_target_action_category_and_order_are_rejected():
    d0, own, own_meta, target, target_meta, order_auth, order = _inputs()
    forged_target = deepcopy(target); forged_target["action_id"] = "opponent:forged"
    assert freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=forged_target, target_move_metadata_authority=target_meta, action_order_authority=order_auth, order=order)["status"] == "rejected"
    forged_category = deepcopy(target); forged_category["action_type"] = "status"
    assert freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=forged_category, target_move_metadata_authority=target_meta, action_order_authority=order_auth, order=order)["status"] == "rejected"
    forged_order = deepcopy(order_auth); forged_order["own_action_id"] = "attack:forged"
    assert freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=target, target_move_metadata_authority=target_meta, action_order_authority=forged_order, order=order)["status"] == "rejected"
    assert freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=target, target_move_metadata_authority=target_meta, action_order_authority=order_auth, order="opponent_first")["status"] == "rejected"


def test_existing_materialized_equal_speed_or_quick_claw_branch_controls_already_acted():
    d0, own, own_meta, target, target_meta, order_auth, _order = _inputs(order="own_first")
    branch = {"order": "opponent_first", "order_branch_id": "quick-claw:opponent-first", **{key: order_auth[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")}}
    result = freeze_runtime_d0_sucker_punch_execution_applicability_authority(strategy_d0=d0, own_action=own, own_move_metadata_authority=own_meta, target_action=target, target_move_metadata_authority=target_meta, action_order_authority=order_auth, order="opponent_first", action_order_branch=branch)
    assert result["status"] == "not_applicable" and result["reason"] == "sucker_punch_target_already_acted"


def test_selected_attack_succeeds_before_later_flinch_cancellation(monkeypatch):
    d0, own_action, own_meta, target, target_meta, order, _ = _inputs()
    own, foe = d0["decision_owner"], d0["active_owners"]["opponent"]
    d0["strategy_state"] = {"active": {"self": {"current_hp": 100}, "opponent": {"current_hp": 100}}}
    target = {"status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1", "selectability": "selectable", "usability": {"status": "known_usable"}, "opponent_actor": foe, "target_owner": own, **{key: d0[{"session_id": "session_id", "source_runtime_fingerprint": "source_runtime_fingerprint", "source_branch_fingerprint": "strategy_preview_fingerprint", "decision_owner": "decision_owner"}[key]] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}, "action_id": target["action_id"], "action_type": "attack", "move_id": "tackle", "metadata_authority": target_meta}
    order = deepcopy(order); order["order"] = "own_first"
    first = {"leaf_id": "sucker:hit", "candidate_id": "attack:sucker-punch", "action_type": "attack", "branch_path": ("hit",), "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit", "critical_state": "non_critical", "damage_roll": {"damage": 10}, "consequences": {"damage": 10, "own_final_hp": 100, "target_final_hp": 90, "target_ko": False, "self_fainted": False, "secondary": None}, "provenance": {"session_id": "sucker", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own, "attacker": own, "target": foe, "move_id": "sucker-punch"}}
    intermediate = {"status": "resolved", "active": {"self": {"hypothetical_fainted": {"value": False}}, "opponent": {"hypothetical_fainted": {"value": False}}}, "second_action_compatibility": {"flinch_cancellation": {"status": "resolved", "affected_owner": foe, "state": "flinched", "provenance": "exact_terminal_leaf_iron_head_flinch_secondary"}}}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.resolve_runtime_d0_selectable_move_metadata_authority", lambda **_: own_meta)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", lambda *, actor, **_: {"status": "evaluable", "terminal_leaves": (first,)})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.materialize_detached_predictive_intermediate_state", lambda **_: intermediate)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot={"state": {}}, own_action=own_action, opponent_action=target, action_order_authority=order)
    assert pair["status"] == "evaluable", pair.get("reason")
    branch = pair["terminal_branches"][0]
    assert branch["first_action_leaf"]["consequences"]["sucker_punch_execution"]["status"] == "applies"
    assert branch["second_action"]["state"] == "cancelled_due_to_flinch"


def test_opponent_switch_is_a_sucker_punch_failure_and_never_hits_the_incoming_target():
    from tests.test_immediate_attack_vs_opponent_switch_action_pair import _inputs as switch_inputs, _state as switch_state
    state = switch_state(); d0, snapshot, action, switch, switch_id = switch_inputs(state)
    action = deepcopy(action)
    action.update(action_id="attack:sucker-punch", identity="sucker-punch")
    action["move_metadata_authority"].update(candidate_id="attack:sucker-punch", move_id="sucker-punch")
    action["move_metadata_authority"]["metadata"] = {"move_id": "sucker-punch", "category": "physical", "power": 70, "type": "dark", "accuracy": 100, "priority": 1}
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, switch_response_authority=switch, selected_switch_response_action_id=switch_id)
    assert pair["status"] == "evaluable", pair.get("reason")
    leaf = pair["terminal_branches"][0]["attack_leaf"]
    assert leaf["consequences"]["damage"] == 0 and leaf["hit_state"] == "not_applicable"
    assert leaf["consequences"]["contact"] == "not_applicable"
    assert pair["sucker_punch_execution_applicability"]["reason"] == "sucker_punch_target_not_readying_attack"


def test_protect_selection_is_sucker_punch_failure_not_protection_block(monkeypatch):
    d0, own_action, own_meta, target, target_meta, order, _ = _inputs()
    own, foe = d0["decision_owner"], d0["active_owners"]["opponent"]
    d0["strategy_state"] = {"active": {"self": {"current_hp": 100}, "opponent": {"current_hp": 100}}}
    target = {"action_id": "opponent:protect", "action_type": "attack", "move_id": "protect"}
    target_meta = {"status": "resolved", "session_id": "sucker", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own, "metadata": {"move_id": "protect", "category": "status", "power": 0, "type": "normal", "accuracy": 100, "priority": 4}}
    order = deepcopy(order); order.update(order="opponent_first", opponent_action_id=target["action_id"])
    base = {"pair_id": "pair:attack:sucker-punch:opponent:protect", "session_id": "sucker", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own, "own_action_id": own_action["action_id"], "opponent_action_id": target["action_id"], "own_actor": own, "opponent_actor": foe}
    protection_leaf = {"leaf_id": "protect:resolved", "candidate_id": "opponent:protect", "action_type": "attack", "branch_path": ("protect",), "probability": {"numerator": 1, "denominator": 1}, "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "own_final_hp": 100, "target_final_hp": 100, "target_ko": False, "self_fainted": False, "secondary": None}, "provenance": {"session_id": "sucker", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own, "attacker": foe, "target": own, "move_id": "protect"}}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._resolved_protection", lambda **_: {"status": "resolved"})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.prevent_supported_direct_damage", lambda **_: {"status": "resolved"})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._protection_leaf", lambda *_, **__: protection_leaf)
    pair = _materialize_protection_response_pair(strategy_d0=d0, runtime_snapshot={"state": {}}, base=base, own_action=own_action, opponent_action=target, own_meta=own_meta, opponent_meta=target_meta, orders=[{"order": "opponent_first", "probability": __import__("fractions").Fraction(1, 1), "source_branch": None}], action_order_authority=order, opponent_protection_success_authority=None, incoming_contact_authority=None, silk_trap_reactive_interaction_authority=None, kings_shield_reactive_interaction_authority=None, obstruct_reactive_interaction_authority=None, spiky_shield_reactive_damage_authority=None, baneful_bunker_reactive_poison_authority=None, burning_bulwark_reactive_burn_authority=None)
    assert pair["status"] == "evaluable", pair.get("reason")
    failure = pair["terminal_branches"][0]["second_action"]["leaf"]
    assert failure["consequences"]["damage"] == 0 and failure["consequences"]["contact"] == "not_applicable"
    assert failure["consequences"]["sucker_punch_execution"]["reason"] == "sucker_punch_target_not_readying_attack"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
