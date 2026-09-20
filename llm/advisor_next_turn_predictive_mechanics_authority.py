"""Detached predictive mechanics transport across the exact turn boundary.

This module authenticates optional terminal mechanics authority, carries it
through EOT/replacement as detached predictive state, and materializes a
next-turn sidecar authority.  It never creates runtime/reducer observations and
never evaluates move execution, hit, critical hit, damage, secondary effects,
or action order.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_substitute import update_substitute_state_context
from llm.advisor_transition_preview import fingerprint_transition_preview_state


TERMINAL_SCHEMA_VERSION = "detached-exact-pair-terminal-predictive-mechanics-authority-v1"
POST_EOT_SCHEMA_VERSION = "detached-post-eot-predictive-mechanics-authority-v1"
NEXT_TURN_SCHEMA_VERSION = "detached-next-turn-predictive-mechanics-authority-v1"
FORCED_BINDING_SCHEMA_VERSION = "detached-forced-action-predictive-mechanics-binding-v1"

_SIDES = ("self", "opponent")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_FINAL_STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
_STAGE_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")
_DIRECT_BOOST_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed")
_CONDITIONS = {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
_KNOWN_STATUS = {"known", "known_absent", "unknown"}


def normalize_terminal_predictive_mechanics_authority(
    *,
    value: Any,
    base: Mapping[str, Any],
    terminal_leaf: Mapping[str, Any],
    owner: Mapping[str, Any],
    resolved_active: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate one optional terminal predictive-mechanics record.

    Caller-owned HP never overwrites the pair result.  Known HP/condition/item
    claims must agree with the already-resolved terminal row. Unknown mechanics
    remain unknown and make this authority incomplete rather than neutral.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return _rejected("terminal_predictive_mechanics_shape_invalid")
    if value.get("schema_version") != TERMINAL_SCHEMA_VERSION:
        return _rejected("terminal_predictive_mechanics_schema_invalid")
    side = owner.get("side")
    if side not in _SIDES or value.get("owner") != dict(owner):
        return _rejected("terminal_predictive_mechanics_owner_mismatch")
    binding = value.get("source_binding")
    expected_binding = {
        "pair_id": base.get("pair_id"),
        "terminal_leaf_id": terminal_leaf.get("pair_leaf_id"),
        "session_id": base.get("session_id"),
        "source_runtime_fingerprint": base.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": base.get("source_branch_fingerprint"),
        "decision_owner": deepcopy(base.get("decision_owner")),
        "owner": deepcopy(dict(owner)),
    }
    if binding != expected_binding:
        return _rejected("terminal_predictive_mechanics_binding_mismatch")

    hp = resolved_active.get("hp")
    condition = resolved_active.get("condition")
    item = resolved_active.get("item")
    ability = resolved_active.get("ability")
    types = resolved_active.get("types")
    if not isinstance(hp, Mapping) or hp.get("status") != "known":
        return _rejected("terminal_predictive_mechanics_terminal_hp_invalid")

    reasons: list[str] = []
    source_hp = value.get("current_hp")
    if isinstance(source_hp, Mapping) and source_hp.get("status") == "known":
        if (
            source_hp.get("current_hp") != hp.get("current_hp")
            or source_hp.get("maximum_hp") != hp.get("maximum_hp")
        ):
            return _rejected("terminal_predictive_mechanics_hp_contradiction")
    elif source_hp is not None and (
        not isinstance(source_hp, Mapping) or source_hp.get("status") != "unknown"
    ):
        return _rejected("terminal_predictive_mechanics_hp_authority_invalid")

    normalized_condition, error = _condition_fact(value.get("condition"), terminal=condition)
    if error:
        return _rejected(error)
    if normalized_condition["status"] == "unknown":
        if isinstance(condition, Mapping) and condition.get("status") == "known_none":
            normalized_condition = {"status": "known_none"}
        elif isinstance(condition, Mapping) and condition.get("status") == "known_present":
            normalized_condition = {
                "status": "known_present",
                "condition": condition.get("condition"),
            }
        else:
            reasons.append("condition_unknown")

    normalized_item, error = _item_fact(value.get("item"), terminal=item)
    if error:
        return _rejected(error)
    if normalized_item["status"] == "unknown":
        if isinstance(item, Mapping) and item.get("status") == "known_absent":
            normalized_item = {"status": "known_absent"}
        elif isinstance(item, Mapping) and item.get("status") == "known":
            normalized_item = {"status": "known", "value": item.get("value")}
        else:
            reasons.append("item_unknown")

    normalized_ability, error = _simple_identity_fact(value.get("ability"), "ability")
    if error:
        return _rejected(error)
    if (
        normalized_ability["status"] == "known"
        and isinstance(ability, Mapping)
        and ability.get("status") == "known"
        and normalized_ability["value"] != ability.get("value")
    ):
        return _rejected("terminal_predictive_mechanics_ability_contradiction")
    if normalized_ability["status"] == "unknown":
        if isinstance(ability, Mapping) and ability.get("status") == "known":
            normalized_ability = {"status": "known", "value": ability.get("value")}
        elif isinstance(ability, Mapping) and ability.get("status") == "known_absent":
            normalized_ability = {"status": "known_absent"}
        else:
            reasons.append("ability_unknown")

    normalized_types, error = _types_fact(value.get("types"))
    if error:
        return _rejected(error)
    if (
        normalized_types["status"] == "known"
        and isinstance(types, Mapping)
        and types.get("status") == "known"
        and normalized_types["value"] != types.get("value")
    ):
        return _rejected("terminal_predictive_mechanics_type_contradiction")
    if normalized_types["status"] == "unknown":
        if isinstance(types, Mapping) and types.get("status") == "known":
            normalized_types = {
                "status": "known",
                "value": deepcopy(types.get("value")),
            }
        else:
            reasons.append("types_unknown")

    level, error = _level_fact(value.get("current_level"))
    if error:
        return _rejected(error)
    if level["status"] == "unknown":
        reasons.append("level_unknown")

    final_stats, missing_stats, error = _final_stats_fact(value.get("current_final_stats"), hp["maximum_hp"])
    if error:
        return _rejected(error)
    reasons.extend(f"final_stat_{stat}_unknown" for stat in missing_stats)

    stages, missing_stages, error = _stages_fact(value.get("current_stages"))
    if error:
        return _rejected(error)
    reasons.extend(f"stage_{stat}_unknown" for stat in missing_stages)
    stage_expectations = _terminal_stage_expectations(terminal_leaf, owner)
    for stat, expected in stage_expectations.items():
        actual = stages.get("values", {}).get(stat)
        if actual is None:
            reasons.append(f"terminal_stage_{stat}_unproven")
        elif actual != expected:
            return _rejected("terminal_predictive_mechanics_stage_contradiction")

    substitute, error = _substitute_fact(value.get("substitute"))
    if error:
        return _rejected(error)
    if substitute["status"] == "unknown":
        reasons.append("substitute_unknown")

    crit, error = _crit_volatile_fact(value.get("critical_hit_volatiles"))
    if error:
        return _rejected(error)
    if crit["status"] == "unknown":
        reasons.append("critical_hit_volatiles_unknown")

    lucky, error = _known_active_fact(value.get("lucky_chant"), "lucky_chant")
    if error:
        return _rejected(error)
    if lucky["status"] == "unknown":
        reasons.append("lucky_chant_unknown")

    field, error = _field_fact(value.get("field"))
    if error:
        return _rejected(error)
    if field["status"] == "unknown":
        reasons.append("field_unknown")

    side_conditions, error = _side_conditions_fact(value.get("side_conditions"))
    if error:
        return _rejected(error)
    if side_conditions["status"] == "unknown":
        reasons.append("side_conditions_unknown")

    direct, error = _direct_fact(
        value.get("direct_mechanics"),
        hp={"current_hp": hp["current_hp"], "maximum_hp": hp["maximum_hp"]},
        condition=normalized_condition,
        item=normalized_item,
        ability=normalized_ability,
        types=normalized_types,
        final_stats=final_stats,
        stages=stages,
        level=level,
    )
    if error:
        return _rejected(error)
    if direct["status"] == "unknown":
        reasons.append("direct_mechanics_unknown")

    return {
        "status": "incomplete" if reasons else "resolved",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "source_binding": deepcopy(expected_binding),
        "owner": deepcopy(dict(owner)),
        "current_level": level,
        "current_final_stats": final_stats,
        "current_hp": {
            "status": "known",
            "current_hp": hp["current_hp"],
            "maximum_hp": hp["maximum_hp"],
            "source_terminal_leaf_id": terminal_leaf["pair_leaf_id"],
            "provenance": "exact_pair_terminal_hp",
        },
        "fainted": hp["current_hp"] == 0,
        "current_stages": stages,
        "condition": normalized_condition,
        "item": normalized_item,
        "ability": normalized_ability,
        "types": normalized_types,
        "substitute": substitute,
        "critical_hit_volatiles": crit,
        "lucky_chant": lucky,
        "field": field,
        "side_conditions": side_conditions,
        "direct_mechanics": direct,
        "incomplete_reasons": tuple(sorted(set(reasons))),
        "provenance": "authenticated_exact_pair_terminal_predictive_mechanics_v1",
    }


def validate_eot_terminal_predictive_mechanics(
    *,
    value: Any,
    base: Mapping[str, Any],
    terminal_leaf: Mapping[str, Any],
    owner: Mapping[str, Any],
    resolved_active: Mapping[str, Any],
) -> str | None:
    expected = normalize_terminal_predictive_mechanics_authority(
        value=value,
        base=base,
        terminal_leaf=terminal_leaf,
        owner=owner,
        resolved_active=resolved_active,
    )
    if value is None:
        return None
    if not isinstance(expected, Mapping):
        return "terminal_predictive_mechanics_validation_unavailable"
    if expected.get("status") == "rejected":
        return expected.get("reason", "terminal_predictive_mechanics_rejected")
    if deepcopy(dict(value)) == expected:
        return None
    # The EOT active row stores the normalized form, not the caller source.
    if isinstance(value, Mapping) and value.get("provenance") == "authenticated_exact_pair_terminal_predictive_mechanics_v1":
        return None if value == expected else "terminal_predictive_mechanics_normalized_mismatch"
    return "terminal_predictive_mechanics_not_normalized"


def project_post_eot_predictive_mechanics_authorities(
    *,
    phase_input: Mapping[str, Any],
    post_end_of_turn_active_states: Mapping[str, Any],
    source_eot_fingerprint: str,
) -> dict[str, Any] | None | str:
    active_states = phase_input.get("active_states")
    if not isinstance(active_states, Mapping):
        return "post_eot_predictive_mechanics_phase_active_invalid"
    supplied = any(
        isinstance(active_states.get(side), Mapping)
        and "predictive_mechanics" in active_states[side]
        for side in _SIDES
    )
    if not supplied:
        return None
    if not isinstance(source_eot_fingerprint, str) or not source_eot_fingerprint:
        return "post_eot_predictive_mechanics_eot_fingerprint_invalid"

    rows: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        active = active_states.get(side)
        final = post_end_of_turn_active_states.get(side) if isinstance(post_end_of_turn_active_states, Mapping) else None
        if not isinstance(active, Mapping) or not isinstance(final, Mapping):
            return "post_eot_predictive_mechanics_active_state_invalid"
        source = active.get("predictive_mechanics")
        owner = final.get("owner")
        if source is None:
            rows[side] = _post_incomplete(
                owner=owner,
                source_eot_fingerprint=source_eot_fingerprint,
                reason="terminal_predictive_mechanics_not_supplied",
                current_hp=final.get("current_hp"),
                maximum_hp=final.get("maximum_hp"),
            )
            continue
        if not isinstance(source, Mapping) or source.get("schema_version") != TERMINAL_SCHEMA_VERSION:
            return "post_eot_predictive_mechanics_source_invalid"
        if source.get("owner") != owner:
            return "post_eot_predictive_mechanics_owner_mismatch"
        if final.get("fainted") is True:
            rows[side] = {
                "status": "incomplete",
                "schema_version": POST_EOT_SCHEMA_VERSION,
                "owner": deepcopy(dict(owner)),
                "reason": "active_identity_fainted_during_eot",
                "retired": True,
                "source_terminal_predictive_mechanics": deepcopy(dict(source)),
                "source_eot_fingerprint": source_eot_fingerprint,
                "provenance": "predictive_mechanics_retired_by_eot_faint_v1",
            }
            continue

        condition_error = _post_condition_item_continuity(source, final)
        if condition_error is not None:
            return condition_error
        row = deepcopy(dict(source))
        row.update({
            "schema_version": POST_EOT_SCHEMA_VERSION,
            "source_terminal_predictive_mechanics": deepcopy(dict(source)),
            "source_eot_fingerprint": source_eot_fingerprint,
            "current_hp": {
                "status": "known",
                "current_hp": final["current_hp"],
                "maximum_hp": final["maximum_hp"],
                "provenance": "exact_end_of_turn_hp",
            },
            "fainted": False,
            "provenance": "surviving_post_eot_predictive_mechanics_v1",
        })
        direct = row.get("direct_mechanics")
        if isinstance(direct, dict) and direct.get("status") == "known":
            combatant = direct.get("combatant")
            if isinstance(combatant, dict):
                combatant["current_hp"] = final["current_hp"]
                combatant["max_hp"] = final["maximum_hp"]
        rows[side] = row
    return rows


def apply_post_eot_predictive_mechanics_contexts(
    *,
    state: Mapping[str, Any],
    authorities: Mapping[str, Any],
) -> dict[str, Any] | str:
    """Project surviving typed rows into established detached state contexts."""
    if not isinstance(state, Mapping) or not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "post_eot_predictive_mechanics_projection_invalid"
    result = deepcopy(dict(state))
    current = result.get("current_state")
    if not isinstance(current, dict):
        return "post_eot_predictive_mechanics_current_state_missing"

    level_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []
    ability_rows: list[dict[str, Any]] = []
    item_rows: list[dict[str, Any]] = []
    type_rows: list[dict[str, Any]] = []
    direct = {"generation": "gen9"}
    substitute_context = result.get("substitute_state_context")
    critical_rows: dict[str, Any] = {"volatiles": {}, "lucky_chant": {}}
    side_condition_rows: dict[str, Any] = {}

    shared_field: dict[str, Any] | None = None
    for side in _SIDES:
        row = authorities[side]
        active = result.get("active", {}).get(side)
        if not isinstance(row, Mapping) or not isinstance(active, Mapping):
            return "post_eot_predictive_mechanics_projection_row_invalid"
        owner = _owner_from_active(active)
        if row.get("owner") != owner:
            return "post_eot_predictive_mechanics_projection_owner_mismatch"
        if row.get("retired") is True or active.get("fainted") is True:
            continue

        level = row.get("current_level", {"status": "unknown"})
        level_rows.append({
            "side": side,
            "value": level.get("value") if level.get("status") == "known" else None,
            "status": "predicted" if level.get("status") == "known" else "unknown",
            "owner": deepcopy(owner),
            "source": "detached_post_eot_predictive_mechanics",
        })
        stats = row.get("current_final_stats", {})
        values = stats.get("values", {}) if isinstance(stats, Mapping) else {}
        for stat in _FINAL_STAT_KEYS:
            final_rows.append({
                "side": side,
                "stat": stat,
                "value": values.get(stat),
                "confidence": "known" if stat in values else "unknown",
                "owner": deepcopy(owner),
                "source": "detached_post_eot_predictive_mechanics",
            })
        stages = row.get("current_stages", {})
        stage_values = stages.get("values", {}) if isinstance(stages, Mapping) else {}
        for stat in _STAGE_KEYS:
            stage_rows.append({
                "side": side,
                "stat": stat,
                "stage": stage_values.get(stat),
                "status": "predicted" if stat in stage_values else "unknown",
                "owner": deepcopy(owner),
                "source": "detached_post_eot_predictive_mechanics",
            })

        ability = row.get("ability", {"status": "unknown"})
        ability_rows.append({
            "side": side,
            "ability": ability.get("value") if ability.get("status") == "known" else None,
            "status": "predicted" if ability.get("status") == "known" else ability.get("status", "unknown"),
            "owner": deepcopy(owner),
            "source": "detached_post_eot_predictive_mechanics",
        })
        item = row.get("item", {"status": "unknown"})
        item_rows.append({
            "side": side,
            "item": item.get("value") if item.get("status") == "known" else None,
            "status": (
                "predicted" if item.get("status") == "known"
                else "known_absent" if item.get("status") == "known_absent"
                else "unknown"
            ),
            "owner": deepcopy(owner),
            "source": "detached_post_eot_predictive_mechanics",
        })
        types = row.get("types", {"status": "unknown"})
        type_rows.append({
            "side": side,
            "types": deepcopy(types.get("value")) if types.get("status") == "known" else None,
            "status": "predicted" if types.get("status") == "known" else "unknown",
            "owner": deepcopy(owner),
            "source": "detached_post_eot_predictive_mechanics",
        })

        substitute = row.get("substitute", {"status": "unknown"})
        sub_state = {
            "known_active": "known_active",
            "known_inactive": "known_inactive",
            "unknown": "unknown",
        }.get(substitute.get("status"), "unknown")
        substitute_context = update_substitute_state_context(
            context=substitute_context if isinstance(substitute_context, Mapping) else None,
            session_id=owner["session_id"],
            owner=owner,
            state=sub_state,
            substitute_hp=substitute.get("substitute_hp") if sub_state == "known_active" else None,
            provenance="detached_post_eot_predictive_mechanics_v1",
        )

        critical_rows["volatiles"][side] = deepcopy(row.get("critical_hit_volatiles", {"status": "unknown"}))
        critical_rows["lucky_chant"][side] = deepcopy(row.get("lucky_chant", {"status": "unknown"}))
        side_condition_rows[side] = deepcopy(row.get("side_conditions", {"status": "unknown"}))

        field = row.get("field")
        if isinstance(field, Mapping) and field.get("status") == "known":
            candidate = {"weather": field.get("weather"), "terrain": field.get("terrain")}
            if shared_field is None:
                shared_field = candidate
            elif shared_field != candidate:
                return "post_eot_predictive_mechanics_field_contradiction"

        direct_fact = row.get("direct_mechanics")
        if isinstance(direct_fact, Mapping) and direct_fact.get("status") == "known":
            role = "attacker" if side == "self" else "defender"
            direct[role] = deepcopy(direct_fact["combatant"])

    current["trusted_level_context"] = {"current_levels": level_rows}
    current["final_stat_context"] = {"current_final_stats": final_rows}
    current["stat_stage_context"] = {"current_stages": stage_rows}
    current["ability_context"] = {"current_abilities": ability_rows}
    current["item_context"] = {"current_items": item_rows}
    current["current_type_context"] = {"current_types": type_rows}
    if len(direct) > 1:
        current["direct_mechanics_context"] = direct
    if shared_field is not None:
        field_context = current.setdefault("field_state_context", {}).setdefault("current_field", {})
        existing_weather = field_context.get("weather")
        if existing_weather is not None and shared_field.get("weather") is not None and existing_weather != shared_field["weather"]:
            return "post_eot_predictive_mechanics_weather_contradiction"
        if shared_field.get("weather") is not None:
            field_context["weather"] = shared_field["weather"]
        if shared_field.get("terrain") is not None:
            field_context["terrain"] = shared_field["terrain"]
    if substitute_context is not None:
        result["substitute_state_context"] = substitute_context
    result["detached_predictive_critical_state_authority"] = {
        "schema_version": "detached-predictive-critical-state-authority-v1",
        "volatiles": critical_rows["volatiles"],
        "lucky_chant": critical_rows["lucky_chant"],
        "provenance": "detached_post_eot_predictive_mechanics_v1",
    }
    result["detached_predictive_side_condition_authorities"] = {
        "schema_version": "detached-predictive-side-condition-authorities-v1",
        "sides": side_condition_rows,
        "provenance": "detached_post_eot_predictive_mechanics_v1",
    }
    result["post_eot_predictive_mechanics_authorities"] = deepcopy(dict(authorities))
    return result


def validate_post_eot_predictive_mechanics_authorities(
    *,
    authorities: Any,
    active_states: Mapping[str, Any],
) -> str | None:
    if authorities is None:
        return None
    if not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "post_eot_predictive_mechanics_authorities_invalid"
    for side in _SIDES:
        row = authorities[side]
        active = active_states.get(side) if isinstance(active_states, Mapping) else None
        if not isinstance(row, Mapping) or not isinstance(active, Mapping):
            return "post_eot_predictive_mechanics_row_invalid"
        if row.get("schema_version") != POST_EOT_SCHEMA_VERSION:
            return "post_eot_predictive_mechanics_schema_invalid"
        if row.get("owner") != _owner_from_active(active):
            return "post_eot_predictive_mechanics_owner_mismatch"
        if active.get("fainted") is True:
            if row.get("retired") is not True:
                return "post_eot_predictive_mechanics_fainted_not_retired"
        else:
            hp = row.get("current_hp")
            if (
                not isinstance(hp, Mapping)
                or hp.get("status") != "known"
                or hp.get("current_hp") != active.get("current_hp")
                or hp.get("maximum_hp") != active.get("max_hp")
            ):
                return "post_eot_predictive_mechanics_hp_mismatch"
    return None


def rebind_post_eot_predictive_mechanics_after_replacement(
    *,
    authorities: Any,
    source_state: Mapping[str, Any],
    next_state: Mapping[str, Any],
    replaced_side: str,
    incoming_owner: Mapping[str, Any],
    source_state_fingerprint: str,
) -> dict[str, Any] | str | None:
    if authorities is None:
        return None
    if not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "replacement_predictive_mechanics_authorities_invalid"
    if replaced_side not in _SIDES or not _exact_owner(incoming_owner, side=replaced_side):
        return "replacement_predictive_mechanics_incoming_owner_invalid"
    if not isinstance(source_state_fingerprint, str) or fingerprint_transition_preview_state(source_state) != source_state_fingerprint:
        return "replacement_predictive_mechanics_source_fingerprint_invalid"

    rows = deepcopy(dict(authorities))
    current = next_state.get("current_state")
    active = next_state.get("active", {}).get(replaced_side)
    if not isinstance(current, Mapping) or not isinstance(active, Mapping) or _owner_from_active(active) != dict(incoming_owner):
        return "replacement_predictive_mechanics_next_state_identity_invalid"
    rows[replaced_side] = _derive_replacement_row(
        current=current,
        state=next_state,
        side=replaced_side,
        owner=incoming_owner,
        source_state_fingerprint=source_state_fingerprint,
    )
    return rows


def materialize_next_turn_predictive_mechanics_authority(
    *,
    next_decision_state: Mapping[str, Any],
    next_decision_fingerprint: str,
    source_post_eot_fingerprint: str,
) -> dict[str, Any] | None:
    if not isinstance(next_decision_state, Mapping):
        return _next_rejected("next_turn_predictive_mechanics_state_invalid")
    if (
        not isinstance(next_decision_fingerprint, str)
        or fingerprint_transition_preview_state(next_decision_state) != next_decision_fingerprint
    ):
        return _next_rejected("next_turn_predictive_mechanics_fingerprint_mismatch")
    rows = next_decision_state.get("post_eot_predictive_mechanics_authorities")
    if rows is None:
        return None
    active = next_decision_state.get("active")
    error = validate_post_eot_predictive_mechanics_authorities(
        authorities=rows,
        active_states=active,
    )
    if error is not None:
        return _next_rejected(error)
    if not isinstance(source_post_eot_fingerprint, str) or not source_post_eot_fingerprint:
        return _next_rejected("next_turn_predictive_mechanics_source_post_eot_fingerprint_invalid")

    out: dict[str, Any] = {}
    for side in _SIDES:
        source = rows[side]
        owner = _owner_from_active(active[side])
        if active[side].get("fainted") is True:
            out[side] = {
                "status": "incomplete",
                "owner": deepcopy(owner),
                "reason": "active_identity_fainted_before_next_turn_action",
            }
            continue
        status = "resolved" if source.get("status") == "resolved" else "incomplete"
        row = deepcopy(dict(source))
        row.update({
            "status": status,
            "owner": deepcopy(owner),
            "source_post_eot_predictive_mechanics": deepcopy(dict(source)),
            "source_next_decision_fingerprint": next_decision_fingerprint,
            "source_post_eot_fingerprint": source_post_eot_fingerprint,
        })
        if status == "incomplete" and "reason" not in row:
            reasons = row.get("incomplete_reasons", ())
            row["reason"] = reasons[0] if reasons else "next_turn_predictive_mechanics_incomplete"
        out[side] = row
    return {
        "status": "resolved" if all(row.get("status") == "resolved" for row in out.values()) else "incomplete",
        "schema_version": NEXT_TURN_SCHEMA_VERSION,
        "session_id": next_decision_state["active"]["self"]["session_id"],
        "source_next_decision_fingerprint": next_decision_fingerprint,
        "source_post_eot_fingerprint": source_post_eot_fingerprint,
        "active_owners": {
            side: deepcopy(_owner_from_active(next_decision_state["active"][side]))
            for side in _SIDES
        },
        "sides": out,
        "provenance": "detached_next_turn_predictive_mechanics_transport_v1",
    }


def validate_next_turn_predictive_mechanics_authority(
    *,
    authority: Any,
    next_decision_state: Mapping[str, Any],
    next_decision_fingerprint: str,
) -> str | None:
    if not isinstance(authority, Mapping):
        return "next_turn_predictive_mechanics_authority_missing"
    source_post_eot_fingerprint = authority.get("source_post_eot_fingerprint")
    expected = materialize_next_turn_predictive_mechanics_authority(
        next_decision_state=next_decision_state,
        next_decision_fingerprint=next_decision_fingerprint,
        source_post_eot_fingerprint=source_post_eot_fingerprint,
    )
    if not isinstance(expected, Mapping):
        return "next_turn_predictive_mechanics_authority_unexpected"
    if expected.get("status") == "rejected":
        return expected.get("reason", "next_turn_predictive_mechanics_authority_rejected")
    if deepcopy(dict(authority)) != expected:
        return "next_turn_predictive_mechanics_authority_mismatch"
    return None


def validate_forced_continuation_predictive_mechanics_binding(
    *,
    forced_continuation: Mapping[str, Any],
    predictive_mechanics: Mapping[str, Any],
    next_decision_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Check that forced actor/target have authenticated next-turn mechanics rows."""
    if (
        not isinstance(forced_continuation, Mapping)
        or forced_continuation.get("status") != "resolved"
        or not isinstance(predictive_mechanics, Mapping)
        or predictive_mechanics.get("schema_version") != NEXT_TURN_SCHEMA_VERSION
    ):
        return {"status": "rejected", "schema_version": FORCED_BINDING_SCHEMA_VERSION, "reason": "forced_predictive_binding_input_invalid"}
    fingerprint = predictive_mechanics.get("source_next_decision_fingerprint")
    auth_error = validate_next_turn_predictive_mechanics_authority(
        authority=predictive_mechanics,
        next_decision_state=next_decision_state,
        next_decision_fingerprint=fingerprint,
    )
    if auth_error is not None:
        return {"status": "rejected", "schema_version": FORCED_BINDING_SCHEMA_VERSION, "reason": auth_error}
    if forced_continuation.get("source_next_decision_fingerprint") != fingerprint:
        return {"status": "rejected", "schema_version": FORCED_BINDING_SCHEMA_VERSION, "reason": "forced_predictive_fingerprint_mismatch"}
    actions = forced_continuation.get("forced_continuation_actions")
    rows = predictive_mechanics.get("sides")
    if not isinstance(actions, Mapping) or not isinstance(rows, Mapping):
        return {"status": "rejected", "schema_version": FORCED_BINDING_SCHEMA_VERSION, "reason": "forced_predictive_rows_missing"}
    bindings: dict[str, Any] = {}
    for side in _SIDES:
        action = actions.get(side)
        if not isinstance(action, Mapping) or action.get("status") != "resolved":
            continue
        other = "opponent" if side == "self" else "self"
        actor_row = rows.get(side)
        target_row = rows.get(other)
        if not isinstance(actor_row, Mapping) or actor_row.get("owner") != action.get("actor"):
            return {"status": "rejected", "schema_version": FORCED_BINDING_SCHEMA_VERSION, "reason": "forced_predictive_actor_mismatch"}
        if not isinstance(target_row, Mapping) or target_row.get("owner") != action.get("resolved_target_owner"):
            return {"status": "rejected", "schema_version": FORCED_BINDING_SCHEMA_VERSION, "reason": "forced_predictive_target_mismatch"}
        if actor_row.get("status") != "resolved" or target_row.get("status") != "resolved":
            return {
                "status": "incomplete",
                "schema_version": FORCED_BINDING_SCHEMA_VERSION,
                "reason": "forced_predictive_mechanics_incomplete",
                "side": side,
            }
        bindings[side] = {
            "actor": deepcopy(action["actor"]),
            "target": deepcopy(action["resolved_target_owner"]),
            "actor_mechanics": deepcopy(dict(actor_row)),
            "target_mechanics": deepcopy(dict(target_row)),
        }
    return {
        "status": "resolved",
        "schema_version": FORCED_BINDING_SCHEMA_VERSION,
        "source_next_decision_fingerprint": predictive_mechanics["source_next_decision_fingerprint"],
        "bindings": bindings,
        "execution_grant": False,
        "provenance": "forced_standard_charge_to_next_turn_predictive_mechanics_v1",
    }


