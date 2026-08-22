"""Partial-order frontier over the detached pairwise comparator."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Sequence
from llm.advisor_deterministic_action_comparison import compare_candidates

SCHEMA="deterministic-candidate-ranking-v1"
def rank_candidates(*, decision_owner:Mapping[str,Any], candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(candidates,Sequence) or isinstance(candidates,(str,bytes)) or len(candidates)<2:return _r("rejected","at_least_two_candidates_required")
    ids=[x.get("candidate_id") if isinstance(x,Mapping) else None for x in candidates]
    if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):return _r("rejected","duplicate_or_invalid_candidate_id")
    rows={x["candidate_id"]:deepcopy(dict(x)) for x in candidates}; matrix=[]; dominated=set(); incomplete=False
    for i,a in enumerate(ids):
      for b in ids[i+1:]:
        result=compare_candidates(decision_owner=decision_owner,candidate_a=rows[a],candidate_b=rows[b]);matrix.append({"candidate_a":a,"candidate_b":b,"result":result})
        if result.get("status")!="resolved": incomplete=True;continue
        if result.get("comparison")=="preferred": dominated.add(b if result["preferred_candidate"]=="a" else a)
    frontier=sorted(set(ids)-dominated)
    if incomplete:return {"schema_version":SCHEMA,"status":"incomplete_comparison_set","preferred_frontier":frontier,"pairwise_matrix":matrix,"reason":"incomplete_candidate_prevents_global_preference"}
    status="uniquely_preferred" if len(frontier)==1 else "tied_preferred_set" if frontier else "no_unique_preference"
    return {"schema_version":SCHEMA,"status":status,"preferred_frontier":frontier,"pairwise_matrix":matrix,"dominance":{"dominated_candidate_ids":sorted(dominated),"rule":"explicit_pairwise_preference_only"}}
def _r(status:str,reason:str)->dict[str,Any]:return {"status":status,"reason":reason}
