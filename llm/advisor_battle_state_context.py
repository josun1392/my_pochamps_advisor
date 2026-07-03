"""Source-bound battle state context helper.

This helper normalizes visible or explicit battle-state facts into a limited
context. It does not infer hidden items, spreads, boosts, status, field state,
post-turn HP, RNG results, or full turn outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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
        "post_turn_hp",
        "item_consumed",
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
    """Normalize future Field Profile Dialog metadata into field state.

    This helper is intentionally not wired into the UI-selected payload path.
    It only locks the future `field_profiles` contract before dialog UI and
    runtime mapping are implemented.
    """
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
