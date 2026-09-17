from copy import deepcopy

import pytest

import llm.advisor_pending_status_action_runtime_admission as admission_owner
from llm.advisor_champions_sleep_freeze_action_gate import SELF_THAW_MOVES
from llm.advisor_champions_status_progression import SCHEMA
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import CURRENT_ABILITY_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pending_status_action_runtime_admission import admit_pending_status_action_execution
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_pending_status_action_execution_authority import (
    freeze_runtime_d0_pending_status_action_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _base_state():
    state = create_unknown_bootstrap_battle_state("pending-runtime", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state):
    slot = state["self_side"]["active_slot_index"]
    pokemon = state["self_side"]["pokemon"][slot]
    return {
        "session_id": state["session_id"],
        "side": "self",
        "slot_index": slot,
        "pokemon_id": pokemon["pokemon_id"],
    }


def _progression(state, condition, *, prior=0, duration=None):
    owner = _owner(state)
    pokemon = state["self_side"]["pokemon"][owner["slot_index"]]
    pokemon["condition"] = condition
    pokemon["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "condition": condition,
    }
    pokemon["champions_status_progression"] = {
        "schema_version": SCHEMA,
        "owner": deepcopy(owner),
        "condition": condition,
        "origin_id": f"status:{condition}:origin:1",
        "established_turn": 1,
        "prior_attempts": prior,
        "sleep_duration": duration,
        "condition_observation": deepcopy(pokemon["condition_provenance"]),
        "observed_turn": 1,
        "provenance": "observed_champions_status_progression_v1",
    }
    return state


def _manager(condition="sleep", *, prior=0, duration=None):
    state = _progression(_base_state(), condition, prior=prior, duration=duration)
    created = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert created["status"] == "session_ready", created
    return created["manager"]


def _call(manager, *, condition="sleep", outcome="blocked_sleep", move="tackle", execution="blocked",
          blocker=None, action="action:status:1", decision="turn:2:pending", turn=2):
    state = manager.read_state()["state"]
    owner = _owner(state)
    if blocker is None and execution == "blocked":
        blocker = condition
    return admit_pending_status_action_execution(
        runtime_session_manager=manager,
        captured_session_id=state["session_id"],
        side="self",
        slot_index=owner["slot_index"],
        pokemon_id=owner["pokemon_id"],
        turn_number=turn,
        decision_point=decision,
        action_id=action,
        move_id=move,
        condition=condition,
        execution_state=execution,
        blocker=blocker,
        outcome_class=outcome,
    )


def _pokemon(manager):
    state = manager.read_state()["state"]
    return state["self_side"]["pokemon"][state["self_side"]["active_slot_index"]]


def _admit_unrelated_ability(manager):
    state = manager.read_state()["state"]
    owner = _owner(state)
    allocated = manager.allocate_observation_sequence()
    boundary = LifecycleConfirmationBoundary(state["session_id"], {"self": owner})
    confirmed = boundary.confirm(
        event_kind="current_ability_observed", payload={"ability": "pressure"},
        session_id=state["session_id"], source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST,
        confirmed=True, side="self", slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"],
        observation_id=f"{state['session_id']}:unrelated:{allocated['observation_sequence']}", turn_number=4,
    )
    assert confirmed["status"] == "confirmed", confirmed
    confirmed["observation"]["observation_sequence"] = allocated["observation_sequence"]
    assert manager.admit_confirmation(state["session_id"], confirmed)["status"] in {"added", "duplicate"}
    applied = manager.apply(state["session_id"], manager.read_collection_snapshot())
    assert applied["status"] in {"applied", "already_applied"}, applied


def _pending_authority(result, *, condition, move, action="action:status:1", decision="turn:2:pending"):
    snapshot = result["runtime_snapshot"]
    d0 = result["strategy_d0"]
    actor = _owner(snapshot["state"])
    return freeze_runtime_d0_pending_status_action_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        pending_actor=actor,
        pending_action={"decision_point": decision, "action_id": action, "move_id": move, "condition": condition},
    )


