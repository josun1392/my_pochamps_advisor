"""Atomic actual-runtime lifecycle for an observed positive HP to zero faint."""
from copy import deepcopy
from typing import Mapping
from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, HP_TRANSITION_SOURCE, FAINT_SOURCE, USER_TRUST
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager

SOURCE = "runtime_exact_hp_zero_faint_lifecycle_v1"

def build_exact_hp_zero_faint_confirmation_pair(*, session_id, owner, hp_before, turn_number, source_event_id, hp_observation_id=None, faint_observation_id=None):
    """Pure builder; callers may compose its rows into a larger atomic batch."""
    if not _owner(owner, session_id) or not _positive(hp_before) or not _positive(turn_number) or not _token(source_event_id): return None
    boundary=LifecycleConfirmationBoundary(session_id,{owner["side"]:owner})
    hp_id=hp_observation_id or f"{session_id}:hp-zero-faint:{source_event_id}:hp"; faint_id=faint_observation_id or f"{session_id}:hp-zero-faint:{source_event_id}:faint"
    if not _observation_id(hp_id) or not _observation_id(faint_id) or hp_id == faint_id: return None
    hp=boundary.confirm(event_kind="exact_hp_transition_observed",payload={"hp_before":hp_before,"hp_after":0},session_id=session_id,source=HP_TRANSITION_SOURCE,trust=USER_TRUST,confirmed=True,side=owner["side"],slot_index=owner["slot_index"],pokemon_id=owner["pokemon_id"],observation_id=hp_id,turn_number=turn_number)
    faint=boundary.confirm(event_kind="pokemon_faint_observed",payload={"cause_known":False},session_id=session_id,source=FAINT_SOURCE,trust=USER_TRUST,confirmed=True,side=owner["side"],slot_index=owner["slot_index"],pokemon_id=owner["pokemon_id"],observation_id=faint_id,related_observation_id=hp_id,turn_number=turn_number)
    return (hp,faint) if hp.get("status")=="confirmed" and faint.get("status")=="confirmed" else None

def admit_exact_hp_zero_faint(*, runtime_session_manager, captured_session_id, side, source_event_id, turn_number):
    if not isinstance(runtime_session_manager,BattleObservationRuntimeSessionManager) or side not in {"self","opponent"} or not _token(source_event_id) or not _positive(turn_number): return _result("rejected","invalid_hp_zero_faint_request")
    snap=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snap.get("status")!="runtime_snapshot_ready": return _result("rejected","runtime_snapshot_unavailable")
    owner=_active_identity(snap.get("state"),side)
    if owner is None: return _result("rejected","active_owner_unavailable")
    pokemon=_pokemon(snap["state"],owner); hp=pokemon.get("current_hp") if isinstance(pokemon,Mapping) else None
    rows=runtime_session_manager.read_collection_snapshot().get("ordered_observations",[])
    hp_id=f"{captured_session_id}:hp-zero-faint:{source_event_id}:hp"; faint_id=f"{captured_session_id}:hp-zero-faint:{source_event_id}:faint"
    oldhp=next((x for x in rows if x.get("observation_id")==hp_id),None); oldfaint=next((x for x in rows if x.get("observation_id")==faint_id),None)
    existing=validate_exact_hp_zero_faint_confirmation_pair(hp=oldhp,faint=oldfaint,owner=owner,turn_number=turn_number,hp_observation_id=hp_id,faint_observation_id=faint_id,session_id=captured_session_id)
    if existing=="exact":
        if not isinstance(pokemon,Mapping) or pokemon.get("current_hp") != 0 or pokemon.get("fainted") is not True: return _result("rejected","inconsistent_committed_hp_zero_faint_lifecycle")
        return {"status":"resolved","reason":"idempotent_reuse","owner":deepcopy(owner),"observations":[deepcopy(oldhp),deepcopy(oldfaint)],"runtime_snapshot":snap,"strategy_d0":None,"idempotent":True,"replacement_boundary":{"status":"replacement_required_after_faint","fainted_owner":deepcopy(owner),"hp_transition_observation_id":hp_id,"faint_observation_id":faint_id,"terminal_sequence":oldfaint["observation_sequence"],"provenance":SOURCE}}
    if existing!="none": return _result("rejected","incomplete_or_conflicting_hp_zero_faint_lifecycle")
    if pokemon.get("fainted") is True: return _result("rejected","already_fainted_without_matching_lifecycle")
    if not _positive(hp): return _result("rejected","current_hp_not_positive")
    pair=build_exact_hp_zero_faint_confirmation_pair(session_id=captured_session_id,owner=owner,hp_before=hp,turn_number=turn_number,source_event_id=source_event_id)
    if pair is None:return _result("rejected","confirmation_rejected")
    for row in pair:
        allocated=runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status")!="allocated" or allocated.get("session_id")!=captured_session_id or not isinstance(allocated.get("observation_sequence"),int): return _result("rejected","observation_sequence_unavailable")
        row["observation"]["observation_sequence"]=allocated["observation_sequence"]
    collection=runtime_session_manager.read_collection_snapshot(); preview={**collection,"ordered_observations":sorted([*collection["ordered_observations"],*[x["observation"] for x in pair]],key=lambda x:(x["observation_sequence"],x["observation_id"]))}
    if runtime_session_manager.preview(captured_session_id,preview).get("status")!="preview_ready":return _result("rejected","preview_rejected")
    if runtime_session_manager.admit_confirmations_atomically(captured_session_id,pair).get("status")!="added":return _result("rejected","admission_rejected")
    if runtime_session_manager.apply(captured_session_id,runtime_session_manager.read_collection_snapshot()).get("status") not in {"applied","already_applied"}:return _result("rejected","application_rejected")
    committed=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id); target=_pokemon(committed.get("state"),owner)
    if not isinstance(target,Mapping) or target.get("current_hp")!=0 or target.get("fainted") is not True:return _result("rejected","committed_faint_verification_failed")
    return {"status":"resolved","reason":None,"owner":owner,"observations":[deepcopy(x["observation"]) for x in pair],"runtime_snapshot":committed,"strategy_d0":None,"idempotent":False,"replacement_boundary":{"status":"replacement_required_after_faint","fainted_owner":owner,"hp_transition_observation_id":hp_id,"faint_observation_id":faint_id,"terminal_sequence":pair[1]["observation"]["observation_sequence"],"provenance":SOURCE}}
