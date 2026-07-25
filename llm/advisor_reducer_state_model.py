"""Pure validation and dry-run projection for the private battle-state-v1 model."""
from copy import deepcopy

STATE_MODEL_VERSION = "battle-state-v1"
_TARGETS = {"apply_exact_hp_transition": "pokemon.current_hp", "set_condition": "pokemon.condition", "clear_condition": "pokemon.condition", "consume_item": "pokemon.known_item", "remove_item": "pokemon.known_item", "start_weather": "field.weather", "end_weather": "field.weather", "start_terrain": "field.terrain", "end_terrain": "field.terrain", "start_side_condition": "side.side_conditions", "end_side_condition": "side.side_conditions", "switch_active": "side.active_slot_index", "mark_fainted": "pokemon.fainted"}


def validate_atomic_transition(base_state, replay_plan, expected_session_id):
    """v15.21 schema-only guard; it intentionally does not project state."""
    base = deepcopy(base_state) if isinstance(base_state, dict) else {}
    plan = deepcopy(replay_plan) if isinstance(replay_plan, dict) else {}
    if base.get("state_version") != STATE_MODEL_VERSION:
        return _legacy_result("unsupported_state_version", base, plan)
    if base.get("session_id") != expected_session_id or plan.get("session_id") != expected_session_id:
        return _legacy_result("invalid_base_state", base, plan)
    if plan.get("status") != "planned":
        return _legacy_result("blocked_by_conflict" if plan.get("conflicts") else "invalid_replay_plan", base, plan)
    steps = plan.get("ordered_steps", [])
    if not steps:
        return _legacy_result("no_reducer_steps", base, plan)
    targets = []
    for step in steps:
        effect = step.get("planned_effect") if isinstance(step, dict) else None
        target = _TARGETS.get(effect)
        if target is None:
            return _legacy_result("invalid_replay_plan", base, plan)
        targets.append({"observation_id": step.get("observation_id"), "target_state_field": target, "planned_effect": effect})
    return {"status": "ready_for_atomic_transition", "base_state": base, "planned_next_state_schema": targets, "accepted_step_ids": [x.get("observation_id") for x in steps], "rejected_step_ids": [], "conflicts": [], "limitations": ["dry_run_only", "no_state_mutation", "unknown_values_not_overwritten"]}


def project_atomic_transition(base_state, replay_plan, expected_session_id=None, state_model_version=STATE_MODEL_VERSION):
    """Validate an entire plan and return a detached projected state only on success.

    This is deliberately a private reducer-time dry run: it never touches UI/runtime
    state, makes no provider calls, and never returns a prefix after a conflict.
    """
    base = deepcopy(base_state) if isinstance(base_state, dict) else None
    plan = deepcopy(replay_plan) if isinstance(replay_plan, dict) else None
    if state_model_version != STATE_MODEL_VERSION or not isinstance(base, dict) or base.get("state_version") != STATE_MODEL_VERSION:
        return _projection_result("unsupported_state_version", base, None)
    session = base.get("session_id")
    if not isinstance(session, str) or not session or (expected_session_id is not None and session != expected_session_id):
        return _projection_result("invalid_base_state", base, None)
    if not isinstance(plan, dict) or plan.get("session_id") != session:
        return _projection_result("invalid_replay_plan", base, plan)
    if plan.get("status") != "planned" or plan.get("conflicts"):
        return _projection_result("blocked_by_semantic_conflict" if plan.get("conflicts") else "invalid_replay_plan", base, plan)
    steps = plan.get("ordered_steps")
    if steps is None or not isinstance(steps, list):
        return _projection_result("invalid_replay_plan", base, plan)
    if not steps:
        return _projection_result("no_reducer_steps", base, plan)
    normalized, error = _normalize_steps(steps, plan)
    if error:
        return _projection_result("invalid_replay_plan", base, plan, rejected=_step_ids(steps), conflicts=[{"reason": error}])
    same_sequence = _same_sequence_conflicts(normalized)
    if same_sequence:
        return _projection_result("blocked_by_semantic_conflict", base, plan, rejected=_step_ids(steps), conflicts=same_sequence)
    projected = deepcopy(base)
    applied = []
    for item in normalized:
        conflict = _apply(projected, item)
        if conflict:
            return _projection_result("blocked_by_semantic_conflict", base, plan, rejected=_step_ids(steps), conflicts=[conflict])
        applied.append(item["observation_id"])
    sequences = [item["observation_sequence"] for item in normalized]
    projected["last_applied_observation_sequence"] = max(sequences)
    return {"status": "ready_with_projected_state", "base_state": deepcopy(base), "projected_state": deepcopy(projected), "applied_step_ids": applied, "rejected_step_ids": [], "conflicts": [], "limitations": ["dry_run_only", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "no_q12_or_modifier_application", "provider_budget_0"]}


