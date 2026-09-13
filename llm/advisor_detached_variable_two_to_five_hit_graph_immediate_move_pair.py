"""Graph-preserving immediate pairs whose first action is an ordinary 2--5-hit move.

This is intentionally not the legacy flat pair schema: a variable multi-hit
first action can have an impractical number of terminal paths.  The result
keeps that first-action graph immutable and attaches second-action outcomes to
each exact terminal graph source without enumerating Cartesian pair leaves.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_intermediate_paralysis_second_action_authority import (
    consume_detached_sleep_freeze_execution_for_second_action,
)
from llm.advisor_detached_intermediate_predictive_authority import (
    detached_intermediate_builder_inputs,
    freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_predictive_intermediate_state import (
    freeze_detached_actor_neutral_root_predictive_authority,
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_detached_variable_two_to_five_hit_per_hit_predictive_materialization import (
    materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves,
)
from llm.advisor_detached_population_bomb_per_hit_accuracy_predictive_graph_materialization import materialize_detached_population_bomb_per_hit_accuracy_predictive_graph
from llm.advisor_detached_escalating_three_hit_predictive_graph_materialization import materialize_detached_escalating_three_hit_predictive_graph
from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority
from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import freeze_runtime_d0_escalating_three_hit_execution_authority
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_runtime_d0_contact_reactive_damage_authority import contact_reactive_damage_relevance
from llm.advisor_runtime_d0_contact_reactive_status_authority import contact_reactive_status_relevance
from llm.advisor_immediate_move_vs_move_action_pair import (
    _analytic_order_authority,
    _attack_ledger,
    _atomic_item_swap_pair_leaf,
    _base,
    _direct_heal_leaf,
    _disable_pair_leaf,
    _encore_pair_leaf,
    _fainted,
    _focus_sash_authorities_by_order,
    _is_atomic_item_swap_metadata,
    _is_direct_heal_metadata,
    _materialize_protection_response_pair,
    _metadata_for_inputs,
    _opponent_metadata,
    _orders,
    _pivot_entry_authority,
    _pivot_replacement_authority,
    _protection_leaf,
    _resolved_protection,
    _status,
    _sturdy_authorities_by_order,
    _taunt_pair_leaf,
)
from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import (
    freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority,
)
from llm.advisor_runtime_d0_pivot_replacement_authority import (
    freeze_runtime_d0_pivot_replacement_authority,
)
from llm.advisor_damage_pivot_continuation import freeze_damage_pivot_continuation_authority
from llm.advisor_detached_atomic_item_swap_status_materializer import materialize_detached_atomic_item_swap_status
from llm.advisor_detached_disable_action_restriction import (
    disable_restriction_failure_leaf,
    materialize_disable_execution_gate,
)
from llm.advisor_detached_encore_action_restriction import materialize_encore_forced_execution_action
from llm.advisor_detached_pivot_switch_transition import materialize_detached_damage_pivot_switch
from llm.advisor_detached_sitrus_berry_immediate_consumption import (
    materialize_detached_sitrus_berry_immediate_consumption,
)
from llm.advisor_hypothetical_protection_effects import (
    canonical_protection_metadata,
    prevent_supported_direct_damage,
)
from advisor.canonical_silk_trap_reactive_protection import (
    canonical_kings_shield_metadata,
    canonical_obstruct_metadata,
    canonical_silk_trap_metadata,
)
from advisor.canonical_spiky_shield_reactive_damage import canonical_spiky_shield_reactive_damage_metadata
from advisor.canonical_baneful_bunker_reactive_poison import canonical_baneful_bunker_reactive_poison_metadata
from advisor.canonical_burning_bulwark_reactive_burn import canonical_burning_bulwark_reactive_burn_metadata
from advisor.canonical_quick_guard_protection import canonical_quick_guard_protection_metadata
from llm.advisor_runtime_d0_sturdy_survival_authority import (
    bind_sturdy_survival_authority_through_actor_neutral_root,
    freeze_runtime_d0_sturdy_survival_authority,
)
from llm.advisor_runtime_d0_focus_sash_survival_authority import (
    bind_focus_sash_survival_authority_through_actor_neutral_root,
    freeze_runtime_d0_focus_sash_survival_authority,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_strategy_d0,
    resolve_runtime_d0_selectable_move_metadata_authority,
)


SCHEMA_VERSION = "detached-variable-two-to-five-hit-graph-immediate-move-pair-v1"
HORIZON = "immediate_action_pair"
_VARIABLE_MOVES = frozenset({"bullet-seed", "rock-blast"})
_ESCALATING_MOVES = frozenset({"triple-axel", "triple-kick"})
_GRAPH_MOVES = _VARIABLE_MOVES | frozenset({"population-bomb"}) | _ESCALATING_MOVES
_STATUSES = {"incomplete", "unsupported", "rejected"}


def materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
    quick_claw_action_order_authority: Mapping[str, Any] | None = None,
    first_action_sturdy_survival_authority: Mapping[str, Any] | None = None,
    first_action_sturdy_survival_authorities_by_order: Mapping[str, Mapping[str, Any]] | None = None,
    first_action_focus_sash_survival_authority: Mapping[str, Any] | None = None,
    first_action_focus_sash_survival_authorities_by_order: Mapping[str, Mapping[str, Any]] | None = None,
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    direct_heal_execution_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    atomic_item_swap_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    taunt_application_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    encore_application_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    disable_application_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    opponent_protection_success_authority: Mapping[str, Any] | None = None,
    incoming_contact_authority: Mapping[str, Any] | None = None,
    silk_trap_reactive_interaction_authority: Mapping[str, Any] | None = None,
    kings_shield_reactive_interaction_authority: Mapping[str, Any] | None = None,
    obstruct_reactive_interaction_authority: Mapping[str, Any] | None = None,
    spiky_shield_reactive_damage_authority: Mapping[str, Any] | None = None,
    baneful_bunker_reactive_poison_authority: Mapping[str, Any] | None = None,
    burning_bulwark_reactive_burn_authority: Mapping[str, Any] | None = None,
    quick_guard_priority_applicability_authority: Mapping[str, Any] | None = None,
    mat_block_direct_damage_applicability_authority: Mapping[str, Any] | None = None,
    pivot_replacement_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    pivot_entry_authorities: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compose one exact pair whenever either selected move uses a native hit graph."""
    base = _base(strategy_d0, own_action, opponent_action)
    if base is None:
        return _result("rejected", "invalid_variable_graph_pair_request", {})
    orders = _orders(action_order_authority, base, quick_claw_action_order_authority)
    if isinstance(orders, tuple):
        return _result(*orders, base)
    focus_by_order = _focus_sash_authorities_by_order(
        first_action_focus_sash_survival_authority,
        first_action_focus_sash_survival_authorities_by_order,
    )
    if isinstance(focus_by_order, tuple):
        return _result(*focus_by_order, base)
    sturdy_by_order = _sturdy_authorities_by_order(
        first_action_sturdy_survival_authority,
        first_action_sturdy_survival_authorities_by_order,
    )
    if isinstance(sturdy_by_order, tuple):
        return _result(*sturdy_by_order, base)
    own_metadata = resolve_runtime_d0_selectable_move_metadata_authority(
        strategy_d0=strategy_d0, action=own_action,
    )
    opponent_metadata = _opponent_metadata(opponent_action, base)
    if own_metadata.get("status") != "resolved":
        return _result(_status(own_metadata), own_metadata.get("reason", "own_move_metadata_unavailable"), base)
    if isinstance(opponent_metadata, tuple):
        return _result(*opponent_metadata, base)
    if not (_is_graph_metadata(own_metadata) or _is_graph_metadata(opponent_metadata)):
        return _result("unsupported", "graph_pair_requires_at_least_one_supported_graph_move", base)

    extension_authorities = {
        "direct_heal_execution_authorities": direct_heal_execution_authorities,
        "atomic_item_swap_status_execution_authorities": atomic_item_swap_status_execution_authorities,
        "taunt_application_authorities": taunt_application_authorities,
        "encore_application_authorities": encore_application_authorities,
        "disable_application_authorities": disable_application_authorities,
        "opponent_protection_success_authority": opponent_protection_success_authority,
        "incoming_contact_authority": incoming_contact_authority,
        "silk_trap_reactive_interaction_authority": silk_trap_reactive_interaction_authority,
        "kings_shield_reactive_interaction_authority": kings_shield_reactive_interaction_authority,
        "obstruct_reactive_interaction_authority": obstruct_reactive_interaction_authority,
        "spiky_shield_reactive_damage_authority": spiky_shield_reactive_damage_authority,
        "baneful_bunker_reactive_poison_authority": baneful_bunker_reactive_poison_authority,
        "burning_bulwark_reactive_burn_authority": burning_bulwark_reactive_burn_authority,
        "quick_guard_priority_applicability_authority": quick_guard_priority_applicability_authority,
        "mat_block_direct_damage_applicability_authority": mat_block_direct_damage_applicability_authority,
        "pivot_replacement_authorities": pivot_replacement_authorities,
        "pivot_entry_authorities": pivot_entry_authorities,
    }
    order_graphs: list[dict[str, Any]] = []
    total_mass = Fraction()
    for plan in orders:
        graph = _materialize_order_graph(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            base=base,
            own_action=own_action,
            opponent_action=opponent_action,
            own_metadata=own_metadata,
            opponent_metadata=opponent_metadata,
            order_plan=plan,
            action_order_authority=action_order_authority,
            first_action_sturdy_survival_authority=sturdy_by_order.get(
                plan["order"], first_action_sturdy_survival_authority,
            ),
            first_action_focus_sash_survival_authority=focus_by_order.get(
                plan["order"], first_action_focus_sash_survival_authority,
            ),
            pending_status_execution_authorities=pending_status_execution_authorities,
            extension_authorities=extension_authorities,
        )
        if graph.get("status") != "evaluable":
            return _result(
                _status(graph),
                graph.get("reason", "variable_graph_order_unavailable"),
                base,
                order_graphs=tuple(order_graphs),
            )
        order_graphs.append(graph)
        total_mass += _fraction(graph["order_weighted_terminal_probability_mass"])
    if total_mass != Fraction(1, 1):
        return _result(
            "rejected",
            "variable_graph_pair_probability_mass_not_one",
            base,
            terminal_probability_mass=_fd(total_mass),
        )
    return {
        "status": "evaluable",
        "schema_version": SCHEMA_VERSION,
        "horizon": HORIZON,
        **base,
        "action_order": deepcopy(dict(action_order_authority)),
        "conditional_on": "opponent_selected_exact_known_usable_move",
        "order_graphs": tuple(order_graphs),
        "terminal_probability_mass": _fd(total_mass),
        "terminal_leaf_representation": "exact_side_neutral_native_action_graph_composition",
        "aggregation": "none_preserve_native_graph_and_path_identity",
        "legacy_flat_pair_ledger_compatibility": "not_applicable_requires_graph_ledger_normalizer",
        "provenance": "strict_detached_side_neutral_graph_immediate_pair_v1",
    }


