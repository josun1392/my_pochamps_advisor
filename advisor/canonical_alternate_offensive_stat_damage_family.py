from __future__ import annotations
from typing import Any, Mapping
_MOVES = {"body-press": {"type":"fighting","category":"physical","power":80,"offensive_stat_owner":"user","offensive_stat_name":"defense"}, "foul-play": {"type":"dark","category":"physical","power":95,"offensive_stat_owner":"target","offensive_stat_name":"attack"}}
def resolve_canonical_alternate_offensive_stat_damage_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    if move_id not in _MOVES: return {"status":"unsupported","move_id":move_id,"reason":"move_not_in_alternate_offensive_stat_catalog"}
    effect = {"move_id":move_id,"accuracy":100,"priority":0,"contact":True,"protection_blockable":True,"family":"alternate_offensive_stat",**_MOVES[move_id]}
    if not isinstance(move, Mapping) or any(move.get(k) != v for k,v in effect.items() if k in move): return {"status":"rejected","move_id":move_id,"reason":"catalog_metadata_mismatch"}
    return {"status":"resolved","move_id":move_id,"effect":effect,"provenance":"canonical-alternate-offensive-stat-damage-family-v1"}
