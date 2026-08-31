"""Exact detached Population Bomb attempt graph materialization.

Each node owns the next independent accuracy check.  This deliberately keeps
the ten-attempt process as a compressed DAG rather than manufacturing either
an action-level accuracy branch or a flat Cartesian terminal-leaf list.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    _apply_reactive, _detached_target_hp_view, _event_with_reactive, _has_life_orb, _hit_events, _sturdy_state,
)
from llm.advisor_focus_sash_survival import focus_sash_state
from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import (
    SCHEMA_VERSION as EXECUTION_SCHEMA,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "detached-population-bomb-per-hit-accuracy-predictive-graph-materialization-v1"
HORIZON = "immediate_action_consequence"
_MOVE_ID = "population-bomb"
_MAX_ATTEMPTS = 10


def materialize_detached_population_bomb_per_hit_accuracy_predictive_graph(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], execution_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any] | None = None,
    focus_sash_survival_authority: Mapping[str, Any] | None = None,
    contact_reactive_contact_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize one exact independent-accuracy graph for Population Bomb."""
    base = _base(strategy_d0, action, execution_authority)
    if base is None:
        return _result("rejected", "invalid_population_bomb_materialization_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    if _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return _result("unsupported", "population_bomb_item_consumption_unsupported", base)
    target_hp = strategy_d0.get("strategy_state", {}).get("active", {}).get(base["target"]["side"], {}).get("current_hp")
    if not _integer(target_hp) or target_hp < 0:
        return _result("incomplete", "population_bomb_target_hp_unknown", base)
    roots, nodes, edges, mass = _path_graph(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
        target_hp=target_hp, sturdy_survival_authority=sturdy_survival_authority,
        focus_sash_survival_authority=focus_sash_survival_authority,
        contact_reactive_contact_authority=contact_reactive_contact_authority,
    )
    if isinstance(roots, Mapping):
        return _result(roots["status"], roots["reason"], base)
    if mass != Fraction(1, 1):
        return _result("rejected", "population_bomb_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        **base,
        "terminal_leaf_representation": "exact_root_to_terminal_per_attempt_accuracy_path_graph_no_final_state_aggregation",
        "terminal_leaf_roots": tuple(_serialize_root(row) for row in roots),
        "terminal_leaf_nodes": tuple(deepcopy(row) for row in nodes),
        "terminal_leaf_edges": tuple(_serialize_edge(row) for row in edges),
        "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_ordered_attempt_hit_miss_critical_roll_damage_and_sturdy_identity_as_graph_paths",
        "provenance": "population_bomb_per_attempt_accuracy_execution_authority_to_detached_ordered_attempt_path_graph_v1",
    }


def _path_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], target_hp: int, sturdy_survival_authority: Mapping[str, Any] | None, focus_sash_survival_authority: Mapping[str, Any] | None, contact_reactive_contact_authority: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Fraction] | tuple[dict[str, str], None, None, None]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    plan = _mapping(_mapping(base["execution_authority"]).get("modifier_authority")).get("modifier_execution_plan")
    kind = _mapping(plan).get("kind")
    if kind == "existing_independent_multiaccuracy":
        planned_counts = ((_MAX_ATTEMPTS, Fraction(1, 1)),)
    elif kind == "single_accuracy_then_fixed_guaranteed_hits" and plan.get("count") == _MAX_ATTEMPTS:
        planned_counts = ((_MAX_ATTEMPTS, Fraction(1, 1)),)
    elif kind == "single_accuracy_then_uniform_guaranteed_hits" and tuple(plan.get("support", ())) == tuple(range(4, 11)) and _fraction_value(plan.get("conditional_probability")) == Fraction(1, 7):
        planned_counts = tuple((count, Fraction(1, 7)) for count in range(4, 11))
    else:
        return {"status": "rejected", "reason": "population_bomb_modifier_execution_plan_invalid"}, None, None, None
    roots = [{"root_id": f"planned-hits:{count}", "probability": probability, "terminal": False,
              "node_id": f"attempt:1/landed:0/max:{count}/hp:{target_hp}/sturdy:available/focus-sash:available",
              "modifier_execution_plan": kind, "selected_hit_count": count if kind == "single_accuracy_then_uniform_guaranteed_hits" else None}
             for count, probability in planned_counts]
    node_index: dict[tuple[int, int, int, int, bool, bool, int], str] = {}
    node_mass: dict[str, Fraction] = {}
    terminal_mass = Fraction()
    hit_factor, miss_factor = base["per_attempt_hit_probability"], base["per_attempt_miss_probability"]

    def add_node(attempt: int, landed: int, maximum: int, hp: int, sturdy_consumed: bool, focus_sash_consumed: bool, attacker_hp: int) -> str:
        key = (attempt, landed, maximum, hp, sturdy_consumed, focus_sash_consumed, attacker_hp)
        existing = node_index.get(key)
        if existing is not None:
            return existing
        node_id = f"attempt:{attempt}/landed:{landed}/max:{maximum}/hp:{hp}/attacker-hp:{attacker_hp}/sturdy:{'consumed' if sturdy_consumed else 'available'}/focus-sash:{'consumed' if focus_sash_consumed else 'available'}"
        node_index[key] = node_id
        nodes.append({"node_id": node_id, "attempt_index": attempt, "landed_hit_count": landed, "maximum_attempts": maximum, "target_hp": hp, "attacker_hp": attacker_hp, "sturdy_consumed": sturdy_consumed, "focus_sash_consumed": focus_sash_consumed})
        node_mass[node_id] = Fraction()
        return node_id

    for root_row, (maximum, probability) in zip(roots, planned_counts):
        root = add_node(1, 0, maximum, target_hp, False, False, base["own_current_hp"])
        root_row["node_id"] = root
        node_mass[root] += probability
    event_cache: dict[tuple[int, bool, bool, bool], list[dict[str, Any]] | dict[str, str]] = {}
    cursor = 0
    while cursor < len(nodes):
        node = nodes[cursor]; cursor += 1
        source_mass = node_mass[node["node_id"]]
        if not source_mass:
            continue
        attempt = node["attempt_index"]
        hit_probability = hit_factor if kind == "existing_independent_multiaccuracy" or attempt == 1 else Fraction(1, 1)
        miss_probability = miss_factor if kind == "existing_independent_multiaccuracy" or attempt == 1 else Fraction()
        if miss_probability:
            edges.append({
                "edge_id": f"{node['node_id']}/attempt:{attempt}:miss", "from_node_id": node["node_id"],
                "conditional_probability": miss_probability, "attempt_outcome": {"attempt_index": attempt, "outcome": "miss"},
                "terminal": True, "terminal_reason": "first_miss_terminates_remaining_attempts",
                "terminal_consequences": _consequences(base, node["target_hp"], sturdy_survival_authority, node["sturdy_consumed"], focus_sash_survival_authority, node["focus_sash_consumed"], node["landed_hit_count"]),
            })
            terminal_mass += source_mass * miss_probability
        if not hit_probability:
            continue
        can_use_sturdy = not node["sturdy_consumed"] and _sturdy_full_hp(sturdy_survival_authority, node["target_hp"])
        can_use_focus_sash = not node["focus_sash_consumed"] and _focus_sash_full_hp(focus_sash_survival_authority, node["target_hp"])
        cache_key = (node["target_hp"], can_use_sturdy, can_use_focus_sash, bool(node["focus_sash_consumed"]))
        events = event_cache.get(cache_key)
        if events is None:
            current_d0, current_snapshot = (strategy_d0, runtime_snapshot) if node["target_hp"] == target_hp and not node["focus_sash_consumed"] else _detached_target_hp_view(
                runtime_snapshot=runtime_snapshot, decision_owner=base["attacker"], target=base["target"], target_hp=node["target_hp"], focus_sash_consumed=bool(node["focus_sash_consumed"]),
            )
            if current_d0 is None or current_snapshot is None:
                return {"status": "rejected", "reason": "population_bomb_intermediate_target_state_invalid"}, None, None, None
            events = _hit_events(
                strategy_d0=current_d0, runtime_snapshot=current_snapshot, base=base,
                single_metadata=base["single_hit_metadata_view"],
                sturdy_survival_authority=sturdy_survival_authority if can_use_sturdy else None,
                focus_sash_survival_authority=focus_sash_survival_authority if can_use_focus_sash else None,
            )
            event_cache[cache_key] = events
        if isinstance(events, Mapping):
            return {"status": events["status"], "reason": events["reason"]}, None, None, None
        for event in events:
            factor = event.get("probability")
            if not isinstance(factor, Fraction):
                return {"status": "rejected", "reason": "population_bomb_per_hit_probability_invalid"}, None, None, None
            row = deepcopy(dict(event))
            row["attempt_index"] = attempt
            row["hit_index"] = node["landed_hit_count"] + 1
            reactive = _apply_reactive(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action={"action_id": base["action_id"], "identity": base["move_id"]}, contact_authority=contact_reactive_contact_authority, event=row, hit_index=row["hit_index"], attacker_hp=node["attacker_hp"])
            if isinstance(reactive, Mapping) and reactive.get("status") != "resolved":
                return {"status": reactive.get("status", "rejected"), "reason": reactive.get("reason", "population_bomb_contact_reactive_damage_unavailable")}, None, None, None
            attacker_hp = reactive["post_hp"] if isinstance(reactive, Mapping) else node["attacker_hp"]
            row = _event_with_reactive(row, reactive)
            sturdy_consumed = bool(node["sturdy_consumed"] or row["sturdy_applied"])
            focus_sash_consumed = bool(node["focus_sash_consumed"] or row["focus_sash_applied"])
            terminal = row["post_hp"] == 0 or attacker_hp == 0 or attempt == node["maximum_attempts"]
            edge = {
                "edge_id": f"{node['node_id']}/attempt:{attempt}:hit:{row['critical_state']}:roll:{row['roll_index']}",
                "from_node_id": node["node_id"], "conditional_probability": hit_probability * factor,
                "attempt_outcome": {"attempt_index": attempt, "outcome": "hit", "ordered_hit": row}, "terminal": terminal,
            }
            if terminal:
                edge["terminal_reason"] = "target_fainted" if row["post_hp"] == 0 else "attacker_fainted_from_contact_reactive_damage" if attacker_hp == 0 else ("maximum_ten_attempts_reached" if kind == "existing_independent_multiaccuracy" else "planned_hit_count_reached")
                edge["terminal_consequences"] = _consequences(base, row["post_hp"], sturdy_survival_authority, sturdy_consumed, focus_sash_survival_authority, focus_sash_consumed, node["landed_hit_count"] + 1, attacker_hp=attacker_hp, terminal_reason=edge["terminal_reason"])
                terminal_mass += source_mass * hit_probability * factor
            else:
                next_node = add_node(attempt + 1, node["landed_hit_count"] + 1, node["maximum_attempts"], row["post_hp"], sturdy_consumed, focus_sash_consumed, attacker_hp)
                edge["to_node_id"] = next_node
                node_mass[next_node] += source_mass * hit_probability * factor
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
    metadata = _mapping(authority.get("move_metadata_authority")).get("metadata")
    maximum = _mapping(authority.get("maximum_attempt_execution"))
    accuracy = _mapping(authority.get("per_attempt_accuracy_execution"))
    critical = _mapping(authority.get("per_hit_critical_execution"))
    probabilities = _probabilities(accuracy)
    modifier = _mapping(authority.get("modifier_authority"))
    plan = _mapping(modifier.get("modifier_execution_plan"))
    if plan.get("kind") not in {"existing_independent_multiaccuracy", "single_accuracy_then_fixed_guaranteed_hits", "single_accuracy_then_uniform_guaranteed_hits"}:
        return None
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != action.get("identity") or metadata.get("move_id") != _MOVE_ID or maximum.get("status") != "resolved" or maximum.get("maximum_attempts") != _MAX_ATTEMPTS or maximum.get("semantics") != "canonical_fixed_ten_attempt_multiaccuracy" or accuracy.get("semantics") != "independent_accuracy_check_per_attempt_stop_on_first_miss" or probabilities is None or critical.get("semantics") != "independent_canonical_critical_roll_per_landed_hit" or not isinstance(critical.get("per_hit_critical_probability"), Mapping):
        return None
    own_hp = _mapping(_mapping(d0.get("strategy_state")).get("active")).get(attacker.get("side") if isinstance(attacker, Mapping) else None)
    if not _integer(_mapping(own_hp).get("current_hp")) or _mapping(own_hp)["current_hp"] < 0:
        return None
    single = deepcopy(dict(metadata)); single.pop("min_hits", None); single.pop("max_hits", None)
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(attacker)), "action_id": action["action_id"], "move_id": _MOVE_ID, "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "own_current_hp": _mapping(own_hp)["current_hp"], "per_attempt_hit_probability": probabilities[0], "per_attempt_miss_probability": probabilities[1], "per_hit_critical_execution": deepcopy(dict(critical)), "single_hit_metadata_view": single, "execution_authority": deepcopy(dict(authority))}


