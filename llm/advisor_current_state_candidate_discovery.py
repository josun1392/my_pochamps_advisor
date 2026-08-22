from typing import Any,Mapping
def discover_candidates(*,snapshot:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(snapshot,Mapping) or snapshot.get("status")!="resolved" or snapshot.get("schema_version")!="deterministic-current-action-authority-v1":return {"status":"rejected","reason":"invalid_current_action_authority"}
 rows=[]
 for a in snapshot["actions"]:
  if a["selection"]=="selectable":rows.append({"schema_version":"deterministic-action-candidate-v1","candidate_id":a["action_id"],"decision_owner":snapshot["decision_owner"],"source_branch_fingerprint":snapshot["decision_branch_fingerprint"],"action_type":a["action_type"],"action_authority":a["execution_authority"]})
 return {"status":"resolved","candidates":rows,"candidate_set_completeness":snapshot["selection_completeness"]["candidate_set"]}
