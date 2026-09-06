"""Strict exact normalization for completed immediate action-pair branches."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_variable_two_to_five_hit_graph_shared_pair_ledger import (
    PAIR_SCHEMA as VARIABLE_GRAPH_PAIR_SCHEMA,
    _effect_spore_contact_reactive_status as _validate_effect_spore_contact_reactive_status,
    normalize_variable_two_to_five_hit_graph_pair,
)
from llm.advisor_low_hp_type_offensive_ability import (
    validate_low_hp_type_offensive_ability_applicability,
)
from llm.advisor_guts_status_attack_ability import (
    validate_guts_status_attack_ability_applicability,
)
from llm.advisor_full_hp_defender_ability import (
    validate_full_hp_defender_ability_applicability,
)
from advisor.canonical_recent_damage_retaliation_family import resolve_canonical_recent_damage_retaliation_move


SCHEMA_VERSION = "exact-immediate-action-pair-outcome-ledger-v1"
PAIR_SCHEMAS = {"immediate-move-vs-move-action-pair-v1", "immediate-attack-vs-opponent-switch-action-pair-v1", VARIABLE_GRAPH_PAIR_SCHEMA}
HORIZON = "immediate_action_pair"
_STATUSES = {"incomplete", "unsupported", "rejected"}


def normalize_exact_immediate_action_pair_outcome_ledger(*, pair: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy an evaluable pair without recomputing mechanics."""
    if not isinstance(pair, Mapping): return _result("rejected", "invalid_immediate_action_pair")
    if pair.get("status") != "evaluable":
        return _result(_status(pair), pair.get("reason", "immediate_action_pair_not_evaluable"), _base(pair))
    base = _base(pair)
    if base is None or pair.get("schema_version") not in PAIR_SCHEMAS or pair.get("horizon") != HORIZON:
        return _result("rejected", "immediate_action_pair_binding_or_schema_invalid")
    if pair.get("schema_version") == VARIABLE_GRAPH_PAIR_SCHEMA:
        return normalize_variable_two_to_five_hit_graph_pair(pair=pair, base=base)
    branches = pair.get("terminal_branches")
    if not isinstance(branches, (tuple, list)) or not branches: return _result("rejected", "pair_terminal_branches_missing", base)
    parsed: list[dict[str, Any]] = []
    identities: set[str] = set()
    for branch in branches:
        leaf = _switch_leaf(branch, base) if pair.get("schema_version") == "immediate-attack-vs-opponent-switch-action-pair-v1" else _leaf(branch, base)
        if isinstance(leaf, str): return _result("rejected", leaf, base)
        if leaf["pair_leaf_id"] in identities: return _result("rejected", "duplicate_pair_terminal_leaf_id", base)
        identities.add(leaf["pair_leaf_id"]); parsed.append(leaf)
    mass = sum((_fraction(leaf["probability"]) for leaf in parsed), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "pair_root_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    declared = _fraction(pair.get("terminal_probability_mass"))
    if declared != mass: return _result("rejected", "pair_declared_terminal_mass_mismatch", base, terminal_probability_mass=_fd(mass))
    return {"status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
            "conditional_on": deepcopy(pair.get("conditional_on")),
            "terminal_leaves": tuple(parsed), "terminal_probability_mass": _fd(mass),
            "aggregation": "none_preserve_pair_branch_and_roll_identity",
            "provenance": "strict_detached_immediate_action_pair_outcome_normalization_v1"}


def _base(pair: Mapping[str, Any]) -> dict[str, Any] | None:
    if pair.get("schema_version") == "immediate-attack-vs-opponent-switch-action-pair-v1":
        required = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_switch_response_action_id", "own_actor", "replaced_opponent_actor")
        strings = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "own_action_id", "opponent_switch_response_action_id")
        switch = pair.get("switch_in_authority")
        incoming = switch.get("target_owner") if isinstance(switch, Mapping) else None
        if not all(key in pair for key in required) or not all(isinstance(pair.get(key), str) and pair[key] for key in strings) or not all(isinstance(pair.get(key), Mapping) for key in ("decision_owner", "own_actor", "replaced_opponent_actor")) or not isinstance(incoming, Mapping): return None
        return {**{key: deepcopy(pair[key]) for key in required}, "opponent_action_id": pair["opponent_switch_response_action_id"], "opponent_actor": deepcopy(dict(incoming)), "response_action_type": "manual_switch"}
    required = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")
    strings = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "own_action_id", "opponent_action_id")
    if not all(key in pair for key in required) or not all(isinstance(pair.get(key), str) and pair[key] for key in strings): return None
    if not isinstance(pair.get("decision_owner"), Mapping) or not isinstance(pair.get("own_actor"), Mapping) or not isinstance(pair.get("opponent_actor"), Mapping): return None
    return {key: deepcopy(pair[key]) for key in required}


def _switch_leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or not isinstance(value.get("pair_leaf_id"), str) or value.get("action_order") != "opponent_switch_first": return "invalid_switch_pair_terminal_branch"
    source_base = {key: deepcopy(value) for key, value in base.items() if key not in {"opponent_action_id", "opponent_actor", "response_action_type"}}
    if value.get("provenance") != source_base: return "switch_pair_terminal_branch_provenance_mismatch"
    attack = value.get("attack_leaf")
    probability = _fraction(value.get("probability"))
    if not isinstance(attack, Mapping) or not isinstance(attack.get("leaf_id"), str) or _fraction(attack.get("probability")) <= 0 or probability != _fraction(attack["probability"]): return "switch_pair_attack_leaf_invalid"
    sucker_error = _sucker_punch_leaf(attack, action_order="opponent_switch_first", pair_base=base)
    if sucker_error is not None: return sucker_error
    final = _final(attack, base)
    if isinstance(final, str): return final
    focus_error = _focus_sash_leaf(attack)
    if focus_error is not None: return focus_error
    low_hp_error = _low_hp_type_leaf(attack)
    if low_hp_error is not None: return low_hp_error
    guts_error = _guts_status_attack_leaf(attack)
    if guts_error is not None: return guts_error
    incoming = value.get("incoming_target")
    if incoming != base["opponent_actor"]: return "switch_pair_incoming_target_identity_mismatch"
    return {"pair_leaf_id": value["pair_leaf_id"], "action_order": value["action_order"], "probability": _fd(probability),
            "switch_response": {"action_id": base["opponent_action_id"], "incoming_target": deepcopy(dict(incoming)), "switch_in_state_id": value.get("switch_in_state_id"), "entry_consequence": deepcopy(value.get("entry_consequence"))},
            "attack_action": _action_leaf(attack), "final_consequences": final, "source_pair_branch": deepcopy(dict(value))}


