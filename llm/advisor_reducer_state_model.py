"""Pure validation and dry-run projection for the private battle-state-v1 model."""
from copy import deepcopy
from hashlib import sha256
import json
from types import MappingProxyType
from llm.advisor_identity_groundedness import build_groundedness, normalize_groundedness

STATE_MODEL_VERSION = "battle-state-v1"
UNKNOWN_BATTLE_FACT = MappingProxyType({"knowledge": "unknown"})
_TARGETS = {"apply_exact_hp_transition": "pokemon.current_hp", "set_condition": "pokemon.condition", "clear_condition": "pokemon.condition", "consume_item": "pokemon.known_item", "remove_item": "pokemon.known_item", "start_weather": "field.weather", "end_weather": "field.weather", "start_terrain": "field.terrain", "end_terrain": "field.terrain", "start_side_condition": "side.side_conditions", "end_side_condition": "side.side_conditions", "switch_active": "side.active_slot_index", "mark_fainted": "pokemon.fainted", "record_known_move": "pokemon.known_move_ids", "set_switch_permission": "side.switch_permission_context", "clear_switch_permission": "side.switch_permission_context", "set_ability_applicability": "state.ability_applicability_context", "clear_ability_applicability": "state.ability_applicability_context", "set_ability_interaction": "state.ability_interaction_context", "clear_ability_interaction": "state.ability_interaction_context", "set_identity_groundedness": "state.identity_groundedness_context", "clear_identity_groundedness": "state.identity_groundedness_context"}


def make_unknown_battle_fact():
    """Return the detached canonical marker for an unconfirmed battle fact."""
    return {"knowledge": "unknown"}


def is_unknown_battle_fact(value):
    return isinstance(value, dict) and value == UNKNOWN_BATTLE_FACT


def validate_battle_state_unknown_markers(state):
    """Reject malformed canonical markers while preserving legacy concrete states."""
    if not isinstance(state, dict):
        return False
    for side_name in ("self_side", "opponent_side"):
        side = state.get(side_name)
        if not isinstance(side, dict):
            return False
        if not _valid_fact_marker(side.get("side_conditions")):
            return False
        roster = side.get("pokemon")
        if not isinstance(roster, dict):
            return False
        if side_name == "self_side" and "switch_permission_context" in side and not _valid_switch_permission_context(state, side["switch_permission_context"]):
            return False
        if any(_contains_marker(value) for key, value in side.items() if key not in {"pokemon", "side_conditions", "switch_permission_context"}):
            return False
        for pokemon in roster.values():
            if not isinstance(pokemon, dict):
                return False
            if any(not _valid_fact_marker(pokemon.get(field)) for field in ("current_hp", "max_hp", "fainted", "condition", "known_item")):
                return False
            known_moves = pokemon.get("known_move_ids", [])
            if not isinstance(known_moves, list) or len(known_moves) > 4 or any(not _canonical_move_id(move) for move in known_moves) or len(set(known_moves)) != len(known_moves):
                return False
            if any(_contains_marker(value) for key, value in pokemon.items() if key not in {"current_hp", "max_hp", "fainted", "condition", "known_item"}):
                return False
    field = state.get("field")
    if not isinstance(field, dict) or not all(_valid_fact_marker(field.get(name)) for name in ("weather", "terrain")):
        return False
    if any(_contains_marker(value) for key, value in field.items() if key not in {"weather", "terrain"}):
        return False
    return not any(_contains_marker(value) for key, value in state.items() if key not in {"self_side", "opponent_side", "field"})


def _valid_fact_marker(value):
    return not (isinstance(value, dict) and "knowledge" in value) or is_unknown_battle_fact(value)


def _contains_marker(value):
    if isinstance(value, dict):
        return "knowledge" in value or any(_contains_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_marker(item) for item in value)
    return False


