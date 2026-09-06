"""Branch-local conditional base-power authority for Avalanche/Revenge."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_was_damaged_power_family import resolve_canonical_was_damaged_power_move

def materialize_detached_was_damaged_by_target_power_authority(*,move:Mapping[str,Any],user:Mapping[str,Any],target:Mapping[str,Any],incoming_event:Mapping[str,Any]|None)->dict[str,Any]:
 c=resolve_canonical_was_damaged_power_move(move=move)
 if c.get("status")!="resolved":return {"status":c.get("status","rejected"),"reason":c.get("reason","catalog_unavailable")}
 ok=isinstance(incoming_event,Mapping) and incoming_event.get("status")=="resolved" and incoming_event.get("recipient")==user and incoming_event.get("source_attacker")==target and incoming_event.get("qualifying_event") is True and isinstance(incoming_event.get("hp_lost"),int) and incoming_event["hp_lost"]>0
 return {"status":"resolved","schema_version":"detached-was-damaged-by-target-power-authority-v1","move_id":move["move_id"],"user":deepcopy(dict(user)),"target":deepcopy(dict(target)),"was_damaged_by_target":ok,"selected_base_power":c["effect"]["boosted_power"] if ok else c["effect"]["power"],"event":deepcopy(dict(incoming_event)) if ok else None,"rule":deepcopy(c["effect"]),"provenance":"exact_branch_local_was_damaged_by_target_power_v1"}
