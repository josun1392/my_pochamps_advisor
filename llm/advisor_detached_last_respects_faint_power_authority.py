from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from advisor.canonical_last_respects_faint_power_family import resolve_canonical_last_respects_faint_power_move
def materialize_detached_last_respects_faint_power_authority(*,strategy_d0:Mapping[str,Any],move:Mapping[str,Any],user:Mapping[str,Any],history_authority:Mapping[str,Any])->dict[str,Any]:
 c=resolve_canonical_last_respects_faint_power_move(move=move)
 if c.get("status")!="resolved":return {"status":c.get("status","rejected"),"reason":c.get("reason")}
 if not isinstance(history_authority,Mapping) or history_authority.get("status")!="resolved" or history_authority.get("owner")!=user:return {"status":"incomplete","reason":"last_respects_faint_history_authority_missing"}
 raw=history_authority.get("raw_allied_faint_count")
 if not isinstance(raw,int) or isinstance(raw,bool) or raw<0:return {"status":"rejected","reason":"last_respects_raw_faint_count_invalid"}
 return {"status":"resolved","schema_version":"detached-last-respects-faint-power-authority-v1","session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"user":deepcopy(dict(user)),"user_side":user["side"],"move_id":"last-respects","trigger_family":"allied_faint_history","raw_allied_faint_count":raw,"resolved_fainted_allies_count":raw,"canonical_cap":None,"selected_base_power":50+50*raw,"history_authority":deepcopy(dict(history_authority)),"rule":deepcopy(c["effect"]),"provenance":"exact_d0_shared_raw_faint_history_last_respects_v1"}