def _materialize_order_graph(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    base: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    own_metadata: Mapping[str, Any], opponent_metadata: Mapping[str, Any],
    order_plan: Mapping[str, Any], action_order_authority: Mapping[str, Any],
    first_action_sturdy_survival_authority: Mapping[str, Any] | None,
    first_action_focus_sash_survival_authority: Mapping[str, Any] | None,
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None,
    extension_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    order = order_plan["order"]
    first_is_own = order == "own_first"
    first_actor = base["own_actor"] if first_is_own else base["opponent_actor"]
    first_target = base["opponent_actor"] if first_is_own else base["own_actor"]
    first_action = own_action if first_is_own else opponent_action
    first_metadata = own_metadata if first_is_own else opponent_metadata
    second_actor = base["opponent_actor"] if first_is_own else base["own_actor"]
    second_target = first_actor
    second_action = opponent_action if first_is_own else own_action
    second_metadata = opponent_metadata if first_is_own else own_metadata

    first_d0, first_snapshot, root = strategy_d0, runtime_snapshot, None
    if not first_is_own:
        root = freeze_detached_actor_neutral_root_predictive_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            opponent_action=opponent_action,
        )
        if root.get("status") != "resolved":
            return _result(
                _status(root),
                root.get("reason", "opponent_root_predictive_authority_unavailable"),
                {},
            )
        first_d0, first_snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
        if isinstance(first_action_focus_sash_survival_authority, Mapping):
            first_action_focus_sash_survival_authority = bind_focus_sash_survival_authority_through_actor_neutral_root(
                strategy_d0=strategy_d0,
                root_predictive_authority=root,
                focus_sash_survival_authority=first_action_focus_sash_survival_authority,
            )
            if first_action_focus_sash_survival_authority.get("status") in {"incomplete", "unsupported", "rejected"}:
                return _result(
                    _status(first_action_focus_sash_survival_authority),
                    first_action_focus_sash_survival_authority.get(
                        "reason", "focus_sash_actor_neutral_root_binding_unavailable",
                    ),
                    {},
                )
        if isinstance(first_action_sturdy_survival_authority, Mapping):
            first_action_sturdy_survival_authority = bind_sturdy_survival_authority_through_actor_neutral_root(
                strategy_d0=strategy_d0,
                root_predictive_authority=root,
                sturdy_survival_authority=first_action_sturdy_survival_authority,
            )
            if first_action_sturdy_survival_authority.get("status") in {"incomplete", "unsupported", "rejected"}:
                return _result(
                    _status(first_action_sturdy_survival_authority),
                    first_action_sturdy_survival_authority.get(
                        "reason", "sturdy_actor_neutral_root_binding_unavailable",
                    ),
                    {},
                )

    if _is_graph_metadata(first_metadata):
        first = _variable_action_graph(
            strategy_d0=first_d0,
            runtime_snapshot=first_snapshot,
            actor=first_actor,
            target=first_target,
            metadata_authority=first_metadata,
            sturdy_survival_authority=first_action_sturdy_survival_authority,
            focus_sash_survival_authority=first_action_focus_sash_survival_authority,
        )
        if first.get("status") != "evaluable":
            return _result(
                _status(first),
                first.get("reason", "variable_first_action_graph_unavailable"),
                {},
            )
        sources = _terminal_sources(first)
        if isinstance(sources, str):
            return _result("rejected", sources, {})
        transitions, conditional_mass = _attach_second_actions(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            base=base,
            first_graph=first,
            terminal_sources=sources,
            first_actor=first_actor,
            first_target=first_target,
            second_actor=second_actor,
            second_target=second_target,
            second_action=second_action,
            second_metadata=second_metadata,
            root_predictive_authority=root,
            pending_status_execution_authorities=pending_status_execution_authorities,
            extension_authorities=extension_authorities,
            order_plan=order_plan,
            action_order_authority=action_order_authority,
        )
        if isinstance(transitions, Mapping):
            return transitions
        if conditional_mass != Fraction(1, 1):
            return _result("rejected", "variable_graph_terminal_transition_probability_mass_not_one", {})
        return _order_payload(
            order_plan=order_plan,
            first_actor=first_actor,
            second_actor=second_actor,
            first_action_graph=first,
            terminal_transitions=transitions,
            root=root,
        )

    if not _is_graph_metadata(second_metadata):
        return _result("unsupported", "selected_order_contains_no_supported_graph_action", {})

    return _materialize_graph_second_order(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        first_d0=first_d0,
        first_snapshot=first_snapshot,
        root=root,
        base=base,
        first_actor=first_actor,
        first_target=first_target,
        first_action=first_action,
        first_metadata=first_metadata,
        second_actor=second_actor,
        second_target=second_target,
        second_action=second_action,
        second_metadata=second_metadata,
        order_plan=order_plan,
        action_order_authority=action_order_authority,
        first_action_sturdy_survival_authority=first_action_sturdy_survival_authority,
        first_action_focus_sash_survival_authority=first_action_focus_sash_survival_authority,
        pending_status_execution_authorities=pending_status_execution_authorities,
        extension_authorities=extension_authorities,
    )


def _order_payload(
    *, order_plan: Mapping[str, Any], first_actor: Mapping[str, Any],
    second_actor: Mapping[str, Any], terminal_transitions: list[dict[str, Any]],
    root: Mapping[str, Any] | None,
    first_action_graph: Mapping[str, Any] | None = None,
    first_action_leaf_set: tuple[Mapping[str, Any], ...] | None = None,
) -> dict[str, Any]:
    order_probability = order_plan["probability"]
    payload = {
        "status": "evaluable",
        "schema_version": SCHEMA_VERSION,
        "action_order": order_plan["order"],
        "order_conditional_probability": _fd(order_probability),
        **(
            {"action_order_branch": deepcopy(dict(order_plan["source_branch"]))}
            if isinstance(order_plan.get("source_branch"), Mapping)
            else {}
        ),
        "terminal_transitions": tuple(transitions for transitions in terminal_transitions),
        "conditional_terminal_probability_mass": _fd(Fraction(1, 1)),
        "order_weighted_terminal_probability_mass": _fd(order_probability),
        "provenance": {
            "root_predictive_authority": _root_summary(root),
            "first_actor": deepcopy(dict(first_actor)),
            "second_actor": deepcopy(dict(second_actor)),
        },
    }
    if isinstance(first_action_graph, Mapping):
        payload["first_action_graph"] = deepcopy(dict(first_action_graph))
    if isinstance(first_action_leaf_set, tuple):
        payload["first_action_leaf_set"] = deepcopy(first_action_leaf_set)
    return payload


def _is_graph_metadata(authority: Any) -> bool:
    metadata = _metadata_for_inputs(authority, None)
    return isinstance(metadata, Mapping) and metadata.get("move_id") in _GRAPH_MOVES


def _variable_action_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata_authority: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None, focus_sash_survival_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    metadata = _metadata_for_inputs(metadata_authority, None)
    opponent_side = "opponent" if isinstance(actor, Mapping) and actor.get("side") == "self" else "self"
    if metadata is None or metadata.get("move_id") not in _GRAPH_MOVES or actor != strategy_d0.get("decision_owner") or target != strategy_d0.get("active_owners", {}).get(opponent_side):
        return _result("unsupported", "variable_multi_hit_move_not_first_action_or_not_supported", {})
    action_id = f"attack:{metadata['move_id']}"
    projection = {
        "status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1",
        "candidate_id": action_id, "move_id": metadata["move_id"], "metadata": deepcopy(dict(metadata)),
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "active_attacker": deepcopy(dict(strategy_d0["decision_owner"])),
        "provenance": "strict_detached_pair_metadata_to_variable_multi_hit_d0_selection_view_v1",
    }
    action = {"action_id": action_id, "action_type": "attack", "identity": metadata["move_id"], "move_metadata_authority": projection}
    relevance = contact_reactive_damage_relevance(runtime_snapshot=runtime_snapshot, defender=target)
    if relevance.get("status") != "resolved":
        return _result(_status(relevance), relevance.get("reason", "variable_multi_hit_contact_reactive_relevance_unknown"), {})
    status_relevance = contact_reactive_status_relevance(runtime_snapshot=runtime_snapshot, defender=target)
    if status_relevance.get("status") != "resolved":
        return _result(_status(status_relevance), status_relevance.get("reason", "variable_multi_hit_contact_reactive_status_relevance_unknown"), {})
    contact = None
    if relevance.get("relevant") is True or status_relevance.get("relevant") is True:
        contact = freeze_runtime_d0_canonical_contact_classification_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, attacker=actor, target=target)
        if contact.get("status") != "resolved":
            return _result(_status(contact), contact.get("reason", "variable_multi_hit_contact_authority_unavailable"), {})
    if metadata["move_id"] == "population-bomb":
        execution = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action)
    elif metadata["move_id"] in _ESCALATING_MOVES:
        execution = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action)
    else:
        execution = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action)
    if execution.get("status") != "resolved":
        return _result(_status(execution), execution.get("reason", "variable_multi_hit_execution_authority_unavailable"), {})
    graph = (materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority, contact_reactive_contact_authority=contact,
    ) if metadata["move_id"] == "population-bomb" else materialize_detached_escalating_three_hit_predictive_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority, contact_reactive_contact_authority=contact,
    ) if metadata["move_id"] in _ESCALATING_MOVES else materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority, contact_reactive_contact_authority=contact,
    ))
    return graph if graph.get("status") == "evaluable" else _result(_status(graph), graph.get("reason", "variable_multi_hit_path_graph_unavailable"), {})


