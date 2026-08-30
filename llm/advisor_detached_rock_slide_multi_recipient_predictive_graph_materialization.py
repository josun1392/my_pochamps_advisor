"""Exact detached recipient-local Rock Slide outcome graph (doubles v1)."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import _has_life_orb
from llm.advisor_predictive_damage_roll_uncertainty import project_predictive_damage_roll_uncertainty
from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval
from llm.advisor_predictive_normal_formula_post_hit import compose_predictive_normal_formula_post_hit
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import SCHEMA_VERSION as EXECUTION_SCOPE_SCHEMA
from llm.advisor_detached_rock_slide_intermediate_state_vector import CONSUMER_SCHEMA_VERSION
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_strategy_d0,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "detached-rock-slide-multi-recipient-predictive-graph-materialization-v1"
HORIZON = "immediate_action_consequence"
_MOVE_ID = "rock-slide"


def materialize_detached_rock_slide_multi_recipient_predictive_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], execution_scope_authority: Mapping[str, Any], frozen_scope_consumer_adapter: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Expand frozen recipients in order, retaining a graph rather than leaves."""
    adapter = _consumer_adapter(frozen_scope_consumer_adapter, action, execution_scope_authority)
    if isinstance(adapter, str): return _result("rejected", adapter, {})
    if isinstance(adapter, Mapping): strategy_d0, runtime_snapshot, execution_scope_authority, base = adapter["strategy_d0"], adapter["runtime_snapshot"], adapter["scope"], adapter["base"]
    else: base = _base(strategy_d0, action, execution_scope_authority)
    if base is None:
        return _result("rejected", "invalid_rock_slide_multi_recipient_graph_request", {})
    if frozen_scope_consumer_adapter is None and runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    if _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return _result("unsupported", "rock_slide_multi_recipient_item_consumption_unsupported", base)
    roots, nodes, edges, mass = _graph(strategy_d0, runtime_snapshot, base)
    if isinstance(roots, Mapping):
        return _result(roots["status"], roots["reason"], base)
    if mass != Fraction(1, 1):
        return _result("rejected", "rock_slide_multi_recipient_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
        "terminal_leaf_representation": "exact_root_to_terminal_ordered_multi_recipient_path_graph_no_terminal_flattening",
        "terminal_leaf_roots": tuple(_root(row) for row in roots),
        "terminal_leaf_nodes": tuple(_node(row) for row in nodes),
        "terminal_leaf_edges": tuple(_edge(row) for row in edges),
        "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_ordered_recipient_local_accuracy_critical_roll_damage_and_hp_identity_as_graph_paths",
        "provenance": "runtime_d0_rock_slide_execution_scope_to_detached_multi_recipient_path_graph_v1",
    }


def _consumer_adapter(value: Any, action: Mapping[str, Any], scope: Mapping[str, Any]) -> dict[str, Any] | str | None:
    if value is None: return None
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != CONSUMER_SCHEMA_VERSION or value.get("hypothetical") is not True or value.get("current_authority") is not False: return "rock_slide_frozen_scope_consumer_adapter_invalid"
    if value.get("frozen_execution_scope_authority") != scope or action.get("action_id") != value.get("action_id") or action.get("identity") != "rock-slide": return "rock_slide_frozen_scope_consumer_binding_mismatch"
    d0, snapshot = value.get("predictive_strategy_d0"), value.get("predictive_runtime_snapshot")
    if not isinstance(d0, Mapping) or not isinstance(snapshot, Mapping) or d0.get("status") != "resolved" or d0.get("decision_owner") != value.get("rock_slide_actor"): return "rock_slide_frozen_scope_consumer_private_state_invalid"
    metadata = scope.get("move_metadata_authority", {}).get("metadata") if isinstance(scope.get("move_metadata_authority"), Mapping) else None
    recipients = value.get("ordered_recipient_states")
    if not isinstance(metadata, Mapping) or not isinstance(recipients, tuple) or tuple(row.get("recipient") for row in recipients) != scope.get("recipients"): return "rock_slide_frozen_scope_consumer_recipient_order_mismatch"
    return {"strategy_d0": d0, "runtime_snapshot": snapshot, "scope": scope, "base": {"session_id": scope["session_id"], "source_runtime_fingerprint": scope["source_runtime_fingerprint"], "source_branch_fingerprint": scope["source_branch_fingerprint"], "decision_owner": deepcopy(scope["decision_owner"]), "attacker": deepcopy(scope["acting_owner"]), "action_id": scope["action_id"], "move_id": "rock-slide", "recipients": deepcopy(scope["recipients"]), "move_metadata": deepcopy(dict(metadata)), "spread_damage_modifier_authority": deepcopy(scope["spread_damage_modifier_authority"]), "execution_scope_authority": deepcopy(dict(scope)), "attacker_hp": value["rock_slide_actor_state"]["hp"], "attacker_max_hp": value["rock_slide_actor_state"]["max_hp"]}}


