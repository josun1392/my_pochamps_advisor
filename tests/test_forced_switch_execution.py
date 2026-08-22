from copy import deepcopy

from llm.advisor_forced_switch_execution import execute_allowed_self_forced_switch, materialize_allowed_forced_replacement
from llm.advisor_forced_switch_replacement import (
    materialize_forced_switch_replacement_authority,
    materialize_observed_forced_replacement_result,
)
from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_executable_switch_transition import _branch, _incoming, _snapshot


def _owner(state, side):
    return {key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}


def _state(*, hp=80, rock="absent"):
    state = _branch()
    snapshot = _snapshot(rock=rock, spikes=0)["current_state"]
    state["current_state"]["self_roster_mechanics_context"] = snapshot["self_roster_mechanics_context"]
    state["current_state"]["self_roster_mechanics_context"]["entries"][0]["fainted_authority"] = {"status": "known", "value": False}
    owners = {side: _owner(state, side) for side in ("self", "opponent")}
    states = {side: {family: {"state": "known_inactive"} for family in ("aqua_ring", "ingrain", "leech_seed")} for side in ("self", "opponent")}
    state["branch_persistent_effect_authority"] = materialize_persistent_effect_authority(owners=owners, source_branch_fingerprint="trusted-fixture", states=states)
    return state, _observed(state, hp=hp, rock=rock)


def _observed(state, *, hp=80, rock="absent"):
    outgoing, incoming = _owner(state, "self"), _incoming(hp=hp)
    incoming["persistent_effect_states"] = {family: {"state": "known_inactive"} for family in ("aqua_ring", "ingrain", "leech_seed")}
    entry = _snapshot(rock=rock, spikes=0)["current_state"]
    return {
        "schema_version": "observed-forced-replacement-result-v1", "session_id": outgoing["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "outgoing_owner": outgoing,
        "incoming_authority": incoming,
        "outgoing_bench_authority": {
            "owner": outgoing, "hp_authority": {"status": "known", "current_hp": 90, "maximum_hp": 100},
            "fainted_authority": {"status": "known", "value": False},
            "retained_current_state": {"condition": "none", "item": "none", "types": ["normal"], "ability": "blaze"},
            "provenance": "trusted_forced_switch_outgoing_bench_v1",
        },
        "entry_authority": {
            "hazards": entry["switch_hazard_context"], "target_roster_mechanics": entry["self_roster_mechanics_context"]["entries"][0],
            "intimidate_authority": None, "download_authority": None, "field_state_context": None,
            "provenance": "trusted_forced_switch_entry_authority_v1",
        },
        "replacement_status": "replacement_resolved", "provenance": "trusted_observed_forced_replacement_result_v1",
    }


def _request(state):
    owner = _owner(state, "self")
    return {"schema_version": "forced-switch-request-v1", "session_id": owner["session_id"], "source_branch_fingerprint": fingerprint_transition_preview_state(state), "target_owner": owner, "request_kind": "drag_out", "provenance": "trusted_forced_switch_request_v1"}


def _authority(state, observed=None):
    observed = observed or _observed(state)
    request = _request(state)
    decision = decide_forced_switch_cancellation(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), forced_switch_request=request)
    return request, decision, materialize_forced_switch_replacement_authority(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), forced_switch_request=request, cancellation_decision=decision, observed_replacement=observed)


def test_observed_replacement_is_pure_idempotent_and_execution_retains_outgoing_without_transfer():
    state, observed = _state(); before = deepcopy(state); fp = fingerprint_transition_preview_state(state)
    first = materialize_observed_forced_replacement_result(branch_state=state, source_branch_fingerprint=fp, observed_replacement=observed)
    second = materialize_observed_forced_replacement_result(branch_state=state, source_branch_fingerprint=fp, observed_replacement=observed)
    request, decision, authority = _authority(state, observed)
    result = execute_allowed_self_forced_switch(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)
    assert first == second and state == before and authority["schema_version"] == "forced-switch-replacement-authority-v1"
    assert result["status"] == "resolved", result
    assert result["next_state"]["active"]["self"]["pokemon_id"] == "incoming"
    bench = result["next_state"]["forced_switch_bench_record"]
    assert bench["owner"] == _owner(state, "self") and bench["hp_authority"]["current_hp"] == 90
    assert set(bench["persistent_effects"].values()) == {"cleared_on_forced_switch"}
    assert result["resulting_branch_fingerprint"] != fp
    assert execute_allowed_self_forced_switch(source_branch=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)["status"] == "rejected"


