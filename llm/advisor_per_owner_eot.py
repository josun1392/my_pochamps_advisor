"""Bounded, exact-owner composition of supported detached EOT phases."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from llm.advisor_end_of_turn_preview import _condition, apply_owner_condition_end_of_turn
from llm.advisor_ice_body_end_of_turn import _ability, _field_weather_authority, _owners, _sync_hp
from llm.advisor_ice_body_recovery_core import evaluate_weather_recovery
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item, _types
from llm.advisor_sandstorm_residual_core import evaluate_sandstorm_residual
from llm.advisor_solar_power_residual_core import evaluate_solar_power_residual
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_weather_event_target_order import validate_weather_event_target_order
from llm.advisor_condition_event_target_order import validate_condition_event_target_order
from llm.advisor_leftovers_end_of_turn import apply_owner_leftovers_end_of_turn
from llm.advisor_black_sludge_end_of_turn import apply_owner_black_sludge_end_of_turn
from llm.advisor_leftovers_event_target_order import validate_item_residual_target_order
from llm.advisor_aqua_ring_persistent_effect import aqua_ring_state, apply_owner_aqua_ring_end_of_turn
from llm.advisor_aqua_ring_target_order import validate_aqua_ring_target_order
from llm.advisor_ingrain_persistent_effect import apply_owner_ingrain_end_of_turn, ingrain_state
from llm.advisor_ingrain_target_order import validate_ingrain_target_order
from llm.advisor_leech_seed_end_of_turn import apply_owner_leech_seed_end_of_turn, leech_seed_state
from llm.advisor_leech_seed_target_order import validate_leech_seed_target_order


_ORDERING_PATH = Path(__file__).parents[1] / "data" / "static" / "detached_eot_ordering_v1.json"
_WEATHER_ABILITIES = {"snow": ("ice-body", "ice_body"), "rain": ("rain-dish", "rain_dish"), "rain-dry": ("dry-skin", "dry_skin"), "sun": ("solar-power", "solar_power")}


def project_per_owner_end_of_turn(*, pre_end_of_turn: Mapping[str, Any], owner: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compose tiers 1 Weather, 5 Leftovers, then 9 condition for one owner.

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
            item = _item(state, side)
            item_adapter = apply_owner_leftovers_end_of_turn if item == "leftovers" else apply_owner_black_sludge_end_of_turn if item == "black-sludge" else None
            if item_adapter is not None:
                item_result = item_adapter(state=state, side=side, owner=owners[side], source_branch_fingerprint=tier_one_fp)
                if item_result.get("status") != "resolved":
                    return item_result
                family = "leftovers" if item == "leftovers" else "black_sludge"
                trace.append({"sequence": len(trace) + 1, "tier": metadata["families"][family]["tier"], "branch_fingerprint_consumed": tier_one_fp, **item_result["trace"]})
        leftovers_fp = fingerprint_transition_preview_state(state)
        aqua_state = aqua_ring_state(state, side, owners[side]) if "aqua_ring_persistent_effect_context" in state else "known_inactive"
        if aqua_state == "unknown": return _result("incomplete", "aqua_ring_persistent_effect_unknown")
        if aqua_state is None: return _result("rejected", "stale_or_invalid_aqua_ring_authority")
        if not state["active"][side]["fainted"] and aqua_state == "known_active":
            aqua = apply_owner_aqua_ring_end_of_turn(state=state, side=side, owner=owners[side], source_branch_fingerprint=leftovers_fp)
            if aqua.get("status") != "resolved": return aqua
            trace.append({"sequence": len(trace) + 1, "tier": metadata["families"]["aqua_ring"]["tier"], "branch_fingerprint_consumed": leftovers_fp, **aqua["trace"]})
        aqua_fp = fingerprint_transition_preview_state(state)
        ingrain_effect_state = ingrain_state(state, side, owners[side]) if "ingrain_persistent_effect_context" in state else "known_inactive"
        if ingrain_effect_state == "unknown": return _result("incomplete", "ingrain_persistent_effect_unknown")
        if ingrain_effect_state is None: return _result("rejected", "stale_or_invalid_ingrain_authority")
        if not state["active"][side]["fainted"] and ingrain_effect_state == "known_active":
            ingrain = apply_owner_ingrain_end_of_turn(state=state, side=side, owner=owners[side], source_branch_fingerprint=aqua_fp)
            if ingrain.get("status") != "resolved": return ingrain
            trace.append({"sequence": len(trace) + 1, "tier": metadata["families"]["ingrain"]["tier"], "branch_fingerprint_consumed": aqua_fp, **ingrain["trace"]})
        ingrain_fp = fingerprint_transition_preview_state(state)
        seed = leech_seed_state(state, side, owners[side]) if "leech_seed_persistent_effect_context" in state else {"state": "known_inactive"}
        if seed is None: return _result("rejected", "stale_or_invalid_leech_seed_authority")
        if seed["state"] == "unknown": return _result("incomplete", "leech_seed_persistent_effect_unknown")
        if not state["active"][side]["fainted"] and seed["state"] == "known_active":
            leech = apply_owner_leech_seed_end_of_turn(state=state, side=side, owner=owners[side], source_branch_fingerprint=ingrain_fp)
            if leech.get("status") != "resolved": return leech
            if leech.get("trace") is not None: trace.append({"sequence": len(trace)+1, "tier": metadata["families"]["leech_seed"]["tier"], "branch_fingerprint_consumed": ingrain_fp, **leech["trace"]})
        leech_fp = fingerprint_transition_preview_state(state)
        if not state["active"][side]["fainted"]:
            condition = apply_owner_condition_end_of_turn(
                state=state,
                side=side,
                source_snapshot_fingerprint=pre_end_of_turn.get("source_snapshot_fingerprint"),
                source_branch_fingerprint=leech_fp,
            )
            if condition.get("status") != "resolved":
                return condition
            if isinstance(condition.get("trace"), Mapping):
                row = deepcopy(condition["trace"])
                family = "poison_heal_compound" if row["effect"] == "poison_heal_recovery" else row["condition"]
                trace.append({"sequence": len(trace) + 1, "tier": metadata["families"][family]["tier"], "branch_fingerprint_consumed": leech_fp, **row})
        elif isinstance(tier_one.get("trace"), Mapping):
            trace.append({"sequence": len(trace) + 1, "tier": metadata["families"]["poison"]["tier"], "effect": "condition_phase", "owner": deepcopy(owners[side]), "execution_status": "skipped", "reason": "fainted_by_tier_one_weather"})
    result_fp = fingerprint_transition_preview_state(state)
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": result_fp, "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "ordering": {"scope": "one_exact_owner", "tiers": [1, 5, 6, 7, 8, 9], "authority": metadata["authority"]["source"]}, "limitations": ["cross_owner_weather_order_unrepresented", "cross_owner_item_residual_order_unrepresented", "cross_owner_aqua_ring_order_unrepresented", "cross_owner_ingrain_order_unrepresented", "cross_owner_leech_seed_order_unrepresented", "no_reducer_or_runtime_writeback"]}


def reject_cross_owner_weather_order(*, owners: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Explicit boundary for callers asking this v1 coordinator to order owners."""
    return _result("incomplete", "cross_owner_weather_order_unrepresented") if len(owners) > 1 else _result("rejected", "exactly_one_owner_required")


