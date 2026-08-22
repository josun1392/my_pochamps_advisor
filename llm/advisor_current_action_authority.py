"""Selection-only D0 authority; never execution evidence."""
from copy import deepcopy
from typing import Any,Mapping,Sequence
from llm.advisor_transition_preview import fingerprint_transition_preview_state
def freeze_current_action_authority(*,decision_state:Mapping[str,Any],decision_owner:Mapping[str,Any],moves:Sequence[Mapping[str,Any]],switches:Sequence[Mapping[str,Any]])->dict[str,Any]:
 fp=fingerprint_transition_preview_state(decision_state);active=decision_state.get("active",{}).get(decision_owner.get("side")) if isinstance(decision_state,Mapping) else None
 keys=("session_id","side","slot_index","pokemon_id")
 if not isinstance(fp,str) or not isinstance(active,Mapping) or dict(decision_owner)!={k:active.get(k) for k in keys}:return {"status":"rejected","reason":"invalid_d0_authority"}
 def row(x,kind):
  if not isinstance(x,Mapping) or x.get("source_branch_fingerprint")!=fp or x.get("owner")!=dict(decision_owner) or x.get("selection") not in {"selectable","not_selectable","selection_unknown"}:raise ValueError
  ident=x.get("move_id") if kind=="attack" else x.get("pokemon_id")
  if not isinstance(ident,str):raise ValueError
  return {"action_id":f"{kind}:{ident}","action_type":kind,"identity":ident,"selection":x["selection"],"execution_readiness":x.get("execution_readiness","execution_incomplete"),"execution_authority":deepcopy(x.get("execution_authority"))}
 try: actions=[row(x,"attack") for x in moves]+[row(x,"manual_switch") for x in switches]
 except ValueError:return {"status":"rejected","reason":"stale_or_invalid_selection_projection"}
 if len({x["action_id"] for x in actions})!=len(actions):return {"status":"rejected","reason":"duplicate_action_identity"}
 return {"status":"resolved","schema_version":"deterministic-current-action-authority-v1","session_id":decision_owner["session_id"],"decision_branch_fingerprint":fp,"decision_owner":deepcopy(dict(decision_owner)),"actions":sorted(actions,key=lambda x:x["action_id"]),"selection_completeness":{"candidate_set":"complete" if all(x["selection"]!="selection_unknown" for x in actions) else "partial"}}
