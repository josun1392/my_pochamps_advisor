"""Maintained canonical metadata for Spiky Shield's blocked-contact damage."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


_PATH = Path(__file__).parents[1] / "data" / "static" / "spiky_shield_reactive_damage_effects.json"
_EFFECT = {
    "owner": "blocked_attacker",
    "basis": "maximum_hp",
    "numerator": 1,
    "denominator": 8,
    "rounding": "floor",
    "minimum_damage": 1,
}


def canonical_spiky_shield_reactive_damage_metadata(move_id: Any) -> dict[str, Any] | None:
    """Return only the exact maintained Spiky Shield damage rule."""
    if move_id != "spiky-shield":
        return None
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        row = data.get("moves", {}).get(move_id)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(row, Mapping) or row.get("protects_self") is not True:
        return None
    if row.get("blocks_supported_direct_damage") is not True:
        return None
    if row.get("reactive_contact_damage") != _EFFECT:
        return None
    return {"move_id": move_id, **deepcopy(dict(row))}
