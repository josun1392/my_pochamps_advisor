"""Closed Eruption/Water Spout execution-time HP-ratio metadata."""
from __future__ import annotations
from typing import Any,Mapping
_MOVES={"eruption":{"type":"fire","category":"special"},"water-spout":{"type":"water","category":"special"}}
def resolve_canonical_current_hp_ratio_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid not in _MOVES:return {"status":"unsupported","move_id":mid,"reason":"move_not_in_current_hp_ratio_power_catalog"}
 expected={"move_id":mid,"power":150,"accuracy":100,"priority":0,"contact":False,**_MOVES[mid]}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in expected.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":{**expected,"family":"current_hp_ratio_power","numerator_constant":150,"minimum_power":1},"provenance":"canonical-current-hp-ratio-power-family-v1"}
