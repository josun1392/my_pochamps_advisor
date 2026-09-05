"""Detached exact target-current-HP fractional damage terminal consequence."""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from advisor.canonical_fractional_target_hp_damage_family import resolve_canonical_fractional_target_hp_damage_move
def materialize_detached_fractional_target_hp_damage(*,move:Mapping[str,Any],target_hp:Mapping[str,Any],hit_state:str,applicability:str)->dict[str,Any]:
    canonical=resolve_canonical_fractional_target_hp_damage_move(move=move)
    if canonical.get("status")!="resolved":return {"status":canonical.get("status","rejected"),"reason":canonical.get("reason","catalog_unavailable")}
    current,maximum,fainted=target_hp.get("current_hp"),target_hp.get("max_hp"),target_hp.get("fainted")
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (current,maximum)) or maximum<1 or not 0<=current<=maximum or fainted is not (current==0):return {"status":"incomplete","reason":"fractional_target_hp_authority_unknown"}
    if hit_state not in {"hit","missed"} or applicability not in {"applicable","immune","blocked"}:return {"status":"rejected","reason":"fractional_hit_or_applicability_invalid"}
    damage=max(1,current//2) if hit_state=="hit" and applicability=="applicable" and current>0 else 0; post=current-damage
    return {"status":"resolved","family":canonical["effect"],"hit_state":hit_state,"applicability":applicability,"target_pre_hp":current,"target_post_hp":post,"damage":damage,"target_fainted":post==0,"critical_state":"not_applicable","damage_roll":"not_applicable","provenance":"strict_detached_fractional_target_hp_damage_v1"}
