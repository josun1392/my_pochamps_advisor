"""Closed canonical owner for Final Gambit's self-current-HP damage."""
from __future__ import annotations
from typing import Any, Mapping
SCHEMA_VERSION="canonical-final-gambit-self-hp-damage-family-v1"
_MOVE={"move_id":"final-gambit","type":"fighting","category":"special","accuracy":100,"contact":False}
def resolve_canonical_final_gambit_self_hp_damage_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 move_id=move.get("move_id") if isinstance(move,Mapping) else None;base={"schema_version":SCHEMA_VERSION,"move_id":move_id}
 if not isinstance(move_id,str) or not move_id:return {**base,"status":"incomplete","reason":"canonical_move_identity_unknown"}
 if move_id!="final-gambit":return {**base,"status":"unsupported","reason":"move_not_in_final_gambit_catalog"}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in _MOVE.items() if k in move):return {**base,"status":"rejected","reason":"catalog_metadata_mismatch"}
 return {**base,"status":"resolved","effect":{**_MOVE,"family":"self_current_hp_damage","self_sacrifice":"final_gambit_self_sacrifice"},"provenance":"canonical-maintained-final-gambit-self-hp-family-v1"}