def _normalize_steps(steps, plan):
    events = {e.get("observation_id"): e for e in plan.get("accepted_events", []) if isinstance(e, dict) and isinstance(e.get("observation_id"), str)}
    result, seen, previous = [], set(), None
    for raw in steps:
        if not isinstance(raw, dict): return [], "invalid_step"
        oid, seq, effect = raw.get("observation_id"), raw.get("observation_sequence"), raw.get("planned_effect")
        if not isinstance(oid, str) or not oid or oid in seen or not isinstance(seq, int) or isinstance(seq, bool) or seq < 1 or effect not in _TARGETS:
            return [], "invalid_step_identity_or_effect"
        if previous is not None and (seq, oid) < previous: return [], "invalid_step_order"
        previous, seen = (seq, oid), seen | {oid}
        event = deepcopy(events.get(oid, {})); event.update(deepcopy(raw))
        event["observation_id"], event["observation_sequence"], event["planned_effect"] = oid, seq, effect
        if not _has_target_identity(event): return [], "missing_required_target_identity"
        result.append(event)
    return result, None


def _value(event, name):
    if name in event: return event[name]
    payload = event.get("payload")
    return payload.get(name) if isinstance(payload, dict) else None


def _has_target_identity(event):
    effect = event["planned_effect"]
    if effect in {"apply_exact_hp_transition", "set_condition", "clear_condition", "consume_item", "remove_item", "mark_fainted"}:
        return isinstance(_value(event, "side"), str) and isinstance(_value(event, "slot_index"), int) and not isinstance(_value(event, "slot_index"), bool) and isinstance(_value(event, "pokemon_id"), str) and bool(_value(event, "pokemon_id"))
    if effect == "switch_active":
        return isinstance(_value(event, "side"), str) and all(_value(event, key) is not None for key in ("switch_out_slot_index", "switch_out_pokemon_id", "switch_in_slot_index", "switch_in_pokemon_id"))
    if effect in {"start_weather", "end_weather"}: return isinstance(_value(event, "weather"), str) and bool(_value(event, "weather"))
    if effect in {"start_terrain", "end_terrain"}: return isinstance(_value(event, "terrain"), str) and bool(_value(event, "terrain"))
    return isinstance(_value(event, "side"), str) and isinstance(_value(event, "side_condition") or _value(event, "effect"), str)


def _side(state, side):
    if side not in {"self", "opponent"}: return None
    value = state.get(f"{side}_side")
    return value if isinstance(value, dict) else None


def _pokemon(state, event):
    side = _side(state, _value(event, "side")); slot, pid = _value(event, "slot_index"), _value(event, "pokemon_id")
    if side is None or not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pid, str) or not pid: return None
    roster = side.get("pokemon")
    if not isinstance(roster, dict): return None
    pokemon = roster.get(slot, roster.get(str(slot)))
    if not isinstance(pokemon, dict) or pokemon.get("pokemon_id", pokemon.get("name_en")) != pid: return None
    return pokemon


def _provenance(event):
    return {key: deepcopy(_value(event, key)) for key in ("source_observation_id", "source_sequence", "trust") if _value(event, key) is not None} | {"source_observation_id": event["observation_id"], "source_sequence": event["observation_sequence"]}


