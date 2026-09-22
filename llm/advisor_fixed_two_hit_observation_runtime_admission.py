"""Production admission for observed fixed-two-hit results."""
from copy import deepcopy
from typing import Mapping
from llm.advisor_exact_hp_zero_faint_runtime_lifecycle import build_exact_hp_zero_faint_confirmation_pair
from llm.advisor_lifecycle_confirmation import HP_TRANSITION_SOURCE,MULTI_HIT_ACTION_RESULT_SOURCE,MULTI_HIT_ORDERED_HIT_SOURCE,USER_TRUST,LifecycleConfirmationBoundary
from llm.advisor_multi_hit_graph_reconciliation import reconcile_observed_fixed_two_hit_graph,validate_historical_multi_hit_prediction
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager

EXECUTION_SOURCE="ui_executed_move_confirmation"

def admit_observed_fixed_two_hit_result(*,runtime_session_manager,captured_session_id,retained_prediction,turn_number,source_execution_observation,action_outcome,landed_hit_count,terminal_reason,ordered_hits):
 r=validate_historical_multi_hit_prediction(retained_prediction)
 if r.get("status")!="resolved":return _out(r.get("status","rejected"),r.get("reason","historical_multi_hit_invalid"))
 if not isinstance(runtime_session_manager,BattleObservationRuntimeSessionManager) or r["session_id"]!=captured_session_id or r["turn_number"]!=turn_number:return _out("rejected","fixed_two_hit_stale_session_or_turn")
 e=_execution_error(source_execution_observation,r)
 if e:return _out("rejected",e)
 hits=_normalize_hits(ordered_hits,landed_hit_count)
 if isinstance(hits,str):return _out("rejected",hits)
 if action_outcome=="miss":
  if landed_hit_count!=0 or terminal_reason!="action_miss" or hits:return _out("rejected","fixed_two_hit_miss_observation_invalid")
 elif action_outcome=="landed":
  if landed_hit_count not in {1,2} or len(hits)!=landed_hit_count:return _out("rejected","fixed_two_hit_landed_count_invalid")
 else:return _out("rejected","fixed_two_hit_result_request_invalid")
 snap=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
 if snap.get("status")!="runtime_snapshot_ready":return _out("rejected","fixed_two_hit_runtime_snapshot_unavailable")
 state=snap.get("state")
 if not _active(state,r["actor"]) or not _active(state,r["target"]):return _out("rejected","fixed_two_hit_actor_or_target_stale")
 coll=runtime_session_manager.read_collection_snapshot()
 executions=[x for x in coll.get("ordered_observations",()) if x.get("event_kind")=="executed_move_observed" and x.get("session_id")==captured_session_id and x.get("turn_number")==turn_number and (x.get("side"),x.get("slot_index"),x.get("pokemon_id"))==(r["actor"]["side"],r["actor"]["slot_index"],r["actor"]["pokemon_id"])]
 if not executions or max(executions,key=lambda x:x.get("observation_sequence",0)).get("observation_id")!=source_execution_observation.get("observation_id"):return _out("rejected","fixed_two_hit_execution_observation_stale")
 pid=f"{captured_session_id}:fixed-two-hit:{turn_number}:{r['action_id']}:result"
 parent_payload=_parent_payload(r,source_execution_observation,action_outcome,landed_hit_count,terminal_reason)
 old=next((x for x in coll.get("ordered_observations",()) if x.get("observation_id")==pid),None)
 if old is not None:
  children=tuple(sorted((x for x in coll.get("ordered_observations",()) if x.get("event_kind")=="multi_hit_ordered_hit_observed" and x.get("payload",{}).get("parent_multi_hit_observation_id")==pid),key=lambda x:x["payload"]["hit_index"]))
  if old.get("payload")!=parent_payload or len(children)!=len(hits) or any(c.get("payload")!=_child_payload(r,pid,h) for c,h in zip(children,hits)):return _out("rejected","conflicting_fixed_two_hit_observation")
  rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=r,source_execution_observation=source_execution_observation,parent_observation=old,hit_observations=children,related_observations=coll.get("ordered_observations",()))
  return {"status":"resolved","reason":"idempotent_reuse","idempotent":True,"parent_observation":deepcopy(old),"hit_observations":deepcopy(children),"reconciliation":rec,"runtime_snapshot":snap}
 actor,target=r["actor"],r["target"];boundary=LifecycleConfirmationBoundary(captured_session_id,{actor["side"]:actor,target["side"]:target})
 parent=boundary.confirm(event_kind="multi_hit_action_result_observed",payload=parent_payload,session_id=captured_session_id,source=MULTI_HIT_ACTION_RESULT_SOURCE,trust=USER_TRUST,confirmed=True,side=actor["side"],slot_index=actor["slot_index"],pokemon_id=actor["pokemon_id"],observation_id=pid,turn_number=turn_number)
 if parent.get("status")!="confirmed":return _out("rejected","fixed_two_hit_parent_confirmation_rejected")
 confirmations=[parent];children=[];_seq(runtime_session_manager,parent)
 current=_pokemon(state,target);current_hp=current.get("current_hp") if isinstance(current,Mapping) else None
 if hits and current_hp!=hits[0]["hp_before"]:return _out("rejected","fixed_two_hit_pre_hp_runtime_mismatch")
 for hit in hits:
  cid=f"{pid}:hit:{hit['hit_index']}";child=boundary.confirm(event_kind="multi_hit_ordered_hit_observed",payload=_child_payload(r,pid,hit),session_id=captured_session_id,source=MULTI_HIT_ORDERED_HIT_SOURCE,trust=USER_TRUST,confirmed=True,side=actor["side"],slot_index=actor["slot_index"],pokemon_id=actor["pokemon_id"],observation_id=cid,turn_number=turn_number)
  if child.get("status")!="confirmed":return _out("rejected","fixed_two_hit_child_confirmation_rejected")
  _seq(runtime_session_manager,child);confirmations.append(child);children.append(child["observation"])
 rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=r,source_execution_observation=source_execution_observation,parent_observation=parent["observation"],hit_observations=children,related_observations=coll.get("ordered_observations",()))
 if rec.get("status")!="resolved" or rec.get("match_outcome")=="incompatible_observation":return {"status":"rejected","reason":"incompatible_fixed_two_hit_observation","idempotent":False,"parent_observation":parent["observation"],"hit_observations":tuple(children),"reconciliation":rec,"runtime_snapshot":snap}
 for child,hit in zip(children,hits):
  if hit["hp_after"]==hit["hp_before"]:continue
  if hit["hp_after"]==0:
   pair=build_exact_hp_zero_faint_confirmation_pair(session_id=captured_session_id,owner=target,hp_before=hit["hp_before"],turn_number=turn_number,source_event_id=r["action_id"],hp_observation_id=child["observation_id"]+":hp",faint_observation_id=child["observation_id"]+":faint")
   if pair is None:return _out("rejected","fixed_two_hit_hp_faint_confirmation_rejected")
   pair[0]["observation"]["related_observation_id"]=child["observation_id"]
   for x in pair:_seq(runtime_session_manager,x);confirmations.append(x)
  else:
   hp=boundary.confirm(event_kind="exact_hp_transition_observed",payload={"hp_before":hit["hp_before"],"hp_after":hit["hp_after"]},session_id=captured_session_id,source=HP_TRANSITION_SOURCE,trust=USER_TRUST,confirmed=True,side=target["side"],slot_index=target["slot_index"],pokemon_id=target["pokemon_id"],observation_id=child["observation_id"]+":hp",related_observation_id=child["observation_id"],turn_number=turn_number)
   if hp.get("status")!="confirmed":return _out("rejected","fixed_two_hit_hp_confirmation_rejected")
   _seq(runtime_session_manager,hp);confirmations.append(hp)
 preview={**coll,"ordered_observations":sorted([*deepcopy(coll.get("ordered_observations",[])),*(deepcopy(x["observation"]) for x in confirmations)],key=lambda x:(x["observation_sequence"],x["observation_id"]))}
 if runtime_session_manager.preview(captured_session_id,preview).get("status")!="preview_ready":return _out("rejected","fixed_two_hit_preview_rejected")
 if runtime_session_manager.admit_confirmations_atomically(captured_session_id,confirmations).get("status") not in {"added","duplicate"}:return _out("rejected","fixed_two_hit_admission_rejected")
 if runtime_session_manager.apply(captured_session_id,runtime_session_manager.read_collection_snapshot()).get("status") not in {"applied","already_applied"}:return _out("rejected","fixed_two_hit_runtime_application_rejected")
 committed=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
 if hits and _pokemon(committed.get("state"),target).get("current_hp")!=hits[-1]["hp_after"]:return _out("rejected","fixed_two_hit_committed_hp_mismatch")
 return {"status":"resolved","reason":None,"idempotent":False,"parent_observation":deepcopy(parent["observation"]),"hit_observations":deepcopy(tuple(children)),"reconciliation":rec,"runtime_snapshot":committed}

