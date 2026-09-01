"""Strict graph-aware shared ledger validation and metric traversal.

This owner validates the compressed variable first-action graph and traverses
only its terminal transition frontier.  It never expands root-to-terminal
multi-hit paths into the legacy flat Cartesian leaf collection.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import _terminal_sources
from llm.advisor_low_hp_type_offensive_ability import (
    validate_low_hp_type_offensive_ability_applicability,
)


PAIR_SCHEMA = "detached-variable-two-to-five-hit-graph-immediate-move-pair-v1"
LEDGER_SCHEMA = "exact-immediate-action-pair-outcome-ledger-v1"
HORIZON = "immediate_action_pair"


def normalize_variable_two_to_five_hit_graph_pair(*, pair: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and preserve a graph pair without replaying mechanics."""
    if pair.get("schema_version") != PAIR_SCHEMA or pair.get("horizon") != HORIZON:
        return _result("rejected", "variable_graph_pair_schema_or_horizon_invalid", base)
    if any(pair.get(key) != value for key, value in base.items()):
        return _result("rejected", "variable_graph_pair_binding_mismatch", base)
    if _fraction(pair.get("terminal_probability_mass")) != Fraction(1, 1):
        return _result("rejected", "variable_graph_pair_declared_root_mass_invalid", base)
    orders = pair.get("order_graphs")
    if not isinstance(orders, tuple) or not orders:
        return _result("rejected", "variable_graph_pair_order_graphs_missing", base)
    parsed: list[dict[str, Any]] = []
    for row in orders:
        value = _order_graph(row, base)
        if isinstance(value, str):
            return _result("rejected", value, base)
        parsed.append(value)
    mass = sum((row["order_weighted_terminal_probability_mass"] for row in parsed), Fraction())
    if mass != Fraction(1, 1):
        return _result("rejected", "variable_graph_pair_root_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": LEDGER_SCHEMA, "horizon": HORIZON, **deepcopy(dict(base)),
        "conditional_on": deepcopy(pair.get("conditional_on")),
        "terminal_leaf_representation": "exact_variable_multi_hit_graph_paths",
        "variable_graph_pair": deepcopy(dict(pair)),
        "validated_order_graphs": tuple(_serialize_order(row) for row in parsed),
        "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_variable_graph_path_identity",
        "provenance": "strict_variable_multi_hit_graph_to_shared_pair_outcome_normalization_v1",
    }


