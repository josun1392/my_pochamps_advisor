"""Maintained canonical execution-scope metadata for one doubles spread move."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


_PATH = Path(__file__).parents[1] / "data" / "static" / "multi_recipient_action_execution_scopes.json"
_EXPECTED = {
    "rock-slide": {
        "canonical_target_class": "all-opponents",
        "recipient_classification": "spread_multi_target",
        "recipient_resolution_order": "frozen_target_set_order",
        "spread_damage_modifier": {"numerator": 3, "denominator": 4, "applies_when_recipient_count_at_least": 2},
        "accuracy_uncertainty_scope": "recipient_local",
        "critical_hit_uncertainty_scope": "recipient_local",
        "damage_roll_uncertainty_scope": "recipient_local",
    }
}


def canonical_multi_recipient_action_execution_metadata(move_id: Any) -> dict[str, Any] | None:
    expected = _EXPECTED.get(move_id)
    if expected is None:
        return None
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        row = data.get("moves", {}).get(move_id) if isinstance(data, Mapping) else None
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("schema_version") != "canonical-multi-recipient-action-execution-scopes-v1" or not isinstance(row, Mapping) or any(row.get(key) != value for key, value in expected.items()):
        return None
    return {"move_id": move_id, **deepcopy(dict(row))}
