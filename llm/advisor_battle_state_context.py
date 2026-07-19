"""Source-bound battle state context helper.

This helper normalizes visible or explicit battle-state facts into a limited
context. It does not infer hidden items, spreads, boosts, status, field state,
post-turn HP, RNG results, or full turn outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from advisor.damage.formula import base_damage
from advisor.damage.modifiers.core import calc_stab
from advisor.damage.q12 import M_STAB, apply_damage_modifier
from advisor.damage.q12 import Q12_ONE
from advisor.damage.modifiers.core import weather_modifier
from advisor.damage.screens import screen_modifier
from advisor.damage.field import SideField
from advisor.damage.types import TYPES, load_type_chart


BATTLE_STATE_CONTEXT_ALLOWED_SOURCES = frozenset(
    {
        "visible_ui",
        "explicit_input",
        "user_confirmed",
        "calculated_from_visible",
    }
)
BATTLE_STATE_CONTEXT_ITEM_ALLOWED_SOURCES = frozenset({"explicit_input", "user_confirmed"})
BATTLE_STATE_CONTEXT_FIELD_ALLOWED_SOURCES = frozenset({"explicit_input", "user_confirmed"})
BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES = frozenset(
    {
        "battle_log_observed",
        "damage_reverse",
        "explicit_user_event_confirmation",
        "field_state_inference",
        "future_turn_engine_resolved",
        "hidden_item_guess",
        "hp_percent_inference",
        "imported_replay_observed",
        "llm_guess",
        "species_common_set",
        "species_common_meta",
        "usage_based_guess",
        "meta_inferred",
        "hidden_state_guess",
        "hidden_guess",
        "damage_reverse_inference",
        "legality_gate_guess",
        "legality_gate",
        "context_derived",
        "resist_berry_inferred",
        "resist_berry_context",
        "ko_context",
        "turn_order_context",
        "opponent_move_context",
        "item_inferred_effect",
        "model_guess",
        "parser_observed",
    }
)
BATTLE_STATE_CONTEXT_ACTIVE_FIELDS = ("species", "current_hp_percent", "status", "boosts", "item")
BATTLE_STATE_CONTEXT_FIELD_FIELDS = ("weather", "terrain", "screens", "hazards", "room")
BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS = frozenset(
    {
        "EVs",
        "IVs",
        "nature",
        "hidden_item",
        "inferred_item",
        "predicted_item",
        "likely_item",
        "inferred_boosts",
        "predicted_boosts",
        "likely_boosts",
        "inferred_status",
        "predicted_status",
        "likely_status",
        "inferred_weather",
        "predicted_weather",
        "likely_weather",
        "inferred_terrain",
        "predicted_terrain",
        "likely_terrain",
        "damage_reverse_inferred",
        "activation_turn",
        "berry_consumed",
        "consumed_turn",
        "damage_reduction_applied",
        "event_confidence",
        "event_provenance",
        "event_source",
        "event_turn",
        "focus_sash_triggered",
        "item_activated",
        "item_event_context",
        "item_event_type",
        "post_turn_hp",
        "post_turn_hp_from_item",
        "post_turn_item_state",
        "post_hit_hp_1",
        "recovery_applied",
        "observed_activation",
        "observed_consumption",
        "observed_events",
        "resolved_item_effect",
        "resolved_effects",
        "rng_roll",
        "speed_order_override",
        "item_consumed",
        "item_damage_modifier_applied",
        "item_speed_modifier_applied",
        "rng_resolved",
        "speed_tie_resolved",
        "quick_claw_activated",
        "full_turn_result",
        "resolved_outcome",
    }
)
BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES = (
    "hidden item inference",
    "EV/IV/nature inference",
    "unobserved boosts inference",
    "unobserved status inference",
    "weather/terrain inference without explicit source",
    "hazards/screens inference without explicit source",
    "damage reverse inference",
    "RNG resolution",
    "item consumption",
    "post-turn HP resolution",
    "full turn resolution",
)
BATTLE_STATE_CONTEXT_SAFETY_NOTES = (
    "Unknown battle state fields must remain unknown.",
    "Do not infer hidden state from species, common sets, damage estimates, or KO context.",
    "Battle state context is not a resolved turn simulation.",
)
BATTLE_STATE_CONTEXT_UNKNOWN_FIELD = {"known": False, "value": "unknown"}
EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES = frozenset(
    {
        "item_activation_observed",
        "item_consumption_observed",
        "item_recovery_observed",
        "item_prevention_observed",
        "item_reveal_observed",
    }
)
EXPLICIT_USER_ITEM_EVENT_ALLOWED_SOURCES = frozenset({"explicit_user_event_confirmation"})
EXPLICIT_USER_ITEM_EVENT_ALLOWED_STATUSES = frozenset({"user_confirmed"})
EXPLICIT_USER_ITEM_EVENT_REQUIRED_FIELDS = frozenset({"side", "item", "event_type", "status", "source"})
EXPLICIT_USER_ITEM_EVENT_OPTIONAL_FIELDS = frozenset({"turn", "note"})
EXPLICIT_USER_ITEM_EVENT_FORBIDDEN_FIELDS = frozenset(
    {
        "exact_damage",
        "exact_hp",
        "focus_sash_post_hit_hp_1",
        "berry_recovered_exact_hp",
        "item_damage_modifier_applied",
        "item_speed_modifier_applied",
        "post_turn_hp_from_item",
        "post_turn_item_state",
        "quick_claw_activated_by_rng",
        "resolved_item_effect",
        "rng_roll",
        "speed_order_override",
    }
)
USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_TYPES = frozenset(
    {
        "burn",
        "poison",
        "toxic",
        "paralysis",
        "sleep",
        "freeze",
        "none",
        "unknown",
    }
)
USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_SOURCES = frozenset({"user_confirmed_current_condition"})
USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_STATUSES = frozenset({"user_confirmed"})
USER_CONFIRMED_CURRENT_CONDITION_REQUIRED_FIELDS = frozenset(
    {"side", "condition_type", "status", "source"}
)
USER_CONFIRMED_CURRENT_CONDITION_OPTIONAL_FIELDS = frozenset({"confidence"})
USER_CONFIRMED_CURRENT_CONDITION_FORBIDDEN_FIELDS = frozenset(
    {
        "exact_status_damage",
        "exact_post_turn_hp",
        "condition_applied_this_turn",
        "condition_triggered_this_turn",
        "full_paralysis_occurred",
        "sleep_turns_remaining",
        "wake_up_turn",
        "freeze_thaw_roll",
        "rng_roll",
        "final_speed_order",
        "resolved_condition_effect",
        "post_turn_condition_state",
    }
)
USER_CONFIRMED_CURRENT_CONDITION_FUTURE_UNSUPPORTED_SOURCES = frozenset(
    {
        "explicit_user_condition_event_confirmation",
        "battle_log",
        "parser",
        "imported_replay",
        "future_turn_engine",
    }
)
USER_CONFIRMED_CURRENT_ABILITY_ALLOWED_SOURCES = frozenset({"user_confirmed_current_ability"})
USER_CONFIRMED_CURRENT_ABILITY_ALLOWED_STATUSES = frozenset({"user_confirmed"})
USER_CONFIRMED_CURRENT_ABILITY_REQUIRED_FIELDS = frozenset({"side", "ability", "status", "source"})
USER_CONFIRMED_CURRENT_ABILITY_OPTIONAL_FIELDS = frozenset({"confidence"})
USER_CONFIRMED_CURRENT_ABILITY_FORBIDDEN_FIELDS = frozenset(
    {
        "ability_activated_this_turn",
        "ability_triggered_this_turn",
        "ability_suppressed",
        "ability_replaced",
        "ability_copied",
        "ability_revealed_by_inference",
        "resolved_ability_effect",
        "exact_stat_change",
        "exact_damage_modifier",
        "exact_damage",
        "exact_post_turn_hp",
        "boosted_stat",
        "final_speed_order",
        "immunity_resolved",
        "prevention_resolved",
        "rng_roll",
        "post_turn_ability_state",
    }
)
USER_CONFIRMED_CURRENT_ABILITY_FUTURE_UNSUPPORTED_SOURCES = frozenset(
    {
        "explicit_user_ability_event_confirmation",
        "battle_log",
        "parser",
        "imported_replay",
        "future_turn_engine",
    }
)
_ABILITY_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
USER_CONFIRMED_CURRENT_STAT_STAGE_ALLOWED_SOURCES = frozenset({"user_confirmed_current_stat_stage"})
USER_CONFIRMED_CURRENT_STAT_STAGE_REQUIRED_FIELDS = frozenset({"side", "stat", "stage", "status", "source"})
USER_CONFIRMED_CURRENT_STAT_STAGE_OPTIONAL_FIELDS = frozenset({"confidence"})
USER_CONFIRMED_CURRENT_STAT_STAGE_FORBIDDEN_FIELDS = frozenset(
    {
        "stage_changed_this_turn", "stage_change_triggered", "stage_change_source",
        "ability_triggered", "item_triggered", "move_resolved", "exact_stat_value",
        "effective_stat", "exact_damage", "exact_post_turn_hp", "final_speed_order",
        "speed_tie_result", "rng_roll", "resolved_stage_effect", "post_turn_stage",
    }
)
_STAT_STAGE_ALIASES = {
    "attack": "attack", "atk": "attack", "defense": "defense", "def": "defense",
    "special-attack": "special-attack", "special attack": "special-attack", "spa": "special-attack", "sp-atk": "special-attack",
    "special-defense": "special-defense", "special defense": "special-defense", "sp-def": "special-defense",
    "speed": "speed", "spe": "speed", "accuracy": "accuracy", "evasion": "evasion",
}
USER_CONFIRMED_FINAL_BATTLE_STAT_FORBIDDEN_FIELDS = frozenset({
    "estimated_ev", "estimated_iv", "inferred_nature", "inferred_level", "inferred_item",
    "inferred_ability", "effective_stat", "stage_applied_stat", "exact_damage",
    "exact_damage_range", "ko_probability", "exact_post_turn_hp", "final_speed_order",
    "speed_tie_result", "rng_roll", "post_turn_stat", "current_hp", "current_hp_percent",
})
_FINAL_STAT_ALIASES = {
    "hp": "hp", "attack": "attack", "atk": "attack", "defense": "defense", "def": "defense",
    "special-attack": "special-attack", "special attack": "special-attack", "spa": "special-attack",
    "special-defense": "special-defense", "special defense": "special-defense", "spd": "special-defense",
    "speed": "speed", "spe": "speed",
}
USER_CONFIRMED_CURRENT_HP_FORBIDDEN_FIELDS = frozenset({"current_hp_percent", "post_turn_hp", "damage_taken", "estimated_hp", "remaining_hp_after_move", "exact_damage"})
EFFECTIVE_STAT_CALCULATION_SCOPE = "final_stat_plus_stage_only"
EFFECTIVE_STAT_EXCLUDED_MODIFIERS = (
    "priority", "item", "ability", "weather", "terrain", "tailwind", "trick-room", "rng",
)
LIMITED_DAMAGE_LEVEL = 50
LIMITED_DAMAGE_CALCULATION_SCOPE = "base_damage_stage_only"
LIMITED_DAMAGE_EXCLUDED_MODIFIERS = (
    "stab", "type-effectiveness", "critical-hit", "burn", "weather", "terrain", "screens",
    "item", "ability", "spread", "helping-hand", "friend-guard", "priority", "ko",
)
_STAGE_ADJUSTABLE_FINAL_STATS = frozenset({"attack", "defense", "special-attack", "special-defense", "speed"})
_VARIABLE_POWER_MOVE_IDS = frozenset({"acrobatics", "avalanche", "brine", "crush-grip", "electro-ball", "eruption", "facade", "flail", "fling", "frustration", "grass-knot", "gyro-ball", "heat-crash", "heavy-slam", "low-kick", "payback", "power-trip", "punishment", "return", "reversal", "stored-power", "water-spout"})
_FIXED_DAMAGE_MOVE_IDS = frozenset({"dragon-rage", "endeavor", "final-gambit", "night-shade", "psywave", "seismic-toss", "sonic-boom", "super-fang"})
_OHKO_MOVE_IDS = frozenset({"fissure", "guillotine", "horn-drill", "sheer-cold"})
_MULTI_HIT_MOVE_IDS = frozenset({"arm-thrust", "bullet-seed", "double-slap", "fury-attack", "fury-swipes", "icicle-spear", "pin-missile", "rock-blast", "tail-slap", "water-shuriken"})
USER_CONFIRMED_CURRENT_FIELD_STATE_FORBIDDEN_FIELDS = frozenset({
    "started_this_turn", "activated_this_turn", "ended_this_turn", "turns_remaining", "source_move", "source_ability", "source_item", "resolved_weather_effect", "resolved_terrain_effect", "resolved_screen_effect", "resolved_tailwind_effect", "exact_damage_modifier", "exact_damage", "exact_post_turn_hp", "effective_speed", "final_speed_order", "speed_tie_result", "rng_roll", "post_turn_field_state",
})
_FIELD_WEATHER = frozenset({"none", "sun", "rain", "sandstorm", "snow"})
_FIELD_TERRAIN = frozenset({"none", "electric", "grassy", "psychic", "misty"})
_FIELD_GLOBAL_EFFECTS = frozenset({"trick-room", "gravity"})
_FIELD_SIDE_EFFECTS = frozenset({"reflect", "light-screen", "aurora-veil", "tailwind"})


def validate_explicit_user_item_event_confirmation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a future explicit user item-event candidate without mapping it to payload."""
    if not isinstance(candidate, Mapping):
        raise ValueError("explicit user item event candidate must be a mapping")

    unexpected_fields = set(candidate) - (
        EXPLICIT_USER_ITEM_EVENT_REQUIRED_FIELDS
        | EXPLICIT_USER_ITEM_EVENT_OPTIONAL_FIELDS
        | EXPLICIT_USER_ITEM_EVENT_FORBIDDEN_FIELDS
    )
    if unexpected_fields:
        raise ValueError(f"unexpected explicit user item event field: {sorted(unexpected_fields)[0]}")

    forbidden_fields = EXPLICIT_USER_ITEM_EVENT_FORBIDDEN_FIELDS.intersection(candidate)
    if forbidden_fields:
        raise ValueError(f"explicit user item event field is forbidden: {sorted(forbidden_fields)[0]}")

    missing_fields = EXPLICIT_USER_ITEM_EVENT_REQUIRED_FIELDS - set(candidate)
    if missing_fields:
        raise ValueError(f"explicit user item event missing required field: {sorted(missing_fields)[0]}")

    side = candidate.get("side")
    if side not in {"self", "opponent"}:
        raise ValueError("explicit user item event side must be self or opponent")

    item = candidate.get("item")
    if not isinstance(item, str) or not item.strip():
        raise ValueError("explicit user item event item must be a non-empty string")

    event_type = candidate.get("event_type")
    if event_type not in EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES:
        raise ValueError("explicit user item event type is not allowed")

    status = candidate.get("status")
    if status not in EXPLICIT_USER_ITEM_EVENT_ALLOWED_STATUSES:
        raise ValueError("explicit user item event status is not allowed")

    source = candidate.get("source")
    if source not in EXPLICIT_USER_ITEM_EVENT_ALLOWED_SOURCES:
        raise ValueError("explicit user item event source is not allowed")

    sanitized = {
        "side": side,
        "item": item.strip(),
        "event_type": event_type,
        "status": status,
        "source": source,
    }

    if "turn" in candidate:
        turn = candidate["turn"]
        if turn is not None and (not isinstance(turn, int) or isinstance(turn, bool) or turn < 1):
            raise ValueError("explicit user item event turn must be a positive integer or null")
        sanitized["turn"] = turn

    if "note" in candidate:
        note = candidate["note"]
        if note is not None and not isinstance(note, str):
            raise ValueError("explicit user item event note must be a string or null")
        sanitized["note"] = note.strip() if isinstance(note, str) else None

    return sanitized


