"""Detached Champions sleep, Yawn, and Rest application authority.

This bounded family installs the already-owned Champions sleep progression; it
does not implement a second action gate or ordinary-duration RNG.
"""
from copy import deepcopy
from typing import Mapping

from llm.advisor_identity_groundedness import project_identity_groundedness
from llm.advisor_reducer_state_model import state_fingerprint

SCHEMA = "champions-sleep-application-authority-v1"
YAWN_SCHEMA = "champions-yawn-drowsiness-v1"
CATALOG = {
    "hypnosis": {"accuracy": 60, "powder": False},
    "sleep-powder": {"accuracy": 75, "powder": True},
    "spore": {"accuracy": 100, "powder": True},
}


def _owner(state, owner):
    return state.get(f"{owner['side']}_side", {}).get("pokemon", {}).get(owner["slot_index"])


def _base(d0, actor, target, action, path, *, allow_self=False):
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not all(isinstance(x, Mapping) for x in (actor, target, action)):
        return None
    if d0.get("active_owners", {}).get(actor.get("side")) != dict(actor) or d0.get("active_owners", {}).get(target.get("side")) != dict(target) or (not allow_self and actor.get("side") == target.get("side")) or not isinstance(action.get("action_id"), str) or not isinstance(action.get("identity"), str):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "actor": deepcopy(actor), "target": deepcopy(target), "action_id": action["action_id"], "move_id": action["identity"], "path": tuple(path)}


def _bound(result, base):
    return isinstance(result, Mapping) and result.get("status") == "resolved" and all(result.get(k) == base.get(k) for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "actor", "target", "action_id", "move_id"))


def _exact_condition(raw):
    provenance = raw.get("condition_provenance") if isinstance(raw, Mapping) else None
    value = raw.get("condition") if isinstance(raw, Mapping) else None
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_condition_observed" or provenance.get("trust") != "user_confirmed_observation": return None
    if value in (None, "none") and provenance.get("condition") == "none": return "none"
    return value if value in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"} and provenance.get("condition") == value else None


def _known_types(raw):
    value, provenance = raw.get("current_type"), raw.get("current_type_provenance")
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value) or not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_type_observed": return None
    return tuple(value)


