from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
SCHEMA_VERSION="runtime-d0-last-respects-faint-history-authority-v1"
def freeze_runtime_d0_last_respects_faint_history_authority(*,strategy_d0:Mapping[str,Any],runtime_snapshot:Mapping[str,Any],owner:Mapping[str,Any])->dict[str,Any]:
 base={"session_id":strategy_d0.get("session_id"),"source_runtime_fingerprint":strategy_d0.get("source_runtime_fingerprint"),"source_branch_fingerprint":strategy_d0.get("strategy_preview_fingerprint"),"decision_owner":deepcopy(strategy_d0.get("decision_owner",{})),"owner":deepcopy(dict(owner))}
 if not isinstance(strategy_d0,Mapping) or strategy_d0.get("status")!="resolved" or strategy_d0.get("active_owners",{}).get(owner.get("side"))!=dict(owner):return {"status":"rejected","schema_version":SCHEMA_VERSION,**base,"reason":"last_respects_owner_identity_invalid"}
 if runtime_strategy_d0_freshness(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot).get("status")!="current":return {"status":"rejected","schema_version":SCHEMA_VERSION,**base,"reason":"stale_runtime_d0"}
 h=runtime_snapshot.get("state",{}).get("supreme_overlord_faint_history_context") if isinstance(runtime_snapshot,Mapping) else None
 if not isinstance(h,Mapping) or owner.get("side") not in h.get("initialized_sides",[]):return {"status":"incomplete","schema_version":SCHEMA_VERSION,**base,"reason":"allied_faint_history_missing"}
 raw=h.get("side_counts",{}).get(owner["side"])
 if not isinstance(raw,int) or isinstance(raw,bool) or raw<0:return {"status":"rejected","schema_version":SCHEMA_VERSION,**base,"reason":"allied_faint_history_invalid"}
 return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"user_side":owner["side"],"raw_allied_faint_count":raw,"provenance":"strict_runtime_d0_shared_raw_faint_history_v1"}