def normalize_user_confirmed_current_condition(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize only a user-confirmed current major condition for future mapping."""
    if not isinstance(candidate, Mapping):
        raise ValueError("current condition candidate must be a mapping")
    forbidden_field = _first_forbidden_condition_field(candidate)
    if forbidden_field is not None:
        raise ValueError(f"current condition field is forbidden: {forbidden_field}")

    allowed_fields = (
        USER_CONFIRMED_CURRENT_CONDITION_REQUIRED_FIELDS
        | USER_CONFIRMED_CURRENT_CONDITION_OPTIONAL_FIELDS
    )
    unexpected_fields = set(candidate) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"unexpected current condition field: {sorted(unexpected_fields)[0]}")
    missing_fields = USER_CONFIRMED_CURRENT_CONDITION_REQUIRED_FIELDS - set(candidate)
    if missing_fields:
        raise ValueError(f"current condition missing required field: {sorted(missing_fields)[0]}")

    side = candidate.get("side")
    if side not in {"self", "opponent"}:
        raise ValueError("current condition side must be self or opponent")
    condition_type = candidate.get("condition_type")
    if condition_type not in USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_TYPES:
        raise ValueError("current condition type is not allowed")
    status = candidate.get("status")
    if status not in USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_STATUSES:
        raise ValueError("current condition status is not allowed")
    source = candidate.get("source")
    if source not in USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_SOURCES:
        raise ValueError("current condition source is not allowed")
    if "confidence" in candidate and candidate["confidence"] != "known":
        raise ValueError("current condition confidence must be known")

    return {
        "side": side,
        "condition_type": condition_type,
        "status": status,
        "source": source,
        "confidence": "known",
    }


def _first_forbidden_condition_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in USER_CONFIRMED_CURRENT_CONDITION_FORBIDDEN_FIELDS:
                return str(key)
            nested = _first_forbidden_condition_field(child)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            nested = _first_forbidden_condition_field(child)
            if nested is not None:
                return nested
    return None


def normalize_user_confirmed_current_ability(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize only a user-confirmed current ability identity.

    This helper deliberately does not consult species/cache ability lists. Those
    lists describe possible species abilities, not a trusted current ability.
    """
    if not isinstance(candidate, Mapping):
        raise ValueError("current ability candidate must be a mapping")
    forbidden_field = _first_forbidden_ability_field(candidate)
    if forbidden_field is not None:
        raise ValueError(f"current ability field is forbidden: {forbidden_field}")

    allowed_fields = (
        USER_CONFIRMED_CURRENT_ABILITY_REQUIRED_FIELDS
        | USER_CONFIRMED_CURRENT_ABILITY_OPTIONAL_FIELDS
    )
    unexpected_fields = set(candidate) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"unexpected current ability field: {sorted(unexpected_fields)[0]}")
    missing_fields = USER_CONFIRMED_CURRENT_ABILITY_REQUIRED_FIELDS - set(candidate)
    if missing_fields:
        raise ValueError(f"current ability missing required field: {sorted(missing_fields)[0]}")

    side = candidate.get("side")
    if side not in {"self", "opponent"}:
        raise ValueError("current ability side must be self or opponent")
    ability = _normalize_current_ability_id(candidate.get("ability"))
    status = candidate.get("status")
    if status not in USER_CONFIRMED_CURRENT_ABILITY_ALLOWED_STATUSES:
        raise ValueError("current ability status is not allowed")
    source = candidate.get("source")
    if source not in USER_CONFIRMED_CURRENT_ABILITY_ALLOWED_SOURCES:
        raise ValueError("current ability source is not allowed")
    if "confidence" in candidate and candidate["confidence"] != "known":
        raise ValueError("current ability confidence must be known")

    return {
        "side": side,
        "ability": ability,
        "status": status,
        "source": source,
        "confidence": "known",
    }


