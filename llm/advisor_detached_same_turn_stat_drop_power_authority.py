"""Branch-local exact Lash Out evidence from an earlier actual stage decrease."""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from advisor.canonical_same_turn_stat_drop_power_family import resolve_canonical_same_turn_stat_drop_power_move
SCHEMA_VERSION="detached-same-turn-stat-drop-power-authority-v1"
_STATS=frozenset({"attack","defense","special-attack","special-defense","speed","accuracy","evasion"})
def materialize_detached_same_turn_stat_drop_power_authority(*,strategy_d0:Mapping[str,Any],move:Mapping[str,Any],user:Mapping[str,Any],source_terminal_leaf:Mapping[str,Any]|None=None,execution_order_provenance:Mapping[str,Any]|None=None)->dict[str,Any]:
    canonical=resolve_canonical_same_turn_stat_drop_power_move(move=move)
    if canonical.get("status")!="resolved": return _bad(canonical.get("status","rejected"),canonical.get("reason","catalog_unavailable"))
    if not all(isinstance(v,Mapping) for v in (strategy_d0,move,user)) or strategy_d0.get("active_owners",{}).get(user.get("side"))!=user or not all(isinstance(strategy_d0.get(k),str) and strategy_d0[k] for k in ("session_id","source_runtime_fingerprint","strategy_preview_fingerprint")): return _bad("rejected","same_turn_stat_drop_power_binding_invalid")
    event=None
    if source_terminal_leaf is not None:
        transition=source_terminal_leaf.get("stage_transition") if isinstance(source_terminal_leaf,Mapping) else None
        if not isinstance(transition,Mapping): return _bad("rejected","same_turn_stat_drop_source_stage_transition_missing")
        before,after,stat,target=transition.get("pre_stage"),transition.get("post_stage"),transition.get("stat"),transition.get("target")
        if target==user and stat in _STATS and isinstance(before,int) and not isinstance(before,bool) and isinstance(after,int) and not isinstance(after,bool) and -6<=before<=6 and -6<=after<=6 and after<before:
            prov=source_terminal_leaf.get("provenance")
            if not isinstance(prov,Mapping) or not isinstance(source_terminal_leaf.get("leaf_id"),str): return _bad("rejected","same_turn_stat_drop_source_provenance_invalid")
            event={"pair_branch_source_leaf_id":source_terminal_leaf["leaf_id"],"stat":stat,"stage_before":before,"stage_after":after,"delta":after-before,"source_action_id":source_terminal_leaf.get("candidate_id"),"source_move_id":prov.get("move_id"),"source_actor":deepcopy(prov.get("attacker")),"event_order":"before_lash_out_execution"}
        elif target==user and stat in _STATS and isinstance(before,int) and isinstance(after,int): event=None
        else: return _bad("rejected","same_turn_stat_drop_source_transition_invalid")
    effect=canonical["effect"]; condition=isinstance(event,Mapping)
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"user":deepcopy(dict(user)),"move_id":"lash-out","trigger_family":"user_stat_was_lowered_this_turn","canonical_base_power":75,"user_stat_was_lowered_before_execution":condition,"selected_base_power":150 if condition else 75,"qualifying_stage_decrease_event":deepcopy(event),"execution_order_provenance":deepcopy(dict(execution_order_provenance)) if isinstance(execution_order_provenance,Mapping) else None,"rule":deepcopy(effect),"provenance":"exact_d0_pair_branch_same_turn_actual_stage_decrease_v1"}
def _bad(status:str,reason:str)->dict[str,Any]: return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