def _mark(container, field, event):
    container[f"{field}_provenance"] = _provenance(event)


def _apply(state, event):
    effect = event["planned_effect"]
    if effect == "apply_exact_hp_transition":
        pokemon = _pokemon(state, event); before, after = _value(event, "hp_before"), _value(event, "hp_after")
        if pokemon is None or not _exact(before) or not _exact(after) or before < after: return _conflict(event, "invalid_exact_hp_transition")
        current, maximum = pokemon.get("current_hp", "unknown"), pokemon.get("max_hp", "unknown")
        if current not in (None, "unknown") and current != before: return _conflict(event, "current_hp_mismatch")
        if _exact(maximum) and after > maximum: return _conflict(event, "hp_after_exceeds_max")
        pokemon["current_hp"] = after; _mark(pokemon, "current_hp", event); return None
    if effect == "switch_active": return _switch(state, event)
    if effect == "mark_fainted":
        pokemon = _pokemon(state, event)
        if pokemon is None: return _conflict(event, "missing_faint_target")
        if pokemon.get("fainted") is True: return _conflict(event, "already_fainted")
        pokemon["fainted"] = True; _mark(pokemon, "fainted", event); return None
    if effect in {"set_condition", "clear_condition", "consume_item", "remove_item"}: return _pokemon_effect(state, event)
    if effect in {"start_weather", "end_weather", "start_terrain", "end_terrain"}: return _field_effect(state, event)
    if effect in {"start_side_condition", "end_side_condition"}: return _side_condition(state, event)
    return _conflict(event, "unsupported_effect")


def _pokemon_effect(state, event):
    pokemon = _pokemon(state, event); effect = event["planned_effect"]
    if pokemon is None: return _conflict(event, "missing_pokemon_target")
    field, expected = ("condition", _value(event, "condition")) if "condition" in effect else ("known_item", _value(event, "item"))
    current = pokemon.get(field, "unknown")
    if not isinstance(expected, str) or not expected: return _conflict(event, "missing_effect_identity")
    if effect in {"set_condition", "consume_item", "remove_item"}:
        if current == expected and effect == "set_condition": return None
        if current in (None, "unknown") and effect == "set_condition": pokemon[field] = expected; _mark(pokemon, field, event); return None
        if effect != "set_condition" and current == expected: pokemon[field] = None; _mark(pokemon, field, event); return None
        return _conflict(event, "known_value_mismatch_or_unknown")
    if current == expected: pokemon[field] = None; _mark(pokemon, field, event); return None
    return _conflict(event, "condition_clear_requires_exact_known_match")


def _field_effect(state, event):
    field = "weather" if "weather" in event["planned_effect"] else "terrain"; desired = _value(event, field); current_field = state.get("field")
    if not isinstance(current_field, dict) or not isinstance(desired, str) or not desired: return _conflict(event, "missing_field_effect_identity")
    current, start = current_field.get(field, "unknown"), event["planned_effect"].startswith("start_")
    if start and current == desired: return None
    if start and current in (None, "unknown"): current_field[field] = desired; _mark(current_field, field, event); return None
    if not start and current == desired: current_field[field] = None; _mark(current_field, field, event); return None
    return _conflict(event, "field_effect_requires_compatible_known_state")


def _side_condition(state, event):
    side = _side(state, _value(event, "side")); effect = _value(event, "side_condition") or _value(event, "effect")
    if side is None or not isinstance(effect, str) or not effect: return _conflict(event, "missing_side_condition_identity")
    conditions = side.get("side_conditions")
    if not isinstance(conditions, list): return _conflict(event, "unsupported_side_condition_state")
    start = event["planned_effect"] == "start_side_condition"
    if start and effect in conditions: return None
    if start: conditions.append(effect); _mark(side, "side_conditions", event); return None
    if not start and effect in conditions: conditions.remove(effect); _mark(side, "side_conditions", event); return None
    return _conflict(event, "side_condition_missing_or_unknown")