def _leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or not isinstance(value.get("pair_leaf_id"), str) or value.get("action_order") not in {"own_first", "opponent_first"}: return "invalid_pair_terminal_branch"
    if value.get("provenance") != dict(base): return "pair_terminal_branch_provenance_mismatch"
    first, second = value.get("first_action_leaf"), value.get("second_action")
    if not isinstance(first, Mapping) or not isinstance(first.get("leaf_id"), str) or _fraction(first.get("probability")) <= 0: return "first_action_leaf_invalid"
    sucker_error = _sucker_punch_leaf(first, action_order=value["action_order"], pair_base=base)
    if sucker_error is not None: return sucker_error
    heal_error = _direct_heal_leaf(first)
    if heal_error is not None: return heal_error
    drain_error = _drain_leaf(first)
    if drain_error is not None: return drain_error
    recoil_error = _damage_based_recoil_leaf(first)
    if recoil_error is not None: return recoil_error
    fractional_error = _fractional_target_hp_damage_leaf(first)
    if fractional_error is not None: return fractional_error
    knock_off_error = _knock_off_item_removal_leaf(first)
    if knock_off_error is not None: return knock_off_error
    fling_error = _fling_item_throw_leaf(first)
    if fling_error is not None: return fling_error
    transfer_error = _item_transfer_leaf(first)
    if transfer_error is not None: return transfer_error
    swap_error = _atomic_item_swap_leaf(first)
    if swap_error is not None: return swap_error
    endeavor_error = _endeavor_hp_difference_damage_leaf(first)
    if endeavor_error is not None: return endeavor_error
    final_gambit_error = _final_gambit_self_hp_damage_leaf(first)
    if final_gambit_error is not None: return final_gambit_error
    retaliation_error = _recent_damage_retaliation_leaf(first)
    if retaliation_error is not None: return retaliation_error
    power_error = _was_damaged_power_leaf(first)
    if power_error is not None: return power_error
    assurance_error = _target_was_damaged_power_leaf(first)
    if assurance_error is not None: return assurance_error
    payback_error = _target_already_acted_power_leaf(first)
    if payback_error is not None: return payback_error
    stomping_error = _previous_action_failure_power_leaf(first)
    if stomping_error is not None: return stomping_error
    lash_error = _same_turn_stat_drop_power_leaf(first)
    if lash_error is not None: return lash_error
    rage_error = _rage_fist_hit_count_power_leaf(first)
    if rage_error is not None: return rage_error
    respects_error = _last_respects_faint_power_leaf(first)
    if respects_error is not None: return respects_error
    if not isinstance(second, Mapping) or second.get("state") not in {"executed", "cancelled_due_to_faint", "cancelled_due_to_paralysis", "cancelled_due_to_flinch", "executed_protection", "prevented_by_protection"}: return "second_action_branch_invalid"
    conditional = _fraction(second.get("conditional_probability"))
    if conditional <= 0: return "second_action_probability_invalid"
    order_probability = _order_probability(value)
    if isinstance(order_probability, str): return order_probability
    execution_probability = _execution_probability(second)
    if isinstance(execution_probability, str): return execution_probability
    second_leaf = second.get("leaf")
    if second["state"] == "executed":
        if not isinstance(second_leaf, Mapping) or not isinstance(second_leaf.get("leaf_id"), str) or _fraction(second_leaf.get("probability")) * execution_probability != conditional: return "executed_second_action_leaf_invalid"
        encore_error = _encore_forced_execution_leaf(first, second, second_leaf, base, value["action_order"])
        if encore_error is not None: return encore_error
        pivot_error = _pivot_second_action_target_binding(value, base, first, second_leaf)
        if pivot_error is not None: return pivot_error
        focus_error = _focus_sash_leaf(second_leaf)
        if focus_error is not None: return focus_error
        low_hp_error = _low_hp_type_leaf(second_leaf)
        if low_hp_error is not None: return low_hp_error
        guts_error = _guts_status_attack_leaf(second_leaf)
        if guts_error is not None: return guts_error
    elif second["state"] == "cancelled_due_to_faint":
        if second_leaf is not None or conditional != Fraction(1, 1) or execution_probability != Fraction(1, 1) or second.get("reason") != "second_action_cancelled_due_to_faint": return "cancelled_second_action_branch_invalid"
    elif second["state"] in {"executed_protection", "prevented_by_protection"}:
        if second_leaf is not None or conditional != Fraction(1, 1) or execution_probability != Fraction(1, 1) or second.get("reason") != second["state"]: return "protection_second_action_branch_invalid"
    elif second["state"] == "cancelled_due_to_paralysis":
        if second_leaf is not None or conditional != Fraction(1, 4) or execution_probability != Fraction(1, 4) or second.get("reason") != "second_action_cancelled_due_to_paralysis": return "cancelled_second_action_branch_invalid"
    elif second_leaf is not None or conditional != Fraction(1, 1) or execution_probability != Fraction(1, 1) or second.get("reason") != "second_action_cancelled_due_to_flinch": return "cancelled_second_action_branch_invalid"
    elif _flinch_cancellation_binding(first, second) is not None: return _flinch_cancellation_binding(first, second)
    probability = _fraction(value.get("probability"))
    if probability != order_probability * _fraction(first["probability"]) * conditional: return "pair_leaf_probability_composition_invalid"
    focus_error = _focus_sash_leaf(first)
    if focus_error is not None: return focus_error
    low_hp_error = _low_hp_type_leaf(first)
    if low_hp_error is not None: return low_hp_error
    guts_error = _guts_status_attack_leaf(first)
    if guts_error is not None: return guts_error
    first_status_error = _contact_reactive_status_leaf(first)
    if first_status_error is not None: return first_status_error
    final_source = second_leaf if isinstance(second_leaf, Mapping) else first
    disable_error = _disable_restriction_leaf(first, second_leaf, base, value["action_order"])
    if disable_error is not None: return disable_error
    if isinstance(second_leaf, Mapping):
        sucker_error = _sucker_punch_leaf(second_leaf, action_order=value["action_order"], pair_base=base)
        if sucker_error is not None: return sucker_error
        heal_error = _direct_heal_leaf(second_leaf)
        if heal_error is not None: return heal_error
        drain_error = _drain_leaf(second_leaf)
        if drain_error is not None: return drain_error
        recoil_error = _damage_based_recoil_leaf(second_leaf)
        if recoil_error is not None: return recoil_error
        fractional_error = _fractional_target_hp_damage_leaf(second_leaf)
        if fractional_error is not None: return fractional_error
        knock_off_error = _knock_off_item_removal_leaf(second_leaf)
        if knock_off_error is not None: return knock_off_error
        fling_error = _fling_item_throw_leaf(second_leaf)
        if fling_error is not None: return fling_error
        transfer_error = _item_transfer_leaf(second_leaf)
        if transfer_error is not None: return transfer_error
        swap_error = _atomic_item_swap_leaf(second_leaf)
        if swap_error is not None: return swap_error
        endeavor_error = _endeavor_hp_difference_damage_leaf(second_leaf)
        if endeavor_error is not None: return endeavor_error
        final_gambit_error = _final_gambit_self_hp_damage_leaf(second_leaf)
        if final_gambit_error is not None: return final_gambit_error
        retaliation_error = _recent_damage_retaliation_leaf(second_leaf)
        if retaliation_error is not None: return retaliation_error
        power_error = _was_damaged_power_leaf(second_leaf)
        if power_error is not None: return power_error
        assurance_error = _target_was_damaged_power_leaf(second_leaf)
        if assurance_error is not None: return assurance_error
        payback_error = _target_already_acted_power_leaf(second_leaf)
        if payback_error is not None: return payback_error
        stomping_error = _previous_action_failure_power_leaf(second_leaf)
        if stomping_error is not None: return stomping_error
        lash_error = _same_turn_stat_drop_power_leaf(second_leaf)
        if lash_error is not None: return lash_error
        rage_error = _rage_fist_hit_count_power_leaf(second_leaf)
        if rage_error is not None: return rage_error
        respects_error = _last_respects_faint_power_leaf(second_leaf)
        if respects_error is not None: return respects_error
        second_status_error = _contact_reactive_status_leaf(second_leaf)
        if second_status_error is not None: return second_status_error
        second_low_hp_error = _low_hp_type_leaf(second_leaf)
        if second_low_hp_error is not None: return second_low_hp_error
        second_guts_error = _guts_status_attack_leaf(second_leaf)
        if second_guts_error is not None: return second_guts_error
    final = _final(final_source, base)
    if isinstance(final, str): return final
    return {"pair_leaf_id": value["pair_leaf_id"], "action_order": value["action_order"],
            **({"action_order_branch": deepcopy(dict(value["action_order_branch"])), "action_order_conditional_probability": _fd(order_probability)} if "action_order_branch" in value else {}),
            "probability": _fd(probability), "first_action": _action_leaf(first),
            "second_action": {"state": second["state"], "actor": deepcopy(second.get("actor")), "conditional_probability": _fd(conditional), **({"execution_branch": deepcopy(dict(second["execution_branch"])), "execution_conditional_probability": _fd(execution_probability)} if "execution_branch" in second else {}), **({"leaf": _action_leaf(second_leaf)} if isinstance(second_leaf, Mapping) else {"reason": second["reason"]})},
            "intermediate_state_id": value.get("intermediate_state_id"), "final_consequences": final,
            "source_pair_branch": deepcopy(dict(value))}


def _action_leaf(leaf: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "leaf_id": leaf["leaf_id"], "branch_path": deepcopy(leaf.get("branch_path")),
        "probability": deepcopy(leaf.get("probability")), "hit_state": leaf.get("hit_state"),
        "critical_state": leaf.get("critical_state"), "damage_roll": deepcopy(leaf.get("damage_roll")),
        **({"ordered_hits": deepcopy(leaf["ordered_hits"])} if "ordered_hits" in leaf else {}),
        "consequences": deepcopy(leaf.get("consequences")), "provenance": deepcopy(leaf.get("provenance")),
    }

def _final_gambit_self_hp_damage_leaf(leaf: Mapping[str, Any]) -> str | None:
 p,c=leaf.get("provenance"),leaf.get("consequences"); move=p.get("move_id") if isinstance(p,Mapping) else None; payload=c.get("final_gambit_self_hp_damage") if isinstance(c,Mapping) else None
 if move!="final-gambit":return "unexpected_final_gambit_payload" if payload is not None else None
 a=p.get("execution_authority") if isinstance(p,Mapping) else None
 if not isinstance(payload,Mapping) or not isinstance(a,Mapping) or a.get("special_damage_family")!="self_current_hp_damage" or payload.get("family")!=a.get("special_damage_rule_authority"):return "final_gambit_authority_binding_mismatch"
 hp,target=payload.get("attacker_execution_hp"),payload.get("target_execution_hp")
 if not all(isinstance(v,int) and not isinstance(v,bool) and v>=1 for v in (hp,target)) or hp!=a.get("execution_attacker_hp") or target!=a.get("execution_target_hp"):return "final_gambit_execution_hp_binding_mismatch"
 success=payload.get("outcome")=="success"; raw=hp if success else 0; actual=min(raw,target) if success else 0; post=target-actual
 if payload.get("raw_damage")!=raw or payload.get("actual_target_hp_loss")!=actual or payload.get("target_post_hp")!=post or c.get("damage")!=raw or c.get("target_final_hp")!=post or payload.get("attacker_post_hp")!=(0 if success else hp) or payload.get("attacker_fainted") is not success or c.get("self_fainted") is not success or payload.get("self_sacrifice",{}).get("outcome")!=("applied" if success else "not_applied") or leaf.get("critical_state")!="not_applicable" or leaf.get("damage_roll")!="not_applicable":return "final_gambit_derived_consequence_invalid"
 return None

