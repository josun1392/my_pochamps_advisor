"""Closed canonical metadata for Lash Out's same-turn stage-drop rule."""
from __future__ import annotations
from typing import Any, Mapping
SCHEMA_VERSION="canonical-same-turn-stat-drop-power-family-v1"
_MOVE={"move_id":"lash-out","type":"dark","category":"physical","power":75,"accuracy":100,"priority":0,"contact":True}
def resolve_canonical_same_turn_stat_drop_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
    mid=move.get("move_id") if isinstance(move,Mapping) else None; base={"schema_version":SCHEMA_VERSION,"move_id":mid}
    if mid!="lash-out": return {**base,"status":"unsupported","reason":"move_not_in_same_turn_stat_drop_power_catalog"}
    if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in _MOVE.items() if k in move): return {**base,"status":"rejected","reason":"catalog_metadata_mismatch"}
    return {**base,"status":"resolved","effect":{**_MOVE,"family":"same_turn_user_stat_was_lowered_power","boosted_power":150,"condition":"user_stat_stage_actually_lowered_earlier_this_turn"},"provenance":"canonical-maintained-same-turn-stat-drop-power-family-v1"}
