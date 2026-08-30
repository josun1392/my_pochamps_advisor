"""Strict graph validation for the detached Rock Slide recipient DAG."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_rock_slide_multi_recipient_predictive_graph_materialization import SCHEMA_VERSION as GRAPH_SCHEMA
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import SCHEMA_VERSION as SCOPE_SCHEMA


SCHEMA_VERSION = "exact-rock-slide-multi-recipient-action-outcome-ledger-v1"
HORIZON = "immediate_action_consequence"


def normalize_rock_slide_multi_recipient_action_outcome_ledger(*, graph: Mapping[str, Any]) -> dict[str, Any]:
    """Validate graph topology/probability without replaying any mechanics."""
    base = _base(graph)
    if base is None:
        return _result("rejected", "invalid_rock_slide_multi_recipient_graph_identity", {})
    if graph.get("status") != "evaluable" or graph.get("schema_version") != GRAPH_SCHEMA or graph.get("horizon") != HORIZON:
        return _result("rejected", "rock_slide_graph_schema_or_status_invalid", base)
    if _fraction(graph.get("terminal_probability_mass")) != Fraction(1, 1):
        return _result("rejected", "rock_slide_graph_declared_root_mass_invalid", base)
    scope = graph.get("execution_scope_authority")
    if not _scope(scope, base):
        return _result("rejected", "rock_slide_graph_execution_scope_binding_mismatch", base)
    nodes = graph.get("terminal_leaf_nodes"); edges = graph.get("terminal_leaf_edges"); roots = graph.get("terminal_leaf_roots")
    parsed = _validate_topology(nodes=nodes, edges=edges, roots=roots, recipients=base["recipients"], wide_guard_authority=graph.get("wide_guard_spread_applicability_authority"), mat_block_authority=graph.get("mat_block_direct_damage_applicability_authority"))
    if isinstance(parsed, str):
        return _result("rejected", parsed, base)
    terminal_mass, terminal_ids = parsed["terminal_mass"], parsed["terminal_edge_ids"]
    if terminal_mass != Fraction(1, 1):
        return _result("rejected", "rock_slide_graph_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(terminal_mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
        "terminal_leaf_representation": "exact_rock_slide_multi_recipient_graph_paths",
        "rock_slide_graph": deepcopy(dict(graph)), "terminal_edge_ids": terminal_ids,
        "terminal_probability_mass": _fd(terminal_mass),
        "aggregation": "none_preserve_graph_path_and_ordered_recipient_identity",
        "provenance": "strict_rock_slide_multi_recipient_graph_to_exact_outcome_ledger_v1",
    }


def graph_terminal_rows(*, ledger: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | str:
    """Return exact terminal transitions from the validated graph only."""
    if ledger.get("status") != "evaluable" or ledger.get("schema_version") != SCHEMA_VERSION or ledger.get("terminal_leaf_representation") != "exact_rock_slide_multi_recipient_graph_paths":
        return "rock_slide_multi_recipient_ledger_unavailable"
    graph = ledger.get("rock_slide_graph")
    base = _base(ledger)
    if not isinstance(graph, Mapping) or base is None or _base(graph) != base:
        return "rock_slide_multi_recipient_ledger_graph_binding_invalid"
    parsed = _validate_topology(nodes=graph.get("terminal_leaf_nodes"), edges=graph.get("terminal_leaf_edges"), roots=graph.get("terminal_leaf_roots"), recipients=base["recipients"], wide_guard_authority=graph.get("wide_guard_spread_applicability_authority"))
    if isinstance(parsed, str) or parsed["terminal_mass"] != Fraction(1, 1):
        return parsed if isinstance(parsed, str) else "rock_slide_multi_recipient_ledger_graph_mass_invalid"
    wanted = ledger.get("terminal_edge_ids")
    if not isinstance(wanted, tuple) or wanted != parsed["terminal_edge_ids"]:
        return "rock_slide_multi_recipient_ledger_terminal_reference_invalid"
    rows = tuple(parsed["terminal_rows"])
    return rows if sum((row["probability"] for row in rows), Fraction()) == Fraction(1, 1) else "rock_slide_multi_recipient_terminal_row_mass_invalid"


def _validate_topology(*, nodes: Any, edges: Any, roots: Any, recipients: tuple[Mapping[str, Any], ...], wide_guard_authority: Any, mat_block_authority: Any = None) -> dict[str, Any] | str:
    if not isinstance(nodes, tuple) or not isinstance(edges, tuple) or not isinstance(roots, tuple) or len(roots) != 1 or not nodes or not edges:
        return "rock_slide_graph_topology_missing"
    node_map: dict[str, Mapping[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, Mapping) or not isinstance(node.get("node_id"), str) or node["node_id"] in node_map:
            return "rock_slide_graph_duplicate_or_invalid_node_id"
        cursor, prior = node.get("recipient_cursor"), node.get("prior_recipient_outcomes")
        if not isinstance(cursor, int) or isinstance(cursor, bool) or not 0 <= cursor < len(recipients) or not isinstance(prior, tuple) or len(prior) != cursor or not _prior(prior, recipients[:cursor]):
            return "rock_slide_graph_recipient_cursor_invalid"
        node_map[node["node_id"]] = node
    root = roots[0]
    if not isinstance(root, Mapping) or root.get("terminal") is not False or _fraction(root.get("probability")) != Fraction(1, 1) or root.get("node_id") not in node_map or node_map[root["node_id"]].get("recipient_cursor") != 0:
        return "rock_slide_graph_root_invalid"
    outgoing: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, Mapping) or not isinstance(edge.get("edge_id"), str) or edge["edge_id"] in edge_ids or edge.get("from_node_id") not in node_map:
            return "rock_slide_graph_dangling_or_duplicate_edge"
        edge_ids.add(edge["edge_id"])
        probability = _fraction(edge.get("conditional_probability"))
        if probability <= 0 or probability > 1 or not _outcome(edge.get("recipient_outcome"), node_map[edge["from_node_id"]], recipients, probability, wide_guard_authority, mat_block_authority):
            return "rock_slide_graph_edge_probability_or_recipient_outcome_invalid"
        terminal = edge.get("terminal")
        if not isinstance(terminal, bool): return "rock_slide_graph_terminal_flag_invalid"
        source = node_map[edge["from_node_id"]]
        if terminal:
            if "to_node_id" in edge or source["recipient_cursor"] + 1 != len(recipients) or not _terminal(edge.get("terminal_consequences"), source, edge["recipient_outcome"], recipients):
                return "rock_slide_graph_terminal_recipient_outcomes_invalid"
        else:
            target = edge.get("to_node_id")
            if target not in node_map or node_map[target]["recipient_cursor"] != source["recipient_cursor"] + 1 or node_map[target]["prior_recipient_outcomes"] != (*source["prior_recipient_outcomes"], edge["recipient_outcome"]):
                return "rock_slide_graph_cursor_transition_invalid"
        outgoing[edge["from_node_id"]].append(edge)
    if any(sum((_fraction(edge["conditional_probability"]) for edge in rows), Fraction()) != Fraction(1, 1) for rows in outgoing.values()):
        return "rock_slide_graph_outgoing_conditional_probability_mass_invalid"
    if set(outgoing) != set(node_map): return "rock_slide_graph_unexpanded_or_unreachable_node"
    mass: dict[str, Fraction] = {root["node_id"]: Fraction(1, 1)}
    terminal_rows: list[dict[str, Any]] = []
    for node in sorted(node_map.values(), key=lambda row: row["recipient_cursor"]):
        source_mass = mass.get(node["node_id"], Fraction())
        if source_mass <= 0: return "rock_slide_graph_unreachable_node"
        for edge in outgoing[node["node_id"]]:
            path_probability = source_mass * _fraction(edge["conditional_probability"])
            if edge["terminal"]:
                terminal_rows.append({"terminal_edge_id": edge["edge_id"], "probability": path_probability, "ordered_recipient_outcomes": deepcopy(edge["terminal_consequences"]["ordered_recipient_outcomes"]), "source_path_reference": {"root_id": root["root_id"], "terminal_edge_id": edge["edge_id"], "from_node_id": edge["from_node_id"]}})
            else:
                target = edge["to_node_id"]
                mass[target] = mass.get(target, Fraction()) + path_probability
    terminal_mass = sum((row["probability"] for row in terminal_rows), Fraction())
    return {"terminal_mass": terminal_mass, "terminal_edge_ids": tuple(row["terminal_edge_id"] for row in terminal_rows), "terminal_rows": tuple(terminal_rows)}


def _scope(value: Any, base: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCOPE_SCHEMA:
        return False
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "acting_owner", "action_id", "move_id", "recipients")
    return all(value.get(key) == base.get(key) for key in keys) and value.get("move_id") == "rock-slide" and value.get("recipient_resolution_order") == "frozen_target_set_order" and all(value.get(key) == "recipient_local" for key in ("accuracy_uncertainty_scope", "critical_hit_uncertainty_scope", "damage_roll_uncertainty_scope"))


def _prior(rows: tuple[Any, ...], expected: tuple[Mapping[str, Any], ...]) -> bool:
    return all(isinstance(row, Mapping) and row.get("recipient") == recipient and row.get("recipient_index") == index for index, (row, recipient) in enumerate(zip(rows, expected), 1))
def _outcome(value: Any, node: Mapping[str, Any], recipients: tuple[Mapping[str, Any], ...], probability: Fraction, wide_guard_authority: Any, mat_block_authority: Any = None) -> bool:
    cursor = node["recipient_cursor"]
    if not isinstance(value, Mapping) or value.get("recipient_index") != cursor + 1 or value.get("recipient") != recipients[cursor] or _fraction(value.get("probability")) != probability or value.get("outcome") not in {"hit", "miss", "immune", "prevented_by_wide_guard", "prevented_by_mat_block"} or not isinstance(value.get("pre_hp"), int) or not isinstance(value.get("post_hp"), int) or value["pre_hp"] < 0 or value["post_hp"] < 0 or value["post_hp"] > value["pre_hp"] or value.get("fainted") is not (value["post_hp"] == 0): return False
    if value["outcome"] == "hit":
        flinch = value.get("flinch")
        if flinch is None:
            return value.get("hit_state") == "hit" and value.get("critical_state") in {"critical", "non_critical"} and isinstance(value.get("damage_roll"), Mapping)
        if not isinstance(flinch, Mapping) or flinch.get("state") not in {"flinched", "not_flinched"}: return False
        if flinch["state"] == "flinched":
            marker = flinch.get("hypothetical_target_flinch")
            if value.get("fainted") is True or not isinstance(marker, Mapping) or marker.get("state") != "flinched" or marker.get("provenance") != "rock_slide_recipient_successful_damage_roll_secondary_v1": return False
        return value.get("hit_state") == "hit" and value.get("critical_state") in {"critical", "non_critical"} and isinstance(value.get("damage_roll"), Mapping)
    if value["outcome"] == "prevented_by_wide_guard":
        return value.get("hit_state") == "not_applicable" and value.get("critical_state") == "not_applicable" and isinstance(value.get("damage_roll"), Mapping) and value["damage_roll"].get("status") == "not_applicable" and value.get("raw_damage") == 0 and value.get("actual_damage") == 0 and value.get("pre_hp") == value.get("post_hp") and value.get("wide_guard_applicability_authority") == wide_guard_authority and value.get("wide_guard_protected_recipient") == recipients[cursor]
    if value["outcome"] == "prevented_by_mat_block":
        return value.get("hit_state") == "not_applicable" and value.get("critical_state") == "not_applicable" and isinstance(value.get("damage_roll"), Mapping) and value["damage_roll"].get("status") == "not_applicable" and value.get("raw_damage") == 0 and value.get("actual_damage") == 0 and value.get("pre_hp") == value.get("post_hp") and value.get("mat_block_applicability_authority") == mat_block_authority and value.get("mat_block_protected_recipient") == recipients[cursor].get("owner")
    return value.get("critical_state") == "not_applicable" and isinstance(value.get("damage_roll"), Mapping) and value["damage_roll"].get("status") == "not_applicable"
def _terminal(value: Any, node: Mapping[str, Any], outcome: Mapping[str, Any], recipients: tuple[Mapping[str, Any], ...]) -> bool:
    rows = value.get("ordered_recipient_outcomes") if isinstance(value, Mapping) else None
    return isinstance(rows, tuple) and rows == (*node["prior_recipient_outcomes"], outcome) and len(rows) == len(recipients) and _prior(rows, recipients)
def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return None
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "action_id", "move_id", "recipients")
    if not all(key in value for key in keys) or value.get("move_id") != "rock-slide" or not isinstance(value.get("recipients"), tuple) or len(value["recipients"]) != 2: return None
    result = {key: deepcopy(value[key]) for key in keys}
    # The graph's attacker is the exact action-scope acting owner.  Keep both
    # labels in the private ledger binding so scope provenance cannot be
    # compared against an absent alias.
    result["acting_owner"] = deepcopy(value["attacker"])
    return result
def _fraction(value: Any) -> Fraction:
    try: return Fraction(value["numerator"], value["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return Fraction(-1, 1)
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