def validate_exact_hp_zero_faint_confirmation_pair(*, hp, faint, owner, turn_number, hp_observation_id, faint_observation_id, session_id):
    """Classify an already-collected deterministic pair without mutating it."""
    turn, hp_id, faint_id, session = turn_number, hp_observation_id, faint_observation_id, session_id
    if hp is None and faint is None:return "none"
    if not isinstance(hp,Mapping) or not isinstance(faint,Mapping):return "partial"
    match=lambda row,kind,source,oid: row.get("event_kind")==kind and row.get("source")==source and row.get("trust")==USER_TRUST and row.get("session_id")==session and row.get("observation_id")==oid and row.get("turn_number")==turn and (row.get("side"),row.get("slot_index"),row.get("pokemon_id"))==(owner["side"],owner["slot_index"],owner["pokemon_id"])
    if not match(hp,"exact_hp_transition_observed",HP_TRANSITION_SOURCE,hp_id) or not match(faint,"pokemon_faint_observed",FAINT_SOURCE,faint_id):return "conflict"
    payload=hp.get("payload")
    if not isinstance(payload,Mapping) or not _positive(payload.get("hp_before")) or payload.get("hp_after")!=0 or faint.get("payload")!={"cause_known":False} or faint.get("related_observation_id")!=hp_id:return "conflict"
    hs,fs=hp.get("observation_sequence"),faint.get("observation_sequence")
    return "exact" if isinstance(hs,int) and not isinstance(hs,bool) and isinstance(fs,int) and not isinstance(fs,bool) and hs<fs else "conflict"
def _active_owner(state,side):
    row=state.get(f"{side}_side") if isinstance(state,Mapping) else None; slot=row.get("active_slot_index") if isinstance(row,Mapping) else None; roster=row.get("pokemon") if isinstance(row,Mapping) else None; p=roster.get(slot) if isinstance(roster,Mapping) else None
    return {"session_id":state.get("session_id"),"side":side,"slot_index":slot,"pokemon_id":p.get("pokemon_id")} if isinstance(p,Mapping) and isinstance(slot,int) and not isinstance(slot,bool) and p.get("fainted") is not True else None
def _active_identity(state,side):
    row=state.get(f"{side}_side") if isinstance(state,Mapping) else None; slot=row.get("active_slot_index") if isinstance(row,Mapping) else None; roster=row.get("pokemon") if isinstance(row,Mapping) else None; p=roster.get(slot) if isinstance(roster,Mapping) else None
    return {"session_id":state.get("session_id"),"side":side,"slot_index":slot,"pokemon_id":p.get("pokemon_id")} if isinstance(p,Mapping) and isinstance(slot,int) and not isinstance(slot,bool) and isinstance(p.get("pokemon_id"),str) and p.get("pokemon_id") else None
def _pokemon(state,o): return state.get(f"{o['side']}_side",{}).get("pokemon",{}).get(o["slot_index"])
def _owner(o,s):return isinstance(o,Mapping) and o.get("session_id")==s and o.get("side") in {"self","opponent"} and isinstance(o.get("slot_index"),int) and not isinstance(o.get("slot_index"),bool) and isinstance(o.get("pokemon_id"),str) and bool(o["pokemon_id"])
def _positive(x):return isinstance(x,int) and not isinstance(x,bool) and x>0
def _token(x):return isinstance(x,str) and bool(x) and x==x.lower() and " " not in x and "_" not in x
def _observation_id(x):return isinstance(x,str) and bool(x)
def _result(status,reason):return {"status":status,"reason":reason,"owner":None,"observations":[],"runtime_snapshot":None,"strategy_d0":None,"replacement_boundary":None}
