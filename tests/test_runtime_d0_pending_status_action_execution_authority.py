from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_CONDITION_SOURCE,
    PENDING_STATUS_ACTION_EXECUTION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_pending_status_action_execution_authority import (
    freeze_runtime_d0_pending_status_action_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state():
    state = create_unknown_bootstrap_battle_state("pending-status", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side="self"):
    roster = state[f"{side}_side"]
    slot = roster["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": roster["pokemon"][slot]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _action(*, condition="sleep", action_id="attack:snore-check", move_id="snore-check", decision_point="turn:1:pending"):
    return {"decision_point": decision_point, "action_id": action_id, "move_id": move_id, "condition": condition}


def _boundary(state):
    return LifecycleConfirmationBoundary(state["session_id"], {side: _owner(state, side) for side in ("self", "opponent")})


def _project(state, observations):
    plan = build_replay_plan(state, observations)
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return result["projected_state"]


def _condition_observation(state, *, side="self", condition="sleep", turn=1, boundary=None):
    owner = _owner(state, side)
    result = (boundary or _boundary(state)).confirm(
        event_kind="current_condition_observed", payload={"condition": condition}, session_id=state["session_id"],
        source=CURRENT_CONDITION_SOURCE, trust=USER_TRUST, confirmed=True,
        side=owner["side"], slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], turn_number=turn,
    )
    assert result["status"] == "confirmed"
    return result["observation"]


def _execution_observation(state, *, side="self", condition="sleep", execution_state="blocked", turn=2, action=None, sequence=None, boundary=None):
    owner, action = _owner(state, side), action or _action(condition=condition)
    result = (boundary or _boundary(state)).confirm(
        event_kind="pending_status_action_execution_observed",
        payload={"decision_point": action["decision_point"], "action_id": action["action_id"], "move_id": action["move_id"], "condition": condition, "execution_state": execution_state, "blocker": condition if execution_state == "blocked" else None},
        session_id=state["session_id"], source=PENDING_STATUS_ACTION_EXECUTION_SOURCE, trust=USER_TRUST,
        confirmed=True, side=owner["side"], slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], turn_number=turn,
    )
    assert result["status"] == "confirmed", result
    if sequence is not None:
        result["observation"]["observation_sequence"] = sequence
    return result["observation"]


def _freeze(state, *, side="self", action=None):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return freeze_runtime_d0_pending_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, pending_actor=_owner(state, side), pending_action=action or _action())


def test_sleep_and_freeze_explicit_blocked_and_executable_results_freeze_exactly():
    sleep = _state(); action = _action(condition="sleep")
    boundary = _boundary(sleep)
    sleep = _project(sleep, [_condition_observation(sleep, condition="sleep", boundary=boundary), _execution_observation(sleep, condition="sleep", action=action, boundary=boundary)])
    blocked = _freeze(sleep, action=action)
    assert blocked["status"] == "resolved" and blocked["execution_state"] == "blocked" and blocked["blocker"] == "sleep"

    freeze = _state(); action = _action(condition="freeze", action_id="attack:freeze-check", move_id="freeze-check")
    boundary = _boundary(freeze)
    freeze = _project(freeze, [_condition_observation(freeze, condition="freeze", boundary=boundary), _execution_observation(freeze, condition="freeze", execution_state="executable", action=action, boundary=boundary)])
    executable = _freeze(freeze, action=action)
    assert executable["status"] == "resolved" and executable["execution_state"] == "executable" and executable["blocker"] is None


def test_bare_sleep_or_freeze_never_becomes_execution_authority():
    state = _state()
    state = _project(state, [_condition_observation(state, condition="sleep")])
    assert _freeze(state)["status"] == "incomplete"


def test_action_actor_condition_and_staleness_mismatches_fail_closed():
    state = _state(); action = _action()
    boundary = _boundary(state)
    state = _project(state, [_condition_observation(state, boundary=boundary), _execution_observation(state, action=action, boundary=boundary)])
    assert _freeze(state, action={**action, "move_id": "other"})["status"] == "rejected"
    assert _freeze(state, side="opponent", action=action)["status"] == "rejected"
    changed = deepcopy(state); changed["self_side"]["pokemon"][0]["condition"] = "freeze"; changed["self_side"]["pokemon"][0]["condition_provenance"]["condition"] = "freeze"
    assert _freeze(changed, action=action)["status"] == "rejected"
    stale = deepcopy(state); stale["last_applied_observation_sequence"] += 1
    assert _freeze(stale, action=action)["status"] == "rejected"


def test_lifecycle_rejects_malformed_and_reducer_rejects_conflicting_same_sequence():
    state = _state(); owner = _owner(state)
    invalid = _boundary(state).confirm(
        event_kind="pending_status_action_execution_observed", payload={"decision_point": "d", "action_id": "a", "move_id": "m", "condition": "sleep", "execution_state": "blocked", "blocker": "freeze"},
        session_id=state["session_id"], source=PENDING_STATUS_ACTION_EXECUTION_SOURCE, trust=USER_TRUST,
        confirmed=True, side=owner["side"], slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], turn_number=1,
    )
    assert invalid["status"] == "invalid_provenance"

    action = _action(); conditioned = _project(state, [_condition_observation(state)])
    first = _execution_observation(conditioned, action=action, sequence=2)
    second = deepcopy(first); second["observation_id"] = "other"; second["payload"]["execution_state"] = "executable"; second["payload"]["blocker"] = None
    plan = build_replay_plan(conditioned, [first, second])
    result = project_atomic_transition(conditioned, plan, conditioned["session_id"])
    assert result["status"] == "blocked_by_semantic_conflict"