def _execution_error(obs,r):
 a=r["actor"];p=obs.get("payload") if isinstance(obs,Mapping) else None
 if not isinstance(obs,Mapping) or obs.get("event_kind")!="executed_move_observed" or obs.get("source")!=EXECUTION_SOURCE or obs.get("trust")!=USER_TRUST or obs.get("session_id")!=r["session_id"] or obs.get("turn_number")!=r["turn_number"] or (obs.get("side"),obs.get("slot_index"),obs.get("pokemon_id"))!=(a["side"],a["slot_index"],a["pokemon_id"]):return "fixed_two_hit_execution_observation_mismatch"
 if not isinstance(p,Mapping) or p.get("move_id")!=r["move_id"] or p.get("source_action_id")!=r["source_action_id"]:return "fixed_two_hit_execution_payload_mismatch"
 return None

def _normalize_hits(rows,count):
 if not isinstance(rows,(tuple,list)) or len(rows)!=count:return "fixed_two_hit_ordered_hit_count_invalid"
 out=[]
 for i,x in enumerate(rows,1):
  if not isinstance(x,Mapping) or x.get("hit_index")!=i:return "fixed_two_hit_ordered_hit_index_invalid"
  b,a=x.get("hp_before"),x.get("hp_after")
  if not _nn(b) or not _nn(a) or a>b:return "fixed_two_hit_ordered_hit_hp_invalid"
  crit=x.get("critical_state")
  if crit not in {None,"critical","non_critical"}:return "fixed_two_hit_critical_observation_invalid"
  ids=x.get("related_contact_observation_ids",())
  if not isinstance(ids,(tuple,list)) or len(ids)!=len(set(ids)) or any(not isinstance(v,str) or not v for v in ids):return "fixed_two_hit_contact_links_invalid"
  out.append({"hit_index":i,"hp_before":b,"hp_after":a,"target_fainted_after_hit":a==0,"critical_state":crit,"related_contact_observation_ids":tuple(ids)})
 if any(out[i]["hp_after"]!=out[i+1]["hp_before"] for i in range(len(out)-1)):return "fixed_two_hit_ordered_hp_chain_invalid"
 return tuple(out)

