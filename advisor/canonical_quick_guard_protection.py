"""Maintained canonical metadata for Quick Guard applicability."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

_PATH = Path(__file__).parents[1] / "data" / "static" / "quick_guard_protection_effects.json"
_RULE = {"protects_side": True, "protection_kind": "priority_action_guard", "requires_positive_effective_priority": True, "blocks_supported_direct_damage": True}


def canonical_quick_guard_protection_metadata(move_id: Any) -> dict[str, Any] | None:
    if move_id != "quick-guard":
        return None
    try:
        row = json.loads(_PATH.read_text(encoding="utf-8")).get("moves", {}).get(move_id)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(row, Mapping) or any(row.get(key) != value for key, value in _RULE.items()):
        return None
    return {"move_id": move_id, **deepcopy(dict(row))}