def _recent_damage_retaliation_leaf(leaf: Mapping[str, Any]) -> str | None:
    p,c=leaf.get("provenance"),leaf.get("consequences"); move=p.get("move_id") if isinstance(p,Mapping) else None; payload=c.get("recent_damage_retaliation") if isinstance(c,Mapping) else None
    if move not in {"counter","mirror-coat","comeuppance","metal-burst"}: return "unexpected_recent_damage_retaliation_payload" if payload is not None else None
    if not isinstance(payload,Mapping): return "recent_damage_retaliation_consequence_missing"
    damage=c.get("damage"); event=payload.get("incoming_event"); outcome=payload.get("outcome")
    family=payload.get("family"); canonical=resolve_canonical_recent_damage_retaliation_move(move={"move_id":move}); expected=canonical.get("effect") if canonical.get("status")=="resolved" else None
    if not isinstance(damage,int) or isinstance(damage,bool) or damage<0 or leaf.get("critical_state")!="not_applicable" or leaf.get("damage_roll")!="not_applicable": return "recent_damage_retaliation_damage_shape_invalid"
    if family!=expected or payload.get("retaliation_target")!=p.get("target"): return "recent_damage_retaliation_rule_or_target_binding_invalid"
    pre,post,actual=payload.get("target_pre_hp"),payload.get("target_post_hp"),payload.get("actual_target_hp_loss")
    if not all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in (pre,post,actual)) or post>pre or actual!=pre-post or post!=c.get("target_final_hp") or payload.get("raw_damage")!=damage or actual!=min(damage,pre): return "recent_damage_retaliation_target_hp_binding_invalid"
    if outcome=="success":
        categories={"physical"} if expected.get("qualifying_category_policy")=="physical_only" else {"special"} if expected.get("qualifying_category_policy")=="special_only" else {"physical","special"}
        raw=max(1,(event["hp_lost"]*expected["multiplier"]["numerator"])//expected["multiplier"]["denominator"]) if isinstance(event,Mapping) and isinstance(event.get("hp_lost"),int) else None
        if not isinstance(event,Mapping) or event.get("status")!="resolved" or event.get("recipient")!=p.get("attacker") or event.get("source_attacker")!=p.get("target") or event.get("source_category") not in categories or event.get("qualifying_event") is not True or not isinstance(event.get("hp_lost"),int) or event["hp_lost"]<0 or damage!=raw: return "recent_damage_retaliation_event_binding_invalid"
    elif damage != 0: return "recent_damage_retaliation_failure_damage_invalid"
    return None


def _was_damaged_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping):
        return "was_damaged_power_leaf_provenance_invalid"
    move = provenance.get("move_id")
    authority = provenance.get("was_damaged_power_authority")
    if move not in {"avalanche", "revenge"}:
        return "unexpected_was_damaged_power_authority" if authority is not None else None
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != "detached-was-damaged-by-target-power-authority-v2":
        return "was_damaged_power_authority_missing_or_invalid"
    condition = authority.get("was_damaged_by_target_before_execution")
    if authority.get("move_id") != move or authority.get("canonical_base_power") != 60 or not isinstance(condition, bool) or authority.get("selected_base_power") != (120 if condition else 60):
        return "was_damaged_power_condition_or_base_power_invalid"
    if authority.get("user") != provenance.get("attacker") or authority.get("target") != provenance.get("target"):
        return "was_damaged_power_target_identity_invalid"
    event, hit = authority.get("source_event"), authority.get("qualifying_hit_provenance")
    if condition:
        if not isinstance(hit, Mapping) or hit.get("target_routing") != "target" or not isinstance(hit.get("actual_hp_loss"), int) or hit["actual_hp_loss"] <= 0:
            return "was_damaged_power_qualifying_hit_invalid"
        if not isinstance(event, Mapping) or event.get("status") != "resolved" or event.get("recipient") != provenance.get("attacker") or event.get("source_attacker") != provenance.get("target") or event.get("damage_route") != "target" or not isinstance(event.get("hp_lost"), int) or event["hp_lost"] < 0:
            return "was_damaged_power_source_event_invalid"
    elif hit is not None:
        return "was_damaged_power_false_condition_has_hit"
    return None


def _target_was_damaged_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping): return "target_was_damaged_power_leaf_provenance_invalid"
    move, authority = provenance.get("move_id"), provenance.get("target_was_damaged_power_authority")
    if move != "assurance": return "unexpected_target_was_damaged_power_authority" if authority is not None else None
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != "detached-target-was-damaged-power-authority-v1": return "target_was_damaged_power_authority_missing_or_invalid"
    condition = authority.get("target_was_damaged_before_execution")
    if authority.get("move_id") != "assurance" or authority.get("trigger_family") != "target_was_damaged_this_turn" or authority.get("canonical_base_power") != 60 or not isinstance(condition, bool) or authority.get("selected_base_power") != (120 if condition else 60): return "target_was_damaged_power_condition_or_base_power_invalid"
    if authority.get("user") != provenance.get("attacker") or authority.get("target") != provenance.get("target"): return "target_was_damaged_power_target_identity_invalid"
    event = authority.get("qualifying_damage_event")
    if not condition: return None if event is None else "target_was_damaged_power_false_condition_has_event"
    allowed = {"direct_attack_damage", "damage_based_recoil", "life_orb_recoil", "contact_reactive_damage"}
    if not isinstance(event, Mapping) or event.get("target") != provenance.get("target") or event.get("event_order") != "before_assurance_execution" or event.get("source_kind") not in allowed or not isinstance(event.get("actual_hp_loss"), int) or event["actual_hp_loss"] <= 0 or not isinstance(event.get("pair_branch_source_leaf_id"), str): return "target_was_damaged_power_qualifying_event_invalid"
    return None

def _target_already_acted_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    p=leaf.get("provenance")
    if not isinstance(p,Mapping): return "target_already_acted_power_leaf_provenance_invalid"
    move,authority=p.get("move_id"),p.get("target_already_acted_power_authority")
    if move!="payback": return "unexpected_target_already_acted_power_authority" if authority is not None else None
    if not isinstance(authority,Mapping) or authority.get("status")!="resolved" or authority.get("schema_version")!="detached-target-already-acted-power-authority-v1": return "target_already_acted_power_authority_missing_or_invalid"
    condition=authority.get("target_already_acted_before_execution")
    if authority.get("move_id")!="payback" or authority.get("trigger_family")!="target_already_acted" or authority.get("canonical_base_power")!=50 or not isinstance(condition,bool) or authority.get("selected_base_power") != (100 if condition else 50) or authority.get("user")!=p.get("attacker") or authority.get("target")!=p.get("target"): return "target_already_acted_power_condition_or_identity_invalid"
    action=authority.get("qualifying_target_action")
    if not condition:return None if action is None else "target_already_acted_false_condition_has_action"
    if not isinstance(action,Mapping) or action.get("event_order")!="before_payback_execution" or action.get("source_action_type") not in {"attack","protection","status","status_protection"} or not all(isinstance(action.get(key),str) and action.get(key) for key in ("pair_branch_source_leaf_id","source_action_id","source_selected_action_id","source_selected_move_id","source_execution_move_id")): return "target_already_acted_qualifying_action_invalid"
    return None

def _previous_action_failure_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    p=leaf.get("provenance")
    if not isinstance(p, Mapping): return "previous_action_failure_power_leaf_provenance_invalid"
    move, authority = p.get("move_id"), p.get("previous_action_failure_power_authority")
    if move != "stomping-tantrum": return "unexpected_previous_action_failure_power_authority" if authority is not None else None
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != "runtime-d0-previous-action-result-authority-v1": return "previous_action_failure_power_authority_missing_or_invalid"
    condition=authority.get("qualifies_as_previous_move_failure")
    if authority.get("move_id") != "stomping-tantrum" or authority.get("trigger_family") != "previous_move_failed" or authority.get("canonical_base_power") != 75 or not isinstance(condition, bool) or authority.get("selected_base_power") != (150 if condition else 75) or authority.get("owner") != p.get("attacker"): return "previous_action_failure_power_condition_or_identity_invalid"
    if not all(isinstance(authority.get(k), str) and authority[k] for k in ("previous_action_id", "selected_move_id", "execution_move_id", "previous_action_result_class")) or not isinstance(authority.get("source_turn"), int): return "previous_action_failure_power_prior_action_invalid"
    return None

def _same_turn_stat_drop_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    p=leaf.get("provenance")
    if not isinstance(p,Mapping): return "same_turn_stat_drop_power_leaf_provenance_invalid"
    move,authority=p.get("move_id"),p.get("same_turn_stat_drop_power_authority")
    if move!="lash-out": return "unexpected_same_turn_stat_drop_power_authority" if authority is not None else None
    if not isinstance(authority,Mapping) or authority.get("status")!="resolved" or authority.get("schema_version")!="detached-same-turn-stat-drop-power-authority-v1": return "same_turn_stat_drop_power_authority_missing_or_invalid"
    condition,event=authority.get("user_stat_was_lowered_before_execution"),authority.get("qualifying_stage_decrease_event")
    if authority.get("trigger_family")!="user_stat_was_lowered_this_turn" or authority.get("canonical_base_power")!=75 or authority.get("user")!=p.get("attacker") or not isinstance(condition,bool) or authority.get("selected_base_power") != (150 if condition else 75): return "same_turn_stat_drop_power_condition_or_identity_invalid"
    if not condition:return None if event is None else "same_turn_stat_drop_false_condition_has_event"
    if not isinstance(event,Mapping) or event.get("event_order")!="before_lash_out_execution" or event.get("stat") not in {"attack","defense","special-attack","special-defense","speed","accuracy","evasion"} or not isinstance(event.get("stage_before"),int) or not isinstance(event.get("stage_after"),int) or event["stage_after"]>=event["stage_before"] or event.get("delta")!=event["stage_after"]-event["stage_before"] or not isinstance(event.get("pair_branch_source_leaf_id"),str): return "same_turn_stat_drop_qualifying_event_invalid"
    return None

