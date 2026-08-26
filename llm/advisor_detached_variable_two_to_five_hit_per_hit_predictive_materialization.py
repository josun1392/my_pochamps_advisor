"""Exact path-graph materialization for bounded ordinary 2--5-hit attacks.

The five-hit critical/roll cartesian product is intentionally represented as
an immutable terminal-path graph, rather than a flattened list that can grow
past tens of millions of leaves.  A root-to-terminal graph path is one exact
terminal leaf; graph edges retain every ordered hit/crit/roll identity.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    _detached_target_hp_view, _has_life_orb, _hit_events, _sturdy_state,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import SCHEMA_VERSION as EXECUTION_SCHEMA
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_strict_hit_probability_assessment,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "detached-variable-two-to-five-hit-per-hit-predictive-materialization-v1"
HORIZON = "immediate_action_consequence"
_SUPPORTED_MOVE_IDS = frozenset({"bullet-seed", "rock-blast"})


def materialize_detached_variable_two_to_five_hit_per_hit_predictive_leaves(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], execution_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze exact action accuracy, count, and ordered per-hit path edges."""
    base = _base(strategy_d0, action, execution_authority)
    if base is None:
        return _result("rejected", "invalid_variable_multi_hit_materialization_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    metadata = execution_authority["move_metadata_authority"]["metadata"]
    single = _single_hit_metadata(metadata)
    if single is None:
        return _result("rejected", "variable_multi_hit_single_hit_metadata_adapter_invalid", base)
    hit = build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=base["attacker"], target=base["target"], selected_move=single,
    )
    if hit.get("status") != "resolved":
        return _result(hit.get("status", "rejected"), hit.get("reason", "variable_multi_hit_action_accuracy_unavailable"), base)
    accuracy = hit.get("probability_percent")
    if not _percent(accuracy):
        return _result("rejected", "variable_multi_hit_action_accuracy_invalid", base)
    if _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return _result("unsupported", "variable_multi_hit_item_consumption_unsupported", base)
    target_hp = strategy_d0.get("strategy_state", {}).get("active", {}).get(base["target"]["side"], {}).get("current_hp")
    if not _integer(target_hp) or target_hp < 0:
        return _result("incomplete", "variable_multi_hit_target_hp_unknown", base)
    roots, nodes, edges, terminal_mass = _path_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
        single_metadata=single, hit_count_distribution=base["hit_count_distribution"],
        action_accuracy=accuracy, target_hp=target_hp,
        sturdy_survival_authority=sturdy_survival_authority,
    )
    if isinstance(roots, Mapping):
        return _result(roots["status"], roots["reason"], base)
    if terminal_mass != Fraction(1, 1):
        return _result("rejected", "variable_multi_hit_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(terminal_mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        **base, "action_accuracy": deepcopy(hit), "single_hit_metadata_view": single,
        "terminal_leaf_representation": "exact_root_to_terminal_path_graph_no_final_state_aggregation",
        "terminal_leaf_roots": tuple(_serialize_root(row) for row in roots),
        "terminal_leaf_nodes": tuple(_serialize_node(row) for row in nodes),
        "terminal_leaf_edges": tuple(_serialize_edge(row) for row in edges),
        "terminal_probability_mass": _fd(terminal_mass),
        "aggregation": "none_preserve_ordered_per_hit_critical_roll_and_sturdy_identity_as_graph_paths",
        "provenance": "variable_two_to_five_hit_count_authority_to_detached_ordered_per_hit_path_graph_v1",
    }