@pytest.mark.parametrize(
    "condition,outcome,move",
    [("sleep", "blocked_sleep", "tackle"), ("freeze", "blocked_freeze", "tackle")],
)
def test_blocked_actual_outcomes_increment_once_and_preserve_condition(condition, outcome, move):
    manager = _manager(condition)
    before = deepcopy(_pokemon(manager)["champions_status_progression"])
    result = _call(manager, condition=condition, outcome=outcome, move=move)
    assert result["status"] == "resolved", result
    after = _pokemon(manager)
    row = after["champions_status_progression"]
    assert after["condition"] == condition
    assert row["prior_attempts"] == before["prior_attempts"] + 1
    assert row["origin_id"] == before["origin_id"]
    assert row["established_turn"] == before["established_turn"]
    assert row["sleep_duration"] == before["sleep_duration"]
    assert [event["event_kind"] for event in result["derived_observations"]] == ["champions_status_progression_derived"]
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    authority = _pending_authority(result, condition=condition, move=move)
    assert authority["status"] == "resolved" and authority["outcome_class"] == outcome


@pytest.mark.parametrize(
    "condition,outcome",
    [("sleep", "wake_and_execute"), ("freeze", "natural_thaw_and_execute")],
)
def test_actual_wake_and_thaw_clear_condition_retire_progression_and_freeze_known_none(condition, outcome):
    manager = _manager(condition, prior=1, duration=3 if condition == "sleep" else None)
    result = _call(manager, condition=condition, outcome=outcome, execution="executable", blocker=None)
    assert result["status"] == "resolved", result
    pokemon = _pokemon(manager)
    assert pokemon["condition"] is None
    assert pokemon.get("champions_status_progression") is None
    provenance = pokemon["condition_provenance"]
    assert provenance["event_kind"] == "champions_status_condition_cleared_derived"
    assert provenance["trust"] == "mechanics_derived_runtime"
    assert provenance["source"] == "runtime_champions_status_action_lifecycle_v1"
    assert provenance["source_pending_observation_id"] == result["observation"]["observation_id"]
    assert result["strategy_d0"]["current_condition_authority"]["self"]["condition"]["status"] == "known_none"
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    authority = _pending_authority(result, condition=condition, move="tackle")
    assert authority["status"] == "resolved" and authority["outcome_class"] == outcome


def test_actual_self_thaw_uses_canonical_catalog_and_clears_condition():
    move = sorted(SELF_THAW_MOVES)[0]
    manager = _manager("freeze", prior=1)
    result = _call(manager, condition="freeze", outcome="self_thaw_move_execute", move=move,
                   execution="executable", blocker=None)
    assert result["status"] == "resolved", result
    pokemon = _pokemon(manager)
    assert pokemon["condition"] is None and pokemon.get("champions_status_progression") is None
    assert result["strategy_d0"]["current_condition_authority"]["self"]["condition"]["status"] == "known_none"

    invalid = _manager("freeze", prior=1)
    rejected = _call(invalid, condition="freeze", outcome="self_thaw_move_execute", move="tackle",
                     execution="executable", blocker=None)
    assert rejected["status"] == "rejected"


@pytest.mark.parametrize("move", ["sleep-talk", "snore"])
def test_sleep_exception_executes_without_clearing_or_advancing_progression(move):
    manager = _manager("sleep", prior=1, duration=3)
    before = deepcopy(_pokemon(manager)["champions_status_progression"])
    result = _call(manager, condition="sleep", outcome="sleep_exception_execute", move=move,
                   execution="executable", blocker=None)
    assert result["status"] == "resolved", result
    pokemon = _pokemon(manager)
    assert pokemon["condition"] == "sleep"
    assert pokemon["champions_status_progression"] == before
    assert result["derived_observations"] == []
    authority = _pending_authority(result, condition="sleep", move=move)
    assert authority["status"] == "resolved" and authority["outcome_class"] == "sleep_exception_execute"