def _rage_fist_hit_count_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    p=leaf.get("provenance")
    if not isinstance(p,Mapping): return "rage_fist_hit_count_leaf_provenance_invalid"
    move,authority=p.get("move_id"),p.get("rage_fist_hit_count_power_authority")
    if move!="rage-fist": return "unexpected_rage_fist_hit_count_authority" if authority is not None else None
    if not isinstance(authority,Mapping) or authority.get("status")!="resolved" or authority.get("schema_version")!="detached-rage-fist-hit-count-power-authority-v1": return "rage_fist_hit_count_authority_missing_or_invalid"
    base,inc,effective,power=authority.get("d0_base_hit_count"),authority.get("same_turn_hit_increment"),authority.get("effective_hit_count"),authority.get("selected_base_power")
    if authority.get("trigger_family")!="persistent_received_hit_count" or authority.get("user")!=p.get("attacker") or authority.get("move_id")!="rage-fist" or authority.get("count_cap")!=6 or not all(isinstance(x,int) and not isinstance(x,bool) and x>=0 for x in (base,inc,effective)) or effective!=base+inc or power!=50+50*min(effective,6) or power not in {50,100,150,200,250,300,350}: return "rage_fist_hit_count_or_power_invalid"
    events=authority.get("qualifying_same_turn_hit_events")
    if not isinstance(events,list) or len(events)!=inc:return "rage_fist_same_turn_increment_event_count_invalid"
    for event in events:
        if not isinstance(event,Mapping) or event.get("target")!=p.get("attacker") or event.get("route")!="successful_direct_hit" or event.get("event_order")!="before_rage_fist_execution" or not isinstance(event.get("source_leaf_id"),str):return "rage_fist_same_turn_hit_event_invalid"
    return None

def _last_respects_faint_power_leaf(leaf: Mapping[str, Any]) -> str | None:
    p=leaf.get("provenance")
    if not isinstance(p,Mapping):return "last_respects_faint_power_leaf_provenance_invalid"
    move,a=p.get("move_id"),p.get("last_respects_faint_power_authority")
    if move!="last-respects":return "unexpected_last_respects_faint_power_authority" if a is not None else None
    if not isinstance(a,Mapping) or a.get("status")!="resolved" or a.get("schema_version")!="detached-last-respects-faint-power-authority-v1":return "last_respects_faint_power_authority_missing_or_invalid"
    raw,count,power=a.get("raw_allied_faint_count"),a.get("resolved_fainted_allies_count"),a.get("selected_base_power")
    if a.get("trigger_family")!="allied_faint_history" or a.get("user")!=p.get("attacker") or a.get("user_side")!=p.get("attacker",{}).get("side") or not isinstance(raw,int) or raw<0 or count!=raw or power!=50+50*count:return "last_respects_faint_power_count_or_binding_invalid"
    return None


def _endeavor_hp_difference_damage_leaf(leaf: Mapping[str, Any]) -> str | None:
    provenance, consequences = leaf.get("provenance"), leaf.get("consequences")
    move_id = provenance.get("move_id") if isinstance(provenance, Mapping) else None
    payload = consequences.get("endeavor_hp_difference_damage") if isinstance(consequences, Mapping) else None
    if move_id != "endeavor": return "unexpected_endeavor_hp_difference_payload" if payload is not None else None
    authority = provenance.get("execution_authority") if isinstance(provenance, Mapping) else None
    if not isinstance(payload, Mapping) or not isinstance(authority, Mapping): return "endeavor_hp_difference_consequence_missing"
    family = payload.get("family")
    if authority.get("schema_version") != "runtime-d0-special-damage-execution-authority-v1" or authority.get("special_damage_family") != "hp_difference_damage" or authority.get("move_id") != "endeavor" or family != authority.get("special_damage_rule_authority"):
        return "endeavor_hp_difference_authority_binding_mismatch"
    if not isinstance(family, Mapping) or family.get("family") != "hp_difference_damage" or family.get("relation") != "target_hp_above_attacker_hp": return "endeavor_hp_difference_rule_invalid"
    attacker, target = payload.get("attacker_execution_hp"), payload.get("target_execution_hp")
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 1 for value in (attacker, target)) or attacker != authority.get("execution_attacker_hp") or target != authority.get("execution_target_hp") or payload.get("target_route") != "target" or payload.get("hit_state") != leaf.get("hit_state") or payload.get("applicability") != authority.get("applicability"):
        return "endeavor_hp_difference_execution_binding_mismatch"
    successful = payload.get("outcome") == "success"
    expected_damage = target-attacker if successful else 0
    expected_post = attacker if successful else target
    if successful != (payload.get("hit_state") == "hit" and payload.get("applicability") == "applicable" and target > attacker) or payload.get("relation") != ("target_hp_above_attacker_hp" if target > attacker else "target_hp_not_above_attacker_hp") or payload.get("derived_damage") != expected_damage or payload.get("damage") != expected_damage or consequences.get("damage") != expected_damage or payload.get("target_post_hp") != expected_post or consequences.get("target_final_hp") != expected_post or leaf.get("critical_state") != "not_applicable" or leaf.get("damage_roll") != "not_applicable":
        return "endeavor_hp_difference_derived_result_invalid"
    if payload.get("outcome") == "failure" and payload.get("reason") != "endeavor_target_hp_not_above_attacker_hp": return "endeavor_hp_difference_failure_reason_invalid"
    return None


