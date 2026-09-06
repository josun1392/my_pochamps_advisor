from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from advisor.canonical_rage_fist_hit_count_power_family import resolve_canonical_rage_fist_hit_count_power_move
SCHEMA_VERSION="detached-rage-fist-hit-count-power-authority-v1"
def materialize_detached_rage_fist_hit_count_power_authority(*,strategy_d0:Mapping[str,Any],move:Mapping[str,Any],user:Mapping[str,Any],base_count_authority:Mapping[str,Any],source_terminal_leaf:Mapping[str,Any]|None=None)->dict[str,Any]:
 c=resolve_canonical_rage_fist_hit_count_power_move(move=move)
 if c.get("status")!="resolved":return {"status":c.get("status","rejected"),"schema_version":SCHEMA_VERSION,"reason":c.get("reason")}
 if not isinstance(base_count_authority,Mapping) or base_count_authority.get("status")!="resolved" or base_count_authority.get("owner")!=user:return {"status":"incomplete","schema_version":SCHEMA_VERSION,"reason":"rage_fist_base_hit_count_authority_missing"}
 base=base_count_authority.get("battle_received_hit_count")
 if not isinstance(base,int) or isinstance(base,bool) or base<0:return {"status":"rejected","schema_version":SCHEMA_VERSION,"reason":"rage_fist_base_hit_count_invalid"}
 inc=0;events=[]
 if isinstance(source_terminal_leaf,Mapping) and source_terminal_leaf.get("hit_state")=="hit":
  p=source_terminal_leaf.get("provenance",{}); cons=source_terminal_leaf.get("consequences",{}); target=p.get("target") if isinstance(p,Mapping) else None
  # successful direct hit, including substitute route; indirect consequences have no hit_state.
  if target==user and isinstance(cons,Mapping) and cons.get("damage") is not None: inc=1;events=[{"source_leaf_id":source_terminal_leaf.get("leaf_id"),"source_action_id":source_terminal_leaf.get("candidate_id"),"source_move_id":p.get("move_id"),"target":deepcopy(user),"route":"successful_direct_hit","event_order":"before_rage_fist_execution"}]
 effective=base+inc;cap=min(effective,6);power=50+50*cap
 return {"status":"resolved","schema_version":SCHEMA_VERSION,"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"user":deepcopy(dict(user)),"move_id":"rage-fist","trigger_family":"persistent_received_hit_count","d0_base_hit_count":base,"same_turn_hit_increment":inc,"qualifying_same_turn_hit_events":events,"effective_hit_count":effective,"count_cap":6,"selected_base_power":power,"rule":deepcopy(c["effect"]),"provenance":"exact_d0_detached_rage_fist_received_hit_count_v1"}