def _graph(d0: Mapping[str, Any], snapshot: Mapping[str, Any], base: Mapping[str, Any]):
    roots: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    masses: dict[str, Fraction] = {}
    index: dict[tuple[int, tuple[str, ...]], str] = {}
    terminal_mass = Fraction()

    def add(cursor: int, outcomes: tuple[dict[str, Any], ...]) -> str:
        key = (cursor, tuple(row["outcome_id"] for row in outcomes))
        existing = index.get(key)
        if existing is not None:
            return existing
        node_id = f"recipient:{cursor}/prior:{'|'.join(key[1]) if key[1] else 'none'}"
        index[key] = node_id
        nodes.append({"node_id": node_id, "recipient_cursor": cursor, "prior_recipient_outcomes": deepcopy(outcomes)})
        masses[node_id] = Fraction()
        return node_id

    first = add(0, ())
    roots.append({"root_id": "recipient:0", "probability": Fraction(1, 1), "terminal": False, "node_id": first})
    masses[first] = Fraction(1, 1)
    cache: dict[tuple[str, int], list[dict[str, Any]] | dict[str, str]] = {}
    cursor = 0
    while cursor < len(nodes):
        node = nodes[cursor]; cursor += 1
        source_mass = masses[node["node_id"]]
        if not source_mass:
            continue
        recipient_index = node["recipient_cursor"]
        recipient = base["recipients"][recipient_index]
        owner = recipient["owner"]
        events = cache.get((owner["pokemon_id"], owner["slot_index"]))
        if events is None:
            events = _recipient_events(d0, snapshot, base, owner)
            cache[(owner["pokemon_id"], owner["slot_index"])] = events
        if isinstance(events, Mapping):
            return {"status": events["status"], "reason": events["reason"]}, None, None, None
        conditional_mass = sum((row["probability"] for row in events), Fraction())
        if conditional_mass != Fraction(1, 1):
            return {"status": "rejected", "reason": "rock_slide_recipient_conditional_probability_mass_invalid"}, None, None, None
        for event in events:
            outcome = {"recipient_index": recipient_index + 1, "recipient": deepcopy(recipient), **deepcopy(event)}
            outcome["outcome_id"] = _outcome_id(outcome)
            terminal = recipient_index + 1 == len(base["recipients"])
            edge = {
                "edge_id": f"{node['node_id']}/recipient:{recipient_index + 1}:{outcome['outcome_id']}",
                "from_node_id": node["node_id"], "conditional_probability": event["probability"],
                "recipient_outcome": outcome, "terminal": terminal,
            }
            if terminal:
                edge["terminal_reason"] = "all_frozen_recipients_resolved"
                edge["terminal_consequences"] = {"ordered_recipient_outcomes": deepcopy((*node["prior_recipient_outcomes"], outcome))}
                terminal_mass += source_mass * event["probability"]
            else:
                next_node = add(recipient_index + 1, (*node["prior_recipient_outcomes"], outcome))
                edge["to_node_id"] = next_node
                masses[next_node] += source_mass * event["probability"]
            edges.append(edge)
    return roots, nodes, edges, terminal_mass


