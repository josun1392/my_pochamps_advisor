"""Closed metadata owner for Avalanche and Revenge's same-turn power rule."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION="canonical-was-damaged-power-family-v1"
_MOVES={
 "avalanche":{"move_id":"avalanche","type":"ice","category":"physical","power":60,"accuracy":100,"priority":-4,"contact":True},
 "revenge":{"move_id":"revenge","type":"fighting","category":"physical","power":60,"accuracy":100,"priority":-4,"contact":True},
}
def resolve_canonical_was_damaged_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None; base={"schema_version":SCHEMA_VERSION,"move_id":mid}
 if not isinstance(mid,str) or not mid:return {**base,"status":"incomplete","reason":"canonical_move_identity_unknown"}
 effect=_MOVES.get(mid)
 if effect is None:return {**base,"status":"unsupported","reason":"move_not_in_was_damaged_power_catalog"}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in effect.items() if k in move):return {**base,"status":"rejected","reason":"catalog_metadata_mismatch"}
 return {**base,"status":"resolved","effect":{**effect,"family":"was_damaged_same_turn_power","boosted_power":120,"condition":"target_caused_positive_direct_hp_damage_earlier_this_turn"},"provenance":"canonical-maintained-was-damaged-power-family-v1"}