def test_replacement_requires_exact_available_nonfainted_roster_and_allowed_decision():
    state, observed = _state(); fp = fingerprint_transition_preview_state(state)
    for mutate in (
        lambda item: item["incoming_authority"].update({"owner": {**item["incoming_authority"]["owner"], "slot_index": 0, "pokemon_id": "outgoing"}}),
        lambda item: item["incoming_authority"].update({"owner": {**item["incoming_authority"]["owner"], "side": "opponent"}}),
        lambda item: item["incoming_authority"].pop("persistent_effect_states"),
    ):
        bad = deepcopy(observed); mutate(bad)
        assert materialize_observed_forced_replacement_result(branch_state=state, source_branch_fingerprint=fp, observed_replacement=bad)["status"] == "rejected"
    request, decision, authority = _authority(state, observed)
    cancelled = {**decision, "decision": "cancelled"}
    assert execute_allowed_self_forced_switch(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=cancelled, replacement_authority=authority) == {"status": "rejected", "reason": "forced_switch_execution_not_allowed"}


def test_hazard_ko_is_terminal_without_second_replacement_and_active_ingrain_never_reaches_execution():
    state, observed = _state(hp=1, rock="present"); fp = fingerprint_transition_preview_state(state)
    request, decision, authority = _authority(state, observed)
    terminal = execute_allowed_self_forced_switch(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)
    assert terminal["status"] == "unsupported" and terminal["reason"] == "replacement_required_after_entry_hazard_ko"
    assert terminal["next_state"]["active"]["self"]["fainted"] is True and terminal["atomic_execution"] is True
    active = _state()[0]
    next(row for row in active["branch_persistent_effect_authority"]["states"] if row["family"] == "ingrain" and row["owner"] == _owner(active, "self"))["state"] = "known_active"
    request, decision, authority = _authority(active)
    assert decision["decision"] == "cancelled"
    assert execute_allowed_self_forced_switch(source_branch=active, source_branch_fingerprint=fingerprint_transition_preview_state(active), forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority) == {"status": "rejected", "reason": "forced_switch_execution_not_allowed"}


def test_opponent_replacement_materializes_exact_owner_and_bench_but_entry_execution_remains_out_of_scope():
    state, observed = _state()
    outgoing = _owner(state, "opponent")
    incoming = deepcopy(observed["incoming_authority"])
    incoming["owner"] = {"session_id": outgoing["session_id"], "side": "opponent", "slot_index": 1, "pokemon_id": "opponent-incoming"}
    target = deepcopy(observed["entry_authority"]["target_roster_mechanics"])
    target.update(incoming["owner"]); target["fainted_authority"] = {"status": "known", "value": False}
    state["current_state"]["opponent_roster_mechanics_context"] = {"session_id": outgoing["session_id"], "side": "opponent", "entries": [target]}
    observed.update({
        "outgoing_owner": outgoing, "session_id": outgoing["session_id"], "incoming_authority": incoming,
        "outgoing_bench_authority": {**observed["outgoing_bench_authority"], "owner": outgoing, "hp_authority": {"status": "known", "current_hp": 100, "maximum_hp": 100}},
        "entry_authority": {**observed["entry_authority"], "hazards": {**observed["entry_authority"]["hazards"], "affected_side": "opponent"}, "target_roster_mechanics": target},
    })
    fp = fingerprint_transition_preview_state(state)
    observed["source_branch_fingerprint"] = fp
    request = {"schema_version": "forced-switch-request-v1", "session_id": outgoing["session_id"], "source_branch_fingerprint": fp, "target_owner": outgoing, "request_kind": "drag_out", "provenance": "trusted_forced_switch_request_v1"}
    decision = decide_forced_switch_cancellation(branch_state=state, source_branch_fingerprint=fp, forced_switch_request=request)
    authority = materialize_forced_switch_replacement_authority(branch_state=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, observed_replacement=observed)
    result = materialize_allowed_forced_replacement(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority)
    assert authority["status"] == "resolved" and result["status"] == "resolved", authority
    assert result["next_state"]["active"]["opponent"]["pokemon_id"] == "opponent-incoming"
    assert result["next_state"]["active"]["self"] == state["active"]["self"]
    assert result["next_state"]["forced_switch_bench_record"]["owner"] == outgoing
    assert execute_allowed_self_forced_switch(source_branch=state, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, replacement_authority=authority) == {"status": "unsupported", "reason": "opponent_forced_switch_execution_out_of_scope"}
