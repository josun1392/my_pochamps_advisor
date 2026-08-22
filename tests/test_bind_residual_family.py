from copy import deepcopy

from llm.advisor_bind_residual import apply_owner_bind_end_of_turn, bind_state, materialize_observed_bind
from llm.advisor_bind_switch_restriction import derive_bind_manual_switch_block, finalize_bind_manual_switch_candidates
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_substitute import materialize_observed_substitute
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_ingrain_detached_eot import _pre
from tests.test_leftovers_end_of_turn import _owner_id


def _switch_facts(state, types=("normal",), item=None):
    row = lambda side: {"side":side,"state":"known","types":list(types if side == "self" else ("normal",)),"status":"user_confirmed","source":"user_confirmed_current_type","authority_provenance":"user_confirmed_current"}
    state["current_state"]["current_type_context"] = {"current_types":[row("self"), row("opponent")]}
    state["current_state"]["current_item_context"] = {"current_item":[{"side":"self","status":"known","value":item,"source":"user_confirmed_current_item","authority_provenance":"user_confirmed_current"}, {"side":"opponent","status":"known","value":None,"source":"user_confirmed_current_item","authority_provenance":"user_confirmed_current"}]}
    direct = state["current_state"].setdefault("direct_mechanics_context", {})
    direct.setdefault("attacker", {})["item"] = {"status":"known", "value":item}
    direct.setdefault("defender", {})["item"] = {"status":"known_absent"}


def _result(state, source="self", target="opponent", **overrides):
    source_owner, target_owner = _owner_id(state, source), _owner_id(state, target)
    value = {"schema_version":"observed-bind-result-v1", "session_id":source_owner["session_id"], "source_branch_fingerprint":fingerprint_transition_preview_state(state), "source_owner":source_owner, "target_owner":target_owner, "move_id":"bind", "damaging_hit_result":"applied", "bind_result":"applied", "duration_turns":5, "provenance":"trusted_observed_bind_result_v1"}
    value.update(overrides); return value


def _apply(state, source="self", target="opponent", **overrides):
    return materialize_observed_bind(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), observed_result=_result(state, source, target, **overrides))