def _unknown(value):
    """Accept legacy string unknown while new bootstrap state uses the marker."""
    return value == "unknown" or is_unknown_battle_fact(value)


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
        if item["planned_effect"] != "set_switch_permission":
            _invalidate_switch_permission(projected)
        if item["planned_effect"] not in {"set_ability_applicability", "set_ability_interaction"}:
            _invalidate_ability_interaction_authorities(projected)
        if item["planned_effect"] not in {"set_identity_groundedness", "clear_identity_groundedness"}:
            context=projected.get("identity_groundedness_context")
            if isinstance(context, dict):
                projected["identity_groundedness_context"]=normalize_groundedness(None,session_id=projected["session_id"],side=context.get("side"),slot_index=context.get("slot_index"),pokemon_id=context.get("pokemon_id"))
        applied.append(item["observation_id"])
    sequences = [item["observation_sequence"] for item in normalized]
    projected["last_applied_observation_sequence"] = max(sequences)
    return {"status": "ready_with_projected_state", "base_state": deepcopy(base), "projected_state": deepcopy(projected), "applied_step_ids": applied, "rejected_step_ids": [], "conflicts": [], "limitations": ["dry_run_only", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "no_q12_or_modifier_application", "provider_budget_0"]}


def state_fingerprint(state):
    """Stable private digest of battle-state semantics; never a public schema field."""
    if not isinstance(state, dict): return None
    return sha256(_canonical_json(_fingerprint_state(state)).encode("utf-8")).hexdigest()


def replay_batch_fingerprint(replay_plan):
    """Stable identity for a replay occurrence, independent of runtime object identity."""
    if not isinstance(replay_plan, dict): return None
    steps = replay_plan.get("ordered_steps")
    if not isinstance(steps, list): return None
    batch = {"session_id": replay_plan.get("session_id"), "replay_policy_version": replay_plan.get("replay_policy_version"), "ordered_steps": deepcopy(steps)}
    return sha256(_canonical_json(batch).encode("utf-8")).hexdigest()