def _probabilities(value: Mapping[str, Any]) -> tuple[Fraction, Fraction] | None:
    try:
        hit = Fraction(value["hit_probability"]["numerator"], value["hit_probability"]["denominator"])
        miss = Fraction(value["miss_probability"]["numerator"], value["miss_probability"]["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    return (hit, miss) if hit >= 0 and miss >= 0 and hit + miss == Fraction(1, 1) and value.get("root_mass") == {"numerator": 1, "denominator": 1} else None


def _fraction_value(value: Any) -> Fraction | None:
    try:
        return Fraction(value["numerator"], value["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def _sturdy_full_hp(authority: Mapping[str, Any] | None, hp: int) -> bool:
    return isinstance(authority, Mapping) and authority.get("status") == "ready" and authority.get("post_entry_hp") == authority.get("maximum_hp") == hp


def _focus_sash_full_hp(authority: Mapping[str, Any] | None, hp: int) -> bool:
    return isinstance(authority, Mapping) and authority.get("status") == "ready" and authority.get("current_hp") == authority.get("maximum_hp") == hp


def _consequences(base: Mapping[str, Any], target_hp: int, sturdy_authority: Mapping[str, Any] | None, sturdy_consumed: bool, focus_sash_authority: Mapping[str, Any] | None, focus_sash_consumed: bool, landed: int, *, attacker_hp: int | None = None, terminal_reason: str | None = None) -> dict[str, Any]:
    own_hp = base["own_current_hp"] if attacker_hp is None else attacker_hp
    return {"own_final_hp": own_hp, "self_fainted": own_hp == 0, "target_final_hp": target_hp, "target_ko": target_hp == 0, "landed_hit_count": landed, **({"terminal_reason": terminal_reason} if terminal_reason else {}), "deterministic_stage_effect": None, "secondary": None, "sturdy": _sturdy_state(sturdy_authority, consumed=sturdy_consumed), "focus_sash": focus_sash_state(focus_sash_authority, consumed=focus_sash_consumed)}


def _serialize_root(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["probability"] = _fd(result["probability"]); return result


def _serialize_edge(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["conditional_probability"] = _fd(result["conditional_probability"])
    hit = _mapping(_mapping(result.get("attempt_outcome")).get("ordered_hit"))
    if hit:
        hit["probability"] = _fd(hit["probability"])
        result["attempt_outcome"]["ordered_hit"] = hit
    return result


def _mapping(value: Any) -> Mapping[str, Any]: return value if isinstance(value, Mapping) else {}
def _integer(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool)
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