def test_bind_application_eot_duration_handoff_expiration_and_side_neutrality():
    pre = _pre(self_hp=100, opponent_hp=100, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    state = pre["next_state"]; bound = _apply(state)
    assert bound["status"] == "resolved" and state == pre["next_state"]
    first_pre = {"status":"resolved", "next_state":bound["next_state"], "boundary":{"phase":"pre_end_of_turn"}}
    first = project_per_owner_end_of_turn(pre_end_of_turn=first_pre, owner=_owner_id(bound["next_state"], "opponent"))
    assert first["status"] == "resolved" and first["next_state"]["active"]["opponent"]["current_hp"] == 88
    assert bind_state(first["next_state"], _owner_id(first["next_state"], "opponent"))["remaining_turns"] == 4
    turn_two = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=first)
    assert turn_two["status"] == "resolved" and bind_state(turn_two["next_state"], _owner_id(turn_two["next_state"], "opponent"))["remaining_turns"] == 4
    current = turn_two["next_state"]
    for _ in range(4):
        eot = project_per_owner_end_of_turn(pre_end_of_turn={"status":"resolved","next_state":current,"boundary":{"phase":"pre_end_of_turn"}}, owner=_owner_id(current,"opponent"))
        assert eot["status"] == "resolved"; current = eot["next_state"]
    assert bind_state(current, _owner_id(current, "opponent"))["state"] == "known_inactive"
    reverse = _pre(self_hp=100, opponent_hp=100, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    assert _apply(reverse, "opponent", "self")["status"] == "resolved"


def test_bind_manual_block_substitute_boundary_replay_and_switch_clear():
    pre = _pre(self_hp=100, opponent_hp=100, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    state = pre["next_state"]; _switch_facts(state); bound = _apply(state, "opponent", "self"); current = bound["next_state"]; owner = _owner_id(current,"self"); fp = fingerprint_transition_preview_state(current)
    assert derive_bind_manual_switch_block(branch_state=current, source_branch_fingerprint=fp, owner=owner)["block_state"] == "confirmed_blocked"
    permission={"schema_version":"switch-permission-context-v1","session_id":owner["session_id"],"side":"self","active_slot_index":owner["slot_index"],"active_pokemon_id":owner["pokemon_id"],"status":"permitted","supportability":"complete","source":"user_confirmed_current_switch_permission","trust":"user_confirmed_current"}
    candidate={"availability_supportability":"complete","reason_code":"available"}
    assert finalize_bind_manual_switch_candidates(base_candidates=[candidate], manual_permission=permission, branch_state=current, source_branch_fingerprint=fp, owner=owner)["switch_candidates"][0]["reason_code"] == "switch_blocked"
    ghost = deepcopy(current); _switch_facts(ghost, ("ghost",)); assert derive_bind_manual_switch_block(branch_state=ghost, source_branch_fingerprint=fingerprint_transition_preview_state(ghost), owner=_owner_id(ghost,"self"))["block_state"] == "exception_applies"
    shell = deepcopy(current); _switch_facts(shell, item="shed-shell"); assert derive_bind_manual_switch_block(branch_state=shell, source_branch_fingerprint=fingerprint_transition_preview_state(shell), owner=_owner_id(shell,"self"))["block_state"] == "exception_applies"
    stale = _result(state, "opponent", "self"); assert materialize_observed_bind(branch_state=current, source_branch_fingerprint=fp, observed_result=stale)["status"] == "rejected"
    incoming={"provenance":"identity_bound_incoming_current_state_v1","owner":{"session_id":owner["session_id"],"side":"self","slot_index":1,"pokemon_id":"next"},"hp_authority":{"status":"known","current_hp":90,"maximum_hp":100},"fainted_authority":{"status":"known","value":False},"current_state":deepcopy(current["current_state"])}
    switched=materialize_incoming_active_branch(source_branch=current, source_branch_fingerprint=fp, incoming_authority=incoming)
    assert switched["status"] == "resolved" and bind_state(switched["next_state"], _owner_id(switched["next_state"],"self"))["state"] == "unknown"
    protected = _pre(self_hp=100, opponent_hp=100, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    sub={"schema_version":"observed-substitute-result-v1","session_id":_owner_id(protected,"opponent")["session_id"],"source_branch_fingerprint":fingerprint_transition_preview_state(protected),"owner":_owner_id(protected,"opponent"),"move_id":"substitute","result":"applied","provenance":"trusted_observed_substitute_result_v1"}
    protected=materialize_observed_substitute(branch_state=protected, source_branch_fingerprint=fingerprint_transition_preview_state(protected), observed_result=sub)["next_state"]
    assert _apply(protected, "self", "opponent")["reason"] == "bind_blocked_by_substitute"


def test_bind_source_loss_ko_unknown_and_residual_ko_fail_closed():
    pre = _pre(self_hp=100, opponent_hp=12, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    bound = _apply(pre["next_state"])["next_state"]; fp=fingerprint_transition_preview_state(bound)
    result=apply_owner_bind_end_of_turn(state=bound, side="opponent", owner=_owner_id(bound,"opponent"), source_branch_fingerprint=fp)
    assert result["status"] == "resolved" and bound["active"]["opponent"]["fainted"] is True
    bad = _pre(self_hp=100, opponent_hp=100, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    bad["bind_residual_state_context"]={"schema_version":"detached-bind-residual-state-v1","session_id":"leftovers-eot","source_branch_fingerprint":"x","provenance":"trusted_observed_bind_result_v1","states":[{"target_owner":_owner_id(bad,"self"),"state":"unknown","source_owner":None,"remaining_turns":None}]}
    assert derive_bind_manual_switch_block(branch_state=bad, source_branch_fingerprint=fingerprint_transition_preview_state(bad), owner=_owner_id(bad,"self")) == {"status":"incomplete","reason":"bind_state_unknown"}


def test_bind_composes_after_existing_condition_residual_on_current_hp():
    pre = _pre(self_hp=100, opponent_hp=100, self_item=None, opponent_item=None, self_condition="none", opponent_condition="poison")
    bound = _apply(pre["next_state"])["next_state"]
    result = project_per_owner_end_of_turn(pre_end_of_turn={"status":"resolved","next_state":bound,"boundary":{"phase":"pre_end_of_turn"}}, owner=_owner_id(bound,"opponent"))
    assert result["status"] == "resolved"
    assert [(row["tier"], row["effect"]) for row in result["eot_consequence_trace"]] == [(9, "poison_residual"), (13, "bind_residual")]
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 76
