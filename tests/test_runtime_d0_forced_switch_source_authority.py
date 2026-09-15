"""Pre-replacement forced-switch source authority bound to runtime D0."""
from copy import deepcopy

import pytest

from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observed_damage_plus_phazing import materialize_observed_damage_plus_phazing_result
from llm.advisor_observed_forced_switch_source_application import materialize_observed_forced_switch_source_application
from llm.advisor_persistent_effect_authority import persistent_effect_state
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_forced_switch_source_authority import freeze_runtime_d0_forced_switch_source_authority
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _state():
    state = create_unknown_bootstrap_battle_state("forced-source", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
        bench = deepcopy(state[f"{side}_side"]["pokemon"][0]); bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    return state


def _owner(state, side):
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _set(state, family, *, side="self", status="active", source_side=None, source_slot=None):
    event = {"observation_id": f"{family}-{side}", "observation_sequence": 1, "planned_effect": f"set_current_{family}_state", "side": side, "slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"], "persistent_state": status, "trust": "user_confirmed_observation", "turn_number": 1}
    if source_side is not None: event.update(source_side=source_side, source_slot_index=source_slot)
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [event]}
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state"
    return result["projected_state"]


def _authority(state, side="self"):
    result = freeze_runtime_d0_forced_switch_source_authority(runtime_snapshot=_snapshot(state), target_side=side)
    assert result["status"] == "resolved", result
    return result


def _request(authority):
    return {"schema_version": "forced-switch-request-v1", "session_id": authority["session_id"], "source_branch_fingerprint": authority["resulting_source_branch_fingerprint"], "target_owner": authority["target_owner"], "request_kind": "drag_out", "provenance": "trusted_forced_switch_request_v1"}


def _source_observation(authority, move_id="roar"):
    target = authority["target_owner"]; user = authority["active_owners"]["opponent" if target["side"] == "self" else "self"]
    return {"schema_version": "observed-forced-switch-source-application-v1", "session_id": authority["session_id"], "source_branch_fingerprint": authority["resulting_source_branch_fingerprint"], "user": user, "target_owner": target, "move_id": move_id, "applied_effect": "drag_out", "result": "applied", "provenance": "trusted_observed_forced_switch_source_application_v1"}


def _compound(authority, move_id="dragon-tail"):
    target = authority["target_owner"]; user = authority["active_owners"]["opponent" if target["side"] == "self" else "self"]
    return {"schema_version": "observed-damage-plus-phazing-result-v1", "session_id": authority["session_id"], "source_branch_fingerprint": authority["resulting_source_branch_fingerprint"], "user": user, "target_owner": target, "move_id": move_id, "damage_amount": 10, "damaging_hit_result": "applied", "drag_out_result": "drag_out_requested", "provenance": "trusted_observed_damage_plus_phazing_result_v1"}


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_resolves_side_neutral_exact_fingerprint_and_target_owner_binding(side):
    state = _state(); authority = _authority(state, side)
    assert authority["session_id"] == state["session_id"] and authority["target_owner"] == _owner(state, side)
    assert authority["source_runtime_fingerprint"] == state_fingerprint(state)
    assert authority["source_strategy_preview_fingerprint"] != authority["persistent_branch_fingerprint"]
    assert authority["persistent_branch_fingerprint"] == authority["resulting_source_branch_fingerprint"] == fingerprint_transition_preview_state(authority["branch_state"])
    assert authority["branch_state"]["active"][side]["current_hp"] == 80


@pytest.mark.parametrize("target_side", ["invalid", None])
def test_invalid_target_side_rejects(target_side):
    assert freeze_runtime_d0_forced_switch_source_authority(runtime_snapshot=_snapshot(_state()), target_side=target_side)["status"] == "rejected"


@pytest.mark.parametrize("mutate", ["stale", "foreign", "fingerprint"])
def test_invalid_stale_foreign_and_forged_runtime_snapshots_reject(mutate):
    state = _state(); snapshot = _snapshot(state)
    if mutate == "stale":
        snapshot["state"]["last_applied_observation_sequence"] = 1
    elif mutate == "foreign": snapshot["session_id"] = "foreign"
    else: snapshot["state_fingerprint"] = "forged"
    assert freeze_runtime_d0_forced_switch_source_authority(runtime_snapshot=snapshot, target_side="self")["status"] == "rejected"