def _known_item(raw):
    value, provenance = raw.get("known_item"), raw.get("known_item_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_item_observed": return None
    if value is None and provenance.get("status") == "known_absent": return None, True
    return (value, True) if isinstance(value, str) and value else None


def _sleep_prevention(*, state, actor, target, powder, allow_safeguard, allow_substitute, allow_existing_condition=False):
    raw, source = _owner(state, target), _owner(state, actor)
    if not isinstance(raw, Mapping) or not isinstance(source, Mapping): return "sleep_active_identity_missing"
    condition = _exact_condition(raw)
    if condition is None: return "target_current_condition_unknown"
    if condition != "none" and not allow_existing_condition: return "target_already_major_statused"
    abilities = {side: _owner(state, {"side": side, "slot_index": state.get(f"{side}_side", {}).get("active_slot_index")}).get("current_ability") for side in ("self", "opponent")}
    if not all(isinstance(value, str) and value for value in abilities.values()): return "sleep_ability_authority_unknown"
    gas = "neutralizing-gas" in abilities.values(); mold_breaker = source.get("current_ability") == "mold-breaker" and not gas
    target_ability = raw.get("current_ability")
    if target_ability in {"insomnia", "vital-spirit", "sweet-veil", "purifying-salt"} and not gas and not mold_breaker: return f"blocked_by_{target_ability}"
    field = state.get("field") if isinstance(state.get("field"), Mapping) else {}
    terrain = field.get("terrain")
    if terrain == "electric":
        grounded = project_identity_groundedness(state, side=target["side"]).get("status")
        if grounded == "unknown": return "electric_terrain_groundedness_unknown"
        if grounded == "grounded": return "blocked_by_electric_terrain"
    if target_ability == "leaf-guard" and field.get("weather") == "sun" and not gas and not mold_breaker: return "blocked_by_leaf_guard"
    if powder:
        types = _known_types(raw)
        item = _known_item(raw)
        if types is None or item is None: return "powder_blocker_authority_unknown"
        if "grass" in types: return "blocked_by_grass_type"
        if target_ability == "overcoat" and not gas and not mold_breaker: return "blocked_by_overcoat"
        if item[0] == "safety-goggles": return "blocked_by_safety_goggles"
    if allow_safeguard:
        side = state.get(f"{target['side']}_side", {})
        conditions = side.get("side_conditions") if isinstance(side, Mapping) else None
        if not isinstance(conditions, list): return "safeguard_authority_unknown"
        if "safeguard" in conditions: return "blocked_by_safeguard"
    if allow_substitute:
        context = state.get("substitute_state_context")
        if isinstance(context, Mapping):
            rows = [row for row in context.get("states", []) if isinstance(row, Mapping) and row.get("owner") == dict(target)]
            if len(rows) != 1 or rows[0].get("state") == "unknown": return "substitute_authority_unknown"
            if rows[0].get("state") == "known_active" and source.get("current_ability") != "infiltrator": return "blocked_by_substitute"
    return {"abilities": abilities, "suppressed": gas, "condition": condition, "terrain": terrain}


def _sleep_progression(*, owner, observation, origin_id, established_turn, source):
    return {"schema_version": "champions-sleep-freeze-progression-v1", "owner": deepcopy(owner), "condition": "sleep", "origin_id": origin_id, "established_turn": established_turn, "prior_attempts": 0, "sleep_duration": None if source != "rest" else 2, "condition_observation": deepcopy(observation), "observed_turn": established_turn, "sleep_source": source, "provenance": "detached_champions_sleep_application_v1"}


def freeze_champions_direct_sleep_application(*, strategy_d0, runtime_snapshot, actor, target, action, move_success_authority, path=(), reflection_authority=None):
    base = _base(strategy_d0, actor, target, action, path)
    if base is None: return {"status": "rejected", "reason": "sleep_application_binding_invalid"}
    rule = CATALOG.get(base["move_id"])
    if rule is None: return {"status": "unsupported", "reason": "move_not_in_champions_direct_sleep_catalog", **base}
    if not isinstance(runtime_snapshot, Mapping) or runtime_snapshot.get("state_fingerprint") != base["source_runtime_fingerprint"]: return {"status": "rejected", "reason": "stale_sleep_application_runtime", **base}
    if not _bound(move_success_authority, base): return {"status": "incomplete", "reason": "sleep_move_success_authority_missing_or_foreign", **base}
    outcome = move_success_authority.get("outcome")
    if outcome not in {"hit", "missed", "blocked_by_protection"}: return {"status": "rejected", "reason": "sleep_move_success_outcome_invalid", **base}
    if reflection_authority is not None:
        if not _bound(reflection_authority, base): return {"status": "incomplete", "reason": "sleep_reflection_authority_missing_or_foreign", **base}
        if reflection_authority.get("outcome") == "reflected": return {"status": "incomplete", "reason": "reflected_sleep_application_owner_unavailable", **base}
        if reflection_authority.get("outcome") != "not_reflected": return {"status": "incomplete", "reason": "sleep_reflection_authority_incomplete", **base}
    prevention = "move_missed" if outcome == "missed" else "blocked_by_protection" if outcome == "blocked_by_protection" else _sleep_prevention(state=runtime_snapshot["state"], actor=actor, target=target, powder=rule["powder"], allow_safeguard=True, allow_substitute=True)
    if isinstance(prevention, str) and prevention.endswith(("unknown", "missing")): return {"status": "incomplete", "reason": prevention, **base}
    if prevention == "sleep_active_identity_missing": return {"status": "rejected", "reason": prevention, **base}
    authority = {"status": "resolved", "schema_version": SCHEMA, **base, "kind": "direct_sleep", "accuracy": rule["accuracy"], "powder": rule["powder"], "move_success_authority": deepcopy(move_success_authority), "reflection_authority": deepcopy(reflection_authority), "prevention": deepcopy(prevention), "sleep_source": "direct", "provenance": "champions_direct_sleep_application_v1"}
    authority["validation_request"] = {"strategy_d0": deepcopy(strategy_d0), "runtime_snapshot": deepcopy(runtime_snapshot), "actor": deepcopy(actor), "target": deepcopy(target), "action": deepcopy(action), "move_success_authority": deepcopy(move_success_authority), "path": tuple(path), "reflection_authority": deepcopy(reflection_authority)}
    return authority


def validate_champions_direct_sleep_application(authority):
    try:
        if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != SCHEMA: raise ValueError()
        if freeze_champions_direct_sleep_application(**authority["validation_request"]) != authority: raise ValueError()
        return {"status": "resolved", "authority": deepcopy(authority)}
    except (KeyError, TypeError, ValueError):
        return {"status": "rejected", "reason": "direct_sleep_application_provenance_invalid"}


def materialize_champions_direct_sleep_application(*, authority, runtime_snapshot):
    if validate_champions_direct_sleep_application(authority).get("status") != "resolved" or runtime_snapshot.get("state_fingerprint") != authority.get("source_runtime_fingerprint"): return {"status": "rejected", "reason": "invalid_or_foreign_direct_sleep_authority"}
    state = deepcopy(runtime_snapshot["state"]); raw = _owner(state, authority["target"]); applies = isinstance(authority["prevention"], Mapping)
    if applies:
        observation = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "sleep", "hypothetical_provenance": "champions_direct_sleep_application_v1"}
        raw["condition"] = "sleep"; raw["condition_provenance"] = observation
        raw["champions_status_progression"] = _sleep_progression(owner=authority["target"], observation=observation, origin_id=f"{authority['action_id']}:sleep", established_turn=1, source="direct")
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
    return {"status": "resolved", "runtime_snapshot": snapshot, "sleep_applied": applies, "outcome": "applies" if applies else authority["prevention"], "authority": deepcopy(authority), "provenance": "detached_champions_direct_sleep_application_v1"}