def project_cross_owner_weather_end_of_turn(*, pre_end_of_turn: Mapping[str, Any], weather_event_target_order: Mapping[str, Any] | None, condition_event_target_order: Mapping[str, Any] | None = None, leftovers_event_target_order: Mapping[str, Any] | None = None, aqua_ring_target_order: Mapping[str, Any] | None = None, ingrain_target_order: Mapping[str, Any] | None = None, leech_seed_target_order: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Execute one frozen canonical Weather plan, then an unambiguous tier-nine owner."""
    weather_phase = project_cross_owner_weather_phase(pre_end_of_turn=pre_end_of_turn, weather_event_target_order=weather_event_target_order)
    if weather_phase.get("status") != "resolved":
        return weather_phase
    state = deepcopy(dict(weather_phase["next_state"]))
    trace = deepcopy(weather_phase["eot_consequence_trace"])
    leftovers = _apply_item_residual_phase(state=state, projection=leftovers_event_target_order)
    if leftovers.get("status") != "resolved":
        return leftovers
    for row in leftovers["trace"]:
        trace.append({"sequence": len(trace) + 1, **row})
    aqua = _apply_aqua_ring_phase(state=state, projection=aqua_ring_target_order)
    if aqua.get("status") != "resolved": return aqua
    for row in aqua["trace"]: trace.append({"sequence": len(trace) + 1, **row})
    ingrain = _apply_ingrain_phase(state=state, projection=ingrain_target_order)
    if ingrain.get("status") != "resolved": return ingrain
    for row in ingrain["trace"]: trace.append({"sequence": len(trace) + 1, **row})
    leech = _apply_leech_seed_phase(state=state, projection=leech_seed_target_order)
    if leech.get("status") != "resolved": return leech
    for row in leech["trace"]: trace.append({"sequence": len(trace) + 1, **row})
    condition = _apply_condition_phase(state=state, source_snapshot_fingerprint=pre_end_of_turn.get("source_snapshot_fingerprint"), projection=condition_event_target_order)
    if condition.get("status") != "resolved":
        return condition
    for row in condition["trace"]:
        trace.append({"sequence": len(trace) + 1, **row})
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": weather_phase["source_pre_end_of_turn_fingerprint"], "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "ordering": {"weather_target_order": deepcopy(weather_phase["ordering"]["weather_target_order"]), "item_residual_target_order": leftovers["ordering"]["leftovers_target_order"], "aqua_ring_target_order": aqua["ordering"]["aqua_ring_target_order"], "ingrain_target_order": ingrain["ordering"]["ingrain_target_order"], "leech_seed_target_order": leech["ordering"]["leech_seed_target_order"], "condition_target_order": condition["ordering"]["condition_target_order"], "tiers": [1, 5, 6, 7, 8, 9]}, "limitations": ["weather_target_order_projection_required", "cross_owner_item_residual_order_unrepresented", "cross_owner_aqua_ring_order_unrepresented", "cross_owner_ingrain_order_unrepresented", "cross_owner_leech_seed_order_unrepresented", "cross_owner_condition_order_unrepresented", "no_reducer_or_runtime_writeback"]}


def project_cross_owner_weather_phase(*, pre_end_of_turn: Mapping[str, Any], weather_event_target_order: Mapping[str, Any] | None) -> dict[str, Any]:
    """Execute only frozen tier-one Weather and expose its actual next branch."""
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
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "pre_condition_end_of_turn"}, "ordering": {"weather_target_order": deepcopy(validated["frozen_weather_event_plan"]), "tiers": [1]}, "limitations": ["weather_target_order_projection_required", "no_reducer_or_runtime_writeback"]}


def project_cross_owner_condition_end_of_turn(*, pre_end_of_turn: Mapping[str, Any], condition_event_target_order: Mapping[str, Any] | None) -> dict[str, Any]:
    """Execute a frozen tier-nine condition plan without adding a Weather phase."""
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("status") != "resolved" or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn":
        return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state")
    source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None:
        return _result("rejected", "invalid_pre_end_of_turn_branch")
    state = deepcopy(dict(source))
    phase = _apply_condition_phase(state=state, source_snapshot_fingerprint=pre_end_of_turn.get("source_snapshot_fingerprint"), projection=condition_event_target_order)
    if phase.get("status") != "resolved":
        return phase
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": phase["trace"], "next_state": state, "boundary": {"phase": "end_of_turn"}, "ordering": phase["ordering"], "limitations": ["condition_target_order_projection_required", "no_reducer_or_runtime_writeback"]}


def project_cross_owner_leftovers_end_of_turn(*, pre_end_of_turn: Mapping[str, Any], leftovers_event_target_order: Mapping[str, Any] | None, condition_event_target_order: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Execute tier-five Leftovers then the existing tier-nine condition phase."""
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("status") != "resolved" or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn":
        return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state")
    source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None:
        return _result("rejected", "invalid_pre_end_of_turn_branch")
    state = deepcopy(dict(source))
    leftovers = _apply_item_residual_phase(state=state, projection=leftovers_event_target_order)
    if leftovers.get("status") != "resolved":
        return leftovers
    condition = _apply_condition_phase(state=state, source_snapshot_fingerprint=pre_end_of_turn.get("source_snapshot_fingerprint"), projection=condition_event_target_order)
    if condition.get("status") != "resolved":
        return condition
    trace = [{"sequence": index + 1, **row} for index, row in enumerate([*leftovers["trace"], *condition["trace"]])]
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "ordering": {"leftovers_target_order": leftovers["ordering"]["leftovers_target_order"], "condition_target_order": condition["ordering"]["condition_target_order"], "tiers": [5, 9]}, "limitations": ["cross_owner_leftovers_order_unrepresented", "cross_owner_condition_order_unrepresented", "no_reducer_or_runtime_writeback"]}


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


