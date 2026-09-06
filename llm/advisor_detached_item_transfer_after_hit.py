from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
def materialize_detached_item_transfer_after_hit(*,authority:Mapping[str,Any],source_leaf:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(authority,Mapping) or authority.get("status")!="resolved":return {"status":"incomplete","reason":"item_transfer_authority_unavailable"}
 if authority.get("move_id") not in {"thief","covet"} or source_leaf.get("provenance",{}).get("move_id")!=authority.get("move_id"):return {"status":"rejected","reason":"item_transfer_move_binding_mismatch"}
 c=source_leaf.get("consequences",{}); hit=c.get("source_hit_context") if isinstance(c,Mapping) else None
 if source_leaf.get("provenance",{}).get("attacker")!=authority.get("user") or source_leaf.get("provenance",{}).get("target")!=authority.get("target"):return {"status":"rejected","reason":"item_transfer_identity_mismatch"}
 before_u,before_t=authority.get("user_item_before"),authority.get("target_item_before")
 base={"authority":deepcopy(dict(authority)),"source_hit":source_leaf.get("leaf_id"),"user_item_before":before_u,"target_item_before":before_t}
 if authority.get("user_item_state")!="known_absent" or authority.get("target_item_state")!="known_present":return {"status":"resolved","outcome":"not_transferred","reason":"item_precondition_not_met","user_item_after":before_u,"target_item_after":before_t,**base}
 if source_leaf.get("hit_state")!="hit" or not isinstance(hit,Mapping) or hit.get("target_routing")!="target" or not isinstance(c.get("damage"),int) or c["damage"]<=0:return {"status":"resolved","outcome":"not_transferred","reason":"hit_not_applicable","user_item_after":before_u,"target_item_after":before_t,**base}
 if authority.get("removable") is not True or authority.get("sticky_hold") is True:return {"status":"resolved","outcome":"not_transferred","reason":"target_item_not_stealable","user_item_after":before_u,"target_item_after":before_t,**base}
 if c.get("self_fainted") is True:return {"status":"resolved","outcome":"not_transferred","reason":"user_fainted_before_transfer","user_item_after":before_u,"target_item_after":before_t,**base}
 return {"status":"resolved","outcome":"transferred","item":before_t,"user_item_after":before_t,"target_item_after":None,**base}
