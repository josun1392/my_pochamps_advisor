"""Immutable bridge from a frozen Rock Slide scope to multi-owner state rows."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_doubles_action_target_set_authority import SCHEMA_VERSION as TARGET_SET_SCHEMA
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import SCHEMA_VERSION as SCOPE_SCHEMA
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


SCHEMA_VERSION = "detached-rock-slide-multi-recipient-intermediate-state-vector-v1"
CONSUMER_SCHEMA_VERSION = "detached-rock-slide-frozen-execution-scope-consumer-view-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STAGES = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")


def materialize_detached_rock_slide_intermediate_state_vector(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], execution_scope_authority: Mapping[str, Any], scalar_intermediate_overlay: Mapping[str, Any] | None = None, source_terminal_path: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Freeze recipient rows; optional exact sources may only overlay one owner."""
    base = _base(strategy_d0, execution_scope_authority)
    if base is None:
        return _result("rejected", "invalid_rock_slide_intermediate_vector_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    scope = _scope(execution_scope_authority, base)
    if isinstance(scope, str):
        return _result("rejected", scope, base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping) or state.get("session_id") != base["session_id"]:
        return _result("rejected", "rock_slide_intermediate_vector_runtime_state_invalid", base)
    rows = [_row_from_runtime(state, recipient, index) for index, recipient in enumerate(scope["recipients"], 1)]
    if any(isinstance(row, str) for row in rows):
        return _result("incomplete", next(row for row in rows if isinstance(row, str)), base)
    actor = _actor_row(state, base["rock_slide_actor"])
    if isinstance(actor, str):
        return _result("incomplete", actor, base)
    path = _terminal_path(source_terminal_path, rows, base)
    if isinstance(path, str):
        return _result("rejected", path, base)
    if path is not None:
        rows = _apply_terminal_path(rows, path)
    overlay = _overlay(scalar_intermediate_overlay, base)
    if isinstance(overlay, str):
        return _result("rejected", overlay, base)
    if overlay is not None:
        matched = [index for index, row in enumerate(rows) if row["owner"] == overlay["owner"]]
        if len(matched) == 1:
            rows[matched[0]] = {**rows[matched[0]], **overlay["state"], "state_provenance": "exact_scalar_intermediate_overlay"}
        elif actor["owner"] == overlay["owner"]:
            actor = {**actor, **overlay["state"], "state_provenance": "exact_scalar_intermediate_overlay"}
        else:
            return _result("incomplete", "scalar_overlay_owner_not_exactly_one_frozen_recipient", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "hypothetical": True,
        "horizon": "immediate_action_consequence", **base,
        "frozen_target_set_authority": deepcopy(scope["target_set_authority"]),
        "frozen_execution_scope_authority": deepcopy(dict(execution_scope_authority)),
        "ordered_recipient_states": tuple(deepcopy(row) for row in rows),
        "rock_slide_actor_state": deepcopy(actor),
        "source_terminal_path": deepcopy(path), "source_scalar_intermediate_overlay": deepcopy(scalar_intermediate_overlay),
        "target_set_rule": "frozen_recipients_preserved_after_faint_no_replacement_or_recomputation",
        "provenance": "strict_frozen_rock_slide_scope_to_detached_multi_recipient_state_vector_v1",
    }


def extract_detached_rock_slide_pending_actor_scalar_view(*, vector: Mapping[str, Any], pending_actor: Mapping[str, Any], pending_target: Mapping[str, Any]) -> dict[str, Any]:
    """Return exact actor/target rows for a later two-owner consumer; no execution."""
    parsed = _vector(vector)
    if isinstance(parsed, str):
        return _view_result("rejected", parsed, {})
    if not _owner(pending_actor) or not _owner(pending_target) or pending_actor == pending_target:
        return _view_result("rejected", "pending_actor_or_target_identity_invalid", parsed["base"])
    states = {tuple(row["owner"][key] for key in _OWNER_KEYS): row for row in (*parsed["rows"], parsed["actor"])}
    actor = states.get(tuple(pending_actor[key] for key in _OWNER_KEYS)); target = states.get(tuple(pending_target[key] for key in _OWNER_KEYS))
    if actor is None or target is None:
        return _view_result("incomplete", "pending_actor_or_target_not_exactly_represented_in_vector", parsed["base"])
    return {"status": "resolved", "schema_version": CONSUMER_SCHEMA_VERSION, "hypothetical": True, **parsed["base"], "pending_actor": deepcopy(dict(pending_actor)), "pending_target": deepcopy(dict(pending_target)), "actor_state": deepcopy(actor), "target_state": deepcopy(target), "actor_can_act": not actor["fainted"], "frozen_execution_scope_authority": deepcopy(vector["frozen_execution_scope_authority"]), "provenance": "detached_multi_recipient_vector_to_exact_pending_actor_scalar_view_v1"}


def freeze_detached_rock_slide_execution_scope_consumer_view(*, vector: Mapping[str, Any]) -> dict[str, Any]:
    """Expose immutable scope provenance plus vector rows to a future graph consumer."""
    parsed = _vector(vector)
    if isinstance(parsed, str):
        return _view_result("rejected", parsed, {})
    return {"status": "resolved", "schema_version": CONSUMER_SCHEMA_VERSION, "hypothetical": True, **parsed["base"], "ordered_recipient_states": deepcopy(parsed["rows"]), "rock_slide_actor_state": deepcopy(parsed["actor"]), "frozen_execution_scope_authority": deepcopy(vector["frozen_execution_scope_authority"]), "provenance": "detached_multi_recipient_vector_to_frozen_scope_consumer_view_v1"}


def build_detached_rock_slide_vector_predictive_builder_view(*, vector: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], pending_actor: Mapping[str, Any], pending_target: Mapping[str, Any]) -> dict[str, Any]:
    """Build a private, explicitly non-current two-owner predictive input."""
    scalar = extract_detached_rock_slide_pending_actor_scalar_view(vector=vector, pending_actor=pending_actor, pending_target=pending_target)
    if scalar.get("status") != "resolved": return _view_result(scalar.get("status", "rejected"), scalar.get("reason", "pending_scalar_view_unavailable"), scalar)
    snapshot = _private_snapshot(runtime_snapshot, (scalar["actor_state"], scalar["target_state"]), scalar["pending_actor"])
    if isinstance(snapshot, str): return _view_result("incomplete", snapshot, scalar)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=scalar["pending_actor"])
    if d0.get("status") != "resolved": return _view_result("incomplete", d0.get("reason", "private_predictive_d0_unavailable"), scalar)
    return {"status": "resolved", "schema_version": CONSUMER_SCHEMA_VERSION, "hypothetical": True, "current_authority": False, **{key: deepcopy(scalar[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "decision_point", "rock_slide_actor", "action_id", "move_id")}, "pending_actor": deepcopy(scalar["pending_actor"]), "pending_target": deepcopy(scalar["pending_target"]), "actor_state": deepcopy(scalar["actor_state"]), "target_state": deepcopy(scalar["target_state"]), "actor_can_act": scalar["actor_can_act"], "predictive_runtime_snapshot": snapshot, "predictive_strategy_d0": d0, "intermediate_overrides": {"actor": deepcopy(scalar["actor_state"]), "target": deepcopy(scalar["target_state"]), "condition_override_requires_direct_consumer": True}, "frozen_execution_scope_authority": deepcopy(scalar["frozen_execution_scope_authority"]), "provenance": "detached_rock_slide_vector_to_private_scalar_predictive_builder_view_v1"}


def freeze_detached_rock_slide_frozen_scope_graph_consumer_adapter(*, vector: Mapping[str, Any], runtime_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Bind private vector state to the unchanged original Rock Slide scope."""
    parsed = _vector(vector)
    if isinstance(parsed, str): return _view_result("rejected", parsed, {})
    scope = vector.get("frozen_execution_scope_authority")
    if not isinstance(scope, Mapping) or _scope(scope, parsed["base"]) is None or isinstance(_scope(scope, parsed["base"]), str): return _view_result("rejected", "frozen_scope_consumer_scope_binding_mismatch", parsed["base"])
    snapshot = _private_snapshot(runtime_snapshot, (*parsed["rows"], parsed["actor"]), parsed["base"]["rock_slide_actor"])
    if isinstance(snapshot, str): return _view_result("incomplete", snapshot, parsed["base"])
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=parsed["base"]["rock_slide_actor"])
    if d0.get("status") != "resolved": return _view_result("incomplete", d0.get("reason", "private_rock_slide_d0_unavailable"), parsed["base"])
    return {"status": "resolved", "schema_version": CONSUMER_SCHEMA_VERSION, "hypothetical": True, "current_authority": False, **parsed["base"], "ordered_recipient_states": deepcopy(parsed["rows"]), "rock_slide_actor_state": deepcopy(parsed["actor"]), "frozen_execution_scope_authority": deepcopy(dict(scope)), "predictive_runtime_snapshot": snapshot, "predictive_strategy_d0": d0, "target_set_rule": vector.get("target_set_rule"), "vector_provenance": vector.get("provenance"), "provenance": "detached_rock_slide_vector_to_unchanged_frozen_scope_graph_consumer_adapter_v1"}


def _private_snapshot(runtime_snapshot: Any, rows: tuple[Mapping[str, Any], ...], decision_owner: Mapping[str, Any]) -> dict[str, Any] | str:
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping): return "private_vector_runtime_snapshot_missing"
    synthetic = deepcopy(dict(state))
    seen = set()
    for row in rows:
        if not isinstance(row, Mapping) or not _owner(row.get("owner")): return "private_vector_state_row_invalid"
        owner = row["owner"]; identity = tuple(owner[key] for key in _OWNER_KEYS)
        if identity in seen: continue
        seen.add(identity); raw = _pokemon(synthetic, owner)
        if raw is None or not _hp(row.get("hp")) or not _hp(row.get("max_hp")) or row["hp"] > row["max_hp"] or row.get("fainted") is not (row["hp"] == 0) or not isinstance(row.get("stages"), Mapping): return "private_vector_state_override_invalid"
        raw["current_hp"] = row["hp"]; raw["max_hp"] = row["max_hp"]; raw["fainted"] = row["fainted"]; raw["stat_stages"] = deepcopy(dict(row["stages"])); raw["detached_vector_private_state"] = True
    return {"status": "runtime_snapshot_ready", "session_id": state.get("session_id"), "state": synthetic, "state_fingerprint": state_fingerprint(synthetic), "hypothetical": True, "current_authority": False}


def _base(d0: Any, scope: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(scope, Mapping) or not _owner(d0.get("decision_owner")):
        return None
    return {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0["decision_owner"]), "decision_point": scope.get("decision_point"), "rock_slide_actor": deepcopy(d0["decision_owner"]), "action_id": scope.get("action_id"), "move_id": scope.get("move_id")}


def _scope(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCOPE_SCHEMA:
        return "rock_slide_execution_scope_authority_unavailable"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "decision_point", "action_id", "move_id")
    if any(value.get(key) != base.get(key) for key in keys) or value.get("acting_owner") != base["rock_slide_actor"] or value.get("move_id") != "rock-slide":
        return "rock_slide_execution_scope_binding_mismatch"
    target = value.get("target_set_authority")
    if not isinstance(target, Mapping) or target.get("status") != "resolved" or target.get("schema_version") != TARGET_SET_SCHEMA:
        return "rock_slide_frozen_target_set_authority_unavailable"
    if any(target.get(key) != base.get(key) for key in keys) or target.get("acting_owner") != base["rock_slide_actor"]:
        return "rock_slide_frozen_target_set_binding_mismatch"
    recipients = value.get("recipients")
    if not isinstance(recipients, tuple) or recipients != target.get("recipients") or len(recipients) != 2 or not _recipients(recipients):
        return "rock_slide_frozen_recipient_order_mismatch"
    return {"recipients": recipients, "target_set_authority": target}


def _row_from_runtime(state: Mapping[str, Any], recipient: Mapping[str, Any], index: int) -> dict[str, Any] | str:
    owner = recipient["owner"]; raw = _pokemon(state, owner)
    if raw is None: return "frozen_recipient_runtime_identity_or_state_missing"
    hp, max_hp, fainted, stages = raw.get("current_hp"), raw.get("max_hp"), raw.get("fainted"), raw.get("stat_stages")
    if not _hp(hp) or not _hp(max_hp) or max_hp < 1 or hp > max_hp or fainted is not (hp == 0): return "frozen_recipient_exact_hp_or_faint_missing"
    if not isinstance(stages, Mapping) or any(not isinstance(stages.get(stat), int) or isinstance(stages.get(stat), bool) or not -6 <= stages[stat] <= 6 for stat in _STAGES): return "frozen_recipient_exact_stage_missing"
    condition = _condition(raw)
    if condition is None: return "frozen_recipient_exact_condition_missing"
    return {"recipient_index": index, "recipient": deepcopy(dict(recipient)), "owner": deepcopy(dict(owner)), "hp": hp, "max_hp": max_hp, "fainted": fainted, "stages": {stat: stages[stat] for stat in _STAGES}, "condition": condition, "state_provenance": "frozen_runtime_topology_recipient_state"}


def _actor_row(state: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any] | str:
    raw = _pokemon(state, owner)
    if raw is None: return "rock_slide_actor_runtime_identity_or_state_missing"
    pseudo = {"owner": owner, "side": owner["side"], "active_slot_index": owner["slot_index"], "relation": "self", "selected": False}
    row = _row_from_runtime(state, pseudo, 0)
    return {**row, "recipient_index": None, "recipient": None, "state_provenance": "frozen_runtime_rock_slide_actor_state"} if isinstance(row, Mapping) else row


def _terminal_path(value: Any, rows: list[dict[str, Any] | str], base: Mapping[str, Any]) -> Mapping[str, Any] | None | str:
    if value is None: return None
    if not isinstance(value, Mapping) or not isinstance(value.get("terminal_edge_id"), str) or not isinstance(value.get("source_path_reference"), Mapping) or value["source_path_reference"].get("terminal_edge_id") != value["terminal_edge_id"] or not isinstance(value.get("ordered_recipient_outcomes"), tuple): return "rock_slide_terminal_path_identity_missing"
    outcomes = value["ordered_recipient_outcomes"]
    if len(outcomes) != len(rows): return "rock_slide_terminal_path_recipient_count_mismatch"
    for row, outcome in zip(rows, outcomes):
        if not isinstance(row, Mapping) or not isinstance(outcome, Mapping) or outcome.get("recipient") != row["recipient"] or outcome.get("recipient_index") != row["recipient_index"] or not _hp(outcome.get("post_hp")) or outcome.get("fainted") is not (outcome["post_hp"] == 0): return "rock_slide_terminal_path_recipient_binding_mismatch"
    return deepcopy(dict(value))


def _apply_terminal_path(rows: list[dict[str, Any]], path: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = deepcopy(rows)
    for row, outcome in zip(result, path["ordered_recipient_outcomes"]):
        row["hp"] = outcome["post_hp"]; row["fainted"] = outcome["fainted"]; row["state_provenance"] = "exact_rock_slide_terminal_path"
    return result


def _overlay(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None | str:
    if value is None: return None
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "detached-predictive-intermediate-state-v1": return "scalar_intermediate_overlay_unavailable"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
    if any(value.get(key) != base.get(key) for key in keys): return "scalar_intermediate_overlay_binding_mismatch"
    first, active = value.get("first_action"), value.get("active")
    provenance = first.get("provenance") if isinstance(first, Mapping) else None
    owner = provenance.get("target") if isinstance(provenance, Mapping) else None
    if not isinstance(first, Mapping) or not isinstance(first.get("leaf_id"), str) or not isinstance(active, Mapping) or not _owner(owner): return "scalar_intermediate_overlay_source_leaf_missing"
    participant = active.get(owner["side"])
    if not isinstance(participant, Mapping) or participant.get("owner") != owner: return "scalar_intermediate_overlay_target_identity_mismatch"
    hp = participant.get("hypothetical_hp", {}); fainted = participant.get("hypothetical_fainted", {}); stages = participant.get("hypothetical_stages"); condition = participant.get("hypothetical_condition")
    if hp.get("status") != "known" or not _hp(hp.get("value")) or fainted.get("status") != "known" or fainted.get("value") is not (hp["value"] == 0) or not isinstance(stages, Mapping) or any(stages.get(stat, {}).get("status") != "known" or not isinstance(stages[stat].get("value"), int) for stat in _STAGES) or not isinstance(condition, Mapping): return "scalar_intermediate_overlay_exact_state_missing"
    return {"owner": deepcopy(dict(owner)), "state": {"hp": hp["value"], "fainted": fainted["value"], "stages": {stat: stages[stat]["value"] for stat in _STAGES}, "condition": deepcopy(dict(condition))}}


def _vector(value: Any) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCHEMA_VERSION or value.get("hypothetical") is not True: return "rock_slide_intermediate_vector_unavailable"
    base = {key: deepcopy(value.get(key)) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "decision_point", "rock_slide_actor", "action_id", "move_id")}
    rows, actor = value.get("ordered_recipient_states"), value.get("rock_slide_actor_state")
    if not isinstance(rows, tuple) or len(rows) != 2 or not all(isinstance(row, Mapping) and _owner(row.get("owner")) and row.get("recipient_index") == index for index, row in enumerate(rows, 1)) or not isinstance(actor, Mapping) or not _owner(actor.get("owner")) or actor.get("owner") != base["rock_slide_actor"]: return "rock_slide_intermediate_vector_state_rows_invalid"
    if len({tuple(row["owner"][key] for key in _OWNER_KEYS) for row in rows}) != len(rows): return "rock_slide_intermediate_vector_duplicate_recipient"
    return {"base": base, "rows": rows, "actor": actor}


def _condition(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    condition, provenance = raw.get("condition"), raw.get("condition_provenance")
    if condition == "none" and isinstance(provenance, Mapping): return {"status": "known_none", "source": "frozen_runtime_condition_observation", "provenance": deepcopy(dict(provenance))}
    if isinstance(condition, str) and condition and condition != "none" and isinstance(provenance, Mapping): return {"status": "known_present", "condition": condition, "source": "frozen_runtime_condition_observation", "provenance": deepcopy(dict(provenance))}
    return None
def _recipients(value: tuple[Any, ...]) -> bool:
    return all(isinstance(row, Mapping) and row.get("recipient_index", index) == index and _owner(row.get("owner")) and row.get("side") == row["owner"].get("side") and row.get("active_slot_index") == row["owner"].get("slot_index") for index, row in enumerate(value, 1)) and len({tuple(row["owner"][key] for key in _OWNER_KEYS) for row in value}) == len(value)
def _pokemon(state: Mapping[str, Any], owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side"); roster = side.get("pokemon") if isinstance(side, Mapping) else None; raw = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return raw if isinstance(raw, Mapping) and raw.get("pokemon_id") == owner.get("pokemon_id") else None
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
def _view_result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": CONSUMER_SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
