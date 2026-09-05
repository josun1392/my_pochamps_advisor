"""Closed current-HP fractional damage catalog."""
from __future__ import annotations
from typing import Any, Mapping
SCHEMA_VERSION="canonical-fractional-target-hp-damage-family-v1"
_MOVES={"super-fang":{"type":"normal","category":"physical","accuracy":90,"contact":True},"natures-madness":{"type":"fairy","category":"special","accuracy":90,"contact":False},"ruination":{"type":"dark","category":"special","accuracy":90,"contact":False}}
def resolve_canonical_fractional_target_hp_damage_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
    move_id=move.get("move_id") if isinstance(move,Mapping) else None;base={"schema_version":SCHEMA_VERSION,"move_id":move_id}
    if not isinstance(move_id,str) or not move_id:return {**base,"status":"incomplete","reason":"canonical_move_identity_unknown"}
    row=_MOVES.get(move_id)
    if row is None:return {**base,"status":"unsupported","reason":"move_not_in_fractional_target_hp_catalog"}
    if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in row.items() if k in move):return {**base,"status":"rejected","reason":"catalog_metadata_mismatch"}
    return {**base,"status":"resolved","effect":{"move_id":move_id,"family":"current_hp_fraction_damage","numerator":1,"denominator":2,"minimum_damage":1,**row},"provenance":"canonical-maintained-fractional-target-hp-family-v1"}