def test_same_semantic_blocked_retry_is_idempotent_but_distinct_action_can_advance():
    manager = _manager("sleep")
    first = _call(manager)
    assert first["status"] == "resolved"
    count = _pokemon(manager)["champions_status_progression"]["prior_attempts"]
    collection_size = len(manager.read_collection_snapshot()["ordered_observations"])

    duplicate = _call(manager)
    assert duplicate["status"] == "resolved" and duplicate["reason"] == "duplicate_pending_status_action"
    assert _pokemon(manager)["champions_status_progression"]["prior_attempts"] == count
    assert len(manager.read_collection_snapshot()["ordered_observations"]) == collection_size

    distinct = _call(manager, action="action:status:2", decision="turn:3:pending", turn=3)
    assert distinct["status"] == "resolved", distinct
    assert _pokemon(manager)["champions_status_progression"]["prior_attempts"] == count + 1


def test_same_semantic_retry_after_unrelated_later_observation_is_stale_not_duplicate():
    manager = _manager("sleep")
    assert _call(manager)["status"] == "resolved"
    count = _pokemon(manager)["champions_status_progression"]["prior_attempts"]
    _admit_unrelated_ability(manager)
    result = _call(manager)
    assert result["status"] == "rejected"
    assert _pokemon(manager)["champions_status_progression"]["prior_attempts"] == count


def test_terminal_blocked_outcomes_are_rejected_without_mutation():
    sleep = _manager("sleep", prior=1, duration=2)
    before = deepcopy(sleep.read_state()["state"])
    result = _call(sleep, condition="sleep", outcome="blocked_sleep")
    assert result["status"] == "rejected"
    assert sleep.read_state()["state"] == before

    freeze = _manager("freeze", prior=2)
    before = deepcopy(freeze.read_state()["state"])
    result = _call(freeze, condition="freeze", outcome="blocked_freeze")
    assert result["status"] == "rejected"
    assert freeze.read_state()["state"] == before


@pytest.mark.parametrize(
    "condition,outcome,execution,blocker",
    [
        ("sleep", "blocked_freeze", "blocked", "sleep"),
        ("freeze", "blocked_sleep", "blocked", "freeze"),
        ("freeze", "wake_and_execute", "executable", None),
        ("sleep", "natural_thaw_and_execute", "executable", None),
        ("sleep", "self_thaw_move_execute", "executable", None),
    ],
)
def test_wrong_condition_outcome_combinations_reject(condition, outcome, execution, blocker):
    manager = _manager(condition)
    result = _call(manager, condition=condition, outcome=outcome, execution=execution, blocker=blocker)
    assert result["status"] == "rejected"


def test_sleep_exception_on_ordinary_move_rejects():
    manager = _manager("sleep", prior=1, duration=3)
    result = _call(manager, condition="sleep", outcome="sleep_exception_execute", move="tackle",
                   execution="executable", blocker=None)
    assert result["status"] == "rejected"


def test_missing_progression_and_condition_provenance_fail_closed():
    missing = _manager("sleep", prior=1, duration=3)
    state = missing.read_state()["state"]
    state["self_side"]["pokemon"][0].pop("champions_status_progression")
    created = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert created["status"] == "session_ready"
    result = _call(created["manager"], condition="sleep", outcome="wake_and_execute",
                   execution="executable", blocker=None)
    assert result["status"] == "incomplete"

    malformed = _manager("freeze")
    state = malformed.read_state()["state"]
    state["self_side"]["pokemon"][0].pop("condition_provenance")
    created = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert created["status"] == "session_ready"
    before = deepcopy(created["manager"].read_state()["state"])
    result = _call(created["manager"], condition="freeze", outcome="blocked_freeze")
    assert result["status"] == "rejected"
    assert created["manager"].read_state()["state"] == before