def execute_atomic_transition(base_state, replay_plan, *, expected_session_id=None, expected_state_version=STATE_MODEL_VERSION, expected_base_fingerprint=None):
    """Pure optimistic-concurrency executor built on the canonical v15.22 projection."""
    base = deepcopy(base_state) if isinstance(base_state, dict) else None
    plan = deepcopy(replay_plan) if isinstance(replay_plan, dict) else None
    if expected_state_version != STATE_MODEL_VERSION or not isinstance(base, dict) or base.get("state_version") != STATE_MODEL_VERSION:
        return _execution_result("unsupported_state_version", None, None, None, plan)
    session = base.get("session_id")
    if not isinstance(session, str) or not session:
        return _execution_result("invalid_base_state", None, None, None, plan)
    if expected_session_id is not None and session != expected_session_id:
        return _execution_result("session_mismatch", None, None, None, plan)
    if not isinstance(plan, dict): return _execution_result("invalid_replay_plan", None, None, None, plan)
    if plan.get("session_id") != session: return _execution_result("session_mismatch", None, None, None, plan)
    base_digest, batch_digest = state_fingerprint(base), replay_batch_fingerprint(plan)
    if expected_base_fingerprint is not None and expected_base_fingerprint != base_digest:
        return _execution_result("stale_base_state", base_digest, None, batch_digest, plan)
    steps = plan.get("ordered_steps")
    if not isinstance(steps, list): return _execution_result("invalid_replay_plan", base_digest, None, batch_digest, plan)
    if not steps: return _execution_result("no_reducer_steps", base_digest, None, batch_digest, plan)
    sequences = [item.get("observation_sequence") for item in steps if isinstance(item, dict)]
    if len(sequences) != len(steps) or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in sequences):
        return _execution_result("invalid_replay_plan", base_digest, None, batch_digest, plan)
    last = base.get("last_applied_observation_sequence")
    if isinstance(last, int) and not isinstance(last, bool):
        if all(sequence <= last for sequence in sequences):
            status = "already_applied" if base.get("last_applied_batch_fingerprint") == batch_digest else "blocked_by_semantic_conflict"
            conflict = [] if status == "already_applied" else [{"reason": "duplicate_or_overlapping_batch"}]
            return _execution_result(status, base_digest, None, batch_digest, plan, conflicts=conflict)
        if any(sequence <= last for sequence in sequences):
            return _execution_result("blocked_by_semantic_conflict", base_digest, None, batch_digest, plan, conflicts=[{"reason": "partial_sequence_overlap"}])
    projection = project_atomic_transition(base, plan, expected_session_id=session, state_model_version=expected_state_version)
    if projection["status"] != "ready_with_projected_state":
        return _execution_result(projection["status"], base_digest, None, batch_digest, plan, rejected=projection.get("rejected_step_ids"), conflicts=projection.get("conflicts"))
    committed = deepcopy(projection["projected_state"])
    committed["last_applied_batch_fingerprint"] = batch_digest
    committed["source_replay_policy_version"] = plan.get("replay_policy_version")
    committed["last_commit_provenance"] = {"base_state_fingerprint": base_digest, "replay_batch_fingerprint": batch_digest, "applied_step_ids": deepcopy(projection["applied_step_ids"])}
    committed_digest = state_fingerprint(committed)
    return {"status": "committed", "committed_state": deepcopy(committed), "base_state_fingerprint": base_digest, "committed_state_fingerprint": committed_digest, "replay_batch_fingerprint": batch_digest, "applied_step_ids": deepcopy(projection["applied_step_ids"]), "rejected_step_ids": [], "conflicts": [], "limitations": ["pure_detached_execution", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "no_q12_or_modifier_application", "provider_budget_0"]}


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
    if effect in {"apply_exact_hp_transition", "set_condition", "clear_condition", "consume_item", "remove_item", "mark_fainted", "record_known_move"}:
        return isinstance(_value(event, "side"), str) and isinstance(_value(event, "slot_index"), int) and not isinstance(_value(event, "slot_index"), bool) and isinstance(_value(event, "pokemon_id"), str) and bool(_value(event, "pokemon_id"))
    if effect == "switch_active":
        return isinstance(_value(event, "side"), str) and all(_value(event, key) is not None for key in ("switch_out_slot_index", "switch_out_pokemon_id", "switch_in_slot_index", "switch_in_pokemon_id"))
    if effect in {"set_switch_permission", "clear_switch_permission"}:
        return _value(event, "side") == "self" and isinstance(_value(event, "slot_index"), int) and not isinstance(_value(event, "slot_index"), bool) and isinstance(_value(event, "pokemon_id"), str) and bool(_value(event, "pokemon_id"))
    if effect in {"set_ability_applicability", "clear_ability_applicability"}:
        return _identity_values(event, "side", "slot_index", "pokemon_id") and isinstance(_value(event, "ability_id"), str) and bool(_value(event, "ability_id"))
    if effect in {"set_ability_interaction", "clear_ability_interaction"}:
        return _identity_values(event, "source_side", "source_slot_index", "source_pokemon_id") and _identity_values(event, "target_side", "target_slot_index", "target_pokemon_id")
    if effect in {"set_identity_groundedness", "clear_identity_groundedness"}: return _identity_values(event,"side","slot_index","pokemon_id")
    if effect in {"start_weather", "end_weather"}: return isinstance(_value(event, "weather"), str) and bool(_value(event, "weather"))
    if effect in {"start_terrain", "end_terrain"}: return isinstance(_value(event, "terrain"), str) and bool(_value(event, "terrain"))
    return isinstance(_value(event, "side"), str) and isinstance(_value(event, "side_condition") or _value(event, "effect"), str)


def _side(state, side):
    if side not in {"self", "opponent"}: return None
    value = state.get(f"{side}_side")
    return value if isinstance(value, dict) else None


def _identity_values(event, side_key, slot_key, pokemon_key):
    return _value(event, side_key) in {"self", "opponent"} and isinstance(_value(event, slot_key), int) and not isinstance(_value(event, slot_key), bool) and isinstance(_value(event, pokemon_key), str) and bool(_value(event, pokemon_key))