def _apply_condition_phase(*, state: dict[str, Any], source_snapshot_fingerprint: Any, projection: Mapping[str, Any] | None) -> dict[str, Any]:
    """Apply one or a frozen cross-owner set of exact tier-nine conditions."""
    source_fp = fingerprint_transition_preview_state(state)
    owners = _owners(state)
    if source_fp is None or owners is None:
        return _result("rejected", "invalid_pre_condition_branch")
    material: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        condition = _condition(state, side, source_snapshot_fingerprint, source_fp)
        if isinstance(condition, Mapping):
            return dict(condition)
        if condition in {"poison", "toxic"} and not state["active"][side]["fainted"]:
            material.append(deepcopy(owners[side]))
    if len(material) <= 1:
        plan = material
        frozen = None
    else:
        validated = validate_condition_event_target_order(branch_state=state, source_branch_fingerprint=source_fp, material_owners=material, projection=projection)
        if validated.get("status") != "resolved":
            return validated
        frozen = validated["frozen_condition_event_plan"]
        plan = frozen["ordered_active_owners"]
    trace: list[dict[str, Any]] = []
    for planned_owner in plan:
        side = _exact_owner_side(planned_owner, owners)
        if side is None:
            return _result("rejected", "stale_or_foreign_condition_event_target")
        consumed = fingerprint_transition_preview_state(state)
        if consumed is None:
            return _result("rejected", "invalid_condition_event_branch_generation")
        if state["active"][side]["fainted"]:
            trace.append({"tier": 9, "effect": "condition_event", "owner": deepcopy(planned_owner), "branch_fingerprint_consumed": consumed, "execution_status": "skipped", "reason": "fainted_before_condition_event"})
            continue
        result = apply_owner_condition_end_of_turn(state=state, side=side, source_snapshot_fingerprint=source_snapshot_fingerprint, source_branch_fingerprint=consumed)
        if result.get("status") != "resolved":
            return result
        if isinstance(result.get("trace"), Mapping):
            row = deepcopy(result["trace"])
            family = "poison_heal_compound" if row["effect"] == "poison_heal_recovery" else row["condition"]
            trace.append({"tier": _ordering_metadata()["families"][family]["tier"], "branch_fingerprint_consumed": consumed, **row})
    return {"status": "resolved", "trace": trace, "ordering": {"condition_target_order": deepcopy(frozen) if frozen else "single_owner", "tier": 9}}


