from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
SCHEMA_VERSION="runtime-d0-rage-fist-hit-count-authority-v1"
def freeze_runtime_d0_rage_fist_hit_count_authority(*,strategy_d0:Mapping[str,Any],runtime_snapshot:Mapping[str,Any],owner:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(strategy_d0,Mapping) or strategy_d0.get("status")!="resolved" or strategy_d0.get("active_owners",{}).get(owner.get("side"))!=dict(owner):return {"status":"rejected","schema_version":SCHEMA_VERSION,"reason":"rage_fist_owner_binding_invalid"}
 fresh=runtime_strategy_d0_freshness(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot)
 if fresh.get("status")!="current":return {"status":"rejected","schema_version":SCHEMA_VERSION,"reason":fresh.get("reason","stale_runtime_d0")}
 state=runtime_snapshot.get("state",{});p=state.get(f"{owner['side']}_side",{}).get("pokemon",{}).get(owner["slot_index"])
 base={"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(strategy_d0["decision_owner"]),"owner":deepcopy(dict(owner))}
 row=p.get("rage_fist_hit_count") if isinstance(p,Mapping) and p.get("pokemon_id")==owner.get("pokemon_id") else None
 if row is None:return {"status":"incomplete","schema_version":SCHEMA_VERSION,**base,"reason":"rage_fist_hit_count_uninitialized"}
 if not isinstance(row,Mapping) or row.get("owner")!=dict(owner) or not isinstance(row.get("count"),int) or isinstance(row.get("count"),bool) or row["count"]<0:return {"status":"rejected","schema_version":SCHEMA_VERSION,**base,"reason":"rage_fist_hit_count_invalid"}
 return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"battle_received_hit_count":row["count"],"counter_provenance":deepcopy(row.get("provenance")),"provenance":"strict_runtime_d0_rage_fist_hit_count_v1"}
