from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, OPPONENT_SWITCH_RESPONSE_SET_SOURCE, USER_TRUST
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_opponent_switch_response_authority import freeze_runtime_d0_opponent_switch_response_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state():
    state = create_unknown_bootstrap_battle_state("s", "self", "opponent")["state"]
    template = deepcopy(state["opponent_side"]["pokemon"][0]); template["pokemon_id"] = "bench"
    state["opponent_side"]["pokemon"][1] = template
    return state


def _owner(state, side):
    slot = state[f"{side}_side"]["active_slot_index"]; return {"session_id": "s", "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _observed(state, permission="permitted", availability="alive"):
    boundary = LifecycleConfirmationBoundary("s", {"self": _owner(state, "self"), "opponent": _owner(state, "opponent")})
    confirmed = boundary.confirm(event_kind="current_opponent_switch_response_set_observed", payload={"permission": permission, "targets": [{"slot_index": 1, "pokemon_id": "bench", "availability": availability}]}, session_id="s", source=OPPONENT_SWITCH_RESPONSE_SET_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=0, pokemon_id="opponent", turn_number=1)
    plan = build_replay_plan(state, [confirmed["observation"]])
    return project_atomic_transition(state, plan, "s")["projected_state"]


def _authority(state):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": "s", "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return freeze_runtime_d0_opponent_switch_response_authority(strategy_d0=d0, runtime_snapshot=snapshot)


def test_explicit_complete_permitted_target_set_produces_only_alive_selectable_target():
    result = _authority(_observed(_state()))
    assert result["status"] == "resolved" and result["selectable_response_action_ids"] == ("opponent_switch:s:1:bench",)
    fainted = _authority(_observed(_state(), availability="fainted"))
    assert fainted["status"] == "resolved" and fainted["selectable_response_action_ids"] == ()


def test_blocked_unknown_and_unknown_target_fail_closed():
    assert _authority(_observed(_state(), permission="blocked"))["selectable_response_action_ids"] == ()
    assert _authority(_observed(_state(), permission="unknown"))["status"] == "incomplete"
    assert _authority(_observed(_state(), availability="unknown"))["status"] == "incomplete"


def test_missing_or_mismatched_current_observation_fails_closed():
    assert _authority(_state())["status"] == "incomplete"
    state = _observed(_state()); state["opponent_side"]["pokemon"][1]["pokemon_id"] = "other"
    assert _authority(state)["status"] == "rejected"
