from copy import deepcopy
from llm.advisor_perish_song import materialize_observed_perish_song, perish_state, apply_perish_song_residual_phase
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_substitute import materialize_observed_substitute
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_leftovers_end_of_turn import _pre, _owner_id

def _obs(state, owners=("self","opponent"), **extra):
    value={"schema_version":"observed-perish-song-result-v1","session_id":"leftovers-eot","source_branch_fingerprint":fingerprint_transition_preview_state(state),"move_id":"perish-song","result":"applied","affected_owners":[_owner_id(state,x) for x in owners],"provenance":"trusted_observed_perish_song_result_v1"};value.update(extra);return value
def _apply(state, owners=("self","opponent")):
    return materialize_observed_perish_song(branch_state=state,source_branch_fingerprint=fingerprint_transition_preview_state(state),observed_result=_obs(state,owners))
def _tick(state):return apply_perish_song_residual_phase(branch_state=state,source_branch_fingerprint=fingerprint_transition_preview_state(state))

def test_perish_song_multi_owner_countdown_terminal_handoff_and_replay():
    pre=_pre(self_hp=100,opponent_hp=100,self_condition="none",opponent_condition="none"); source=pre["next_state"]; before=deepcopy(source); applied=_apply(source)
    assert applied["status"]=="resolved" and source==before
    current=applied["next_state"]; assert [perish_state(current,_owner_id(current,s))["remaining_count"] for s in ("self","opponent")]==[4,4]
    first=_tick(current); current=first["next_state"]; assert [x["count_after"] for x in first["trace"]]==[3,3]
    eot={"status":"resolved","next_state":current,"resulting_branch_fingerprint":fingerprint_transition_preview_state(current),"boundary":{"phase":"end_of_turn"}}; current=handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    for expected in (2,1,0):
        step=_tick(current); current=step["next_state"]; assert [x["count_after"] for x in step["trace"]]==[expected,expected]
    assert all(current["active"][s]["fainted"] for s in ("self","opponent"))
    assert materialize_observed_perish_song(branch_state=current,source_branch_fingerprint=fingerprint_transition_preview_state(current),observed_result=_obs(source))["status"]=="rejected"

def test_perish_song_substitute_isolation_single_owner_and_switch_clear():
    pre=_pre(self_hp=100,opponent_hp=100,self_condition="none",opponent_condition="none"); state=pre["next_state"]; owner=_owner_id(state,"self")
    sub={"schema_version":"observed-substitute-result-v1","session_id":owner["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(state),"owner":owner,"move_id":"substitute","result":"applied","provenance":"trusted_observed_substitute_result_v1"}
    state=materialize_observed_substitute(branch_state=state,source_branch_fingerprint=fingerprint_transition_preview_state(state),observed_result=sub)["next_state"]; applied=_apply(state,("self",)); assert applied["status"]=="resolved" and applied["next_state"]["substitute_state_context"]==state["substitute_state_context"]
    current=applied["next_state"]; incoming={"provenance":"identity_bound_incoming_current_state_v1","owner":{"session_id":"leftovers-eot","side":"self","slot_index":1,"pokemon_id":"incoming"},"hp_authority":{"status":"known","current_hp":80,"maximum_hp":100},"fainted_authority":{"status":"known","value":False},"current_state":deepcopy(current["current_state"])}
    switched=materialize_incoming_active_branch(source_branch=current,source_branch_fingerprint=fingerprint_transition_preview_state(current),incoming_authority=incoming)
    assert switched["status"]=="resolved" and perish_state(switched["next_state"],_owner_id(switched["next_state"],"self"))["state"]=="unknown"

def test_perish_song_rejects_malformed_and_duplicate_active_application():
    state=_pre(self_condition="none",opponent_condition="none")["next_state"]; assert _apply(state)["status"]=="resolved"
    active=_apply(state)["next_state"]; assert _apply(active)["reason"]=="perish_song_already_active"
    assert materialize_observed_perish_song(branch_state=state,source_branch_fingerprint=fingerprint_transition_preview_state(state),observed_result={**_obs(state),"affected_owners":[]})["status"]=="rejected"
