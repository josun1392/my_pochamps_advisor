from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    BERRY_EATEN_STATE_SOURCE,
    LifecycleConfirmationBoundary,
    SWITCH_SOURCE,
    USER_TRUST,
)
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_reducer_state_model import execute_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_current_berry_eaten_authority import (
    freeze_runtime_d0_current_berry_eaten_authority,
)


def _state(session="berry-state"):
    return create_unknown_bootstrap_battle_state(session, "pikachu", "eevee")["state"]


def _owner(state, side="self", slot=None):
    if slot is None:
        slot = state[f"{side}_side"]["active_slot_index"]
    pokemon = state[f"{side}_side"]["pokemon"][slot]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}


def _snapshot(state):
    return {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }


def _confirm(state, *, value, oid, turn=1, item_id=None, side="self", slot=0):
    owner = _owner(state, side, slot)
    boundary = LifecycleConfirmationBoundary(state["session_id"], {
        side: {"slot_index": slot, "pokemon_id": owner["pokemon_id"]}
    })
    boundary._next_sequence = (state.get("last_applied_observation_sequence") or 0) + 1
    payload = {"state": value, "basis": "fresh_battle_initialization" if value == "known_false" else "observed_berry_consumption"}
    if item_id is not None:
        payload["item_id"] = item_id
    result = boundary.confirm(
        event_kind="berry_eaten_state_observed", payload=payload,
        session_id=state["session_id"], source=BERRY_EATEN_STATE_SOURCE,
        trust=USER_TRUST, confirmed=True, side=side, slot_index=slot,
        pokemon_id=owner["pokemon_id"], observation_id=oid, turn_number=turn,
    )
    return result


def _apply(state, *results):
    collection = ObservationCollection(state["session_id"])
    assert collection.add_confirmation_results(results)["status"] == "added"
    plan = build_replay_plan(state, collection.snapshot()["ordered_observations"])
    return execute_atomic_transition(state, plan, expected_session_id=state["session_id"])


def test_missing_history_stays_unknown_in_runtime_d0():
    state = _state()
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    authority = d0["current_berry_eaten_authority"]["self"]
    assert authority["status"] == "incomplete"
    assert authority["state"] == "unknown"


def test_fresh_battle_initialization_is_the_only_false_observation():
    state = _state()
    result = _confirm(state, value="known_false", oid="fresh", turn=1)
    assert result["status"] == "confirmed"
    committed = _apply(state, result)["committed_state"]
    row = committed["self_side"]["pokemon"][0]
    assert row["berry_eaten_state"] == "known_false"
    snapshot = _snapshot(committed)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(committed))
    assert freeze_runtime_d0_current_berry_eaten_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(committed)
    )["state"] == "known_false"
    assert _confirm(_state(), value="known_false", oid="late", turn=2)["status"] == "invalid_provenance"


def test_item_absence_or_missing_consumption_history_does_not_imply_true_or_false():
    state = _state()
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["known_item"] = None
    pokemon["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 3,
        "status": "known_absent",
        "source_observation_id": "item-absent",
        "source_sequence": 1,
    }
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    authority = d0["current_berry_eaten_authority"]["self"]
    assert authority["status"] == "incomplete"
    assert authority["state"] == "unknown"


def test_exact_berry_consumption_sets_true_and_non_berry_is_rejected_by_reducer():
    state = _state()
    result = _confirm(state, value="known_true", oid="eat", turn=3, item_id="cheri-berry")
    assert result["status"] == "confirmed"
    committed = _apply(state, result)
    assert committed["status"] == "committed"
    assert committed["committed_state"]["self_side"]["pokemon"][0]["berry_eaten_state"] == "known_true"

    nonberry = _confirm(_state(), value="known_true", oid="bad", turn=3, item_id="leftovers")
    assert nonberry["status"] == "confirmed"
    rejected = _apply(_state(), nonberry)
    assert rejected["status"] == "blocked_by_semantic_conflict"


def test_true_transition_is_idempotent_and_cannot_reset_false():
    state = _state()
    first = _confirm(state, value="known_true", oid="eat1", turn=2, item_id="cheri-berry")
    committed = _apply(state, first)["committed_state"]
    second = _confirm(committed, value="known_true", oid="eat2", turn=3, item_id="pecha-berry")
    again = _apply(committed, second)
    assert again["status"] == "committed"
    assert again["committed_state"]["self_side"]["pokemon"][0]["berry_eaten_state"] == "known_true"
    false = _confirm(again["committed_state"], value="known_false", oid="reset", turn=1)
    assert _apply(again["committed_state"], false)["status"] == "blocked_by_semantic_conflict"