def _active_identity_matches(state, side_name, slot, pokemon_id):
    side = _side(state, side_name)
    roster = side.get("pokemon") if isinstance(side, dict) else None
    active = side.get("active_slot_index") if isinstance(side, dict) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
    return active == slot and isinstance(pokemon, dict) and pokemon.get("pokemon_id", pokemon.get("name_en")) == pokemon_id


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
        if current is not None and not _unknown(current) and current != before: return _conflict(event, "current_hp_mismatch")
        if not _unknown(maximum) and _exact(maximum) and after > maximum: return _conflict(event, "hp_after_exceeds_max")
        pokemon["current_hp"] = after; _mark(pokemon, "current_hp", event); return None
    if effect == "switch_active": return _switch(state, event)
    if effect == "set_switch_permission": return _set_switch_permission(state, event)
    if effect == "clear_switch_permission": return _clear_switch_permission(state, event)
    if effect == "set_ability_applicability": return _set_ability_applicability(state, event)
    if effect == "clear_ability_applicability": return _clear_ability_applicability(state, event)
    if effect == "set_ability_interaction": return _set_ability_interaction(state, event)
    if effect == "clear_ability_interaction": return _clear_ability_interaction(state, event)
    if effect in {"set_identity_groundedness","clear_identity_groundedness"}:
        side,slot,pid=_value(event,"side"),_value(event,"slot_index"),_value(event,"pokemon_id")
        if not _active_identity_matches(state,side,slot,pid): return _conflict(event,"invalid_identity_groundedness")
        status="unknown" if effect.startswith("clear") else _value(event,"groundedness_status")
        try: state["identity_groundedness_context"]=build_groundedness(session_id=state["session_id"],side=side,slot_index=slot,pokemon_id=pid,status=status)
        except ValueError: return _conflict(event,"invalid_identity_groundedness")
        return None
    if effect == "mark_fainted":
        pokemon = _pokemon(state, event)
        if pokemon is None: return _conflict(event, "missing_faint_target")
        if pokemon.get("fainted") is True: return _conflict(event, "already_fainted")
        pokemon["fainted"] = True; _mark(pokemon, "fainted", event); return None
    if effect == "record_known_move":
        pokemon = _pokemon(state, event); move_id = _value(event, "canonical_move_id")
        if pokemon is None or not _canonical_move_id(move_id): return _conflict(event, "invalid_canonical_move_id")
        known_moves = pokemon.get("known_move_ids", [])
        if not isinstance(known_moves, list) or len(set(known_moves)) != len(known_moves) or any(not _canonical_move_id(move) for move in known_moves):
            return _conflict(event, "invalid_known_move_state")
        if move_id in known_moves: return None
        if len(known_moves) >= 4: return _conflict(event, "known_move_capacity_exceeded")
        pokemon["known_move_ids"] = [*known_moves, move_id]; _mark(pokemon, "known_move_ids", event); return None
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
        if (current is None or _unknown(current)) and effect == "set_condition": pokemon[field] = expected; _mark(pokemon, field, event); return None
        if effect != "set_condition" and current == expected: pokemon[field] = None; _mark(pokemon, field, event); return None
        return _conflict(event, "known_value_mismatch_or_unknown")
    if current == expected: pokemon[field] = None; _mark(pokemon, field, event); return None
    return _conflict(event, "condition_clear_requires_exact_known_match")


def _field_effect(state, event):
    field = "weather" if "weather" in event["planned_effect"] else "terrain"; desired = _value(event, field); current_field = state.get("field")
    if not isinstance(current_field, dict) or not isinstance(desired, str) or not desired: return _conflict(event, "missing_field_effect_identity")
    current, start = current_field.get(field, "unknown"), event["planned_effect"].startswith("start_")
    if start and current == desired: return None
    if start and (current is None or _unknown(current)): current_field[field] = desired; _mark(current_field, field, event); return None
    if not start and current == desired: current_field[field] = None; _mark(current_field, field, event); return None
    return _conflict(event, "field_effect_requires_compatible_known_state")


def _side_condition(state, event):
    side = _side(state, _value(event, "side")); effect = _value(event, "side_condition") or _value(event, "effect")
    if side is None or not isinstance(effect, str) or not effect: return _conflict(event, "missing_side_condition_identity")
    conditions = side.get("side_conditions")
    if is_unknown_battle_fact(conditions): return _conflict(event, "side_condition_set_unknown")
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


