"""Pure v14.1 design contracts; no evaluation or provider orchestration."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from copy import deepcopy
from decimal import Decimal
import math
import re

from llm.advisor_battle_state_context import (
    build_deterministic_calculation_context,
    normalize_user_confirmed_current_condition,
    normalize_user_confirmed_current_field_state,
    normalize_user_confirmed_current_stat_stage,
    normalize_user_confirmed_final_battle_stat,
    normalize_user_confirmed_current_ability,
    normalize_user_confirmed_current_hp,
)
from llm.advisor_turn_snapshot import (
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
    build_snapshot_trusted_level_provenance,
    build_request_start_recommendation_snapshot,
    snapshot_deterministic_context,
)
from llm.advisor_q12_snapshot_adapter import invoke_existing_q12_from_snapshot
from llm.advisor_direct_mechanics import NATIVE_DIRECT_MECHANICS_SOURCES, evaluate_direct_damage_mechanics
from llm.narrow_action_order import evaluate_action_order
from llm.move_consequence_evidence import evaluate_move_consequence_evidence

CANDIDATE_STATUSES = frozenset({"resolved", "partial", "unavailable"})
RECOMMENDATION_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate", "validation_failed"})

def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    required = {"move", "status", "availability", "self_effects", "dynamic_move", "warnings", "unavailable_reasons"}
    if not required <= set(candidate) or not isinstance(candidate.get("move"), str) or candidate.get("status") not in CANDIDATE_STATUSES:
        raise ValueError("invalid candidate schema")
    if not all(isinstance(candidate[key], list) for key in ("self_effects", "warnings", "unavailable_reasons")):
        raise ValueError("invalid candidate collections")
    return deepcopy(dict(candidate))

def build_evidence_bundle(snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], limitations: Sequence[str]) -> dict[str, Any]:
    normalized = [validate_candidate(candidate) for candidate in candidates]
    return {"battle_snapshot_summary": deepcopy(dict(snapshot)), "candidates": normalized, "comparison_policy": {"allow_partial_candidates": True, "no_untrusted_inference": True, "preserve_slot_order": True}, "known_limitations": list(limitations)}

def validate_recommendation(response: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status = response.get("recommendation_status")
    if status not in RECOMMENDATION_STATUSES: raise ValueError("invalid recommendation status")
    moves = {candidate["move"] for candidate in candidates}
    move = response.get("recommended_move")
    if status == "resolved" and (not isinstance(move, str) or move not in moves): raise ValueError("recommendation outside candidate exact-set")
    if any(key not in response or not isinstance(response[key], list) for key in ("primary_reasons", "risks", "alternatives")): raise ValueError("invalid recommendation evidence")
    return dict(response)

def _metadata_value(metadata: Any, name: str) -> Any:
    return metadata.get(name) if isinstance(metadata, Mapping) else getattr(metadata, name, None)


def _selected_move_from_metadata(move: str, metadata: Any) -> dict[str, Any]:
    fields = ("category", "power", "type", "accuracy", "always_hit", "priority", "drain", "min_hits", "max_hits", "healing", "target", "effect_category", "ailment", "stat_changes")
    selected = {"move_id": _metadata_value(metadata, "move_id") or move}
    selected.update({field: _metadata_value(metadata, field) for field in fields if _metadata_value(metadata, field) is not None})
    return selected


def _accuracy_stage_context(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    """Resolve only explicit request-start Accuracy/Evasion stage authority."""
    context = snapshot.get("stat_stage_context")
    if not isinstance(context, Mapping):
        return None
    entries = context.get("current_stages")
    if not isinstance(entries, list):
        return {"status": "unsupported_mechanic", "unsupported_reason": "accuracy_stage_context"}
    resolved: dict[tuple[str, str], int] = {}
    for entry in entries:
        try:
            normalized = normalize_user_confirmed_current_stat_stage(
                {key: value for key, value in entry.items() if key != "provenance"}
            )
        except (ValueError, AttributeError):
            return {"status": "unsupported_mechanic", "unsupported_reason": "accuracy_stage_context"}
        key = (normalized["side"], normalized["stat"])
        if key in resolved:
            return {"status": "unsupported_mechanic", "unsupported_reason": "accuracy_stage_context"}
        resolved[key] = normalized["stage"]
    missing = [
        label
        for side, stat, label in (("self", "accuracy", "self_accuracy_stage"), ("opponent", "evasion", "opponent_evasion_stage"))
        if (side, stat) not in resolved
    ]
    if missing:
        return {"status": "insufficient_context", "missing_inputs": missing}
    return {
        "status": "known",
        "self_accuracy_stage": resolved[("self", "accuracy")],
        "opponent_evasion_stage": resolved[("opponent", "evasion")],
    }


def _accuracy_evidence(metadata: Any, snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Expose canonical move accuracy, applying only explicit stage authority."""
    if _metadata_value(metadata, "always_hit") is True:
        return {"status": "always_hits", "canonical_accuracy": None, "outcome": "always_hits", "uncertainty": []}
    accuracy = _metadata_value(metadata, "accuracy")
    if isinstance(accuracy, (int, float)) and not isinstance(accuracy, bool) and 1 <= accuracy <= 100:
        stage_context = _accuracy_stage_context(snapshot) if isinstance(snapshot, Mapping) and isinstance(snapshot.get("stat_stage_context"), Mapping) else None
        if isinstance(stage_context, Mapping) and stage_context.get("status") != "known":
            if stage_context.get("status") == "insufficient_context":
                return {"status": "insufficient_context", "canonical_accuracy": accuracy, "outcome": None, "uncertainty": stage_context["missing_inputs"]}
            return {"status": "unsupported_mechanic", "canonical_accuracy": accuracy, "outcome": None, "unsupported_reason": stage_context.get("unsupported_reason")}
        if isinstance(stage_context, Mapping):
            accuracy_stage, evasion_stage = stage_context["self_accuracy_stage"], stage_context["opponent_evasion_stage"]
            net_stage = max(-6, min(6, accuracy_stage - evasion_stage))
            numerator, denominator = (3 + net_stage, 3) if net_stage >= 0 else (3, 3 - net_stage)
            adjusted = min(100, int(Decimal(str(accuracy)) * numerator // denominator))
            return {
                "status": "known_accuracy", "canonical_accuracy": accuracy, "adjusted_accuracy": adjusted,
                "outcome": "stage_adjusted_accuracy", "uncertainty": [],
                "accuracy_stage_evidence": {
                    "self_accuracy_stage": accuracy_stage, "opponent_evasion_stage": evasion_stage,
                    "accuracy_stage_adjustment_applied": True, "resolved_accuracy_basis": "canonical_accuracy_and_stages",
                },
            }
        return {"status": "known_accuracy", "canonical_accuracy": accuracy, "outcome": "canonical_accuracy_only", "uncertainty": []}
    if _metadata_value(metadata, "accuracy_mechanic") is not None or _metadata_value(metadata, "dynamic_accuracy") is True:
        return {"status": "unsupported_mechanic", "canonical_accuracy": None, "outcome": None, "unsupported_reason": "dynamic_accuracy_mechanic"}
    return {"status": "insufficient_context", "canonical_accuracy": None, "outcome": None, "uncertainty": ["canonical_accuracy_missing"]}


_SELF_TARGETS = frozenset({"user", "users-field", "user-and-allies", "user-or-ally"})
_TARGETED_OPPONENT_TARGETS = frozenset({"selected-pokemon", "all-opponents", "all-other-pokemon", "opponents-field"})


def _canonical_stat_changes(metadata: Any) -> tuple[tuple[str, int], ...] | None:
    value = _metadata_value(metadata, "stat_changes")
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        return None
    changes: list[tuple[str, int]] = []
    for item in value:
        if isinstance(item, Mapping):
            stat, change = item.get("stat"), item.get("change")
        elif isinstance(item, tuple) and len(item) == 2:
            stat, change = item
        else:
            return None
        if not isinstance(stat, str) or not stat or not isinstance(change, int) or isinstance(change, bool) or change == 0:
            return None
        changes.append((stat, change))
    return tuple(changes)


def _status_move_evidence(metadata: Any) -> dict[str, Any]:
    """Classify only canonical status-move metadata; never infer utility."""
    if _metadata_value(metadata, "category") != "status":
        return {"status": "not_applicable", "role_tags": [], "canonical_effect_tags": [], "target_scope": None, "uncertainty": []}
    target = _metadata_value(metadata, "target")
    effect_category = _metadata_value(metadata, "effect_category")
    ailment = _metadata_value(metadata, "ailment")
    changes = _canonical_stat_changes(metadata)
    if changes is None:
        return {"status": "unsupported_mechanic", "role_tags": [], "canonical_effect_tags": [], "target_scope": target if isinstance(target, str) else None, "unsupported_reason": "invalid_canonical_stat_changes"}
    if not isinstance(target, str) or not target:
        return {"status": "insufficient_context", "role_tags": [], "canonical_effect_tags": [], "target_scope": None, "uncertainty": ["canonical_target_missing"]}
    roles: list[str] = []
    effect_tags: list[str] = []
    healing = _metadata_value(metadata, "healing")
    if isinstance(healing, int) and not isinstance(healing, bool) and healing > 0:
        roles.append("recovery")
        effect_tags.append("canonical_healing")
    if changes:
        effect_tags.append("canonical_stat_change")
        if target in _SELF_TARGETS and any(change > 0 for _stat, change in changes):
            roles.append("self_stat_raise")
        if target in _TARGETED_OPPONENT_TARGETS and any(change < 0 for _stat, change in changes):
            roles.append("target_stat_lower")
    if isinstance(ailment, str) and ailment not in {"none", "unknown"}:
        roles.append("status_infliction")
        effect_tags.append("canonical_ailment")
    if isinstance(effect_category, str) and effect_category:
        effect_tags.append("canonical_effect_category")
    if roles:
        return {"status": "known_role", "role_tags": roles, "canonical_effect_tags": effect_tags, "target_scope": target, "uncertainty": []}
    if isinstance(effect_category, str) and effect_category:
        return {"status": "known_role", "role_tags": ["utility_or_other"], "canonical_effect_tags": effect_tags, "target_scope": target, "uncertainty": []}
    return {"status": "insufficient_context", "role_tags": [], "canonical_effect_tags": effect_tags, "target_scope": target, "uncertainty": ["canonical_effect_metadata_missing"]}


def _dynamic_summary(context: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(context, Mapping):
        return None
    key = next((name for name in context if isinstance(name, str) and name.endswith("_power_assessment") or name == "environment_based_move_assessment"), None)
    if key is None or not isinstance(context.get(key), Mapping):
        return None
    assessment = context[key]
    family = key.removesuffix("_assessment")
    resolved = assessment.get("status") == "resolved"
    return {
        "family": family,
        "assessment_key": key,
        "status": assessment.get("status", "unavailable"),
        "effective_power": assessment.get("effective_power") if resolved else None,
        "effective_type": assessment.get("effective_type") if resolved and family == "environment_based_move" else None,
    }


def _damage_summary(context: Mapping[str, Any] | None) -> dict[str, Any]:
    estimates = context.get("damage_estimates") if isinstance(context, Mapping) else None
    estimate = estimates[0] if isinstance(estimates, list) and estimates and isinstance(estimates[0], Mapping) else None
    if not isinstance(estimate, Mapping) or estimate.get("calculation_status") != "resolved":
        reason = estimate.get("reason") if isinstance(estimate, Mapping) and isinstance(estimate.get("reason"), str) else "deterministic_damage_unavailable"
        return {"status": "unavailable", "reason": reason}
    summary = {"status": "resolved", "minimum": estimate["min_damage"], "maximum": estimate["max_damage"]}
    hp = context.get("hp_assessments") if isinstance(context, Mapping) else None
    if isinstance(hp, list) and hp and isinstance(hp[0], Mapping) and isinstance(hp[0].get("two_hit_ko"), Mapping):
        summary["ko"] = hp[0]["two_hit_ko"].get("status")
    return summary


def _optional_outputs(context: Mapping[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if not isinstance(context, Mapping):
        return {}, [], []
    outputs: dict[str, Any] = {}
    reasons: list[str] = []
    for source, target, fields in (
        ("hit_chance_assessment", "hit_chance", ("hit_chance_percent", "result", "reason")),
        ("move_order_assessment", "move_order", ("result", "reason")),
    ):
        assessment = context.get(source)
        if isinstance(assessment, Mapping):
            status = assessment.get("calculation_status", assessment.get("status", "unavailable"))
            outputs[target] = {"status": status, **{field: assessment[field] for field in fields if field in assessment}}
            if status == "unavailable" and isinstance(assessment.get("reason"), str):
                reasons.append(assessment["reason"])
    self_effects = []
    for source in ("direct_healing_assessment", "drain_recoil_assessment", "self_consequence_assessment"):
        assessment = context.get(source)
        if isinstance(assessment, Mapping):
            status = assessment.get("calculation_status", assessment.get("status", "unavailable"))
            self_effects.append({"kind": source.removesuffix("_assessment"), "status": status, **{key: deepcopy(assessment[key]) for key in ("effect", "reason") if key in assessment}})
            if status == "unavailable" and isinstance(assessment.get("reason"), str):
                reasons.append(assessment["reason"])
    return outputs, self_effects, reasons


def _production_context(snapshot: Mapping[str, Any], selected_move: Mapping[str, Any]) -> dict[str, Any] | None:
    # Legacy deterministic helpers predate canonical provenance fields.  Feed
    # them a detached value-only view while Q12 continues to consume the frozen
    # provenance-aware snapshot separately.
    context = _without_internal_provenance(snapshot)
    return build_deterministic_calculation_context(
        context.get("final_stat_context"), context.get("stat_stage_context"), selected_move,
        context.get("current_hp_context"), context.get("pokemon"), context.get("condition_context"),
        context.get("field_state_context"), context.get("battle_format_context"), None,
        context.get("attacker_level_context"), context.get("observed_previous_damage_context"),
        context.get("battle_counter_context"), context.get("consecutive_use_context"),
        context.get("weight_context"), context.get("turn_event_context"),
    )


def _without_internal_provenance(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _without_internal_provenance(item) for key, item in value.items() if key != "provenance"}
    if isinstance(value, list):
        return [_without_internal_provenance(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_without_internal_provenance(item) for item in value)
    return deepcopy(value)


def _trusted_final_speed(snapshot: Mapping[str, Any], side: str) -> int | None:
    context = snapshot.get("final_stat_context")
    entries = context.get("current_final_stats") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        try:
            normalized = normalize_user_confirmed_final_battle_stat({key: value for key, value in entry.items() if key != "provenance"})
        except ValueError:
            continue
        if normalized["side"] == side and normalized["stat"] == "speed":
            return normalized["value"]
    return None


def _known_trick_room(snapshot: Mapping[str, Any]) -> tuple[str, str]:
    context = snapshot.get("field_state_context")
    declared = context.get("trick_room") if isinstance(context, Mapping) else None
    if isinstance(declared, Mapping):
        status, provenance = declared.get("status"), declared.get("provenance")
        if status == "known_active" and provenance in {"user_confirmed_current", "trusted_observed_current"}:
            return "active", provenance
        if status == "known_inactive" and provenance in {"user_confirmed_current", "trusted_observed_current"}:
            return "inactive", provenance
        if status == "unknown" and provenance == "unknown":
            return "unknown", "unknown"
        return "unknown", "unknown"
    field = context.get("current_field") if isinstance(context, Mapping) else None
    try:
        normalized = normalize_user_confirmed_current_field_state(field)
    except ValueError:
        return "unknown", "unknown"
    return ("active" if "trick-room" in normalized["global_effects"] else "inactive"), "user_confirmed_current"


def _known_tailwind(snapshot: Mapping[str, Any]) -> tuple[tuple[str, str], tuple[str, str]]:
    context = snapshot.get("field_state_context")
    declared = context.get("tailwind") if isinstance(context, Mapping) else None
    if isinstance(declared, Mapping):
        values = []
        for side in ("self", "opponent"):
            value = declared.get(side)
            if not isinstance(value, Mapping):
                values.append(("invalid", "unknown"))
                continue
            status, provenance = value.get("status"), value.get("provenance")
            if status == "known_active" and provenance in {"user_confirmed_current", "trusted_observed_current"}:
                values.append(("active", provenance))
            elif status == "known_inactive" and provenance in {"user_confirmed_current", "trusted_observed_current"}:
                values.append(("inactive", provenance))
            elif status == "unknown" and provenance == "unknown":
                values.append(("unknown", "unknown"))
            else:
                values.append(("invalid", "unknown"))
        return values[0], values[1]
    field = context.get("current_field") if isinstance(context, Mapping) else None
    try:
        normalized = normalize_user_confirmed_current_field_state(field)
    except ValueError:
        return ("unknown", "unknown"), ("unknown", "unknown")
    effects = {(entry["side"], entry["effect"]) for entry in normalized["side_effects"]}
    return (
        ("active" if ("self", "tailwind") in effects else "inactive", "user_confirmed_current"),
        ("active" if ("opponent", "tailwind") in effects else "inactive", "user_confirmed_current"),
    )


def _known_paralysis(snapshot: Mapping[str, Any]) -> tuple[tuple[str, str], tuple[str, str]]:
    context = snapshot.get("condition_context")
    declared = context.get("paralysis") if isinstance(context, Mapping) else None
    if isinstance(declared, Mapping):
        values = []
        for side in ("self", "opponent"):
            value = declared.get(side)
            if not isinstance(value, Mapping):
                values.append(("invalid", "unknown"))
                continue
            status, provenance = value.get("status"), value.get("provenance")
            if status == "known_paralyzed" and provenance in {"user_confirmed_current", "trusted_observed_current"}:
                values.append(("paralyzed", provenance))
            elif status == "known_not_paralyzed" and provenance in {"user_confirmed_current", "trusted_observed_current"}:
                values.append(("not_paralyzed", provenance))
            elif status == "unknown" and provenance == "unknown":
                values.append(("unknown", "unknown"))
            else:
                values.append(("invalid", "unknown"))
        return values[0], values[1]
    entries = context.get("current_conditions") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return ("unknown", "unknown"), ("unknown", "unknown")
    values = []
    for side in ("self", "opponent"):
        matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == side]
        if len(matches) == 0:
            values.append(("unknown", "unknown"))
            continue
        if len(matches) != 1:
            values.append(("invalid", "unknown"))
            continue
        try:
            condition = normalize_user_confirmed_current_condition(matches[0])
        except ValueError:
            values.append(("invalid", "unknown"))
            continue
        if condition["condition_type"] == "unknown":
            values.append(("unknown", "unknown"))
        elif condition["condition_type"] == "paralysis":
            values.append(("paralyzed", "user_confirmed_current"))
        else:
            values.append(("not_paralyzed", "user_confirmed_current"))
    return values[0], values[1]


def _has_quick_feet(snapshot: Mapping[str, Any], side: str) -> bool:
    context = snapshot.get("ability_context")
    entries = context.get("current_abilities") if isinstance(context, Mapping) else None
    return isinstance(entries, list) and any(isinstance(entry, Mapping) and entry.get("side") == side and entry.get("ability") == "quick-feet" for entry in entries)


def _known_speed_item(snapshot: Mapping[str, Any], side: str) -> str:
    profiles = snapshot.get("item_profiles")
    profile = profiles.get("my_active" if side == "self" else "opponent_active") if isinstance(profiles, Mapping) else None
    if not isinstance(profile, Mapping): return "unknown"
    status, source, item_id = profile.get("status"), profile.get("source"), profile.get("item_id")
    if status in {"none", "absent"} and source == "user_input": return "none"
    if status != "user_confirmed" or source != "user_input": return "unknown" if status in {None, "unknown", "system_default_none"} else "invalid"
    return item_id if isinstance(item_id, str) and item_id else "invalid"


def _known_speed_ability(snapshot: Mapping[str, Any], side: str) -> str:
    context = snapshot.get("ability_context"); entries = context.get("current_abilities") if isinstance(context, Mapping) else None
    if not isinstance(entries, list): return "unknown"
    matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == side]
    if len(matches) != 1: return "unknown" if not matches else "invalid"
    if matches[0].get("ability") == "quick-feet": return "quick-feet"
    try: return normalize_user_confirmed_current_ability({key: value for key, value in matches[0].items() if key != "provenance"})["ability"]
    except ValueError: return "invalid"


def _known_full_hp(snapshot: Mapping[str, Any], side: str) -> str:
    """Classify only exact, request-start HP authority for Gale Wings."""
    context = snapshot.get("current_hp_context")
    entries = context.get("current_hp") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return "unknown"
    matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == side]
    if len(matches) != 1:
        return "unknown" if not matches else "invalid"
    entry = matches[0]
    provenance = entry.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("source") != "user_confirmed_current_hp" or provenance.get("trust") != "user_confirmed_current":
        return "invalid"
    try:
        normalized = normalize_user_confirmed_current_hp({key: value for key, value in entry.items() if key != "provenance"})
    except ValueError:
        return "invalid"
    current, maximum = normalized["current_hp"], normalized["maximum_hp"]
    return "full" if current > 0 and current == maximum else "not_full"


def _known_speed_weather(snapshot: Mapping[str, Any]) -> str:
    context = snapshot.get("field_state_context"); field = context.get("current_field") if isinstance(context, Mapping) else None
    try: weather = normalize_user_confirmed_current_field_state(field)["weather"]
    except ValueError: return "unknown"
    return "sand" if weather == "sandstorm" else weather


def _trusted_speed_stage(snapshot: Mapping[str, Any], side: str) -> int | None:
    context = snapshot.get("stat_stage_context")
    entries = context.get("current_stages") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return None
    found = []
    for entry in entries:
        try:
            value = normalize_user_confirmed_current_stat_stage({key: item for key, item in entry.items() if key != "provenance"})
        except (ValueError, AttributeError):
            return None
        if value["side"] == side and value["stat"] == "speed": found.append(value["stage"])
    return found[0] if len(found) == 1 else None


def _triage_healing_eligibility(metadata: Any) -> str:
    """Classify Triage only from canonical numeric healing/drain metadata."""
    healing, drain = _metadata_value(metadata, "healing"), _metadata_value(metadata, "drain")
    values = (healing, drain)
    if (healing is not None and (isinstance(healing, bool) or not isinstance(healing, int) or not 0 <= healing <= 100)) or (drain is not None and (isinstance(drain, bool) or not isinstance(drain, int) or not -100 <= drain <= 100)):
        return "invalid"
    if isinstance(healing, int) and isinstance(drain, int) and healing > 0 and drain != 0:
        return "invalid"
    if any(isinstance(value, int) and value > 0 for value in values):
        return "eligible"
    if all(isinstance(value, int) for value in values):
        return "non_eligible"
    return "unknown"


def _canonical_opponent_action(snapshot: Mapping[str, Any], repositories: Any) -> dict[str, Any] | None:
    selected = snapshot.get("opponent_selected_move")
    move_id = selected.get("move_id") if isinstance(selected, Mapping) else None
    if not isinstance(move_id, str) or not move_id:
        return None
    try:
        metadata = repositories.get(move_id) if hasattr(repositories, "get") else repositories[move_id]
    except Exception:
        return {"move_id": move_id}
    return {"move_id": move_id, "priority": _metadata_value(metadata, "priority"), "category": _metadata_value(metadata, "category"), "type": _metadata_value(metadata, "type"), "triage_healing": _triage_healing_eligibility(metadata)}


def _action_order_evidence(snapshot: Mapping[str, Any], *, move: str, metadata: Any, repositories: Any) -> dict[str, Any]:
    trick_room, trick_room_provenance = _known_trick_room(snapshot)
    (self_tailwind, self_tailwind_provenance), (opponent_tailwind, opponent_tailwind_provenance) = _known_tailwind(snapshot)
    (self_paralysis, self_paralysis_provenance), (opponent_paralysis, opponent_paralysis_provenance) = _known_paralysis(snapshot)
    kwargs = {
        "self_action": {"move_id": move, "priority": _metadata_value(metadata, "priority"), "category": _metadata_value(metadata, "category"), "type": _metadata_value(metadata, "type"), "triage_healing": _triage_healing_eligibility(metadata)},
        "opponent_action": _canonical_opponent_action(snapshot, repositories),
        "self_final_speed": _trusted_final_speed(snapshot, "self"),
        "opponent_final_speed": _trusted_final_speed(snapshot, "opponent"),
        "trick_room": trick_room,
        "trick_room_provenance": trick_room_provenance,
        "self_tailwind": self_tailwind,
        "opponent_tailwind": opponent_tailwind,
        "self_tailwind_provenance": self_tailwind_provenance,
        "opponent_tailwind_provenance": opponent_tailwind_provenance,
        "self_paralysis": self_paralysis,
        "opponent_paralysis": opponent_paralysis,
        "self_paralysis_provenance": self_paralysis_provenance,
        "opponent_paralysis_provenance": opponent_paralysis_provenance,
        "self_paralysis_speed_ability_unsupported": _has_quick_feet(snapshot, "self"),
        "opponent_paralysis_speed_ability_unsupported": _has_quick_feet(snapshot, "opponent"),
    }
    if isinstance(snapshot.get("stat_stage_context"), Mapping):
        kwargs.update(self_speed_stage=_trusted_speed_stage(snapshot, "self"), opponent_speed_stage=_trusted_speed_stage(snapshot, "opponent"))
    if isinstance(snapshot.get("item_profiles"), Mapping):
        kwargs.update(self_speed_item=_known_speed_item(snapshot, "self"), opponent_speed_item=_known_speed_item(snapshot, "opponent"))
    if isinstance(snapshot.get("ability_context"), Mapping):
        self_ability, opponent_ability = _known_speed_ability(snapshot, "self"), _known_speed_ability(snapshot, "opponent")
        kwargs.update(self_speed_ability=self_ability, opponent_speed_ability=opponent_ability, self_priority_ability=self_ability, opponent_priority_ability=opponent_ability, weather=_known_speed_weather(snapshot))
    if isinstance(snapshot.get("current_hp_context"), Mapping):
        kwargs.update(self_gale_wings_full_hp=_known_full_hp(snapshot, "self"), opponent_gale_wings_full_hp=_known_full_hp(snapshot, "opponent"))
    return evaluate_action_order(**kwargs)


def evaluate_move_candidate(*, slot_index: int, move: Any, battle_snapshot: Mapping[str, Any], repositories: Any, turn_snapshot: Any = None, selectable_moves: Sequence[str | None] | None = None, species_repository: Any = None) -> dict[str, Any]:
    """Pure v14.2 slot evaluator; isolates metadata failures per candidate."""
    if not isinstance(slot_index, int) or not 0 <= slot_index < 4: raise ValueError("invalid slot index")
    if not isinstance(move, str) or not move:
        return {"slot_index":slot_index,"move":"unknown","status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["invalid_move_identity"]}
    try:
        metadata = repositories.get(move) if hasattr(repositories, "get") else repositories[move]
    except Exception:
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["move_metadata_unavailable"]}
    if not isinstance(metadata, Mapping) and not hasattr(metadata, "category"):
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["move_metadata_unavailable"]}
    if _metadata_value(metadata, "category") == "status":
        snapshot = battle_snapshot if isinstance(battle_snapshot, Mapping) else {}
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":{"status":"not_applicable"},"q12_damage":{"status":"unavailable","limitations":["status_move_not_damaging"]},"mechanics_result":{"status":"unsupported_mechanic","unsupported_reason":"status_move"},"action_order":_action_order_evidence(snapshot, move=move, metadata=metadata, repositories=repositories),"accuracy_evidence":_accuracy_evidence(metadata, snapshot),"status_move_evidence":_status_move_evidence(metadata),"move_consequence_evidence":evaluate_move_consequence_evidence(move_id=move, metadata=metadata),"self_effects":[],"dynamic_move":None,"warnings":["unsupported_non_damage_utility_ranking"],"unavailable_reasons":[]}
    snapshot = battle_snapshot if isinstance(battle_snapshot, Mapping) else {}
    selected_move = _selected_move_from_metadata(move, metadata)
    if turn_snapshot is not None:
        try:
            damage_input = build_snapshot_damage_input(
                turn_snapshot,
                candidate_slot_index=slot_index,
                candidate_move_id=move,
                selectable_moves=selectable_moves or (),
                move_metadata=selected_move,
            )
        except ValueError:
            return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["invalid_snapshot"]}
        selected_move = deepcopy(damage_input["move"])
        q12_damage = _snapshot_q12_damage(
            turn_snapshot=turn_snapshot, damage_input=damage_input,
            species_repository=species_repository,
        )
        mechanics_result = _snapshot_direct_mechanics(
            turn_snapshot=turn_snapshot, damage_input=damage_input,
            species_repository=species_repository,
        )
    else:
        q12_damage = {"status": "unavailable", "limitations": ["snapshot_q12_unavailable"]}
        mechanics_result = {"status": "insufficient_context", "missing_inputs": ["turn_snapshot"]}
    context = _production_context(snapshot, selected_move)
    dynamic_move = _dynamic_summary(context)
    damage = _damage_summary(context)
    optional_outputs, self_effects, optional_reasons = _optional_outputs(context)
    optional_outputs["action_order"] = _action_order_evidence(snapshot, move=move, metadata=metadata, repositories=repositories)
    optional_outputs["accuracy_evidence"] = _accuracy_evidence(metadata, snapshot)
    optional_outputs["status_move_evidence"] = _status_move_evidence(metadata)
    optional_outputs["move_consequence_evidence"] = evaluate_move_consequence_evidence(move_id=move, metadata=metadata)
    if dynamic_move is not None and dynamic_move["status"] != "resolved":
        reasons = ["required_dynamic_context_unavailable"]
        assessment = context.get(dynamic_move["assessment_key"]) if isinstance(context, Mapping) else None
        if isinstance(assessment, Mapping) and isinstance(assessment.get("reason"), str): reasons.append(assessment["reason"])
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","damage":damage,"q12_damage":q12_damage,"mechanics_result":mechanics_result,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":reasons,**optional_outputs}
    if damage["status"] != "resolved":
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":damage,"q12_damage":q12_damage,"mechanics_result":mechanics_result,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":[damage["reason"], *optional_reasons],**optional_outputs}
    if optional_reasons:
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":damage,"q12_damage":q12_damage,"mechanics_result":mechanics_result,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":optional_reasons,**optional_outputs}
    return {"slot_index":slot_index,"move":move,"status":"resolved","availability":"usable","damage":damage,"q12_damage":q12_damage,"mechanics_result":mechanics_result,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":[],**optional_outputs}

def _snapshot_q12_damage(*, turn_snapshot: Any, damage_input: Mapping[str, Any], species_repository: Any) -> dict[str, Any]:
    if species_repository is None:
        return {"status": "unavailable", "limitations": ["species_repository_unavailable"]}
    try:
        provenance = build_snapshot_stat_provenance(turn_snapshot, species_repository=species_repository)
        level = build_snapshot_trusted_level_provenance(turn_snapshot)
        if level.get("available") is not True:
            return {"status": "unavailable", "limitations": [str(level.get("reason", "trusted_level_unavailable"))]}
        return invoke_existing_q12_from_snapshot(
            damage_input, stat_provenance=provenance, trusted_level=level.get("value"),
        )
    except (TypeError, ValueError):
        return {"status": "unavailable", "limitations": ["invalid_snapshot"]}


def _snapshot_direct_mechanics(*, turn_snapshot: Any, damage_input: Mapping[str, Any], species_repository: Any) -> dict[str, Any]:
    battle_context = damage_input.get("battle_context")
    current_state = battle_context.get("current_state") if isinstance(battle_context, Mapping) else None
    if not isinstance(current_state, Mapping) or not isinstance(current_state.get("direct_mechanics_context"), Mapping):
        return {"status": "not_requested"}
    if species_repository is None:
        return {"status": "insufficient_context", "missing_inputs": ["species_repository"]}
    try:
        provenance = build_snapshot_stat_provenance(turn_snapshot, species_repository=species_repository)
        level = build_snapshot_trusted_level_provenance(turn_snapshot)
        return evaluate_direct_damage_mechanics(
            damage_input, stat_provenance=provenance,
            trusted_level=level.get("value") if level.get("available") is True else None,
        )
    except (TypeError, ValueError):
        return {"status": "insufficient_context", "missing_inputs": ["snapshot"]}


def evaluate_move_slots(*, moves: Sequence[Any], battle_snapshot: Mapping[str, Any], repositories: Any, maximum_slots: int = 4, turn_snapshot: Any = None, species_repository: Any = None) -> list[dict[str, Any]]:
    if isinstance(moves, (str, bytes)) or not isinstance(moves, Sequence) or len(moves) > maximum_slots: raise ValueError("invalid move slots")
    return [evaluate_move_candidate(slot_index=index, move=move, battle_snapshot=deepcopy(dict(battle_snapshot)), repositories=repositories, turn_snapshot=turn_snapshot, selectable_moves=moves, species_repository=species_repository) for index, move in enumerate(moves) if move is not None]


_MECHANICS_COMPARISON_STATUSES = frozenset({"rankable", "insufficient_context", "unsupported_mechanic", "unavailable"})
_NATIVE_DIRECT_MECHANICS_SOURCES = NATIVE_DIRECT_MECHANICS_SOURCES


def _finite_number(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None
    return float(value)


def _known_direct_metrics(mechanics: Mapping[str, Any]) -> tuple[float, float, float, float, float, float, float] | None:
    damage = mechanics.get("damage_range")
    percent = mechanics.get("damage_percent_range")
    ko = mechanics.get("ko_result")
    if not isinstance(damage, Mapping) or not isinstance(percent, Mapping) or not isinstance(ko, Mapping):
        return None
    minimum, maximum = _finite_number(damage.get("minimum")), _finite_number(damage.get("maximum"))
    minimum_percent, maximum_percent = _finite_number(percent.get("minimum")), _finite_number(percent.get("maximum"))
    probability, effectiveness = _finite_number(ko.get("single_hit_probability")), _finite_number(mechanics.get("type_effectiveness"))
    if None in {minimum, maximum, minimum_percent, maximum_percent, probability, effectiveness}:
        return None
    assert minimum is not None and maximum is not None and minimum_percent is not None and maximum_percent is not None and probability is not None and effectiveness is not None
    if minimum < 0 or maximum < minimum or minimum_percent < 0 or maximum_percent < minimum_percent or not 0 <= probability <= 1 or effectiveness < 0:
        return None
    return minimum, maximum, minimum_percent, maximum_percent, probability, effectiveness, float(probability >= 1)


def _direct_mechanics_comparison(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[float, ...] | None] | None:
    mechanics = candidate.get("mechanics_result")
    if not isinstance(mechanics, Mapping):
        return None
    if mechanics.get("unsupported_reason") == "status_move":
        return {"comparison_status": "unsupported_mechanic", "rank": None, "comparison_reason": "status_move_not_damage_rankable"}, None
    if mechanics.get("mechanics_source") not in _NATIVE_DIRECT_MECHANICS_SOURCES:
        return None
    if candidate.get("status") == "unavailable" or candidate.get("availability") == "unavailable":
        return {"comparison_status": "unavailable", "rank": None, "comparison_reason": "candidate_unavailable"}, None
    status = mechanics.get("status")
    if status == "insufficient_context":
        return {"comparison_status": "insufficient_context", "rank": None, "comparison_reason": "mechanics_insufficient_context"}, None
    if status == "unsupported_mechanic":
        return {"comparison_status": "unsupported_mechanic", "rank": None, "comparison_reason": "mechanics_unsupported"}, None
    if status != "known":
        return {"comparison_status": "unavailable", "rank": None, "comparison_reason": "mechanics_unavailable"}, None
    metrics = _known_direct_metrics(mechanics)
    if metrics is None:
        return {"comparison_status": "unavailable", "rank": None, "comparison_reason": "mechanics_evidence_unavailable"}, None
    minimum, maximum, minimum_percent, maximum_percent, probability, effectiveness, guaranteed = metrics
    effective_action = float(effectiveness > 0 and maximum > 0)
    # The tuple is internal-only ranking evidence.  Only its resulting rank and
    # fixed reason are placed in the provider-safe comparison row.
    key = (effective_action, guaranteed, probability, minimum_percent, maximum_percent, minimum, maximum, effectiveness)
    return {"comparison_status": "rankable", "rank": None, "comparison_reason": "deterministic_known_mechanics"}, key


def rank_direct_mechanics_candidates(*, candidates: Sequence[Mapping[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    """Classify and deterministically rank native direct-mechanics candidates.

    Only a complete native direct result is rankable.  Unknown, incomplete,
    unsupported, and unavailable inputs never receive an inferred score.
    """
    comparisons: dict[tuple[int, str], dict[str, Any]] = {}
    rankable: list[tuple[tuple[float, ...], int, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        slot, move = candidate.get("slot_index"), candidate.get("move")
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(move, str) or not move:
            continue
        result = _direct_mechanics_comparison(candidate)
        if result is None:
            continue
        comparison, key = result
        comparisons[(slot, move)] = comparison
        if key is not None:
            rankable.append((key, slot, move))
    rankable.sort(key=lambda item: (*item[0], -item[1]), reverse=True)
    only_rankable = len(rankable) == 1
    for rank, (_key, slot, move) in enumerate(rankable, start=1):
        comparison = comparisons[(slot, move)]
        comparison["rank"] = rank
        if only_rankable:
            comparison["comparison_reason"] = "only_rankable_candidate"
    return comparisons


def _comparison_facts(
    *, candidate: Mapping[str, Any], comparison: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build provider-safe, candidate-local facts from existing native evidence.

    This intentionally does not contribute to ``mechanics_comparison.rank``.
    The facts describe only evidence already attached to this candidate, so an
    action-order outcome can never become a damage-ranking input.
    """
    pair = _exact_pair(candidate, exact=False)
    mechanics = candidate.get("mechanics_result")
    mechanics_status = mechanics.get("status") if isinstance(mechanics, Mapping) else "unavailable"
    action_order = candidate.get("action_order")
    action_order_status = action_order.get("status") if isinstance(action_order, Mapping) else "unavailable"
    accuracy = candidate.get("accuracy_evidence")
    status_role = candidate.get("status_move_evidence")
    consequence = candidate.get("move_consequence_evidence")
    tags: list[str] = []
    evidence_refs: list[str] = []
    if isinstance(mechanics, Mapping):
        evidence_refs.append("mechanics_result")
    if comparison.get("comparison_status") == "insufficient_context":
        tags.append("insufficient_mechanics_context")
    elif comparison.get("comparison_status") == "unsupported_mechanic":
        tags.append("unsupported_mechanic")
    metrics = _known_direct_metrics(mechanics) if isinstance(mechanics, Mapping) else None
    if metrics is not None:
        _minimum, _maximum, minimum_percent, maximum_percent, probability, effectiveness, _guaranteed = metrics
        if effectiveness == 0:
            tags.append("immune")
        if probability >= 1:
            tags.append("guaranteed_ohko")
        elif probability > 0:
            tags.append("possible_ohko")
        for other in candidates:
            if other is candidate or not isinstance(other, Mapping):
                continue
            other_mechanics = other.get("mechanics_result")
            other_metrics = _known_direct_metrics(other_mechanics) if isinstance(other_mechanics, Mapping) else None
            if other_metrics is None:
                continue
            other_minimum_percent, other_maximum_percent = other_metrics[2], other_metrics[3]
            if minimum_percent >= other_maximum_percent and maximum_percent > other_maximum_percent:
                tags.append("higher_native_damage_range")
                break
    if isinstance(action_order, Mapping):
        evidence_refs.append("action_order")
        if action_order_status == "acts_first":
            tags.append("acts_first_if_known")
        elif action_order_status == "speed_tie":
            tags.append("speed_tie")
    if isinstance(accuracy, Mapping):
        evidence_refs.append("accuracy_evidence")
        if accuracy.get("status") == "always_hits":
            tags.append("always_hits")
        elif accuracy.get("status") == "insufficient_context":
            tags.append("accuracy_unknown")
        elif accuracy.get("status") == "unsupported_mechanic":
            tags.append("accuracy_unsupported")
        elif accuracy.get("status") == "known_accuracy":
            value = _finite_number(accuracy.get("canonical_accuracy"))
            known = [
                _finite_number(other.get("accuracy_evidence", {}).get("canonical_accuracy"))
                for other in candidates if isinstance(other, Mapping) and isinstance(other.get("accuracy_evidence"), Mapping) and other.get("accuracy_evidence", {}).get("status") == "known_accuracy"
            ]
            known = [item for item in known if item is not None]
            if value is not None and len(known) >= 2:
                if value == max(known) and value > min(known): tags.append("known_higher_canonical_accuracy")
                if value == min(known) and value < max(known): tags.append("known_lower_canonical_accuracy")
    if isinstance(status_role, Mapping) and status_role.get("status") != "not_applicable":
        evidence_refs.append("status_move_evidence")
        if status_role.get("status") == "insufficient_context":
            tags.append("status_role_unknown")
        elif status_role.get("status") == "unsupported_mechanic":
            tags.append("status_role_unsupported")
        elif status_role.get("status") == "known_role":
            role_tags = status_role.get("role_tags")
            if isinstance(role_tags, list):
                if "recovery" in role_tags:
                    tags.append("known_recovery_role")
                if "protection" in role_tags:
                    tags.append("known_protection_role")
                if any(role in role_tags for role in ("self_stat_raise", "hazard_setup", "screen_setup")):
                    tags.append("known_setup_role")
                if "status_infliction" in role_tags:
                    tags.append("known_status_infliction_role")
                if any(role in role_tags for role in ("field_or_weather_setup", "hazard_removal", "switching_or_phazing")):
                    tags.append("known_field_role")
    if isinstance(consequence, Mapping):
        evidence_refs.append("move_consequence_evidence")
        if consequence.get("status") == "insufficient_context":
            tags.append("consequence_unknown")
        elif consequence.get("status") == "unsupported_mechanic":
            tags.append("consequence_unsupported")
        elif consequence.get("status") == "known" and isinstance(consequence.get("consequence_tags"), list):
            mapping = {"recoil": "known_recoil", "drain_or_healing_from_damage": "known_drain", "charge_turn": "requires_charge_turn", "recharge_turn": "requires_recharge_turn", "self_faint": "causes_self_faint", "forced_switch": "causes_forced_switch"}
            tags.extend(mapping[tag] for tag in consequence["consequence_tags"] if tag in mapping)
    return {
        "candidate_id": pair,
        "mechanics_status": mechanics_status,
        "action_order_status": action_order_status,
        "comparison_tags": tags,
        "evidence_refs": evidence_refs,
    }

_RECOMMENDATION_GUARDRAILS = {
    "select_only_from_selectable_exact_set": True,
    "do_not_modify_deterministic_evidence": True,
    "do_not_infer_opponent_moves": True,
    "do_not_infer_items_abilities_or_stats": True,
    "do_not_claim_unsupported_mechanics": True,
}
_REQUEST_READINESS = frozenset({"ready", "no_candidates", "no_selectable_candidates", "invalid_evidence_bundle"})


def _candidate_eligibility(candidate: Mapping[str, Any]) -> str:
    status, availability = candidate.get("status"), candidate.get("availability")
    if status == "resolved" and availability == "usable":
        return "eligible"
    if status == "partial" and availability in {"usable", "partially_evaluable"}:
        return "eligible_with_warnings"
    if status == "unavailable" and availability == "unavailable":
        return "not_selectable"
    raise ValueError("invalid candidate eligibility")


def _exact_pair(value: Any, *, exact: bool = True) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not {"slot_index", "move"} <= set(value) or (exact and set(value) != {"slot_index", "move"}):
        raise ValueError("invalid exact-set entry")
    if not isinstance(value["slot_index"], int) or isinstance(value["slot_index"], bool) or not 0 <= value["slot_index"] < 4:
        raise ValueError("invalid exact-set entry")
    if not isinstance(value["move"], str) or not value["move"]:
        raise ValueError("invalid exact-set entry")
    return {"slot_index": value["slot_index"], "move": value["move"]}


def _invalid_request() -> dict[str, Any]:
    request = {
        "request_version": "v14.3",
        "readiness": {"status": "invalid_evidence_bundle", "selectable_candidate_count": 0},
        "battle_snapshot_summary": {}, "candidate_exact_set": [],
        "selectable_candidate_exact_set": [], "candidate_comparisons": [],
        "known_limitations": [], "guardrails": deepcopy(_RECOMMENDATION_GUARDRAILS),
    }
    return request


def _validate_request_contract(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping) or request.get("request_version") != "v14.3":
        raise ValueError("invalid recommendation request")
    readiness = request.get("readiness")
    if not isinstance(readiness, Mapping) or readiness.get("status") not in _REQUEST_READINESS:
        raise ValueError("invalid recommendation request")
    if request.get("guardrails") != _RECOMMENDATION_GUARDRAILS:
        raise ValueError("invalid recommendation request")
    candidate_set, selectable_set, comparisons = request.get("candidate_exact_set"), request.get("selectable_candidate_exact_set"), request.get("candidate_comparisons")
    if not isinstance(candidate_set, list) or not isinstance(selectable_set, list) or not isinstance(comparisons, list):
        raise ValueError("invalid recommendation request")
    pairs = [_exact_pair(value) for value in candidate_set]
    if len({pair["slot_index"] for pair in pairs}) != len(pairs):
        raise ValueError("invalid recommendation request")
    selectable = [_exact_pair(value) for value in selectable_set]
    if any(pair not in pairs for pair in selectable) or len({pair["slot_index"] for pair in selectable}) != len(selectable):
        raise ValueError("invalid recommendation request")
    if len(comparisons) != len(pairs):
        raise ValueError("invalid recommendation request")
    expected_selectable = []
    for pair, row in zip(pairs, comparisons, strict=True):
        if not isinstance(row, Mapping) or _exact_pair(row, exact=False) != pair:
            raise ValueError("invalid recommendation request")
        eligibility = _candidate_eligibility(row)
        if row.get("eligibility") != eligibility:
            raise ValueError("invalid recommendation request")
        if eligibility != "not_selectable":
            expected_selectable.append(pair)
    if selectable != expected_selectable:
        raise ValueError("invalid recommendation request")
    expected_mechanics_comparisons = rank_direct_mechanics_candidates(candidates=comparisons)
    for row in comparisons:
        pair = _exact_pair(row, exact=False)
        expected_comparison = expected_mechanics_comparisons.get((pair["slot_index"], pair["move"]))
        if expected_comparison is None:
            if "mechanics_comparison" in row or "comparison_facts" in row:
                raise ValueError("invalid recommendation request")
        else:
            if row.get("mechanics_comparison") != expected_comparison:
                raise ValueError("invalid recommendation request")
            expected_facts = _comparison_facts(
                candidate=row, comparison=expected_comparison, candidates=comparisons,
            )
            if row.get("comparison_facts") != expected_facts:
                raise ValueError("invalid recommendation request")
    expected_status = "no_candidates" if not pairs else "ready" if selectable else "no_selectable_candidates"
    if readiness.get("status") != expected_status or readiness.get("selectable_candidate_count") != len(selectable):
        raise ValueError("invalid recommendation request")


def build_recommendation_request(*, evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence_bundle, Mapping):
        return _invalid_request()
    candidates = evidence_bundle.get("candidates")
    limitations = evidence_bundle.get("known_limitations")
    snapshot = evidence_bundle.get("battle_snapshot_summary")
    if not isinstance(candidates, list) or not isinstance(limitations, list) or not isinstance(snapshot, Mapping):
        return _invalid_request()
    try:
        comparisons = []
        pairs = []
        normalized_candidates = []
        for candidate in candidates:
            normalized = validate_candidate(candidate)
            pair = _exact_pair(normalized, exact=False)
            if pair["slot_index"] in {existing["slot_index"] for existing in pairs}:
                raise ValueError("duplicate slot index")
            eligibility = _candidate_eligibility(normalized)
            # Q12 is internal deterministic evidence.  Keep its compact result
            # on the prepared candidate while preserving the provider comparison
            # contract and never serializing a calculation input/provenance block.
            normalized_candidates.append(normalized)
            pairs.append(pair)
        ranked_mechanics = rank_direct_mechanics_candidates(candidates=normalized_candidates)
        for normalized in normalized_candidates:
            eligibility = _candidate_eligibility(normalized)
            provider_candidate = {key: value for key, value in normalized.items() if key != "q12_damage"}
            pair = _exact_pair(normalized, exact=False)
            row = {**deepcopy(provider_candidate), "eligibility": eligibility}
            comparison = ranked_mechanics.get((pair["slot_index"], pair["move"]))
            if comparison is not None:
                row["mechanics_comparison"] = comparison
                row["comparison_facts"] = _comparison_facts(
                    candidate=normalized, comparison=comparison, candidates=normalized_candidates,
                )
            comparisons.append(row)
        if not all(isinstance(item, str) for item in limitations):
            raise ValueError("invalid known limitations")
    except (TypeError, ValueError):
        return _invalid_request()
    selectable = [deepcopy(pair) for pair, row in zip(pairs, comparisons, strict=True) if row["eligibility"] != "not_selectable"]
    readiness = "no_candidates" if not pairs else "ready" if selectable else "no_selectable_candidates"
    request = {
        "request_version": "v14.3",
        "readiness": {"status": readiness, "selectable_candidate_count": len(selectable)},
        "battle_snapshot_summary": deepcopy(dict(snapshot)),
        "candidate_exact_set": deepcopy(pairs),
        "selectable_candidate_exact_set": selectable,
        "candidate_comparisons": comparisons,
        "known_limitations": deepcopy(limitations),
        "guardrails": deepcopy(_RECOMMENDATION_GUARDRAILS),
    }
    turn_snapshot = snapshot.get("turn_snapshot") if isinstance(snapshot, Mapping) else None
    current_state = turn_snapshot.get("current_state") if isinstance(turn_snapshot, Mapping) else None
    runtime = current_state.get("runtime_advice_state") if isinstance(current_state, Mapping) else None
    if isinstance(runtime, Mapping):
        request["runtime_advice_state"] = deepcopy(dict(runtime))
    return request


def validate_recommendation_selection(*, request: Mapping[str, Any], recommended_move: str, recommended_slot_index: int) -> dict[str, Any]:
    _validate_request_contract(request)
    if request["readiness"]["status"] != "ready":
        raise ValueError("request not ready")
    pair = {"move": recommended_move, "slot_index": recommended_slot_index}
    if pair not in request["selectable_candidate_exact_set"]:
        raise ValueError("selection outside selectable exact-set")
    return deepcopy(pair)


def serialize_recommendation_request(request: Mapping[str, Any]) -> dict[str, Any]:
    banned = {"apikey", "token", "accesstoken", "refreshtoken", "authorization", "credential", "credentials", "providersecret", "clientsecret", "rawresponse", "rawproviderresponse", "traceback", "stacktrace"}

    def clean(value: Any) -> Any:
        if type(value) is dict:
            result = {}
            for key, item in value.items():
                if type(key) is not str or key.lower().replace("_", "").replace("-", "") in banned:
                    raise ValueError("unsafe request field")
                result[key] = clean(item)
            return result
        if type(value) is list:
            return [clean(item) for item in value]
        if type(value) is float:
            if not math.isfinite(value):
                raise ValueError("non-json-safe value")
            return value
        if value is None or type(value) in {str, int, bool}:
            return value
        raise ValueError("non-json-safe value")

    return clean(request)


_RESPONSE_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate", "validation_failed"})
_CLAIM_KINDS = frozenset({"damage", "ko", "hit_chance", "move_order", "self_effect", "dynamic_mechanic", "partial_context", "mechanics"})
_FORBIDDEN_RESPONSE_KEYS = frozenset({
    "rawresponse", "rawproviderresponse", "traceback", "stacktrace", "apikey", "token", "authorization",
    "credential", "credentials", "providersecret", "clientsecret", "accesstoken", "refreshtoken", "rawprompt",
    "providermodel", "modeloverride", "network", "networkconfiguration", "deterministicevidence", "damagerange",
    "candidatecomparisons", "unknownmove", "opponentmove", "item", "ability", "ev", "iv",
})


def _response_failure(code: str) -> dict[str, Any]:
    return {"status": "validation_failed", "recommended_move": None, "recommended_slot_index": None,
            "primary_reasons": [], "risks": [], "alternatives": [], "errors": [code]}


def _has_forbidden_response_content(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if normalized in _FORBIDDEN_RESPONSE_KEYS or _has_forbidden_response_content(item):
                return True
    elif isinstance(value, list):
        return any(_has_forbidden_response_content(item) for item in value)
    return False


def _comparison_context_for_pair(request: Mapping[str, Any], pair: Mapping[str, Any]) -> tuple[Mapping[str, Any], str] | None:
    for index, comparison in enumerate(request.get("candidate_comparisons", [])):
        if isinstance(comparison, Mapping) and comparison.get("move") == pair["move"] and comparison.get("slot_index") == pair["slot_index"]:
            return comparison, f"candidate_comparisons.{index}.mechanics_result"
    return None


def _comparison_for_pair(request: Mapping[str, Any], pair: Mapping[str, Any]) -> Mapping[str, Any] | None:
    context = _comparison_context_for_pair(request, pair)
    return context[0] if context else None


_NUMERIC_SCOPE_VALUES = frozenset({"damage_range", "damage_percent_range", "single_hit_probability"})
_NUMERIC_LITERAL_PATTERN = re.compile(r"(?<![A-Za-z_])\d+(?:\.\d+)?")
INCOMPLETE_DIRECT_MECHANICS_CLAIM_VALUES = frozenset({
    "deterministic mechanics is incomplete",
    "missing deterministic mechanics context",
    "conditional advice requires missing mechanics context",
})
DIRECT_MECHANICS_PROVIDER_CLAIM_KINDS = frozenset({
    "damage_value", "damage_percent", "ko_probability", "value_free_mechanics", "partial_context",
})
_DIRECT_PROVIDER_NUMERIC_SCOPES = {
    "damage_value": "damage_range",
    "damage_percent": "damage_percent_range",
    "ko_probability": "single_hit_probability",
}


def _numeric_literals(claim: str) -> list[Decimal]:
    return [Decimal(value) for value in _NUMERIC_LITERAL_PATTERN.findall(claim)]


def _mechanics_scope_values(mechanics: Mapping[str, Any], scope: str) -> list[Decimal] | None:
    if scope in {"damage_range", "damage_percent_range"}:
        value = mechanics.get(scope)
        if not isinstance(value, Mapping):
            return None
        values = [value.get("minimum"), value.get("maximum")]
    elif scope == "single_hit_probability":
        ko_result = mechanics.get("ko_result")
        values = [ko_result.get("single_hit_probability")] if isinstance(ko_result, Mapping) else [None]
    else:
        return None
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        return None
    return [Decimal(str(value)) for value in values]


def _classify_claim(*, reason: Mapping[str, Any], mechanics_known: bool, mechanics_insufficient: bool, multi_mechanics_ranking: bool) -> str | None:
    """Classify direct-mechanics claims without weakening numeric evidence checks."""
    if mechanics_insufficient and reason.get("kind") == "partial_context":
        return "partial_context_claim"
    if mechanics_known and multi_mechanics_ranking and reason.get("kind") == "mechanics":
        return "numeric_mechanics_claim" if _numeric_literals(reason["claim"]) else "value_free_ranking_claim"
    if mechanics_known and _numeric_literals(reason["claim"]):
        return "numeric_mechanics_claim"
    return None


def _validate_claim(reason: Any, candidate: Mapping[str, Any], *, mechanics_path: str | None = None, multi_mechanics_ranking: bool = False) -> None:
    allowed_keys = {"kind", "claim", "mechanics_path", "numeric_scope"}
    if not isinstance(reason, Mapping) or not set(reason) <= allowed_keys or not {"kind", "claim"} <= set(reason) or not isinstance(reason.get("claim"), str) or not reason["claim"]:
        raise ValueError("invalid_claim")
    kind = reason["kind"]
    damage = candidate.get("damage")
    mechanics = candidate.get("mechanics_result")
    direct_mechanics = isinstance(mechanics, Mapping) and mechanics.get("mechanics_source") in _NATIVE_DIRECT_MECHANICS_SOURCES
    mechanics_known = direct_mechanics and mechanics.get("status") == "known" and isinstance(mechanics.get("damage_range"), Mapping)
    mechanics_insufficient = direct_mechanics and mechanics.get("status") == "insufficient_context"
    if kind not in _CLAIM_KINDS:
        raise ValueError("mechanics_claim_scope_invalid" if isinstance(mechanics, Mapping) and mechanics.get("status") != "not_requested" else "invalid_claim")
    numeric_claim = bool(_numeric_literals(reason["claim"]))
    if mechanics_insufficient:
        if kind != "partial_context":
            raise ValueError("mechanics_numeric_claim_on_insufficient_context" if numeric_claim else "mechanics_claim_on_insufficient_context")
        if numeric_claim or "mechanics_path" in reason or "numeric_scope" in reason:
            raise ValueError("mechanics_numeric_claim_on_insufficient_context")
        if reason["claim"] not in INCOMPLETE_DIRECT_MECHANICS_CLAIM_VALUES:
            raise ValueError("mechanics_partial_context_claim_invalid")
    claim_classification = _classify_claim(
        reason=reason,
        mechanics_known=mechanics_known,
        mechanics_insufficient=mechanics_insufficient,
        multi_mechanics_ranking=multi_mechanics_ranking,
    )
    has_mechanics_reference = "mechanics_path" in reason or "numeric_scope" in reason
    if claim_classification == "value_free_ranking_claim":
        if has_mechanics_reference:
            raise ValueError("multi_move_claim_reference_forbidden")
    elif multi_mechanics_ranking and claim_classification == "numeric_mechanics_claim":
        raise ValueError("multi_move_numeric_claim_forbidden")
    elif mechanics_known and kind in {"damage", "ko", "mechanics"} and (numeric_claim or kind == "mechanics" and has_mechanics_reference):
        path = reason.get("mechanics_path")
        scope = reason.get("numeric_scope")
        if path != mechanics_path or not isinstance(scope, str) or scope not in _NUMERIC_SCOPE_VALUES:
            raise ValueError("mechanics_numeric_scope_invalid")
        if numeric_claim:
            expected = _mechanics_scope_values(mechanics, scope)
            if expected is None or _numeric_literals(reason["claim"]) != expected:
                raise ValueError("mechanics_numeric_value_mismatch")
    elif has_mechanics_reference:
        raise ValueError("mechanics_numeric_scope_invalid")
    if kind == "damage" and (not isinstance(damage, Mapping) or damage.get("status") != "resolved") and not mechanics_known:
        raise ValueError("claim_evidence_unavailable")
    if kind == "ko" and (not isinstance(damage, Mapping) or "ko" not in damage or damage["ko"] is None) and not (mechanics_known and isinstance(mechanics.get("ko_result"), Mapping)):
        raise ValueError("claim_evidence_unavailable")
    if kind == "hit_chance" and not isinstance(candidate.get("hit_chance"), Mapping):
        raise ValueError("claim_evidence_unavailable")
    if kind == "move_order" and not isinstance(candidate.get("move_order"), Mapping):
        raise ValueError("claim_evidence_unavailable")
    if kind == "dynamic_mechanic" and not isinstance(candidate.get("dynamic_move"), Mapping):
        raise ValueError("claim_evidence_unavailable")
    if kind == "self_effect" and (not isinstance(candidate.get("self_effects"), list) or not candidate["self_effects"]):
        raise ValueError("claim_evidence_unavailable")
    if kind == "mechanics" and not mechanics_known:
        raise ValueError("mechanics_claim_path_missing")
    if kind == "partial_context" and candidate.get("status") == "resolved" and any(word in reason["claim"].lower() for word in ("missing", "unavailable", "incomplete")):
        raise ValueError("claim_evidence_contradiction")


def _direct_provider_claim_context(*, request: Mapping[str, Any], response: Mapping[str, Any]) -> tuple[Mapping[str, Any], str] | None:
    if response.get("recommendation_status") == "resolved":
        move, slot = response.get("recommended_move"), response.get("recommended_slot_index")
        if not isinstance(move, str) or not isinstance(slot, int) or isinstance(slot, bool):
            return None
        return _comparison_context_for_pair(request, {"move": move, "slot_index": slot})
    if response.get("recommendation_status") == "insufficient_context":
        contexts = [
            (comparison, f"candidate_comparisons.{index}.mechanics_result")
            for index, comparison in enumerate(request.get("candidate_comparisons", []))
            if isinstance(comparison, Mapping)
            and isinstance(comparison.get("mechanics_result"), Mapping)
            and comparison["mechanics_result"].get("mechanics_source") in _NATIVE_DIRECT_MECHANICS_SOURCES
        ]
        return contexts[0] if len(contexts) == 1 else None
    return None


def _normalize_direct_provider_claim(*, claim: Any, candidate: Mapping[str, Any], mechanics_path: str) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(claim, Mapping) or not isinstance(claim.get("kind"), str):
        return None, "provider_direct_claim_invalid"
    kind = claim["kind"]
    if kind not in DIRECT_MECHANICS_PROVIDER_CLAIM_KINDS:
        return deepcopy(dict(claim)), None
    if set(claim) != {"kind", "claim"} or not isinstance(claim.get("claim"), str) or not claim["claim"]:
        return None, "provider_mechanics_linkage_forbidden"
    mechanics = candidate.get("mechanics_result")
    if not isinstance(mechanics, Mapping) or mechanics.get("mechanics_source") not in _NATIVE_DIRECT_MECHANICS_SOURCES:
        return None, "provider_direct_claim_candidate_invalid"
    status = mechanics.get("status")
    if kind == "partial_context":
        if status != "insufficient_context":
            return None, "provider_partial_context_claim_invalid"
        if _numeric_literals(claim["claim"]):
            return None, "mechanics_numeric_claim_on_insufficient_context"
        if claim["claim"] not in INCOMPLETE_DIRECT_MECHANICS_CLAIM_VALUES:
            return None, "provider_partial_context_claim_invalid"
        return {"kind": "partial_context", "claim": claim["claim"]}, None
    if status != "known":
        return None, "provider_direct_claim_status_invalid"
    if kind == "value_free_mechanics":
        if _numeric_literals(claim["claim"]):
            return None, "provider_value_free_mechanics_numeric_forbidden"
        return {"kind": "mechanics", "claim": claim["claim"]}, None
    scope = _DIRECT_PROVIDER_NUMERIC_SCOPES[kind]
    expected = _mechanics_scope_values(mechanics, scope)
    values = _numeric_literals(claim["claim"])
    if expected is None:
        return None, "ambiguous_native_mechanics_evidence"
    if not values:
        return None, "mechanics_numeric_claim_without_evidence"
    return {"kind": "mechanics", "claim": claim["claim"], "mechanics_path": mechanics_path, "numeric_scope": scope}, None


def _normalize_direct_provider_claims(*, request: Mapping[str, Any], response: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Bind provider claim kinds to the selected candidate's native mechanics only."""
    all_claims = [*response.get("primary_reasons", []), *response.get("risks", [])] if isinstance(response.get("primary_reasons"), list) and isinstance(response.get("risks"), list) else []
    alternatives = response.get("alternatives")
    if not any(isinstance(claim, Mapping) and claim.get("kind") in DIRECT_MECHANICS_PROVIDER_CLAIM_KINDS for claim in all_claims) and not any(isinstance(item, Mapping) and isinstance(item.get("reason"), Mapping) and item["reason"].get("kind") in DIRECT_MECHANICS_PROVIDER_CLAIM_KINDS for item in alternatives or []):
        return deepcopy(dict(response)), None
    context = _direct_provider_claim_context(request=request, response=response)
    if context is None:
        return None, "provider_direct_claim_candidate_invalid"
    candidate, mechanics_path = context
    normalized = deepcopy(dict(response))
    for key in ("primary_reasons", "risks"):
        values = normalized.get(key)
        if not isinstance(values, list):
            return None, "provider_direct_claim_invalid"
        output = []
        for claim in values:
            item, error = _normalize_direct_provider_claim(claim=claim, candidate=candidate, mechanics_path=mechanics_path)
            if error:
                return None, error
            output.append(item)
        normalized[key] = output
    if not isinstance(alternatives, list):
        return None, "provider_direct_claim_invalid"
    output_alternatives = []
    for alternative in alternatives:
        if not isinstance(alternative, Mapping) or not isinstance(alternative.get("reason"), Mapping):
            return None, "provider_direct_claim_invalid"
        pair = {"move": alternative.get("move"), "slot_index": alternative.get("slot_index")}
        alternative_context = _comparison_context_for_pair(request, pair) if isinstance(pair["move"], str) and isinstance(pair["slot_index"], int) and not isinstance(pair["slot_index"], bool) else None
        if alternative_context is None:
            return None, "provider_direct_claim_candidate_invalid"
        reason, error = _normalize_direct_provider_claim(claim=alternative["reason"], candidate=alternative_context[0], mechanics_path=alternative_context[1])
        if error:
            return None, error
        output_alternatives.append({"move": pair["move"], "slot_index": pair["slot_index"], "reason": reason})
    normalized["alternatives"] = output_alternatives
    return normalized, None


def parse_recommendation_response(*, request: Mapping[str, Any], response_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an already-decoded, offline recommendation response without provider access."""
    if not isinstance(response_payload, Mapping):
        return _response_failure("invalid_response_payload")
    if _has_forbidden_response_content(response_payload):
        return _response_failure("forbidden_response_content")
    status = response_payload.get("recommendation_status")
    if status not in _RESPONSE_STATUSES or status == "validation_failed":
        return _response_failure("unsupported_recommendation_status")
    reasons, risks, alternatives = response_payload.get("primary_reasons"), response_payload.get("risks"), response_payload.get("alternatives")
    if not isinstance(reasons, list) or not isinstance(risks, list) or not isinstance(alternatives, list):
        return _response_failure("invalid_response_collections")
    move, slot = response_payload.get("recommended_move"), response_payload.get("recommended_slot_index")
    if status == "resolved":
        if not isinstance(move, str) or not isinstance(slot, int) or isinstance(slot, bool):
            return _response_failure("missing_recommended_candidate")
        try:
            validate_recommendation_selection(request=request, recommended_move=move, recommended_slot_index=slot)
        except ValueError:
            return _response_failure("recommended_candidate_not_selectable")
        primary = {"move": move, "slot_index": slot}
        context = _comparison_context_for_pair(request, primary)
        if context is None:
            return _response_failure("request_candidate_evidence_missing")
        candidate, mechanics_path = context
    else:
        if move is not None or slot is not None:
            return _response_failure("unexpected_recommended_candidate")
        readiness = request.get("readiness", {}).get("status") if isinstance(request, Mapping) else None
        if status == "no_usable_candidate" and readiness not in {"no_selectable_candidates", "no_candidates"}:
            return _response_failure("request_not_no_usable_candidate")
        direct_contexts = [
            (comparison, f"candidate_comparisons.{index}.mechanics_result")
            for index, comparison in enumerate(request.get("candidate_comparisons", []))
            if isinstance(comparison, Mapping)
            and isinstance(comparison.get("mechanics_result"), Mapping)
            and comparison["mechanics_result"].get("status") != "not_requested"
        ]
        if status == "insufficient_context" and len(direct_contexts) == 1:
            candidate, mechanics_path = dict(direct_contexts[0][0]), direct_contexts[0][1]
            candidate["status"] = "partial"
        else:
            candidate, mechanics_path = {}, None
        primary = None
    multi_mechanics_ranking = _request_has_multi_mechanics_ranking(request)
    try:
        for reason in [*reasons, *risks]:
            _validate_claim(reason, candidate, mechanics_path=mechanics_path, multi_mechanics_ranking=multi_mechanics_ranking)
        seen_alternatives = set()
        for alternative in alternatives:
            if not isinstance(alternative, Mapping) or set(alternative) != {"move", "slot_index", "reason"}:
                raise ValueError("invalid_alternative")
            pair = {"move": alternative.get("move"), "slot_index": alternative.get("slot_index")}
            validate_recommendation_selection(request=request, recommended_move=pair["move"], recommended_slot_index=pair["slot_index"])
            key = (pair["move"], pair["slot_index"])
            if key in seen_alternatives or pair == primary:
                raise ValueError("invalid_alternative")
            alternative_context = _comparison_context_for_pair(request, pair)
            if alternative_context is None:
                raise ValueError("invalid_alternative")
            alternative_candidate, alternative_path = alternative_context
            _validate_claim(alternative["reason"], alternative_candidate, mechanics_path=alternative_path, multi_mechanics_ranking=multi_mechanics_ranking)
            seen_alternatives.add(key)
    except ValueError as error:
        return _response_failure(str(error))
    return {"status": status, "recommended_move": move, "recommended_slot_index": slot,
            "primary_reasons": deepcopy(reasons), "risks": deepcopy(risks),
            "alternatives": deepcopy(alternatives), "errors": []}


def _cycle_result(*, status: str, candidates: Sequence[Mapping[str, Any]] = (), evidence_bundle: Mapping[str, Any] | None = None, recommendation_request: Mapping[str, Any] | None = None, recommendation_result: Mapping[str, Any] | None = None, errors: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "status": status,
        "candidates": deepcopy(list(candidates)),
        "evidence_bundle": deepcopy(dict(evidence_bundle)) if isinstance(evidence_bundle, Mapping) else None,
        "recommendation_request": deepcopy(dict(recommendation_request)) if isinstance(recommendation_request, Mapping) else None,
        "recommendation_result": deepcopy(dict(recommendation_result)) if isinstance(recommendation_result, Mapping) else None,
        "errors": list(errors),
    }


def prepare_recommendation_cycle(*, moves: Sequence[Any], battle_snapshot: Mapping[str, Any], repositories: Any, battle_snapshot_summary: Mapping[str, Any] | None = None, known_limitations: Sequence[str] = (), turn_snapshot: Any = None, species_repository: Any = None) -> dict[str, Any]:
    """Prepare a provider-neutral recommendation cycle from deterministic evidence."""
    if isinstance(moves, (str, bytes)) or not isinstance(moves, Sequence):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_move_slots"])
    if not isinstance(battle_snapshot, Mapping) or (battle_snapshot_summary is not None and not isinstance(battle_snapshot_summary, Mapping)):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_battle_snapshot"])
    if isinstance(known_limitations, (str, bytes)) or not isinstance(known_limitations, Sequence) or not all(isinstance(item, str) for item in known_limitations):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_battle_snapshot"])
    try:
        candidates = evaluate_move_slots(moves=moves, battle_snapshot=battle_snapshot, repositories=repositories, turn_snapshot=turn_snapshot, species_repository=species_repository)
    except (TypeError, ValueError):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_move_slots"])
    except Exception:
        return _cycle_result(status="candidate_evaluation_failed", errors=["candidate_evaluation_failed"])
    summary = battle_snapshot if battle_snapshot_summary is None else battle_snapshot_summary
    try:
        evidence = build_evidence_bundle(summary, candidates, known_limitations)
    except (TypeError, ValueError):
        return _cycle_result(status="request_validation_failed", candidates=candidates, errors=["request_validation_failed"])
    if not candidates:
        return _cycle_result(status="no_candidates", candidates=candidates, evidence_bundle=evidence, errors=["no_candidates"])
    request = build_recommendation_request(evidence_bundle=evidence)
    readiness = request.get("readiness", {}).get("status") if isinstance(request, Mapping) else None
    if readiness == "invalid_evidence_bundle":
        return _cycle_result(status="request_validation_failed", candidates=candidates, evidence_bundle=evidence, errors=["request_validation_failed"])
    if readiness == "no_selectable_candidates":
        return _cycle_result(status="no_selectable_candidates", candidates=candidates, evidence_bundle=evidence, errors=["no_selectable_candidates"])
    if readiness != "ready":
        return _cycle_result(status="request_validation_failed", candidates=candidates, evidence_bundle=evidence, errors=["request_validation_failed"])
    return _cycle_result(status="ready", candidates=candidates, evidence_bundle=evidence, recommendation_request=request)


def _bind_multi_provider_response(*, request: Mapping[str, Any], response: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Bind a minimal multi-move provider choice to authoritative request evidence."""
    if set(response) != set(_MULTI_PROVIDER_RESPONSE_KEYS) or response.get("recommendation_status") != "resolved":
        return None
    selected = response.get("selected_candidate_id")
    rows = request.get("candidate_comparisons")
    if not isinstance(selected, int) or isinstance(selected, bool) or not isinstance(rows, list):
        return None
    chosen = next((row for row in rows if isinstance(row, Mapping) and row.get("slot_index") == selected), None)
    if not isinstance(chosen, Mapping):
        return None
    comparison = chosen.get("mechanics_comparison")
    if not isinstance(comparison, Mapping) or comparison.get("comparison_status") != "rankable" or comparison.get("rank") != 1:
        return None
    rankable = [row for row in rows if isinstance(row, Mapping) and isinstance(row.get("mechanics_comparison"), Mapping) and row["mechanics_comparison"].get("comparison_status") == "rankable"]
    expected_code = "only_rankable_candidate" if comparison.get("comparison_reason") == "only_rankable_candidate" else "stable_tie_break" if any(row is not chosen and row.get("mechanics_result") == chosen.get("mechanics_result") for row in rankable) else "clear_ranked_winner"
    if response.get("explanation_code") != expected_code:
        return None
    mechanics_acknowledgements = []
    ranking_acknowledgements = []
    for index, row in enumerate(rows):
        mechanics = row.get("mechanics_result") if isinstance(row, Mapping) else None
        ranking = row.get("mechanics_comparison") if isinstance(row, Mapping) else None
        if not isinstance(row, Mapping) or not isinstance(mechanics, Mapping) or not isinstance(ranking, Mapping):
            return None
        mechanics_acknowledgements.append({"slot_index": row["slot_index"], "move": row["move"], "mechanics_path": f"candidate_comparisons.{index}.mechanics_result", "status": mechanics.get("status"), "missing_inputs_path": None})
        ranking_acknowledgements.append({"slot_index": row["slot_index"], "move": row["move"], **ranking})
    return {"recommendation_status": "resolved", "recommended_move": chosen["move"], "recommended_slot_index": selected, "primary_reasons": [{"kind": "mechanics", "claim": "deterministic ranking evidence"}], "risks": [], "alternatives": [], "grounding": {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [], "evidence_only": [], "conflicts": [], "conditional_dependencies": []}, "mechanics_acknowledgements": mechanics_acknowledgements, "ranking_acknowledgements": ranking_acknowledgements}


def _attach_validated_multi_selection(*, request: Mapping[str, Any], result: Mapping[str, Any], explanation_code: str) -> dict[str, Any] | None:
    """Attach only the selected request-start candidate's deterministic evidence."""
    if result.get("status") != "resolved" or not isinstance(result.get("recommended_slot_index"), int):
        return None
    slot, move = result["recommended_slot_index"], result.get("recommended_move")
    rows = request.get("candidate_comparisons")
    if not isinstance(move, str) or not isinstance(rows, list):
        return None
    selected = next((row for row in rows if isinstance(row, Mapping) and row.get("slot_index") == slot and row.get("move") == move), None)
    if not isinstance(selected, Mapping):
        return None
    facts = selected.get("comparison_facts")
    mechanics = selected.get("mechanics_result")
    if not isinstance(facts, Mapping) or facts.get("candidate_id") != {"slot_index": slot, "move": move} or not isinstance(mechanics, Mapping):
        return None
    action_order = selected.get("action_order")
    if action_order is not None and not isinstance(action_order, Mapping):
        return None
    output = deepcopy(dict(result))
    output.update({
        "selected_candidate_id": slot,
        "selected_action": {"slot_index": slot, "move": move},
        "explanation_code": explanation_code,
        "selected_candidate_evidence": {
            "mechanics_result": deepcopy(dict(mechanics)),
            "action_order": deepcopy(dict(action_order)) if isinstance(action_order, Mapping) else None,
            "accuracy_evidence": deepcopy(dict(selected["accuracy_evidence"])) if isinstance(selected.get("accuracy_evidence"), Mapping) else None,
            "status_move_evidence": deepcopy(dict(selected["status_move_evidence"])) if isinstance(selected.get("status_move_evidence"), Mapping) else None,
            "move_consequence_evidence": deepcopy(dict(selected["move_consequence_evidence"])) if isinstance(selected.get("move_consequence_evidence"), Mapping) else None,
            "comparison_facts": deepcopy(dict(facts)),
        },
        "uncertainty": {
            "mechanics_status": mechanics.get("status"),
            "missing_inputs": deepcopy(mechanics.get("missing_inputs")) if isinstance(mechanics.get("missing_inputs"), list) else [],
            "unsupported_reason": mechanics.get("unsupported_reason") if isinstance(mechanics.get("unsupported_reason"), str) else None,
        },
    })
    return output


def complete_recommendation_cycle(*, prepared_cycle: Mapping[str, Any], response_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Complete a ready provider-neutral cycle through the offline parser only."""
    if not isinstance(prepared_cycle, Mapping) or prepared_cycle.get("status") != "ready" or not isinstance(prepared_cycle.get("recommendation_request"), Mapping):
        source = prepared_cycle if isinstance(prepared_cycle, Mapping) else {}
        return _cycle_result(status="cycle_not_ready", candidates=source.get("candidates", ()), evidence_bundle=source.get("evidence_bundle"), errors=["cycle_not_ready"])
    candidates = prepared_cycle.get("candidates", ())
    evidence = prepared_cycle.get("evidence_bundle")
    request = prepared_cycle["recommendation_request"]
    mechanics_required = _request_has_mechanics_result(request)
    ranking_required = _request_has_multi_mechanics_ranking(request)
    explanation_code = response_payload.get("explanation_code") if isinstance(response_payload, Mapping) else None
    if ranking_required:
        bound = _bind_multi_provider_response(request=request, response=response_payload)
        if bound is None:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["multi_provider_binding_invalid"])
        response_payload = bound
    elif mechanics_required:
        normalized, diagnostic = _normalize_direct_provider_claims(request=request, response=response_payload)
        if normalized is None:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=[diagnostic or "provider_direct_claim_invalid"])
        response_payload = normalized
    if (_RUNTIME_PROVIDER_KEY in request or mechanics_required) and "grounding" not in response_payload:
        return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["grounding_required"])
    if mechanics_required and "mechanics_acknowledgements" not in response_payload:
        return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["mechanics_acknowledgement_missing"])
    if ranking_required and "ranking_acknowledgements" not in response_payload:
        return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["ranking_acknowledgement_missing"])
    if _RUNTIME_PROVIDER_KEY in request:
        errors = validate_runtime_grounding(runtime_advice_state=request[_RUNTIME_PROVIDER_KEY], grounding=response_payload.get("grounding"), legacy_compatible=False)
        if errors:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=errors)
    if mechanics_required:
        errors = validate_mechanics_acknowledgements(
            request=request,
            acknowledgements=response_payload.get("mechanics_acknowledgements"),
            allow_untrusted_missing_input_dependency=ranking_required,
        )
        if errors:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=errors)
    if ranking_required:
        errors = validate_ranking_acknowledgements(
            request=request,
            acknowledgements=response_payload.get("ranking_acknowledgements"),
        )
        if errors:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=errors)
    result = parse_recommendation_response(request=request, response_payload=response_payload)
    if result["status"] == "validation_failed":
        return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=result.get("errors", ["response_validation_failed"]))
    if ranking_required:
        if not isinstance(explanation_code, str):
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["multi_provider_binding_invalid"])
        enriched = _attach_validated_multi_selection(request=request, result=result, explanation_code=explanation_code)
        if enriched is None:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["validated_selection_resolution_invalid"])
        result = enriched
    return _cycle_result(status=result["status"], candidates=candidates, evidence_bundle=evidence, recommendation_request=request, recommendation_result=result)


_UI_SNAPSHOT_CONTEXT_KEYS = (
    "final_stat_context", "stat_stage_context", "current_hp_context", "condition_context", "ability_context", "field_state_context",
    "item_profiles",
    "battle_format_context", "attacker_level_context", "observed_previous_damage_context", "battle_counter_context",
    "consecutive_use_context", "weight_context", "turn_event_context",
)
_UI_RECOMMENDATION_LIMITATION_GUARDRAILS = (
    "Unknown opponent moves remain untrusted.", "Unknown item, ability, EV, IV, nature, and final stats remain untrusted unless confirmed.",
    "No multi-turn planning, switch recommendation, Turn Engine, or untrusted inference.",
)


def adapt_ui_move_slots(*, selected_moves: Sequence[Any]) -> tuple[str | None, ...]:
    """Normalize current UI move slots without reducing them to the selected index."""
    if isinstance(selected_moves, (str, bytes)) or not isinstance(selected_moves, Sequence) or len(selected_moves) > 4:
        raise ValueError("invalid_move_slots")
    result = []
    for value in selected_moves:
        if value is None:
            result.append(None)
            continue
        move_id = value.get("move_id") if isinstance(value, Mapping) else getattr(value, "move_id", None)
        if not isinstance(move_id, str) or not move_id:
            raise ValueError("unsupported_move_slot_shape")
        result.append(move_id)
    return tuple(result)


def adapt_ui_battle_snapshot(*, battle_input: Mapping[str, Any]) -> dict[str, Any]:
    """Copy only trusted deterministic contexts from normalized UI battle input."""
    if not isinstance(battle_input, Mapping):
        raise ValueError("invalid_battle_snapshot")
    pokemon = battle_input.get("pokemon")
    if not isinstance(pokemon, Mapping) or not isinstance(pokemon.get("my_active"), Mapping) or not isinstance(pokemon.get("opponent_active"), Mapping):
        raise ValueError("missing_selected_pokemon")
    snapshot = {"pokemon": deepcopy(dict(pokemon))}
    for key in _UI_SNAPSHOT_CONTEXT_KEYS:
        if isinstance(battle_input.get(key), Mapping):
            snapshot[key] = deepcopy(dict(battle_input[key]))
    moves = battle_input.get("moves")
    if isinstance(moves, Mapping) and isinstance(moves.get("opponent_selected_move"), Mapping):
        snapshot["opponent_selected_move"] = deepcopy(dict(moves["opponent_selected_move"]))
    elif isinstance(battle_input.get("opponent_selected_move"), Mapping):
        snapshot["opponent_selected_move"] = deepcopy(dict(battle_input["opponent_selected_move"]))
    return snapshot


def build_ui_recommendation_snapshot_summary(*, battle_input: Mapping[str, Any], turn_snapshot: Any = None) -> dict[str, Any]:
    if not isinstance(battle_input, Mapping):
        raise ValueError("invalid_battle_snapshot")
    scenario = battle_input.get("scenario")
    summary = {}
    if isinstance(scenario, Mapping):
        summary["scenario"] = {key: deepcopy(scenario[key]) for key in ("mode", "format_note") if key in scenario}
    pokemon = battle_input.get("pokemon")
    if isinstance(pokemon, Mapping):
        summary["pokemon"] = deepcopy(dict(pokemon))
    if turn_snapshot is not None:
        summary["turn_snapshot"] = deepcopy(turn_snapshot.to_dict())
    return summary


def _ui_known_limitations(battle_input: Mapping[str, Any]) -> list[str]:
    scenario = battle_input.get("scenario") if isinstance(battle_input, Mapping) else None
    existing = scenario.get("known_limitations") if isinstance(scenario, Mapping) else None
    values = [item for item in existing if isinstance(item, str)] if isinstance(existing, list) else []
    return list(dict.fromkeys([*values, *_UI_RECOMMENDATION_LIMITATION_GUARDRAILS]))


def prepare_ui_recommendation_cycle(*, selected_moves: Sequence[Any], battle_input: Mapping[str, Any], move_repository: Any, species_repository: Any = None, observation_snapshot: Mapping[str, Any] | None = None, trusted_turn_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Prepare an offline recommendation cycle from UI-shaped, trusted inputs."""
    try:
        moves = adapt_ui_move_slots(selected_moves=selected_moves)
        request_turn_snapshot = build_request_start_recommendation_snapshot(
            battle_input, selectable_moves=moves, observation_snapshot=observation_snapshot, trusted_turn_context=trusted_turn_context
        )
        snapshot = adapt_ui_battle_snapshot(battle_input=battle_input)
        snapshot.update(snapshot_deterministic_context(request_turn_snapshot))
        summary = build_ui_recommendation_snapshot_summary(
            battle_input=battle_input, turn_snapshot=request_turn_snapshot
        )
    except ValueError as error:
        return _cycle_result(status="invalid_snapshot", errors=[str(error)])
    return prepare_recommendation_cycle(
        moves=moves, battle_snapshot=snapshot, repositories=move_repository,
        battle_snapshot_summary=summary, known_limitations=_ui_known_limitations(battle_input),
        turn_snapshot=request_turn_snapshot, species_repository=species_repository,
    )


_PROVIDER_OUTBOUND_KEYS = (
    "request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set",
    "candidate_comparisons", "known_limitations", "guardrails",
)
_RUNTIME_PROVIDER_KEY = "runtime_advice_state"
_PROVIDER_RESPONSE_KEYS = (
    "recommendation_status", "recommended_move", "recommended_slot_index", "primary_reasons", "risks", "alternatives",
)
_GROUNDED_PROVIDER_RESPONSE_KEYS = (*_PROVIDER_RESPONSE_KEYS, "grounding")
_MECHANICS_ACK_PROVIDER_RESPONSE_KEYS = (*_GROUNDED_PROVIDER_RESPONSE_KEYS, "mechanics_acknowledgements")
_RANKING_ACK_PROVIDER_RESPONSE_KEYS = (*_MECHANICS_ACK_PROVIDER_RESPONSE_KEYS, "ranking_acknowledgements")
_MULTI_PROVIDER_RESPONSE_KEYS = ("recommendation_status", "selected_candidate_id", "explanation_code")
_PROVIDER_RESPONSE_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate"})
_PREPARED_CYCLE_KEYS = frozenset({"status", "candidates", "evidence_bundle", "recommendation_request", "recommendation_result", "errors"})


def _provider_adapter_failure(status: str, code: str) -> dict[str, Any]:
    return {"status": status, "errors": [code]}


def build_provider_recommendation_payload(*, prepared_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Build a serialized provider-neutral payload from a ready prepared cycle."""
    if not isinstance(prepared_cycle, Mapping) or prepared_cycle.get("status") != "ready":
        return _provider_adapter_failure("prepared_cycle_not_ready", "prepared_cycle_not_ready")
    if not set(prepared_cycle) <= _PREPARED_CYCLE_KEYS:
        return _provider_adapter_failure("provider_payload_validation_failed", "provider_payload_validation_failed")
    request = prepared_cycle.get("recommendation_request")
    if not isinstance(request, Mapping):
        return _provider_adapter_failure("provider_payload_validation_failed", "provider_payload_validation_failed")
    try:
        if not set(_PROVIDER_OUTBOUND_KEYS) <= set(request):
            raise ValueError("missing approved request field")
        serialize_recommendation_request(deepcopy(dict(request)))
        payload = {key: deepcopy(request[key]) for key in _PROVIDER_OUTBOUND_KEYS}
        if _RUNTIME_PROVIDER_KEY in request:
            runtime = request[_RUNTIME_PROVIDER_KEY]
            if not isinstance(runtime, Mapping):
                raise ValueError("invalid runtime projection")
            payload[_RUNTIME_PROVIDER_KEY] = deepcopy(dict(runtime))
        return serialize_recommendation_request(payload)
    except (TypeError, ValueError):
        return _provider_adapter_failure("provider_payload_validation_failed", "provider_payload_validation_failed")


def adapt_provider_recommendation_response(*, provider_response: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a provider-independent structured response without semantic evaluation."""
    if type(provider_response) is not dict:
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")
    if set(provider_response) not in (set(_PROVIDER_RESPONSE_KEYS), set(_GROUNDED_PROVIDER_RESPONSE_KEYS), set(_MECHANICS_ACK_PROVIDER_RESPONSE_KEYS), set(_RANKING_ACK_PROVIDER_RESPONSE_KEYS), set(_MULTI_PROVIDER_RESPONSE_KEYS)):
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")
    if provider_response.get("recommendation_status") not in _PROVIDER_RESPONSE_STATUSES:
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")
    try:
        if set(provider_response) == set(_MULTI_PROVIDER_RESPONSE_KEYS):
            if provider_response.get("recommendation_status") != "resolved" or not isinstance(provider_response.get("selected_candidate_id"), int) or isinstance(provider_response.get("selected_candidate_id"), bool) or provider_response.get("explanation_code") not in {"clear_ranked_winner", "only_rankable_candidate", "stable_tie_break", "partial_context", "unsupported_alternatives"}:
                raise ValueError("invalid multi response")
            return serialize_recommendation_request(deepcopy(provider_response))
        if "grounding" in provider_response:
            grounding = provider_response["grounding"]
            required = {"schema_version", "confirmed_facts", "unknown_facts", "evidence_only", "conflicts", "conditional_dependencies"}
            if not isinstance(grounding, Mapping) or set(grounding) != required or grounding.get("schema_version") != "grounding-v1" or not all(isinstance(grounding[key], list) for key in required - {"schema_version"}):
                raise ValueError("invalid grounding")
        if "mechanics_acknowledgements" in provider_response and not isinstance(provider_response["mechanics_acknowledgements"], list):
            raise ValueError("invalid mechanics acknowledgements")
        if "ranking_acknowledgements" in provider_response and not isinstance(provider_response["ranking_acknowledgements"], list):
            raise ValueError("invalid ranking acknowledgements")
        return serialize_recommendation_request(deepcopy(provider_response))
    except (TypeError, ValueError):
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")


_GROUNDING_V1_ENTRY_KEYS = ("confirmed_facts", "unknown_facts", "evidence_only", "conflicts", "conditional_dependencies")


def grounding_structure_diagnostic(grounding: Any) -> str | None:
    """Return one bounded structural code without exposing response values."""
    if grounding is None:
        return "grounding_missing"
    if not isinstance(grounding, Mapping):
        return "grounding_not_mapping"
    allowed = {"schema_version", *_GROUNDING_V1_ENTRY_KEYS}
    if any(key not in allowed for key in grounding):
        return "grounding_unknown_field"
    if "schema_version" not in grounding:
        return "grounding_version_missing"
    if grounding.get("schema_version") != "grounding-v1":
        return "grounding_version_invalid"
    for key in _GROUNDING_V1_ENTRY_KEYS:
        if key not in grounding:
            return "grounding_entries_missing"
        if not isinstance(grounding[key], list):
            return "grounding_entries_not_list"
        for entry in grounding[key]:
            if not isinstance(entry, Mapping):
                return "grounding_entry_not_mapping"
            if "path" not in entry:
                return "grounding_entry_field_missing"
            if not isinstance(entry["path"], str) or not entry["path"]:
                return "grounding_entry_field_invalid"
    return None


def _request_has_mechanics_result(request: Mapping[str, Any]) -> bool:
    comparisons = request.get("candidate_comparisons")
    return isinstance(comparisons, list) and any(
        isinstance(candidate, Mapping)
        and isinstance(candidate.get("mechanics_result"), Mapping)
        and candidate["mechanics_result"].get("status") != "not_requested"
        for candidate in comparisons
    )


def _request_has_multi_mechanics_ranking(request: Mapping[str, Any]) -> bool:
    comparisons = request.get("candidate_comparisons")
    return isinstance(comparisons, list) and sum(
        isinstance(candidate, Mapping) and isinstance(candidate.get("mechanics_comparison"), Mapping)
        for candidate in comparisons
    ) >= 2


def validate_mechanics_acknowledgements(*, request: Mapping[str, Any], acknowledgements: Any, allow_untrusted_missing_input_dependency: bool = False) -> list[str]:
    """Validate the schema-required, value-free direct-mechanics links."""
    comparisons = request.get("candidate_comparisons")
    if not isinstance(comparisons, list):
        return ["mechanics_acknowledgement_request_invalid"]
    if not isinstance(acknowledgements, list):
        return ["mechanics_acknowledgement_missing"]
    expected: dict[tuple[int, str], tuple[str, str, str | None]] = {}
    for index, candidate in enumerate(comparisons):
        mechanics = candidate.get("mechanics_result") if isinstance(candidate, Mapping) else None
        move = candidate.get("move") if isinstance(candidate, Mapping) else None
        if not isinstance(mechanics, Mapping) or mechanics.get("status") == "not_requested":
            continue
        path = f"candidate_comparisons.{index}.mechanics_result"
        if not isinstance(move, str) or not move:
            return ["mechanics_acknowledgement_request_invalid"]
        status = mechanics.get("status")
        if status not in {"known", "insufficient_context", "unsupported_mechanic"}:
            return ["mechanics_acknowledgement_request_invalid"]
        expected[(index, move)] = (path, status, f"{path}.missing_inputs" if status == "insufficient_context" else None)
    seen: set[tuple[int, str]] = set()
    for acknowledgement in acknowledgements:
        if not isinstance(acknowledgement, Mapping) or set(acknowledgement) != {"slot_index", "move", "mechanics_path", "status", "missing_inputs_path"}:
            return ["mechanics_acknowledgement_invalid"]
        slot_index = acknowledgement.get("slot_index")
        move = acknowledgement.get("move")
        if not isinstance(slot_index, int) or isinstance(slot_index, bool) or not isinstance(move, str) or not move:
            return ["mechanics_acknowledgement_invalid"]
        key = (slot_index, move)
        if key not in expected or key in seen:
            return ["mechanics_acknowledgement_candidate_invalid"]
        seen.add(key)
        expected_path, expected_status, expected_dependency = expected[key]
        if acknowledgement.get("mechanics_path") != expected_path:
            return ["mechanics_acknowledgement_path_invalid"]
        if acknowledgement.get("status") != expected_status:
            return ["mechanics_acknowledgement_status_invalid"]
        dependency = acknowledgement.get("missing_inputs_path")
        if dependency != expected_dependency and not (
            allow_untrusted_missing_input_dependency and expected_dependency is not None
            and (dependency is None or isinstance(dependency, str))
        ):
            return ["mechanics_acknowledgement_dependency_invalid"]
    return [] if seen == set(expected) else ["mechanics_acknowledgement_missing"]


def validate_ranking_acknowledgements(*, request: Mapping[str, Any], acknowledgements: Any) -> list[str]:
    """Validate value-free provider copies of deterministic multi-move ranks."""
    comparisons = request.get("candidate_comparisons")
    if not isinstance(comparisons, list):
        return ["ranking_acknowledgement_request_invalid"]
    if not isinstance(acknowledgements, list):
        return ["ranking_acknowledgement_missing"]
    expected: dict[tuple[int, str], Mapping[str, Any]] = {}
    for candidate in comparisons:
        if not isinstance(candidate, Mapping):
            return ["ranking_acknowledgement_request_invalid"]
        comparison = candidate.get("mechanics_comparison")
        if not isinstance(comparison, Mapping):
            continue
        slot, move = candidate.get("slot_index"), candidate.get("move")
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(move, str) or not move:
            return ["ranking_acknowledgement_request_invalid"]
        expected[(slot, move)] = comparison
    if len(expected) < 2:
        return ["ranking_acknowledgement_request_invalid"]
    seen: set[tuple[int, str]] = set()
    required = {"slot_index", "move", "comparison_status", "rank", "comparison_reason"}
    for acknowledgement in acknowledgements:
        if not isinstance(acknowledgement, Mapping) or set(acknowledgement) != required:
            return ["ranking_acknowledgement_invalid"]
        slot, move = acknowledgement.get("slot_index"), acknowledgement.get("move")
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(move, str) or not move:
            return ["ranking_acknowledgement_invalid"]
        key = (slot, move)
        if key not in expected or key in seen:
            return ["ranking_acknowledgement_candidate_invalid"]
        seen.add(key)
        comparison = expected[key]
        if any(acknowledgement.get(field) != comparison.get(field) for field in ("comparison_status", "rank", "comparison_reason")):
            return ["ranking_acknowledgement_value_invalid"]
    return [] if seen == set(expected) else ["ranking_acknowledgement_missing"]


def validate_runtime_grounding(*, runtime_advice_state: Mapping[str, Any], grounding: Mapping[str, Any], legacy_compatible: bool = False, user_answer: str = "") -> list[str]:
    """Return deterministic grounding errors without reading raw runtime state."""
    if not isinstance(runtime_advice_state, Mapping):
        return ["missing_runtime_projection"]
    diagnostic = grounding_structure_diagnostic(grounding)
    if diagnostic:
        return [] if legacy_compatible and diagnostic == "grounding_missing" else [diagnostic]
    facts: dict[str, Mapping[str, Any]] = {}
    def collect(value: Any, prefix: str = "") -> None:
        if isinstance(value, Mapping) and value.get("status") in {"known", "known_absent", "unknown"}:
            facts[prefix] = value; return
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key not in {"schema_version", "session_id"}:
                    collect(item, f"{prefix}.{key}" if prefix else str(key))
    collect(runtime_advice_state)
    seen: set[str] = set(); errors: list[str] = []
    categories = set(_GROUNDING_V1_ENTRY_KEYS)
    for category in categories:
        for entry in grounding[category]:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str) or not entry["path"]:
                errors.append("grounding_entry_field_invalid"); continue
            path = entry["path"]
            if any(token in path.lower() for token in ("fingerprint", "cas", "ledger", "token", "thread", "reducer", "persistence")):
                errors.append("internal_metadata_grounding"); continue
            if category in {"confirmed_facts", "unknown_facts"}:
                if entry.get("authority") != "runtime": errors.append("runtime_authority_invalid")
                if path not in facts or path in seen:
                    errors.append("grounding_fact_missing_or_duplicate"); continue
                seen.add(path)
                status = facts[path].get("status")
                if category == "unknown_facts" and status != "unknown": errors.append("unknown_misclassification")
                if category == "confirmed_facts" and status == "unknown": errors.append("unknown_promoted")
                if category == "confirmed_facts" and entry.get("status") != status: errors.append("runtime_fact_contradiction")
                if status == "known" and entry.get("value") != facts[path].get("value"): errors.append("runtime_fact_contradiction")
            elif category == "evidence_only" and entry.get("authority") not in {"evidence", "stale"}:
                errors.append("evidence_authority_invalid")
            elif category == "conflicts" and entry.get("authority") != "conflict":
                errors.append("conflict_authority_invalid")
    forbidden = ("fingerprint", "cas", "reducer", "ledger", "request token", "thread identity", "runtime_advice_state")
    if any(term in user_answer.lower() for term in forbidden): errors.append("internal_metadata_in_answer")
    return sorted(set(errors))


def run_offline_recommendation_provider_adapter(*, prepared_cycle: Mapping[str, Any], fake_provider: Any) -> dict[str, Any]:
    """Exercise a supplied in-memory provider boundary without network or retry behavior."""
    payload = build_provider_recommendation_payload(prepared_cycle=prepared_cycle)
    if "status" in payload and "errors" in payload:
        return {"status": payload["status"], "prepared_cycle": deepcopy(dict(prepared_cycle)) if isinstance(prepared_cycle, Mapping) else {}, "response_payload": None, "errors": list(payload["errors"])}
    if not callable(fake_provider):
        return {"status": "provider_unavailable", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_unavailable"]}
    try:
        raw_response = fake_provider(deepcopy(payload))
    except Exception:
        return {"status": "provider_unavailable", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_unavailable"]}
    if type(raw_response) is not dict:
        return {"status": "provider_response_malformed", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_response_malformed"]}
    adapted = adapt_provider_recommendation_response(provider_response=raw_response)
    if "status" in adapted and "errors" in adapted:
        return {"status": "provider_response_validation_failed", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_response_validation_failed"]}
    return {"status": "provider_response_ready", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": deepcopy(adapted), "errors": []}


def run_offline_recommendation_cycle(*, selected_moves: Sequence[Any], battle_input: Mapping[str, Any], move_repository: Any, fake_provider: Any) -> dict[str, Any]:
    """Compose the existing pure UI, fake-provider, and response boundaries."""
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=selected_moves,
        battle_input=battle_input,
        move_repository=move_repository,
    )
    if prepared.get("status") != "ready":
        return {
            "status": "preparation_not_ready",
            "prepared_cycle": deepcopy(prepared),
            "provider_stage": None,
            "completed_cycle": None,
            "errors": ["preparation_not_ready"],
        }
    provider_stage = run_offline_recommendation_provider_adapter(
        prepared_cycle=prepared,
        fake_provider=fake_provider,
    )
    if provider_stage.get("status") != "provider_response_ready":
        return {
            "status": provider_stage.get("status", "provider_response_validation_failed"),
            "prepared_cycle": deepcopy(prepared),
            "provider_stage": deepcopy(provider_stage),
            "completed_cycle": None,
            "errors": list(provider_stage.get("errors", ["provider_response_validation_failed"])),
        }
    completed = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload=provider_stage["response_payload"],
    )
    return {
        "status": completed["status"],
        "prepared_cycle": deepcopy(prepared),
        "provider_stage": deepcopy(provider_stage),
        "completed_cycle": deepcopy(completed),
        "errors": list(completed.get("errors", ())),
    }


def build_recommendation_presentation_model(*, completed_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Build a copied UI-neutral model from a validated completion only."""
    empty = {
        "status": "validation_failed",
        "recommended_move": None,
        "recommended_slot_index": None,
        "primary_reasons": [],
        "risks": [],
        "alternatives": [],
        "candidate_summaries": [],
        "selected_candidate": None,
        "errors": ["invalid_completed_cycle"],
    }
    if not isinstance(completed_cycle, Mapping):
        return empty
    try:
        candidates = serialize_recommendation_request(deepcopy(list(completed_cycle.get("candidates", ()))))
    except (TypeError, ValueError):
        return empty
    errors = completed_cycle.get("errors", ())
    sanitized_errors = [error for error in errors if isinstance(error, str)] if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)) else []
    result = completed_cycle.get("recommendation_result")
    if completed_cycle.get("status") not in {"resolved", "insufficient_context", "no_usable_candidate"} or not isinstance(result, Mapping):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": sanitized_errors or ["response_validation_failed"],
        }
    required = {"status", "recommended_move", "recommended_slot_index", "primary_reasons", "risks", "alternatives", "errors"}
    if not required <= set(result) or result.get("status") != completed_cycle.get("status"):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": sanitized_errors or ["response_validation_failed"],
        }
    try:
        approved = serialize_recommendation_request({key: deepcopy(result[key]) for key in required})
    except (TypeError, ValueError):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": ["response_validation_failed"],
        }
    if not all(isinstance(approved[key], list) for key in ("primary_reasons", "risks", "alternatives", "errors")):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": ["response_validation_failed"],
        }
    selected_candidate = None
    if approved["status"] == "resolved" and "selected_candidate_evidence" in result:
        expected_action = {"slot_index": approved["recommended_slot_index"], "move": approved["recommended_move"]}
        evidence = result.get("selected_candidate_evidence")
        if result.get("selected_candidate_id") != approved["recommended_slot_index"] or result.get("selected_action") != expected_action or not isinstance(result.get("explanation_code"), str) or not isinstance(evidence, Mapping):
            return {**empty, "candidate_summaries": deepcopy(candidates), "errors": ["response_validation_failed"]}
        try:
            selected_candidate = serialize_recommendation_request({
                "selected_candidate_id": result["selected_candidate_id"], "selected_action": result["selected_action"],
                "explanation_code": result["explanation_code"], "evidence": evidence,
                "uncertainty": result.get("uncertainty", {}),
            })
        except (TypeError, ValueError):
            return {**empty, "candidate_summaries": deepcopy(candidates), "errors": ["response_validation_failed"]}
    return {
        "status": approved["status"],
        "recommended_move": approved["recommended_move"],
        "recommended_slot_index": approved["recommended_slot_index"],
        "primary_reasons": deepcopy(approved["primary_reasons"]),
        "risks": deepcopy(approved["risks"]),
        "alternatives": deepcopy(approved["alternatives"]),
        "candidate_summaries": deepcopy(candidates),
        "selected_candidate": selected_candidate,
        "errors": deepcopy(approved["errors"]),
    }