def _fractional_target_hp_damage_leaf(leaf: Mapping[str, Any]) -> str | None:
    """Validate the opaque fractional-family consequence without recomputing it."""
    provenance, consequences = leaf.get("provenance"), leaf.get("consequences")
    move_id = provenance.get("move_id") if isinstance(provenance, Mapping) else None
    payload = consequences.get("fractional_target_hp_damage") if isinstance(consequences, Mapping) else None
    supported = {"super-fang", "natures-madness", "ruination"}
    if move_id not in supported:
        return "unexpected_fractional_target_hp_damage_payload" if payload is not None else None
    if not isinstance(payload, Mapping) or not isinstance(provenance.get("execution_authority"), Mapping):
        return "fractional_target_hp_damage_consequence_missing"
    authority = provenance["execution_authority"]
    family = payload.get("family")
    expected = authority.get("special_damage_rule_authority")
    if authority.get("schema_version") != "runtime-d0-special-damage-execution-authority-v1" or authority.get("special_damage_family") != "current_hp_fraction_damage" or authority.get("move_id") != move_id or family != expected:
        return "fractional_target_hp_damage_authority_binding_mismatch"
    if not isinstance(family, Mapping) or family.get("move_id") != move_id or family.get("numerator") != 1 or family.get("denominator") != 2 or family.get("minimum_damage") != 1:
        return "fractional_target_hp_damage_rule_invalid"
    route, hp, state, applicability = payload.get("target_route"), payload.get("execution_target_hp"), payload.get("hit_state"), payload.get("applicability")
    if route not in {"target", "substitute"} or route != authority.get("target_route") or state != leaf.get("hit_state") or state not in {"hit", "miss"} or applicability != authority.get("applicability") or applicability not in {"applicable", "immune"} or not isinstance(hp, int) or isinstance(hp, bool) or hp < 1 or hp != authority.get("execution_target_hp"):
        return "fractional_target_hp_damage_execution_binding_mismatch"
    damage = payload.get("derived_damage")
    success = state == "hit" and applicability == "applicable"
    expected_damage = max(1, hp // 2) if success else 0
    if damage != expected_damage or consequences.get("damage") != expected_damage or leaf.get("critical_state") != "not_applicable" or leaf.get("damage_roll") != "not_applicable":
        return "fractional_target_hp_damage_derived_damage_invalid"
    route_post = payload.get("route_post_hp")
    if route_post != hp - damage or payload.get("target_post_hp") != consequences.get("target_final_hp"):
        return "fractional_target_hp_damage_post_hp_invalid"
    if route == "target" and consequences.get("target_final_hp") != hp - damage:
        return "fractional_target_hp_damage_target_route_post_hp_invalid"
    return None


def _knock_off_item_removal_leaf(leaf: Mapping[str, Any]) -> str | None:
    provenance, consequences = leaf.get("provenance"), leaf.get("consequences")
    payload = consequences.get("knock_off_item_removal") if isinstance(consequences, Mapping) else None
    move = provenance.get("move_id") if isinstance(provenance, Mapping) else None
    if move != "knock-off":
        return "unexpected_knock_off_item_removal_payload" if payload is not None else None
    authority = provenance.get("knock_off_item_removal_authority") if isinstance(provenance, Mapping) else None
    if not isinstance(payload, Mapping) or not isinstance(authority, Mapping):
        return "knock_off_item_removal_consequence_missing"
    if payload.get("authority") != authority or authority.get("status") != "resolved" or authority.get("move_id") != move or authority.get("target") != provenance.get("target"):
        return "knock_off_item_removal_authority_binding_invalid"
    if authority.get("power_modifier_q12") not in {4096, 6144} or authority.get("boost_eligible") is not authority.get("removable") or not isinstance(authority.get("sticky_hold"), bool):
        return "knock_off_item_removal_power_authority_invalid"
    before, after, outcome = payload.get("item_before"), payload.get("item_after"), payload.get("outcome")
    if authority.get("item_state") == "known_absent":
        return None if (before is None and after is None and outcome == "not_applicable") else "knock_off_absent_item_consequence_invalid"
    if not isinstance(before, str) or before != authority.get("item_before") or outcome not in {"removed", "not_removed"}:
        return "knock_off_item_before_or_outcome_invalid"
    source_hit = consequences.get("source_hit_context")
    hit = leaf.get("hit_state") == "hit" and isinstance(consequences.get("damage"), int) and consequences["damage"] > 0 and isinstance(source_hit, Mapping) and source_hit.get("target_routing") == "target"
    if outcome == "removed":
        if not hit or authority.get("removable") is not True or after is not None:
            return "knock_off_removal_consequence_invalid"
        if authority.get("sticky_hold") is True and consequences.get("target_final_hp") != 0:
            return "knock_off_sticky_hold_survival_removal_invalid"
    elif after != before:
        return "knock_off_nonremoval_item_after_invalid"
    return None

def _fling_item_throw_leaf(leaf: Mapping[str, Any]) -> str | None:
    provenance, consequences = leaf.get("provenance"), leaf.get("consequences")
    payload = consequences.get("fling_item_throw") if isinstance(consequences, Mapping) else None
    move = provenance.get("move_id") if isinstance(provenance, Mapping) else None
    if move != "fling": return "unexpected_fling_item_throw_payload" if payload is not None else None
    authority = provenance.get("fling_execution_authority") if isinstance(provenance, Mapping) else None
    if isinstance(authority, Mapping) and authority.get("outcome") in {"failed_item_suppressed", "failed_no_item", "failed_klutz"}:
        return None if payload is None and leaf.get("hit_state") == "not_applicable" and consequences.get("fling_execution") == authority else "fling_failure_leaf_invalid"
    if not isinstance(payload, Mapping) or not isinstance(authority, Mapping) or payload.get("authority") != authority:
        return "fling_item_throw_authority_missing"
    if authority.get("status") != "resolved" or authority.get("outcome") != "ready_throw" or authority.get("move_id") != "fling" or authority.get("actor") != provenance.get("attacker") or authority.get("target") != provenance.get("target") or any(authority.get(key) != provenance.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")):
        return "fling_item_throw_authority_binding_invalid"
    item = authority.get("user_item_before"); metadata = authority.get("fling_item_metadata")
    field, abilities = authority.get("item_suppression_field_authority"), authority.get("ability_suppression_authority")
    if not isinstance(item, Mapping) or item.get("status") != "known" or payload.get("item_before") != item.get("value") or payload.get("item_after") is not None or payload.get("outcome") != "thrown" or payload.get("timing") != "prepare_hit_before_accuracy_protection_immunity_damage" or leaf.get("hit_state") not in {"hit", "miss"} or not isinstance(metadata, Mapping) or metadata.get("effect", {}).get("kind") != "none" or metadata.get("effect", {}).get("classification") != "explicit_no_target_effect" or metadata.get("support_status") != "not_applicable" or metadata.get("provenance") != "frozen_pinned_showdown_fling_metadata_v1" or authority.get("resolved_base_power") != metadata.get("base_power") or authority.get("item_after") != {"state": "known_absent", "item": None} or not isinstance(field, Mapping) or field.get("status") != "resolved" or field.get("state") != "known_absent" or not isinstance(abilities, Mapping) or abilities.get("status") != "resolved" or abilities.get("klutz_active") is not False:
        return "fling_item_throw_transition_invalid"
    return None

def _item_transfer_leaf(leaf: Mapping[str, Any]) -> str | None:
 p,c=leaf.get("provenance"),leaf.get("consequences"); move=p.get("move_id") if isinstance(p,Mapping) else None; x=c.get("item_transfer_after_hit") if isinstance(c,Mapping) else None
 if move not in {"thief","covet"}: return "unexpected_item_transfer_payload" if x is not None else None
 a=p.get("item_transfer_authority") if isinstance(p,Mapping) else None
 if not isinstance(x,Mapping) or not isinstance(a,Mapping) or x.get("authority")!=a or a.get("move_id")!=move or a.get("user")!=p.get("attacker") or a.get("target")!=p.get("target"):return "item_transfer_authority_binding_invalid"
 if x.get("outcome")=="transferred":
  hit=c.get("source_hit_context"); item=a.get("target_item_before")
  if a.get("user_item_state")!="known_absent" or a.get("target_item_state")!="known_present" or a.get("removable") is not True or a.get("sticky_hold") is True or not isinstance(item,str) or leaf.get("hit_state")!="hit" or not isinstance(hit,Mapping) or hit.get("target_routing")!="target" or c.get("self_fainted") is True or x.get("item")!=item or x.get("user_item_after")!=item or x.get("target_item_after") is not None:return "item_transfer_consequence_invalid"
 elif x.get("outcome")!="not_transferred" or x.get("user_item_after")!=a.get("user_item_before") or x.get("target_item_after")!=a.get("target_item_before"):return "item_transfer_nontransfer_consequence_invalid"
 return None


def _atomic_item_swap_leaf(leaf: Mapping[str, Any]) -> str | None:
    p, c = leaf.get("provenance"), leaf.get("consequences")
    move = p.get("move_id") if isinstance(p, Mapping) else None
    transition = c.get("atomic_item_swap_status") if isinstance(c, Mapping) else None
    if move not in {"trick", "switcheroo"}:
        return "unexpected_atomic_item_swap_payload" if transition is not None else None
    authority = p.get("atomic_item_swap_status_execution_authority") if isinstance(p, Mapping) else None
    if not isinstance(transition, Mapping) or not isinstance(authority, Mapping) or transition.get("authority") != authority:
        return "atomic_item_swap_authority_binding_invalid"
    if authority.get("move_id") != move or authority.get("actor") != p.get("attacker") or authority.get("target") != p.get("target"):
        return "atomic_item_swap_identity_binding_invalid"
    before_a, before_t = transition.get("actor_item_before"), transition.get("target_item_before")
    after_a, after_t = transition.get("actor_item_after"), transition.get("target_item_after")
    valid = lambda x: isinstance(x, Mapping) and ((x.get("state") == "known_present" and isinstance(x.get("item"), str) and bool(x["item"])) or (x.get("state") == "known_absent" and x.get("item") is None))
    if not all(valid(x) for x in (before_a, before_t, after_a, after_t)):
        return "atomic_item_swap_item_state_invalid"
    outcome = transition.get("outcome")
    if outcome == "executed_swap":
        if after_a != before_t or after_t != before_a or authority.get("outcome") != outcome:
            return "atomic_item_swap_atomic_after_state_invalid"
    elif outcome in {"failed_both_no_item", "failed_item_restriction", "blocked_sticky_hold", "blocked_protection"}:
        if after_a != before_a or after_t != before_t or authority.get("outcome") != outcome:
            return "atomic_item_swap_nontransition_state_invalid"
    else: return "atomic_item_swap_outcome_invalid"
    return None


def _focus_sash_leaf(leaf: Mapping[str, Any]) -> str | None:
    consequences = leaf.get("consequences")
    provenance = leaf.get("provenance")
    if not isinstance(consequences, Mapping) or not isinstance(provenance, Mapping):
        return "focus_sash_leaf_consequence_missing"
    focus = consequences.get("focus_sash_survival")
    if focus is None:
        return None
    if not isinstance(focus, Mapping):
        return "focus_sash_survival_record_invalid"
    if focus.get("outcome") != "applied":
        return None
    item_after = focus.get("item_after")
    source = focus.get("source_hit")
    damage = consequences.get("damage")
    target_hp = consequences.get("target_final_hp")
    hp_before = focus.get("hp_before")
    ordered = leaf.get("ordered_hits")
    if isinstance(ordered, tuple):
        applied = [row for row in ordered if isinstance(row, Mapping) and isinstance(row.get("focus_sash_survival"), Mapping) and row["focus_sash_survival"].get("outcome") == "applied"]
        if len(applied) != 1 or applied[0].get("focus_sash_survival") != focus:
            return "focus_sash_survival_record_invalid"
        hit = applied[0]
        return None if (
            hit.get("pre_hp") == hp_before
            and hit.get("post_hp") == focus.get("target_final_hp") == 1
            and hit.get("actual_damage") == focus.get("actual_damage")
            and isinstance(source, Mapping)
            and source.get("move_id") == provenance.get("move_id")
            and item_after.get("status") == "known_absent" if isinstance(item_after, Mapping) else False
        ) else "focus_sash_survival_record_invalid"
    if (
        focus.get("item_before") != "focus-sash"
        or not isinstance(item_after, Mapping)
        or item_after.get("status") != "known_absent"
        or focus.get("focus_sash_eligible") is not True
        or focus.get("holder") != provenance.get("target")
        or not _hp(hp_before)
        or focus.get("target_final_hp") != target_hp
        or focus.get("actual_damage") != damage
        or focus.get("pre_survival_lethal") is not True
        or not isinstance(focus.get("raw_damage"), int)
        or isinstance(focus.get("raw_damage"), bool)
        or focus.get("raw_damage") < hp_before
        or not isinstance(source, Mapping)
        or source.get("move_id") != provenance.get("move_id")
        or focus.get("provenance") != "exact_detached_focus_sash_survival_consumption_v1"
    ):
        return "focus_sash_survival_record_invalid"
    return None


def _low_hp_type_leaf(leaf: Mapping[str, Any]) -> str | None:
    ordered = leaf.get("ordered_hits")
    if not isinstance(ordered, (tuple, list)):
        return None
    for hit in ordered:
        evidence = hit.get("low_hp_type_ability") if isinstance(hit, Mapping) else None
        if evidence is None:
            continue
        source_hit = evidence.get("source_hit") if isinstance(evidence, Mapping) else None
        if (
            not validate_low_hp_type_offensive_ability_applicability(evidence)
            or not isinstance(source_hit, Mapping)
            or source_hit.get("hit_index") != hit.get("hit_index")
        ):
            return "pair_final_low_hp_type_ability_consequence_invalid"
    return None


def _guts_status_attack_leaf(leaf: Mapping[str, Any]) -> str | None:
    ordered = leaf.get("ordered_hits")
    if not isinstance(ordered, (tuple, list)):
        return None
    for hit in ordered:
        evidence = hit.get("guts_status_attack_ability") if isinstance(hit, Mapping) else None
        if evidence is None:
            continue
        source_hit = evidence.get("source_hit") if isinstance(evidence, Mapping) else None
        if (
            not validate_guts_status_attack_ability_applicability(evidence)
            or (source_hit is not None and source_hit.get("hit_index") != hit.get("hit_index"))
        ):
            return "pair_final_guts_status_attack_ability_consequence_invalid"
    full_hp_error = _full_hp_defender_ability_leaf(ordered)
    if full_hp_error is not None:
        return full_hp_error
    return None


def _full_hp_defender_ability_leaf(ordered: tuple | list) -> str | None:
    for hit in ordered:
        evidence = hit.get("full_hp_defender_ability") if isinstance(hit, Mapping) else None
        if evidence is None:
            continue
        source_hit = evidence.get("source_hit") if isinstance(evidence, Mapping) else None
        if (
            not validate_full_hp_defender_ability_applicability(evidence)
            or not isinstance(source_hit, Mapping)
            or source_hit.get("hit_index") != hit.get("hit_index")
            or evidence.get("defender_current_hp") != hit.get("pre_hp")
            or evidence.get("defender_max_hp") != hit.get("target_max_hp")
        ):
            return "pair_final_full_hp_defender_ability_consequence_invalid"
    return None


def _order_probability(value: Mapping[str, Any]) -> Fraction | str:
    branch = value.get("action_order_branch")
    probability = value.get("action_order_conditional_probability")
    if branch is None and probability is None:
        return Fraction(1, 1)
    if not isinstance(branch, Mapping) or branch.get("order") != value.get("action_order"):
        return "pair_order_branch_invalid"
    parsed = _fraction(probability)
    if branch.get("order_branch_id") in {"equal_speed:own_first", "equal_speed:opponent_first"}:
        return parsed if parsed == Fraction(1, 2) else "pair_order_probability_invalid"
    if branch.get("mechanic") != "quick_claw" or branch.get("activation_state") not in {"activated", "not_activated"} or not isinstance(branch.get("holder"), Mapping): return "pair_order_branch_invalid"
    provenance = value.get("provenance")
    if not isinstance(provenance, Mapping) or branch["holder"] not in (provenance.get("own_actor"), provenance.get("opponent_actor")):
        return "quick_claw_order_holder_identity_invalid"
    holder_order = "own_first" if branch["holder"] == provenance.get("own_actor") else "opponent_first"
    if branch["activation_state"] == "activated":
        return parsed if parsed == Fraction(1, 5) and value.get("action_order") == holder_order else "quick_claw_activation_probability_invalid"
    tie = branch.get("non_activation_order_branch")
    if tie is None:
        return parsed if parsed == Fraction(4, 5) else "quick_claw_non_activation_probability_invalid"
    if not isinstance(tie, Mapping) or tie.get("order") != value.get("action_order") or tie.get("order_branch_id") not in {"equal_speed:own_first", "equal_speed:opponent_first"}: return "quick_claw_non_activation_tie_binding_invalid"
    return parsed if parsed == Fraction(2, 5) else "quick_claw_non_activation_tie_probability_invalid"


def _execution_probability(second: Mapping[str, Any]) -> Fraction | str:
    branch = second.get("execution_branch")
    probability = second.get("execution_conditional_probability")
    if branch is None and probability is None:
        return Fraction(1, 1)
    if not isinstance(branch, Mapping) or not isinstance(branch.get("execution_branch_id"), str):
        return "second_action_execution_branch_invalid"
    parsed = _fraction(probability)
    if branch.get("state") != second.get("state") or _fraction(branch.get("conditional_probability")) != parsed:
        return "second_action_execution_branch_mismatch"
    if second["state"] == "cancelled_due_to_paralysis":
        return parsed if branch.get("execution_branch_id") == "second_action:fully_paralyzed" and parsed == Fraction(1, 4) else "second_action_execution_probability_invalid"
    if second["state"] == "cancelled_due_to_flinch":
        return parsed if branch.get("execution_branch_id") == "second_action:flinched" and parsed == Fraction(1, 1) and branch.get("reason") == "second_action_cancelled_due_to_flinch" else "second_action_execution_probability_invalid"
    if second["state"] == "executed":
        return parsed if branch.get("execution_branch_id") == "second_action:can_act_after_paralysis" and parsed == Fraction(3, 4) else "second_action_execution_probability_invalid"
    return "second_action_execution_branch_invalid"


def _flinch_cancellation_binding(first: Mapping[str, Any], second: Mapping[str, Any]) -> str | None:
    """A flinch cancellation must be a surviving first-hit consequence on this actor."""
    consequences, provenance = first.get("consequences"), first.get("provenance")
    secondary = consequences.get("secondary") if isinstance(consequences, Mapping) else None
    marker = secondary.get("hypothetical_target_flinch") if isinstance(secondary, Mapping) else None
    if not isinstance(provenance, Mapping) or not isinstance(marker, Mapping) or secondary.get("branch") != "effect": return "flinch_cancellation_missing_exact_provenance"
    if marker.get("schema_version") != "detached-hypothetical-immediate-flinch-v1" or marker.get("state") != "flinched": return "flinch_cancellation_provenance_invalid"
    if marker.get("provenance") == "fling_item_bound_deterministic_flinch_v1":
        authority = secondary.get("fling_item_bound_target_effect_authority")
        if not isinstance(authority, Mapping) or authority.get("schema_version") != "runtime-d0-fling-item-bound-deterministic-target-effect-authority-v1" or authority.get("status") != "resolved" or authority.get("outcome") != "applied_flinch_pending_action" or authority.get("target") != provenance.get("target") or marker.get("source_fling_item") != authority.get("item_id") or marker.get("pending_action_id") != authority.get("pending_target_action", {}).get("action_id"): return "fling_flinch_cancellation_authority_invalid"
    elif marker.get("provenance") not in {"iron_head_successful_damage_roll_secondary_v1", "fake_out_successful_damage_roll_secondary_v1"}: return "flinch_cancellation_provenance_invalid"
    if provenance.get("target") != second.get("actor"): return "flinch_cancellation_wrong_pending_actor"
    target_hp = consequences.get("target_final_hp")
    if not isinstance(target_hp, int) or target_hp <= 0: return "flinch_cancellation_after_target_faint"
    return None


def _final(source: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any] | str:
    provenance, consequences = source.get("provenance"), source.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping): return "pair_final_consequence_missing"
    actor = provenance.get("attacker")
    if actor == base["own_actor"]:
        own_hp, opponent_hp = consequences.get("own_final_hp"), consequences.get("target_final_hp")
    elif actor == base["opponent_actor"]:
        own_hp, opponent_hp = consequences.get("target_final_hp"), consequences.get("own_final_hp")
    else: return "pair_final_actor_identity_mismatch"
    if not _hp(own_hp) or not _hp(opponent_hp): return "pair_final_hp_missing"
    if isinstance(consequences.get("life_orb"), Mapping) and not _life_orb(consequences["life_orb"]):
        return "pair_final_life_orb_consequence_invalid"
    if isinstance(consequences.get("contact_reactive_status"), Mapping) and not _contact_reactive_status(consequences["contact_reactive_status"]):
        return "pair_final_contact_reactive_status_consequence_invalid"
    return {"own_final_hp": own_hp, "opponent_final_hp": opponent_hp,
            "own_fainted": own_hp == 0, "opponent_fainted": opponent_hp == 0,
            "supported_stage_consequence": deepcopy(consequences.get("deterministic_stage_effect")),
            "supported_secondary_consequence": deepcopy(consequences.get("secondary")),
            "reactive_shield_condition_consequence": deepcopy(consequences.get("reactive_shield_condition_transition")),
            "contact_reactive_damage_consequence": deepcopy(consequences.get("contact_reactive_damage")),
            "contact_reactive_status_consequence": deepcopy(consequences.get("contact_reactive_status")),
            "life_orb_consequence": deepcopy(consequences.get("life_orb"))}


def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _direct_heal_leaf(leaf: Mapping[str, Any]) -> str | None:
    consequences, provenance = leaf.get("consequences"), leaf.get("provenance")
    if not isinstance(consequences, Mapping) or not isinstance(provenance, Mapping): return "direct_heal_leaf_consequence_missing"
    heal = consequences.get("direct_heal")
    if heal is None: return None
    if leaf.get("hit_state") != "not_applicable" or leaf.get("critical_state") != "not_applicable" or leaf.get("damage_roll") != "not_applicable" or consequences.get("damage") != 0 or consequences.get("contact") != "not_applicable": return "direct_heal_leaf_non_heal_semantics_invalid"
    if not isinstance(heal, Mapping) or not all(isinstance(heal.get(key), int) and not isinstance(heal.get(key), bool) for key in ("pre_hp", "max_hp", "nominal_heal", "actual_heal", "post_hp")): return "direct_heal_leaf_shape_invalid"
    if heal["max_hp"] < 1 or not 0 < heal["pre_hp"] <= heal["max_hp"] or heal["nominal_heal"] != (heal["max_hp"] + 1) // 2 or heal["actual_heal"] != min(heal["nominal_heal"], heal["max_hp"] - heal["pre_hp"]) or heal["post_hp"] != heal["pre_hp"] + heal["actual_heal"] or consequences.get("own_final_hp") != heal["post_hp"]: return "direct_heal_leaf_replay_invalid"
    authority = provenance.get("direct_heal_execution_authority")
    if not isinstance(authority, Mapping) or authority.get("actor") != provenance.get("attacker") or authority.get("action_id") != leaf.get("candidate_id") or authority.get("move_id") != provenance.get("move_id"): return "direct_heal_leaf_provenance_invalid"
    return None
def _drain_leaf(leaf: Mapping[str, Any]) -> str | None:
    consequences = leaf.get("consequences")
    drain = consequences.get("drain") if isinstance(consequences, Mapping) else None
    if drain is None: return None
    if not isinstance(drain, Mapping) or drain.get("drain_family") != "ordinary_damage_drain": return "drain_family_invalid"
    fraction, source = drain.get("fraction"), drain.get("source_hit")
    if not isinstance(fraction, Mapping) or (fraction.get("numerator"), fraction.get("denominator")) not in {(1,2),(3,4)} or not isinstance(source, Mapping): return "drain_fraction_or_source_invalid"
    actual, pre, post = drain.get("actual_target_hp_loss"), source.get("target_pre_hp"), source.get("target_post_hp")
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (actual,pre,post)) or actual != pre-post or actual < 1: return "drain_actual_damage_basis_invalid"
    nominal = (actual*fraction["numerator"] + fraction["denominator"]//2)//fraction["denominator"]
    big = drain.get("big_root")
    if not isinstance(big,Mapping) or big.get("modifier") != {"numerator":5324,"denominator":4096} or not isinstance(big.get("applies"),bool) or big.get("would_be_recovery") != ((nominal*5324)//4096 if big["applies"] else nominal) or drain.get("nominal_recovery") != nominal: return "drain_big_root_replay_invalid"
    own, maximum, post_own = drain.get("attacker_pre_hp"), drain.get("attacker_max_hp"), drain.get("attacker_post_hp")
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (own,maximum,post_own)) or not 0 <= own <= maximum: return "drain_attacker_hp_invalid"
    would = big["would_be_recovery"]
    if drain.get("liquid_ooze") is True:
        if post_own != max(0,own-would) or drain.get("reversed_damage") != would or drain.get("effective_heal") != 0: return "drain_liquid_ooze_replay_invalid"
    elif drain.get("liquid_ooze") is False:
        if post_own != min(maximum,own+would) or drain.get("effective_heal") != post_own-own or drain.get("reversed_damage") != 0: return "drain_heal_replay_invalid"
    else: return "drain_liquid_ooze_state_invalid"
    return None
def _damage_based_recoil_leaf(leaf: Mapping[str, Any]) -> str | None:
    c=leaf.get("consequences"); recoil=c.get("damage_based_recoil") if isinstance(c,Mapping) else None
    if recoil is None:return None
    if not isinstance(recoil,Mapping) or recoil.get("recoil_family")!="damage_based_recoil":return "recoil_family_invalid"
    fraction,source=recoil.get("fraction"),recoil.get("source_hit")
    if not isinstance(fraction,Mapping) or (fraction.get("numerator"),fraction.get("denominator")) not in {(1,4),(1,3),(1,2)} or not isinstance(source,Mapping):return "recoil_fraction_or_source_invalid"
    actual,pre,post=recoil.get("actual_target_hp_loss"),source.get("target_pre_hp"),source.get("target_post_hp")
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (actual,pre,post)) or actual<1 or actual!=pre-post:return "recoil_actual_damage_basis_invalid"
    nominal=max(1,(actual*fraction["numerator"]+fraction["denominator"]//2)//fraction["denominator"])
    own,after=recoil.get("attacker_pre_hp"),recoil.get("attacker_post_hp")
    if not isinstance(own,int) or not isinstance(after,int) or recoil.get("nominal_recoil")!=nominal or recoil.get("prevention") not in {"none","rock_head","magic_guard"}:return "recoil_replay_invalid"
    expected=0 if recoil["prevention"]!="none" else nominal
    return None if recoil.get("recoil_damage")==expected and after==max(0,own-expected) else "recoil_post_hp_invalid"
def _contact_reactive_status_leaf(leaf: Mapping[str, Any]) -> str | None:
    consequences = leaf.get("consequences")
    status = consequences.get("contact_reactive_status") if isinstance(consequences, Mapping) else None
    if isinstance(status, Mapping) and not _contact_reactive_status(status):
        return "pair_final_contact_reactive_status_consequence_invalid"
    return None
def _contact_reactive_status(value: Any) -> bool:
    authority = value.get("authority") if isinstance(value, Mapping) else None
    overlay = value.get("overlay") if isinstance(value, Mapping) else None
    branch = value.get("branch") if isinstance(value, Mapping) else None
    if not isinstance(authority, Mapping) or authority.get("schema_version") != "runtime-d0-contact-reactive-status-authority-v1" or authority.get("status") != "resolved":
        return False
    if authority.get("outcome") != "applies":
        return overlay is None
    if authority.get("reactive_ability") == "effect-spore":
        return _effect_spore_contact_reactive_status(authority, overlay, branch)
    if branch not in {"activation", "no_activation"}:
        return False
    if authority.get("activation_probability") != {"numerator": 3, "denominator": 10} or authority.get("no_activation_probability") != {"numerator": 7, "denominator": 10}:
        return False
    if authority.get("reactive_ability") not in {"static", "flame-body", "poison-point"} or authority.get("attempted_condition") not in {"paralysis", "burn", "poison"}:
        return False
    if not isinstance(overlay, Mapping) or overlay.get("schema_version") != "detached-contact-reactive-status-overlay-v1" or overlay.get("branch") != branch:
        return False
    expected = authority["activation_probability"] if branch == "activation" else authority["no_activation_probability"]
    if overlay.get("probability") != expected:
        return False
    transition = overlay.get("hypothetical_condition_authority")
    if overlay.get("transition_applied") is True:
        return isinstance(transition, Mapping) and transition.get("status") == "known_present" and transition.get("condition") == authority.get("attempted_condition")
    return overlay.get("transition_applied") is False


def _effect_spore_contact_reactive_status(authority: Mapping[str, Any], overlay: Any, branch: Any) -> bool:
    """Use the graph ledger's strict canonical Effect Spore row contract."""
    return _validate_effect_spore_contact_reactive_status(authority, overlay, branch)


def _disable_restriction_leaf(first: Mapping[str, Any], second_leaf: Any, base: Mapping[str, Any], action_order: str) -> str | None:
    if not isinstance(second_leaf, Mapping): return None
    consequences, provenance = second_leaf.get("consequences"), second_leaf.get("provenance")
    gate = consequences.get("disable_execution_gate") if isinstance(consequences, Mapping) else None
    marker = provenance.get("disable_action_restriction") if isinstance(provenance, Mapping) else None
    if gate is None and marker is None: return None
    if action_order != "own_first" or not isinstance(gate, Mapping) or marker != gate or consequences.get("execution_failure") != "disable_action_restriction" or gate.get("actor") != base["opponent_actor"] or gate.get("selected_action_id") != base["opponent_action_id"] or gate.get("execution_state") != "restricted_by_disable": return "disable_restriction_ledger_binding_invalid"
    first_app = first.get("consequences", {}).get("disable_application") if isinstance(first.get("consequences"), Mapping) else None
    evidence = gate.get("restriction_evidence")
    if not isinstance(first_app, Mapping) or first_app.get("outcome") != "applicable" or first_app.get("actor") != base["own_actor"] or first_app.get("target") != base["opponent_actor"] or first_app.get("disabled_move_id") != gate.get("selected_move_id") or not isinstance(evidence, tuple) or not evidence or evidence[0] != first_app: return "disable_restriction_ledger_application_invalid"
    if any(second_leaf.get(key) != "not_applicable" for key in ("hit_state", "critical_state", "damage_roll")) or consequences.get("damage") != 0 or consequences.get("contact") != "not_applicable": return "disable_restriction_ledger_failure_identity_invalid"
    return None


def _encore_forced_execution_leaf(first: Mapping[str, Any], second: Mapping[str, Any], leaf: Mapping[str, Any], base: Mapping[str, Any], action_order: str) -> str | None:
    forced = second.get("forced_execution_action")
    marker = leaf.get("consequences", {}).get("encore_forced_execution") if isinstance(leaf.get("consequences"), Mapping) else None
    provenance = leaf.get("provenance") if isinstance(leaf.get("provenance"), Mapping) else None
    if forced is None and marker is None and not (isinstance(provenance, Mapping) and "encore_forced_execution" in provenance): return None
    if action_order != "own_first" or not isinstance(forced, Mapping) or marker != forced or not isinstance(provenance, Mapping) or provenance.get("encore_forced_execution") != forced:
        return "encore_forced_execution_binding_invalid"
    required = {"status", "schema_version", "actor", "selected_action_id", "selected_move_id", "execution_action_id", "execution_move_id", "execution_move_metadata", "execution_priority", "replacement_reason", "encore_application", "provenance"}
    if set(forced) != required or forced.get("status") != "resolved" or forced.get("schema_version") != "detached-encore-action-restriction-v1" or forced.get("actor") != base["opponent_actor"] or forced.get("selected_action_id") != base["opponent_action_id"] or forced.get("replacement_reason") != "encore":
        return "encore_forced_execution_binding_invalid"
    meta, application = forced.get("execution_move_metadata"), forced.get("encore_application")
    if not isinstance(meta, Mapping) or meta.get("move_id") != forced.get("execution_move_id") or meta.get("priority") != forced.get("execution_priority") or not isinstance(forced.get("execution_priority"), int) or isinstance(forced.get("execution_priority"), bool) or not isinstance(application, Mapping):
        return "encore_forced_execution_metadata_invalid"
    if application.get("status") != "resolved" or application.get("outcome") != "applicable" or application.get("actor") != base["own_actor"] or application.get("target") != base["opponent_actor"] or application.get("action_id") != base["own_action_id"] or application.get("locked_move_id") != forced.get("execution_move_id"):
        return "encore_forced_execution_application_invalid"
    if leaf.get("candidate_id") != forced.get("execution_action_id") or provenance.get("selected_action_id") != forced.get("selected_action_id") or provenance.get("execution_move_id") != forced.get("execution_move_id") or provenance.get("replacement_reason") != "encore":
        return "encore_forced_execution_leaf_identity_invalid"
    return None


def _sucker_punch_leaf(leaf: Mapping[str, Any], *, action_order: str, pair_base: Mapping[str, Any]) -> str | None:
    provenance = leaf.get("provenance") if isinstance(leaf, Mapping) else None
    if not isinstance(provenance, Mapping) or provenance.get("move_id") != "sucker-punch": return None
    applicability = provenance.get("sucker_punch_execution_applicability")
    consequences = leaf.get("consequences")
    if not isinstance(applicability, Mapping) or not isinstance(consequences, Mapping) or consequences.get("sucker_punch_execution") != applicability:
        return "sucker_punch_execution_applicability_missing"
    expected_metadata = {"move_id": "sucker-punch", "category": "physical", "power": 70, "type": "dark", "accuracy": 100, "priority": 1}
    if (
        applicability.get("schema_version") != "runtime-d0-sucker-punch-execution-applicability-authority-v1"
        or applicability.get("move_id") != "sucker-punch"
        or applicability.get("own_action_id") != "attack:sucker-punch"
        or applicability.get("canonical_move_metadata") != expected_metadata
        or applicability.get("sucker_punch_actor") != provenance.get("attacker")
        or applicability.get("target") != provenance.get("target")
        or any(applicability.get(key) != pair_base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner"))
    ):
        return "sucker_punch_execution_applicability_invalid"
    if applicability.get("status") == "applies":
        if action_order != "own_first" or applicability.get("action_order") != "own_first" or applicability.get("target_already_acted") is not False or applicability.get("target_selected_action_kind") != "attack" or applicability.get("target_selected_move_category") not in {"physical", "special"}:
            return "sucker_punch_success_condition_invalid"
        return None
    if applicability.get("status") != "not_applicable" or applicability.get("reason") not in {"sucker_punch_target_not_readying_attack", "sucker_punch_target_already_acted"}:
        return "sucker_punch_failure_condition_invalid"
    if applicability.get("reason") == "sucker_punch_target_already_acted" and (action_order != "opponent_first" or applicability.get("action_order") != "opponent_first" or applicability.get("target_already_acted") is not True):
        return "sucker_punch_failure_order_invalid"
    if leaf.get("hit_state") != "not_applicable" or leaf.get("critical_state") != "not_applicable" or leaf.get("damage_roll") != "not_applicable" or consequences.get("damage") != 0 or consequences.get("contact") != "not_applicable":
        return "sucker_punch_failure_leaf_not_deterministic"
    return None

    outcomes = authority.get("effect_spore_outcomes")
    contact = authority.get("contact_authority")
    source_hit = authority.get("source_hit")
    if (
        branch not in expected or not isinstance(outcomes, (tuple, list)) or len(outcomes) != 4
        or not isinstance(contact, Mapping) or contact.get("status") != "resolved" or contact.get("contact_state") != "contact"
        or not isinstance(source_hit, Mapping) or not isinstance(source_hit.get("hit_index"), int) or source_hit["hit_index"] < 1
        or source_hit.get("source_action_id") != authority.get("source_action_id") or source_hit.get("source_move_id") != authority.get("source_move_id")
        or contact.get("action_id") != authority.get("source_action_id") or contact.get("attacker") != authority.get("attacker") or contact.get("target") != authority.get("defender")
        or authority.get("effect_spore_immunity", {}).get("outcome") != "not_immune"
        or not isinstance(authority.get("type_authority"), Mapping) or authority["type_authority"].get("status") != "resolved"
        or not isinstance(authority.get("attacker_modifier_authorities"), Mapping) or not isinstance(authority.get("defender_modifier_authorities"), Mapping)
        or authority["defender_modifier_authorities"].get("ability_authority", {}).get("value") != "effect-spore"
        or not all(authority.get(key) == contact.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner"))
    ):
        return False
    rows = {row.get("outcome"): row for row in outcomes if isinstance(row, Mapping)}
    if set(rows) != set(expected) or any(row.get("probability") != expected[outcome] or not isinstance(row.get("transition_applies"), bool) for outcome, row in rows.items()):
        return False
    if not isinstance(overlay, Mapping) or overlay.get("schema_version") != "detached-contact-reactive-status-overlay-v1" or overlay.get("branch") != branch or overlay.get("probability") != expected[branch] or overlay.get("source_authority") != authority or overlay.get("owner") != authority.get("attacker"):
        return False
    transition = overlay.get("hypothetical_condition_authority")
    if overlay.get("transition_applied") is True:
        return (
            branch != "none" and rows[branch].get("transition_applies") is True
            and authority.get("condition_before") == "none" and isinstance(transition, Mapping)
            and transition.get("status") == "known_present" and transition.get("condition") == branch
            and transition.get("condition_before") == "known_none" and transition.get("condition_after") == branch
            and transition.get("source_hit") == source_hit
            and overlay.get("cancels_remaining_hits") is (branch == "sleep")
            and overlay.get("cancellation_reason") == ("effect_spore_sleep_cancels_remaining_hits" if branch == "sleep" else None)
        )
    return rows[branch].get("transition_applies") is False and overlay.get("transition_applied") is False and overlay.get("cancels_remaining_hits") in {None, False}


def _pivot_second_action_target_binding(branch: Mapping[str, Any], base: Mapping[str, Any], first: Mapping[str, Any], second: Mapping[str, Any]) -> str | None:
    """Validate the narrow changed-target exception owned by a pivot transition."""
    pivot = branch.get("pivot_transition")
    if pivot is None:
        return None
    authority = pivot.get("pivot_authority") if isinstance(pivot, Mapping) else None
    incoming = pivot.get("resulting_active_owner") if isinstance(pivot, Mapping) else None
    provenance = second.get("provenance") if isinstance(second, Mapping) else None
    if (
        branch.get("action_order") != "own_first"
        or not isinstance(authority, Mapping) or authority.get("status") != "applies"
        or not isinstance(incoming, Mapping) or not isinstance(provenance, Mapping)
        or first.get("provenance", {}).get("attacker") != base["own_actor"]
        or provenance.get("attacker") != base["opponent_actor"]
        or not _same_owner_identity(authority.get("selected_replacement_owner"), incoming)
        or not _same_owner_identity(provenance.get("target"), incoming)
        or _same_owner_identity(incoming, base["own_actor"])
    ):
        return "pivot_second_action_target_binding_invalid"
    return None


def _same_owner_identity(left: Any, right: Any) -> bool:
    keys = ("session_id", "side", "slot_index", "pokemon_id")
    return isinstance(left, Mapping) and isinstance(right, Mapping) and all(left.get(key) == right.get(key) for key in keys)


def _life_orb(value: Any) -> bool:
    authority = value.get("authority") if isinstance(value, Mapping) else None
    overlay = value.get("overlay") if isinstance(value, Mapping) else None
    modifier = authority.get("damage_modifier") if isinstance(authority, Mapping) else None
    recoil = authority.get("recoil") if isinstance(authority, Mapping) else None
    fraction = modifier.get("fraction") if isinstance(modifier, Mapping) else None
    if not isinstance(authority, Mapping) or authority.get("schema_version") != "runtime-d0-life-orb-immediate-authority-v1" or authority.get("status") != "resolved":
        return False
    if modifier.get("applies") is True and (modifier.get("modifier_q12") != 5324 or fraction != {"numerator": 5324, "denominator": 4096}): return False
    if modifier.get("applies") is False and (modifier.get("modifier_q12") != 4096 or fraction != {"numerator": 4096, "denominator": 4096}): return False
    if not isinstance(recoil, Mapping) or recoil.get("suppressed_by") not in {None, "sheer-force", "magic-guard"}: return False
    if not all(isinstance(recoil.get(key), int) and not isinstance(recoil.get(key), bool) and recoil[key] >= 0 for key in ("pre_hp", "max_hp", "recoil_damage", "post_hp")): return False
    if recoil["max_hp"] < 1 or recoil["post_hp"] != max(0, recoil["pre_hp"] - recoil["recoil_damage"]) or recoil.get("fainted") is not (recoil["post_hp"] == 0): return False
    if recoil.get("outcome") == "recoiled" and recoil["recoil_damage"] != max(1, recoil["max_hp"] // 10): return False
    if recoil.get("suppressed_by") is not None and (recoil["recoil_damage"] != 0 or recoil["post_hp"] != recoil["pre_hp"]): return False
    hp = overlay.get("hypothetical_hp_authority") if isinstance(overlay, Mapping) and overlay.get("schema_version") == "detached-life-orb-attacker-hp-overlay-v1" else None
    return isinstance(hp, Mapping) and hp.get("current_hp") == recoil["post_hp"] and hp.get("maximum_hp") == recoil["max_hp"]
def _fraction(value: Any) -> Fraction:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or not isinstance(value.get("denominator"), int) or value["denominator"] <= 0 or value["numerator"] <= 0: return Fraction(-1, 1)
    return Fraction(value["numerator"], value["denominator"])
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _status(value: Mapping[str, Any]) -> str: return value.get("status") if value.get("status") in _STATUSES else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any] | None = None, **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **(deepcopy(dict(base)) if isinstance(base, Mapping) else {}), "reason": reason, **deepcopy(extra)}