def _apply_item_residual_phase(*, state: dict[str, Any], projection: Mapping[str, Any] | None) -> dict[str, Any]:
    """Apply supported canonical tier-five item residuals from one frozen plan."""
    source_fp = fingerprint_transition_preview_state(state)
    owners = _owners(state)
    if source_fp is None or owners is None:
        return _result("rejected", "invalid_pre_item_residual_branch")
    material: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        item = _item(state, side)
        if item is _UNKNOWN:
            return _result("incomplete", "item_residual_current_item_authority")
        if item in {"leftovers", "black-sludge"} and not state["active"][side]["fainted"]:
            material.append(deepcopy(owners[side]))
    if len(material) <= 1:
        plan, frozen = material, None
    else:
        validated = validate_item_residual_target_order(branch_state=state, source_branch_fingerprint=source_fp, material_owners=material, projection=projection)
        if validated.get("status") != "resolved":
            return validated
        frozen = validated["frozen_item_residual_plan"]
        plan = frozen["ordered_active_owners"]
    trace: list[dict[str, Any]] = []
    for planned_owner in plan:
        side = _exact_owner_side(planned_owner, owners)
        if side is None:
            return _result("rejected", "stale_or_foreign_item_residual_target")
        consumed = fingerprint_transition_preview_state(state)
        if consumed is None:
            return _result("rejected", "invalid_item_residual_branch_generation")
        if state["active"][side]["fainted"]:
            trace.append({"tier": 5, "effect": "item_residual_event", "owner": deepcopy(planned_owner), "branch_fingerprint_consumed": consumed, "execution_status": "skipped", "reason": "fainted_before_item_residual_event"})
            continue
        item = _item(state, side)
        adapter = apply_owner_leftovers_end_of_turn if item == "leftovers" else apply_owner_black_sludge_end_of_turn if item == "black-sludge" else None
        if adapter is None:
            return _result("rejected", "unsupported_item_residual_owner")
        result = adapter(state=state, side=side, owner=planned_owner, source_branch_fingerprint=consumed)
        if result.get("status") != "resolved":
            return result
        trace.append({"tier": 5, "branch_fingerprint_consumed": consumed, **result["trace"]})
    return {"status": "resolved", "trace": trace, "ordering": {"leftovers_target_order": deepcopy(frozen) if frozen else "single_owner", "tier": 5}}


