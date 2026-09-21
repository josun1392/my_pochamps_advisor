"""Pinned terminal-move facts for the bounded standard-charge continuation.

Recognition is deliberately separate from execution.  The detached turn-two
owner must still authenticate an existing continuation before it can consume
these facts.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from advisor.canonical_charge_move_lifecycle import COMMIT, resolve_canonical_charge_move_lifecycle


SCHEMA_VERSION = "canonical-standard-charge-turn-two-effects-v1"

_EFFECTS = {
    "sky-attack": {"power": 140, "category": "physical", "type": "flying", "accuracy": 90, "crit_ratio": 2, "secondary": {"kind": "flinch", "chance": 30}},
    "razor-wind": {"power": 80, "category": "special", "type": "normal", "accuracy": 100, "crit_ratio": 2, "secondary": {"kind": "none", "chance": 0}},
    "freeze-shock": {"power": 140, "category": "physical", "type": "ice", "accuracy": 90, "crit_ratio": 1, "secondary": {"kind": "status", "condition": "paralysis", "chance": 30}},
    "ice-burn": {"power": 140, "category": "special", "type": "ice", "accuracy": 90, "crit_ratio": 1, "secondary": {"kind": "status", "condition": "burn", "chance": 30}},
    "solar-beam": {"power": 120, "category": "special", "type": "grass", "accuracy": 100, "crit_ratio": 1, "secondary": {"kind": "none", "chance": 0}},
    "solar-blade": {"power": 125, "category": "physical", "type": "grass", "accuracy": 100, "crit_ratio": 1, "secondary": {"kind": "none", "chance": 0}},
}


def resolve_canonical_standard_charge_turn_two_effect(move_id: Any) -> dict[str, Any]:
    """Return only the bounded audited Showdown terminal effects.

    The lifecycle resolver hash-authenticates the vendored Showdown source at
    ``COMMIT``.  Its move proof is retained as source provenance here.
    """
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    if lifecycle.get("status") != "resolved":
        return {"status": lifecycle.get("status", "rejected"), "schema_version": SCHEMA_VERSION, "reason": lifecycle.get("reason", "canonical_charge_lifecycle_unavailable")}
    normalized = lifecycle["move_id"]
    effect = _EFFECTS.get(normalized)
    allowed_family = (
        "weather_sensitive_charge_then_damage"
        if normalized in {"solar-beam", "solar-blade"}
        else "ordinary_charge_then_damage"
    )
    if effect is None or lifecycle.get("lifecycle_family") != allowed_family:
        return {"status": "unsupported", "schema_version": SCHEMA_VERSION, "move_id": normalized, "reason": "move_not_in_standard_charge_turn_two_effect_inventory"}
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "move_id": normalized, "move": {"move_id": normalized, "power": effect["power"], "category": effect["category"], "type": effect["type"], "accuracy": effect["accuracy"], "target": "selected-pokemon", "effect_chance": effect["secondary"]["chance"], "ailment": effect["secondary"].get("condition", effect["secondary"]["kind"])},
        "crit_ratio": effect["crit_ratio"], "secondary": deepcopy(effect["secondary"]),
        "lifecycle": lifecycle, "source_provenance": {"repository": "https://github.com/smogon/pokemon-showdown", "commit_sha": COMMIT, "move_block": deepcopy(lifecycle["source_provenance"]["move_block"])},
        "provenance": "authenticated_pinned_showdown_standard_charge_turn_two_effect_v1",
    }
