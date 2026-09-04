from copy import deepcopy

from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_taunt_move_selectability import resolve_taunt_move_selectability
from llm.advisor_runtime_d0_taunt_restriction_authority import freeze_runtime_d0_taunt_restriction_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_native_damage_context import _state


def _owner(state):
    pokemon = state["self_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _plan(state, *steps): return {"session_id": state["session_id"], "status": "planned", "conflicts": [], "replay_policy_version": "v1", "ordered_steps": list(steps)}
def _step(oid, sequence, effect, owner, **extra): return {"observation_id": oid, "observation_sequence": sequence, "planned_effect": effect, "trust": "user_confirmed_observation", **owner, **extra}
def _snapshot(state): return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _restriction(state):
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return d0, freeze_runtime_d0_taunt_restriction_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state))


def _move(d0, category):
    owner = d0["active_owners"]["self"]
    return {"status": "resolved", "candidate_id": "attack:x", "move_id": "x", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(owner), "metadata": {"move_id": "x", "category": category}}


def _applied(state):
    owner = _owner(state)
    return project_atomic_transition(state, _plan(state, _step("taunt-hit", 1, "apply_taunt_restriction", owner, turn_number=1, source_action_id="attack:taunt", source_move_id="taunt")), state["session_id"])["projected_state"]


def test_reducer_tracks_exact_three_affected_turns_then_proven_expiry():
    current = _applied(_state("taunt-lifecycle")); owner = _owner(current)
    assert current["current_taunt_restrictions"]["self"]["remaining_target_turns"] == 3
    for sequence, turn, remaining in ((2, 2, 2), (3, 3, 1), (4, 4, None)):
        current = project_atomic_transition(current, _plan(current, _step(f"complete-{turn}", sequence, "complete_restricted_active_turn", owner, turn_number=turn, completion_kind="affected_active_turn_completed")), current["session_id"])["projected_state"]
        assert current["current_taunt_restrictions"]["self"]["remaining_target_turns"] == remaining
    row = current["current_taunt_restrictions"]["self"]
    assert row["state"] == "not_active" and row["retired_reason"] == "expired"
    _, authority = _restriction(current)
    assert authority["status"] == "resolved" and authority["state"] == "not_active"


def test_lifecycle_replay_identity_and_missing_authority_fail_closed():
    applied = _applied(_state("taunt-guards")); owner = _owner(applied)
    completion = _plan(applied, _step("complete", 2, "complete_restricted_active_turn", owner, turn_number=2, completion_kind="affected_active_turn_completed"))
    advanced = project_atomic_transition(applied, completion, applied["session_id"])["projected_state"]
    duplicate = project_atomic_transition(advanced, completion, advanced["session_id"])
    assert duplicate["status"] == "ready_with_projected_state"
    assert duplicate["projected_state"]["current_taunt_restrictions"] == advanced["current_taunt_restrictions"]
    wrong = {**owner, "pokemon_id": "foreign"}
    assert project_atomic_transition(applied, _plan(applied, _step("wrong", 3, "complete_restricted_active_turn", wrong, turn_number=3, completion_kind="affected_active_turn_completed")), applied["session_id"])["status"] == "blocked_by_semantic_conflict"
    _, missing = _restriction(_state("taunt-missing"))
    assert missing["status"] == "incomplete"


def test_switch_retires_taunt_without_transfer_or_reentry_resurrection():
    state = _state("taunt-switch"); state["self_side"]["pokemon"][1] = {**deepcopy(state["self_side"]["pokemon"][0]), "pokemon_id": "incoming"}
    applied = _applied(state); owner = _owner(applied)
    switched = project_atomic_transition(applied, _plan(applied, {"observation_id": "switch", "observation_sequence": 2, "planned_effect": "switch_active", "trust": "user_confirmed_observation", "side": "self", "switch_out_slot_index": 0, "switch_out_pokemon_id": owner["pokemon_id"], "switch_in_slot_index": 1, "switch_in_pokemon_id": "incoming"}), applied["session_id"])["projected_state"]
    row = switched["current_taunt_restrictions"]["self"]
    assert row["state"] == "not_active" and row["retired_reason"] == "switch_out"
    snapshot = _snapshot(switched); incoming_d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": switched["session_id"], "side": "self", "slot_index": 1, "pokemon_id": "incoming"})
    incoming = freeze_runtime_d0_taunt_restriction_authority(strategy_d0=incoming_d0, runtime_snapshot=snapshot, owner=incoming_d0["active_owners"]["self"])
    assert incoming["status"] == "resolved" and incoming["state"] == "not_active" and incoming["retired_activation_owner"] == owner
    reentered = project_atomic_transition(switched, _plan(switched, {"observation_id": "return", "observation_sequence": 3, "planned_effect": "switch_active", "trust": "user_confirmed_observation", "side": "self", "switch_out_slot_index": 1, "switch_out_pokemon_id": "incoming", "switch_in_slot_index": 0, "switch_in_pokemon_id": owner["pokemon_id"]}), switched["session_id"])["projected_state"]
    _, authority = _restriction(reentered)
    assert authority["status"] == "resolved" and authority["state"] == "not_active" and authority["owner"]["pokemon_id"] == owner["pokemon_id"]


def test_active_taunt_blocks_only_exact_bound_status_metadata_without_mutation():
    applied = _applied(_state("taunt-selectability")); owner = _owner(applied); d0, taunt = _restriction(applied)
    status, physical = _move(d0, "status"), _move(d0, "physical")
    assert resolve_taunt_move_selectability(taunt_authority=taunt, owner=owner, move_metadata_authority=status)["selectability"] == "not_selectable"
    assert resolve_taunt_move_selectability(taunt_authority=taunt, owner=owner, move_metadata_authority=physical)["selectability"] == "selectable"
    original = deepcopy(status); unknown = _move(d0, "status"); unknown["metadata"] = {"move_id": "x"}
    assert resolve_taunt_move_selectability(taunt_authority=taunt, owner=owner, move_metadata_authority=unknown)["status"] == "incomplete"
    foreign = deepcopy(status); foreign["active_attacker"] = {**owner, "pokemon_id": "foreign"}
    assert resolve_taunt_move_selectability(taunt_authority=taunt, owner=owner, move_metadata_authority=foreign)["status"] == "rejected"
    assert status == original
