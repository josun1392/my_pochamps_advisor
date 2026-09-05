"""Post-damage recoil consequence derived only from actual target HP loss."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_damage_based_recoil_move_family import resolve_canonical_damage_based_recoil_move

def apply_detached_damage_based_recoil(*, runtime_snapshot: Mapping[str, Any], attacker: Mapping[str, Any], move_metadata: Mapping[str, Any], leaf: Mapping[str, Any]) -> dict[str, Any]:
    canonical=resolve_canonical_damage_based_recoil_move(move=move_metadata)
    if canonical.get("status")=="unsupported": return {"status":"resolved","leaf":deepcopy(dict(leaf))}
    if canonical.get("status")!="resolved": return {"status":canonical.get("status","rejected"),"reason":canonical.get("reason","recoil_catalog_unavailable")}
    c=leaf.get("consequences") if isinstance(leaf,Mapping) else None; hit=c.get("source_hit_context") if isinstance(c,Mapping) else None
    if not isinstance(c,Mapping) or not isinstance(hit,Mapping): return {"status":"rejected","reason":"recoil_source_hit_missing"}
    if leaf.get("hit_state")!="hit" or hit.get("target_routing")!="target": return {"status":"resolved","leaf":deepcopy(dict(leaf))}
    pre,post,actual=hit.get("target_pre_hp"),hit.get("target_post_hp"),hit.get("actual_damage")
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (pre,post,actual)) or not 0<=post<=pre or actual != pre-post: return {"status":"rejected","reason":"recoil_actual_target_hp_loss_invalid"}
    if actual==0: return {"status":"resolved","leaf":deepcopy(dict(leaf))}
    own=c.get("own_final_hp")
    if not isinstance(own,int) or isinstance(own,bool) or own<0: return {"status":"incomplete","reason":"recoil_path_local_attacker_hp_unknown"}
    ability=_ability(runtime_snapshot,attacker)
    if ability is None: return {"status":"incomplete","reason":"recoil_attacker_ability_unknown"}
    num,den=canonical["effect"]["recoil_numerator"],canonical["effect"]["recoil_denominator"]
    nominal=max(1,(actual*num+den//2)//den)
    prevented=ability in {"rock-head","magic-guard"}
    recoil=0 if prevented else nominal; post_own=max(0,own-recoil)
    row=deepcopy(dict(leaf)); updated=deepcopy(dict(c)); updated["own_final_hp"]=post_own; updated["self_fainted"]=post_own==0
    updated["damage_based_recoil"]={"move_id":move_metadata["move_id"],"recoil_family":"damage_based_recoil","fraction":{"numerator":num,"denominator":den},"minimum_recoil":1,"source_hit":deepcopy(dict(hit)),"actual_target_hp_loss":actual,"nominal_recoil":nominal,"attacker_pre_hp":own,"attacker_ability":ability,"prevention":"rock_head" if ability=="rock-head" else "magic_guard" if ability=="magic-guard" else "none","recoil_damage":recoil,"attacker_post_hp":post_own,"attacker_fainted":post_own==0}
    row["consequences"]=updated; row["provenance"]={**deepcopy(dict(row.get("provenance",{}))),"damage_based_recoil_catalog":deepcopy(canonical)}
    return {"status":"resolved","leaf":row}

def _ability(snapshot:Mapping[str,Any],owner:Mapping[str,Any])->str|None:
    state=snapshot.get("state") if isinstance(snapshot,Mapping) else None; side=state.get(f"{owner.get('side')}_side") if isinstance(state,Mapping) else None; roster=side.get("pokemon") if isinstance(side,Mapping) else None; row=roster.get(owner.get("slot_index")) if isinstance(roster,Mapping) else None
    provenance=row.get("current_ability_provenance") if isinstance(row,Mapping) else None; value=row.get("current_ability") if isinstance(row,Mapping) else None
    return value if isinstance(value,str) and value and isinstance(provenance,Mapping) and provenance.get("event_kind")=="current_ability_observed" and provenance.get("trust")=="user_confirmed_observation" else None
