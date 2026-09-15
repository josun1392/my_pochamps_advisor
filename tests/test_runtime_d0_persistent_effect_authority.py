"""Runtime D0 projection for reducer-owned persistent effects."""
from copy import deepcopy

import pytest

from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import PERSISTENT_EFFECT_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_persistent_effect_authority import persistent_effect_state
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_persistent_effect_authority import project_runtime_d0_persistent_effect_branch
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _state():
    state = create_unknown_bootstrap_battle_state("d0-persistent", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
        bench = deepcopy(state[f"{side}_side"]["pokemon"][0]); bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    return state


def _owner(state, side="self"):
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _d0(state):
    snapshot = _snapshot(state)
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))


def _set(state, family, *, side="self", status="active", sequence=1, source_side=None, source_slot=None):
    event = {"observation_id": f"{family}-{side}-{sequence}", "observation_sequence": sequence, "planned_effect": f"set_current_{family}_state", "side": side, "slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"], "persistent_state": status, "trust": USER_TRUST, "turn_number": 1}
    if source_side is not None: event.update(source_side=source_side, source_slot_index=source_slot)
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [event]}
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return result["projected_state"]


def _result(state):
    snapshot, d0 = _d0(state)
    result = project_runtime_d0_persistent_effect_branch(strategy_d0=d0, runtime_snapshot=snapshot)
    assert result["status"] == "resolved", result
    return snapshot, d0, result


def _row(result, family, side="self"):
    return persistent_effect_state(result["branch_state"], family, side, result["active_owners"][side])


def _request(result, side):
    return {"schema_version": "forced-switch-request-v1", "session_id": result["session_id"], "source_branch_fingerprint": result["resulting_branch_fingerprint"], "target_owner": result["active_owners"][side], "request_kind": "drag_out", "provenance": "trusted_forced_switch_request_v1"}


def test_exact_runtime_d0_resolves_with_complete_detached_fingerprint_chain():
    state = _state(); snapshot, d0, result = _result(state)
    assert result["source_runtime_fingerprint"] == snapshot["state_fingerprint"] == d0["source_runtime_fingerprint"]
    assert result["source_strategy_preview_fingerprint"] == d0["strategy_preview_fingerprint"] == fingerprint_transition_preview_state(d0["strategy_state"])
    assert result["resulting_branch_fingerprint"] == fingerprint_transition_preview_state(result["branch_state"])
    assert result["resulting_branch_fingerprint"] != result["source_strategy_preview_fingerprint"]
    assert len(result["branch_persistent_effect_authority"]["states"]) == 6


@pytest.mark.parametrize("mutate", ["stale", "foreign", "runtime_fingerprint", "preview_fingerprint", "owners"])
def test_rejects_stale_foreign_forged_and_owner_mismatched_bindings(mutate):
    state = _state(); snapshot, d0 = _d0(state)
    if mutate == "stale":
        stale = deepcopy(state); stale["last_applied_observation_sequence"] = 1; snapshot = _snapshot(stale)
    elif mutate == "foreign": snapshot = {**snapshot, "session_id": "foreign"}
    elif mutate == "runtime_fingerprint": d0["source_runtime_fingerprint"] = "forged"
    elif mutate == "preview_fingerprint": d0["strategy_preview_fingerprint"] = "forged"
    else: d0["active_owners"]["self"]["pokemon_id"] = "forged"
    assert project_runtime_d0_persistent_effect_branch(strategy_d0=d0, runtime_snapshot=snapshot)["status"] == "rejected"


def test_unknown_inactive_active_and_both_sides_project_independently():
    state = _state(); _, _, absent = _result(state)
    assert all(_row(absent, family, side)["state"] == "unknown" for side in ("self", "opponent") for family in ("aqua_ring", "ingrain", "leech_seed"))
    state = _set(state, "aqua_ring", status="inactive")
    state = _set(state, "ingrain", side="opponent", status="active", sequence=2)
    _, _, result = _result(state)
    assert _row(result, "aqua_ring")["state"] == "known_inactive"
    assert _row(result, "ingrain", "opponent")["state"] == "known_active"
    assert _row(result, "ingrain", "self")["state"] == "unknown" and _row(result, "aqua_ring", "opponent")["state"] == "unknown"


def test_active_leech_seed_preserves_exact_source_slot_across_source_active_owner_change():
    state = _set(_state(), "leech_seed", status="active", source_side="opponent", source_slot=0)
    # A current source-side identity change does not rewrite target-bound source_slot.
    state["opponent_side"]["active_slot_index"] = 1
    _, _, result = _result(state)
    assert _row(result, "leech_seed")["state"] == "known_active"
    assert _row(result, "leech_seed")["source_slot"] == {"session_id": state["session_id"], "side": "opponent", "slot_index": 0}
    state = _set(_state(), "leech_seed", side="opponent", status="active", source_side="self", source_slot=0)
    _, _, other = _result(state)
    assert _row(other, "leech_seed", "opponent")["source_slot"]["side"] == "self"


def test_inactive_and_unknown_leech_seed_have_no_source_slot_and_inputs_are_detached():
    state = _set(_state(), "leech_seed", status="inactive")
    snapshot, d0, result = _result(state)
    assert "source_slot" not in _row(result, "leech_seed")
    assert "source_slot" not in _row(_result(_state())[2], "leech_seed")
    before_snapshot, before_d0 = deepcopy(snapshot), deepcopy(d0)
    result["branch_state"]["branch_persistent_effect_authority"]["states"][0]["state"] = "changed"
    assert snapshot == before_snapshot and d0 == before_d0


@pytest.mark.parametrize(("side", "state_name", "expected"), [
    ("self", "active", "cancelled"), ("self", "inactive", "allowed_to_proceed"),
    ("opponent", "active", "cancelled"), ("opponent", "inactive", "allowed_to_proceed"),
])
def test_forced_switch_reads_projected_ingrain_side_neutrally(side, state_name, expected):
    state = _set(_state(), "ingrain", side=side, status=state_name)
    _, _, result = _result(state)
    decision = decide_forced_switch_cancellation(branch_state=result["branch_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], forced_switch_request=_request(result, side))
    assert decision["status"] == "resolved" and decision["decision"] == expected


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_forced_switch_unknown_ingrain_is_incomplete(side):
    _, _, result = _result(_state())
    assert decide_forced_switch_cancellation(branch_state=result["branch_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], forced_switch_request=_request(result, side)) == {"status": "incomplete", "reason": "ingrain_persistent_effect_unknown"}


def test_production_observation_replay_state_flows_to_d0_and_cancels_ingrain():
    state = _state(); owner = _owner(state)
    boundary = LifecycleConfirmationBoundary(state["session_id"], {"self": {"slot_index": 0, "pokemon_id": owner["pokemon_id"]}, "opponent": {"slot_index": 0, "pokemon_id": _owner(state, "opponent")["pokemon_id"]}})
    confirmation = boundary.confirm(event_kind="current_ingrain_state_observed", payload={"persistent_state": "active"}, session_id=state["session_id"], source=PERSISTENT_EFFECT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id=owner["pokemon_id"], turn_number=1)
    collection = ObservationCollection(state["session_id"]); assert collection.add_confirmation_result(confirmation)["status"] == "added"
    plan = build_replay_plan(state, collection.snapshot()["ordered_observations"])
    state = project_atomic_transition(state, plan, state["session_id"])["projected_state"]
    _, _, result = _result(state)
    assert _row(result, "ingrain")["state"] == "known_active"
    assert decide_forced_switch_cancellation(branch_state=result["branch_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], forced_switch_request=_request(result, "self"))["decision"] == "cancelled"
