"""Maintained canonical metadata for Baneful Bunker's blocked-contact poison."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


_PATH = Path(__file__).parents[1] / "data" / "static" / "baneful_bunker_reactive_poison_effects.json"
_EFFECT = {
    "owner": "blocked_attacker",
    "condition_before": "none",
    "condition_after": "poison",
    "trigger": "baneful_bunker_successful_blocked_contact",
}


def canonical_baneful_bunker_reactive_poison_metadata(move_id: Any) -> dict[str, Any] | None:
    """Return only the exact maintained Baneful Bunker reactive condition rule."""
    if move_id != "baneful-bunker":
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
    if row.get("reactive_contact_condition") != _EFFECT:
        return None
    return {"move_id": move_id, **deepcopy(dict(row))}
