"""Bounded, exact-owner composition of supported detached EOT phases."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from llm.advisor_end_of_turn_preview import apply_owner_condition_end_of_turn
from llm.advisor_ice_body_end_of_turn import _ability, _field_weather_authority, _owners, _sync_hp
from llm.advisor_ice_body_recovery_core import evaluate_weather_recovery
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item, _types
from llm.advisor_sandstorm_residual_core import evaluate_sandstorm_residual
from llm.advisor_solar_power_residual_core import evaluate_solar_power_residual
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_weather_event_target_order import validate_weather_event_target_order


_ORDERING_PATH = Path(__file__).parents[1] / "data" / "static" / "detached_eot_ordering_v1.json"
_WEATHER_ABILITIES = {"snow": ("ice-body", "ice_body"), "rain": ("rain-dish", "rain_dish"), "rain-dry": ("dry-skin", "dry_skin"), "sun": ("solar-power", "solar_power")}


def project_per_owner_end_of_turn(*, pre_end_of_turn: Mapping[str, Any], owner: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compose tier 1 Weather then tier 9 condition for one exact active owner.

    This deliberately refuses a multi-owner request: Showdown's within-Weather
    target ordering is not represented by the detached branch model.
    """
    metadata = _ordering_metadata()
    if metadata is None:
        return _result("rejected", "invalid_detached_eot_ordering_metadata")
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("status") != "resolved" or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn":
        return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state")
    source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None:
        return _result("rejected", "invalid_pre_end_of_turn_branch")
    state = deepcopy(dict(source))
    owners = _owners(state)
    if owners is None:
        return _result("rejected", "invalid_active_owner")
    side = _exact_owner_side(owner, owners)
    if side is None:
        return _result("rejected", "stale_or_foreign_eot_owner")
    trace: list[dict[str, Any]] = []
    active = state["active"][side]
    if not active["fainted"]:
        weather = _weather(state)
        if weather == "unknown":
            return _result("incomplete", "current_field_weather_authority")
        tier_one = _apply_weather_for_owner(state=state, side=side, weather=weather, source_fingerprint=source_fp, owner=owners[side])
        if tier_one.get("status") != "resolved":
            return tier_one
        if isinstance(tier_one.get("trace"), Mapping):
            trace.append({"sequence": 1, "tier": metadata["families"]["weather"]["tier"], "branch_fingerprint_consumed": source_fp, **tier_one["trace"]})
        tier_one_fp = fingerprint_transition_preview_state(state)
        if not state["active"][side]["fainted"]:
            condition = apply_owner_condition_end_of_turn(
                state=state,
                side=side,
                source_snapshot_fingerprint=pre_end_of_turn.get("source_snapshot_fingerprint"),
                source_branch_fingerprint=tier_one_fp,
            )
            if condition.get("status") != "resolved":
                return condition
            if isinstance(condition.get("trace"), Mapping):
                row = deepcopy(condition["trace"])
                family = "poison_heal_compound" if row["effect"] == "poison_heal_recovery" else row["condition"]
                trace.append({"sequence": len(trace) + 1, "tier": metadata["families"][family]["tier"], "branch_fingerprint_consumed": tier_one_fp, **row})
        elif isinstance(tier_one.get("trace"), Mapping):
            trace.append({"sequence": len(trace) + 1, "tier": metadata["families"]["poison"]["tier"], "effect": "condition_phase", "owner": deepcopy(owners[side]), "execution_status": "skipped", "reason": "fainted_by_tier_one_weather"})
    result_fp = fingerprint_transition_preview_state(state)
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": result_fp, "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "ordering": {"scope": "one_exact_owner", "tiers": [1, 9], "authority": metadata["authority"]["source"]}, "limitations": ["cross_owner_weather_order_unrepresented", "no_reducer_or_runtime_writeback"]}


