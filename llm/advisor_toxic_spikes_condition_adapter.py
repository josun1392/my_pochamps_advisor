"""Compose exact Toxic Spikes outcomes into existing detached condition overlays."""
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_hypothetical_condition_effects import apply_predicted_condition

def apply_toxic_spikes_condition(*, branch_state: Mapping[str, Any], branch_fingerprint: str, owner: Mapping[str, Any], evaluator_result: Mapping[str, Any]) -> dict[str, Any]:
    if fingerprint_transition_preview_state(branch_state) != branch_fingerprint: return _r("rejected","stale_post_entry_branch")
    active=branch_state.get("active",{}).get(owner.get("side")) if isinstance(branch_state.get("active"),Mapping) else None
    if not isinstance(active,Mapping) or any(active.get(k)!=owner.get(k) for k in ("session_id","side","slot_index","pokemon_id")): return _r("rejected","stale_or_foreign_toxic_spikes_owner")
    ailment=evaluator_result.get("post_condition") if isinstance(evaluator_result,Mapping) and evaluator_result.get("status")=="complete" and evaluator_result.get("outcome")=="status_applied" else None
    if ailment not in {"poison","toxic"}: return _r("incomplete","toxic_spikes_status_outcome")
    state=deepcopy(dict(branch_state)); effect={"status":"resolved","applicable":True,"ailment":ailment,"owner":deepcopy(dict(owner))}
    apply_predicted_condition(state,effect,source_snapshot_fingerprint=branch_fingerprint,branch_state_fingerprint=fingerprint_transition_preview_state(state))
    state["predicted_condition_context"]["provenance"]="turn_engine_predicted_toxic_spikes"
    return {"status":"resolved","next_state":state,"resulting_branch_fingerprint":fingerprint_transition_preview_state(state)}
def _r(status,reason): return {"status":status,"reason":reason}
