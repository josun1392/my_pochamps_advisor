from __future__ import annotations
from typing import Any, Mapping
def resolve_canonical_user_held_item_absence_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid!="acrobatics":return {"status":"unsupported","move_id":mid,"reason":"move_not_in_user_held_item_absence_catalog"}
 effect={"move_id":"acrobatics","type":"flying","category":"physical","base_power":55,"boosted_power":110,"accuracy":100,"priority":0,"contact":True,"protection_blockable":True,"family":"user_held_item_absence_power"}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-user-held-item-absence-power-v1"}
