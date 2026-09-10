from copy import deepcopy

from llm.advisor_detached_current_healing_prevented_at_item_check_authority import (
    materialize_detached_current_healing_prevented_at_item_check_authority,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_HEALING_PREVENTED_SOURCE, SWITCH_SOURCE, USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_current_healing_prevented_authority,
    freeze_runtime_strategy_d0,
)


def _state(session="healing-prevented-d0"):
    state = create_unknown_bootstrap_battle_state(session, "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side="self"):
    roster = state[f"{side}_side"]
    slot = roster["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": roster["pokemon"][slot]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _authority(state, side="self"):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return snapshot, d0, freeze_runtime_d0_current_healing_prevented_authority(strategy_d0=d0, runtime_snapshot=snapshot, recipient=_owner(state, side))


def _observe(state, *, side="self", status="active", turn=1):
    owner = _owner(state, side)
    boundary = LifecycleConfirmationBoundary(state["session_id"], {name: _owner(state, name) for name in ("self", "opponent")})
    confirmed = boundary.confirm(
        event_kind="current_healing_prevented_observed", payload={"status": status},
        session_id=state["session_id"], source=CURRENT_HEALING_PREVENTED_SOURCE,
        trust=USER_TRUST, confirmed=True, side=owner["side"], slot_index=owner["slot_index"],
        pokemon_id=owner["pokemon_id"], turn_number=turn,
    )
    assert confirmed["status"] == "confirmed"
    projected = project_atomic_transition(state, build_replay_plan(state, [confirmed["observation"]]), state["session_id"])
    assert projected["status"] == "ready_with_projected_state"
    return projected["projected_state"]


def test_explicit_present_absent_and_missing_remain_three_distinct_states():
    assert _authority(_state())[2]["status"] == "incomplete"
    assert _authority(_state())[2]["state"] == "unknown"
    present = _authority(_observe(_state(), status="active"))[2]
    absent = _authority(_observe(_state(), status="inactive"))[2]
    assert present["status"] == "resolved" and present["state"] == "known_present"
    assert absent["status"] == "resolved" and absent["state"] == "known_absent"


def test_only_the_explicit_production_observation_source_is_accepted():
    state = _state()
    owner = _owner(state)
    boundary = LifecycleConfirmationBoundary(state["session_id"], {"self": owner, "opponent": _owner(state, "opponent")})
    rejected = boundary.confirm(
        event_kind="current_healing_prevented_observed", payload={"status": "inactive"},
        session_id=state["session_id"], source="ui_current_condition_confirmation", trust=USER_TRUST,
        confirmed=True, side="self", slot_index=0, pokemon_id="self-a", turn_number=1,
    )
    assert rejected["status"] == "invalid_provenance"
    assert _authority(state)[2]["state"] == "unknown"


def test_stale_foreign_and_malformed_observations_fail_closed():
    state = _observe(_state(), status="active")
    snapshot, d0, authority = _authority(state)
    assert authority["status"] == "resolved"
    stale = deepcopy(state); stale["last_applied_observation_sequence"] = 2
    assert freeze_runtime_d0_current_healing_prevented_authority(strategy_d0=d0, runtime_snapshot=_snapshot(stale), recipient=_owner(state))["status"] == "rejected"
    foreign = deepcopy(snapshot); foreign["session_id"] = "foreign"
    assert freeze_runtime_d0_current_healing_prevented_authority(strategy_d0=d0, runtime_snapshot=foreign, recipient=_owner(state))["status"] == "rejected"
    state["self_side"]["pokemon"][0]["healing_prevented_status_provenance"]["trust"] = "untrusted"
    assert _authority(state)[2]["status"] == "rejected"


def test_switch_does_not_transfer_an_observation_to_the_incoming_active_owner():
    state = _observe(_state(), status="active")
    incoming = deepcopy(state["self_side"]["pokemon"][0])
    incoming["pokemon_id"] = "self-b"
    incoming["healing_prevented_status"] = {"knowledge": "unknown"}
    incoming.pop("healing_prevented_status_provenance", None)
    state["self_side"]["pokemon"][1] = incoming
    switch = {"observation_id": "switch", "observation_sequence": 2, "planned_effect": "switch_active", "trust": USER_TRUST, "side": "self", "switch_out_slot_index": 0, "switch_out_pokemon_id": "self-a", "switch_in_slot_index": 1, "switch_in_pokemon_id": "self-b"}
    switched = project_atomic_transition(state, {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [switch]}, state["session_id"])["projected_state"]
    assert _authority(switched)[2]["state"] == "unknown"


def test_d0_authority_is_accepted_by_the_detached_item_check_consumer():
    state = _observe(_state(), side="opponent", status="inactive")
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    recipient = _owner(state, "opponent")
    current = freeze_runtime_d0_current_healing_prevented_authority(strategy_d0=d0, runtime_snapshot=snapshot, recipient=recipient)
    binding = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    leaf = {"action_type": "attack", "consequences": {}, "provenance": {**binding, "attacker": _owner(state, "self"), "target": recipient, "move_id": "tackle"}}
    result = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=leaf, recipient=recipient, current_healing_prevented_authority=current)
    assert result["status"] == "resolved" and result["state"] == "known_absent"
