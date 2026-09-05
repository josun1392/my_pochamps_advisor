"""Closed catalog for ordinary single-target damaging drain moves."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-drain-move-family-v1"
_FRACTIONS = {
    **{move: (1, 2) for move in ("absorb", "mega-drain", "giga-drain", "drain-punch", "horn-leech", "leech-life", "bitter-blade", "parabolic-charge")},
    "draining-kiss": (3, 4), "oblivion-wing": (3, 4),
}

def resolve_canonical_drain_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id: return {**base, "status":"incomplete", "reason":"canonical_move_identity_unknown"}
    fraction = _FRACTIONS.get(move_id)
    if fraction is None: return {**base, "status":"unsupported", "reason":"move_not_in_drain_move_catalog"}
    if not isinstance(move, Mapping) or move.get("category") not in {"physical", "special"}: return {**base, "status":"rejected", "reason":"catalog_metadata_category_mismatch"}
    return {**base, "status":"resolved", "effect":{"move_id":move_id,"drain_family":"ordinary_damage_drain","drain_numerator":fraction[0],"drain_denominator":fraction[1]}, "provenance":"canonical-maintained-drain-family-v1"}
