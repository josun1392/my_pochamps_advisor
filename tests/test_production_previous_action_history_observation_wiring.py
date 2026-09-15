from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import EXECUTED_MOVE_SOURCE, PREVIOUS_ACTION_RESULT_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_previous_action_result_authority import freeze_runtime_d0_previous_action_result_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_detached_previous_action_failure_power_authority import materialize_previous_action_failure_power_authority


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _admit(manager, *, side="self", move="tackle", selected=None, action="action:tackle", result=None, session="s"):
    return admit_previous_action_history_observation(runtime_session_manager=manager, captured_session_id=session, side=side, execution_move_id=move, selected_move_id=selected or move, source_action_id=action, result_class=result, turn_number=1)


def _power(manager):
    snap = manager.capture_runtime_state_snapshot("s"); state = snap["state"]; pokemon = state["self_side"]["pokemon"][0]
    owner = {"session_id":"s", "side":"self", "slot_index":0, "pokemon_id":pokemon["pokemon_id"]}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snap, decision_owner=owner)
    prior = freeze_runtime_d0_previous_action_result_authority(strategy_d0=d0, runtime_snapshot=snap, owner=owner)
    return materialize_previous_action_failure_power_authority(strategy_d0=d0, move={"move_id":"stomping-tantrum","type":"ground","category":"physical","power":75,"accuracy":100,"priority":0,"contact":True}, user=owner, previous_action_authority=prior)


def test_execution_only_reaches_exact_reducer_history_and_preserves_owner():
    manager = _manager(); result = _admit(manager)
    assert result["status"] == "resolved"
    row = manager.read_state()["state"]["self_side"]["pokemon"][0]["last_executed_move"]
    assert row["owner"] == {"session_id":"s", "side":"self", "slot_index":0, "pokemon_id":"pikachu"}
    assert row["move_id"] == "tackle" and row["source_action_id"] == "action:tackle"
    assert row["execution_id"] == result["observations"][0]["observation_id"]
    assert manager.read_state()["state"]["self_side"]["pokemon"][0].get("previous_action_result") is None


def test_exact_failure_success_and_later_execution_lifecycle():
    manager = _manager()
    assert _admit(manager, result="accuracy_miss")["status"] == "resolved"
    assert _power(manager)["selected_base_power"] == 150
    assert _admit(manager, move="scratch", action="action:scratch")["status"] == "resolved"
    assert _power(manager)["status"] == "incomplete"
    assert _admit(manager, move="scratch", action="action:scratch-2", result="success")["status"] == "resolved"
    assert _power(manager)["selected_base_power"] == 75


def test_rejects_stale_session_foreign_or_malformed_inputs_without_mutation():
    manager = _manager()
    assert _admit(manager, session="old")["status"] == "rejected"
    assert _admit(manager, side="foreign")["status"] == "rejected"
    assert _admit(manager, move="Bad Move")["status"] == "rejected"
    assert _admit(manager, action="bad action")["status"] == "rejected"
    assert _admit(manager, result="invented")["status"] == "rejected"
    assert manager.read_collection_snapshot()["ordered_observations"] == []


def test_replay_rejects_result_before_or_mismatched_execution():
    manager = _manager(); state = manager.read_state()["state"]
    owner = {"session_id":"s", "side":"self", "slot_index":0, "pokemon_id":"pikachu"}
    boundary = LifecycleConfirmationBoundary("s", {"self": owner})
    result = boundary.confirm(event_kind="previous_action_result_observed", payload={"previous_action_id":"action:tackle","selected_move_id":"tackle","execution_move_id":"tackle","result_class":"accuracy_miss"}, session_id="s", source=PREVIOUS_ACTION_RESULT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", observation_id="result", turn_number=1)["observation"]
    execution = boundary.confirm(event_kind="executed_move_observed", payload={"move_id":"scratch","source_action_id":"action:scratch"}, session_id="s", source=EXECUTED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", observation_id="execution", turn_number=1)["observation"]
    plan = build_replay_plan(state, [result, execution])
    assert [step["planned_effect"] for step in plan["ordered_steps"]] == ["record_executed_move"]
    assert plan["unsupported_events"] == [result]


def test_opponent_history_is_isolated_and_duplicate_replay_is_deterministic():
    manager = _manager(); result = _admit(manager, side="opponent", move="scratch", action="action:opponent", result="success")
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0].get("last_executed_move") is None
    assert state["opponent_side"]["pokemon"][0]["previous_action_result"]["result_class"] == "success"
    snapshot = manager.read_collection_snapshot(); assert manager.apply("s", snapshot)["status"] == "already_applied"
    assert result["observations"][0]["observation_sequence"] < result["observations"][1]["observation_sequence"]