def _set_switch_permission(state, event):
    side = _side(state, "self")
    pokemon = _pokemon(state, event)
    status = _value(event, "permission_status")
    if side is None or pokemon is None or side.get("active_slot_index") != _value(event, "slot_index"):
        return _conflict(event, "switch_permission_owner_mismatch")
    if status not in {"permitted", "blocked"} or _value(event, "source") != "user_confirmed_current_switch_permission" or _value(event, "trust") != "user_confirmed_current":
        return _conflict(event, "invalid_switch_permission_authority")
    reason = _value(event, "block_reason")
    if status == "permitted" and reason is not None:
        return _conflict(event, "invalid_switch_permission_reason")
    if status == "blocked" and reason not in (None, "trapped", "switch_lock", "other_confirmed_block"):
        return _conflict(event, "invalid_switch_permission_reason")
    context = {"schema_version": "switch-permission-context-v1", "session_id": state.get("session_id"), "side": "self", "active_slot_index": _value(event, "slot_index"), "active_pokemon_id": _value(event, "pokemon_id"), "status": status, "supportability": "complete", "source": "user_confirmed_current_switch_permission", "trust": "user_confirmed_current"}
    if reason is not None: context["block_reason"] = reason
    side["switch_permission_context"] = context
    return None


def _clear_switch_permission(state, event):
    side = _side(state, "self"); pokemon = _pokemon(state, event)
    if side is None or pokemon is None or side.get("active_slot_index") != _value(event, "slot_index") or _value(event, "source") != "user_confirmed_current_switch_permission" or _value(event, "trust") != "user_confirmed_current":
        return _conflict(event, "invalid_switch_permission_authority")
    _invalidate_switch_permission(state)
    return None


def _invalidate_switch_permission(state):
    side = _side(state, "self")
    roster = side.get("pokemon") if isinstance(side, dict) else None
    slot = side.get("active_slot_index") if isinstance(side, dict) else None
    active = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
    pokemon_id = active.get("pokemon_id", active.get("name_en")) if isinstance(active, dict) else None
    if isinstance(side, dict) and isinstance(slot, int) and not isinstance(slot, bool) and isinstance(pokemon_id, str) and pokemon_id:
        side["switch_permission_context"] = {"schema_version": "switch-permission-context-v1", "session_id": state.get("session_id"), "side": "self", "active_slot_index": slot, "active_pokemon_id": pokemon_id, "status": "unknown", "supportability": "insufficient_context"}


def _set_ability_applicability(state, event):
    side, slot, pokemon_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
    status, ability_id = _value(event, "applicability_status"), _value(event, "ability_id")
    if not _active_identity_matches(state, side, slot, pokemon_id) or status not in {"applicable", "not_applicable"}:
        return _conflict(event, "invalid_ability_applicability_authority")
    state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state.get("session_id"), "source": {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "ability_id": ability_id, "status": status}
    return None


def _clear_ability_applicability(state, event):
    side, slot, pokemon_id, ability_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id"), _value(event, "ability_id")
    if not _active_identity_matches(state, side, slot, pokemon_id):
        return _conflict(event, "invalid_ability_applicability_authority")
    state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state.get("session_id"), "source": {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "ability_id": ability_id, "status": "unknown"}
    return None


def _set_ability_interaction(state, event):
    source = (_value(event, "source_side"), _value(event, "source_slot_index"), _value(event, "source_pokemon_id"))
    target = (_value(event, "target_side"), _value(event, "target_slot_index"), _value(event, "target_pokemon_id"))
    status = _value(event, "interaction_status")
    if source[0] == target[0] or not _active_identity_matches(state, *source) or not _active_identity_matches(state, *target) or status not in {"affecting", "not_affecting"}:
        return _conflict(event, "invalid_ability_interaction_authority")
    state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state.get("session_id"), "source": {"side": source[0], "slot_index": source[1], "pokemon_id": source[2]}, "target": {"side": target[0], "slot_index": target[1], "pokemon_id": target[2]}, "status": status}
    return None


def _clear_ability_interaction(state, event):
    source = (_value(event, "source_side"), _value(event, "source_slot_index"), _value(event, "source_pokemon_id"))
    target = (_value(event, "target_side"), _value(event, "target_slot_index"), _value(event, "target_pokemon_id"))
    if source[0] == target[0] or not _active_identity_matches(state, *source) or not _active_identity_matches(state, *target):
        return _conflict(event, "invalid_ability_interaction_authority")
    state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state.get("session_id"), "source": {"side": source[0], "slot_index": source[1], "pokemon_id": source[2]}, "target": {"side": target[0], "slot_index": target[1], "pokemon_id": target[2]}, "status": "unknown"}
    return None


