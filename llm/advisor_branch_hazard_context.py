"""Detached, side-owned switch hazard authority for Turn Engine branches."""
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_transition_preview import fingerprint_transition_preview_state

_KEYS = ("stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web")

def project_side_hazards(*, branch_state: Mapping[str, Any], source_fingerprint: str, frozen_hazards: Mapping[str, Any]) -> dict[str, Any]:
    if fingerprint_transition_preview_state(branch_state) != source_fingerprint: return _r("rejected", "stale_source_branch")
    if not isinstance(frozen_hazards, Mapping) or set(_KEYS).difference(frozen_hazards): return _r("incomplete", "switch_hazard_authority")
    side, session = frozen_hazards.get("affected_side"), frozen_hazards.get("session_id")
    if side not in {"self", "opponent"} or branch_state.get("active", {}).get(side, {}).get("session_id") != session: return _r("rejected", "foreign_hazard_authority")
    state = deepcopy(dict(branch_state)); state["branch_side_hazard_context"] = {"schema_version":"detached-side-hazards-v1","session_id":session,"side":side,"source_branch_fingerprint":source_fingerprint,"provenance":"frozen_switch_hazard_context","hazards":{k:deepcopy(frozen_hazards[k]) for k in _KEYS}}
    return {"status":"resolved","next_state":state,"resulting_branch_fingerprint":fingerprint_transition_preview_state(state)}

def remove_absorbed_toxic_spikes(*, branch_state: Mapping[str, Any], source_fingerprint: str, absorption: Mapping[str, Any]) -> dict[str, Any]:
    if fingerprint_transition_preview_state(branch_state) != source_fingerprint: return _r("rejected", "stale_source_branch")
    ctx=branch_state.get("branch_side_hazard_context")
    if not isinstance(ctx, Mapping) or absorption.get("removes_toxic_spikes") is not True or absorption.get("outcome") != "absorbed": return _r("rejected", "invalid_toxic_spikes_absorption")
    state=deepcopy(dict(branch_state)); state["branch_side_hazard_context"]["hazards"]["toxic_spikes_layers"]=0; state["branch_side_hazard_context"]["source_branch_fingerprint"]=source_fingerprint
    return {"status":"resolved","next_state":state,"resulting_branch_fingerprint":fingerprint_transition_preview_state(state)}
def _r(status,reason): return {"status":status,"reason":reason}