def _apply_aqua_ring_phase(*, state: dict[str, Any], projection: Mapping[str, Any] | None) -> dict[str, Any]:
    """Apply only typed Aqua Ring tier-six authority, never inferred absence."""
    if "aqua_ring_persistent_effect_context" not in state:
        return {"status": "resolved", "trace": [], "ordering": {"aqua_ring_target_order": "not_material", "tier": 6}}
    source_fp, owners = fingerprint_transition_preview_state(state), _owners(state)
    if source_fp is None or owners is None: return _result("rejected", "invalid_pre_aqua_ring_branch")
    material = []
    for side in ("self", "opponent"):
        status = aqua_ring_state(state, side, owners[side])
        if status is None: return _result("rejected", "stale_or_invalid_aqua_ring_authority")
        if status == "unknown": return _result("incomplete", "aqua_ring_persistent_effect_unknown")
        if status == "known_active" and not state["active"][side]["fainted"]: material.append(deepcopy(owners[side]))
    if len(material) <= 1: plan, frozen = material, None
    else:
        validated = validate_aqua_ring_target_order(branch_state=state, source_branch_fingerprint=source_fp, material_owners=material, projection=projection)
        if validated.get("status") != "resolved": return validated
        frozen = validated["frozen_aqua_ring_plan"]; plan = frozen["ordered_active_owners"]
    trace=[]
    for owner in plan:
        side = _exact_owner_side(owner, owners); consumed=fingerprint_transition_preview_state(state)
        if side is None or consumed is None: return _result("rejected", "stale_or_foreign_aqua_ring_owner")
        if state["active"][side]["fainted"]: continue
        result=apply_owner_aqua_ring_end_of_turn(state=state, side=side, owner=owner, source_branch_fingerprint=consumed)
        if result.get("status") != "resolved": return result
        if result.get("trace") is not None: trace.append({"tier":6,"branch_fingerprint_consumed":consumed,**result["trace"]})
    return {"status":"resolved","trace":trace,"ordering":{"aqua_ring_target_order":deepcopy(frozen) if frozen else "single_owner","tier":6}}


