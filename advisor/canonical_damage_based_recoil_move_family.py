"""Closed catalog for ordinary moves whose recoil tracks actual target HP loss."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-damage-based-recoil-family-v1"
_FRACTIONS = {
    "wild-charge": (1, 4), "take-down": (1, 4),
    **{move: (1, 3) for move in ("brave-bird", "double-edge", "flare-blitz", "wood-hammer", "wave-crash", "volt-tackle", "head-charge")},
    "head-smash": (1, 2), "light-of-ruin": (1, 2),
}

def resolve_canonical_damage_based_recoil_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id: return {**base,"status":"incomplete","reason":"canonical_move_identity_unknown"}
    fraction = _FRACTIONS.get(move_id)
    if fraction is None: return {**base,"status":"unsupported","reason":"move_not_in_damage_based_recoil_catalog"}
    if not isinstance(move, Mapping) or move.get("category") not in {"physical","special"}: return {**base,"status":"rejected","reason":"catalog_metadata_category_mismatch"}
    return {**base,"status":"resolved","effect":{"move_id":move_id,"recoil_family":"damage_based_recoil","recoil_numerator":fraction[0],"recoil_denominator":fraction[1],"minimum_recoil":1},"provenance":"canonical-maintained-damage-based-recoil-family-v1"}
