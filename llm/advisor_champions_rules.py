"""Canonical Pokémon Champions battle-rules metadata for trusted snapshot inputs."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

CHAMPIONS_RULES_CONTEXT = "pokemon-champions-2026"
CHAMPIONS_BATTLE_LEVEL = 50
_RULE_SOURCE = "deterministic_rules_metadata"
_RULE_TRUST = "deterministic_rules_metadata"


def build_champions_trusted_level_context(
    *,
    rules_context: str,
    session_id: str,
    pokemon: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]] | None:
    """Materialize identity-bound Level 50 authority only for the supported Champions ruleset."""
    if rules_context != CHAMPIONS_RULES_CONTEXT:
        return None
    if not isinstance(session_id, str) or not session_id:
        return None
    if not isinstance(pokemon, Mapping):
        return None

    rows: list[dict[str, Any]] = []
    for side, key in (("self", "my_active"), ("opponent", "opponent_active")):
        active = pokemon.get(key)
        if not isinstance(active, Mapping):
            return None
        slot_index = active.get("slot_index")
        pokemon_id = active.get("name_en")
        if (
            isinstance(slot_index, bool)
            or not isinstance(slot_index, int)
            or slot_index < 0
            or not isinstance(pokemon_id, str)
            or not pokemon_id
        ):
            return None
        rows.append({
            "side": side,
            "value": CHAMPIONS_BATTLE_LEVEL,
            "provenance": {
                "side": side,
                "slot_index": slot_index,
                "pokemon_id": pokemon_id,
                "session_id": session_id,
                "source": _RULE_SOURCE,
                "trust": _RULE_TRUST,
            },
        })
    return {"current_levels": deepcopy(rows)}
