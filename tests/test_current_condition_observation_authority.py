"""Strict present/none/unknown current-condition authority contracts."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CONDITION_APPLICATION_SOURCE, CURRENT_CONDITION_SOURCE, SWITCH_SOURCE,
    USER_TRUST, LifecycleConfirmationBoundary,
)
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority, freeze_runtime_strategy_d0,
)


def _state(session="condition-state"):
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side="self"):
    roster = state[f"{side}_side"]
    slot = roster["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": roster["pokemon"][slot]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _observe(state, *, side="self", condition="none", turn=1):
    owner = _owner(state, side)
    boundary = LifecycleConfirmationBoundary(state["session_id"], {name: _owner(state, name) | {"slot_index": 0, "pokemon_id": _owner(state, name)["pokemon_id"]} for name in ("self", "opponent")})
    confirmation = boundary.confirm(
        event_kind="current_condition_observed", payload={"condition": condition},
        session_id=state["session_id"], source=CURRENT_CONDITION_SOURCE, trust=USER_TRUST,
        confirmed=True, side=owner["side"], slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], turn_number=turn,
    )
    assert confirmation["status"] == "confirmed"
    projected = project_atomic_transition(state, build_replay_plan(state, [confirmation["observation"]]), state["session_id"])
    assert projected["status"] == "ready_with_projected_state"
    return projected["projected_state"]


def _authority(state, side="self"):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return snapshot, d0, freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state, side))


def test_fresh_state_and_legacy_condition_application_remain_unknown_not_known_none():
    state = _state()
    _snapshot_value, _d0, authority = _authority(state)
    assert authority["condition"]["status"] == "unknown"

    boundary = LifecycleConfirmationBoundary(state["session_id"], {side: {"slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"]} for side in ("self", "opponent")})
    observed = boundary.confirm(event_kind="condition_applied_observed", payload={"condition": "burn"}, session_id=state["session_id"], source=CONDITION_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="attacker")["observation"]
    projected = project_atomic_transition(state, build_replay_plan(state, [observed]), state["session_id"])["projected_state"]
    assert _authority(projected)[2]["condition"]["status"] == "unknown"


def test_explicit_current_observation_projects_present_and_known_none_detached():
    state = _observe(_state(), condition="paralysis")
    snapshot, d0, authority = _authority(state)
    assert authority["condition"] == {"status": "known_present", "condition": "paralysis", "provenance": "runtime_current_condition_observed"}
    authority["condition"]["condition"] = "burn"
    assert state["self_side"]["pokemon"][0]["condition"] == "paralysis"

    none = _observe(state, condition="none", turn=2)
    assert _authority(none)[2]["condition"]["status"] == "known_none"
    assert freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state))["status"] == "resolved"


def test_switch_preserves_owner_record_but_never_transfers_active_d0_authority_and_stale_fails_closed():
    state = _observe(_state(), condition="burn")
    incoming = deepcopy(state["self_side"]["pokemon"][0]); incoming["pokemon_id"] = "incoming"
    state["self_side"]["pokemon"][1] = incoming
    state["self_side"]["pokemon"][1]["condition"] = {"knowledge": "unknown"}
    state["self_side"]["pokemon"][1].pop("condition_provenance", None)
    switch = {"observation_id": "switch", "observation_sequence": 2, "planned_effect": "switch_active", "trust": USER_TRUST, "side": "self", "switch_out_slot_index": 0, "switch_out_pokemon_id": "attacker", "switch_in_slot_index": 1, "switch_in_pokemon_id": "incoming"}
    switched = project_atomic_transition(state, {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [switch]}, state["session_id"])["projected_state"]
    snapshot, d0, incoming_authority = _authority(switched)
    assert switched["self_side"]["pokemon"][0]["condition"] == "burn"
    assert incoming_authority["condition"]["status"] == "unknown"
    stale = deepcopy(switched); stale["last_applied_observation_sequence"] = 3
    assert freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=_snapshot(stale), owner=_owner(switched))["status"] == "rejected"