def _recipient_events(d0: Mapping[str, Any], snapshot: Mapping[str, Any], base: Mapping[str, Any], recipient: Mapping[str, Any]) -> list[dict[str, Any]] | dict[str, str]:
    local_d0, local_snapshot = _recipient_d0_view(d0, snapshot, base["attacker"], recipient)
    if local_d0 is None or local_snapshot is None:
        return {"status": "incomplete", "reason": "rock_slide_recipient_private_d0_view_unavailable"}
    raw_recipient = local_snapshot["state"][f"{recipient['side']}_side"]["pokemon"].get(recipient["slot_index"])
    if isinstance(raw_recipient, Mapping) and raw_recipient.get("current_ability") == "sturdy":
        return {"status": "incomplete", "reason": "rock_slide_recipient_sturdy_survival_authority_required"}
    metadata = base["move_metadata"]
    hit = build_runtime_d0_strict_hit_probability_assessment(strategy_d0=local_d0, runtime_snapshot=local_snapshot, attacker=base["attacker"], target=recipient, selected_move=metadata)
    if hit.get("status") != "resolved": return {"status": hit.get("status", "rejected"), "reason": hit.get("reason", "rock_slide_recipient_hit_authority_unavailable")}
    native = build_runtime_d0_native_damage_context(strategy_d0=local_d0, runtime_snapshot=local_snapshot, attacker=base["attacker"], target=recipient, move_metadata=metadata)
    if native.get("status") != "resolved": return {"status": native.get("status", "incomplete"), "reason": native.get("reason", "rock_slide_recipient_normal_damage_authority_unavailable")}
    try:
        hit_probability = Fraction(hit["probability_percent"], 100)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return {"status": "rejected", "reason": "rock_slide_recipient_probability_invalid"}
    if not 0 <= hit_probability <= 1:
        return {"status": "rejected", "reason": "rock_slide_recipient_probability_out_of_range"}
    result: list[dict[str, Any]] = []
    if hit_probability < 1:
        result.append({"probability": 1 - hit_probability, "outcome": "miss", "hit_state": "miss", "critical_state": "not_applicable", "damage_roll": {"status": "not_applicable", "reason": "miss_has_no_critical_or_damage_roll"}, "raw_damage": 0, "actual_damage": 0, "pre_hp": _hp(local_d0, recipient), "post_hp": _hp(local_d0, recipient), "fainted": False})
    if not hit_probability:
        return result
    applicability_interval = build_predictive_normal_formula_interval(branch_state=local_d0["strategy_state"], decision_owner=base["attacker"], target_owner=recipient, snapshot_damage_input=native["snapshot_damage_input"], stat_provenance=native["stat_provenance"], trusted_level=native["trusted_level"], is_critical=False, is_spread=True, source_runtime_fingerprint=local_d0["source_runtime_fingerprint"])
    if applicability_interval.get("completeness") != "exact_complete": return {"status": "incomplete", "reason": applicability_interval.get("reason", "rock_slide_recipient_applicability_unavailable")}
    type_effectiveness = applicability_interval.get("native_evaluator_result", {}).get("type_effectiveness") if isinstance(applicability_interval.get("native_evaluator_result"), Mapping) else None
    if type_effectiveness == 0.0:
        hp = _hp(local_d0, recipient)
        result.append({"probability": hit_probability, "outcome": "immune", "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": {"status": "not_applicable", "reason": "type_immune_recipient_has_no_critical_or_damage_roll"}, "raw_damage": 0, "actual_damage": 0, "pre_hp": hp, "post_hp": hp, "fainted": False})
        return result
    critical = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=local_d0, runtime_snapshot=local_snapshot, attacker=base["attacker"], target=recipient, move_metadata=metadata)
    if critical.get("status") != "resolved": return {"status": critical.get("status", "rejected"), "reason": critical.get("reason", "rock_slide_recipient_critical_authority_unavailable")}
    try:
        critical_probability = Fraction(critical["critical_probability"]["numerator"], critical["critical_probability"]["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return {"status": "rejected", "reason": "rock_slide_recipient_probability_invalid"}
    if not 0 <= critical_probability <= 1:
        return {"status": "rejected", "reason": "rock_slide_recipient_probability_out_of_range"}
    for state, factor in (("non_critical", 1 - critical_probability), ("critical", critical_probability)):
        if not factor: continue
        raw_interval = build_predictive_normal_formula_interval(branch_state=local_d0["strategy_state"], decision_owner=base["attacker"], target_owner=recipient, snapshot_damage_input=native["snapshot_damage_input"], stat_provenance=native["stat_provenance"], trusted_level=native["trusted_level"], is_critical=state == "critical", is_spread=False, source_runtime_fingerprint=local_d0["source_runtime_fingerprint"])
        interval = build_predictive_normal_formula_interval(branch_state=local_d0["strategy_state"], decision_owner=base["attacker"], target_owner=recipient, snapshot_damage_input=native["snapshot_damage_input"], stat_provenance=native["stat_provenance"], trusted_level=native["trusted_level"], is_critical=state == "critical", is_spread=True, source_runtime_fingerprint=local_d0["source_runtime_fingerprint"])
        if raw_interval.get("completeness") != "exact_complete" or interval.get("completeness") != "exact_complete" or interval.get("spread_damage_scope") != "spread": return {"status": "incomplete", "reason": interval.get("reason", raw_interval.get("reason", "rock_slide_spread_damage_interval_unavailable"))}
        post = compose_predictive_normal_formula_post_hit(interval=interval, move_metadata=metadata, attacker_hp={"current_hp": base["attacker_hp"], "max_hp": base["attacker_max_hp"]}, attacker_item=None, attacker_ability=native["snapshot_damage_input"]["battle_context"]["current_state"]["direct_mechanics_context"]["attacker"].get("ability"), target_ability=native["snapshot_damage_input"]["battle_context"]["current_state"]["direct_mechanics_context"]["defender"].get("ability"), attacker_item_known=True)
        rolls = project_predictive_damage_roll_uncertainty(interval=interval, post_hit=post)
        if post.get("status") != "resolved" or rolls.get("status") != "resolved": return {"status": "incomplete", "reason": "rock_slide_recipient_post_hit_or_roll_authority_unavailable"}
        for roll in rolls["outcomes"]:
            consequence = roll.get("post_hit_consequence")
            if not isinstance(consequence, Mapping) or not isinstance(consequence.get("actual_damage"), int): return {"status": "rejected", "reason": "rock_slide_recipient_roll_post_hit_binding_invalid"}
            before = interval.get("target_hp_before")
            if not isinstance(before, int) or consequence["actual_damage"] < 0 or consequence["actual_damage"] > before: return {"status": "rejected", "reason": "rock_slide_recipient_hp_transition_invalid"}
            raw_rolls = raw_interval.get("exact_damage_rolls")
            raw_pre_spread = raw_rolls[roll["roll_index"]] if isinstance(raw_rolls, tuple) and len(raw_rolls) == 16 else None
            if not isinstance(raw_pre_spread, int): return {"status": "rejected", "reason": "rock_slide_pre_spread_roll_binding_invalid"}
            result.append({"probability": hit_probability * factor * Fraction(1, 16), "outcome": "hit", "hit_state": "hit", "critical_state": state, "damage_roll": {"roll_index": roll["roll_index"], "random_factor_percent": roll["random_factor_percent"]}, "raw_pre_spread_damage": raw_pre_spread, "raw_damage": consequence["raw_damage"], "actual_damage": consequence["actual_damage"], "pre_hp": before, "post_hp": before - consequence["actual_damage"], "fainted": before == consequence["actual_damage"], "spread_modifier": deepcopy(base["spread_damage_modifier_authority"])})
    return result


def _recipient_d0_view(d0: Mapping[str, Any], snapshot: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any]):
    if target.get("side") == d0.get("active_owners", {}).get(target.get("side"), {}).get("side") and target == d0.get("active_owners", {}).get(target.get("side")):
        return d0, snapshot
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    if not isinstance(state, Mapping): return None, None
    synthetic = deepcopy(dict(state)); side = synthetic.get(f"{target['side']}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(target.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(side, Mapping) or not isinstance(row, Mapping) or row.get("pokemon_id") != target.get("pokemon_id"): return None, None
    side["active_slot_index"] = target["slot_index"]
    local_snapshot = {"status": "runtime_snapshot_ready", "session_id": d0["session_id"], "state": synthetic, "state_fingerprint": state_fingerprint(synthetic)}
    local_d0 = freeze_runtime_strategy_d0(runtime_snapshot=local_snapshot, decision_owner=attacker)
    return (local_d0, local_snapshot) if local_d0.get("status") == "resolved" else (None, None)


def _base(d0: Any, action: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(action, Mapping) or not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != EXECUTION_SCOPE_SCHEMA:
        return None
    actor = d0.get("decision_owner")
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "acting_owner", "action_id", "move_id")
    if not isinstance(actor, Mapping) or any(authority.get(key) != ({"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": actor, "acting_owner": actor, "action_id": action.get("action_id"), "move_id": action.get("identity")}[key]) for key in keys): return None
    recipients = authority.get("recipients"); modifier = authority.get("spread_damage_modifier_authority"); metadata = authority.get("move_metadata_authority", {}).get("metadata") if isinstance(authority.get("move_metadata_authority"), Mapping) else None
    if action.get("identity") != _MOVE_ID or not isinstance(recipients, tuple) or len(recipients) != 2 or not isinstance(metadata, Mapping) or metadata.get("move_id") != _MOVE_ID or metadata.get("target") != "all-opponents" or authority.get("recipient_resolution_order") != "frozen_target_set_order" or any(authority.get(key) != "recipient_local" for key in ("accuracy_uncertainty_scope", "critical_hit_uncertainty_scope", "damage_roll_uncertainty_scope")) or not isinstance(modifier, Mapping) or (modifier.get("numerator"), modifier.get("denominator"), modifier.get("applies_when_recipient_count_at_least")) != (3, 4, 2): return None
    active = d0.get("strategy_state", {}).get("active", {}).get(actor.get("side"))
    if not isinstance(active, Mapping) or not isinstance(active.get("current_hp"), int) or not isinstance(active.get("max_hp"), int): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(actor)), "attacker": deepcopy(dict(actor)), "action_id": action["action_id"], "move_id": _MOVE_ID, "recipients": deepcopy(recipients), "move_metadata": deepcopy(dict(metadata)), "spread_damage_modifier_authority": deepcopy(dict(modifier)), "execution_scope_authority": deepcopy(dict(authority)), "attacker_hp": active["current_hp"], "attacker_max_hp": active["max_hp"]}