def _path_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], single_metadata: Mapping[str, Any], hit_count_distribution: tuple[tuple[int, Fraction], ...], action_accuracy: int, target_hp: int, sturdy_survival_authority: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Fraction] | tuple[dict[str, str], None, None, None]:
    roots: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_index: dict[tuple[int, int, int, bool], str] = {}
    node_mass: dict[str, Fraction] = {}
    terminal_mass = Fraction()
    hit_factor = Fraction(action_accuracy, 100)
    miss_factor = Fraction(100 - action_accuracy, 100)
    if miss_factor:
        roots.append({"root_id": "miss", "probability": miss_factor, "terminal": True, "selected_hit_count": None, "consequences": _miss_consequences(base, target_hp, sturdy_survival_authority)})
        terminal_mass += miss_factor

    def add_node(selected: int, completed: int, hp: int, consumed: bool) -> str:
        key = (selected, completed, hp, consumed)
        existing = node_index.get(key)
        if existing is not None:
            return existing
        node_id = f"hits:{selected}/completed:{completed}/hp:{hp}/sturdy:{'consumed' if consumed else 'available'}"
        node_index[key] = node_id
        nodes.append({"node_id": node_id, "selected_hit_count": selected, "completed_hit_count": completed, "target_hp": hp, "sturdy_consumed": consumed})
        node_mass[node_id] = Fraction()
        return node_id

    for selected, factor in hit_count_distribution:
        node = add_node(selected, 0, target_hp, False)
        probability = hit_factor * factor
        roots.append({"root_id": f"hit_count:{selected}", "probability": probability, "terminal": False, "selected_hit_count": selected, "node_id": node})
        node_mass[node] += probability

    event_cache: dict[tuple[int, bool], list[dict[str, Any]] | dict[str, str]] = {}
    cursor = 0
    while cursor < len(nodes):
        node = nodes[cursor]; cursor += 1
        source_mass = node_mass[node["node_id"]]
        if not source_mass:
            continue
        can_use_sturdy = not node["sturdy_consumed"] and _sturdy_full_hp(sturdy_survival_authority, node["target_hp"])
        cache_key = (node["target_hp"], can_use_sturdy)
        events = event_cache.get(cache_key)
        if events is None:
            current_d0, current_snapshot = (strategy_d0, runtime_snapshot) if node["target_hp"] == target_hp else _detached_target_hp_view(runtime_snapshot=runtime_snapshot, decision_owner=base["attacker"], target=base["target"], target_hp=node["target_hp"])
            if current_d0 is None or current_snapshot is None:
                return {"status": "rejected", "reason": "variable_multi_hit_intermediate_target_state_invalid"}, None, None, None
            events = _hit_events(strategy_d0=current_d0, runtime_snapshot=current_snapshot, base=base, single_metadata=single_metadata, sturdy_survival_authority=sturdy_survival_authority if can_use_sturdy else None)
            event_cache[cache_key] = events
        if isinstance(events, Mapping):
            return {"status": events["status"], "reason": events["reason"]}, None, None, None
        hit_index = node["completed_hit_count"] + 1
        for event in events:
            probability = event["probability"]
            if not isinstance(probability, Fraction):
                return {"status": "rejected", "reason": "variable_multi_hit_per_hit_probability_invalid"}, None, None, None
            event_row = deepcopy(dict(event))
            event_row["hit_index"] = hit_index
            event_row["selected_hit_count"] = node["selected_hit_count"]
            consumed = bool(node["sturdy_consumed"] or event_row["sturdy_applied"])
            terminal = event_row["post_hp"] == 0 or hit_index == node["selected_hit_count"]
            edge = {"edge_id": f"{node['node_id']}/hit:{hit_index}:{event_row['critical_state']}:roll:{event_row['roll_index']}", "from_node_id": node["node_id"], "conditional_probability": probability, "ordered_hit": event_row, "terminal": terminal}
            if terminal:
                edge["terminal_consequences"] = _consequences(base, event_row["post_hp"], sturdy_survival_authority, consumed)
                terminal_mass += source_mass * probability
            else:
                next_node = add_node(node["selected_hit_count"], hit_index, event_row["post_hp"], consumed)
                edge["to_node_id"] = next_node
                node_mass[next_node] += source_mass * probability
            edges.append(edge)
    return roots, nodes, edges, terminal_mass