def test_persistent_states_all_six_rows_and_leech_source_are_transported_unknown_first():
    state = _set(_state(), "aqua_ring", status="active")
    state = _set(state, "ingrain", side="opponent", status="inactive")
    state = _set(state, "leech_seed", status="active", source_side="opponent", source_slot=0)
    authority = _authority(state)
    assert len(authority["branch_state"]["branch_persistent_effect_authority"]["states"]) == 6
    assert persistent_effect_state(authority["branch_state"], "aqua_ring", "self", authority["active_owners"]["self"])["state"] == "known_active"
    assert persistent_effect_state(authority["branch_state"], "ingrain", "opponent", authority["active_owners"]["opponent"])["state"] == "known_inactive"
    assert persistent_effect_state(authority["branch_state"], "ingrain", "self", authority["active_owners"]["self"])["state"] == "unknown"
    assert persistent_effect_state(authority["branch_state"], "leech_seed", "self", authority["active_owners"]["self"])["source_slot"] == {"session_id": state["session_id"], "side": "opponent", "slot_index": 0}


@pytest.mark.parametrize(("side", "status", "expected"), [("self", "active", "cancelled"), ("self", "inactive", "allowed_to_proceed"), ("opponent", "active", "cancelled"), ("opponent", "inactive", "allowed_to_proceed")])
def test_ingrain_decisions_are_directly_consumable_side_neutrally(side, status, expected):
    authority = _authority(_set(_state(), "ingrain", side=side, status=status), side)
    decision = decide_forced_switch_cancellation(branch_state=authority["branch_state"], source_branch_fingerprint=authority["resulting_source_branch_fingerprint"], forced_switch_request=_request(authority))
    assert decision["decision"] == expected


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_unknown_ingrain_is_incomplete_for_both_target_sides(side):
    authority = _authority(_state(), side)
    assert decide_forced_switch_cancellation(branch_state=authority["branch_state"], source_branch_fingerprint=authority["resulting_source_branch_fingerprint"], forced_switch_request=_request(authority)) == {"status": "incomplete", "reason": "ingrain_persistent_effect_unknown"}


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_target_side_hazards_transport_known_and_unknown_without_mutation(side):
    state = _state(); state["switch_hazard_context"] = build_switch_hazard_context(session_id=state["session_id"], affected_side=side, stealth_rock="present", spikes_layers=2, toxic_spikes_layers=1, sticky_web="present")
    before = deepcopy(state); authority = _authority(state, side)
    hazards = authority["switch_hazard_authority"]
    assert hazards == state["switch_hazard_context"] and state == before
    unknown = _authority(_state(), side)["switch_hazard_authority"]
    assert unknown["affected_side"] == side and unknown["stealth_rock"] == unknown["spikes_layers"] == unknown["toxic_spikes_layers"] == unknown["sticky_web"] == "unknown"


@pytest.mark.parametrize(("side", "move_id"), [("self", "roar"), ("opponent", "whirlwind")])
def test_roar_and_whirlwind_observations_materialize_exact_requests_and_stale_reject(side, move_id):
    authority = _authority(_state(), side); observation = _source_observation(authority, move_id)
    result = materialize_observed_forced_switch_source_application(branch_state=authority["branch_state"], source_branch_fingerprint=authority["resulting_source_branch_fingerprint"], observed_source_result=observation)
    assert result["status"] == "resolved" and result["forced_switch_request"]["target_owner"] == authority["target_owner"]
    stale = {**observation, "source_branch_fingerprint": "stale"}
    assert materialize_observed_forced_switch_source_application(branch_state=authority["branch_state"], source_branch_fingerprint=authority["resulting_source_branch_fingerprint"], observed_source_result=stale)["status"] == "rejected"


@pytest.mark.parametrize(("side", "move_id"), [("self", "dragon-tail"), ("opponent", "circle-throw")])
def test_damage_plus_phazing_evidence_binds_to_source_branch_side_neutrally(side, move_id):
    authority = _authority(_state(), side); observation = _compound(authority, move_id)
    result = materialize_observed_damage_plus_phazing_result(branch_state=authority["branch_state"], source_branch_fingerprint=authority["resulting_source_branch_fingerprint"], observed_result=observation)
    assert result["status"] == "resolved" and result["forced_switch_request"]["target_owner"] == authority["target_owner"]
    assert materialize_observed_damage_plus_phazing_result(branch_state=authority["branch_state"], source_branch_fingerprint=authority["resulting_source_branch_fingerprint"], observed_result={**observation, "source_branch_fingerprint": "stale"})["status"] == "rejected"


def test_projection_is_detached_and_repeated_deterministically_without_replacement_work():
    state = _state(); snapshot = _snapshot(state); before = deepcopy(snapshot)
    first = freeze_runtime_d0_forced_switch_source_authority(runtime_snapshot=snapshot, target_side="self")
    second = freeze_runtime_d0_forced_switch_source_authority(runtime_snapshot=snapshot, target_side="self")
    first["branch_state"]["active"]["self"]["pokemon_id"] = "changed"
    assert snapshot == before and first["resulting_source_branch_fingerprint"] == second["resulting_source_branch_fingerprint"]
