from __future__ import annotations
from typing import Any,Mapping
SCHEMA_VERSION="canonical-rage-fist-hit-count-power-family-v1"
_MOVE={"move_id":"rage-fist","type":"ghost","category":"physical","power":50,"accuracy":100,"priority":0,"contact":True}
def resolve_canonical_rage_fist_hit_count_power_move(*,move:Mapping[str,Any]|Any)->dict[str,Any]:
 mid=move.get("move_id") if isinstance(move,Mapping) else None;base={"schema_version":SCHEMA_VERSION,"move_id":mid}
 if mid!="rage-fist":return {**base,"status":"unsupported","reason":"move_not_in_rage_fist_hit_count_catalog"}
 if not isinstance(move,Mapping) or any(move.get(k)!=v for k,v in _MOVE.items() if k in move):return {**base,"status":"rejected","reason":"catalog_metadata_mismatch"}
 return {**base,"status":"resolved","effect":{**_MOVE,"family":"persistent_received_hit_count","count_cap":6,"boost_per_hit":50,"maximum_power":350},"provenance":"canonical-maintained-rage-fist-hit-count-power-family-v1"}
