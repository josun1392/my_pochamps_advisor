from __future__ import annotations
from typing import Any, Mapping
def resolve_canonical_user_status_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid!="facade":return {"status":"unsupported","move_id":mid,"reason":"move_not_in_user_status_power_catalog"}
 effect={"move_id":"facade","type":"normal","category":"physical","base_power":70,"boosted_power":140,"accuracy":100,"priority":0,"contact":True,"protection_blockable":True,"family":"user_status_power","qualifying_conditions":("burn","poison","toxic","paralysis")}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-user-status-power-family-v1"}