def reject_cross_owner_weather_order(*, owners: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Explicit boundary for callers asking this v1 coordinator to order owners."""
    return _result("incomplete", "cross_owner_weather_order_unrepresented") if len(owners) > 1 else _result("rejected", "exactly_one_owner_required")


def project_cross_owner_weather_end_of_turn(*, pre_end_of_turn: Mapping[str, Any], weather_event_target_order: Mapping[str, Any] | None) -> dict[str, Any]:
    """Execute one frozen canonical Weather plan, then an unambiguous tier-nine owner."""
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("status") != "resolved" or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn":
        return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state")
    source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None:
        return _result("rejected", "invalid_pre_end_of_turn_branch")
    validated = validate_weather_event_target_order(branch_state=source, source_branch_fingerprint=source_fp, projection=weather_event_target_order)
    if validated.get("status") != "resolved":
        return validated
    state = deepcopy(dict(source))
    owners = _owners(state)
    if owners is None:
        return _result("rejected", "invalid_active_owner")
    weather = _weather(state)
    if weather == "unknown":
        return _result("incomplete", "current_field_weather_authority")
    trace: list[dict[str, Any]] = []
    for planned_owner in validated["frozen_weather_event_plan"]["ordered_active_owners"]:
        side = _exact_owner_side(planned_owner, owners)
        if side is None:
            return _result("rejected", "stale_or_foreign_weather_event_target")
        consumed = fingerprint_transition_preview_state(state)
        if consumed is None:
            return _result("rejected", "invalid_weather_event_branch_generation")
        active = state["active"][side]
        if active["fainted"]:
            trace.append({"sequence": len(trace) + 1, "tier": 1, "effect": "weather_event", "owner": deepcopy(planned_owner), "branch_fingerprint_consumed": consumed, "execution_status": "skipped", "reason": "fainted_before_weather_event"})
            continue
        result = _apply_weather_for_owner(state=state, side=side, weather=weather, source_fingerprint=consumed, owner=planned_owner)
        if result.get("status") != "resolved":
            return result
        if isinstance(result.get("trace"), Mapping):
            trace.append({"sequence": len(trace) + 1, "tier": 1, "branch_fingerprint_consumed": consumed, **result["trace"]})
    condition_side = _single_condition_side(state)
    if condition_side == "multiple":
        return _result("incomplete", "cross_owner_condition_order_unrepresented")
    if isinstance(condition_side, str) and not state["active"][condition_side]["fainted"]:
        consumed = fingerprint_transition_preview_state(state)
        condition = apply_owner_condition_end_of_turn(state=state, side=condition_side, source_snapshot_fingerprint=pre_end_of_turn.get("source_snapshot_fingerprint"), source_branch_fingerprint=consumed)
        if condition.get("status") != "resolved":
            return condition
        if isinstance(condition.get("trace"), Mapping):
            row = deepcopy(condition["trace"])
            family = "poison_heal_compound" if row["effect"] == "poison_heal_recovery" else row["condition"]
            trace.append({"sequence": len(trace) + 1, "tier": _ordering_metadata()["families"][family]["tier"], "branch_fingerprint_consumed": consumed, **row})
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "ordering": {"weather_target_order": deepcopy(validated["frozen_weather_event_plan"]), "tiers": [1, 9]}, "limitations": ["weather_target_order_projection_required", "cross_owner_condition_order_unrepresented", "no_reducer_or_runtime_writeback"]}


def _apply_weather_for_owner(*, state: dict[str, Any], side: str, weather: str, source_fingerprint: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    if weather == "none":
        return {"status": "resolved", "trace": None}
    session = owner["session_id"]
    if weather not in {"sandstorm", "snow", "rain", "sun"} or not _field_weather_authority(state, source_fingerprint, session, weather):
        return _result("rejected", f"stale_or_invalid_branch_{weather}_authority")
    ability = _ability(state, side)
    if ability is None:
        return _result("incomplete", "current_ability_authority")
    abilities = {candidate: _ability(state, candidate) for candidate in ("self", "opponent")}
    if any(value is None for value in abilities.values()):
        return _result("incomplete", "current_ability_authority")
    active = state["active"][side]
    if weather == "sandstorm":
        current_type, item = _types(state, side), _item(state, side)
        if current_type is None:
            return _result("incomplete", "sandstorm_current_type_authority")
        if item is _UNKNOWN:
            return _result("incomplete", "sandstorm_current_item_authority")
        outcome = evaluate_sandstorm_residual(current_type=current_type, item=item, active_abilities=abilities, target_side=side, current_hp=active["current_hp"], maximum_hp=active["max_hp"])
        label = "sandstorm_residual"
    elif weather == "snow" and ability == "ice-body":
        outcome, label = evaluate_weather_recovery(active_abilities=abilities, target_side=side, required_ability=ability, current_hp=active["current_hp"], maximum_hp=active["max_hp"]), "ice_body_recovery"
    elif weather == "rain" and ability in {"rain-dish", "dry-skin"}:
        outcome, label = evaluate_weather_recovery(active_abilities=abilities, target_side=side, required_ability=ability, current_hp=active["current_hp"], maximum_hp=active["max_hp"]), f"{ability.replace('-', '_')}_recovery"
    elif weather == "sun" and ability == "solar-power":
        outcome, label = evaluate_solar_power_residual(active_abilities=abilities, target_side=side, current_hp=active["current_hp"], maximum_hp=active["max_hp"]), "solar_power_residual"
    else:
        return {"status": "resolved", "trace": None}
    if outcome.get("status") != "complete":
        return _result("incomplete", f"canonical_{label}_authority")
    post = outcome.get("post_hp")
    if not isinstance(post, int):
        return _result("incomplete", f"canonical_{label}_post_hp")
    active["current_hp"], active["fainted"] = post, post == 0
    _sync_hp(state, side, post, outcome["max_hp"])
    return {"status": "resolved", "trace": {"effect": label, "owner": deepcopy(dict(owner)), "weather": weather, "execution_status": "prevented" if outcome.get("outcome", "").startswith(("suppressed", "immune")) else "executed", "provenance": f"detached_branch_{label}_v1", **deepcopy(outcome)}}


def _weather(state: Mapping[str, Any]) -> str:
    current = state.get("current_state")
    field = current.get("field_state_context", {}).get("current_field") if isinstance(current, Mapping) else None
    return field.get("weather") if isinstance(field, Mapping) and field.get("weather") in {"none", "rain", "sun", "sandstorm", "snow", "unknown"} else "unknown"


def _single_condition_side(state: Mapping[str, Any]) -> str | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("condition_context", {}).get("current_conditions") if isinstance(current, Mapping) else None
    found = [row.get("side") for row in rows if isinstance(row, Mapping) and row.get("condition_type") in {"poison", "toxic"}] if isinstance(rows, list) else []
    predicted = state.get("predicted_condition_context") if isinstance(state, Mapping) else None
    if isinstance(predicted, Mapping) and predicted.get("condition_type") in {"poison", "toxic"}:
        side = predicted.get("owner", {}).get("side")
        if side not in found:
            found.append(side)
    return found[0] if len(found) == 1 and found[0] in {"self", "opponent"} else "multiple" if len(found) > 1 else None


def _exact_owner_side(owner: Mapping[str, Any] | None, owners: Mapping[str, Mapping[str, Any]]) -> str | None:
    if not isinstance(owner, Mapping):
        return None
    return next((side for side, exact in owners.items() if dict(owner) == dict(exact)), None)


def _ordering_metadata() -> dict[str, Any] | None:
    try:
        data = json.loads(_ORDERING_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    expected = {"weather": 1, "poison": 9, "toxic": 9, "poison_heal_compound": 9}
    families = data.get("families") if isinstance(data, Mapping) else None
    if data.get("schema_version") != "detached-eot-ordering-v1" or not isinstance(families, Mapping) or any(not isinstance(families.get(name), Mapping) or families[name].get("tier") != tier for name, tier in expected.items()):
        return None
    return data


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
