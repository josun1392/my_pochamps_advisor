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
from llm.advisor_guts_status_attack_ability import (
    validate_guts_status_attack_ability_applicability,
)
from llm.advisor_full_hp_defender_ability import (
    validate_full_hp_defender_ability_applicability,
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
    """Traverse graph transition outcomes exactly without flattening stored graphs."""
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
            first_final = _final_from_consequences(
                transition.get("first_terminal_consequences"), first_actor, base,
            )
            second = transition.get("second_action")
            if incoming <= 0 or isinstance(first_final, str) or not isinstance(second, Mapping):
                return first_final if isinstance(first_final, str) else "variable_graph_metric_transition_invalid"
            state = second.get("state")
            if state in {
                "cancelled_due_to_faint", "executed_protection",
                "prevented_by_protection", "prevented_by_mat_block",
            }:
                if _fraction(second.get("conditional_probability")) != Fraction(1, 1):
                    return "variable_graph_metric_terminal_second_probability_invalid"
                rows.append(_row(order, transition, state, None, order_probability * incoming, first_final))
                continue
            if state != "outcome_graph" or _fraction(second.get("conditional_probability")) != Fraction(1, 1):
                return "variable_graph_metric_second_action_payload_invalid"
            outcomes = second.get("outcomes")
            if not isinstance(outcomes, tuple) or not outcomes:
                return "variable_graph_metric_second_action_outcomes_missing"
            outcome_mass = Fraction()
            for outcome in outcomes:
                conditional = _fraction(outcome.get("conditional_probability"))
                if conditional <= 0:
                    return "variable_graph_metric_second_outcome_probability_invalid"
                outcome_mass += conditional
                if outcome.get("state") in {
                    "cancelled_due_to_paralysis", "cancelled_due_to_sleep", "cancelled_due_to_freeze",
                }:
                    rows.append(_row(
                        order, transition, outcome["state"], None,
                        order_probability * incoming * conditional, first_final,
                    ))
                    continue
                if outcome.get("state") != "executed":
                    return "variable_graph_metric_second_outcome_invalid"
                graph = outcome.get("second_action_graph")
                leaves = outcome.get("second_action_terminal_leaves")
                if isinstance(graph, Mapping):
                    if leaves is not None:
                        return "variable_graph_metric_second_execution_representation_conflict"
                    sources = _terminal_sources(graph)
                    if isinstance(sources, str):
                        return f"variable_graph_metric_second_{sources}"
                    graph_mass = sum((source["path_probability"] for source in sources), Fraction())
                    if (
                        graph_mass != Fraction(1, 1)
                        or _fraction(outcome.get("second_action_terminal_probability_mass")) != graph_mass
                    ):
                        return "variable_graph_metric_second_graph_mass_invalid"
                    for source in sources:
                        final = _final_from_consequences(source["consequences"], graph.get("attacker"), base)
                        if isinstance(final, str):
                            return final
                        rows.append(_row(
                            order, transition, "executed_graph", source["source_id"],
                            order_probability * incoming * conditional * source["path_probability"], final,
                        ))
                    continue
                if not isinstance(leaves, tuple) or not leaves:
                    return "variable_graph_metric_second_execution_payload_missing"
                leaf_mass = sum(
                    (_fraction(leaf.get("probability")) for leaf in leaves if isinstance(leaf, Mapping)),
                    Fraction(),
                )
                if (
                    leaf_mass != Fraction(1, 1)
                    or _fraction(outcome.get("second_action_terminal_probability_mass")) != leaf_mass
                ):
                    return "variable_graph_metric_second_leaf_mass_invalid"
                pivots = {
                    row.get("leaf_id"): row.get("pivot_transition")
                    for row in outcome.get("second_action_pivot_transitions", ())
                    if isinstance(row, Mapping) and isinstance(row.get("leaf_id"), str)
                }
                for leaf in leaves:
                    final = _final_from_leaf(leaf, base, pivots.get(leaf.get("leaf_id")))
                    if isinstance(final, str):
                        return final
                    rows.append(_row(
                        order, transition, "executed", leaf.get("leaf_id"),
                        order_probability * incoming * conditional * _fraction(leaf["probability"]), final,
                    ))
            if outcome_mass != Fraction(1, 1):
                return "variable_graph_metric_second_outcome_mass_not_one"
    mass = sum((row["probability"] for row in rows), Fraction())
    return tuple(rows) if mass == Fraction(1, 1) else "variable_graph_metric_root_mass_not_one"

def _order_graph(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if (
        not isinstance(value, Mapping)
        or value.get("status") != "evaluable"
        or value.get("schema_version") != PAIR_SCHEMA
        or value.get("action_order") not in {"own_first", "opponent_first"}
    ):
        return "variable_graph_order_graph_invalid"
    order_probability = _fraction(value.get("order_conditional_probability"))
    conditional_mass = _fraction(value.get("conditional_terminal_probability_mass"))
    weighted = _fraction(value.get("order_weighted_terminal_probability_mass"))
    if order_probability <= 0 or conditional_mass != Fraction(1, 1) or weighted != order_probability:
        return "variable_graph_order_probability_composition_invalid"

    provenance = value.get("provenance")
    first_actor = provenance.get("first_actor") if isinstance(provenance, Mapping) else None
    if first_actor != base["own_actor"] and first_actor != base["opponent_actor"]:
        return "variable_graph_first_actor_binding_mismatch"

    graph = value.get("first_action_graph")
    leaf_set = value.get("first_action_leaf_set")
    if isinstance(graph, Mapping) == isinstance(leaf_set, tuple):
        return "variable_graph_first_action_representation_invalid"

    if isinstance(graph, Mapping):
        if graph.get("status") != "evaluable" or _fraction(graph.get("terminal_probability_mass")) != Fraction(1, 1):
            return "variable_graph_first_action_graph_invalid"
        if graph.get("attacker") != first_actor:
            return "variable_graph_first_actor_binding_mismatch"
        for entry in (
            *graph.get("terminal_leaf_nodes", ()),
            *graph.get("terminal_leaf_edges", ()),
            *graph.get("terminal_leaf_roots", ()),
        ):
            if isinstance(entry, Mapping) and (
                "ability_item_steal" in entry
                or "ability_item_steal" in entry.get("terminal_consequences", {})
                or "ability_item_steal" in entry.get("consequences", {})
            ):
                return "variable_graph_ability_steal_outside_terminal_adapter"
        sources = _terminal_sources(graph)
        if isinstance(sources, str):
            return f"variable_graph_first_action_{sources}"
        source_by_id = {row["source_id"]: row for row in sources}
        representation = "graph"
    else:
        if not leaf_set:
            return "variable_graph_first_action_leaf_set_missing"
        source_by_id: dict[str, dict[str, Any]] = {}
        total = Fraction()
        for leaf in leaf_set:
            if (
                not isinstance(leaf, Mapping)
                or not isinstance(leaf.get("leaf_id"), str)
                or not isinstance(leaf.get("provenance"), Mapping)
                or leaf["provenance"].get("attacker") != first_actor
            ):
                return "variable_graph_first_action_leaf_invalid"
            probability = _fraction(leaf.get("probability"))
            if probability <= 0 or not isinstance(leaf.get("consequences"), Mapping):
                return "variable_graph_first_action_leaf_invalid"
            source_id = f"leaf:{leaf['leaf_id']}"
            if source_id in source_by_id:
                return "variable_graph_first_action_leaf_duplicate"
            source_by_id[source_id] = {
                "source_id": source_id,
                "path_probability": probability,
                "consequences": deepcopy(dict(leaf["consequences"])),
                "ordered_hit": None,
                "native_terminal": None,
                "terminal_leaf": deepcopy(dict(leaf)),
            }
            total += probability
        if total != Fraction(1, 1):
            return "variable_graph_first_action_leaf_mass_not_one"
        representation = "leaf_set"

    transitions = value.get("terminal_transitions")
    if not isinstance(transitions, tuple) or len(transitions) != len(source_by_id):
        return "variable_graph_terminal_transition_set_invalid"
    parsed = []
    for transition in transitions:
        if not isinstance(transition, Mapping) or not isinstance(transition.get("first_terminal_source_id"), str):
            return "variable_graph_terminal_transition_invalid"
        source = source_by_id.get(transition["first_terminal_source_id"])
        consequences = transition.get("first_terminal_consequences")
        if source is None or not isinstance(consequences, Mapping):
            return "variable_graph_terminal_consequences_invalid"
        native_consequences = (
            {k: v for k, v in consequences.items() if k != "ability_item_steal"}
            if representation == "graph"
            else consequences
        )
        if (
            _fraction(transition.get("incoming_path_probability")) != source["path_probability"]
            or native_consequences != source["consequences"]
        ):
            return "variable_graph_terminal_transition_source_mismatch"
        if representation == "leaf_set" and transition.get("first_terminal_leaf") != source["terminal_leaf"]:
            return "variable_graph_first_terminal_leaf_mismatch"

        effect = transition.get("ability_item_steal_terminal_effect")
        if representation == "graph" and (effect is not None or "ability_item_steal" in consequences):
            from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
            from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import _synthetic_terminal_leaf
            from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata
            if not isinstance(effect, Mapping) or not isinstance(source.get("native_terminal"), Mapping):
                return "variable_graph_steal_nonterminal"
            leaf = _synthetic_terminal_leaf(first_graph=graph, source=source)
            landed = source["consequences"].get("landed_hit_count", 1 if source.get("ordered_hit") else 0)
            leaf["hit_state"] = "hit" if landed else "miss"
            contact = canonical_move_contact_metadata(graph["move_id"])
            leaf["consequences"]["contact"] = (
                "successful_contact_eligible" if contact.get("contact_state") == "contact" else "successful_non_contact"
            ) if landed and contact.get("status") == "resolved" else "not_applicable"
            leaf["consequences"]["ability_item_steal"] = consequences.get("ability_item_steal")
            leaf["provenance"]["ability_item_steal_completion_authority"] = effect.get("effect_authority")
            error = validate_ability_item_steal_leaf(
                leaf, envelope=effect, native_terminal=source["native_terminal"], pair_base=base, first_action=True,
            )
            if error is not None:
                return error
        if representation == "graph":
            low_hp_error = _low_hp_type_hit(source.get("ordered_hit"))
            if low_hp_error is not None:
                return low_hp_error
            guts_error = _guts_status_attack_hit(source.get("ordered_hit"))
            if guts_error is not None:
                return guts_error

        second = _validate_second(transition.get("second_action"))
        if isinstance(second, str):
            return second
        parsed.append({
            "first_terminal_source_id": transition["first_terminal_source_id"],
            "incoming_path_probability": source["path_probability"],
            "first_terminal_consequences": deepcopy(dict(consequences)),
            **({"first_terminal_leaf": deepcopy(source["terminal_leaf"])} if representation == "leaf_set" else {}),
            "ability_item_steal_terminal_effect": deepcopy(effect),
            "ordered_terminal_hit": deepcopy(source.get("ordered_hit")),
            **({"pivot_transition": deepcopy(transition.get("pivot_transition"))} if transition.get("pivot_transition") is not None else {}),
            "second_action": second,
        })

    if len({row["first_terminal_source_id"] for row in parsed}) != len(parsed):
        return "variable_graph_duplicate_terminal_transition_source"
    if sum((row["incoming_path_probability"] for row in parsed), Fraction()) != Fraction(1, 1):
        return "variable_graph_terminal_transition_mass_not_one"
    result = {
        "action_order": value["action_order"],
        "order_conditional_probability": order_probability,
        "order_weighted_terminal_probability_mass": weighted,
        "first_actor": deepcopy(dict(first_actor)),
        "terminal_transitions": tuple(parsed),
        "first_action_representation": representation,
    }
    if representation == "graph":
        result["first_action_graph"] = deepcopy(dict(graph))
    else:
        result["first_action_leaf_set"] = deepcopy(leaf_set)
    return result


def _validate_second(value: Any) -> dict[str, Any] | str:
    if not isinstance(value, Mapping):
        return "variable_graph_second_action_missing"
    state = value.get("state")
    terminal_states = {
        "cancelled_due_to_faint",
        "executed_protection",
        "prevented_by_protection",
        "prevented_by_mat_block",
    }
    if state in terminal_states:
        if _fraction(value.get("conditional_probability")) != Fraction(1, 1):
            return "variable_graph_terminal_second_action_probability_invalid"
        if value.get("reason") != state and state != "cancelled_due_to_faint":
            return "variable_graph_terminal_second_action_reason_invalid"
        if state == "cancelled_due_to_faint" and value.get("reason") != "second_action_cancelled_due_to_faint":
            return "variable_graph_faint_cancellation_invalid"
        return deepcopy(dict(value))
    if (
        state != "outcome_graph"
        or _fraction(value.get("conditional_probability")) != Fraction(1, 1)
        or not isinstance(value.get("outcomes"), tuple)
        or not value["outcomes"]
    ):
        return "variable_graph_second_action_outcome_graph_invalid"

    mass = Fraction()
    for outcome in value["outcomes"]:
        if not isinstance(outcome, Mapping):
            return "variable_graph_second_action_outcome_invalid"
        conditional = _fraction(outcome.get("conditional_probability"))
        if conditional <= 0:
            return "variable_graph_second_action_outcome_invalid"
        mass += conditional
        if outcome.get("state") in {
            "cancelled_due_to_paralysis", "cancelled_due_to_sleep", "cancelled_due_to_freeze",
        }:
            continue
        if outcome.get("state") != "executed":
            return "variable_graph_second_action_outcome_state_invalid"
        graph = outcome.get("second_action_graph")
        leaves = outcome.get("second_action_terminal_leaves")
        if isinstance(graph, Mapping):
            if leaves is not None or graph.get("status") != "evaluable":
                return "variable_graph_second_action_graph_invalid"
            sources = _terminal_sources(graph)
            if isinstance(sources, str):
                return f"variable_graph_second_action_{sources}"
            graph_mass = sum((row["path_probability"] for row in sources), Fraction())
            if (
                graph_mass != Fraction(1, 1)
                or _fraction(outcome.get("second_action_terminal_probability_mass")) != graph_mass
            ):
                return "variable_graph_second_action_graph_mass_invalid"
            for source in sources:
                error = _low_hp_type_hit(source.get("ordered_hit"))
                if error is not None:
                    return error
                error = _guts_status_attack_hit(source.get("ordered_hit"))
                if error is not None:
                    return error
            continue
        if not isinstance(leaves, tuple) or not leaves:
            return "variable_graph_second_action_leaf_set_invalid"
        leaf_mass = sum(
            (_fraction(leaf.get("probability")) for leaf in leaves if isinstance(leaf, Mapping)),
            Fraction(),
        )
        if (
            leaf_mass != Fraction(1, 1)
            or _fraction(outcome.get("second_action_terminal_probability_mass")) != leaf_mass
        ):
            return "variable_graph_second_action_leaf_set_invalid"
        for leaf in leaves:
            from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
            error = validate_ability_item_steal_leaf(leaf)
            if error is not None:
                return error
            error = _low_hp_type_leaf(leaf)
            if error is not None:
                return error
            error = _guts_status_attack_leaf(leaf)
            if error is not None:
                return error
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


def _final_from_leaf(
    leaf: Any, base: Mapping[str, Any], pivot_transition: Mapping[str, Any] | None = None,
) -> dict[str, Any] | str:
    if not isinstance(leaf, Mapping) or not isinstance(leaf.get("provenance"), Mapping):
        return "variable_graph_second_leaf_invalid"
    final = _final_from_consequences(
        leaf.get("consequences"), leaf["provenance"].get("attacker"), base,
    )
    if isinstance(final, str) or not isinstance(pivot_transition, Mapping):
        return final
    incoming = pivot_transition.get("resulting_active_owner")
    authority = pivot_transition.get("pivot_authority")
    if not isinstance(incoming, Mapping) or not isinstance(authority, Mapping):
        return "variable_graph_second_pivot_transition_invalid"
    hp = incoming.get("current_hp")
    if not _hp(hp):
        return "variable_graph_second_pivot_incoming_hp_invalid"
    side = authority.get("attacker", {}).get("side")
    if side == "self":
        final["own_final_hp"] = hp
        final["own_fainted"] = hp == 0
    elif side == "opponent":
        final["opponent_final_hp"] = hp
        final["opponent_fainted"] = hp == 0
    else:
        return "variable_graph_second_pivot_actor_invalid"
    final["pivot_transition"] = deepcopy(dict(pivot_transition))
    return final


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
    expected = {
        "sleep": {"numerator": 11, "denominator": 100},
        "paralysis": {"numerator": 1, "denominator": 10},
        "poison": {"numerator": 9, "denominator": 100},
        "none": {"numerator": 7, "denominator": 10},
    }
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


def _low_hp_type_leaf(leaf: Any) -> str | None:
    ordered = leaf.get("ordered_hits") if isinstance(leaf, Mapping) else None
    if not isinstance(ordered, (tuple, list)):
        return None
    for hit in ordered:
        error = _low_hp_type_hit(hit)
        if error is not None:
            return error
    return None


def _guts_status_attack_leaf(leaf: Any) -> str | None:
    ordered = leaf.get("ordered_hits") if isinstance(leaf, Mapping) else None
    if not isinstance(ordered, (tuple, list)):
        return None
    for hit in ordered:
        error = _guts_status_attack_hit(hit)
        if error is not None:
            return error
        error = _full_hp_defender_ability_hit(hit)
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


def _guts_status_attack_hit(hit: Any) -> str | None:
    evidence = hit.get("guts_status_attack_ability") if isinstance(hit, Mapping) else None
    if evidence is None:
        return None
    source_hit = evidence.get("source_hit") if isinstance(evidence, Mapping) else None
    if (
        not validate_guts_status_attack_ability_applicability(evidence)
        or (source_hit is not None and source_hit.get("hit_index") != hit.get("hit_index"))
    ):
        return "variable_graph_guts_status_attack_ability_consequence_invalid"
    return None


def _full_hp_defender_ability_hit(hit: Any) -> str | None:
    evidence = hit.get("full_hp_defender_ability") if isinstance(hit, Mapping) else None
    if evidence is None:
        return None
    source_hit = evidence.get("source_hit") if isinstance(evidence, Mapping) else None
    if (
        not validate_full_hp_defender_ability_applicability(evidence)
        or not isinstance(source_hit, Mapping)
        or source_hit.get("hit_index") != hit.get("hit_index")
        or evidence.get("defender_current_hp") != hit.get("pre_hp")
        or evidence.get("defender_max_hp") != hit.get("target_max_hp")
    ):
        return "variable_graph_full_hp_defender_ability_consequence_invalid"
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