def _switch(state, event):
    side = _side(state, _value(event, "side")); out_slot, out_id = _value(event, "switch_out_slot_index"), _value(event, "switch_out_pokemon_id"); in_slot, in_id = _value(event, "switch_in_slot_index"), _value(event, "switch_in_pokemon_id")
    if side is None or not all(isinstance(v, int) and not isinstance(v, bool) for v in (out_slot, in_slot)) or not all(isinstance(v, str) and v for v in (out_id, in_id)) or (out_slot, out_id) == (in_slot, in_id): return _conflict(event, "invalid_switch_identity")
    active = side.get("active_slot_index")
    if active in (None, "unknown") or active != out_slot: return _conflict(event, "switch_out_not_projected_active")
    roster = side.get("pokemon", {}); incoming = roster.get(in_slot, roster.get(str(in_slot))) if isinstance(roster, dict) else None
    if not isinstance(incoming, dict) or incoming.get("pokemon_id", incoming.get("name_en")) != in_id: return _conflict(event, "missing_switch_in_target")
    if incoming.get("fainted") is True: return _conflict(event, "switch_in_fainted")
    side["active_slot_index"] = in_slot; _mark(side, "active_slot_index", event); return None


def _same_sequence_conflicts(steps):
    groups = {}
    for item in steps: groups.setdefault(item["observation_sequence"], []).append(item)
    conflicts = []
    for sequence, group in groups.items():
        if len(group) < 2: continue
        keys = {}
        for item in group:
            key = _semantic_key(item)
            if key in keys and not _explicitly_related(item, keys[key]): conflicts.append({"reason": "same_sequence_dependency_ambiguous", "observation_sequence": sequence, "observation_ids": [keys[key]["observation_id"], item["observation_id"]]})
            keys[key] = item
        switches = [x for x in group if x["planned_effect"] == "switch_active"]
        faints = [x for x in group if x["planned_effect"] == "mark_fainted"]
        for switch in switches:
            for faint in faints:
                if _value(switch, "side") == _value(faint, "side") and not _explicitly_related(switch, faint): conflicts.append({"reason": "same_sequence_switch_faint_dependency", "observation_sequence": sequence, "observation_ids": [switch["observation_id"], faint["observation_id"]]})
    return conflicts


def _semantic_key(event):
    effect = event["planned_effect"]
    if effect in {"start_weather", "end_weather"}: return ("field", "weather")
    if effect in {"start_terrain", "end_terrain"}: return ("field", "terrain")
    if effect in {"start_side_condition", "end_side_condition"}: return ("side", _value(event, "side"), _value(event, "side_condition") or _value(event, "effect"))
    if effect == "switch_active": return ("active", _value(event, "side"))
    return ("pokemon", _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id"), _TARGETS[effect])


def _explicitly_related(left, right):
    return left.get("depends_on_observation_id") == right["observation_id"] or right.get("depends_on_observation_id") == left["observation_id"]


def _exact(value): return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _conflict(event, reason): return {"observation_id": event["observation_id"], "reason": reason}
def _step_ids(steps): return [x.get("observation_id") for x in steps if isinstance(x, dict)]
def _projection_result(status, base, plan, rejected=None, conflicts=None): return {"status": status, "base_state": deepcopy(base) if isinstance(base, dict) else None, "projected_state": None, "applied_step_ids": [], "rejected_step_ids": rejected or [], "conflicts": deepcopy(conflicts or []), "limitations": ["dry_run_only", "no_runtime_state_mutation", "provider_budget_0"]}
def _legacy_result(status, base, plan): return {"status": status, "base_state": base, "planned_next_state_schema": [], "accepted_step_ids": [], "rejected_step_ids": [x.get("observation_id") for x in plan.get("ordered_steps", []) if isinstance(x, dict)], "conflicts": deepcopy(plan.get("conflicts", [])), "limitations": ["dry_run_only", "no_state_mutation"]}