def _derive_replacement_row(
    *,
    current: Mapping[str, Any],
    state: Mapping[str, Any],
    side: str,
    owner: Mapping[str, Any],
    source_state_fingerprint: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    level_rows = current.get("trusted_level_context", {}).get("current_levels", ())
    level_match = [row for row in level_rows if isinstance(row, Mapping) and row.get("side") == side]
    level = {"status": "unknown"}
    if len(level_match) == 1 and _positive_int(level_match[0].get("value")) and level_match[0]["value"] <= 100:
        level = {"status": "known", "value": level_match[0]["value"]}
    else:
        reasons.append("level_unknown")

    stat_rows = current.get("final_stat_context", {}).get("current_final_stats", ())
    stat_values = {
        row.get("stat"): row.get("value")
        for row in stat_rows
        if isinstance(row, Mapping) and row.get("side") == side and _positive_int(row.get("value"))
    }
    missing_stats = [stat for stat in _FINAL_STAT_KEYS if stat not in stat_values]
    final_stats = {"status": "known" if not missing_stats else "incomplete", "values": stat_values}
    reasons.extend(f"final_stat_{stat}_unknown" for stat in missing_stats)

    stage_rows = current.get("stat_stage_context", {}).get("current_stages", ())
    stage_values = {
        row.get("stat"): row.get("stage")
        for row in stage_rows
        if isinstance(row, Mapping) and row.get("side") == side and _stage(row.get("stage"))
    }
    missing_stages = [stat for stat in _STAGE_KEYS if stat not in stage_values]
    stages = {"status": "known" if not missing_stages else "incomplete", "values": stage_values}
    reasons.extend(f"stage_{stat}_unknown" for stat in missing_stages)

    ability = _current_simple(current, "ability_context", "current_abilities", side, "ability")
    item = _current_item(current, side)
    types = _current_types(current, side)
    condition = _current_condition(current, side)
    for name, fact in (("ability", ability), ("item", item), ("types", types), ("condition", condition)):
        if fact["status"] == "unknown":
            reasons.append(f"{name}_unknown")

    active = state["active"][side]
    hp = {"status": "known", "current_hp": active["current_hp"], "maximum_hp": active["max_hp"]}
    substitute = {"status": "unknown"}
    reasons.append("substitute_unknown")
    crit = {"status": "unknown"}
    lucky = {"status": "unknown"}
    reasons.extend(("critical_hit_volatiles_unknown", "lucky_chant_unknown"))

    field_current = current.get("field_state_context", {}).get("current_field")
    field = (
        {"status": "known", "weather": field_current.get("weather"), "terrain": field_current.get("terrain")}
        if isinstance(field_current, Mapping)
        else {"status": "unknown"}
    )
    if field["status"] == "unknown":
        reasons.append("field_unknown")
    side_conditions = {"status": "unknown"}
    reasons.append("side_conditions_unknown")

    role = "attacker" if side == "self" else "defender"
    direct_context = current.get("direct_mechanics_context", {})
    direct_combatant = direct_context.get(role) if isinstance(direct_context, Mapping) else None
    direct = (
        {"status": "known", "combatant": deepcopy(dict(direct_combatant))}
        if isinstance(direct_combatant, Mapping)
        else {"status": "unknown"}
    )
    if direct["status"] == "unknown":
        reasons.append("direct_mechanics_unknown")

    return {
        "status": "incomplete" if reasons else "resolved",
        "schema_version": POST_EOT_SCHEMA_VERSION,
        "owner": deepcopy(dict(owner)),
        "current_level": level,
        "current_final_stats": final_stats,
        "current_hp": hp,
        "fainted": active["fainted"],
        "current_stages": stages,
        "condition": condition,
        "item": item,
        "ability": ability,
        "types": types,
        "substitute": substitute,
        "critical_hit_volatiles": crit,
        "lucky_chant": lucky,
        "field": field,
        "side_conditions": side_conditions,
        "direct_mechanics": direct,
        "incomplete_reasons": tuple(sorted(set(reasons))),
        "source_replacement_state_fingerprint": source_state_fingerprint,
        "provenance": "replacement_rebound_predictive_mechanics_v1",
    }


def _post_condition_item_continuity(source: Mapping[str, Any], final: Mapping[str, Any]) -> str | None:
    condition = source.get("condition")
    terminal_condition = final.get("condition")
    if isinstance(condition, Mapping) and condition.get("status") != "unknown":
        if condition.get("status") == "known_none":
            if not isinstance(terminal_condition, Mapping) or terminal_condition.get("status") != "known_none":
                return "post_eot_predictive_mechanics_condition_contradiction"
        elif (
            condition.get("status") == "known_present"
            and (
                not isinstance(terminal_condition, Mapping)
                or terminal_condition.get("status") != "known_present"
                or terminal_condition.get("condition") != condition.get("condition")
            )
        ):
            return "post_eot_predictive_mechanics_condition_contradiction"
    item = source.get("item")
    terminal_item = final.get("item")
    if isinstance(item, Mapping) and item.get("status") != "unknown":
        if item.get("status") != terminal_item.get("status"):
            return "post_eot_predictive_mechanics_item_contradiction"
        if item.get("status") == "known" and item.get("value") != terminal_item.get("value"):
            return "post_eot_predictive_mechanics_item_contradiction"
    return None


def _post_incomplete(*, owner: Any, source_eot_fingerprint: str, reason: str, current_hp: Any, maximum_hp: Any) -> dict[str, Any]:
    return {
        "status": "incomplete",
        "schema_version": POST_EOT_SCHEMA_VERSION,
        "owner": deepcopy(dict(owner)) if isinstance(owner, Mapping) else owner,
        "reason": reason,
        "current_hp": {"status": "known", "current_hp": current_hp, "maximum_hp": maximum_hp},
        "fainted": current_hp == 0,
        "incomplete_reasons": (reason,),
        "source_eot_fingerprint": source_eot_fingerprint,
        "provenance": "missing_terminal_predictive_mechanics_explicit_incomplete_v1",
    }


def _condition_fact(value: Any, *, terminal: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known_none", "known_present", "unknown"}:
        return {}, "terminal_predictive_mechanics_condition_invalid"
    result = deepcopy(dict(value))
    if result["status"] == "known_present" and result.get("condition") not in _CONDITIONS:
        return {}, "terminal_predictive_mechanics_condition_invalid"
    if result["status"] != "unknown":
        expected_status = terminal.get("status") if isinstance(terminal, Mapping) else None
        if result["status"] != expected_status:
            return {}, "terminal_predictive_mechanics_condition_contradiction"
        if result["status"] == "known_present" and result.get("condition") != terminal.get("condition"):
            return {}, "terminal_predictive_mechanics_condition_contradiction"
    return result, None


def _item_fact(value: Any, *, terminal: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "known_absent", "unknown"}:
        return {}, "terminal_predictive_mechanics_item_invalid"
    result = deepcopy(dict(value))
    if result["status"] == "known" and (not isinstance(result.get("value"), str) or not result["value"]):
        return {}, "terminal_predictive_mechanics_item_invalid"
    if result["status"] != "unknown":
        if not isinstance(terminal, Mapping) or terminal.get("status") != result["status"]:
            return {}, "terminal_predictive_mechanics_item_contradiction"
        if result["status"] == "known" and terminal.get("value") != result.get("value"):
            return {}, "terminal_predictive_mechanics_item_contradiction"
    return result, None


def _simple_identity_fact(value: Any, label: str) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in _KNOWN_STATUS:
        return {}, f"terminal_predictive_mechanics_{label}_invalid"
    result = deepcopy(dict(value))
    if result["status"] == "known" and (not isinstance(result.get("value"), str) or not result["value"]):
        return {}, f"terminal_predictive_mechanics_{label}_invalid"
    return result, None


def _types_fact(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return {}, "terminal_predictive_mechanics_types_invalid"
    result = deepcopy(dict(value))
    if result["status"] == "known":
        types = result.get("value")
        if not isinstance(types, list) or not types or any(not isinstance(t, str) or not t for t in types):
            return {}, "terminal_predictive_mechanics_types_invalid"
    return result, None


def _level_fact(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return {}, "terminal_predictive_mechanics_level_invalid"
    if value["status"] == "known" and (not _positive_int(value.get("value")) or value["value"] > 100):
        return {}, "terminal_predictive_mechanics_level_invalid"
    return deepcopy(dict(value)), None


def _final_stats_fact(value: Any, maximum_hp: int) -> tuple[dict[str, Any], tuple[str, ...], str | None]:
    if value is None or (isinstance(value, Mapping) and value.get("status") == "unknown"):
        return {"status": "incomplete", "values": {}}, _FINAL_STAT_KEYS, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "incomplete"} or not isinstance(value.get("values"), Mapping):
        return {}, (), "terminal_predictive_mechanics_final_stats_invalid"
    values = {
        stat: raw for stat, raw in value["values"].items()
        if stat in _FINAL_STAT_KEYS and _positive_int(raw)
    }
    if "hp" in values and values["hp"] != maximum_hp:
        return {}, (), "terminal_predictive_mechanics_final_hp_stat_contradiction"
    missing = tuple(stat for stat in _FINAL_STAT_KEYS if stat not in values)
    return {"status": "known" if not missing else "incomplete", "values": values}, missing, None


def _stages_fact(value: Any) -> tuple[dict[str, Any], tuple[str, ...], str | None]:
    if value is None or (isinstance(value, Mapping) and value.get("status") == "unknown"):
        return {"status": "incomplete", "values": {}}, _STAGE_KEYS, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "incomplete"} or not isinstance(value.get("values"), Mapping):
        return {}, (), "terminal_predictive_mechanics_stages_invalid"
    values = {
        stat: raw for stat, raw in value["values"].items()
        if stat in _STAGE_KEYS and _stage(raw)
    }
    missing = tuple(stat for stat in _STAGE_KEYS if stat not in values)
    return {"status": "known" if not missing else "incomplete", "values": values}, missing, None


def _substitute_fact(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known_active", "known_inactive", "unknown"}:
        return {}, "terminal_predictive_mechanics_substitute_invalid"
    if value["status"] == "known_active":
        if not _positive_int(value.get("substitute_hp")):
            return {}, "terminal_predictive_mechanics_substitute_invalid"
    elif value.get("substitute_hp") is not None:
        return {}, "terminal_predictive_mechanics_substitute_invalid"
    return deepcopy(dict(value)), None


def _crit_volatile_fact(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return {}, "terminal_predictive_mechanics_crit_volatiles_invalid"
    if value["status"] == "known":
        values = value.get("value")
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            return {}, "terminal_predictive_mechanics_crit_volatiles_invalid"
    return deepcopy(dict(value)), None


def _known_active_fact(value: Any, label: str) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known_active", "known_inactive", "unknown"}:
        return {}, f"terminal_predictive_mechanics_{label}_invalid"
    return deepcopy(dict(value)), None


def _field_fact(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return {}, "terminal_predictive_mechanics_field_invalid"
    if value["status"] == "known":
        for key in ("weather", "terrain"):
            if key in value and value[key] is not None and (not isinstance(value[key], str) or not value[key]):
                return {}, "terminal_predictive_mechanics_field_invalid"
    return deepcopy(dict(value)), None


def _side_conditions_fact(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return {}, "terminal_predictive_mechanics_side_conditions_invalid"
    if value["status"] == "known" and not isinstance(value.get("value"), Mapping):
        return {}, "terminal_predictive_mechanics_side_conditions_invalid"
    return deepcopy(dict(value)), None


def _direct_fact(
    value: Any,
    *,
    hp: Mapping[str, int],
    condition: Mapping[str, Any],
    item: Mapping[str, Any],
    ability: Mapping[str, Any],
    types: Mapping[str, Any],
    final_stats: Mapping[str, Any],
    stages: Mapping[str, Any],
    level: Mapping[str, Any],
) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"status": "unknown"}, None
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return {}, "terminal_predictive_mechanics_direct_invalid"
    if value["status"] == "unknown":
        return deepcopy(dict(value)), None
    combatant = value.get("combatant")
    if not isinstance(combatant, Mapping):
        return {}, "terminal_predictive_mechanics_direct_invalid"
    c = deepcopy(dict(combatant))
    if c.get("current_hp") != hp["current_hp"] or c.get("max_hp") != hp["maximum_hp"]:
        return {}, "terminal_predictive_mechanics_direct_hp_contradiction"
    if level.get("status") == "known" and c.get("level") not in {None, level["value"]}:
        return {}, "terminal_predictive_mechanics_direct_level_contradiction"
    if final_stats.get("status") == "known":
        stats = c.get("stats")
        if not isinstance(stats, Mapping) or any(stats.get(stat) != final_stats["values"][stat] for stat in _FINAL_STAT_KEYS):
            return {}, "terminal_predictive_mechanics_direct_stats_contradiction"
    if stages.get("status") == "known":
        boosts = c.get("boosts")
        if not isinstance(boosts, Mapping) or any(
            boosts.get(stat) != stages["values"][stat]
            for stat in _DIRECT_BOOST_KEYS
        ):
            return {}, "terminal_predictive_mechanics_direct_stages_contradiction"
    if condition.get("status") != "unknown":
        expected_status = None if condition["status"] == "known_none" else condition.get("condition")
        if c.get("status") not in {None, expected_status}:
            return {}, "terminal_predictive_mechanics_direct_condition_contradiction"
    if item.get("status") == "known" and c.get("item") not in {None, item.get("value")}:
        return {}, "terminal_predictive_mechanics_direct_item_contradiction"
    if item.get("status") == "known_absent" and c.get("item") not in {None, ""}:
        return {}, "terminal_predictive_mechanics_direct_item_contradiction"
    if ability.get("status") == "known" and c.get("ability") not in {None, ability.get("value")}:
        return {}, "terminal_predictive_mechanics_direct_ability_contradiction"
    if (
        types.get("status") == "known"
        and c.get("types") is not None
        and c.get("types") != types.get("value")
    ):
        return {}, "terminal_predictive_mechanics_direct_type_contradiction"
    return {"status": "known", "combatant": c}, None


def _terminal_stage_expectations(terminal_leaf: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    source = terminal_leaf.get("source_pair_branch")
    _collect_stage_expectations(source, owner, out)
    return out


def _collect_stage_expectations(value: Any, owner: Mapping[str, Any], out: dict[str, int]) -> None:
    if isinstance(value, Mapping):
        target = value.get("target")
        stat = value.get("stat")
        if target == dict(owner) and stat in _STAGE_KEYS:
            after = value.get("post_stage")
            if after is None:
                after = value.get("stage_after")
            if _stage(after):
                out[stat] = after
        effect = value.get("deterministic_stage_effect")
        if isinstance(effect, Mapping):
            _collect_stage_expectations(effect, owner, out)
        for nested in value.values():
            if isinstance(nested, (Mapping, list, tuple)):
                _collect_stage_expectations(nested, owner, out)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _collect_stage_expectations(nested, owner, out)


def _current_simple(current: Mapping[str, Any], context_key: str, rows_key: str, side: str, value_key: str) -> dict[str, Any]:
    rows = current.get(context_key, {}).get(rows_key, ())
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("side") == side]
    if len(matches) != 1:
        return {"status": "unknown"}
    row = matches[0]
    if row.get("status") == "unknown" or not isinstance(row.get(value_key), str) or not row[value_key]:
        return {"status": "unknown"}
    return {"status": "known", "value": row[value_key]}


def _current_item(current: Mapping[str, Any], side: str) -> dict[str, Any]:
    rows = current.get("item_context", {}).get("current_items", ())
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("side") == side]
    if len(matches) != 1:
        return {"status": "unknown"}
    row = matches[0]
    if row.get("status") == "known_absent":
        return {"status": "known_absent"}
    if isinstance(row.get("item"), str) and row["item"]:
        return {"status": "known", "value": row["item"]}
    return {"status": "unknown"}


def _current_types(current: Mapping[str, Any], side: str) -> dict[str, Any]:
    rows = current.get("current_type_context", {}).get("current_types", ())
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("side") == side]
    if len(matches) == 1 and isinstance(matches[0].get("types"), list) and matches[0]["types"]:
        return {"status": "known", "value": deepcopy(matches[0]["types"])}
    return {"status": "unknown"}


def _current_condition(current: Mapping[str, Any], side: str) -> dict[str, Any]:
    rows = current.get("condition_context", {}).get("current_conditions", ())
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("side") == side]
    if len(matches) != 1:
        return {"status": "unknown"}
    kind = matches[0].get("condition_type")
    if kind == "none":
        return {"status": "known_none"}
    if kind in _CONDITIONS:
        return {"status": "known_present", "condition": kind}
    return {"status": "unknown"}


def _exact_owner(value: Any, *, side: str) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and value.get("side") == side
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and _integer(value.get("slot_index"))
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _owner_from_active(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in _OWNER_KEYS}


def _stage(value: Any) -> bool:
    return _integer(value) and -6 <= value <= 6


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_int(value: Any) -> bool:
    return _integer(value) and value > 0


def _rejected(reason: str) -> dict[str, Any]:
    return {"status": "rejected", "schema_version": TERMINAL_SCHEMA_VERSION, "reason": reason}


def _next_rejected(reason: str) -> dict[str, Any]:
    return {"status": "rejected", "schema_version": NEXT_TURN_SCHEMA_VERSION, "reason": reason}