def _terminal_sources(graph: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | str:
    roots, nodes, edges = graph.get("terminal_leaf_roots"), graph.get("terminal_leaf_nodes"), graph.get("terminal_leaf_edges")
    if not isinstance(roots, tuple) or not isinstance(nodes, tuple) or not isinstance(edges, tuple):
        return "variable_graph_payload_invalid"
    node_ids = {node.get("node_id") for node in nodes if isinstance(node, Mapping) and isinstance(node.get("node_id"), str)}
    if len(node_ids) != len(nodes):
        return "variable_graph_node_identity_invalid"
    outgoing: dict[str, list[Mapping[str, Any]]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        population = graph.get("move_id") == "population-bomb"
        escalating = graph.get("move_id") in _ESCALATING_MOVES
        hit = edge.get("ordered_hit") if isinstance(edge, Mapping) else None
        if population and isinstance(edge, Mapping): hit = _mapping(_mapping(edge.get("attempt_outcome")).get("ordered_hit")) or None
        if escalating and isinstance(edge, Mapping): hit = _mapping(_mapping(edge.get("hit_outcome")).get("ordered_hit")) or None
        if not isinstance(edge, Mapping) or edge.get("from_node_id") not in node_ids or _fraction(edge.get("conditional_probability")) <= 0 or (not population and not escalating and not isinstance(hit, Mapping)):
            return "variable_graph_edge_invalid"
        if edge.get("terminal") is True:
            if "terminal_consequences" not in edge:
                return "variable_graph_terminal_edge_consequence_missing"
        elif edge.get("to_node_id") not in node_ids:
            return "variable_graph_nonterminal_edge_target_invalid"
        outgoing[edge["from_node_id"]].append(edge)
    incoming = {node_id: Fraction() for node_id in node_ids}
    result: list[dict[str, Any]] = []
    for root in roots:
        if not isinstance(root, Mapping) or _fraction(root.get("probability")) <= 0 or not isinstance(root.get("root_id"), str):
            return "variable_graph_root_invalid"
        probability = _fraction(root["probability"])
        if root.get("terminal") is True:
            consequences = root.get("consequences")
            if not isinstance(consequences, Mapping):
                return "variable_graph_terminal_root_consequence_missing"
            result.append({"source_id": f"root:{root['root_id']}", "path_probability": probability, "consequences": deepcopy(dict(consequences)), "ordered_hit": None})
        elif root.get("node_id") in incoming:
            incoming[root["node_id"]] += probability
        else:
            return "variable_graph_root_node_invalid"
    # Nodes are emitted in increasing completed-hit order by the materializer;
    # verify that each graph edge advances that order before one exact DP pass.
    node_by_id = {node["node_id"]: node for node in nodes}
    for node in nodes:
        source_probability = incoming[node["node_id"]]
        for edge in outgoing[node["node_id"]]:
            probability = source_probability * _fraction(edge["conditional_probability"])
            if edge.get("terminal") is True:
                ordered = edge.get("ordered_hit") if isinstance(edge.get("ordered_hit"), Mapping) else _mapping(_mapping(edge.get("attempt_outcome")).get("ordered_hit")) or _mapping(_mapping(edge.get("hit_outcome")).get("ordered_hit")) or None
                result.append({"native_terminal": deepcopy(dict(edge)), "source_id": f"edge:{edge['edge_id']}", "path_probability": probability, "consequences": deepcopy(dict(edge["terminal_consequences"])), "ordered_hit": deepcopy(dict(ordered)) if isinstance(ordered, Mapping) else None})
            else:
                target = node_by_id[edge["to_node_id"]]
                advancing = target.get("attempt_index") == node.get("attempt_index", -1) + 1 if population else target.get("hit_index") == node.get("hit_index", -1) + 1 if escalating else target.get("completed_hit_count") == node.get("completed_hit_count", -1) + 1
                if not advancing:
                    return "variable_graph_cycle_or_nonadvancing_edge"
                incoming[edge["to_node_id"]] += probability
    mass = sum((row["path_probability"] for row in result), Fraction())
    return result if mass == Fraction(1, 1) else "variable_graph_terminal_path_mass_not_one"


def _materialize_graph_second_order(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    first_d0: Mapping[str, Any], first_snapshot: Mapping[str, Any],
    root: Mapping[str, Any] | None, base: Mapping[str, Any],
    first_actor: Mapping[str, Any], first_target: Mapping[str, Any],
    first_action: Mapping[str, Any], first_metadata: Mapping[str, Any],
    second_actor: Mapping[str, Any], second_target: Mapping[str, Any],
    second_action: Mapping[str, Any], second_metadata: Mapping[str, Any],
    order_plan: Mapping[str, Any], action_order_authority: Mapping[str, Any],
    first_action_sturdy_survival_authority: Mapping[str, Any] | None,
    first_action_focus_sash_survival_authority: Mapping[str, Any] | None,
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None,
    extension_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    protection = _graph_second_protection_first(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        base=base,
        first_actor=first_actor,
        first_action=first_action,
        first_metadata=first_metadata,
        second_metadata=second_metadata,
        order_plan=order_plan,
        action_order_authority=action_order_authority,
        extension_authorities=extension_authorities,
    )
    if isinstance(protection, Mapping):
        if protection.get("status") != "continue_graph":
            return deepcopy(dict(protection))
        if protection.get("graph_second_from_unchanged_state") is True:
            return _materialize_unchanged_graph_second_after_protection(
                strategy_d0=strategy_d0,
                runtime_snapshot=runtime_snapshot,
                first_actor=first_actor,
                second_actor=second_actor,
                second_target=second_target,
                second_action=second_action,
                second_metadata=second_metadata,
                first_leaf=protection["first_action_leaf_set"][0],
                order_plan=order_plan,
                root=root,
            )
        first_leaves = protection["first_action_leaf_set"]
    else:
        first = _flat_first_action_ledger(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            execution_d0=first_d0,
            execution_snapshot=first_snapshot,
            base=base,
            actor=first_actor,
            target=first_target,
            action=first_action,
            metadata_authority=first_metadata,
            order_plan=order_plan,
            action_order_authority=action_order_authority,
            sturdy_survival_authority=first_action_sturdy_survival_authority,
            focus_sash_survival_authority=first_action_focus_sash_survival_authority,
            extension_authorities=extension_authorities,
        )
        if first.get("status") != "evaluable" or not isinstance(first.get("terminal_leaves"), tuple):
            return _result(
                _status(first),
                first.get("reason", "graph_second_first_action_unavailable"),
                {},
            )
        first_leaves = first["terminal_leaves"]

    if not first_leaves:
        return _result("rejected", "graph_second_first_action_leaf_set_empty", {})
    leaf_mass = sum((_fraction(leaf.get("probability")) for leaf in first_leaves), Fraction())
    if leaf_mass != Fraction(1, 1):
        return _result("rejected", "graph_second_first_action_leaf_mass_not_one", {})
    if _is_direct_heal_metadata(first_metadata.get("metadata")):
        if len(first_leaves) != 1:
            return _result("rejected", "graph_second_direct_heal_leaf_set_invalid", {})
        return _materialize_graph_second_after_direct_heal(
            runtime_snapshot=runtime_snapshot,
            first_actor=first_actor,
            second_actor=second_actor,
            second_target=second_target,
            second_action=second_action,
            second_metadata=second_metadata,
            first_leaf=first_leaves[0],
            order_plan=order_plan,
            root=root,
        )
    if first_metadata.get("metadata", {}).get("move_id") in {"taunt", "encore", "disable"}:
        if len(first_leaves) != 1:
            return _result("rejected", "graph_second_status_special_leaf_set_invalid", {})
        return _materialize_graph_second_after_status_special(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            first_actor=first_actor,
            second_actor=second_actor,
            second_target=second_target,
            first_action=first_action,
            first_metadata=first_metadata,
            second_action=second_action,
            second_metadata=second_metadata,
            first_leaf=first_leaves[0],
            order_plan=order_plan,
            root=root,
            extension_authorities=extension_authorities,
        )

    transitions: list[dict[str, Any]] = []
    materialized_first_leaves: list[dict[str, Any]] = []
    for raw_leaf in first_leaves:
        leaf = deepcopy(dict(raw_leaf))
        if isinstance(root, Mapping):
            leaf = _bind_leaf_through_actor_neutral_root(leaf, root)
            if isinstance(leaf, str):
                return _result("rejected", leaf, {})
        if first_metadata.get("metadata", {}).get("category") in {"physical", "special"}:
            sitrus = materialize_detached_sitrus_berry_immediate_consumption(
                strategy_d0=first_d0,
                runtime_snapshot=first_snapshot,
                terminal_leaf=leaf,
                holder=first_target,
                move_metadata=first_metadata.get("metadata", {}),
            )
            if sitrus.get("status") != "resolved":
                return _result(
                    _status(sitrus),
                    sitrus.get("reason", "graph_second_first_action_sitrus_unavailable"),
                    {},
                )
            leaf = sitrus["leaf"]
        intermediate = materialize_detached_predictive_intermediate_state(
            strategy_d0=strategy_d0,
            terminal_leaf=leaf,
            root_predictive_authority=root,
        )
        if intermediate.get("status") != "resolved":
            return _result(
                _status(intermediate),
                intermediate.get("reason", "graph_second_intermediate_state_unavailable"),
                {},
                first_terminal_source=leaf.get("leaf_id"),
            )
        materialized_first_leaves.append(deepcopy(dict(leaf)))
        transition = {
            "first_terminal_source_id": f"leaf:{leaf['leaf_id']}",
            "incoming_path_probability": deepcopy(leaf["probability"]),
            "first_terminal_consequences": deepcopy(dict(leaf["consequences"])),
            "first_terminal_leaf": deepcopy(dict(leaf)),
            "intermediate_state_id": intermediate.get("first_action", {}).get("leaf_id"),
            "ordered_terminal_hit": None,
        }
        if _fainted(intermediate, second_actor) or _fainted(intermediate, first_actor):
            transition["second_action"] = _cancelled_second(second_actor)
            transitions.append(transition)
            continue

        effective_action = second_action
        effective_metadata = second_metadata
        override = _status_special_pending_override(
            strategy_d0=strategy_d0,
            first_action=first_action,
            first_metadata=first_metadata,
            second_action=second_action,
            second_metadata=second_metadata,
            second_actor=second_actor,
            second_target=second_target,
            extension_authorities=extension_authorities,
        )
        if isinstance(override, Mapping) and override.get("terminal_leaf") is not None:
            transition["second_action"] = {
                "state": "outcome_graph",
                "actor": deepcopy(dict(second_actor)),
                "conditional_probability": _fd(Fraction(1, 1)),
                "outcomes": ({
                    "state": "executed",
                    "conditional_probability": _fd(Fraction(1, 1)),
                    "second_action_terminal_leaves": (deepcopy(dict(override["terminal_leaf"])),),
                    "second_action_terminal_probability_mass": _fd(Fraction(1, 1)),
                    **({"forced_execution_action": deepcopy(override.get("forced_execution_action"))} if override.get("forced_execution_action") is not None else {}),
                },),
            }
            transitions.append(transition)
            continue
        if isinstance(override, Mapping) and override.get("action") is not None:
            effective_action = override["action"]
            effective_metadata = override["metadata"]
        elif isinstance(override, str):
            return _result("incomplete", override, {})

        pivot = _apply_first_action_pivot_if_needed(
            strategy_d0=first_d0,
            runtime_snapshot=first_snapshot,
            original_strategy_d0=strategy_d0,
            intermediate=intermediate,
            first_action=first_action,
            first_metadata=first_metadata,
            first_actor=first_actor,
            second_actor=second_actor,
            leaf=leaf,
            extension_authorities=extension_authorities,
        )
        if isinstance(pivot, Mapping) and pivot.get("status") in {"incomplete", "unsupported", "rejected"}:
            return _result(
                _status(pivot),
                pivot.get("reason", "graph_second_pivot_transition_unavailable"),
                {},
            )
        if isinstance(pivot, Mapping) and pivot.get("status") == "resolved":
            post_snapshot = pivot.get("runtime_snapshot")
            incoming = pivot.get("resulting_active_owner")
            if not isinstance(post_snapshot, Mapping) or not isinstance(incoming, Mapping):
                return _result("rejected", "graph_second_pivot_result_invalid", {})
            post_d0 = freeze_runtime_strategy_d0(
                runtime_snapshot=post_snapshot,
                decision_owner=second_actor,
            )
            if post_d0.get("status") != "resolved":
                return _result(
                    _status(post_d0),
                    post_d0.get("reason", "graph_second_post_pivot_d0_unavailable"),
                    {},
                )
            graph = _execute_graph_in_context(
                strategy_d0=post_d0,
                runtime_snapshot=post_snapshot,
                actor=second_actor,
                target=_owner_identity_for_graph(incoming),
                action=effective_action,
                metadata_authority=effective_metadata,
            )
            if graph.get("status") != "evaluable":
                return _result(_status(graph), graph.get("reason", "graph_second_after_pivot_unavailable"), {})
            transition["pivot_transition"] = deepcopy(dict(pivot))
            transition["second_action"] = _executed_graph_second(second_actor, graph, override)
            transitions.append(transition)
            continue

        outcomes = _execute_second_from_intermediate(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            intermediate=intermediate,
            actor=second_actor,
            target=second_target,
            action=effective_action,
            metadata_authority=effective_metadata,
            pending_status_execution_authorities=pending_status_execution_authorities,
            extension_authorities=extension_authorities,
            source_leaf=leaf,
            override=override if isinstance(override, Mapping) else None,
        )
        if isinstance(outcomes, Mapping) and outcomes.get("status") in {"incomplete", "unsupported", "rejected"}:
            return _result(_status(outcomes), outcomes.get("reason", "graph_second_execution_unavailable"), {})
        transition["second_action"] = outcomes
        transitions.append(transition)

    conditional_mass = sum(
        (_fraction(row["incoming_path_probability"]) for row in transitions),
        Fraction(),
    )
    if conditional_mass != Fraction(1, 1):
        return _result("rejected", "graph_second_transition_mass_not_one", {})
    return _order_payload(
        order_plan=order_plan,
        first_actor=first_actor,
        second_actor=second_actor,
        first_action_leaf_set=tuple(materialized_first_leaves),
        terminal_transitions=transitions,
        root=root,
    )


def _graph_second_protection_first(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    base: Mapping[str, Any], first_actor: Mapping[str, Any],
    first_action: Mapping[str, Any], first_metadata: Mapping[str, Any],
    second_metadata: Mapping[str, Any], order_plan: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
    extension_authorities: Mapping[str, Any],
) -> dict[str, Any] | None:
    move_id = first_metadata.get("metadata", {}).get("move_id")
    if canonical_quick_guard_protection_metadata(move_id) is not None:
        authority = extension_authorities.get("quick_guard_priority_applicability_authority")
        if first_actor != base["opponent_actor"]:
            return _result("incomplete", "graph_quick_guard_self_side_authority_unavailable", {})
        if not isinstance(authority, Mapping):
            return _result("incomplete", "quick_guard_priority_applicability_authority_missing", {})
        if authority.get("status") != "resolved":
            return _result(_status(authority), authority.get("reason", "quick_guard_applicability_unavailable"), {})
        leaf = _protection_leaf(base, strategy_d0, {"move_id": "quick-guard"})
        if leaf is None:
            return _result("incomplete", "quick_guard_protection_leaf_unavailable", {})
        leaf["consequences"]["quick_guard_priority_applicability"] = deepcopy(dict(authority))
        if authority.get("outcome") == "applies":
            return _blocked_graph_second_order(
                base=base, first_actor=first_actor, first_leaf=leaf,
                order_plan=order_plan, state="prevented_by_protection",
            )
        if authority.get("outcome") == "not_applicable":
            return {
                "status": "continue_graph",
                "first_action_leaf_set": (leaf,),
                "graph_second_from_unchanged_state": True,
            }
        return _result("rejected", "quick_guard_priority_applicability_outcome_invalid", {})

    if move_id == "mat-block":
        authority = extension_authorities.get("mat_block_direct_damage_applicability_authority")
        if first_actor != base["opponent_actor"]:
            return _result("incomplete", "graph_mat_block_self_side_authority_unavailable", {})
        if not isinstance(authority, Mapping):
            return _result("incomplete", "mat_block_direct_damage_applicability_authority_missing", {})
        if authority.get("status") != "resolved":
            return _result(_status(authority), authority.get("reason", "mat_block_applicability_unavailable"), {})
        leaf = _protection_leaf(base, strategy_d0, {"move_id": "mat-block"})
        if leaf is None:
            return _result("incomplete", "mat_block_protection_leaf_unavailable", {})
        leaf["consequences"]["mat_block_direct_damage_applicability"] = deepcopy(dict(authority))
        if authority.get("outcome") == "applies":
            return _blocked_graph_second_order(
                base=base, first_actor=first_actor, first_leaf=leaf,
                order_plan=order_plan, state="prevented_by_mat_block",
            )
        if authority.get("outcome") == "not_applicable":
            return {
                "status": "continue_graph",
                "first_action_leaf_set": (leaf,),
                "graph_second_from_unchanged_state": True,
            }
        return _result("rejected", "mat_block_direct_damage_applicability_outcome_invalid", {})

    if not _is_protection_family(first_metadata.get("metadata")):
        return None
    if first_actor != base["opponent_actor"]:
        return _result("incomplete", "graph_self_side_protection_composition_not_owned_by_ordinary_pair", {})
    if second_metadata.get("metadata", {}).get("protection_bypass") is True:
        leaf = _protection_leaf(base, strategy_d0, first_metadata["metadata"])
        if leaf is None:
            return _result("incomplete", "graph_bypassed_protection_leaf_unavailable", {})
        return {
            "status": "continue_graph",
            "first_action_leaf_set": (leaf,),
            "graph_second_from_unchanged_state": True,
        }

    pair = _materialize_protection_response_pair(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        base=base,
        own_action={
            "action_id": base["own_action_id"],
            "action_type": "attack",
            "identity": second_metadata.get("metadata", {}).get("move_id"),
        },
        opponent_action=first_action,
        own_meta=second_metadata,
        opponent_meta=first_metadata,
        orders=[order_plan],
        action_order_authority=action_order_authority,
        opponent_protection_success_authority=extension_authorities.get("opponent_protection_success_authority"),
        incoming_contact_authority=extension_authorities.get("incoming_contact_authority"),
        silk_trap_reactive_interaction_authority=extension_authorities.get("silk_trap_reactive_interaction_authority"),
        kings_shield_reactive_interaction_authority=extension_authorities.get("kings_shield_reactive_interaction_authority"),
        obstruct_reactive_interaction_authority=extension_authorities.get("obstruct_reactive_interaction_authority"),
        spiky_shield_reactive_damage_authority=extension_authorities.get("spiky_shield_reactive_damage_authority"),
        baneful_bunker_reactive_poison_authority=extension_authorities.get("baneful_bunker_reactive_poison_authority"),
        burning_bulwark_reactive_burn_authority=extension_authorities.get("burning_bulwark_reactive_burn_authority"),
    )
    if pair.get("status") != "evaluable":
        return _result(_status(pair), pair.get("reason", "graph_protection_first_unavailable"), {})
    branches = pair.get("terminal_branches")
    if not isinstance(branches, tuple) or len(branches) != 1:
        return _result("rejected", "graph_protection_first_branch_shape_invalid", {})
    branch = branches[0]
    second = branch.get("second_action")
    if not isinstance(second, Mapping) or second.get("state") != "prevented_by_protection":
        return _result("rejected", "graph_protection_first_did_not_prevent_graph", {})
    return _blocked_graph_second_order(
        base=base,
        first_actor=first_actor,
        first_leaf=branch["first_action_leaf"],
        order_plan=order_plan,
        state="prevented_by_protection",
    )





def _materialize_graph_second_after_status_special(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    first_actor: Mapping[str, Any], second_actor: Mapping[str, Any],
    second_target: Mapping[str, Any], first_action: Mapping[str, Any],
    first_metadata: Mapping[str, Any], second_action: Mapping[str, Any],
    second_metadata: Mapping[str, Any], first_leaf: Mapping[str, Any],
    order_plan: Mapping[str, Any], root: Mapping[str, Any] | None,
    extension_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    override = _status_special_pending_override(
        strategy_d0=strategy_d0,
        first_action=first_action,
        first_metadata=first_metadata,
        second_action=second_action,
        second_metadata=second_metadata,
        second_actor=second_actor,
        second_target=second_target,
        extension_authorities=extension_authorities,
    )
    if isinstance(override, str):
        return _result("incomplete", override, {})
    transition = {
        "first_terminal_source_id": f"leaf:{first_leaf['leaf_id']}",
        "incoming_path_probability": deepcopy(first_leaf["probability"]),
        "first_terminal_consequences": deepcopy(dict(first_leaf["consequences"])),
        "first_terminal_leaf": deepcopy(dict(first_leaf)),
        "intermediate_state_id": None,
        "ordered_terminal_hit": None,
    }
    if isinstance(override, Mapping) and override.get("terminal_leaf") is not None:
        transition["second_action"] = {
            "state": "outcome_graph",
            "actor": deepcopy(dict(second_actor)),
            "conditional_probability": _fd(Fraction(1, 1)),
            "outcomes": ({
                "state": "executed",
                "conditional_probability": _fd(Fraction(1, 1)),
                "second_action_terminal_leaves": (deepcopy(dict(override["terminal_leaf"])),),
                "second_action_terminal_probability_mass": _fd(Fraction(1, 1)),
            },),
        }
        return _order_payload(
            order_plan=order_plan,
            first_actor=first_actor,
            second_actor=second_actor,
            first_action_leaf_set=(deepcopy(dict(first_leaf)),),
            terminal_transitions=[transition],
            root=root,
        )
    effective_action = (
        override["action"]
        if isinstance(override, Mapping) and isinstance(override.get("action"), Mapping)
        else second_action
    )
    effective_metadata = (
        override["metadata"]
        if isinstance(override, Mapping) and isinstance(override.get("metadata"), Mapping)
        else second_metadata
    )
    executed = _execute_action_in_context(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        actor=second_actor,
        target=second_target,
        action=effective_action,
        metadata_authority=effective_metadata,
        extension_authorities=extension_authorities,
        source_leaf=first_leaf,
        original_strategy_d0=strategy_d0,
        original_runtime_snapshot=runtime_snapshot,
    )
    if executed.get("status") != "evaluable":
        return _result(
            _status(executed),
            executed.get("reason", "graph_second_after_status_special_unavailable"),
            {},
        )
    if isinstance(executed.get("native_graph"), Mapping):
        second = _executed_graph_second(second_actor, executed["native_graph"], override if isinstance(override, Mapping) else None)
    else:
        outcome = {
            "state": "executed",
            "conditional_probability": _fd(Fraction(1, 1)),
            "second_action_terminal_leaves": deepcopy(executed["terminal_leaves"]),
            "second_action_terminal_probability_mass": deepcopy(executed.get("terminal_probability_mass", _fd(Fraction(1, 1)))),
        }
        if isinstance(override, Mapping) and override.get("forced_execution_action") is not None:
            outcome["forced_execution_action"] = deepcopy(override["forced_execution_action"])
        second = {
            "state": "outcome_graph",
            "actor": deepcopy(dict(second_actor)),
            "conditional_probability": _fd(Fraction(1, 1)),
            "outcomes": (outcome,),
        }
    transition["second_action"] = second
    return _order_payload(
        order_plan=order_plan,
        first_actor=first_actor,
        second_actor=second_actor,
        first_action_leaf_set=(deepcopy(dict(first_leaf)),),
        terminal_transitions=[transition],
        root=root,
    )


def _status_special_second_from_intermediate(
    *, strategy_d0: Mapping[str, Any], intermediate: Mapping[str, Any],
    actor: Mapping[str, Any], target: Mapping[str, Any], action: Mapping[str, Any],
    move_id: str, extension_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "taunt": ("taunt_application_authorities", _taunt_pair_leaf),
        "encore": ("encore_application_authorities", _encore_pair_leaf),
        "disable": ("disable_application_authorities", _disable_pair_leaf),
    }
    field, builder = fields[move_id]
    authorities = extension_authorities.get(field)
    application = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
    if not isinstance(application, Mapping):
        return _result("incomplete", f"{move_id}_application_authority_missing", {})
    if (
        application.get("status") != "resolved"
        or application.get("actor") != actor
        or application.get("target") != target
        or application.get("action_id") != action.get("action_id")
    ):
        return _result(
            _status(application) if isinstance(application, Mapping) else "rejected",
            f"{move_id}_application_authority_binding_mismatch",
            {},
        )
    leaf = builder(application, strategy_d0)
    if isinstance(leaf, str):
        return _result("incomplete", leaf, {})
    active = intermediate.get("active", {})
    actor_state = active.get(actor.get("side")) if isinstance(active, Mapping) else None
    target_state = active.get(target.get("side")) if isinstance(active, Mapping) else None
    actor_hp = actor_state.get("hypothetical_hp", {}).get("value") if isinstance(actor_state, Mapping) else None
    target_hp = target_state.get("hypothetical_hp", {}).get("value") if isinstance(target_state, Mapping) else None
    if not _hp_value(actor_hp) or not _hp_value(target_hp):
        return _result("incomplete", f"{move_id}_path_local_hp_unknown", {})
    leaf = deepcopy(dict(leaf))
    leaf["consequences"]["own_final_hp"] = actor_hp
    leaf["consequences"]["target_final_hp"] = target_hp
    leaf["consequences"]["self_fainted"] = actor_hp == 0
    leaf["consequences"]["target_ko"] = target_hp == 0
    return {
        "status": "evaluable",
        "terminal_leaves": (leaf,),
        "terminal_probability_mass": _fd(Fraction(1, 1)),
    }

def _materialize_graph_second_after_direct_heal(
    *, runtime_snapshot: Mapping[str, Any], first_actor: Mapping[str, Any],
    second_actor: Mapping[str, Any], second_target: Mapping[str, Any],
    second_action: Mapping[str, Any], second_metadata: Mapping[str, Any],
    first_leaf: Mapping[str, Any], order_plan: Mapping[str, Any],
    root: Mapping[str, Any] | None,
) -> dict[str, Any]:
    heal = first_leaf.get("consequences", {}).get("direct_heal")
    post_hp = heal.get("post_hp") if isinstance(heal, Mapping) else None
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not _hp_value(post_hp) or not isinstance(state, Mapping):
        return _result("rejected", "graph_second_direct_heal_state_invalid", {})
    synthetic = deepcopy(dict(state))
    side_state = synthetic.get(f"{first_actor.get('side')}_side")
    pokemon = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    row = pokemon.get(first_actor.get("slot_index")) if isinstance(pokemon, Mapping) else None
    if not isinstance(row, Mapping) or row.get("pokemon_id") != first_actor.get("pokemon_id"):
        return _result("rejected", "graph_second_direct_heal_actor_identity_mismatch", {})
    row["current_hp"] = post_hp
    row["fainted"] = post_hp == 0
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": synthetic.get("session_id"),
        "state": synthetic,
        "state_fingerprint": state_fingerprint(synthetic),
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=second_actor)
    if d0.get("status") != "resolved":
        return _result(
            _status(d0),
            d0.get("reason", "graph_second_direct_heal_predictive_d0_unavailable"),
            {},
        )
    graph = _execute_graph_in_context(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        actor=second_actor,
        target=second_target,
        action=second_action,
        metadata_authority=second_metadata,
    )
    if graph.get("status") != "evaluable":
        return _result(
            _status(graph),
            graph.get("reason", "graph_second_after_direct_heal_unavailable"),
            {},
        )
    transition = {
        "first_terminal_source_id": f"leaf:{first_leaf['leaf_id']}",
        "incoming_path_probability": deepcopy(first_leaf["probability"]),
        "first_terminal_consequences": deepcopy(dict(first_leaf["consequences"])),
        "first_terminal_leaf": deepcopy(dict(first_leaf)),
        "intermediate_state_id": None,
        "ordered_terminal_hit": None,
        "second_action": _executed_graph_second(second_actor, graph, None),
    }
    return _order_payload(
        order_plan=order_plan,
        first_actor=first_actor,
        second_actor=second_actor,
        first_action_leaf_set=(deepcopy(dict(first_leaf)),),
        terminal_transitions=[transition],
        root=root,
    )

def _materialize_unchanged_graph_second_after_protection(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    first_actor: Mapping[str, Any], second_actor: Mapping[str, Any],
    second_target: Mapping[str, Any], second_action: Mapping[str, Any],
    second_metadata: Mapping[str, Any], first_leaf: Mapping[str, Any],
    order_plan: Mapping[str, Any], root: Mapping[str, Any] | None,
) -> dict[str, Any]:
    graph = _execute_graph_in_context(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        actor=second_actor,
        target=second_target,
        action=second_action,
        metadata_authority=second_metadata,
    )
    if graph.get("status") != "evaluable":
        return _result(
            _status(graph),
            graph.get("reason", "graph_second_after_nonapplicable_protection_unavailable"),
            {},
        )
    transition = {
        "first_terminal_source_id": f"leaf:{first_leaf['leaf_id']}",
        "incoming_path_probability": deepcopy(first_leaf["probability"]),
        "first_terminal_consequences": deepcopy(dict(first_leaf["consequences"])),
        "first_terminal_leaf": deepcopy(dict(first_leaf)),
        "intermediate_state_id": None,
        "ordered_terminal_hit": None,
        "second_action": _executed_graph_second(second_actor, graph, None),
    }
    return _order_payload(
        order_plan=order_plan,
        first_actor=first_actor,
        second_actor=second_actor,
        first_action_leaf_set=(deepcopy(dict(first_leaf)),),
        terminal_transitions=[transition],
        root=root,
    )

def _blocked_graph_second_order(
    *, base: Mapping[str, Any], first_actor: Mapping[str, Any],
    first_leaf: Mapping[str, Any], order_plan: Mapping[str, Any], state: str,
) -> dict[str, Any]:
    transition = {
        "first_terminal_source_id": f"leaf:{first_leaf['leaf_id']}",
        "incoming_path_probability": deepcopy(first_leaf["probability"]),
        "first_terminal_consequences": deepcopy(dict(first_leaf["consequences"])),
        "first_terminal_leaf": deepcopy(dict(first_leaf)),
        "intermediate_state_id": None,
        "ordered_terminal_hit": None,
        "second_action": {
            "state": state,
            "actor": deepcopy(dict(base["own_actor"] if first_actor == base["opponent_actor"] else base["opponent_actor"])),
            "conditional_probability": _fd(Fraction(1, 1)),
            "reason": state,
        },
    }
    return _order_payload(
        order_plan=order_plan,
        first_actor=first_actor,
        second_actor=transition["second_action"]["actor"],
        first_action_leaf_set=(deepcopy(dict(first_leaf)),),
        terminal_transitions=[transition],
        root=None,
    )


def _flat_first_action_ledger(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    execution_d0: Mapping[str, Any], execution_snapshot: Mapping[str, Any],
    base: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any],
    action: Mapping[str, Any], metadata_authority: Mapping[str, Any],
    order_plan: Mapping[str, Any], action_order_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any] | None,
    focus_sash_survival_authority: Mapping[str, Any] | None,
    extension_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = metadata_authority.get("metadata", {})
    move_id = metadata.get("move_id")
    if _is_direct_heal_metadata(metadata):
        authorities = extension_authorities.get("direct_heal_execution_authorities")
        authority = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
        leaf = _direct_heal_leaf(
            authority, strategy_d0, runtime_snapshot, action, actor, target, None,
        )
        if isinstance(leaf, str):
            return _result("incomplete", leaf, {})
        return {"status": "evaluable", "terminal_leaves": (leaf,)}
    if _is_atomic_item_swap_metadata(metadata):
        authorities = extension_authorities.get("atomic_item_swap_status_execution_authorities")
        authority = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
        if not isinstance(authority, Mapping):
            return _result("incomplete", "atomic_item_swap_status_execution_authority_missing", {})
        materialized = materialize_detached_atomic_item_swap_status(execution_authority=authority)
        if materialized.get("status") != "resolved":
            return _result(_status(materialized), materialized.get("reason", "atomic_item_swap_materialization_unavailable"), {})
        leaf = _atomic_item_swap_pair_leaf(materialized, strategy_d0)
        if isinstance(leaf, str):
            return _result("rejected", leaf, {})
        return {"status": "evaluable", "terminal_leaves": (leaf,)}
    if move_id == "taunt":
        return _application_first_ledger(
            strategy_d0, action, actor, target,
            extension_authorities.get("taunt_application_authorities"),
            _taunt_pair_leaf, "taunt_application_authority_missing",
        )
    if move_id == "encore":
        return _application_first_ledger(
            strategy_d0, action, actor, target,
            extension_authorities.get("encore_application_authorities"),
            _encore_pair_leaf, "encore_application_authority_missing",
        )
    if move_id == "disable":
        return _application_first_ledger(
            strategy_d0, action, actor, target,
            extension_authorities.get("disable_application_authorities"),
            _disable_pair_leaf, "disable_application_authority_missing",
        )
    if metadata.get("category") not in {"physical", "special"}:
        return _result("incomplete", "graph_counterpart_status_family_not_bound", {})
    analytic = _analytic_order_authority(
        strategy_d0=execution_d0,
        actor=actor,
        target=target,
        base=base,
        plan=order_plan,
        source_action_order_authority=action_order_authority,
    ) if actor == base["own_actor"] else None
    return _attack_ledger(
        strategy_d0=execution_d0,
        runtime_snapshot=execution_snapshot,
        actor=actor,
        target=target,
        metadata_authority=metadata_authority,
        sturdy_survival_authority=sturdy_survival_authority,
        focus_sash_survival_authority=focus_sash_survival_authority,
        action=action,
        analytic_action_order_authority=analytic,
        action_order=order_plan["order"],
    )


def _application_first_ledger(
    strategy_d0: Mapping[str, Any], action: Mapping[str, Any],
    actor: Mapping[str, Any], target: Mapping[str, Any],
    authorities: Any, leaf_builder: Any, missing_reason: str,
) -> dict[str, Any]:
    authority = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
    if not isinstance(authority, Mapping):
        return _result("incomplete", missing_reason, {})
    if authority.get("status") != "resolved":
        return _result(_status(authority), authority.get("reason", missing_reason), {})
    if authority.get("actor") != actor or authority.get("target") != target or authority.get("action_id") != action.get("action_id"):
        return _result("rejected", f"{missing_reason}_binding_mismatch", {})
    leaf = leaf_builder(authority, strategy_d0)
    if isinstance(leaf, str):
        return _result("incomplete", leaf, {})
    return {"status": "evaluable", "terminal_leaves": (leaf,)}


def _status_special_pending_override(
    *, strategy_d0: Mapping[str, Any], first_action: Mapping[str, Any],
    first_metadata: Mapping[str, Any], second_action: Mapping[str, Any],
    second_metadata: Mapping[str, Any], second_actor: Mapping[str, Any],
    second_target: Mapping[str, Any], extension_authorities: Mapping[str, Any],
) -> Mapping[str, Any] | str | None:
    move_id = first_metadata.get("metadata", {}).get("move_id")
    if move_id == "encore":
        authorities = extension_authorities.get("encore_application_authorities")
        application = authorities.get(first_action.get("action_id")) if isinstance(authorities, Mapping) else None
        if not isinstance(application, Mapping):
            return "encore_application_authority_missing"
        if application.get("outcome") != "applicable":
            return None
        forced = materialize_encore_forced_execution_action(
            selected_action=second_action,
            actor=second_actor,
            encore_application=application,
        )
        if forced.get("status") != "resolved":
            return forced.get("reason", "encore_forced_execution_unavailable")
        forced_meta = {"status": "resolved", "metadata": deepcopy(dict(forced["execution_move_metadata"]))}
        forced_action = {
            **deepcopy(dict(second_action)),
            "action_id": forced["execution_action_id"],
            "move_id": forced["execution_move_id"],
            "identity": forced["execution_move_id"],
            "metadata_authority": forced_meta,
            "move_metadata_authority": forced_meta,
        }
        return {
            "action": forced_action,
            "metadata": forced_meta,
            "forced_execution_action": deepcopy(dict(forced)),
        }
    if move_id == "disable":
        authorities = extension_authorities.get("disable_application_authorities")
        application = authorities.get(first_action.get("action_id")) if isinstance(authorities, Mapping) else None
        if not isinstance(application, Mapping):
            return "disable_application_authority_missing"
        pending = {**deepcopy(dict(second_action)), "metadata_authority": deepcopy(dict(second_metadata))}
        gate = materialize_disable_execution_gate(
            selected_action=pending,
            actor=second_actor,
            same_branch_application=application,
        )
        if gate.get("status") != "resolved":
            return gate.get("reason", "disable_execution_gate_unavailable")
        if gate.get("execution_state") == "restricted_by_disable":
            failure = disable_restriction_failure_leaf(
                strategy_d0=strategy_d0,
                action=second_action,
                actor=second_actor,
                target=second_target,
                gate=gate,
            )
            if failure.get("status") != "evaluable" or not isinstance(failure.get("terminal_leaves"), tuple):
                return failure.get("reason", "disable_failure_leaf_unavailable")
            return {"terminal_leaf": failure["terminal_leaves"][0]}
    return None



def _pivot_selected_action_leaf(
    *, leaf: Mapping[str, Any], action: Mapping[str, Any],
    actor: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any] | str:
    if not isinstance(leaf, Mapping) or not isinstance(action, Mapping) or not isinstance(move_metadata, Mapping):
        return "pivot_selected_action_leaf_invalid"
    provenance = leaf.get("provenance")
    move_id = move_metadata.get("move_id")
    action_id = action.get("action_id")
    if (
        not isinstance(provenance, Mapping)
        or provenance.get("attacker") != actor
        or provenance.get("move_id") != move_id
        or not isinstance(action_id, str)
        or action_id not in {f"attack:{move_id}", f"opponent_attack:{move_id}"}
    ):
        return "pivot_selected_action_leaf_binding_mismatch"
    result = deepcopy(dict(leaf))
    result["candidate_id"] = action_id
    return result

def _apply_first_action_pivot_if_needed(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    original_strategy_d0: Mapping[str, Any], intermediate: Mapping[str, Any],
    first_action: Mapping[str, Any], first_metadata: Mapping[str, Any],
    first_actor: Mapping[str, Any], second_actor: Mapping[str, Any],
    leaf: Mapping[str, Any], extension_authorities: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if first_metadata.get("metadata", {}).get("move_id") not in {"u-turn", "volt-switch", "flip-turn"}:
        return None
    replacements = extension_authorities.get("pivot_replacement_authorities")
    entries = extension_authorities.get("pivot_entry_authorities")
    pivot_leaf = _pivot_selected_action_leaf(
        leaf=leaf, action=first_action, actor=first_actor,
        move_metadata=first_metadata["metadata"],
    )
    if isinstance(pivot_leaf, str):
        return {"status": "rejected", "reason": pivot_leaf}
    pivot = freeze_damage_pivot_continuation_authority(
        strategy_d0=strategy_d0,
        action=first_action,
        move_metadata=first_metadata["metadata"],
        attack_terminal_leaf=pivot_leaf,
        replacement_authority=_pivot_replacement_authority(replacements, leaf, first_action),
    )
    if pivot.get("status") != "applies":
        return pivot if pivot.get("status") in {"incomplete", "unsupported", "rejected"} else None
    entry = _pivot_entry_authority(entries, leaf, first_action)
    if not isinstance(entry, Mapping):
        return {"status": "incomplete", "reason": "pivot_switch_entry_authority_missing"}
    pivot_intermediate = materialize_detached_predictive_intermediate_state(
        strategy_d0=strategy_d0,
        terminal_leaf=leaf,
    )
    if pivot_intermediate.get("status") != "resolved":
        return pivot_intermediate
    pivot_metadata = _graph_metadata_authority_for_context(
        strategy_d0=strategy_d0,
        actor=first_actor,
        metadata=first_metadata["metadata"],
    )
    precursor = freeze_detached_intermediate_predictive_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        intermediate_state=pivot_intermediate,
        actor=first_actor,
        target=second_actor,
        move_metadata_authority=pivot_metadata,
    )
    if precursor.get("status") != "resolved":
        return precursor
    return materialize_detached_damage_pivot_switch(
        intermediate_authority=precursor,
        pivot_authority=pivot,
        entry_authority=entry,
    )


def _attach_second_actions(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    base: Mapping[str, Any], first_graph: Mapping[str, Any],
    terminal_sources: tuple[Mapping[str, Any], ...],
    first_actor: Mapping[str, Any], first_target: Mapping[str, Any],
    second_actor: Mapping[str, Any], second_target: Mapping[str, Any],
    second_action: Mapping[str, Any], second_metadata: Mapping[str, Any],
    root_predictive_authority: Mapping[str, Any] | None,
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None,
    extension_authorities: Mapping[str, Any], order_plan: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], Fraction] | tuple[dict[str, Any], None]:
    transitions: list[dict[str, Any]] = []
    mass = Fraction()
    second_cache: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source in terminal_sources:
        leaf = _synthetic_terminal_leaf(first_graph=first_graph, source=source)
        intermediate = materialize_detached_predictive_intermediate_state(
            strategy_d0=strategy_d0,
            terminal_leaf=leaf,
            root_predictive_authority=root_predictive_authority,
        )
        if intermediate.get("status") != "resolved":
            return _result(
                _status(intermediate),
                intermediate.get("reason", "variable_graph_intermediate_state_unavailable"),
                {},
                first_terminal_source=source["source_id"],
            ), None
        if source.get("native_terminal") is not None:
            from llm.advisor_detached_ability_item_steal_terminal import attach_ability_item_steal
            from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata
            landed = source["consequences"].get("landed_hit_count", 1 if source.get("ordered_hit") else 0)
            classification = canonical_move_contact_metadata(first_graph["move_id"])
            leaf["hit_state"] = "hit" if landed > 0 else "miss"
            leaf["consequences"]["contact"] = (
                "successful_contact_eligible"
                if classification.get("contact_state") == "contact"
                else "successful_non_contact"
            ) if landed > 0 and classification.get("status") == "resolved" else "not_applicable"
            family = {
                "population-bomb": "population_bomb",
                "triple-axel": "triple_axel",
                "triple-kick": "triple_kick",
            }.get(first_graph["move_id"], "variable_two_to_five_hit")
            effect_d0 = (
                root_predictive_authority["predictive_strategy_d0"]
                if isinstance(root_predictive_authority, Mapping)
                else strategy_d0
            )
            effect_state = materialize_detached_predictive_intermediate_state(
                strategy_d0=effect_d0, terminal_leaf=leaf,
            )
            status, leaf = attach_ability_item_steal(
                strategy_d0=effect_d0,
                runtime_snapshot=runtime_snapshot,
                leaf=leaf,
                intermediate=effect_state,
                family=family,
                graph=first_graph,
                terminal_edge=source["native_terminal"],
            )
            if status.get("status") != "resolved":
                return _result(
                    _status(status),
                    status.get("reason", "graph_ability_item_steal_unavailable"),
                    {},
                ), None
            intermediate = materialize_detached_predictive_intermediate_state(
                strategy_d0=strategy_d0,
                terminal_leaf=leaf,
                root_predictive_authority=root_predictive_authority,
            )
            if intermediate.get("status") != "resolved":
                return intermediate, None
        transition = {
            "first_terminal_source_id": source["source_id"],
            "incoming_path_probability": _fd(source["path_probability"]),
            "first_terminal_consequences": {
                **deepcopy(dict(source["consequences"])),
                **(
                    {"ability_item_steal": deepcopy(leaf["consequences"]["ability_item_steal"])}
                    if "ability_item_steal" in leaf["consequences"]
                    else {}
                ),
            },
            "ability_item_steal_terminal_effect": deepcopy(
                leaf["provenance"].get("ability_item_steal_terminal_effect"),
            ),
            "intermediate_state_id": intermediate.get("first_action", {}).get("leaf_id"),
            "ordered_terminal_hit": deepcopy(source.get("ordered_hit")),
        }
        if _fainted(intermediate, second_actor) or _fainted(intermediate, first_actor):
            transition["second_action"] = _cancelled_second(second_actor)
            transitions.append(transition)
            mass += source["path_probability"]
            continue

        if second_metadata.get("metadata", {}).get("move_id") in {"taunt", "encore", "disable"}:
            status_leaf = _status_special_second_from_intermediate(
                strategy_d0=strategy_d0,
                intermediate=intermediate,
                actor=second_actor,
                target=second_target,
                action=second_action,
                move_id=second_metadata["metadata"]["move_id"],
                extension_authorities=extension_authorities,
            )
            if status_leaf.get("status") != "evaluable":
                return _result(
                    _status(status_leaf),
                    status_leaf.get("reason", "variable_graph_status_special_second_unavailable"),
                    {},
                    first_terminal_source=source["source_id"],
                ), None
            transition["second_action"] = {
                "state": "outcome_graph",
                "actor": deepcopy(dict(second_actor)),
                "conditional_probability": _fd(Fraction(1, 1)),
                "outcomes": ({
                    "state": "executed",
                    "conditional_probability": _fd(Fraction(1, 1)),
                    "second_action_terminal_leaves": deepcopy(status_leaf["terminal_leaves"]),
                    "second_action_terminal_probability_mass": _fd(Fraction(1, 1)),
                },),
            }
            transitions.append(transition)
            mass += source["path_probability"]
            continue

        if _is_atomic_item_swap_metadata(second_metadata.get("metadata")):
            swapped = _atomic_item_swap_second_from_intermediate(
                strategy_d0=strategy_d0,
                runtime_snapshot=runtime_snapshot,
                intermediate=intermediate,
                source_leaf=leaf,
                action=second_action,
                authorities=extension_authorities.get("atomic_item_swap_status_execution_authorities"),
            )
            if swapped.get("status") != "evaluable":
                return _result(
                    _status(swapped),
                    swapped.get("reason", "variable_graph_atomic_item_swap_second_unavailable"),
                    {},
                    first_terminal_source=source["source_id"],
                ), None
            transition["second_action"] = {
                "state": "outcome_graph",
                "actor": deepcopy(dict(second_actor)),
                "conditional_probability": _fd(Fraction(1, 1)),
                "outcomes": ({
                    "state": "executed",
                    "conditional_probability": _fd(Fraction(1, 1)),
                    "second_action_terminal_leaves": deepcopy(swapped["terminal_leaves"]),
                    "second_action_terminal_probability_mass": _fd(Fraction(1, 1)),
                },),
            }
            transitions.append(transition)
            mass += source["path_probability"]
            continue

        if _is_direct_heal_metadata(second_metadata.get("metadata")):
            healed = _direct_heal_second_from_intermediate(
                strategy_d0=strategy_d0,
                runtime_snapshot=runtime_snapshot,
                intermediate=intermediate,
                actor=second_actor,
                target=second_target,
                action=second_action,
                authorities=extension_authorities.get("direct_heal_execution_authorities"),
            )
            if healed.get("status") != "evaluable":
                return _result(
                    _status(healed),
                    healed.get("reason", "variable_graph_direct_heal_second_unavailable"),
                    {},
                    first_terminal_source=source["source_id"],
                ), None
            transition["second_action"] = {
                "state": "outcome_graph",
                "actor": deepcopy(dict(second_actor)),
                "conditional_probability": _fd(Fraction(1, 1)),
                "outcomes": ({
                    "state": "executed",
                    "conditional_probability": _fd(Fraction(1, 1)),
                    "second_action_terminal_leaves": deepcopy(healed["terminal_leaves"]),
                    "second_action_terminal_probability_mass": _fd(Fraction(1, 1)),
                },),
            }
            transitions.append(transition)
            mass += source["path_probability"]
            continue

        if _is_protection_family(second_metadata.get("metadata")) or canonical_quick_guard_protection_metadata(
            second_metadata.get("metadata", {}).get("move_id"),
        ) is not None or second_metadata.get("metadata", {}).get("move_id") == "mat-block":
            transition["second_action"] = {
                "state": "executed_protection",
                "actor": deepcopy(dict(second_actor)),
                "conditional_probability": _fd(Fraction(1, 1)),
                "reason": "executed_protection",
            }
            transitions.append(transition)
            mass += source["path_probability"]
            continue

        cache_key = (
            *_second_cache_key(intermediate, second_actor, second_metadata),
            repr(leaf.get("consequences", {}).get("damage")),
            repr(leaf.get("consequences", {}).get("target_final_hp")),
        )
        outcomes = second_cache.get(cache_key)
        if outcomes is None:
            outcomes = _execute_second_from_intermediate(
                strategy_d0=strategy_d0,
                runtime_snapshot=runtime_snapshot,
                intermediate=intermediate,
                actor=second_actor,
                target=second_target,
                action=second_action,
                metadata_authority=second_metadata,
                pending_status_execution_authorities=pending_status_execution_authorities,
                extension_authorities=extension_authorities,
                source_leaf=leaf,
                override=None,
            )
            if not (
                isinstance(outcomes, Mapping)
                and outcomes.get("status") in {"incomplete", "unsupported", "rejected"}
            ):
                second_cache[cache_key] = deepcopy(dict(outcomes))
        if isinstance(outcomes, Mapping) and outcomes.get("status") in {"incomplete", "unsupported", "rejected"}:
            return _result(
                _status(outcomes),
                outcomes.get("reason", "variable_graph_second_action_unavailable"),
                {},
                first_terminal_source=source["source_id"],
            ), None
        transition["second_action"] = outcomes
        transitions.append(transition)
        mass += source["path_probability"]
    return transitions, mass




def _atomic_item_swap_second_from_intermediate(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    intermediate: Mapping[str, Any], source_leaf: Mapping[str, Any],
    action: Mapping[str, Any], authorities: Any,
) -> dict[str, Any]:
    authority = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
    if not isinstance(authority, Mapping):
        return _result("incomplete", "atomic_item_swap_status_execution_authority_missing", {})
    materialized = materialize_detached_atomic_item_swap_status(execution_authority=authority)
    if materialized.get("status") != "resolved":
        return _result(
            _status(materialized),
            materialized.get("reason", "atomic_item_swap_materialization_unavailable"),
            {},
        )
    actor, target = materialized.get("actor"), materialized.get("target")
    active = intermediate.get("active", {})
    actor_state = active.get(actor.get("side")) if isinstance(actor, Mapping) and isinstance(active, Mapping) else None
    target_state = active.get(target.get("side")) if isinstance(target, Mapping) and isinstance(active, Mapping) else None
    actor_before = _intermediate_item_before(actor_state)
    target_before = _intermediate_item_before(target_state)
    if actor_before is None:
        actor_before = _runtime_item_before_if_unchanged(runtime_snapshot, source_leaf, actor)
    if target_before is None:
        target_before = _runtime_item_before_if_unchanged(runtime_snapshot, source_leaf, target)
    transition = materialized.get("item_transition")
    if actor_before is None or target_before is None:
        return _result("incomplete", "atomic_item_swap_path_local_item_authority_unknown", {})
    if (
        not isinstance(transition, Mapping)
        or transition.get("actor_item_before") != actor_before
        or transition.get("target_item_before") != target_before
    ):
        return _result("incomplete", "atomic_item_swap_path_local_item_state_changed", {})
    leaf = _atomic_item_swap_pair_leaf(materialized, strategy_d0)
    if isinstance(leaf, str):
        return _result("rejected", leaf, {})
    actor_hp = actor_state.get("hypothetical_hp", {}).get("value") if isinstance(actor_state, Mapping) else None
    target_hp = target_state.get("hypothetical_hp", {}).get("value") if isinstance(target_state, Mapping) else None
    if not _hp_value(actor_hp) or not _hp_value(target_hp):
        return _result("incomplete", "atomic_item_swap_path_local_hp_unknown", {})
    leaf = deepcopy(dict(leaf))
    leaf["consequences"]["own_final_hp"] = actor_hp
    leaf["consequences"]["target_final_hp"] = target_hp
    leaf["consequences"]["self_fainted"] = actor_hp == 0
    leaf["consequences"]["target_ko"] = target_hp == 0
    return {
        "status": "evaluable",
        "terminal_leaves": (leaf,),
        "terminal_probability_mass": _fd(Fraction(1, 1)),
    }


def _intermediate_item_before(state: Any) -> dict[str, Any] | None:
    item = state.get("hypothetical_item") if isinstance(state, Mapping) else None
    if not isinstance(item, Mapping):
        return None
    status = item.get("status")
    if status in {"known", "known_present"} and isinstance(item.get("value"), str) and item["value"]:
        return {"state": "known_present", "item": item["value"]}
    if status in {"known_absent", "absent"} and item.get("value") is None:
        return {"state": "known_absent", "item": None}
    return None


def _runtime_item_before_if_unchanged(
    runtime_snapshot: Mapping[str, Any], source_leaf: Mapping[str, Any], owner: Mapping[str, Any],
) -> dict[str, Any] | None:
    consequences = source_leaf.get("consequences") if isinstance(source_leaf, Mapping) else None
    if not isinstance(consequences, Mapping) or _leaf_has_item_mutation(consequences):
        return None
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    raw = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(raw, Mapping) or raw.get("pokemon_id") != owner.get("pokemon_id"):
        return None
    value = raw.get("known_item")
    provenance = raw.get("known_item_provenance")
    if isinstance(value, str) and value and isinstance(provenance, Mapping) and provenance.get("status") == "known":
        return {"state": "known_present", "item": value}
    if value is None and isinstance(provenance, Mapping) and provenance.get("status") == "known_absent":
        return {"state": "known_absent", "item": None}
    return None


def _leaf_has_item_mutation(consequences: Mapping[str, Any]) -> bool:
    for key in (
        "focus_sash_survival", "sitrus_berry_immediate_consumption",
        "knock_off_item_removal", "fling_item_throw", "item_transfer",
        "atomic_item_swap_status", "ability_item_steal",
    ):
        value = consequences.get(key)
        if value is not None and value is not False:
            return True
    return False

def _direct_heal_second_from_intermediate(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    intermediate: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any],
    action: Mapping[str, Any], authorities: Any,
) -> dict[str, Any]:
    authority = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
    active = intermediate.get("active", {})
    actor_state = active.get(actor.get("side")) if isinstance(active, Mapping) else None
    target_state = active.get(target.get("side")) if isinstance(active, Mapping) else None
    actor_hp = actor_state.get("hypothetical_hp", {}).get("value") if isinstance(actor_state, Mapping) else None
    actor_fainted = actor_state.get("hypothetical_fainted", {}).get("value") if isinstance(actor_state, Mapping) else None
    target_hp = target_state.get("hypothetical_hp", {}).get("value") if isinstance(target_state, Mapping) else None
    maximum = strategy_d0.get("strategy_state", {}).get("active", {}).get(actor.get("side"), {}).get("max_hp")
    if (
        not _hp_value(actor_hp)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum < 1
        or actor_fainted is not (actor_hp == 0)
        or not _hp_value(target_hp)
    ):
        return _result("incomplete", "direct_heal_path_local_hp_authority_missing", {})
    leaf = _direct_heal_leaf(
        authority,
        strategy_d0,
        runtime_snapshot,
        action,
        actor,
        target,
        {"current_hp": actor_hp, "max_hp": maximum, "fainted": actor_fainted},
    )
    if isinstance(leaf, str):
        return _result("incomplete", leaf, {})
    leaf = deepcopy(dict(leaf))
    leaf["consequences"]["target_final_hp"] = target_hp
    leaf["consequences"]["target_ko"] = target_hp == 0
    return {
        "status": "evaluable",
        "terminal_leaves": (leaf,),
        "terminal_probability_mass": _fd(Fraction(1, 1)),
    }