def _apply_ingrain_phase(*, state: dict[str, Any], projection: Mapping[str, Any] | None) -> dict[str, Any]:
    """Apply only typed Ingrain tier-seven authority, never inferred absence."""
    if "ingrain_persistent_effect_context" not in state:
        return {"status": "resolved", "trace": [], "ordering": {"ingrain_target_order": "not_material", "tier": 7}}
    source_fp, owners = fingerprint_transition_preview_state(state), _owners(state)
    if source_fp is None or owners is None: return _result("rejected", "invalid_pre_ingrain_branch")
    material = []
    for side in ("self", "opponent"):
        status = ingrain_state(state, side, owners[side])
        if status is None: return _result("rejected", "stale_or_invalid_ingrain_authority")
        if status == "unknown": return _result("incomplete", "ingrain_persistent_effect_unknown")
        if status == "known_active" and not state["active"][side]["fainted"]: material.append(deepcopy(owners[side]))
    if len(material) <= 1: plan, frozen = material, None
    else:
        validated = validate_ingrain_target_order(branch_state=state, source_branch_fingerprint=source_fp, material_owners=material, projection=projection)
        if validated.get("status") != "resolved": return validated
        frozen = validated["frozen_ingrain_plan"]; plan = frozen["ordered_active_owners"]
    trace=[]
    for owner in plan:
        side = _exact_owner_side(owner, owners); consumed=fingerprint_transition_preview_state(state)
        if side is None or consumed is None: return _result("rejected", "stale_or_foreign_ingrain_owner")
        if state["active"][side]["fainted"]: continue
        result=apply_owner_ingrain_end_of_turn(state=state, side=side, owner=owner, source_branch_fingerprint=consumed)
        if result.get("status") != "resolved": return result
        if result.get("trace") is not None: trace.append({"tier":7,"branch_fingerprint_consumed":consumed,**result["trace"]})
    return {"status":"resolved","trace":trace,"ordering":{"ingrain_target_order":deepcopy(frozen) if frozen else "single_owner","tier":7}}


def _apply_leech_seed_phase(*, state: dict[str, Any], projection: Mapping[str, Any] | None) -> dict[str, Any]:
    if "leech_seed_persistent_effect_context" not in state:return {"status":"resolved","trace":[],"ordering":{"leech_seed_target_order":"not_material","tier":8}}
    source_fp,owners=fingerprint_transition_preview_state(state),_owners(state)
    if source_fp is None or owners is None:return _result("rejected","invalid_pre_leech_seed_branch")
    material=[]
    for side in ("self","opponent"):
        seed=leech_seed_state(state,side,owners[side])
        if seed is None:return _result("rejected","stale_or_invalid_leech_seed_authority")
        if seed["state"]=="unknown":return _result("incomplete","leech_seed_persistent_effect_unknown")
        if seed["state"]=="known_active" and not state["active"][side]["fainted"]:material.append(deepcopy(owners[side]))
    if len(material)<=1:plan,frozen=material,None
    else:
        validated=validate_leech_seed_target_order(branch_state=state,source_branch_fingerprint=source_fp,material_owners=material,projection=projection)
        if validated.get("status")!="resolved":return validated
        frozen=validated["frozen_leech_seed_plan"];plan=frozen["ordered_active_owners"]
    trace=[]
    for owner in plan:
        side=_exact_owner_side(owner,owners); consumed=fingerprint_transition_preview_state(state)
        if side is None or consumed is None:return _result("rejected","stale_or_foreign_leech_seed_owner")
        if state["active"][side]["fainted"]:continue
        result=apply_owner_leech_seed_end_of_turn(state=state,side=side,owner=owner,source_branch_fingerprint=consumed)
        if result.get("status")!="resolved":return result
        if result.get("trace") is not None:trace.append({"tier":8,"branch_fingerprint_consumed":consumed,**result["trace"]})
    return {"status":"resolved","trace":trace,"ordering":{"leech_seed_target_order":deepcopy(frozen) if frozen else "single_owner","tier":8}}


def _exact_owner_side(owner: Mapping[str, Any] | None, owners: Mapping[str, Mapping[str, Any]]) -> str | None:
    if not isinstance(owner, Mapping):
        return None
    return next((side for side, exact in owners.items() if dict(owner) == dict(exact)), None)


def _ordering_metadata() -> dict[str, Any] | None:
    try:
        data = json.loads(_ORDERING_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    expected = {"weather": 1, "leftovers": 5, "black_sludge": 5, "aqua_ring": 6, "ingrain": 7, "leech_seed": 8, "poison": 9, "toxic": 9, "poison_heal_compound": 9}
    families = data.get("families") if isinstance(data, Mapping) else None
    if data.get("schema_version") != "detached-eot-ordering-v1" or not isinstance(families, Mapping) or any(not isinstance(families.get(name), Mapping) or families[name].get("tier") != tier for name, tier in expected.items()):
        return None
    return data


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
