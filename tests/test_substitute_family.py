from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_forced_switch_execution import execute_allowed_self_forced_switch
from llm.advisor_forced_switch_replacement import materialize_forced_switch_replacement_authority
from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_observed_damage_application import apply_exact_observed_damage
from llm.advisor_observed_damage_plus_phazing import materialize_observed_damage_plus_phazing_result
from llm.advisor_observed_damage_plus_target_condition import materialize_observed_sludge_bomb
from llm.advisor_observed_damage_plus_target_stage import materialize_observed_acid_spray
from llm.advisor_observed_forced_switch_source_application import materialize_observed_forced_switch_source_application
from llm.advisor_substitute import materialize_observed_substitute, substitute_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _observed, _owner, _state
from tests.test_executable_switch_transition import _incoming


def _creation(state, side="self", **overrides):
    owner = _owner(state, side)
    value = {"schema_version":"observed-substitute-result-v1","session_id":owner["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(state),"owner":owner,"move_id":"substitute","result":"applied","provenance":"trusted_observed_substitute_result_v1"}
    value.update(overrides); return value


def _create(state, side="self"):
    return materialize_observed_substitute(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), observed_result=_creation(state, side))


def _damage(state, user, target, amount):
    return apply_exact_observed_damage(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), user=_owner(state, user), target_owner=_owner(state, target), damage_amount=amount)


def test_substitute_creation_partial_break_and_sequential_side_neutral_damage():
    state, _ = _state(); baseline = deepcopy(state); created = _create(state)
    assert created["status"] == "resolved" and state == baseline
    assert created["next_state"]["active"]["self"]["current_hp"] == 65 and substitute_state(created["next_state"], _owner(created["next_state"], "self"))["substitute_hp"] == 25
    partial = _damage(created["next_state"], "opponent", "self", 15)
    assert partial["status"] == "resolved" and partial["next_state"]["active"]["self"]["current_hp"] == 65 and partial["damage_application"]["substitute_hp_after"] == 10
    broken = _damage(partial["next_state"], "opponent", "self", 30)
    assert broken["status"] == "resolved" and broken["next_state"]["active"]["self"]["current_hp"] == 65
    assert substitute_state(broken["next_state"], _owner(broken["next_state"], "self"))["state"] == "known_inactive"
    reverse, _ = _state(); assert _create(reverse, "opponent")["status"] == "resolved"


