"""Exact detached graph materialization for canonical escalating three-hit moves."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    _detached_target_hp_view, _has_life_orb, _hit_events, _sturdy_state,
)
from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import (
    SCHEMA_VERSION as EXECUTION_SCHEMA,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "detached-escalating-three-hit-predictive-graph-materialization-v1"
HORIZON = "immediate_action_consequence"
_MOVE_IDS = frozenset({"triple-axel", "triple-kick"})
_CANONICAL_POWERS = {"triple-axel": (20, 40, 60), "triple-kick": (10, 20, 30)}


def materialize_detached_escalating_three_hit_predictive_graph(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], execution_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize the ordered per-hit accuracy/DAG without flattening paths."""
    base = _base(strategy_d0, action, execution_authority)
    if base is None:
        return _result("rejected", "invalid_escalating_three_hit_materialization_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    if _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return _result("unsupported", "escalating_three_hit_item_consumption_unsupported", base)
    target_hp = _mapping(_mapping(_mapping(strategy_d0.get("strategy_state")).get("active")).get(base["target"]["side"])).get("current_hp")
    if not _integer(target_hp) or target_hp < 0:
        return _result("incomplete", "escalating_three_hit_target_hp_unknown", base)
    roots, nodes, edges, mass = _path_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
        target_hp=target_hp, sturdy_survival_authority=sturdy_survival_authority,
    )
    if isinstance(roots, Mapping):
        return _result(roots["status"], roots["reason"], base)
    if mass != Fraction(1, 1):
        return _result("rejected", "escalating_three_hit_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        **base,
        "terminal_leaf_representation": "exact_root_to_terminal_escalating_three_hit_path_graph_no_final_state_aggregation",
        "terminal_leaf_roots": tuple(_serialize_root(row) for row in roots),
        "terminal_leaf_nodes": tuple(deepcopy(row) for row in nodes),
        "terminal_leaf_edges": tuple(_serialize_edge(row) for row in edges),
        "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_ordered_hit_accuracy_critical_roll_damage_power_and_sturdy_identity_as_graph_paths",
        "provenance": "escalating_three_hit_execution_authority_to_detached_ordered_hit_path_graph_v1",
    }


def _path_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], target_hp: int, sturdy_survival_authority: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Fraction] | tuple[dict[str, str], None, None, None]:
    roots: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_index: dict[tuple[int, int, bool], str] = {}
    node_mass: dict[str, Fraction] = {}
    terminal_mass = Fraction()
    hit_factor, miss_factor = base["per_attempt_hit_probability"], base["per_attempt_miss_probability"]

    def add_node(index: int, hp: int, consumed: bool) -> str:
        key = (index, hp, consumed)
        if key in node_index:
            return node_index[key]
        node_id = f"hit:{index}/hp:{hp}/sturdy:{'consumed' if consumed else 'available'}"
        node_index[key] = node_id
        nodes.append({"node_id": node_id, "hit_index": index, "target_hp": hp, "sturdy_consumed": consumed})
        node_mass[node_id] = Fraction()
        return node_id

    root = add_node(1, target_hp, False)
    roots.append({"root_id": "hit:1", "probability": Fraction(1, 1), "terminal": False, "node_id": root})
    node_mass[root] = Fraction(1, 1)
    event_cache: dict[tuple[int, bool, int], list[dict[str, Any]] | dict[str, str]] = {}
    cursor = 0
    while cursor < len(nodes):
        node = nodes[cursor]; cursor += 1
        source_mass = node_mass[node["node_id"]]
        if not source_mass:
            continue
        hit_index = node["hit_index"]
        power = base["powers"][hit_index - 1]
        hit_probability = hit_factor if base["execution_plan"] == "sequential_accuracy_per_hit" or hit_index == 1 else Fraction(1, 1)
        miss_probability = miss_factor if base["execution_plan"] == "sequential_accuracy_per_hit" or hit_index == 1 else Fraction()
        if miss_probability:
            edges.append({
                "edge_id": f"{node['node_id']}/hit:{hit_index}:miss", "from_node_id": node["node_id"],
                "conditional_probability": miss_probability,
                "hit_outcome": {"hit_index": hit_index, "base_power": power, "outcome": "miss"},
                "terminal": True, "terminal_reason": "first_miss_terminates_remaining_hits",
                "terminal_consequences": _consequences(base, node["target_hp"], sturdy_survival_authority, node["sturdy_consumed"], hit_index - 1),
            })
            terminal_mass += source_mass * miss_probability
        if not hit_probability:
            continue
        can_use_sturdy = not node["sturdy_consumed"] and _sturdy_full_hp(sturdy_survival_authority, node["target_hp"])
        cache_key = (node["target_hp"], can_use_sturdy, power)
        events = event_cache.get(cache_key)
        if events is None:
            current_d0, current_snapshot = (strategy_d0, runtime_snapshot) if node["target_hp"] == target_hp else _detached_target_hp_view(runtime_snapshot=runtime_snapshot, decision_owner=base["attacker"], target=base["target"], target_hp=node["target_hp"])
            if current_d0 is None or current_snapshot is None:
                return {"status": "rejected", "reason": "escalating_three_hit_intermediate_target_state_invalid"}, None, None, None
            move = deepcopy(base["single_hit_metadata_view"]); move["power"] = power
            events = _hit_events(strategy_d0=current_d0, runtime_snapshot=current_snapshot, base=base, single_metadata=move, sturdy_survival_authority=sturdy_survival_authority if can_use_sturdy else None)
            event_cache[cache_key] = events
        if isinstance(events, Mapping):
            return {"status": events["status"], "reason": events["reason"]}, None, None, None
        for event in events:
            factor = event.get("probability")
            if not isinstance(factor, Fraction):
                return {"status": "rejected", "reason": "escalating_three_hit_per_hit_probability_invalid"}, None, None, None
            row = deepcopy(dict(event)); row["hit_index"] = hit_index; row["base_power"] = power
            consumed = bool(node["sturdy_consumed"] or row["sturdy_applied"])
            terminal = row["post_hp"] == 0 or hit_index == 3
            edge = {"edge_id": f"{node['node_id']}/hit:{hit_index}:landed:{row['critical_state']}:roll:{row['roll_index']}", "from_node_id": node["node_id"], "conditional_probability": hit_probability * factor, "hit_outcome": {"hit_index": hit_index, "base_power": power, "outcome": "hit", "ordered_hit": row}, "terminal": terminal}
            if terminal:
                edge["terminal_reason"] = "target_fainted" if row["post_hp"] == 0 else "all_three_hits_landed"
                edge["terminal_consequences"] = _consequences(base, row["post_hp"], sturdy_survival_authority, consumed, hit_index)
                terminal_mass += source_mass * hit_probability * factor
            else:
                next_node = add_node(hit_index + 1, row["post_hp"], consumed)
                edge["to_node_id"] = next_node
                node_mass[next_node] += source_mass * hit_probability * factor
            edges.append(edge)
    return roots, nodes, edges, terminal_mass


