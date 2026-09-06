from __future__ import annotations
from typing import Any, Mapping

_MOVES={"thief":("dark",60),"covet":("normal",60)}
def resolve_canonical_item_transfer_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None
 if mid not in _MOVES:return {"status":"unsupported","move_id":mid,"reason":"move_not_in_item_transfer_catalog"}
 typ,power=_MOVES[mid]; effect={"move_id":mid,"type":typ,"category":"physical","base_power":power,"accuracy":100,"priority":0,"contact":True,"protection_blockable":True,"family":"item_transfer_after_hit"}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
 return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-item-transfer-moves-v1"}
