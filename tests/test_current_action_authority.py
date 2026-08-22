from llm.advisor_current_action_authority import freeze_current_action_authority
from llm.advisor_current_state_candidate_discovery import discover_candidates
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _state,_owner
def test_selection_only_snapshot_and_discovery():
 s,_=_state();o=_owner(s,"self");fp=fingerprint_transition_preview_state(s);m={"owner":o,"source_branch_fingerprint":fp,"move_id":"water-gun","selection":"selectable"};w={"owner":o,"source_branch_fingerprint":fp,"pokemon_id":"bench","selection":"selection_unknown"}
 snap=freeze_current_action_authority(decision_state=s,decision_owner=o,moves=[m],switches=[w]);assert snap["selection_completeness"]["candidate_set"]=="partial" and discover_candidates(snapshot=snap)["candidates"][0]["candidate_id"]=="attack:water-gun"

def test_selection_states_stable_ids_detachment_and_d0_rejection():
 s,_=_state();o=_owner(s,"self");fp=fingerprint_transition_preview_state(s)
 def row(move,selection,ready="execution_incomplete"):return {"owner":o,"source_branch_fingerprint":fp,"move_id":move,"selection":selection,"execution_readiness":ready}
 switch={"owner":o,"source_branch_fingerprint":fp,"pokemon_id":"bench-a","selection":"selectable","execution_readiness":"execution_incomplete"}
 snap=freeze_current_action_authority(decision_state=s,decision_owner=o,moves=[row("z-move","not_selectable"),row("a-move","selectable","execution_ready"),row("unknown","selection_unknown")],switches=[switch])
 assert [x["action_id"] for x in snap["actions"]]==["attack:a-move","attack:unknown","attack:z-move","manual_switch:bench-a"]
 frozen=snap["actions"][0]; switch["selection"]="not_selectable";assert snap["actions"][3]["selection"]=="selectable" and discover_candidates(snapshot=snap)["candidates"][-1]["candidate_id"]=="manual_switch:bench-a"
 assert freeze_current_action_authority(decision_state=s,decision_owner=o,moves=[{**row("x","selectable"),"source_branch_fingerprint":"stale"}],switches=[])["status"]=="rejected"
 assert freeze_current_action_authority(decision_state=s,decision_owner={**o,"pokemon_id":"foreign"},moves=[],switches=[])["status"]=="rejected"