def _normalize_current_ability_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("current ability must be a non-empty string")
    if any(delimiter in value for delimiter in (",", "/", ";", "|")):
        raise ValueError("current ability must name exactly one ability")
    normalized = re.sub(r"[\s_]+", "-", value.strip().lower())
    if normalized in {"", "none"} or _ABILITY_ID_PATTERN.fullmatch(normalized) is None:
        raise ValueError("current ability must be a canonical ability id or unknown")
    return normalized


def _first_forbidden_ability_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in USER_CONFIRMED_CURRENT_ABILITY_FORBIDDEN_FIELDS:
                return str(key)
            nested = _first_forbidden_ability_field(child)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            nested = _first_forbidden_ability_field(child)
            if nested is not None:
                return nested
    return None


def build_current_condition_context_from_confirmations(
    confirmations: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    """Build a future current-condition payload candidate without runtime mapping."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, str | bytes):
        return None
    by_side: dict[str, dict[str, Any]] = {}
    for candidate in confirmations:
        try:
            normalized = normalize_user_confirmed_current_condition(candidate)
        except ValueError:
            continue
        by_side[normalized["side"]] = normalized
    current_conditions = [by_side[side] for side in ("self", "opponent") if side in by_side]
    return {"current_conditions": current_conditions} if current_conditions else None


def build_current_ability_context_from_confirmations(
    confirmations: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    """Normalize user-confirmed current abilities for a future payload context."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, str | bytes):
        return None
    by_side: dict[str, dict[str, Any]] = {}
    for candidate in confirmations:
        try:
            normalized = normalize_user_confirmed_current_ability(candidate)
        except ValueError:
            continue
        by_side[normalized["side"]] = normalized
    current_abilities = [by_side[side] for side in ("self", "opponent") if side in by_side]
    return {"current_abilities": current_abilities} if current_abilities else None


def normalize_user_confirmed_current_stat_stage(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one user-confirmed current stat stage without resolving its cause or effect."""
    if not isinstance(candidate, Mapping):
        raise ValueError("current stat stage candidate must be a mapping")
    forbidden = _first_forbidden_stat_stage_field(candidate)
    if forbidden is not None:
        raise ValueError(f"current stat stage field is forbidden: {forbidden}")
    allowed = USER_CONFIRMED_CURRENT_STAT_STAGE_REQUIRED_FIELDS | USER_CONFIRMED_CURRENT_STAT_STAGE_OPTIONAL_FIELDS
    unexpected = set(candidate) - allowed
    if unexpected:
        raise ValueError(f"unexpected current stat stage field: {sorted(unexpected)[0]}")
    missing = USER_CONFIRMED_CURRENT_STAT_STAGE_REQUIRED_FIELDS - set(candidate)
    if missing:
        raise ValueError(f"current stat stage missing required field: {sorted(missing)[0]}")
    side = candidate.get("side")
    if side not in {"self", "opponent"}:
        raise ValueError("current stat stage side must be self or opponent")
    stat = _normalize_stat_stage_id(candidate.get("stat"))
    stage = candidate.get("stage")
    if isinstance(stage, bool) or not isinstance(stage, int) or not -6 <= stage <= 6:
        raise ValueError("current stat stage must be an integer from -6 to 6")
    if candidate.get("status") != "user_confirmed":
        raise ValueError("current stat stage status is not allowed")
    if candidate.get("source") not in USER_CONFIRMED_CURRENT_STAT_STAGE_ALLOWED_SOURCES:
        raise ValueError("current stat stage source is not allowed")
    if "confidence" in candidate and candidate["confidence"] != "known":
        raise ValueError("current stat stage confidence must be known")
    return {"side": side, "stat": stat, "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}


def _normalize_stat_stage_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("current stat stage stat must be supported")
    normalized = value.strip().lower().replace("_", "-")
    canonical = _STAT_STAGE_ALIASES.get(normalized)
    if canonical is None:
        raise ValueError("current stat stage stat must be supported")
    return canonical


def _first_forbidden_stat_stage_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in USER_CONFIRMED_CURRENT_STAT_STAGE_FORBIDDEN_FIELDS:
                return str(key)
            nested = _first_forbidden_stat_stage_field(child)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            nested = _first_forbidden_stat_stage_field(child)
            if nested is not None:
                return nested
    return None


def build_current_stat_stage_context_from_confirmations(confirmations: Sequence[Mapping[str, Any]] | None) -> dict[str, Any] | None:
    """Build a normalized current-stage context keyed by side and stat."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, str | bytes):
        return None
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in confirmations:
        try:
            normalized = normalize_user_confirmed_current_stat_stage(candidate)
        except ValueError:
            continue
        by_key[(normalized["side"], normalized["stat"])] = normalized
    stages = [by_key[key] for key in sorted(by_key, key=lambda key: (("self", "opponent").index(key[0]), key[1]))]
    return {"current_stages": stages} if stages else None


def normalize_user_confirmed_final_battle_stat(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one stage-unmodified final stat supplied by the user."""
    if not isinstance(candidate, Mapping):
        raise ValueError("final battle stat candidate must be a mapping")
    forbidden = _first_forbidden_final_stat_field(candidate)
    if forbidden is not None:
        raise ValueError(f"final battle stat field is forbidden: {forbidden}")
    required = {"side", "stat", "value", "status", "source"}
    if set(candidate) - (required | {"confidence"}):
        raise ValueError("unexpected final battle stat field")
    if required - set(candidate):
        raise ValueError("final battle stat missing required field")
    side = candidate.get("side")
    if side not in {"self", "opponent"}:
        raise ValueError("final battle stat side must be self or opponent")
    stat_value = candidate.get("stat")
    stat = _FINAL_STAT_ALIASES.get(stat_value.strip().lower().replace("_", "-") if isinstance(stat_value, str) else "")
    if stat is None:
        raise ValueError("final battle stat must be hp, attack, defense, special-attack, special-defense, or speed")
    value = candidate.get("value")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
        raise ValueError("final battle stat value must be an integer from 1 to 9999")
    if candidate.get("status") != "user_confirmed" or candidate.get("source") != "user_confirmed_final_battle_stat":
        raise ValueError("final battle stat source or status is not allowed")
    if "confidence" in candidate and candidate["confidence"] != "known":
        raise ValueError("final battle stat confidence must be known")
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _first_forbidden_final_stat_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in USER_CONFIRMED_FINAL_BATTLE_STAT_FORBIDDEN_FIELDS:
                return str(key)
            nested = _first_forbidden_final_stat_field(child)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            nested = _first_forbidden_final_stat_field(child)
            if nested is not None:
                return nested
    return None


def build_final_stat_context_from_confirmations(confirmations: Sequence[Mapping[str, Any]] | None) -> dict[str, Any] | None:
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, (str, bytes)):
        return None
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in confirmations:
        try:
            normalized = normalize_user_confirmed_final_battle_stat(candidate)
        except ValueError:
            continue
        by_key[(normalized["side"], normalized["stat"])] = normalized
    stats = [by_key[key] for key in sorted(by_key, key=lambda key: (("self", "opponent").index(key[0]), key[1]))]
    return {"current_final_stats": stats} if stats else None


def normalize_user_confirmed_current_hp(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one exact current/max HP snapshot; percent and post-turn values are excluded."""
    if not isinstance(candidate, Mapping):
        raise ValueError("current HP candidate must be a mapping")
    forbidden = next((str(key) for key in candidate if key in USER_CONFIRMED_CURRENT_HP_FORBIDDEN_FIELDS), None)
    if forbidden is not None:
        raise ValueError(f"current HP field is forbidden: {forbidden}")
    required = {"side", "current_hp", "maximum_hp", "status", "source"}
    if set(candidate) - (required | {"confidence"}) or required - set(candidate):
        raise ValueError("current HP fields are invalid")
    side, current_hp, maximum_hp = candidate.get("side"), candidate.get("current_hp"), candidate.get("maximum_hp")
    if side not in {"self", "opponent"}:
        raise ValueError("current HP side must be self or opponent")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (current_hp, maximum_hp)) or maximum_hp < 1 or current_hp < 0 or current_hp > maximum_hp:
        raise ValueError("current HP values are invalid")
    if candidate.get("status") != "user_confirmed" or candidate.get("source") != "user_confirmed_current_hp":
        raise ValueError("current HP source or status is not allowed")
    if "confidence" in candidate and candidate["confidence"] != "known":
        raise ValueError("current HP confidence must be known")
    return {"side": side, "current_hp": current_hp, "maximum_hp": maximum_hp, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"}


def build_current_hp_context_from_confirmations(confirmations: Sequence[Mapping[str, Any]] | None) -> dict[str, Any] | None:
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, (str, bytes)):
        return None
    by_side: dict[str, dict[str, Any]] = {}
    for candidate in confirmations:
        try:
            normalized = normalize_user_confirmed_current_hp(candidate)
        except ValueError:
            continue
        by_side[normalized["side"]] = normalized
    entries = [by_side[side] for side in ("self", "opponent") if side in by_side]
    return {"current_hp": entries} if entries else None


def build_deterministic_stat_inputs(
    final_stat_context: Mapping[str, Any] | None,
    stat_stage_context: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, dict[str, int]]]:
    """Expose validated inputs without applying stages or calculating outcomes."""
    result: dict[str, dict[str, dict[str, int]]] = {"base_final_stats": {}, "current_stat_stages": {}}
    if isinstance(final_stat_context, Mapping):
        for entry in final_stat_context.get("current_final_stats", []):
            if isinstance(entry, Mapping):
                normalized = normalize_user_confirmed_final_battle_stat({key: value for key, value in entry.items() if key != "confidence"})
                result["base_final_stats"].setdefault(normalized["side"], {})[normalized["stat"]] = normalized["value"]
    if isinstance(stat_stage_context, Mapping):
        for entry in stat_stage_context.get("current_stages", []):
            if isinstance(entry, Mapping):
                normalized = normalize_user_confirmed_current_stat_stage({key: value for key, value in entry.items() if key != "confidence"})
                result["current_stat_stages"].setdefault(normalized["side"], {})[normalized["stat"]] = normalized["stage"]
    return result


def calculate_stage_adjusted_stat(final_stat: int, stage: int) -> int:
    """Return the floor-rounded standard stat-stage result for a trusted final stat."""
    if isinstance(final_stat, bool) or not isinstance(final_stat, int) or final_stat < 1:
        raise ValueError("final stat must be a positive integer")
    if isinstance(stage, bool) or not isinstance(stage, int) or not -6 <= stage <= 6:
        raise ValueError("stat stage must be an integer from -6 to 6")
    if stage >= 0:
        return final_stat * (2 + stage) // 2
    return final_stat * 2 // (2 - stage)


def build_effective_stat_inputs(
    final_stat_context: Mapping[str, Any] | None,
    stat_stage_context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build deterministic stage-only results from user-confirmed input contexts.

    This deliberately does not consume species, item, ability, field, move, or
    legacy stat-profile data, and it never resolves final move order.
    """
    final_stats = build_deterministic_stat_inputs(final_stat_context, None)["base_final_stats"]
    if not final_stats:
        return None
    stages = build_deterministic_stat_inputs(None, stat_stage_context)["current_stat_stages"]
    effective_stats: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        for stat in sorted(final_stats.get(side, {})):
            if stat not in _STAGE_ADJUSTABLE_FINAL_STATS:
                continue
            base_value = final_stats[side][stat]
            stage = stages.get(side, {}).get(stat, 0)
            effective_stats.append(
                {
                    "side": side,
                    "stat": stat,
                    "base_final_value": base_value,
                    "stage": stage,
                    "effective_value": calculate_stage_adjusted_stat(base_value, stage),
                    "calculation_status": "resolved",
                }
            )
    return {
        "calculation_status": "resolved",
        "calculation_scope": EFFECTIVE_STAT_CALCULATION_SCOPE,
        "excluded_modifiers": list(EFFECTIVE_STAT_EXCLUDED_MODIFIERS),
        "effective_stats": effective_stats,
        "speed_comparison": build_speed_comparison_result(effective_stats),
    }


def build_speed_comparison_result(effective_stats: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare only resolved stage-adjusted speed; never determine move order."""
    speeds: dict[str, int] = {}
    for entry in effective_stats:
        if entry.get("stat") == "speed" and entry.get("side") in {"self", "opponent"}:
            value = entry.get("effective_value")
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                speeds[entry["side"]] = value
    result: dict[str, Any] = {
        "calculation_scope": "stage_only",
        "calculation_status": "resolved" if len(speeds) == 2 else "unavailable",
        "result": "unavailable",
    }
    if "self" in speeds:
        result["self_effective_speed"] = speeds["self"]
    if "opponent" in speeds:
        result["opponent_effective_speed"] = speeds["opponent"]
    if len(speeds) != 2:
        return result
    if speeds["self"] > speeds["opponent"]:
        result["result"] = "self_faster"
    elif speeds["self"] < speeds["opponent"]:
        result["result"] = "opponent_faster"
    else:
        result["result"] = "tie"
    return result


def build_deterministic_calculation_context(
    final_stat_context: Mapping[str, Any] | None,
    stat_stage_context: Mapping[str, Any] | None = None,
    selected_move: Mapping[str, Any] | None = None,
    current_hp_context: Mapping[str, Any] | None = None,
    pokemon: Mapping[str, Any] | None = None,
    condition_context: Mapping[str, Any] | None = None,
    field_state_context: Mapping[str, Any] | None = None,
    battle_format_context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Combine trusted stats with separately-scoped base and type-aware results."""
    context = build_effective_stat_inputs(final_stat_context, stat_stage_context)
    if context is None:
        return None
    estimate = build_limited_damage_estimate(context["effective_stats"], selected_move)
    type_estimate = build_type_aware_damage_estimate(estimate, pokemon)
    context_estimate = build_context_modified_damage_estimate(type_estimate, condition_context, field_state_context, battle_format_context)
    # Preserve the v13.3 result as a distinct calculator intermediate.  When
    # type sources resolve, the primary acknowledgement/result is type-aware.
    primary_estimate = context_estimate if context_estimate and context_estimate.get("calculation_status") == "resolved" else (type_estimate if type_estimate and type_estimate.get("calculation_status") == "resolved" else estimate)
    hp_assessment = build_hp_ko_assessment(primary_estimate, current_hp_context)
    return {
        **context,
        "base_damage_estimates": [estimate] if estimate is not None else [],
        "type_aware_damage_estimates": [type_estimate] if type_estimate is not None else [],
        "context_modified_damage_estimates": [context_estimate] if context_estimate is not None else [],
        "damage_estimates": [primary_estimate] if primary_estimate is not None else [],
        "hp_assessments": [hp_assessment] if hp_assessment is not None else [],
    }


def build_limited_damage_estimate(
    effective_stats: Sequence[Mapping[str, Any]], selected_move: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Return one base-damage-only range, never legacy or modifier-resolved damage."""
    if not isinstance(selected_move, Mapping):
        return None
    move_id = selected_move.get("move_id")
    category = selected_move.get("category")
    power = selected_move.get("power")
    move_type = selected_move.get("type") or selected_move.get("type_en")
    base = {
        "attacker_side": "self",
        "defender_side": "opponent",
        "move": move_id if isinstance(move_id, str) and move_id else "unknown",
        "damage_class": category if isinstance(category, str) else "unknown",
        "move_type": move_type.strip().lower() if isinstance(move_type, str) else None,
        "calculation_scope": LIMITED_DAMAGE_CALCULATION_SCOPE,
        "excluded_modifiers": list(LIMITED_DAMAGE_EXCLUDED_MODIFIERS),
    }
    if not isinstance(move_id, str) or not move_id:
        return {**base, "calculation_status": "unavailable", "reason": "missing_move_id"}
    if move_id in _OHKO_MOVE_IDS:
        return {**base, "calculation_status": "unsupported_move", "reason": "ohko"}
    if move_id in _FIXED_DAMAGE_MOVE_IDS:
        return {**base, "calculation_status": "unsupported_move", "reason": "fixed_damage"}
    if move_id in _MULTI_HIT_MOVE_IDS:
        return {**base, "calculation_status": "unsupported_move", "reason": "multi_hit_unresolved"}
    if move_id in _VARIABLE_POWER_MOVE_IDS or selected_move.get("power_status") == "variable":
        return {**base, "calculation_status": "unsupported_move", "reason": "variable_power"}
    if category == "status":
        return {**base, "calculation_status": "unsupported_move", "reason": "status_move"}
    if category not in {"physical", "special"}:
        return {**base, "calculation_status": "unavailable", "reason": "missing_move_category"}
    if isinstance(power, bool) or not isinstance(power, int) or power < 1:
        return {**base, "calculation_status": "unavailable", "reason": "missing_move_power"}
    stat = ("attack", "defense") if category == "physical" else ("special-attack", "special-defense")
    values = {(entry.get("side"), entry.get("stat")): entry.get("effective_value") for entry in effective_stats if isinstance(entry, Mapping)}
    offense, defense = values.get(("self", stat[0])), values.get(("opponent", stat[1]))
    if isinstance(offense, bool) or not isinstance(offense, int) or offense < 1:
        return {**base, "power": power, "level": LIMITED_DAMAGE_LEVEL, "calculation_status": "unavailable", "reason": "missing_offensive_stat"}
    if isinstance(defense, bool) or not isinstance(defense, int) or defense < 1:
        return {**base, "power": power, "level": LIMITED_DAMAGE_LEVEL, "offensive_stat": offense, "calculation_status": "unavailable", "reason": "missing_defensive_stat"}
    unmodified_base = base_damage(LIMITED_DAMAGE_LEVEL, power, offense, defense)
    rolls = [unmodified_base * random_factor // 100 for random_factor in range(85, 101)]
    return {
        **base,
        "power": power,
        "level": LIMITED_DAMAGE_LEVEL,
        "offensive_stat": offense,
        "defensive_stat": defense,
        "min_damage": min(rolls),
        "max_damage": max(rolls),
        "calculation_status": "resolved",
    }


TYPE_AWARE_DAMAGE_CALCULATION_SCOPE = "base_damage_stage_stab_type"
_TYPE_RATIOS = {0.0: (0, 1), 0.25: (1, 4), 0.5: (1, 2), 1.0: (1, 1), 2.0: (2, 1), 4.0: (4, 1)}


def build_type_aware_damage_estimate(
    base_estimate: Mapping[str, Any] | None, pokemon: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Apply only ordinary STAB and the base chart to the v13.3 raw-roll path."""
    if not isinstance(base_estimate, Mapping):
        return None
    result = {key: value for key, value in base_estimate.items() if key != "excluded_modifiers"}
    result.update({
        "calculation_scope": TYPE_AWARE_DAMAGE_CALCULATION_SCOPE,
        "excluded_modifiers": ["ability", "item", "weather", "terrain", "screens", "burn", "critical-hit", "tera", "type-changing-effects", "survival-effects", "between-turn-effects"],
    })
    if base_estimate.get("calculation_status") != "resolved":
        return result
    move_type = _normalized_type(base_estimate.get("move_type"))
    # v13.3's selected-move result intentionally did not retain type; callers
    # attach it below from the trusted selected move when available.
    if move_type is None:
        return {**result, "calculation_status": "unavailable", "reason": "missing_move_type"}
    attacker_types = _selected_types(pokemon, "my_active")
    defender_types = _selected_types(pokemon, "opponent_active")
    if attacker_types is None:
        return {**result, "calculation_status": "unavailable", "reason": "missing_attacker_type"}
    if defender_types is None:
        return {**result, "calculation_status": "unavailable", "reason": "missing_defender_type"}
    chart = load_type_chart()
    try:
        multiplier = 1.0
        for defender_type in defender_types:
            multiplier *= chart[move_type][defender_type]
        numerator, denominator = _TYPE_RATIOS[multiplier]
    except (KeyError, TypeError):
        return {**result, "calculation_status": "unavailable", "reason": "unknown_type"}
    stab_q12 = calc_stab(attacker_types, move_type, is_terastallized=False, tera_type=None)
    rolls = _damage_rolls_from_estimate(base_estimate)
    if rolls is None:
        return {**result, "calculation_status": "unavailable", "reason": "missing_damage_rolls"}
    typed_rolls = [(apply_damage_modifier(roll, stab_q12) * numerator) // denominator for roll in rolls]
    return {
        **result,
        "move_type": move_type,
        "attacker_types": list(attacker_types),
        "defender_types": list(defender_types),
        "stab": {"applied": stab_q12 == M_STAB, "numerator": 3 if stab_q12 == M_STAB else 1, "denominator": 2 if stab_q12 == M_STAB else 1},
        "type_effectiveness": {"numerator": numerator, "denominator": denominator, "label": _type_label(numerator, denominator)},
        "min_damage": min(typed_rolls), "max_damage": max(typed_rolls),
        "damage_rolls": typed_rolls,
        "calculation_status": "resolved",
    }


def _normalized_type(value: object) -> str | None:
    return value.strip().lower() if isinstance(value, str) and value.strip().lower() in TYPES else None


def _selected_types(pokemon: Mapping[str, Any] | None, side: str) -> tuple[str, ...] | None:
    active = pokemon.get(side) if isinstance(pokemon, Mapping) else None
    raw = active.get("types") if isinstance(active, Mapping) else None
    if not isinstance(raw, list) or not raw:
        return None
    normalized = tuple(item.strip().lower() for item in raw if isinstance(item, str) and item.strip().lower() in TYPES)
    return normalized if len(normalized) == len(raw) and len(normalized) <= 2 else None


def _type_label(numerator: int, denominator: int) -> str:
    return {(0, 1): "immune", (1, 4): "quarter-effective", (1, 2): "resisted", (1, 1): "neutral", (2, 1): "super-effective", (4, 1): "quadruple-effective"}[(numerator, denominator)]


def _damage_rolls_from_estimate(estimate: Mapping[str, Any]) -> list[int] | None:
    raw = estimate.get("damage_rolls")
    if isinstance(raw, list) and len(raw) == 16 and all(isinstance(value, int) and not isinstance(value, bool) for value in raw):
        return list(raw)
    values = tuple(estimate.get(key) for key in ("level", "power", "offensive_stat", "defensive_stat"))
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        return None
    return [base_damage(*values) * factor // 100 for factor in range(85, 101)]


CONTEXT_DAMAGE_CALCULATION_SCOPE = "base_damage_stage_stab_type_context"


def build_context_modified_damage_estimate(
    type_estimate: Mapping[str, Any] | None,
    condition_context: Mapping[str, Any] | None,
    field_state_context: Mapping[str, Any] | None,
    battle_format_context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Apply only trusted burn, ordinary rain/sun, and singles screens."""
    if not isinstance(type_estimate, Mapping):
        return None
    if condition_context is None and field_state_context is None:
        return None
    result = dict(type_estimate)
    result["calculation_scope"] = CONTEXT_DAMAGE_CALCULATION_SCOPE
    if type_estimate.get("calculation_status") != "resolved":
        return result
    conditions = condition_context.get("current_conditions") if isinstance(condition_context, Mapping) else []
    field = field_state_context.get("current_field") if isinstance(field_state_context, Mapping) else None
    if conditions is None: conditions = []
    if field is None: field = {"weather": "none", "side_effects": []}
    if not isinstance(conditions, list) or not isinstance(field, Mapping):
        return {**result, "calculation_status": "unavailable", "reason": "unresolved_context_state"}
    category, move_type = result.get("damage_class"), result.get("move_type")
    burned = any(isinstance(entry, Mapping) and entry.get("side") == "self" and entry.get("condition_type") == "burn" for entry in conditions)
    burn_q12 = 2048 if burned and category == "physical" else Q12_ONE
    weather = field.get("weather")
    if weather not in {"none", "rain", "sun", "sandstorm", "snow"}:
        return {**result, "calculation_status": "unavailable", "reason": "unknown_weather"}
    weather_q12 = weather_modifier(str(move_type), str(weather)) if weather in {"rain", "sun"} else Q12_ONE
    side_effects = field.get("side_effects", [])
    if not isinstance(side_effects, list):
        return {**result, "calculation_status": "unavailable", "reason": "unresolved_screen_state"}
    defender_screens = {entry.get("effect") for entry in side_effects if isinstance(entry, Mapping) and entry.get("side") == "opponent"}
    if any(entry.get("side") not in {"self", "opponent"} for entry in side_effects if isinstance(entry, Mapping)):
        return {**result, "calculation_status": "unavailable", "reason": "invalid_screen_side"}
    applicable = "reflect" if category == "physical" and "reflect" in defender_screens else ("light-screen" if category == "special" and "light-screen" in defender_screens else "aurora-veil" if "aurora-veil" in defender_screens else None)
    # No trusted battle-format field exists. A present screen therefore cannot
    # be silently treated as singles or doubles.
    battle_format = battle_format_context.get("battle_format") if isinstance(battle_format_context, Mapping) else None
    if applicable is not None and battle_format not in {"singles", "doubles"}:
        return {**result, "calculation_status": "unavailable", "reason": "missing_battle_format_for_screen"}
    rolls = _damage_rolls_from_estimate(result)
    if rolls is None:
        return {**result, "calculation_status": "unavailable", "reason": "missing_damage_rolls"}
    screen_q12 = screen_modifier(SideField(reflect="reflect" in defender_screens, light_screen="light-screen" in defender_screens, aurora_veil="aurora-veil" in defender_screens), category == "physical", False, battle_format == "doubles") if applicable else Q12_ONE
    rolls = [apply_damage_modifier(apply_damage_modifier(apply_damage_modifier(roll, burn_q12), weather_q12), screen_q12) for roll in rolls]
    return {**result, "burn_modifier": {"applied": burn_q12 != Q12_ONE, "numerator": 1, "denominator": 2 if burn_q12 != Q12_ONE else 1}, "weather_modifier": {"weather": weather, "numerator": {6144: 3, 2048: 1}.get(weather_q12, 1), "denominator": {6144: 2, 2048: 2}.get(weather_q12, 1)}, "screen_modifier": {"applied": applicable is not None, "screen": applicable, "battle_format": battle_format, "numerator": 2 if screen_q12 != Q12_ONE and battle_format == "doubles" else 1, "denominator": 3 if screen_q12 != Q12_ONE and battle_format == "doubles" else 2 if screen_q12 != Q12_ONE else 1}, "damage_rolls": rolls, "min_damage": min(rolls), "max_damage": max(rolls), "calculation_status": "resolved"}


def normalize_user_confirmed_battle_format(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping) or set(candidate) - {"battle_format", "source", "confidence"} or candidate.get("battle_format") not in {"singles", "doubles"} or candidate.get("source") != "user_confirmed_battle_format":
        raise ValueError("battle format is invalid")
    if candidate.get("confidence", "known") != "known":
        raise ValueError("battle format confidence is invalid")
    return {"battle_format": candidate["battle_format"], "source": "user_confirmed_battle_format", "confidence": "known"}


def build_hp_ko_assessment(
    damage_estimate: Mapping[str, Any] | None, current_hp_context: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Assess user-confirmed current HP against v13.3's unchanged 16-roll range only."""
    if not isinstance(damage_estimate, Mapping) or damage_estimate.get("calculation_status") != "resolved":
        return None
    hp_entries = current_hp_context.get("current_hp") if isinstance(current_hp_context, Mapping) else None
    if not isinstance(hp_entries, list):
        return None
    defender = damage_estimate.get("defender_side")
    hp = next((entry for entry in hp_entries if isinstance(entry, Mapping) and entry.get("side") == defender), None)
    if hp is None:
        return None
    try:
        normalized = normalize_user_confirmed_current_hp(hp)
    except ValueError:
        return None
    rolls = _damage_rolls_from_estimate(damage_estimate)
    if rolls is None:
        return None
    current_hp, maximum_hp = normalized["current_hp"], normalized["maximum_hp"]
    base_result = {
        "attacker_side": damage_estimate["attacker_side"], "defender_side": defender, "move": damage_estimate["move"],
        "current_hp": current_hp, "maximum_hp": maximum_hp,
        "min_damage": min(rolls), "max_damage": max(rolls),
        "min_percent": round(min(rolls) * 100 / maximum_hp, 1), "max_percent": round(max(rolls) * 100 / maximum_hp, 1),
        "percentage_scope": str(damage_estimate.get("calculation_scope", LIMITED_DAMAGE_CALCULATION_SCOPE)),
        "calculation_scope": str(damage_estimate.get("calculation_scope", LIMITED_DAMAGE_CALCULATION_SCOPE)),
    }
    if current_hp == 0:
        return {**base_result, "calculation_status": "resolved", "assessment_status": "not_applicable", "reason": "target_already_fainted"}
    ohko_successes = sum(damage >= current_hp for damage in rolls)
    two_hit_successes = sum(first + second >= current_hp for first in rolls for second in rolls)
    def status(successes: int, total: int) -> str:
        return "guaranteed" if successes == total else "possible" if successes else "impossible"
    return {
        **base_result,
        "ohko": {"successful_rolls": ohko_successes, "total_rolls": 16, "chance_percent": ohko_successes * 100 / 16, "status": status(ohko_successes, 16), "scope": str(damage_estimate.get("calculation_scope", LIMITED_DAMAGE_CALCULATION_SCOPE))},
        "two_hit_ko": {"successful_combinations": two_hit_successes, "total_combinations": 256, "chance_percent": two_hit_successes * 100 / 256, "status": status(two_hit_successes, 256), "scope": "two-hit-independent-rolls-no-between-turn-effects"},
        "calculation_status": "resolved", "assessment_status": "resolved",
    }


def normalize_user_confirmed_current_field_state(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a snapshot of user-confirmed current field identities only."""
    if not isinstance(candidate, Mapping):
        raise ValueError("current field state must be a mapping")
    forbidden = _first_forbidden_field_state_field(candidate)
    if forbidden is not None:
        raise ValueError(f"current field state field is forbidden: {forbidden}")
    required = {"weather", "terrain", "global_effects", "side_effects", "status", "source"}
    allowed = required | {"confidence"}
    unexpected, missing = set(candidate) - allowed, required - set(candidate)
    if unexpected:
        raise ValueError(f"unexpected current field state field: {sorted(unexpected)[0]}")
    if missing:
        raise ValueError(f"current field state missing required field: {sorted(missing)[0]}")
    weather, terrain = candidate.get("weather"), candidate.get("terrain")
    if weather not in _FIELD_WEATHER or terrain not in _FIELD_TERRAIN:
        raise ValueError("current field weather or terrain is not supported")
    if candidate.get("status") != "user_confirmed" or candidate.get("source") != "user_confirmed_current_field_state":
        raise ValueError("current field state source or status is not allowed")
    if "confidence" in candidate and candidate["confidence"] != "known":
        raise ValueError("current field state confidence must be known")
    global_effects = candidate.get("global_effects")
    if not isinstance(global_effects, list) or any(effect not in _FIELD_GLOBAL_EFFECTS for effect in global_effects):
        raise ValueError("current field global effects are not supported")
    if len(set(global_effects)) != len(global_effects):
        raise ValueError("current field global effects must not duplicate")
    side_effects = candidate.get("side_effects")
    if not isinstance(side_effects, list):
        raise ValueError("current field side effects must be a list")
    normalized_side: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in side_effects:
        if not isinstance(entry, Mapping) or set(entry) != {"side", "effect"}:
            raise ValueError("current field side effect is invalid")
        side, effect = entry.get("side"), entry.get("effect")
        if side not in {"self", "opponent"} or effect not in _FIELD_SIDE_EFFECTS or (side, effect) in seen:
            raise ValueError("current field side effect is invalid")
        seen.add((side, effect)); normalized_side.append({"side": side, "effect": effect})
    return {"weather": weather, "terrain": terrain, "global_effects": sorted(global_effects), "side_effects": sorted(normalized_side, key=lambda value: (("self", "opponent").index(value["side"]), value["effect"])), "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}


def _first_forbidden_field_state_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in USER_CONFIRMED_CURRENT_FIELD_STATE_FORBIDDEN_FIELDS:
                return str(key)
            nested = _first_forbidden_field_state_field(child)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            nested = _first_forbidden_field_state_field(child)
            if nested is not None:
                return nested
    return None


def build_item_event_context_from_confirmations(
    confirmations: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    """Normalize explicit user observed item events for the limited payload path."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, str | bytes):
        return None

    observed_events: list[dict[str, Any]] = []
    for candidate in confirmations:
        try:
            normalized = validate_explicit_user_item_event_confirmation(candidate)
        except ValueError:
            continue
        observed_events.append({**normalized, "confidence": "observed"})

    return {"observed_events": observed_events} if observed_events else None


def build_battle_state_context(
    *,
    self_active: Mapping[str, Any] | None = None,
    opponent_active: Mapping[str, Any] | None = None,
    field: Mapping[str, Any] | None = None,
    known_conditions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a safe battle-state context from caller-provided visible facts."""
    normalized_self = _active_side(self_active)
    normalized_opponent = _active_side(opponent_active)
    normalized_field = _field_state(field)
    normalized_conditions = _known_conditions(known_conditions)

    return {
        "kind": "battle_state_context",
        "confidence": _confidence(
            self_active=normalized_self,
            opponent_active=normalized_opponent,
            field=normalized_field,
            known_conditions=normalized_conditions,
        ),
        "self_active": normalized_self,
        "opponent_active": normalized_opponent,
        "field": normalized_field,
        "known_conditions": normalized_conditions,
        "unsupported": list(BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES),
        "safety_notes": list(BATTLE_STATE_CONTEXT_SAFETY_NOTES),
    }


def build_battle_state_context_from_ui_selected_state(
    battle_input: Mapping[str, Any] | None,
    *,
    include_user_confirmed_items: bool = False,
    include_user_confirmed_fields: bool = False,
) -> dict[str, Any]:
    """Build battle-state context from the current UI-selected payload shape.

    By default this adapter extracts only visible species and HP percent.
    User-confirmed item and field profiles are included only through explicit
    opt-ins. It does not read damage estimates, KO context, move context, or
    other optional contexts.
    """
    pokemon = battle_input.get("pokemon") if isinstance(battle_input, Mapping) else None
    pokemon = pokemon if isinstance(pokemon, Mapping) else {}
    self_active = _active_side_from_ui_pokemon(pokemon.get("my_active"))
    opponent_active = _active_side_from_ui_pokemon(pokemon.get("opponent_active"))

    if include_user_confirmed_items:
        item_profiles = battle_input.get("item_profiles") if isinstance(battle_input, Mapping) else None
        item_profiles = item_profiles if isinstance(item_profiles, Mapping) else {}
        self_item = _item_from_ui_item_profile(item_profiles.get("my_active"))
        opponent_item = _item_from_ui_item_profile(item_profiles.get("opponent_active"))
        if self_item is not None:
            self_active["item"] = self_item
        if opponent_item is not None:
            opponent_active["item"] = opponent_item

    field = None
    if include_user_confirmed_fields:
        field_profiles = battle_input.get("field_profiles") if isinstance(battle_input, Mapping) else None
        field = build_field_state_from_field_profiles(field_profiles if isinstance(field_profiles, Mapping) else None)

    return build_battle_state_context(
        self_active=self_active,
        opponent_active=opponent_active,
        field=field,
    )


def build_field_state_from_field_profiles(field_profiles: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize Field Profile Dialog metadata into field state."""
    field_profiles = field_profiles if isinstance(field_profiles, Mapping) else {}
    field: dict[str, Any] = {}
    for field_name in BATTLE_STATE_CONTEXT_FIELD_FIELDS:
        entry = _field_entry_from_profile(field_name, field_profiles.get(field_name))
        if entry is not None:
            field[field_name] = entry
    return _field_state(field)


def _confidence(
    *,
    self_active: Mapping[str, Any],
    opponent_active: Mapping[str, Any],
    field: Mapping[str, Any],
    known_conditions: Sequence[Mapping[str, Any]],
) -> str:
    if _has_known_source(self_active) or _has_known_source(opponent_active) or _has_known_source(field) or known_conditions:
        return "limited"
    return "unknown"


def _active_side_from_ui_pokemon(pokemon: object) -> dict[str, Any]:
    if not isinstance(pokemon, Mapping):
        return {}

    active: dict[str, Any] = {}
    name = pokemon.get("name_en")
    if isinstance(name, str) and name.strip():
        active["species"] = {"source": "visible_ui", "name": name.strip()}

    hp_percent = pokemon.get("hp_percent")
    if isinstance(hp_percent, int | float) and not isinstance(hp_percent, bool):
        active["current_hp_percent"] = {"source": "visible_ui", "value": hp_percent}

    return active


def _item_from_ui_item_profile(profile: object) -> dict[str, Any] | None:
    if not isinstance(profile, Mapping):
        return None
    if profile.get("status") != "user_confirmed" or profile.get("source") != "user_input":
        return None
    item_id = profile.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip():
        return None
    return {"source": "user_confirmed", "value": item_id.strip()}


def _field_entry_from_profile(field_name: str, profile: object) -> dict[str, Any] | None:
    if not isinstance(profile, Mapping):
        return None
    if profile.get("status") != "user_confirmed" or profile.get("source") != "user_input":
        return None
    value = profile.get("value")
    if isinstance(value, str):
        value = value.strip()
        if not value or value == "unknown":
            return None
    elif value is None:
        return None
    entry = {"source": "user_confirmed", "value": value}
    if not _field_value_is_allowed(field_name, value):
        return None
    return entry


def _active_side(active: Mapping[str, Any] | None) -> dict[str, Any]:
    active = active or {}
    return {
        "species": _source_name_or_unknown(active.get("species")),
        "current_hp_percent": _source_value_or_unknown(active.get("current_hp_percent")),
        "status": _known_value_or_unknown(active.get("status")),
        "boosts": _known_value_or_unknown(active.get("boosts")),
        "item": _known_item_or_unknown(active.get("item")),
    }


def _field_state(field: Mapping[str, Any] | None) -> dict[str, Any]:
    field = field or {}
    return {
        key: _known_field_value_or_unknown(key, field.get(key))
        for key in BATTLE_STATE_CONTEXT_FIELD_FIELDS
    }


def _known_conditions(conditions: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if conditions is None:
        return []

    normalized: list[dict[str, Any]] = []
    for condition in conditions:
        if not isinstance(condition, Mapping):
            continue
        if not _source_is_allowed(condition.get("source")):
            continue
        sanitized = _sanitize_value(condition)
        if isinstance(sanitized, dict):
            normalized.append(sanitized)
    return normalized


def _source_name_or_unknown(entry: object) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        return _unknown_field()
    source = entry.get("source")
    name = entry.get("name")
    if not _source_is_allowed(source) or name is None:
        return _unknown_field()
    return {"source": str(source), "name": _sanitize_value(name)}


def _source_value_or_unknown(entry: object) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        return _unknown_field()
    source = entry.get("source")
    value = entry.get("value")
    if not _source_is_allowed(source) or value is None:
        return _unknown_field()
    return {"source": str(source), "value": _sanitize_value(value)}


def _known_value_or_unknown(entry: object) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        return _unknown_field()
    source = entry.get("source")
    value = entry.get("value")
    if not _source_is_allowed(source) or value is None:
        return _unknown_field()
    return {"known": True, "source": str(source), "value": _sanitize_value(value)}


def _known_item_or_unknown(entry: object) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        return _unknown_field()
    source = entry.get("source")
    value = entry.get("value")
    if not isinstance(source, str) or source not in BATTLE_STATE_CONTEXT_ITEM_ALLOWED_SOURCES or value is None:
        return _unknown_field()
    return {"known": True, "source": source, "value": _sanitize_value(value)}


def _known_field_value_or_unknown(field_name: str, entry: object) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        return _unknown_field()
    if entry.get("known") is False:
        return _unknown_field()
    source = entry.get("source")
    value = entry.get("value")
    if not isinstance(source, str) or source not in BATTLE_STATE_CONTEXT_FIELD_ALLOWED_SOURCES or value is None:
        return _unknown_field()
    if not _field_value_is_allowed(field_name, value):
        return _unknown_field()
    return {"known": True, "source": source, "value": _sanitize_value(value)}


def _field_value_is_allowed(field_name: str, value: object) -> bool:
    if field_name in {"screens", "hazards"}:
        return _side_specific_field_value_is_allowed(value)
    if field_name in {"weather", "terrain"}:
        return isinstance(value, str) and bool(value.strip())
    if field_name == "room":
        return _simple_field_value_is_allowed(value)
    return False


def _simple_field_value_is_allowed(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value) and all(isinstance(key, str) and key.strip() for key in value)
    return False


def _side_specific_field_value_is_allowed(value: object) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    if not set(value).issubset({"self", "opponent"}):
        return False
    if not all(_side_specific_condition_list_is_allowed(side_value) for side_value in value.values()):
        return False
    if any(_side_specific_condition_list_has_known_value(side_value) for side_value in value.values()):
        return True
    return set(value) == {"self", "opponent"} and all(
        isinstance(side_value, Sequence) and not isinstance(side_value, (str, bytes))
        for side_value in value.values()
    )


def _side_specific_condition_list_is_allowed(value: object) -> bool:
    if value == "unknown":
        return True
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return all(isinstance(entry, str) and bool(entry.strip()) for entry in value)
    return False


def _side_specific_condition_list_has_known_value(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and any(value)


def _source_is_allowed(source: object) -> bool:
    return isinstance(source, str) and source in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES


def _has_known_source(value: object) -> bool:
    if isinstance(value, Mapping):
        source = value.get("source")
        if isinstance(source, str) and source in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
            return True
        return any(_has_known_source(child_value) for child_value in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_has_known_source(child_value) for child_value in value)
    return False


def _sanitize_value(value: object) -> object:
    if isinstance(value, Mapping):
        source = value.get("source")
        if source in BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES:
            return _unknown_field()
        sanitized: dict[str, Any] = {}
        for key, child_value in value.items():
            if key in BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS:
                continue
            if key == "source" and child_value in BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES:
                continue
            sanitized[str(key)] = _sanitize_value(child_value)
        return sanitized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_sanitize_value(child_value) for child_value in value]
    return value


def _unknown_field() -> dict[str, Any]:
    return dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD)