def _invalidate_ability_interaction_authorities(state):
    """Conservatively drop positive authority when any unrelated state changes."""
    applicability = state.get("ability_applicability_context")
    if isinstance(applicability, dict):
        source, ability_id = applicability.get("source"), applicability.get("ability_id")
        if isinstance(source, dict) and isinstance(ability_id, str) and ability_id:
            state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state.get("session_id"), "source": deepcopy(source), "ability_id": ability_id, "status": "unknown"}
    interaction = state.get("ability_interaction_context")
    if isinstance(interaction, dict):
        source, target = interaction.get("source"), interaction.get("target")
        if isinstance(source, dict) and isinstance(target, dict):
            state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state.get("session_id"), "source": deepcopy(source), "target": deepcopy(target), "status": "unknown"}


def _valid_switch_permission_context(state, value):
    if not isinstance(value, dict): return False
    side = state.get("self_side", {}); roster = side.get("pokemon", {}) if isinstance(side, dict) else {}
    slot = side.get("active_slot_index") if isinstance(side, dict) else None
    active = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
    pid = active.get("pokemon_id", active.get("name_en")) if isinstance(active, dict) else None
    common = {"schema_version": "switch-permission-context-v1", "session_id": state.get("session_id"), "side": "self", "active_slot_index": slot, "active_pokemon_id": pid}
    if any(value.get(key) != expected for key, expected in common.items()): return False
    if value.get("status") == "unknown": return set(value) == {*common, "status", "supportability"} and value.get("supportability") == "insufficient_context"
    return value.get("status") in {"permitted", "blocked"} and value.get("supportability") == "complete" and value.get("source") == "user_confirmed_current_switch_permission" and value.get("trust") == "user_confirmed_current" and set(value) <= {*common, "status", "supportability", "source", "trust", "block_reason"}


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


def _fingerprint_state(state):
    """Exclude executor receipts so a committed replay remains identifiable."""
    excluded = {"last_applied_batch_fingerprint", "source_replay_policy_version", "last_commit_provenance"}
    return {key: _fingerprint_state(value) if isinstance(value, dict) else [_fingerprint_state(item) if isinstance(item, dict) else item for item in value] if isinstance(value, list) else value for key, value in state.items() if key not in excluded}


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=lambda item: {"__type__": type(item).__name__, "value": str(item)})


def _exact(value): return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _canonical_move_id(value): return isinstance(value, str) and bool(value) and value == value.strip() and value == value.lower() and " " not in value and "_" not in value
def _conflict(event, reason): return {"observation_id": event["observation_id"], "reason": reason}
def _step_ids(steps): return [x.get("observation_id") for x in steps if isinstance(x, dict)]
def _projection_result(status, base, plan, rejected=None, conflicts=None): return {"status": status, "base_state": deepcopy(base) if isinstance(base, dict) else None, "projected_state": None, "applied_step_ids": [], "rejected_step_ids": rejected or [], "conflicts": deepcopy(conflicts or []), "limitations": ["dry_run_only", "no_runtime_state_mutation", "provider_budget_0"]}
def _execution_result(status, base_digest, committed_digest, batch_digest, plan, rejected=None, conflicts=None): return {"status": status, "committed_state": None, "base_state_fingerprint": base_digest, "committed_state_fingerprint": committed_digest, "replay_batch_fingerprint": batch_digest, "applied_step_ids": [], "rejected_step_ids": deepcopy(rejected if rejected is not None else _step_ids(plan.get("ordered_steps", []) if isinstance(plan, dict) else [])), "conflicts": deepcopy(conflicts or []), "limitations": ["pure_detached_execution", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "provider_budget_0"]}
def _legacy_result(status, base, plan): return {"status": status, "base_state": base, "planned_next_state_schema": [], "accepted_step_ids": [], "rejected_step_ids": [x.get("observation_id") for x in plan.get("ordered_steps", []) if isinstance(x, dict)], "conflicts": deepcopy(plan.get("conflicts", [])), "limitations": ["dry_run_only", "no_state_mutation"]}
