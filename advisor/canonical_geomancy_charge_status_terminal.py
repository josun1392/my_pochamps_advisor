"""Authenticated canonical terminal facts for the bounded Geomancy charge family."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle

SCHEMA_VERSION = "canonical-geomancy-charge-status-terminal-v1"
_MOVE = {
    "move_id": "geomancy",
    "category": "status",
    "power": 0,
    "accuracy": True,
    "target": "self",
    "type": "fairy",
}
_BOOSTS = {
    "special-attack": 2,
    "special-defense": 2,
    "speed": 2,
}


def resolve_canonical_geomancy_charge_status_terminal(move_id: Any) -> dict[str, Any]:
    if not isinstance(move_id, str) or move_id.strip().lower().replace("_", "-").replace(" ", "-") != "geomancy":
        return {
            "status": "unsupported",
            "schema_version": SCHEMA_VERSION,
            "reason": "move_not_geomancy",
        }
    lifecycle = resolve_canonical_charge_move_lifecycle("geomancy")
    if lifecycle.get("status") != "resolved":
        return {
            "status": lifecycle.get("status", "rejected"),
            "schema_version": SCHEMA_VERSION,
            "reason": lifecycle.get("reason", "geomancy_canonical_lifecycle_unavailable"),
        }
    expected = {
        "move_id": "geomancy",
        "lifecycle_family": "charge_then_status_terminal",
        "execution_model": "other_two_turn",
        "terminal_effect_class": "self_stat_change",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "power_herb_eligible": True,
        "power_herb_charge_skip_possible": True,
        "canonical_recognition_grants_immediate_execution": False,
    }
    if any(lifecycle.get(key) != value for key, value in expected.items()):
        return {
            "status": "rejected",
            "schema_version": SCHEMA_VERSION,
            "reason": "geomancy_canonical_lifecycle_mismatch",
        }
    proof = lifecycle.get("source_provenance", {}).get("move_block")
    tokens = set(proof.get("move_specific_tokens", ())) if isinstance(proof, dict) else set()
    required = {
        'accuracy: true', 'basePower: 0', 'category: "Status"', 'boosts: {',
        'spa: 2', 'spd: 2', 'spe: 2', 'target: "self"', 'type: "Fairy"',
    }
    if not required.issubset(tokens):
        return {
            "status": "rejected",
            "schema_version": SCHEMA_VERSION,
            "reason": "geomancy_pinned_terminal_source_proof_incomplete",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "move_id": "geomancy",
        "move": deepcopy(_MOVE),
        "boosts": deepcopy(_BOOSTS),
        "lifecycle": deepcopy(dict(lifecycle)),
        "source_provenance": deepcopy(dict(lifecycle["source_provenance"])),
        "provenance": "authenticated_pinned_showdown_geomancy_status_terminal_v1",
    }
