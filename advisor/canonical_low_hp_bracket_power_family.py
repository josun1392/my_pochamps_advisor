"""Closed Flail/Reversal metadata; evaluation remains the existing HP owner."""
from __future__ import annotations
from typing import Any,Mapping
_MOVES={"flail":{"type":"normal"},"reversal":{"type":"fighting"}}
def resolve_canonical_low_hp_bracket_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid not in _MOVES:return {"status":"unsupported","move_id":mid,"reason":"move_not_in_low_hp_bracket_power_catalog"}
 effect={"move_id":mid,"category":"physical","power":20,"accuracy":100,"priority":0,"contact":True,**_MOVES[mid],"family":"current_hp_bracket_power"}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-low-hp-bracket-power-family-v1"}