def _hp(d0: Mapping[str, Any], recipient: Mapping[str, Any]) -> int:
    value = d0.get("strategy_state", {}).get("active", {}).get(recipient.get("side"), {}).get("current_hp")
    return value if isinstance(value, int) else 0
def _outcome_id(row: Mapping[str, Any]) -> str:
    if row["outcome"] == "miss":
        return "miss"
    if row["outcome"] == "immune":
        return "immune"
    return f"hit:{row['critical_state']}:roll:{row['damage_roll']['roll_index']}"
def _root(row: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(row)); result["probability"] = _fd(result["probability"]); return result
def _edge(row: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(row)); result["conditional_probability"] = _fd(result["conditional_probability"]); outcome = result.get("recipient_outcome")
    if isinstance(outcome, Mapping): result["recipient_outcome"] = _outcome(outcome)
    consequences = result.get("terminal_consequences")
    if isinstance(consequences, Mapping) and isinstance(consequences.get("ordered_recipient_outcomes"), tuple):
        result["terminal_consequences"] = {**consequences, "ordered_recipient_outcomes": tuple(_outcome(value) for value in consequences["ordered_recipient_outcomes"])}
    return result
def _node(row: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(row)); prior = result.get("prior_recipient_outcomes")
    if isinstance(prior, tuple): result["prior_recipient_outcomes"] = tuple(_outcome(value) for value in prior)
    return result
def _outcome(row: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(row))
    if isinstance(result.get("probability"), Fraction): result["probability"] = _fd(result["probability"])
    return result
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
