from __future__ import annotations
from typing import Any, Mapping
def resolve_canonical_defensive_stat_override_damage_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    mid=move.get("move_id") if isinstance(move,Mapping) else None
    if mid!="psyshock": return {"status":"unsupported","move_id":mid,"reason":"move_not_in_defensive_stat_override_catalog"}
    effect={"move_id":"psyshock","type":"psychic","category":"special","power":80,"accuracy":100,"priority":0,"contact":False,"protection_blockable":True,"family":"defensive_stat_override","offensive_stat_owner":"user","offensive_stat_name":"special-attack","defensive_stat_owner":"target","defensive_stat_name":"defense"}
    if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move): return {"status":"rejected","move_id":mid,"reason":"catalog_metadata_mismatch"}
    return {"status":"resolved","move_id":mid,"effect":effect,"provenance":"canonical-defensive-stat-override-damage-family-v1"}
