"""Checked-in canonical Mat Block direct-damage protection metadata."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "mat_block_protection_effects.json"

def canonical_mat_block_protection_metadata(move_id: Any) -> dict[str, Any] | None:
    if move_id != "mat-block": return None
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        rule = data.get("moves", {}).get("mat-block") if isinstance(data, Mapping) else None
    except (OSError, ValueError): return None
    if not isinstance(rule, Mapping) or rule.get("protection_class") != "active_entry_direct_damage_guard" or rule.get("requires_explicit_active_entry_eligibility") is not True or rule.get("supported_incoming_categories") != ["physical", "special"]: return None
    return {"move_id": "mat-block", **dict(rule)}
