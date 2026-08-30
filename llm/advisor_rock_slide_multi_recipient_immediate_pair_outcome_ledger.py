"""Strict, non-flattening ledger for nested Rock Slide immediate pairs."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Iterable, Mapping

from llm.advisor_detached_rock_slide_multi_recipient_immediate_move_pair import SCHEMA_VERSION as PAIR_SCHEMA
from llm.advisor_rock_slide_multi_recipient_action_outcome_ledger import (
    graph_terminal_rows,
    normalize_rock_slide_multi_recipient_action_outcome_ledger,
)


SCHEMA_VERSION = "exact-rock-slide-multi-recipient-immediate-pair-outcome-ledger-v1"
HORIZON = "immediate_action_pair"


def normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(*, pair: Mapping[str, Any]) -> dict[str, Any]:
    """Validate nested pair references and exact probability factors only."""
    base = _base(pair)
    if base is None or pair.get("status") != "evaluable" or pair.get("schema_version") != PAIR_SCHEMA or pair.get("horizon") != HORIZON:
        return _result("rejected", "invalid_rock_slide_nested_pair_identity", base)
    if _fraction(pair.get("terminal_probability_mass")) != Fraction(1, 1):
        return _result("rejected", "rock_slide_nested_pair_declared_root_mass_invalid", base)
    branches = pair.get("order_graphs")
    if not isinstance(branches, tuple) or not branches:
        return _result("rejected", "rock_slide_nested_pair_order_branches_missing", base)
    parsed: list[dict[str, Any]] = []
    names: set[str] = set()
    mass = Fraction()
    for branch in branches:
        row = _order_branch(branch, base)
        if isinstance(row, str):
            return _result("rejected", row, base)
        if row["order"] in names:
            return _result("rejected", "rock_slide_nested_pair_duplicate_order_branch", base)
        names.add(row["order"]); parsed.append(row); mass += row["weighted_mass"]
    if mass != Fraction(1, 1):
        return _result("rejected", "rock_slide_nested_pair_root_mass_not_one", base, terminal_probability_mass=_fd(mass))
    if names == {"own_first", "opponent_first"} and any(row["order_probability"] != Fraction(1, 2) for row in parsed):
        return _result("rejected", "rock_slide_nested_pair_equal_speed_order_mass_invalid", base)
    if len(names) != len(parsed):
        return _result("rejected", "rock_slide_nested_pair_order_branch_identity_invalid", base)
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
        # Keep the source nested graph by reference.  This authority only
        # validates/traverses it and must not eagerly duplicate its DAG.
        "nested_pair": pair,
        "order_branches": tuple(_public_branch(row) for row in parsed),
        "terminal_transition_representation": "nested_rock_slide_graph_sources_with_attached_second_action_outcomes",
        "terminal_probability_mass": _fd(mass),
        "aggregation": "dynamic_reference_traversal_no_eager_pair_cartesian_flattening",
        "provenance": "strict_nested_rock_slide_immediate_pair_to_outcome_ledger_v1",
    }


def iter_rock_slide_multi_recipient_immediate_pair_terminal_rows(*, ledger: Mapping[str, Any]) -> Iterable[dict[str, Any]] | str:
    """Dynamically yield final pair rows after validating the frozen ledger."""
    if not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable" or ledger.get("schema_version") != SCHEMA_VERSION:
        return "rock_slide_nested_pair_ledger_unavailable"
    pair = ledger.get("nested_pair")
    rebuilt = normalize_rock_slide_multi_recipient_immediate_pair_outcome_ledger(pair=pair) if isinstance(pair, Mapping) else None
    if not isinstance(rebuilt, Mapping) or rebuilt.get("status") != "evaluable" or _base(rebuilt) != _base(ledger):
        return "rock_slide_nested_pair_ledger_source_binding_invalid"
    return _rows(pair=pair)


def _order_branch(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("schema_version") != PAIR_SCHEMA or value.get("action_order") not in {"own_first", "opponent_first"}:
        return "rock_slide_nested_pair_order_branch_invalid"
    order = value["action_order"]; probability = _fraction(value.get("order_conditional_probability"))
    if probability <= 0 or probability > 1 or _fraction(value.get("conditional_terminal_probability_mass")) != Fraction(1, 1) or _fraction(value.get("order_weighted_terminal_probability_mass")) != probability:
        return "rock_slide_nested_pair_order_probability_invalid"
    transitions = value.get("terminal_transitions")
    if not isinstance(transitions, tuple) or not transitions:
        return "rock_slide_nested_pair_terminal_transitions_missing"
    if order == "own_first":
        graph = value.get("first_action")
        source_rows = _graph_rows(graph)
        if isinstance(source_rows, str): return source_rows
        parsed = _own_first_transitions(transitions, source_rows, base, probability)
    else:
        first = value.get("first_action", {}).get("first_action_ledger") if isinstance(value.get("first_action"), Mapping) else None
        parsed = _opponent_first_transitions(transitions, first, base, probability)
    if isinstance(parsed, str): return parsed
    if sum((row["source_probability"] for row in parsed), Fraction()) != Fraction(1, 1):
        return "rock_slide_nested_pair_order_source_mass_invalid"
    return {"order": order, "order_probability": probability, "weighted_mass": probability, "transitions": tuple(parsed)}


def _own_first_transitions(transitions: tuple[Any, ...], sources: tuple[Mapping[str, Any], ...], base: Mapping[str, Any], order: Fraction) -> tuple[dict[str, Any], ...] | str:
    source_map = {row["terminal_edge_id"]: row for row in sources}
    if len(source_map) != len(sources) or len(transitions) != len(sources): return "rock_slide_nested_pair_source_terminal_count_mismatch"
    seen: set[str] = set(); parsed = []
    for value in transitions:
        if not isinstance(value, Mapping) or not isinstance(value.get("first_terminal_source_id"), str): return "rock_slide_nested_pair_source_terminal_missing"
        source_id = value["first_terminal_source_id"]
        if source_id in seen or source_id not in source_map or value.get("rock_slide_terminal_source") != source_map[source_id]: return "rock_slide_nested_pair_source_terminal_duplicate_or_mismatch"
        seen.add(source_id)
        row = _transition(value, base, order, source_map[source_id]["probability"], "own_first")
        if isinstance(row, str): return row
        if row["vector"].get("source_terminal_path") != source_map[source_id]: return "rock_slide_nested_pair_vector_source_path_mismatch"
        parsed.append(row)
    return tuple(parsed) if seen == set(source_map) else "rock_slide_nested_pair_source_terminal_omission"


def _opponent_first_transitions(transitions: tuple[Any, ...], first: Any, base: Mapping[str, Any], order: Fraction) -> tuple[dict[str, Any], ...] | str:
    leaves = _attack_rows(first)
    if isinstance(leaves, str): return leaves
    source_map = {row["leaf_id"]: row for row in leaves}
    if len(source_map) != len(leaves) or len(transitions) != len(leaves): return "rock_slide_nested_pair_first_terminal_count_mismatch"
    seen: set[str] = set(); parsed = []
    for value in transitions:
        leaf = value.get("first_terminal_leaf") if isinstance(value, Mapping) else None
        leaf_id = leaf.get("leaf_id") if isinstance(leaf, Mapping) else None
        if not isinstance(leaf_id, str) or leaf_id in seen or leaf_id not in source_map or leaf != source_map[leaf_id]: return "rock_slide_nested_pair_first_terminal_duplicate_or_mismatch"
        seen.add(leaf_id)
        row = _transition(value, base, order, _fraction(leaf.get("probability")), "opponent_first")
        if isinstance(row, str): return row
        overlay = row["vector"].get("source_scalar_intermediate_overlay")
        if not isinstance(overlay, Mapping) or overlay.get("first_action", {}).get("leaf_id") != leaf_id: return "rock_slide_nested_pair_vector_overlay_source_mismatch"
        parsed.append(row)
    return tuple(parsed) if seen == set(source_map) else "rock_slide_nested_pair_first_terminal_omission"


def _transition(value: Any, base: Mapping[str, Any], order: Fraction, source_probability: Fraction, direction: str) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or _fraction(value.get("incoming_path_probability")) != source_probability or value.get("pending_actor") != (base["opponent_actor"] if direction == "own_first" else base["own_actor"]):
        return "rock_slide_nested_pair_transition_probability_or_actor_mismatch"
    factors = value.get("path_probability_factorization")
    if not isinstance(factors, Mapping) or _fraction(factors.get("order_probability")) != order or _fraction(factors.get("first_action_path_probability")) != source_probability or _fraction(factors.get("second_action_conditional_probability_mass")) != Fraction(1, 1) or _fraction(factors.get("order_weighted_source_probability")) != order * source_probability:
        return "rock_slide_nested_pair_probability_factorization_invalid"
    vector = value.get("recipient_vector")
    if not _vector(vector, base): return "rock_slide_nested_pair_vector_provenance_mismatch"
    second = value.get("second_action")
    if not isinstance(second, Mapping) or second.get("actor") != value["pending_actor"] or _fraction(second.get("conditional_probability")) != Fraction(1, 1): return "rock_slide_nested_pair_second_action_invalid"
    state = second.get("state")
    if state == "cancelled_due_to_faint":
        if second.get("reason") != "second_action_cancelled_due_to_faint" or not _state_for_owner(vector, value["pending_actor"], "fainted"):
            return "rock_slide_nested_pair_cancellation_faint_state_invalid"
    elif state == "outcome_ledger":
        if direction != "own_first" or second.get("builder_view_provenance") != "strict_hypothetical_rock_slide_vector_predictive_builder_view_v1" or isinstance(_attack_rows(second), str): return "rock_slide_nested_pair_builder_or_second_ledger_invalid"
    elif state == "rock_slide_graph":
        if direction != "opponent_first" or second.get("frozen_scope_adapter_provenance") != "detached_rock_slide_vector_to_unchanged_frozen_scope_graph_consumer_adapter_v1" or isinstance(_graph_rows(second.get("rock_slide_graph")), str): return "rock_slide_nested_pair_adapter_or_second_graph_invalid"
    else: return "rock_slide_nested_pair_second_action_state_invalid"
    return {"source_probability": source_probability, "transition": value, "vector": vector, "second_state": state}


def _graph_rows(graph: Any) -> tuple[Mapping[str, Any], ...] | str:
    if not isinstance(graph, Mapping): return "rock_slide_nested_pair_graph_missing"
    ledger = normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=graph)
    rows = graph_terminal_rows(ledger=ledger)
    return rows if not isinstance(rows, str) else "rock_slide_nested_pair_graph_invalid"


def _attack_rows(ledger: Any) -> tuple[Mapping[str, Any], ...] | str:
    if not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable" or _fraction(ledger.get("terminal_probability_mass")) != Fraction(1, 1): return "rock_slide_nested_pair_second_outcome_ledger_invalid"
    rows = ledger.get("terminal_leaves")
    if not isinstance(rows, tuple) or not rows: return "rock_slide_nested_pair_second_outcome_leaves_missing"
    ids: set[str] = set(); mass = Fraction()
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("leaf_id"), str) or row["leaf_id"] in ids or _fraction(row.get("probability")) <= 0 or not isinstance(row.get("consequences"), Mapping): return "rock_slide_nested_pair_second_outcome_leaf_invalid"
        ids.add(row["leaf_id"]); mass += _fraction(row["probability"])
    return rows if mass == Fraction(1, 1) else "rock_slide_nested_pair_second_outcome_mass_invalid"


def _vector(value: Any, base: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("hypothetical") is not True or value.get("current_authority") is True:
        return False
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner"):
        if value.get(key) != base.get(key): return False
    scope = value.get("frozen_execution_scope_authority")
    rows = value.get("ordered_recipient_states")
    return isinstance(scope, Mapping) and scope.get("action_id") == base["own_action_id"] and scope.get("move_id") == "rock-slide" and isinstance(rows, tuple) and len(rows) == 2 and all(isinstance(row, Mapping) and isinstance(row.get("owner"), Mapping) and _hp(row.get("hp")) and row.get("fainted") is (row["hp"] == 0) for row in rows)


def _state_for_owner(vector: Mapping[str, Any], owner: Mapping[str, Any], field: str) -> Any:
    rows = [row for row in (*vector.get("ordered_recipient_states", ()), vector.get("rock_slide_actor_state")) if isinstance(row, Mapping) and row.get("owner") == owner]
    return rows[0].get(field) if len(rows) == 1 else None


def _rows(*, pair: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    # Revalidation above makes these accesses strict; this iterator remains lazy
    # over source transitions and nested second-action leaves.
    for branch in pair["order_graphs"]:
        order = _fraction(branch["order_conditional_probability"])
        for transition in branch["terminal_transitions"]:
            vector = transition["recipient_vector"]; source = _fraction(transition["incoming_path_probability"])
            second = transition["second_action"]; pending = transition["pending_actor"]
            if second["state"] == "cancelled_due_to_faint":
                yield _row(branch["action_order"], order * source, transition, vector, pending, second, None, None)
            elif second["state"] == "outcome_ledger":
                for leaf in second["terminal_leaves"]:
                    yield _row(branch["action_order"], order * source * _fraction(leaf["probability"]), transition, vector, pending, second, leaf, None)
            else:
                rows = _graph_rows(second["rock_slide_graph"])
                assert not isinstance(rows, str)
                for rock in rows:
                    yield _row(branch["action_order"], order * source * rock["probability"], transition, vector, pending, second, None, rock)


def _row(order: str, probability: Fraction, transition: Mapping[str, Any], vector: Mapping[str, Any], pending: Mapping[str, Any], second: Mapping[str, Any], leaf: Mapping[str, Any] | None, rock: Mapping[str, Any] | None) -> dict[str, Any]:
    recipients = [deepcopy(dict(row)) for row in vector["ordered_recipient_states"]]
    actor = deepcopy(dict(vector["rock_slide_actor_state"]))
    if isinstance(rock, Mapping):
        for outcome in rock["ordered_recipient_outcomes"]:
            match = [row for row in recipients if row["owner"] == outcome["recipient"]["owner"]]
            assert len(match) == 1 and match[0]["hp"] == outcome["pre_hp"]
            match[0].update(hp=outcome["post_hp"], fainted=outcome["fainted"])
        source_id = rock["terminal_edge_id"]
    else:
        source_id = transition.get("first_terminal_source_id") or transition["first_terminal_leaf"]["leaf_id"]
    if isinstance(leaf, Mapping):
        consequences = leaf["consequences"]; provenance = leaf.get("provenance", {})
        attacker, target = provenance.get("attacker"), provenance.get("target")
        _apply_hp([*recipients, actor], attacker, consequences.get("own_final_hp"))
        _apply_hp([*recipients, actor], target, consequences.get("target_final_hp"))
    pending_state = next((row for row in [*recipients, actor] if row["owner"] == pending), None)
    return {"pair_terminal_id": f"{order}:{source_id}:{leaf.get('leaf_id') if isinstance(leaf, Mapping) else 'cancelled' if second['state'] == 'cancelled_due_to_faint' else source_id}", "order": order, "probability": probability, "ordered_recipient_states": tuple(recipients), "rock_slide_actor_state": actor, "pending_actor": deepcopy(dict(pending)), "pending_actor_state": deepcopy(pending_state), "second_action_state": second["state"], "rock_slide_source_terminal_id": source_id, "source_transition": deepcopy(dict(transition))}


def _apply_hp(rows: list[dict[str, Any]], owner: Any, hp: Any) -> None:
    if not isinstance(owner, Mapping) or not _hp(hp): return
    matches = [row for row in rows if row.get("owner") == owner]
    if len(matches) == 1: matches[0].update(hp=hp, fainted=hp == 0)


def _public_branch(value: Mapping[str, Any]) -> dict[str, Any]:
    return {"order": value["order"], "order_probability": _fd(value["order_probability"]), "conditional_terminal_probability_mass": _fd(Fraction(1, 1)), "order_weighted_terminal_probability_mass": _fd(value["weighted_mass"]), "source_transition_count": len(value["transitions"])}


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return None
    keys = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")
    return {key: deepcopy(value[key]) for key in keys} if all(key in value for key in keys) else None
def _fraction(value: Any) -> Fraction:
    try: return Fraction(value["numerator"], value["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return Fraction(-1, 1)
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any] | None, **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **(deepcopy(dict(base)) if isinstance(base, Mapping) else {}), "reason": reason, **deepcopy(extra)}
