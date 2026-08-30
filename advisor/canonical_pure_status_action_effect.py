"""Strict maintained classification for the small pure-status v1 catalog."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-pure-status-action-effect-v1"
_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "pure_status_action_effects.json"


def resolve_canonical_pure_status_action_effect(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id:
        return _result("incomplete", "canonical_move_identity_unknown", base)
    row = _catalog().get(move_id)
    if not isinstance(row, Mapping):
        return _result("unsupported", "move_not_in_pure_status_action_catalog", base)
    if not isinstance(move, Mapping):
        return _result("incomplete", "canonical_move_metadata_unknown", base)
    for key in ("category", "target"):
        if move.get(key) != row.get(key):
            return _result("rejected", f"catalog_metadata_{key}_mismatch", base)
    if row.get("consequence_family") != "target_stage_change" or row.get("stat") != "defense" or row.get("delta") != -1:
        return _result("rejected", "canonical_pure_status_effect_row_invalid", base)
    return {**base, "status": "resolved", "effect": deepcopy(dict(row)),
            "provenance": "canonical-maintained-gen9-mechanics-catalog-v1"}


def _catalog() -> Mapping[str, Any]:
    try:
        value = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value.get("moves", {}) if isinstance(value, Mapping) else {}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {**base, "status": status, "reason": reason}