def materialize_champions_yawn_drowsiness(*, strategy_d0, runtime_snapshot, actor, target, action, move_success_authority, established_turn, path=(), reflection_authority=None):
    base = _base(strategy_d0, actor, target, action, path)
    if base is None or base["move_id"] != "yawn" or not isinstance(established_turn, int) or established_turn < 1: return {"status": "rejected", "reason": "yawn_application_binding_invalid"}
    if not _bound(move_success_authority, base) or move_success_authority.get("outcome") not in {"hit", "missed", "blocked_by_protection"}: return {"status": "incomplete", "reason": "yawn_success_authority_missing_or_foreign", **base}
    if runtime_snapshot.get("state_fingerprint") != base["source_runtime_fingerprint"]: return {"status": "rejected", "reason": "stale_yawn_runtime", **base}
    if reflection_authority is not None and (not _bound(reflection_authority, base) or reflection_authority.get("outcome") != "not_reflected"): return {"status": "incomplete", "reason": "yawn_reflection_owner_required", **base}
    outcome = move_success_authority["outcome"]
    prevention = "move_missed" if outcome == "missed" else "blocked_by_protection" if outcome == "blocked_by_protection" else _sleep_prevention(state=runtime_snapshot["state"], actor=actor, target=target, powder=False, allow_safeguard=True, allow_substitute=True)
    if isinstance(prevention, str) and prevention.endswith(("unknown", "missing")): return {"status": "incomplete", "reason": prevention, **base}
    state = deepcopy(runtime_snapshot["state"]); raw = _owner(state, target)
    if isinstance(prevention, Mapping): raw["champions_yawn_drowsiness"] = {"schema_version": YAWN_SCHEMA, "owner": deepcopy(target), "source": deepcopy(actor), "action_id": action["action_id"], "move_id": "yawn", "established_turn": established_turn, "resolve_at_turn": established_turn + 1, "path": tuple(path), "provenance": "champions_yawn_drowsiness_v1"}
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
    return {"status": "resolved", "runtime_snapshot": snapshot, "drowsy_established": isinstance(prevention, Mapping), "outcome": "drowsy" if isinstance(prevention, Mapping) else prevention, "prevention_authority": deepcopy(prevention), **base, "provenance": "champions_yawn_application_v1"}


