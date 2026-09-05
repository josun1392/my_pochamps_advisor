"""Pure Final Gambit arithmetic and its successful self-sacrifice gate."""
from __future__ import annotations
from typing import Any,Mapping
from advisor.canonical_final_gambit_self_hp_damage_family import resolve_canonical_final_gambit_self_hp_damage_move
def materialize_detached_final_gambit_self_hp_damage(*,move:Mapping[str,Any],attacker_hp:Mapping[str,Any],target_hp:Mapping[str,Any],hit_state:str,applicability:str)->dict[str,Any]:
 c=resolve_canonical_final_gambit_self_hp_damage_move(move=move)
 if c.get("status")!="resolved":return {"status":c.get("status","rejected"),"reason":c.get("reason","catalog_unavailable")}
 a,t=_hp(attacker_hp),_hp(target_hp)
 if a is None or t is None or a<1:return {"status":"incomplete","reason":"final_gambit_execution_hp_unknown"}
 if hit_state not in {"hit","miss"} or applicability not in {"applicable","immune","blocked"}:return {"status":"rejected","reason":"final_gambit_hit_or_applicability_invalid"}
 success=hit_state=="hit" and applicability=="applicable"; raw=a if success else 0; actual=min(raw,t); post=t-actual
 return {"status":"resolved","family":c["effect"],"attacker_execution_hp":a,"target_execution_hp":t,"hit_state":hit_state,"applicability":applicability,"outcome":"success" if success else applicability if hit_state=="hit" else "miss","raw_damage":raw,"actual_target_hp_loss":actual,"target_post_hp":post,"target_fainted":post==0,"attacker_post_hp":0 if success else a,"attacker_fainted":success,"self_sacrifice":{"outcome":"applied","provenance":"final_gambit_self_sacrifice"} if success else {"outcome":"not_applied"},"critical_state":"not_applicable","damage_roll":"not_applicable","provenance":"strict_detached_final_gambit_self_hp_damage_v1"}
def _hp(v:Any)->int|None:
 if not isinstance(v,Mapping):return None
 c,m,f=v.get("current_hp"),v.get("max_hp"),v.get("fainted")
 return c if isinstance(c,int) and not isinstance(c,bool) and isinstance(m,int) and not isinstance(m,bool) and 0<=c<=m and f is (c==0) else None
