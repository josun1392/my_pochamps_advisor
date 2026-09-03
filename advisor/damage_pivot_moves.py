"""Canonical post-damage self-switch capability for the supported pivot family."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_PIVOT_MOVE_IDS = frozenset({"u-turn", "volt-switch", "flip-turn"})


def canonical_damage_pivot_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached metadata view with one narrowly owned pivot flag."""
    result = deepcopy(dict(metadata))
    result["self_switch_after_successful_attack"] = result.get("move_id") in _PIVOT_MOVE_IDS
    return result


def is_canonical_damage_pivot(metadata: Any) -> bool:
    return (
        isinstance(metadata, Mapping)
        and metadata.get("move_id") in _PIVOT_MOVE_IDS
        and metadata.get("self_switch_after_successful_attack") is True
    )
