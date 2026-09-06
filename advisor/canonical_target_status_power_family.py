from __future__ import annotations
from typing import Any, Mapping
_MOVES={"hex":{"type":"ghost","category":"special","contact":False,"qualifier":"any_major_status"},"venoshock":{"type":"poison","category":"special","contact":False,"qualifier":"poison_or_toxic"}}
def resolve_canonical_target_status_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid not in _MOVES:return {"status":"unsupported","move_id":mid,"reason":"move_not_in_target_status_power_catalog"}
 effect={"move_id":mid,"base_power":65,"boosted_power":130,"accuracy":100,"priority":0,"protection_blockable":True,"family":"target_status_power",**_MOVES[mid]}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-target-status-power-family-v1"}
