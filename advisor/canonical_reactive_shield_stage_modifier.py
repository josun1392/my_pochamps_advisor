"""Narrow maintained modifier facts for reactive-shield stage interactions."""
from __future__ import annotations

from typing import Any


def canonical_reactive_shield_stage_ability_interaction(ability_id: Any) -> str | None:
    """Return only a verified target-side outcome; unknown abilities stay unknown."""
    return {
        "contrary": "reversed",
        "clear-body": "prevented",
        "white-smoke": "prevented",
        "full-metal-body": "prevented",
        "pressure": "applies",
    }.get(ability_id) if isinstance(ability_id, str) else None


def canonical_reactive_shield_stage_source_ignore_state(ability_id: Any) -> str | None:
    """This bounded resolver recognizes only a maintained non-ignoring source."""
    return "does_not_ignore_target_ability" if ability_id == "pressure" else None