def _execute_second_from_intermediate(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    intermediate: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any],
    action: Mapping[str, Any], metadata_authority: Mapping[str, Any],
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None,
    extension_authorities: Mapping[str, Any], source_leaf: Mapping[str, Any],
    override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    authority = freeze_detached_intermediate_predictive_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        intermediate_state=intermediate,
        actor=actor,
        target=target,
        move_metadata_authority=metadata_authority,
    )
    status_gate = consume_detached_sleep_freeze_execution_for_second_action(
        intermediate_predictive_authority=authority,
        pending_action_id=action.get("action_id"),
        pending_status_execution_authority=(pending_status_execution_authorities or {}).get(action.get("action_id"))
        if isinstance(action.get("action_id"), str)
        else None,
    )
    if status_gate.get("status") != "resolved":
        return {
            "status": _status(status_gate),
            "reason": status_gate.get("reason", "graph_second_action_intermediate_authority_unavailable"),
        }
    execution = status_gate.get("second_action_execution_branches")
    if not isinstance(execution, tuple) or not execution:
        return {"status": "rejected", "reason": "graph_second_action_execution_branches_invalid"}
    inputs = status_gate.get("builder_inputs", {})
    if not isinstance(inputs, Mapping):
        return {"status": "rejected", "reason": "graph_second_action_builder_inputs_invalid"}

    outcomes: list[dict[str, Any]] = []
    for branch in execution:
        factor = _fraction(branch.get("conditional_probability"))
        if factor <= 0:
            return {"status": "rejected", "reason": "graph_second_action_execution_probability_invalid"}
        if branch.get("state") in {
            "cancelled_due_to_paralysis", "cancelled_due_to_sleep", "cancelled_due_to_freeze",
        }:
            outcomes.append({
                "state": branch["state"],
                "conditional_probability": _fd(factor),
                "reason": branch.get("reason"),
                "execution_branch": deepcopy(dict(branch)),
            })
            continue
        if branch.get("state") != "executed":
            return {"status": "rejected", "reason": "graph_second_action_execution_state_invalid"}
        executed = _execute_action_in_context(
            strategy_d0=inputs.get("strategy_d0", {}),
            runtime_snapshot=inputs.get("runtime_snapshot", {}),
            actor=inputs.get("attacker", {}),
            target=inputs.get("target", {}),
            action=action,
            metadata_authority=_metadata_for_inputs(metadata_authority, inputs),
            extension_authorities=extension_authorities,
            source_leaf=source_leaf,
            original_strategy_d0=strategy_d0,
            original_runtime_snapshot=runtime_snapshot,
        )
        if executed.get("status") != "evaluable":
            return {"status": _status(executed), "reason": executed.get("reason", "graph_second_action_execution_unavailable")}
        row = {
            "state": "executed",
            "conditional_probability": _fd(factor),
            "execution_branch": deepcopy(dict(branch)),
            **(
                {
                    "second_action_graph": deepcopy(dict(executed["native_graph"])),
                    "second_action_terminal_probability_mass": deepcopy(
                        executed["native_graph"].get("terminal_probability_mass"),
                    ),
                }
                if isinstance(executed.get("native_graph"), Mapping)
                else {
                    "second_action_terminal_leaves": deepcopy(executed["terminal_leaves"]),
                    "second_action_terminal_probability_mass": deepcopy(executed.get("terminal_probability_mass")),
                }
            ),
        }
        if isinstance(executed.get("pivot_transitions"), tuple):
            row["second_action_pivot_transitions"] = deepcopy(executed["pivot_transitions"])
        if isinstance(override, Mapping) and override.get("forced_execution_action") is not None:
            row["forced_execution_action"] = deepcopy(override["forced_execution_action"])
        outcomes.append(row)
    conditional = sum((_fraction(row["conditional_probability"]) for row in outcomes), Fraction())
    if conditional != Fraction(1, 1):
        return {"status": "rejected", "reason": "graph_second_action_execution_probability_mass_not_one"}
    return {
        "state": "outcome_graph",
        "actor": deepcopy(dict(actor)),
        "conditional_probability": _fd(Fraction(1, 1)),
        "outcomes": tuple(outcomes),
    }



