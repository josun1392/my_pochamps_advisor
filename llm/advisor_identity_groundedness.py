"""Exact-active groundedness authority for future legality mechanics."""
from copy import deepcopy
from typing import Any, Mapping

def build_groundedness(*, session_id: str, side: str, slot_index: int, pokemon_id: str, status: str="unknown") -> dict[str, Any]:
    if not isinstance(session_id,str) or not session_id or side not in {"self","opponent"} or not isinstance(slot_index,int) or isinstance(slot_index,bool) or slot_index<0 or not isinstance(pokemon_id,str) or not pokemon_id or status not in {"grounded","ungrounded","unknown"}: raise ValueError("invalid_identity_groundedness")
    return deepcopy({"schema_version":"identity-groundedness-v1","session_id":session_id,"side":side,"slot_index":slot_index,"pokemon_id":pokemon_id,"status":status})

def normalize_groundedness(value: Any, *, session_id: str, side: str, slot_index: int, pokemon_id: str) -> dict[str, Any]:
    unknown=build_groundedness(session_id=session_id,side=side,slot_index=slot_index,pokemon_id=pokemon_id)
    if not isinstance(value,Mapping): return unknown
    try: expected=build_groundedness(session_id=session_id,side=side,slot_index=slot_index,pokemon_id=pokemon_id,status=value.get("status"))
    except (TypeError,ValueError): return unknown
    return deepcopy(expected) if set(value)==set(expected) and all(value[k]==expected[k] for k in expected) else unknown

def project_identity_groundedness(runtime_state: Mapping[str, Any], *, side: str) -> dict[str, Any]:
    side_state=runtime_state.get(f"{side}_side") if isinstance(runtime_state,Mapping) else None; roster=side_state.get("pokemon") if isinstance(side_state,Mapping) else None; slot=side_state.get("active_slot_index") if isinstance(side_state,Mapping) else None; pokemon=roster.get(slot,roster.get(str(slot))) if isinstance(roster,Mapping) else None; pid=pokemon.get("pokemon_id",pokemon.get("name_en")) if isinstance(pokemon,Mapping) else None
    if not isinstance(runtime_state.get("session_id"),str) or not isinstance(pid,str): raise ValueError("invalid_identity_groundedness")
    return normalize_groundedness(runtime_state.get("identity_groundedness_context"),session_id=runtime_state["session_id"],side=side,slot_index=slot,pokemon_id=pid)

def arena_trap_prerequisite(*, ability_authority: Mapping[str,Any], groundedness: Mapping[str,Any]) -> dict[str,str]:
    if not isinstance(ability_authority,Mapping) or ability_authority.get("ability_id")!="arena-trap" or ability_authority.get("applicability")!="applicable" or ability_authority.get("interaction")!="affecting": return {"status":"insufficient_context"}
    return {"status":"complete"} if isinstance(groundedness,Mapping) and groundedness.get("status")=="grounded" else {"status":"not_applicable"} if isinstance(groundedness,Mapping) and groundedness.get("status")=="ungrounded" else {"status":"insufficient_context"}