def _base(d0: Any, action: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(action, Mapping) or not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != EXECUTION_SCHEMA:
        return None
    attacker = d0.get("decision_owner")
    target = d0.get("active_owners", {}).get("opponent" if isinstance(attacker, Mapping) and attacker.get("side") == "self" else "self")
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": attacker, "action_id": action.get("action_id")}
    if any(authority.get(key) != value for key, value in expected.items()) or authority.get("attacker") != attacker or authority.get("target") != target:
        return None
    metadata = authority.get("move_metadata_authority", {}).get("metadata") if isinstance(authority.get("move_metadata_authority"), Mapping) else None
    critical = authority.get("per_hit_critical_execution")
    distribution = _distribution(authority.get("hit_count_execution"))
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != action.get("identity") or metadata.get("move_id") not in _SUPPORTED_MOVE_IDS or not isinstance(critical, Mapping) or critical.get("semantics") != "independent_canonical_critical_roll_per_hit" or not isinstance(critical.get("per_hit_critical_probability"), Mapping) or distribution is None:
        return None
    own_hp = d0.get("strategy_state", {}).get("active", {}).get(attacker.get("side") if isinstance(attacker, Mapping) else None, {}).get("current_hp")
    if not _integer(own_hp) or own_hp < 0:
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(attacker)), "action_id": action["action_id"], "move_id": metadata["move_id"], "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "own_current_hp": own_hp, "per_hit_critical_execution": deepcopy(dict(critical)), "hit_count_distribution": distribution, "execution_authority": deepcopy(dict(authority))}


def _distribution(value: Any) -> tuple[tuple[int, Fraction], ...] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("root_mass") != {"numerator": 1, "denominator": 1} or not isinstance(value.get("distribution"), tuple):
        return None
    rows: list[tuple[int, Fraction]] = []
    for row in value["distribution"]:
        try:
            count, fraction = row["hit_count"], Fraction(row["probability"]["numerator"], row["probability"]["denominator"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None
        if not _integer(count) or count not in {2, 3, 4, 5} or fraction <= 0:
            return None
        rows.append((count, fraction))
    # A strict modifier authority may reduce the canonical family to an exact
    # subset (Skill Link: five; Loaded Dice: four/five).  Each row remains a
    # valid ordinary 2--5-hit count and the authority must still own unit mass.
    return tuple(sorted(rows)) if len({count for count, _ in rows}) == len(rows) and sum((probability for _, probability in rows), Fraction()) == Fraction(1, 1) else None


def _single_hit_metadata(metadata: Mapping[str, Any]) -> dict[str, Any] | None:
    value = deepcopy(dict(metadata)); value.pop("min_hits", None); value.pop("max_hits", None)
    return value if value.get("move_id") in _SUPPORTED_MOVE_IDS else None


def _sturdy_full_hp(authority: Mapping[str, Any] | None, hp: int) -> bool:
    return isinstance(authority, Mapping) and authority.get("status") == "ready" and authority.get("post_entry_hp") == authority.get("maximum_hp") == hp


def _consequences(base: Mapping[str, Any], target_hp: int, sturdy_authority: Mapping[str, Any] | None, consumed: bool) -> dict[str, Any]:
    return {"own_final_hp": base["own_current_hp"], "self_fainted": False, "target_final_hp": target_hp, "target_ko": target_hp == 0, "deterministic_stage_effect": None, "secondary": None, "sturdy": _sturdy_state(sturdy_authority, consumed=consumed)}


def _miss_consequences(base: Mapping[str, Any], target_hp: int, sturdy_authority: Mapping[str, Any] | None) -> dict[str, Any]:
    return _consequences(base, target_hp, sturdy_authority, False)


def _serialize_root(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["probability"] = _fd(result["probability"]); return result


def _serialize_node(value: Mapping[str, Any]) -> dict[str, Any]: return deepcopy(dict(value))


def _serialize_edge(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["conditional_probability"] = _fd(result["conditional_probability"]); result["ordered_hit"]["probability"] = _fd(result["ordered_hit"]["probability"]); return result


def _percent(value: Any) -> bool: return _integer(value) and 0 <= value <= 100
def _integer(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool)
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