def _refresh_pivot_replacement_for_execution(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    actor: Mapping[str, Any], action: Mapping[str, Any],
    move_metadata: Mapping[str, Any], source_replacement: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(source_replacement, Mapping):
        return {"status": "incomplete", "reason": "pivot_replacement_authority_missing"}
    if source_replacement.get("status") == "incomplete":
        return deepcopy(dict(source_replacement))
    if source_replacement.get("status") not in {"resolved", "known_none"}:
        return {"status": "rejected", "reason": "pivot_replacement_authority_invalid"}
    fresh = freeze_runtime_d0_pivot_replacement_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        pivot_actor=actor,
        pivot_action=action,
        move_metadata=move_metadata,
    )
    if fresh.get("status") in {"incomplete", "rejected"}:
        return deepcopy(dict(fresh))
    if source_replacement.get("status") != fresh.get("status"):
        return {"status": "rejected", "reason": "pivot_replacement_path_local_state_conflict"}
    if fresh.get("status") == "resolved" and source_replacement.get("owner") != fresh.get("owner"):
        return {"status": "rejected", "reason": "pivot_replacement_path_local_owner_conflict"}
    return deepcopy(dict(fresh))

def _execute_action_in_context(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    actor: Mapping[str, Any], target: Mapping[str, Any], action: Mapping[str, Any],
    metadata_authority: Mapping[str, Any], extension_authorities: Mapping[str, Any],
    source_leaf: Mapping[str, Any], original_strategy_d0: Mapping[str, Any],
    original_runtime_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = _metadata_for_inputs(metadata_authority, None)
    if not isinstance(metadata, Mapping):
        return _result("rejected", "graph_action_metadata_unavailable", {})
    if metadata.get("move_id") in _GRAPH_MOVES:
        graph = _execute_graph_in_context(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            actor=actor,
            target=target,
            action=action,
            metadata_authority=metadata_authority,
        )
        return {"status": "evaluable", "native_graph": graph} if graph.get("status") == "evaluable" else graph
    if _is_direct_heal_metadata(metadata):
        authorities = extension_authorities.get("direct_heal_execution_authorities")
        frozen = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
        path_hp = _intermediate_path_hp(strategy_d0, actor)
        leaf = _direct_heal_leaf(
            frozen,
            original_strategy_d0,
            original_runtime_snapshot,
            action,
            actor,
            target,
            path_hp,
        )
        if isinstance(leaf, str):
            return _result("incomplete", leaf, {})
        leaf = _rebase_leaf_to_strategy_state(leaf, strategy_d0)
        return {
            "status": "evaluable",
            "terminal_leaves": (leaf,),
            "terminal_probability_mass": _fd(Fraction(1, 1)),
        }
    if _is_atomic_item_swap_metadata(metadata):
        authorities = extension_authorities.get("atomic_item_swap_status_execution_authorities")
        frozen = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
        if not isinstance(frozen, Mapping):
            return _result("incomplete", "atomic_item_swap_status_execution_authority_missing", {})
        materialized = materialize_detached_atomic_item_swap_status(execution_authority=frozen)
        if materialized.get("status") != "resolved":
            return _result(_status(materialized), materialized.get("reason", "atomic_item_swap_materialization_unavailable"), {})
        leaf = _atomic_item_swap_pair_leaf(materialized, original_strategy_d0)
        if isinstance(leaf, str):
            return _result("rejected", leaf, {})
        leaf = _rebase_leaf_to_strategy_state(leaf, strategy_d0)
        return {"status": "evaluable", "terminal_leaves": (leaf,), "terminal_probability_mass": _fd(Fraction(1, 1))}
    if metadata.get("move_id") in {"taunt", "encore", "disable"}:
        field = f"{metadata['move_id']}_application_authorities"
        builders = {"taunt": _taunt_pair_leaf, "encore": _encore_pair_leaf, "disable": _disable_pair_leaf}
        authorities = extension_authorities.get(field)
        application = authorities.get(action.get("action_id")) if isinstance(authorities, Mapping) else None
        if not isinstance(application, Mapping):
            return _result("incomplete", f"{metadata['move_id']}_application_authority_missing", {})
        leaf = builders[metadata["move_id"]](application, original_strategy_d0)
        if isinstance(leaf, str):
            return _result("incomplete", leaf, {})
        leaf = _rebase_leaf_to_strategy_state(leaf, strategy_d0)
        return {"status": "evaluable", "terminal_leaves": (leaf,), "terminal_probability_mass": _fd(Fraction(1, 1))}
    if metadata.get("category") not in {"physical", "special"}:
        return _result("incomplete", "graph_second_special_family_not_bound", {})

    ledger = _attack_ledger(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        actor=actor,
        target=target,
        metadata_authority=metadata_authority,
        action=action,
        source_terminal_leaf=source_leaf,
    )
    if ledger.get("status") != "evaluable":
        return ledger
    if metadata.get("move_id") not in {"u-turn", "volt-switch", "flip-turn"}:
        return ledger

    replacements = extension_authorities.get("pivot_replacement_authorities")
    entries = extension_authorities.get("pivot_entry_authorities")
    transitions: list[dict[str, Any]] = []
    for leaf in ledger.get("terminal_leaves", ()):
        pivot_leaf = _pivot_selected_action_leaf(
            leaf=leaf, action=action, actor=actor, move_metadata=metadata,
        )
        if isinstance(pivot_leaf, str):
            return _result("rejected", pivot_leaf, {})
        source_replacement = _pivot_replacement_authority(replacements, leaf, action)
        refreshed_replacement = _refresh_pivot_replacement_for_execution(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            actor=actor,
            action=action,
            move_metadata=metadata,
            source_replacement=source_replacement,
        )
        if refreshed_replacement.get("status") in {"incomplete", "rejected"}:
            return refreshed_replacement
        pivot = freeze_damage_pivot_continuation_authority(
            strategy_d0=strategy_d0,
            action=action,
            move_metadata=metadata,
            attack_terminal_leaf=pivot_leaf,
            replacement_authority=refreshed_replacement,
        )
        if pivot.get("status") == "applies":
            entry = refreshed_replacement.get("entry_authority")
            if not isinstance(entry, Mapping):
                entry = _pivot_entry_authority(entries, leaf, action)
            if not isinstance(entry, Mapping):
                return _result("incomplete", "pivot_switch_entry_authority_missing", {})
            intermediate = materialize_detached_predictive_intermediate_state(
                strategy_d0=strategy_d0, terminal_leaf=leaf,
            )
            if intermediate.get("status") != "resolved":
                return intermediate
            pivot_metadata_authority = _graph_metadata_authority_for_context(
                strategy_d0=strategy_d0,
                actor=actor,
                metadata=metadata,
            )
            precursor = freeze_detached_intermediate_predictive_authority(
                strategy_d0=strategy_d0,
                runtime_snapshot=runtime_snapshot,
                intermediate_state=intermediate,
                actor=actor,
                target=target,
                move_metadata_authority=pivot_metadata_authority,
            )
            if precursor.get("status") != "resolved":
                return precursor
            switched = materialize_detached_damage_pivot_switch(
                intermediate_authority=precursor,
                pivot_authority=pivot,
                entry_authority=entry,
            )
            if switched.get("status") != "resolved":
                return switched
            transitions.append({"leaf_id": leaf["leaf_id"], "pivot_transition": deepcopy(dict(switched))})
        elif pivot.get("status") in {"incomplete", "unsupported", "rejected"}:
            return pivot
    return {**ledger, "pivot_transitions": tuple(transitions)}


def _execute_graph_in_context(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    actor: Mapping[str, Any], target: Mapping[str, Any], action: Mapping[str, Any],
    metadata_authority: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = _metadata_for_inputs(metadata_authority, None)
    if not isinstance(metadata, Mapping):
        return _result("rejected", "graph_execution_metadata_unavailable", {})
    bound_metadata = _graph_metadata_authority_for_context(
        strategy_d0=strategy_d0, actor=actor, metadata=metadata,
    )
    sturdy = freeze_runtime_d0_sturdy_survival_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        defender=target,
        attacker=actor,
        action=_graph_execution_action(action, bound_metadata, metadata),
        move_metadata=metadata,
    )
    if sturdy.get("status") in {"incomplete", "unsupported", "rejected"}:
        return _result(_status(sturdy), sturdy.get("reason", "graph_sturdy_authority_unavailable"), {})
    focus = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        holder=target,
        attacker=actor,
        action=_graph_execution_action(action, bound_metadata, metadata),
        move_metadata=metadata,
    )
    if focus.get("status") in {"incomplete", "unsupported", "rejected"}:
        return _result(_status(focus), focus.get("reason", "graph_focus_sash_authority_unavailable"), {})
    return _variable_action_graph(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        actor=actor,
        target=target,
        metadata_authority=bound_metadata,
        sturdy_survival_authority=sturdy,
        focus_sash_survival_authority=focus,
    )