def test_late_forged_derived_event_has_zero_committed_prefix(monkeypatch):
    manager = _manager("sleep")
    before_state = deepcopy(manager.read_state()["state"])
    before_collection = deepcopy(manager.read_collection_snapshot()["ordered_observations"])
    before_snapshot = manager.capture_runtime_state_snapshot(manager.session_id)
    native = admission_owner.derive_status_action_lifecycle_consequence

    def forged(**kwargs):
        result = native(**kwargs)
        if result.get("status") == "confirmed":
            result = deepcopy(result)
            result["observation"]["payload"]["source_pending_observation_id"] = "foreign-source"
        return result

    monkeypatch.setattr(admission_owner, "derive_status_action_lifecycle_consequence", forged)
    result = _call(manager)
    assert result["status"] == "rejected"
    assert manager.read_state()["state"] == before_state
    assert manager.read_collection_snapshot()["ordered_observations"] == before_collection
    after_snapshot = manager.capture_runtime_state_snapshot(manager.session_id)
    assert after_snapshot["state_fingerprint"] == before_snapshot["state_fingerprint"]


def test_compound_pending_d0_freshness_rejects_unrelated_or_forged_terminal_binding():
    manager = _manager("sleep")
    result = _call(manager)
    assert result["status"] == "resolved"
    action = {"decision_point": "turn:2:pending", "action_id": "action:status:1", "move_id": "tackle", "condition": "sleep"}
    actor = _owner(result["runtime_snapshot"]["state"])
    assert freeze_runtime_d0_pending_status_action_execution_authority(
        strategy_d0=result["strategy_d0"], runtime_snapshot=result["runtime_snapshot"],
        pending_actor=actor, pending_action=action,
    )["status"] == "resolved"

    for field, value in (("lifecycle_batch_terminal_sequence", 999), ("lifecycle_batch_source_observation_id", "forged")):
        snapshot = deepcopy(result["runtime_snapshot"])
        snapshot["state"]["pending_status_action_execution_context"][field] = value
        snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
        assert freeze_runtime_d0_pending_status_action_execution_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, pending_actor=actor, pending_action=action,
        )["status"] == "rejected"

    snapshot = deepcopy(result["runtime_snapshot"])
    snapshot["state"]["last_applied_observation_sequence"] += 1
    snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    assert freeze_runtime_d0_pending_status_action_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, pending_actor=actor, pending_action=action,
    )["status"] == "rejected"


def test_switch_out_and_reentry_preserve_progression_then_new_admission_consumes_it():
    state = _progression(_base_state(), "sleep", prior=1, duration=3)
    original = deepcopy(state["self_side"]["pokemon"][0]["champions_status_progression"])
    bench = deepcopy(state["self_side"]["pokemon"][0])
    bench["pokemon_id"] = "bench-member"
    bench.pop("champions_status_progression", None)
    bench["condition"] = "none"
    bench["condition_provenance"] = {
        "event_kind": "current_condition_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "condition": "none",
    }
    state["self_side"]["pokemon"][1] = bench
    session = state["session_id"]
    for sequence, out_slot, in_slot, out_id, in_id in (
        (2, 0, 1, "self-a", "bench-member"),
        (3, 1, 0, "bench-member", "self-a"),
    ):
        event = {
            "observation_id": f"switch-{sequence}", "observation_sequence": sequence,
            "planned_effect": "switch_active", "side": "self", "trust": "user_confirmed_observation",
            "turn_number": 2, "switch_out_slot_index": out_slot, "switch_in_slot_index": in_slot,
            "switch_out_pokemon_id": out_id, "switch_in_pokemon_id": in_id,
        }
        projected = project_atomic_transition(
            state,
            {"session_id": session, "status": "planned", "conflicts": [], "ordered_steps": [event]},
            session,
        )
        assert projected["status"] == "ready_with_projected_state", projected
        state = projected["projected_state"]
    assert state["self_side"]["pokemon"][0]["champions_status_progression"] == original
    created = BattleObservationRuntimeSessionManager.create(session, state)
    assert created["status"] == "session_ready"
    result = _call(created["manager"], condition="sleep", outcome="blocked_sleep",
                   action="action:status:return", decision="turn:3:pending", turn=3)
    assert result["status"] == "resolved", result
    assert _pokemon(created["manager"])["champions_status_progression"]["prior_attempts"] == 2
