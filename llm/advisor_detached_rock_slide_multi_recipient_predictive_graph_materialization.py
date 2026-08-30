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
from llm.advisor_runtime_d0_wide_guard_spread_applicability_authority import SCHEMA_VERSION as WIDE_GUARD_SCHEMA
from llm.advisor_runtime_d0_mat_block_direct_damage_applicability_authority import SCHEMA_VERSION as MAT_BLOCK_SCHEMA
from llm.advisor_detached_rock_slide_intermediate_state_vector import CONSUMER_SCHEMA_VERSION
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_strategy_d0,
    runtime_strategy_d0_freshness,
    freeze_runtime_current_condition_authority,
    _runtime_probabilistic_target_status_source_authority,
    _runtime_target_substitute_authority,
)
from llm.advisor_substitute import substitute_state
from advisor.probabilistic_target_flinch_effect_capabilities import resolve_probabilistic_target_flinch_effect_capability


SCHEMA_VERSION = "detached-rock-slide-multi-recipient-predictive-graph-materialization-v1"
HORIZON = "immediate_action_consequence"
_MOVE_ID = "rock-slide"


def materialize_detached_rock_slide_multi_recipient_predictive_graph(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], execution_scope_authority: Mapping[str, Any], frozen_scope_consumer_adapter: Mapping[str, Any] | None = None, wide_guard_spread_applicability_authority: Mapping[str, Any] | None = None, mat_block_direct_damage_applicability_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Expand frozen recipients in order, retaining a graph rather than leaves."""
    adapter = _consumer_adapter(frozen_scope_consumer_adapter, action, execution_scope_authority)
    if isinstance(adapter, str): return _result("rejected", adapter, {})
    if isinstance(adapter, Mapping): strategy_d0, runtime_snapshot, execution_scope_authority, base = adapter["strategy_d0"], adapter["runtime_snapshot"], adapter["scope"], adapter["base"]
    else: base = _base(strategy_d0, action, execution_scope_authority)
    if base is None:
        return _result("rejected", "invalid_rock_slide_multi_recipient_graph_request", {})
    if frozen_scope_consumer_adapter is None and runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    wide_guard = _wide_guard(wide_guard_spread_applicability_authority, base)
    if isinstance(wide_guard, Mapping) and "status" in wide_guard:
        return _result(wide_guard["status"], wide_guard["reason"], base)
    mat_block = _mat_block(mat_block_direct_damage_applicability_authority, base)
    if isinstance(mat_block, Mapping) and "status" in mat_block: return _result(mat_block["status"], mat_block["reason"], base)
    if _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return _result("unsupported", "rock_slide_multi_recipient_item_consumption_unsupported", base)
    roots, nodes, edges, mass = _graph(strategy_d0, runtime_snapshot, base, wide_guard, mat_block)
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
        **({"wide_guard_spread_applicability_authority": deepcopy(dict(wide_guard["authority"]))} if wide_guard is not None else {}),
        **({"mat_block_direct_damage_applicability_authority": deepcopy(dict(mat_block["authority"]))} if mat_block is not None else {}),
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


def _graph(d0: Mapping[str, Any], snapshot: Mapping[str, Any], base: Mapping[str, Any], wide_guard: Mapping[str, Any] | None, mat_block: Mapping[str, Any] | None):
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
            events = _recipient_events(d0, snapshot, base, owner, wide_guard, mat_block)
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


def _recipient_events(d0: Mapping[str, Any], snapshot: Mapping[str, Any], base: Mapping[str, Any], recipient: Mapping[str, Any], wide_guard: Mapping[str, Any] | None, mat_block: Mapping[str, Any] | None) -> list[dict[str, Any]] | dict[str, str]:
    protected = wide_guard.get("protected_recipients", {}).get(_owner_key(recipient)) if isinstance(wide_guard, Mapping) else None
    if isinstance(protected, Mapping) and protected.get("owner") == recipient:
        hp = _hp(d0, recipient)
        return [{"probability": Fraction(1, 1), "outcome": "prevented_by_wide_guard", "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": {"status": "not_applicable", "reason": "wide_guard_prevented_recipient_has_no_critical_or_damage_roll"}, "raw_damage": 0, "actual_damage": 0, "pre_hp": hp, "post_hp": hp, "fainted": False, "wide_guard_applicability_authority": deepcopy(dict(wide_guard["authority"])), "wide_guard_protected_recipient": deepcopy(dict(protected))}]
    protected = mat_block.get("protected_recipients", {}).get(_owner_key(recipient)) if isinstance(mat_block, Mapping) else None
    if isinstance(protected, Mapping) and protected == recipient:
        hp = _hp(d0, recipient)
        return [{"probability": Fraction(1, 1), "outcome": "prevented_by_mat_block", "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": {"status": "not_applicable", "reason": "mat_block_prevented_recipient_has_no_critical_or_damage_roll"}, "raw_damage": 0, "actual_damage": 0, "pre_hp": hp, "post_hp": hp, "fainted": False, "mat_block_applicability_authority": deepcopy(dict(mat_block["authority"])), "mat_block_protected_recipient": deepcopy(dict(protected))}]
    local_d0, local_snapshot = _recipient_d0_view(d0, snapshot, base["attacker"], recipient)
    if local_d0 is None or local_snapshot is None:
        return {"status": "incomplete", "reason": "rock_slide_recipient_private_d0_view_unavailable"}
    raw_recipient = local_snapshot["state"][f"{recipient['side']}_side"]["pokemon"].get(recipient["slot_index"])
    if isinstance(raw_recipient, Mapping) and raw_recipient.get("current_ability") == "sturdy":
        return {"status": "incomplete", "reason": "rock_slide_recipient_sturdy_survival_authority_required"}
    metadata = base["move_metadata"]
    flinch = _recipient_flinch_authority(local_d0, local_snapshot, base["attacker"], recipient, metadata)
    if isinstance(flinch, Mapping) and flinch.get("status") != "resolved": return {"status": flinch.get("status", "rejected"), "reason": flinch.get("reason", "rock_slide_recipient_flinch_authority_unavailable")}
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
            event = {"probability": hit_probability * factor * Fraction(1, 16), "outcome": "hit", "hit_state": "hit", "critical_state": state, "damage_roll": {"roll_index": roll["roll_index"], "random_factor_percent": roll["random_factor_percent"]}, "raw_pre_spread_damage": raw_pre_spread, "raw_damage": consequence["raw_damage"], "actual_damage": consequence["actual_damage"], "pre_hp": before, "post_hp": before - consequence["actual_damage"], "fainted": before == consequence["actual_damage"], "spread_modifier": deepcopy(base["spread_damage_modifier_authority"])}
            result.extend(_recipient_flinch_branches(event, flinch))
    return result


def _recipient_flinch_authority(d0: Mapping[str, Any], snapshot: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], metadata: Mapping[str, Any]) -> dict[str, Any]:
    # Older detached Rock Slide fixtures intentionally model damage-only move
    # metadata.  They remain valid damage graphs; flinch is materialized only
    # when the maintained secondary fields are present.
    if metadata.get("effect_chance") is None and metadata.get("ailment") is None:
        return {"status": "resolved", "applicable": False, "provenance": "rock_slide_damage_only_metadata_no_secondary_materialization"}
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    if not isinstance(state, Mapping): return {"status": "rejected", "reason": "rock_slide_recipient_runtime_snapshot_invalid"}
    raw_attacker = state.get(f"{attacker['side']}_side", {}).get("pokemon", {}).get(attacker.get("slot_index"))
    raw_target = state.get(f"{target['side']}_side", {}).get("pokemon", {}).get(target.get("slot_index"))
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping): return {"status": "rejected", "reason": "rock_slide_recipient_flinch_owner_mismatch"}
    condition = freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=target)
    source = _runtime_probabilistic_target_status_source_authority(state=state, raw_attacker=raw_attacker, raw_target=raw_target, attacker=attacker, target=target, target_condition=condition)
    capability = resolve_probabilistic_target_flinch_effect_capability(move=metadata, source_authority=source)
    substitute = _runtime_target_substitute_authority(substitute_state(state, target))
    if capability.get("status") != "resolved": return capability
    if condition.get("status") == "rejected": return {"status": "rejected", "reason": condition.get("reason", "rock_slide_recipient_condition_authority_invalid")}
    if substitute.get("status") != "known": return {"status": "incomplete", "reason": "rock_slide_recipient_substitute_unknown"}
    return {"status": "resolved", "applicable": True, "capability": capability, "target_substitute_authority": substitute, "provenance": "rock_slide_recipient_local_catalogued_flinch_authority_v1"}


def _recipient_flinch_branches(event: Mapping[str, Any], authority: Mapping[str, Any]) -> list[dict[str, Any]]:
    if authority.get("applicable") is False:
        return [deepcopy(dict(event))]
    if event.get("outcome") != "hit" or event.get("fainted") is True or authority["target_substitute_authority"].get("state") == "known_active":
        return [{**deepcopy(dict(event)), "flinch": {"state": "not_flinched", "reason": "hit_required_target_survival_and_substitute_applicability"}}]
    probability = authority["capability"]["probability"]
    chance = Fraction(probability["numerator"], probability["denominator"])
    no = {**deepcopy(dict(event)), "probability": event["probability"] * (1 - chance), "flinch": {"state": "not_flinched", "conditional_probability": deepcopy(probability), "provenance": authority["provenance"]}}
    yes = {**deepcopy(dict(event)), "probability": event["probability"] * chance, "flinch": {"state": "flinched", "conditional_probability": deepcopy(probability), "hypothetical_target_flinch": {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "provenance": "rock_slide_recipient_successful_damage_roll_secondary_v1"}, "provenance": authority["provenance"]}}
    return [row for row in (no, yes) if row["probability"]]


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


def _wide_guard(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return {"status": "rejected", "reason": "wide_guard_applicability_authority_invalid"}
    status = value.get("status")
    if status in {"incomplete", "rejected"}:
        return {"status": status, "reason": value.get("reason", "wide_guard_applicability_authority_unavailable")}
    if status != "resolved" or value.get("schema_version") != WIDE_GUARD_SCHEMA:
        return {"status": "rejected", "reason": "wide_guard_applicability_authority_schema_invalid"}
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
    scope_value = value.get("execution_scope_authority")
    if any(value.get(key) != base.get(key) for key in keys) or value.get("incoming_actor") != base["attacker"] or value.get("incoming_action_id") != base["action_id"] or value.get("incoming_move_id") != _MOVE_ID or (scope_value is not None and scope_value != base["execution_scope_authority"]):
        return {"status": "rejected", "reason": "wide_guard_applicability_authority_binding_mismatch"}
    target_set = base["execution_scope_authority"].get("target_set_authority")
    if value.get("target_set_authority") != target_set:
        return {"status": "rejected", "reason": "wide_guard_target_set_authority_binding_mismatch"}
    if value.get("outcome") == "not_applicable":
        if value.get("protected_recipients") != ():
            return {"status": "rejected", "reason": "wide_guard_not_applicable_recipient_binding_invalid"}
        return {"authority": value, "protected_recipients": {}}
    if value.get("outcome") != "applies" or value.get("execution_scope_authority") != base["execution_scope_authority"] or value.get("incoming_recipient_classification") != "spread_multi_target":
        return {"status": "rejected", "reason": "wide_guard_applicability_result_invalid"}
    rows = value.get("protected_recipients")
    if not isinstance(rows, tuple) or not rows:
        return {"status": "rejected", "reason": "wide_guard_protected_recipient_binding_invalid"}
    expected = {_owner_key(row): row for row in base["recipients"]}
    protected = {}
    for row in rows:
        key = _owner_key(row)
        if key not in expected or row != expected[key] or key in protected:
            return {"status": "rejected", "reason": "wide_guard_protected_recipient_binding_invalid"}
        protected[key] = deepcopy(dict(row))
    return {"authority": value, "protected_recipients": protected}


def _mat_block(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None:
    if value is None: return None
    if not isinstance(value, Mapping): return {"status": "rejected", "reason": "mat_block_applicability_authority_invalid"}
    if value.get("status") in {"incomplete", "rejected"}: return {"status": value["status"], "reason": value.get("reason", "mat_block_applicability_authority_unavailable")}
    if value.get("status") != "resolved" or value.get("schema_version") != MAT_BLOCK_SCHEMA: return {"status": "rejected", "reason": "mat_block_applicability_authority_schema_invalid"}
    incoming = value.get("incoming_action")
    if value.get("session_id") != base.get("session_id") or not isinstance(incoming, Mapping) or incoming.get("action_id") != base.get("action_id") or incoming.get("move_id") != "rock-slide": return {"status": "rejected", "reason": "mat_block_applicability_authority_binding_mismatch"}
    if value.get("outcome") == "not_applicable": return {"authority": value, "protected_recipients": {}}
    if value.get("outcome") != "applies": return {"status": "rejected", "reason": "mat_block_applicability_result_invalid"}
    expected = {_owner_key(row["owner"]): row["owner"] for row in base["recipients"]}
    rows = value.get("protected_recipients")
    if not isinstance(rows, tuple) or not rows: return {"status": "rejected", "reason": "mat_block_protected_recipient_binding_invalid"}
    protected = {}
    for row in rows:
        key = _owner_key(row)
        if key not in expected or row != expected[key] or key in protected: return {"status": "rejected", "reason": "mat_block_protected_recipient_binding_invalid"}
        protected[key] = deepcopy(dict(row))
    return {"authority": value, "protected_recipients": protected}


def _owner_key(recipient: Mapping[str, Any]) -> tuple[Any, ...]:
    owner = recipient.get("owner") if isinstance(recipient, Mapping) and isinstance(recipient.get("owner"), Mapping) else recipient
    return (owner.get("session_id"), owner.get("side"), owner.get("slot_index"), owner.get("pokemon_id")) if isinstance(owner, Mapping) else (None,)


def _hp(d0: Mapping[str, Any], recipient: Mapping[str, Any]) -> int:
    value = d0.get("strategy_state", {}).get("active", {}).get(recipient.get("side"), {}).get("current_hp")
    return value if isinstance(value, int) else 0
def _outcome_id(row: Mapping[str, Any]) -> str:
    if row["outcome"] == "prevented_by_wide_guard":
        return "prevented_by_wide_guard"
    if row["outcome"] == "prevented_by_mat_block": return "prevented_by_mat_block"
    if row["outcome"] == "miss":
        return "miss"
    if row["outcome"] == "immune":
        return "immune"
    flinch = row.get("flinch") if isinstance(row.get("flinch"), Mapping) else {}
    flinch_state = flinch.get("state", "not_flinched")
    return f"hit:{row['critical_state']}:roll:{row['damage_roll']['roll_index']}:flinch:{flinch_state}"
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
