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
from llm.advisor_immediate_move_vs_move_action_pair import (
    _attack_ledger, _base, _fainted, _metadata_for_inputs, _opponent_metadata,
    _orders, _status,
)
from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import (
    freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import resolve_runtime_d0_selectable_move_metadata_authority


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
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Attach exact second-action outcomes to a variable first-action graph."""
    base = _base(strategy_d0, own_action, opponent_action)
    if base is None:
        return _result("rejected", "invalid_variable_graph_pair_request", {})
    orders = _orders(action_order_authority, base, quick_claw_action_order_authority)
    if isinstance(orders, tuple):
        return _result(*orders, base)
    own_metadata = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=own_action)
    opponent_metadata = _opponent_metadata(opponent_action, base)
    if own_metadata.get("status") != "resolved":
        return _result(_status(own_metadata), own_metadata.get("reason", "own_move_metadata_unavailable"), base)
    if isinstance(opponent_metadata, tuple):
        return _result(*opponent_metadata, base)
    order_graphs: list[dict[str, Any]] = []
    total_mass = Fraction()
    for plan in orders:
        graph = _materialize_order_graph(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
            own_action=own_action, opponent_action=opponent_action,
            own_metadata=own_metadata, opponent_metadata=opponent_metadata,
            order_plan=plan, first_action_sturdy_survival_authority=first_action_sturdy_survival_authority,
            pending_status_execution_authorities=pending_status_execution_authorities,
        )
        if graph.get("status") != "evaluable":
            return _result(_status(graph), graph.get("reason", "variable_graph_order_unavailable"), base, order_graphs=tuple(order_graphs))
        order_graphs.append(graph)
        total_mass += _fraction(graph["order_weighted_terminal_probability_mass"])
    if total_mass != Fraction(1, 1):
        return _result("rejected", "variable_graph_pair_probability_mass_not_one", base, terminal_probability_mass=_fd(total_mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        **base, "action_order": deepcopy(dict(action_order_authority)),
        "conditional_on": "opponent_selected_exact_known_usable_move",
        "order_graphs": tuple(order_graphs), "terminal_probability_mass": _fd(total_mass),
        "terminal_leaf_representation": "exact_first_action_graph_paths_with_attached_second_action_outcomes",
        "aggregation": "none_preserve_variable_first_action_path_identity",
        "legacy_flat_pair_ledger_compatibility": "not_applicable_requires_graph_ledger_normalizer",
        "provenance": "strict_detached_variable_multi_hit_graph_to_immediate_pair_v1",
    }


def _materialize_order_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any], own_metadata: Mapping[str, Any], opponent_metadata: Mapping[str, Any], order_plan: Mapping[str, Any], first_action_sturdy_survival_authority: Mapping[str, Any] | None, pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    order = order_plan["order"]
    first_actor = base["own_actor"] if order == "own_first" else base["opponent_actor"]
    first_metadata = own_metadata if order == "own_first" else opponent_metadata
    first_d0, first_snapshot, root = strategy_d0, runtime_snapshot, None
    if order == "opponent_first":
        root = freeze_detached_actor_neutral_root_predictive_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, opponent_action=opponent_action,
        )
        if root.get("status") != "resolved":
            return _result(_status(root), root.get("reason", "opponent_root_predictive_authority_unavailable"), {})
        first_d0, first_snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
    first = _variable_action_graph(
        strategy_d0=first_d0, runtime_snapshot=first_snapshot, actor=first_actor,
        target=base["opponent_actor"] if first_actor == base["own_actor"] else base["own_actor"],
        metadata_authority=first_metadata, sturdy_survival_authority=first_action_sturdy_survival_authority,
    )
    if first.get("status") != "evaluable":
        return _result(_status(first), first.get("reason", "variable_first_action_graph_unavailable"), {})
    sources = _terminal_sources(first)
    if isinstance(sources, str):
        return _result("rejected", sources, {})
    second_actor = base["opponent_actor"] if order == "own_first" else base["own_actor"]
    second_metadata = opponent_metadata if order == "own_first" else own_metadata
    transitions, conditional_mass = _attach_second_actions(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
        first_graph=first, terminal_sources=sources, second_actor=second_actor,
        second_metadata=second_metadata, root_predictive_authority=root,
        pending_action_id=opponent_action.get("action_id") if order == "own_first" else own_action.get("action_id"),
        pending_status_execution_authorities=pending_status_execution_authorities,
    )
    if isinstance(transitions, Mapping):
        return transitions
    if conditional_mass != Fraction(1, 1):
        return _result("rejected", "variable_graph_terminal_transition_probability_mass_not_one", {})
    order_probability = order_plan["probability"]
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "action_order": order,
        "order_conditional_probability": _fd(order_probability),
        **({"action_order_branch": deepcopy(dict(order_plan["source_branch"]))} if isinstance(order_plan.get("source_branch"), Mapping) else {}),
        "first_action_graph": deepcopy(first), "terminal_transitions": tuple(transitions),
        "conditional_terminal_probability_mass": _fd(conditional_mass),
        "order_weighted_terminal_probability_mass": _fd(order_probability * conditional_mass),
        "provenance": {"root_predictive_authority": _root_summary(root), "first_actor": deepcopy(dict(first_actor)), "second_actor": deepcopy(dict(second_actor))},
    }


def _variable_action_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata_authority: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None) -> dict[str, Any]:
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
    if metadata["move_id"] == "population-bomb":
        execution = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action)
    elif metadata["move_id"] in _ESCALATING_MOVES:
        execution = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action)
    else:
        execution = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action)
    if execution.get("status") != "resolved":
        return _result(_status(execution), execution.get("reason", "variable_multi_hit_execution_authority_unavailable"), {})
    graph = (materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority,
    ) if metadata["move_id"] == "population-bomb" else materialize_detached_escalating_three_hit_predictive_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority,
    ) if metadata["move_id"] in _ESCALATING_MOVES else materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority,
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
                result.append({"source_id": f"edge:{edge['edge_id']}", "path_probability": probability, "consequences": deepcopy(dict(edge["terminal_consequences"])), "ordered_hit": deepcopy(dict(ordered)) if isinstance(ordered, Mapping) else None})
            else:
                target = node_by_id[edge["to_node_id"]]
                advancing = target.get("attempt_index") == node.get("attempt_index", -1) + 1 if population else target.get("hit_index") == node.get("hit_index", -1) + 1 if escalating else target.get("completed_hit_count") == node.get("completed_hit_count", -1) + 1
                if not advancing:
                    return "variable_graph_cycle_or_nonadvancing_edge"
                incoming[edge["to_node_id"]] += probability
    mass = sum((row["path_probability"] for row in result), Fraction())
    return result if mass == Fraction(1, 1) else "variable_graph_terminal_path_mass_not_one"


def _attach_second_actions(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], first_graph: Mapping[str, Any], terminal_sources: tuple[Mapping[str, Any], ...], second_actor: Mapping[str, Any], second_metadata: Mapping[str, Any], root_predictive_authority: Mapping[str, Any] | None, pending_action_id: Any, pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None) -> tuple[list[dict[str, Any]], Fraction] | tuple[dict[str, Any], None]:
    first_actor, first_target = first_graph.get("attacker"), first_graph.get("target")
    if not isinstance(first_actor, Mapping) or not isinstance(first_target, Mapping):
        return _result("rejected", "variable_graph_first_actor_target_missing", {}), None
    cache: dict[tuple[Any, ...], tuple[dict[str, Any], tuple[dict[str, Any], ...]]] = {}
    transitions: list[dict[str, Any]] = []
    mass = Fraction()
    for source in terminal_sources:
        leaf = _synthetic_terminal_leaf(first_graph=first_graph, source=source)
        intermediate = materialize_detached_predictive_intermediate_state(
            strategy_d0=strategy_d0, terminal_leaf=leaf, root_predictive_authority=root_predictive_authority,
        )
        if intermediate.get("status") != "resolved":
            return _result(_status(intermediate), intermediate.get("reason", "variable_graph_intermediate_state_unavailable"), {}, first_terminal_source=source["source_id"]), None
        transition = {"first_terminal_source_id": source["source_id"], "incoming_path_probability": _fd(source["path_probability"]), "first_terminal_consequences": deepcopy(dict(source["consequences"])), "intermediate_state_id": intermediate.get("first_action", {}).get("leaf_id"), "ordered_terminal_hit": deepcopy(source.get("ordered_hit"))}
        if _fainted(intermediate, second_actor):
            transition["second_action"] = {"state": "cancelled_due_to_faint", "actor": deepcopy(dict(second_actor)), "conditional_probability": _fd(Fraction(1, 1)), "reason": "second_action_cancelled_due_to_faint"}
            transitions.append(transition); mass += source["path_probability"]; continue
        key = _second_cache_key(intermediate, second_actor, second_metadata)
        cached = cache.get(key)
        if cached is None:
            authority = freeze_detached_intermediate_predictive_authority(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, intermediate_state=intermediate,
                actor=second_actor, target=first_target if second_actor == first_actor else first_actor,
                move_metadata_authority=second_metadata,
            )
            paralysis = consume_detached_sleep_freeze_execution_for_second_action(intermediate_predictive_authority=authority, pending_action_id=pending_action_id, pending_status_execution_authority=(pending_status_execution_authorities or {}).get(pending_action_id) if isinstance(pending_action_id, str) else None)
            if paralysis.get("status") != "resolved":
                return _result(_status(paralysis), paralysis.get("reason", "variable_graph_second_action_intermediate_authority_unavailable"), {}, first_terminal_source=source["source_id"]), None
            execution = paralysis.get("second_action_execution_branches")
            if not isinstance(execution, tuple) or not execution:
                return _result("rejected", "variable_graph_second_action_execution_branches_invalid", {}), None
            outcomes: list[dict[str, Any]] = []
            for branch in execution:
                factor = _fraction(branch.get("conditional_probability"))
                if factor <= 0:
                    return _result("rejected", "variable_graph_second_action_execution_probability_invalid", {}), None
                if branch.get("state") in {"cancelled_due_to_paralysis", "cancelled_due_to_sleep", "cancelled_due_to_freeze"}:
                    outcomes.append({"state": branch["state"], "conditional_probability": _fd(factor), "reason": branch.get("reason"), "execution_branch": deepcopy(dict(branch))}); continue
                if branch.get("state") != "executed":
                    return _result("rejected", "variable_graph_second_action_execution_state_invalid", {}), None
                inputs = paralysis.get("builder_inputs", {})
                ledger = _attack_ledger(strategy_d0=inputs.get("strategy_d0", {}), runtime_snapshot=inputs.get("runtime_snapshot", {}), actor=inputs.get("attacker", {}), target=inputs.get("target", {}), metadata_authority=_metadata_for_inputs(second_metadata, inputs))
                if ledger.get("status") != "evaluable" or not isinstance(ledger.get("terminal_leaves"), tuple):
                    return _result(_status(ledger), ledger.get("reason", "variable_graph_second_action_ledger_unavailable"), {}), None
                outcomes.append({"state": "executed", "conditional_probability": _fd(factor), "execution_branch": deepcopy(dict(branch)), "second_action_terminal_leaves": deepcopy(ledger["terminal_leaves"]), "second_action_terminal_probability_mass": deepcopy(ledger.get("terminal_probability_mass"))})
            conditional = sum((_fraction(row["conditional_probability"]) for row in outcomes), Fraction())
            if conditional != Fraction(1, 1):
                return _result("rejected", "variable_graph_second_action_execution_probability_mass_not_one", {}), None
            cached = (paralysis, tuple(outcomes)); cache[key] = cached
        _paralysis, outcomes = cached
        transition["second_action"] = {"state": "outcome_graph", "actor": deepcopy(dict(second_actor)), "conditional_probability": _fd(Fraction(1, 1)), "outcomes": deepcopy(outcomes), "cache_key": repr(key)}
        transitions.append(transition); mass += source["path_probability"]
    return transitions, mass


def _synthetic_terminal_leaf(*, first_graph: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    return {"leaf_id": f"variable_graph:{source['source_id']}", "candidate_id": f"attack:{first_graph['move_id']}", "action_type": "attack", "branch_path": ("variable_multi_hit_graph", source["source_id"]), "probability": _fd(source["path_probability"]), "hit_state": "miss" if source.get("ordered_hit") is None else "hit", "critical_state": "per_hit_independent" if source.get("ordered_hit") is not None else "not_applicable", "damage_roll": "per_hit_independent" if source.get("ordered_hit") is not None else "not_applicable", "consequences": deepcopy(dict(source["consequences"])), "provenance": {key: deepcopy(first_graph[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")}}


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