def test_true_persists_across_switch_out_and_reentry():
    state = _state()
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = "raichu"
    true = _confirm(state, value="known_true", oid="eat", turn=2, item_id="rawst-berry")
    state = _apply(state, true)["committed_state"]

    boundary = LifecycleConfirmationBoundary(state["session_id"], {
        "self": {"slot_index": 0, "pokemon_id": "pikachu"},
        "self_targets": [{"slot_index": 1, "pokemon_id": "raichu"}],
    })
    boundary._next_sequence = (state.get("last_applied_observation_sequence") or 0) + 1
    out = boundary.confirm(
        event_kind="pokemon_switch_observed",
        payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu"},
        session_id=state["session_id"], source=SWITCH_SOURCE, trust=USER_TRUST,
        confirmed=True, side="self", slot_index=0, pokemon_id="pikachu",
        observation_id="sw1", turn_number=3,
    )
    state = _apply(state, out)["committed_state"]
    assert state["self_side"]["pokemon"][0]["berry_eaten_state"] == "known_true"

    boundary = LifecycleConfirmationBoundary(state["session_id"], {
        "self": {"slot_index": 1, "pokemon_id": "raichu"},
        "self_targets": [{"slot_index": 0, "pokemon_id": "pikachu"}],
    })
    boundary._next_sequence = (state.get("last_applied_observation_sequence") or 0) + 1
    back = boundary.confirm(
        event_kind="pokemon_switch_observed",
        payload={"switch_out_slot_index": 1, "switch_out_pokemon_id": "raichu", "switch_in_slot_index": 0, "switch_in_pokemon_id": "pikachu"},
        session_id=state["session_id"], source=SWITCH_SOURCE, trust=USER_TRUST,
        confirmed=True, side="self", slot_index=1, pokemon_id="raichu",
        observation_id="sw2", turn_number=4,
    )
    state = _apply(state, back)["committed_state"]
    assert state["self_side"]["pokemon"][0]["berry_eaten_state"] == "known_true"


def test_true_is_not_cleared_by_faint():
    state = _state()
    true = _confirm(state, value="known_true", oid="eat-before-faint", turn=2, item_id="cheri-berry")
    state = _apply(state, true)["committed_state"]
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["current_hp"] = 0
    pokemon["fainted"] = False
    sequence = state["last_applied_observation_sequence"] + 1
    owner = _owner(state)
    plan = {
        "session_id": state["session_id"], "status": "planned", "conflicts": [],
        "ordered_steps": [{
            "observation_id": "faint", "observation_sequence": sequence,
            "planned_effect": "mark_fainted",
            "trust": "user_confirmed_observation",
            **owner, "turn_number": 2,
        }],
    }
    fainted = execute_atomic_transition(state, plan, expected_session_id=state["session_id"])
    assert fainted["status"] == "committed", fainted
    row = fainted["committed_state"]["self_side"]["pokemon"][0]
    assert row["fainted"] is True
    assert row["berry_eaten_state"] == "known_true"


def test_true_is_not_cleared_by_turn_progression():
    state = _state()
    true = _confirm(state, value="known_true", oid="eat", turn=2, item_id="aspear-berry")
    state = _apply(state, true)["committed_state"]
    sequence = state["last_applied_observation_sequence"] + 1
    plan = {
        "session_id": state["session_id"], "status": "planned", "conflicts": [],
        "ordered_steps": [{
            "observation_id": "eot", "observation_sequence": sequence,
            "planned_effect": "mark_first_end_of_turn_reached",
            "turn_number": 2,
        }],
    }
    progressed = execute_atomic_transition(state, plan, expected_session_id=state["session_id"])
    assert progressed["status"] == "committed"
    assert progressed["committed_state"]["self_side"]["pokemon"][0]["berry_eaten_state"] == "known_true"


def test_foreign_owner_and_stale_d0_fail_closed():
    state = _state()
    result = _confirm(state, value="known_true", oid="eat", turn=2, item_id="cheri-berry")
    state = _apply(state, result)["committed_state"]
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    foreign = {**_owner(state), "pokemon_id": "foreign"}
    assert freeze_runtime_d0_current_berry_eaten_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, owner=foreign
    )["status"] == "rejected"
    advanced = deepcopy(state)
    advanced["last_applied_observation_sequence"] = state["last_applied_observation_sequence"] + 1
    assert freeze_runtime_d0_current_berry_eaten_authority(
        strategy_d0=d0, runtime_snapshot=_snapshot(advanced), owner=_owner(state)
    )["status"] == "rejected"