def test_substitute_creation_failures_unknown_and_replay():
    state, _ = _state(); state["active"]["self"]["current_hp"] = 25
    assert _create(state)["reason"] == "substitute_insufficient_hp"
    state, _ = _state(); created = _create(state)
    assert _create(created["next_state"])["status"] == "rejected"
    assert _create(state, "self")["status"] == "resolved"
    unknown, _ = _state(); owner = _owner(unknown, "opponent")
    unknown["substitute_state_context"] = {"schema_version":"detached-substitute-state-v1","session_id":"s","source_branch_fingerprint":"x","provenance":"trusted_observed_substitute_result_v1","states":[{"owner":owner,"state":"unknown","substitute_hp":None}]}
    assert _damage(unknown, "self", "opponent", 10) == {"status":"incomplete","reason":"substitute_state_unknown"}
    assert _create(state, "self")["status"] == "resolved"
    stale = _creation(state); assert materialize_observed_substitute(branch_state=created["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(created["next_state"]), observed_result=stale)["status"] == "rejected"


def _post_observation(state, move, result_key, value, **overrides):
    user, target = _owner(state, "opponent"), _owner(state, "self")
    result = {"schema_version":"observed-damage-plus-target-condition-result-v1" if move == "sludge-bomb" else "observed-damage-plus-target-stage-result-v1","session_id":user["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(state),"user":user,"target_owner":target,"move_id":move,"damage_amount":10,"damaging_hit_result":"applied",result_key:"applied","provenance":"trusted_observed_damage_plus_target_condition_result_v1" if move == "sludge-bomb" else "trusted_observed_damage_plus_target_stage_result_v1"}
    if move == "sludge-bomb": result["condition"] = value
    else: result.update({"stat":"special-defense","stage_delta":value})
    result.update(overrides); return result


def test_substitute_blocks_supported_target_consequences_and_damaging_phazing():
    state, _ = _state(); protected = _create(state)["next_state"]
    sludge = _post_observation(protected, "sludge-bomb", "target_condition_result", "poison")
    acid = _post_observation(protected, "acid-spray", "target_stage_result", -2)
    assert materialize_observed_sludge_bomb(branch_state=protected, source_branch_fingerprint=fingerprint_transition_preview_state(protected), observed_result=sludge)["reason"] == "condition_blocked_by_substitute"
    assert materialize_observed_acid_spray(branch_state=protected, source_branch_fingerprint=fingerprint_transition_preview_state(protected), observed_result=acid)["reason"] == "target_stage_blocked_by_substitute"
    phaze = {"schema_version":"observed-damage-plus-phazing-result-v1","session_id":_owner(protected,"self")["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(protected),"user":_owner(protected,"opponent"),"target_owner":_owner(protected,"self"),"move_id":"dragon-tail","damage_amount":10,"damaging_hit_result":"applied","drag_out_result":"drag_out_requested","provenance":"trusted_observed_damage_plus_phazing_result_v1"}
    assert materialize_observed_damage_plus_phazing_result(branch_state=protected, source_branch_fingerprint=fingerprint_transition_preview_state(protected), observed_result=phaze)["reason"] == "drag_out_blocked_by_substitute"
    roar = {"schema_version":"observed-forced-switch-source-application-v1","session_id":_owner(protected,"self")["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(protected),"user":_owner(protected,"opponent"),"target_owner":_owner(protected,"self"),"move_id":"roar","applied_effect":"drag_out","result":"applied","provenance":"trusted_observed_forced_switch_source_application_v1"}
    assert materialize_observed_forced_switch_source_application(branch_state=protected, source_branch_fingerprint=fingerprint_transition_preview_state(protected), observed_source_result=roar)["status"] == "resolved"


def test_substitute_handoff_persists_active_and_break_does_not_resurrect():
    state, _ = _state(); created = _create(state)
    eot = {"status":"resolved","next_state":created["next_state"],"resulting_branch_fingerprint":fingerprint_transition_preview_state(created["next_state"]),"boundary":{"phase":"end_of_turn"}}
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    assert substitute_state(handoff, _owner(handoff,"self"))["state"] == "known_active"
    broken = _damage(created["next_state"], "opponent", "self", 30)
    eot["next_state"] = broken["next_state"]; eot["resulting_branch_fingerprint"] = fingerprint_transition_preview_state(broken["next_state"])
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    assert substitute_state(handoff, _owner(handoff,"self"))["state"] == "known_inactive"


def test_substitute_clears_on_manual_and_forced_replacement_without_transfer():
    state, observed = _state(); protected = _create(state)["next_state"]
    incoming = _incoming(hp=80)
    manual = materialize_incoming_active_branch(source_branch=protected, source_branch_fingerprint=fingerprint_transition_preview_state(protected), incoming_authority=incoming)
    assert manual["status"] == "resolved"
    assert substitute_state(manual["next_state"], _owner(manual["next_state"], "self"))["state"] == "unknown"
    state, _ = _state(); protected = _create(state)["next_state"]; fp = fingerprint_transition_preview_state(protected); observed = _observed(protected)
    observed["outgoing_bench_authority"]["hp_authority"] = {"status":"known","current_hp":protected["active"]["self"]["current_hp"],"maximum_hp":protected["active"]["self"]["max_hp"]}
    request = {"schema_version":"forced-switch-request-v1","session_id":_owner(protected,"self")["session_id"],"source_branch_fingerprint":fp,"target_owner":_owner(protected,"self"),"request_kind":"drag_out","provenance":"trusted_forced_switch_request_v1"}
    decision = decide_forced_switch_cancellation(branch_state=protected, source_branch_fingerprint=fp, forced_switch_request=request)
    authority = materialize_forced_switch_replacement_authority(branch_state=protected, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, observed_replacement=observed)
    forced = execute_allowed_self_forced_switch(source_branch=protected, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)
    assert forced["status"] == "resolved" and substitute_state(forced["next_state"], _owner(forced["next_state"], "self"))["state"] == "unknown"