def _parent_payload(r,e,o,c,t):return {"family":"fixed_two_hit","decision_point":r["decision_point"],"action_id":r["action_id"],"move_id":r["move_id"],"actor":deepcopy(r["actor"]),"target":deepcopy(r["target"]),"action_outcome":o,"landed_hit_count":c,"terminal_reason":t,"source_execution_observation_id":e["observation_id"],"predictive_artifact_fingerprint":r["predictive_artifact_fingerprint"]}
def _child_payload(r,p,h):return {"family":"fixed_two_hit","decision_point":r["decision_point"],"action_id":r["action_id"],"move_id":r["move_id"],"actor":deepcopy(r["actor"]),"target":deepcopy(r["target"]),"parent_multi_hit_observation_id":p,**deepcopy(dict(h))}
def _seq(m,x):
 s=m.allocate_observation_sequence()
 if s.get("status")!="allocated":raise ValueError("observation sequence unavailable")
 x["observation"]["observation_sequence"]=s["observation_sequence"]
def _active(state,o):
 side=state.get(f"{o['side']}_side") if isinstance(state,Mapping) else None;roster=side.get("pokemon") if isinstance(side,Mapping) else None;slot=side.get("active_slot_index") if isinstance(side,Mapping) else None;p=roster.get(slot,roster.get(str(slot))) if isinstance(roster,Mapping) else None
 return slot==o.get("slot_index") and isinstance(p,Mapping) and p.get("pokemon_id")==o.get("pokemon_id")
def _pokemon(state,o):
 side=state.get(f"{o['side']}_side") if isinstance(state,Mapping) else None;roster=side.get("pokemon") if isinstance(side,Mapping) else None
 return roster.get(o["slot_index"],roster.get(str(o["slot_index"]))) if isinstance(roster,Mapping) else None
def _nn(v):return isinstance(v,int) and not isinstance(v,bool) and v>=0
def _out(s,r):return {"status":s,"reason":r,"idempotent":False,"parent_observation":None,"hit_observations":(),"reconciliation":None,"runtime_snapshot":None}