def resolve_champions_yawn_at_end_of_turn(*, strategy_d0, runtime_snapshot, target, resolution_turn, path=()):
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("active_owners", {}).get(target.get("side")) != dict(target) or runtime_snapshot.get("state_fingerprint") != strategy_d0.get("source_runtime_fingerprint") or not isinstance(resolution_turn, int): return {"status": "rejected", "reason": "yawn_resolution_binding_invalid"}
    state = deepcopy(runtime_snapshot["state"]); raw = _owner(state, target); drowsy = raw.get("champions_yawn_drowsiness") if isinstance(raw, Mapping) else None
    if not isinstance(drowsy, Mapping) or drowsy.get("schema_version") != YAWN_SCHEMA or drowsy.get("owner") != dict(target): return {"status": "rejected", "reason": "yawn_drowsiness_missing_or_foreign"}
    if resolution_turn != drowsy.get("resolve_at_turn"): return {"status": "rejected", "reason": "yawn_resolution_boundary_invalid"}
    prevention = _sleep_prevention(state=state, actor=drowsy["source"], target=target, powder=False, allow_safeguard=False, allow_substitute=False)
    if isinstance(prevention, str) and prevention.endswith(("unknown", "missing")): return {"status": "incomplete", "reason": prevention}
    raw.pop("champions_yawn_drowsiness", None); applies = isinstance(prevention, Mapping)
    if applies:
        observation = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": resolution_turn, "condition": "sleep", "hypothetical_provenance": "champions_yawn_delayed_sleep_v1"}
        raw["condition"] = "sleep"; raw["condition_provenance"] = observation
        raw["champions_status_progression"] = _sleep_progression(owner=target, observation=observation, origin_id=f"{drowsy['action_id']}:yawn-sleep", established_turn=resolution_turn, source="yawn")
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
    return {"status": "resolved", "runtime_snapshot": snapshot, "sleep_applied": applies, "outcome": "applies" if applies else prevention, "drowsiness": deepcopy(drowsy), "resolution_turn": resolution_turn, "path": tuple(path), "provenance": "champions_yawn_delayed_resolution_v1"}


def materialize_champions_rest(*, strategy_d0, runtime_snapshot, actor, action, path=()):
    base = _base(strategy_d0, actor, actor, action, path, allow_self=True)
    if base is None or base["move_id"] != "rest": return {"status": "rejected", "reason": "rest_application_binding_invalid"}
    if runtime_snapshot.get("state_fingerprint") != base["source_runtime_fingerprint"]: return {"status": "rejected", "reason": "stale_rest_runtime", **base}
    state = deepcopy(runtime_snapshot["state"]); raw = _owner(state, actor)
    if not isinstance(raw, Mapping) or not isinstance(raw.get("current_hp"), int) or not isinstance(raw.get("max_hp"), int): return {"status": "incomplete", "reason": "rest_hp_authority_unknown", **base}
    if raw["current_hp"] >= raw["max_hp"]: return {"status": "resolved", "rest_applied": False, "outcome": "rest_failed_full_hp", **base}
    # Rest is self-origin: side protection and Substitute are deliberately irrelevant.
    prevention = _sleep_prevention(state=state, actor=actor, target=actor, powder=False, allow_safeguard=False, allow_substitute=False, allow_existing_condition=True)
    if isinstance(prevention, str) and prevention.endswith(("unknown", "missing")): return {"status": "incomplete", "reason": prevention, **base}
    if isinstance(prevention, str): return {"status": "resolved", "rest_applied": False, "outcome": prevention, **base}
    before_hp, prior_condition = raw["current_hp"], _exact_condition(raw)
    raw["current_hp"] = raw["max_hp"]
    observation = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "sleep", "hypothetical_provenance": "champions_rest_fixed_sleep_v1"}
    raw["condition"] = "sleep"; raw["condition_provenance"] = observation
    raw["champions_status_progression"] = _sleep_progression(owner=actor, observation=observation, origin_id=f"{action['action_id']}:rest", established_turn=1, source="rest")
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
    result = {"status": "resolved", "rest_applied": True, "outcome": "applies", "hp_before": before_hp, "hp_after": raw["max_hp"], "prior_condition": prior_condition, "sleep_source": "rest", "fixed_sleep_duration": 2, "runtime_snapshot": snapshot, **base, "provenance": "champions_rest_atomic_application_v1"}
    result["validation_request"] = {"strategy_d0": deepcopy(strategy_d0), "runtime_snapshot": deepcopy(runtime_snapshot), "actor": deepcopy(actor), "action": deepcopy(action), "path": tuple(path)}
    return result


def validate_champions_rest(result):
    try:
        if not isinstance(result, Mapping) or result.get("status") != "resolved" or result.get("rest_applied") is not True: raise ValueError()
        if materialize_champions_rest(**result["validation_request"]) != result: raise ValueError()
        return {"status": "resolved", "result": deepcopy(result)}
    except (KeyError, TypeError, ValueError):
        return {"status": "rejected", "reason": "champions_rest_provenance_invalid"}