def _graph_metadata_authority_for_context(
    *, strategy_d0: Mapping[str, Any], actor: Mapping[str, Any], metadata: Mapping[str, Any],
) -> dict[str, Any]:
    move_id = metadata["move_id"]
    return {
        "status": "resolved",
        "move_id": move_id,
        "metadata": deepcopy(dict(metadata)),
        "candidate_id": f"attack:{move_id}",
        "active_attacker": deepcopy(dict(actor)),
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "provenance": "detached_graph_pair_path_local_move_metadata_authority_v1",
    }


def _graph_execution_action(
    action: Mapping[str, Any], metadata_authority: Mapping[str, Any], metadata: Mapping[str, Any],
) -> dict[str, Any]:
    move_id = metadata["move_id"]
    return {
        **deepcopy(dict(action)),
        "action_id": f"attack:{move_id}",
        "action_type": "attack",
        "identity": move_id,
        "move_metadata_authority": deepcopy(dict(metadata_authority)),
    }


def _executed_graph_second(
    actor: Mapping[str, Any], graph: Mapping[str, Any], override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    outcome = {
        "state": "executed",
        "conditional_probability": _fd(Fraction(1, 1)),
        "second_action_graph": deepcopy(dict(graph)),
        "second_action_terminal_probability_mass": deepcopy(graph.get("terminal_probability_mass")),
    }
    if isinstance(override, Mapping) and override.get("forced_execution_action") is not None:
        outcome["forced_execution_action"] = deepcopy(override["forced_execution_action"])
    return {
        "state": "outcome_graph",
        "actor": deepcopy(dict(actor)),
        "conditional_probability": _fd(Fraction(1, 1)),
        "outcomes": (outcome,),
    }


def _cancelled_second(actor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "state": "cancelled_due_to_faint",
        "actor": deepcopy(dict(actor)),
        "conditional_probability": _fd(Fraction(1, 1)),
        "reason": "second_action_cancelled_due_to_faint",
    }


def _bind_leaf_through_actor_neutral_root(
    leaf: Mapping[str, Any], root: Mapping[str, Any],
) -> dict[str, Any] | str:
    predictive = root.get("predictive_strategy_d0")
    if not isinstance(predictive, Mapping):
        return "actor_neutral_root_predictive_d0_missing"
    result = deepcopy(dict(leaf))
    provenance = result.get("provenance")
    if not isinstance(provenance, Mapping):
        return "actor_neutral_special_leaf_provenance_missing"
    move_id = provenance.get("move_id")
    if move_id != root.get("move_id"):
        return "actor_neutral_special_leaf_move_mismatch"
    result["candidate_id"] = f"attack:{move_id}"
    result["provenance"] = {
        **deepcopy(dict(provenance)),
        "session_id": predictive["session_id"],
        "source_runtime_fingerprint": predictive["source_runtime_fingerprint"],
        "source_branch_fingerprint": predictive["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(predictive["decision_owner"])),
    }
    return result


def _rebase_leaf_to_strategy_state(
    leaf: Mapping[str, Any], strategy_d0: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(leaf))
    provenance = result.get("provenance", {})
    actor, target = provenance.get("attacker"), provenance.get("target")
    active = strategy_d0.get("strategy_state", {}).get("active", {})
    actor_hp = active.get(actor.get("side"), {}).get("current_hp") if isinstance(actor, Mapping) else None
    target_hp = active.get(target.get("side"), {}).get("current_hp") if isinstance(target, Mapping) else None
    if _hp_value(actor_hp) and _hp_value(target_hp):
        consequences = result.get("consequences", {})
        consequences["own_final_hp"] = actor_hp
        consequences["target_final_hp"] = target_hp
        consequences["self_fainted"] = actor_hp == 0
        consequences["target_ko"] = target_hp == 0
    return result


def _intermediate_path_hp(strategy_d0: Mapping[str, Any], actor: Mapping[str, Any]) -> dict[str, Any] | None:
    active = strategy_d0.get("strategy_state", {}).get("active", {}).get(actor.get("side"), {})
    current, maximum = active.get("current_hp"), active.get("max_hp")
    if not _hp_value(current) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
        return None
    return {"current_hp": current, "max_hp": maximum, "fainted": current == 0}


def _owner_identity_for_graph(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value[key])
        for key in ("session_id", "side", "slot_index", "pokemon_id")
        if key in value
    }


def _is_protection_family(metadata: Any) -> bool:
    if not isinstance(metadata, Mapping):
        return False
    move_id = metadata.get("move_id")
    return (
        canonical_protection_metadata(move_id) is not None
        or canonical_silk_trap_metadata(move_id) is not None
        or canonical_kings_shield_metadata(move_id) is not None
        or canonical_obstruct_metadata(move_id) is not None
        or canonical_spiky_shield_reactive_damage_metadata(move_id) is not None
        or canonical_baneful_bunker_reactive_poison_metadata(move_id) is not None
        or canonical_burning_bulwark_reactive_burn_metadata(move_id) is not None
    )


def _hp_value(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _synthetic_terminal_leaf(*, first_graph: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    consequences = deepcopy(dict(source["consequences"]))
    ordered = source.get("ordered_hit")
    focus = ordered.get("focus_sash_survival") if isinstance(ordered, Mapping) else None
    if isinstance(focus, Mapping) and focus.get("outcome") == "applied":
        consequences["focus_sash_survival"] = deepcopy(dict(focus))
    return {"leaf_id": f"variable_graph:{source['source_id']}", "candidate_id": f"attack:{first_graph['move_id']}", "action_type": "attack", "branch_path": ("variable_multi_hit_graph", source["source_id"]), "probability": _fd(source["path_probability"]), "hit_state": "miss" if source.get("ordered_hit") is None else "hit", "critical_state": "per_hit_independent" if source.get("ordered_hit") is not None else "not_applicable", "damage_roll": "per_hit_independent" if source.get("ordered_hit") is not None else "not_applicable", "consequences": consequences, "provenance": {key: deepcopy(first_graph[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")}}


def _second_cache_key(intermediate: Mapping[str, Any], actor: Mapping[str, Any], metadata: Mapping[str, Any]) -> tuple[Any, ...]:
    active = intermediate.get("active", {})
    return (actor.get("side"), actor.get("pokemon_id"), _metadata_for_inputs(metadata, None).get("move_id") if _metadata_for_inputs(metadata, None) else None, repr(active.get("self")), repr(active.get("opponent")))


def _root_summary(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return None
    return {"schema_version": value.get("schema_version"), "hypothetical": value.get("hypothetical"), "root_action_id": value.get("root_action_id")}


def _fraction(value: Any) -> Fraction:
    try:
        return Fraction(value["numerator"], value["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return Fraction(-1, 1)


def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _mapping(value: Any) -> Mapping[str, Any]: return value if isinstance(value, Mapping) else {}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
