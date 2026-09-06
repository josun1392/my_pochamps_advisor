from __future__ import annotations
from typing import Any,Mapping
_MOVES={"electro-ball":{"type":"electric","category":"special","contact":False},"gyro-ball":{"type":"steel","category":"physical","contact":True}}
def resolve_canonical_speed_relation_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid not in _MOVES:return {"status":"unsupported","move_id":mid,"reason":"move_not_in_speed_relation_power_catalog"}
 effect={"move_id":mid,"accuracy":100,"priority":0,"family":"speed_ratio_power",**_MOVES[mid]}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-speed-relation-power-family-v1"}
