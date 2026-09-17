"""Conservative support boundary for Trace copied-ability runtime writeback.

Trace itself can copy many abilities.  Writing the copied identity into current
runtime is exact only when gaining that ability has no additional immediate
state transition that this bounded switch-entry transaction would need to
materialize.  Reuse the project's existing ability categories and admit only
continuous/passive families; everything else stays fail-closed.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any


_SAFE_PASSIVE_CATEGORIES = frozenset({
    "ability_suppress",
    "ally_immunity",
    "bp_modifier",
    "damage_mod_dual",
    "damage_mod_flag",
    "damage_mod_hp",
    "damage_mod_not_very_effective",
    "damage_mod_super_effective",
    "damage_mod_type",
    "move_flag_immunity",
    "multihit_modifier",
    "residual_immunity",
    "stat_multiplier",
    "stat_multiplier_status",
    "status_reflect",
    "type_dual_effect",
    "type_immunity",
    "type_immunity_redirect",
    "weather_suppress",
    "wonder_guard",
})
# These alter separately-owned current authority immediately on acquisition;
# ability identity alone is therefore insufficient for an exact writeback.
_REQUIRES_ADDITIONAL_CURRENT_AUTHORITY = frozenset({
    "levitate",
})


def resolve_trace_runtime_copy_support(copied_ability: Any) -> dict[str, Any]:
    """Classify one exact copied ability for this bounded runtime writeback."""
    if not isinstance(copied_ability, str) or not copied_ability:
        return {"status": "rejected", "reason": "trace_copied_ability_invalid"}
    categories = _ability_categories()
    if categories is None:
        return {"status": "incomplete", "reason": "trace_copy_support_catalog_unavailable"}
    if copied_ability in _REQUIRES_ADDITIONAL_CURRENT_AUTHORITY:
        return {
            "status": "unsupported",
            "reason": "trace_copied_ability_additional_current_authority_required",
            "copied_ability": copied_ability,
        }
    matches = sorted(category for category in _SAFE_PASSIVE_CATEGORIES if copied_ability in categories.get(category, ()))
    if not matches:
        return {
            "status": "unsupported",
            "reason": "trace_copied_ability_followup_unsupported",
            "copied_ability": copied_ability,
        }
    return {
        "status": "resolved",
        "copied_ability": copied_ability,
        "supporting_categories": matches,
        "provenance": "champions_ability_categories_passive_trace_writeback_v1",
    }


@lru_cache(maxsize=1)
def _ability_categories() -> dict[str, tuple[str, ...]] | None:
    path = Path(__file__).resolve().parents[1] / "data" / "static" / "ability_categories.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    categories = raw.get("categories") if isinstance(raw, dict) else None
    if raw.get("version") != "champions-2026" or not isinstance(categories, dict):
        return None
    result: dict[str, tuple[str, ...]] = {}
    for name, values in categories.items():
        if not isinstance(name, str) or not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            return None
        result[name] = tuple(values)
    return result
