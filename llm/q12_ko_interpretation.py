"""Read-only deterministic KO interpretation for already-resolved damage ranges."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from llm.advisor_battle_state_context import normalize_user_confirmed_current_hp


_SUPPORTED_DAMAGE_MODELS = frozenset({"single_hit_formula", "fixed_hit_formula", "level_based_fixed"})
_PRIMARY_LABELS = (
    ("guaranteed_ohko", "guaranteed", 1), ("possible_ohko", "possible", 1),
    ("guaranteed_2hko", "guaranteed", 2), ("possible_2hko", "possible", 2),
    ("guaranteed_3hko", "guaranteed", 3), ("possible_3hko", "possible", 3),
)


def resolve_exact_defender_current_hp(*, current_hp_context: Any, defender_side: str) -> dict[str, Any] | None:
    """Resolve the same request-start HP authority used by deterministic KO evidence."""
    if defender_side not in {"self", "opponent"}:
        raise ValueError("invalid defender side")
    if current_hp_context is None:
        return None
    if not isinstance(current_hp_context, Mapping):
        return {"ko_supportability": "unsupported_mechanic", "reason": "defender_hp_authority"}
    entries = current_hp_context.get("current_hp")
    if not isinstance(entries, list):
        return {"ko_supportability": "insufficient_context", "missing_inputs": [f"{defender_side}.current_hp"]}
    matching = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == defender_side]
    if len(matching) == 0:
        return {"ko_supportability": "insufficient_context", "missing_inputs": [f"{defender_side}.current_hp"]}
    if len(matching) != 1:
        return {"ko_supportability": "unsupported_mechanic", "reason": "defender_hp_authority"}
    entry = matching[0]
    if entry.get("state") == "unknown":
        return {"ko_supportability": "insufficient_context", "missing_inputs": [f"{defender_side}.current_hp"]}
    try:
        hp = normalize_user_confirmed_current_hp({key: value for key, value in entry.items() if key != "provenance"})
    except (TypeError, ValueError):
        return {"ko_supportability": "unsupported_mechanic", "reason": "defender_hp_authority"}
    if hp["current_hp"] == 0:
        return {"ko_supportability": "not_applicable", "reason": "target_already_fainted"}
    return {"current_hp": hp["current_hp"], "defender_hp_authority": "exact_current_hp"}


def evaluate_q12_ko_interpretation(*, mechanics_result: Mapping[str, Any], current_hp_context: Any, defender_side: str) -> dict[str, Any] | None:
    """Derive bounded KO evidence without changing damage or candidate usability."""
    if defender_side not in {"self", "opponent"}:
        raise ValueError("invalid defender side")
    if mechanics_result.get("status") != "known":
        return {"ko_supportability": "not_applicable", "reason": "damage_supportability"}
    if mechanics_result.get("damage_model") not in _SUPPORTED_DAMAGE_MODELS:
        return {"ko_supportability": "not_applicable", "reason": "unsupported_damage_model"}
    damage_range = mechanics_result.get("damage_range")
    if not isinstance(damage_range, Mapping):
        return {"ko_supportability": "unsupported_mechanic", "reason": "damage_range"}
    minimum, maximum = damage_range.get("minimum"), damage_range.get("maximum")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (minimum, maximum)) or minimum < 0 or maximum < minimum:
        return {"ko_supportability": "unsupported_mechanic", "reason": "damage_range"}
    hp = resolve_exact_defender_current_hp(current_hp_context=current_hp_context, defender_side=defender_side)
    if hp is None:
        return None
    if "ko_supportability" in hp:
        return hp
    current = hp["current_hp"]
    horizons = {turns: "guaranteed" if turns * minimum >= current else "possible" if turns * maximum >= current else "no" for turns in (1, 2, 3)}
    primary = next((label for label, result, turns in _PRIMARY_LABELS if horizons[turns] == result), "no_ko_within_supported_horizon")
    return {"ko_supportability": "complete", "defender_hp_authority": "exact_current_hp", "ko_damage_range_basis": "server_owned_total_damage_range", "ohko_result": horizons[1], "two_hko_result": horizons[2], "three_hko_result": horizons[3], "primary_ko_label": primary}
