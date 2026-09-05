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
    if marker.get("schema_version") != "detached-hypothetical-immediate-flinch-v1" or marker.get("state") != "flinched" or marker.get("provenance") not in {"iron_head_successful_damage_roll_secondary_v1", "fake_out_successful_damage_roll_secondary_v1"}: return "flinch_cancellation_provenance_invalid"
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