def _base(d0: Any, action: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(action, Mapping) or not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != EXECUTION_SCHEMA:
        return None
    attacker = d0.get("decision_owner")
    target = _mapping(d0.get("active_owners")).get("opponent" if isinstance(attacker, Mapping) and attacker.get("side") == "self" else "self")
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": attacker, "action_id": action.get("action_id")}
    if any(authority.get(key) != value for key, value in expected.items()) or authority.get("attacker") != attacker or authority.get("target") != target:
        return None
    metadata = _mapping(_mapping(authority.get("move_metadata_authority")).get("metadata"))
    powers = _powers(authority.get("per_hit_power_execution"), metadata.get("move_id"))
    accuracy = _probabilities(_mapping(authority.get("per_attempt_accuracy_execution")))
    critical = _mapping(authority.get("per_hit_critical_execution"))
    modifier = _mapping(authority.get("modifier_authority")); execution_plan = modifier.get("execution_plan")
    if metadata.get("move_id") != action.get("identity") or metadata.get("move_id") not in _MOVE_IDS or powers is None or accuracy is None or execution_plan not in {"sequential_accuracy_per_hit", "single_initial_accuracy_then_guaranteed_remaining_hits"} or critical.get("semantics") != "independent_canonical_critical_roll_per_landed_hit" or not isinstance(critical.get("per_hit_critical_probability"), Mapping):
        return None
    own = _mapping(_mapping(_mapping(d0.get("strategy_state")).get("active")).get(attacker.get("side") if isinstance(attacker, Mapping) else None)).get("current_hp")
    if not _integer(own) or own < 0:
        return None
    single = deepcopy(dict(metadata)); single.pop("min_hits", None); single.pop("max_hits", None)
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(attacker)), "action_id": action["action_id"], "move_id": metadata["move_id"], "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "own_current_hp": own, "powers": powers, "execution_plan": execution_plan, "per_attempt_hit_probability": accuracy[0], "per_attempt_miss_probability": accuracy[1], "per_hit_critical_execution": deepcopy(dict(critical)), "single_hit_metadata_view": single, "execution_authority": deepcopy(dict(authority))}


def _powers(value: Any, move_id: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("semantics") != "canonical_ordered_base_power_escalation" or not isinstance(value.get("hits"), list) or len(value["hits"]) != 3:
        return None
    rows = value["hits"]
    if any(not isinstance(row, Mapping) or row.get("hit_index") != index or not _integer(row.get("base_power")) or row["base_power"] <= 0 for index, row in enumerate(rows, 1)):
        return None
    powers = tuple(row["base_power"] for row in rows)
    return powers if powers == _CANONICAL_POWERS.get(move_id) else None  # type: ignore[return-value]


def _probabilities(value: Mapping[str, Any]) -> tuple[Fraction, Fraction] | None:
    try:
        hit = Fraction(value["hit_probability"]["numerator"], value["hit_probability"]["denominator"]); miss = Fraction(value["miss_probability"]["numerator"], value["miss_probability"]["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    return (hit, miss) if hit >= 0 and miss >= 0 and hit + miss == 1 and value.get("root_mass") == {"numerator": 1, "denominator": 1} else None


def _sturdy_full_hp(authority: Mapping[str, Any] | None, hp: int) -> bool:
    return isinstance(authority, Mapping) and authority.get("status") == "ready" and authority.get("post_entry_hp") == authority.get("maximum_hp") == hp


def _consequences(base: Mapping[str, Any], target_hp: int, sturdy: Mapping[str, Any] | None, consumed: bool, landed: int) -> dict[str, Any]:
    return {"own_final_hp": base["own_current_hp"], "self_fainted": False, "target_final_hp": target_hp, "target_ko": target_hp == 0, "landed_hit_count": landed, "deterministic_stage_effect": None, "secondary": None, "sturdy": _sturdy_state(sturdy, consumed=consumed)}


def _serialize_root(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["probability"] = _fd(result["probability"]); return result


def _serialize_edge(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["conditional_probability"] = _fd(result["conditional_probability"])
    hit = _mapping(_mapping(result.get("hit_outcome")).get("ordered_hit"))
    if hit:
        hit["probability"] = _fd(hit["probability"]); result["hit_outcome"]["ordered_hit"] = hit
    return result


def _mapping(value: Any) -> Mapping[str, Any]: return value if isinstance(value, Mapping) else {}
def _integer(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool)
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