def graph_metric_rows(*, ledger: Mapping[str, Any], base: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | str:
    """Traverse graph transition outcomes exactly for descriptive metrics."""
    if ledger.get("terminal_leaf_representation") != "exact_variable_multi_hit_graph_paths":
        return "variable_graph_ledger_representation_invalid"
    orders = ledger.get("validated_order_graphs")
    if not isinstance(orders, tuple) or not orders:
        return "variable_graph_ledger_order_graphs_missing"
    rows: list[dict[str, Any]] = []
    for order in orders:
        order_probability = _fraction(order.get("order_conditional_probability"))
        first_actor = order.get("first_actor")
        transitions = order.get("terminal_transitions")
        if order_probability <= 0 or not isinstance(first_actor, Mapping) or not isinstance(transitions, tuple):
            return "variable_graph_metric_order_payload_invalid"
        for transition in transitions:
            incoming = _fraction(transition.get("incoming_path_probability"))
            first_final = _final_from_consequences(transition.get("first_terminal_consequences"), first_actor, base)
            second = transition.get("second_action")
            if incoming <= 0 or isinstance(first_final, str) or not isinstance(second, Mapping):
                return first_final if isinstance(first_final, str) else "variable_graph_metric_transition_invalid"
            state = second.get("state")
            if state == "cancelled_due_to_faint":
                if _fraction(second.get("conditional_probability")) != Fraction(1, 1): return "variable_graph_metric_faint_cancellation_probability_invalid"
                rows.append(_row(order, transition, "cancelled_due_to_faint", None, order_probability * incoming, first_final)); continue
            if state != "outcome_graph" or _fraction(second.get("conditional_probability")) != Fraction(1, 1):
                return "variable_graph_metric_second_action_payload_invalid"
            outcomes = second.get("outcomes")
            if not isinstance(outcomes, tuple) or not outcomes:
                return "variable_graph_metric_second_action_outcomes_missing"
            outcome_mass = Fraction()
            for outcome in outcomes:
                conditional = _fraction(outcome.get("conditional_probability"))
                if conditional <= 0: return "variable_graph_metric_second_outcome_probability_invalid"
                outcome_mass += conditional
                if outcome.get("state") == "cancelled_due_to_paralysis":
                    rows.append(_row(order, transition, "cancelled_due_to_paralysis", None, order_probability * incoming * conditional, first_final)); continue
                if outcome.get("state") != "executed" or not isinstance(outcome.get("second_action_terminal_leaves"), tuple):
                    return "variable_graph_metric_second_outcome_invalid"
                leaves = outcome["second_action_terminal_leaves"]
                leaf_mass = sum((_fraction(leaf.get("probability")) for leaf in leaves if isinstance(leaf, Mapping)), Fraction())
                if not leaves or leaf_mass != Fraction(1, 1) or _fraction(outcome.get("second_action_terminal_probability_mass")) != leaf_mass:
                    return "variable_graph_metric_second_leaf_mass_invalid"
                for leaf in leaves:
                    final = _final_from_leaf(leaf, base)
                    if isinstance(final, str): return final
                    rows.append(_row(order, transition, "executed", leaf.get("leaf_id"), order_probability * incoming * conditional * _fraction(leaf["probability"]), final))
            if outcome_mass != Fraction(1, 1): return "variable_graph_metric_second_outcome_mass_not_one"
    mass = sum((row["probability"] for row in rows), Fraction())
    return tuple(rows) if mass == Fraction(1, 1) else "variable_graph_metric_root_mass_not_one"


def _order_graph(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "evaluable" or value.get("schema_version") != PAIR_SCHEMA or value.get("action_order") not in {"own_first", "opponent_first"}:
        return "variable_graph_order_graph_invalid"
    order_probability = _fraction(value.get("order_conditional_probability"))
    conditional_mass = _fraction(value.get("conditional_terminal_probability_mass"))
    weighted = _fraction(value.get("order_weighted_terminal_probability_mass"))
    if order_probability <= 0 or conditional_mass != Fraction(1, 1) or weighted != order_probability:
        return "variable_graph_order_probability_composition_invalid"
    graph = value.get("first_action_graph")
    if not isinstance(graph, Mapping) or graph.get("status") != "evaluable" or _fraction(graph.get("terminal_probability_mass")) != Fraction(1, 1):
        return "variable_graph_first_action_graph_invalid"
    sources = _terminal_sources(graph)
    if isinstance(sources, str): return f"variable_graph_first_action_{sources}"
    source_by_id = {row["source_id"]: row for row in sources}
    transitions = value.get("terminal_transitions")
    if not isinstance(transitions, tuple) or len(transitions) != len(source_by_id): return "variable_graph_terminal_transition_set_invalid"
    parsed = []
    for transition in transitions:
        if not isinstance(transition, Mapping) or not isinstance(transition.get("first_terminal_source_id"), str): return "variable_graph_terminal_transition_invalid"
        source = source_by_id.get(transition["first_terminal_source_id"])
        if source is None or _fraction(transition.get("incoming_path_probability")) != source["path_probability"] or transition.get("first_terminal_consequences") != source["consequences"]:
            return "variable_graph_terminal_transition_source_mismatch"
        low_hp_error = _low_hp_type_hit(source.get("ordered_hit"))
        if low_hp_error is not None:
            return low_hp_error
        second = _validate_second(transition.get("second_action"))
        if isinstance(second, str): return second
        parsed.append({"first_terminal_source_id": transition["first_terminal_source_id"], "incoming_path_probability": source["path_probability"], "first_terminal_consequences": deepcopy(dict(source["consequences"])), "ordered_terminal_hit": deepcopy(source.get("ordered_hit")), "second_action": second})
    if len({row["first_terminal_source_id"] for row in parsed}) != len(parsed): return "variable_graph_duplicate_terminal_transition_source"
    if sum((row["incoming_path_probability"] for row in parsed), Fraction()) != Fraction(1, 1): return "variable_graph_terminal_transition_mass_not_one"
    first_actor = value.get("provenance", {}).get("first_actor") if isinstance(value.get("provenance"), Mapping) else None
    if (
        first_actor != graph.get("attacker")
        or (first_actor != base["own_actor"] and first_actor != base["opponent_actor"])
    ):
        return "variable_graph_first_actor_binding_mismatch"
    return {"action_order": value["action_order"], "order_conditional_probability": order_probability, "order_weighted_terminal_probability_mass": weighted, "first_actor": deepcopy(dict(first_actor)), "terminal_transitions": tuple(parsed), "first_action_graph": deepcopy(dict(graph))}


def _validate_second(value: Any) -> dict[str, Any] | str:
    if not isinstance(value, Mapping): return "variable_graph_second_action_missing"
    state = value.get("state")
    if state == "cancelled_due_to_faint":
        return deepcopy(dict(value)) if _fraction(value.get("conditional_probability")) == Fraction(1, 1) and value.get("reason") == "second_action_cancelled_due_to_faint" else "variable_graph_faint_cancellation_invalid"
    if state != "outcome_graph" or _fraction(value.get("conditional_probability")) != Fraction(1, 1) or not isinstance(value.get("outcomes"), tuple): return "variable_graph_second_action_outcome_graph_invalid"
    mass = Fraction()
    for outcome in value["outcomes"]:
        if not isinstance(outcome, Mapping) or _fraction(outcome.get("conditional_probability")) <= 0: return "variable_graph_second_action_outcome_invalid"
        mass += _fraction(outcome["conditional_probability"])
        if outcome.get("state") == "cancelled_due_to_paralysis":
            if outcome.get("reason") != "second_action_cancelled_due_to_paralysis": return "variable_graph_paralysis_cancellation_invalid"
        elif outcome.get("state") == "executed":
            leaves = outcome.get("second_action_terminal_leaves")
            if not isinstance(leaves, tuple) or not leaves or sum((_fraction(leaf.get("probability")) for leaf in leaves if isinstance(leaf, Mapping)), Fraction()) != Fraction(1, 1): return "variable_graph_second_action_leaf_set_invalid"
            for leaf in leaves:
                error = _low_hp_type_leaf(leaf)
                if error is not None:
                    return error
        else: return "variable_graph_second_action_outcome_state_invalid"
    return deepcopy(dict(value)) if mass == Fraction(1, 1) else "variable_graph_second_action_outcome_mass_not_one"


def _row(order: Mapping[str, Any], transition: Mapping[str, Any], state: str, leaf_id: Any, probability: Fraction, final: Mapping[str, Any]) -> dict[str, Any]:
    suffix = f"/{leaf_id}" if isinstance(leaf_id, str) else ""
    return {"pair_leaf_id": f"graph:{order['action_order']}/{transition['first_terminal_source_id']}/{state}{suffix}", "probability": probability, "final": deepcopy(dict(final)), "source_path_reference": {"action_order": order["action_order"], "first_terminal_source_id": transition["first_terminal_source_id"], "second_action_state": state, **({"second_action_leaf_id": leaf_id} if isinstance(leaf_id, str) else {})}}


def _final_from_consequences(consequences: Any, actor: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(consequences, Mapping): return "variable_graph_final_consequences_missing"
    if actor == base["own_actor"]: own, opponent = consequences.get("own_final_hp"), consequences.get("target_final_hp")
    elif actor == base["opponent_actor"]: own, opponent = consequences.get("target_final_hp"), consequences.get("own_final_hp")
    else: return "variable_graph_final_actor_identity_mismatch"
    if not _hp(own) or not _hp(opponent): return "variable_graph_final_hp_invalid"
    if isinstance(consequences.get("life_orb"), Mapping) and not _life_orb(consequences["life_orb"]):
        return "variable_graph_final_life_orb_consequence_invalid"
    if isinstance(consequences.get("contact_reactive_status"), Mapping) and not _contact_reactive_status(consequences["contact_reactive_status"]):
        return "variable_graph_final_contact_reactive_status_consequence_invalid"
    return {"own_final_hp": own, "opponent_final_hp": opponent, "own_fainted": own == 0, "opponent_fainted": opponent == 0, "supported_stage_consequence": deepcopy(consequences.get("deterministic_stage_effect")), "supported_secondary_consequence": deepcopy(consequences.get("secondary")), "contact_reactive_damage_consequence": deepcopy(consequences.get("contact_reactive_damage")), "contact_reactive_status_consequence": deepcopy(consequences.get("contact_reactive_status")), "life_orb_consequence": deepcopy(consequences.get("life_orb"))}


def _final_from_leaf(leaf: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(leaf, Mapping) or not isinstance(leaf.get("provenance"), Mapping): return "variable_graph_second_leaf_invalid"
    return _final_from_consequences(leaf.get("consequences"), leaf["provenance"].get("attacker"), base)


def _life_orb(value: Any) -> bool:
    authority = value.get("authority") if isinstance(value, Mapping) else None
    overlay = value.get("overlay") if isinstance(value, Mapping) else None
    modifier = authority.get("damage_modifier") if isinstance(authority, Mapping) else None
    recoil = authority.get("recoil") if isinstance(authority, Mapping) else None
    fraction = modifier.get("fraction") if isinstance(modifier, Mapping) else None
    if not isinstance(authority, Mapping) or authority.get("schema_version") != "runtime-d0-life-orb-immediate-authority-v1" or authority.get("status") != "resolved": return False
    if modifier.get("applies") is True and (modifier.get("modifier_q12") != 5324 or fraction != {"numerator": 5324, "denominator": 4096}): return False
    if modifier.get("applies") is False and (modifier.get("modifier_q12") != 4096 or fraction != {"numerator": 4096, "denominator": 4096}): return False
    if not isinstance(recoil, Mapping) or recoil.get("suppressed_by") not in {None, "sheer-force", "magic-guard"}: return False
    if not all(isinstance(recoil.get(key), int) and not isinstance(recoil.get(key), bool) and recoil[key] >= 0 for key in ("pre_hp", "max_hp", "recoil_damage", "post_hp")): return False
    if recoil["max_hp"] < 1 or recoil["post_hp"] != max(0, recoil["pre_hp"] - recoil["recoil_damage"]) or recoil.get("fainted") is not (recoil["post_hp"] == 0): return False
    if recoil.get("outcome") == "recoiled" and recoil["recoil_damage"] != max(1, recoil["max_hp"] // 10): return False
    if recoil.get("suppressed_by") is not None and (recoil["recoil_damage"] != 0 or recoil["post_hp"] != recoil["pre_hp"]): return False
    hp = overlay.get("hypothetical_hp_authority") if isinstance(overlay, Mapping) and overlay.get("schema_version") == "detached-life-orb-attacker-hp-overlay-v1" else None
    return isinstance(hp, Mapping) and hp.get("current_hp") == recoil["post_hp"] and hp.get("maximum_hp") == recoil["max_hp"]


def _contact_reactive_status(value: Any) -> bool:
    authority = value.get("authority") if isinstance(value, Mapping) else None
    overlay = value.get("overlay") if isinstance(value, Mapping) else None
    branch = value.get("branch") if isinstance(value, Mapping) else None
    if not isinstance(authority, Mapping) or authority.get("schema_version") != "runtime-d0-contact-reactive-status-authority-v1" or authority.get("status") != "resolved":
        return False
    if authority.get("outcome") != "applies":
        return overlay is None
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


def _low_hp_type_leaf(leaf: Any) -> str | None:
    ordered = leaf.get("ordered_hits") if isinstance(leaf, Mapping) else None
    if not isinstance(ordered, (tuple, list)):
        return None
    for hit in ordered:
        error = _low_hp_type_hit(hit)
        if error is not None:
            return error
    return None


def _low_hp_type_hit(hit: Any) -> str | None:
    evidence = hit.get("low_hp_type_ability") if isinstance(hit, Mapping) else None
    if evidence is None:
        return None
    source_hit = evidence.get("source_hit") if isinstance(evidence, Mapping) else None
    if (
        not validate_low_hp_type_offensive_ability_applicability(evidence)
        or not isinstance(source_hit, Mapping)
        or source_hit.get("hit_index") != hit.get("hit_index")
    ):
        return "variable_graph_low_hp_type_ability_consequence_invalid"
    return None


def _fraction(value: Any) -> Fraction:
    try: return Fraction(value["numerator"], value["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return Fraction(-1, 1)
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _serialize_order(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["order_conditional_probability"] = _fd(result["order_conditional_probability"]); result["order_weighted_terminal_probability_mass"] = _fd(result["order_weighted_terminal_probability_mass"])
    for transition in result["terminal_transitions"]: transition["incoming_path_probability"] = _fd(transition["incoming_path_probability"])
    return result
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": LEDGER_SCHEMA, "horizon": HORIZON, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
