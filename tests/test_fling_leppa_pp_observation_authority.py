from copy import deepcopy

import pytest

from llm.advisor_current_combined_opponent_response_universe_observation import (
    admit_current_combined_opponent_response_universe_observation,
)
from llm.advisor_current_opponent_response_set_observation import (
    admit_current_opponent_response_set_observation,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_current_opponent_move_pp_state_authority import (
    freeze_runtime_d0_current_opponent_move_pp_state_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


MOVES = ["water-gun", "tackle", "growl", "tail-whip"]


def _manager(session="leppa-pp", *, bench=False):
    state = create_unknown_bootstrap_battle_state(session, "self", "opponent")["state"]
    if bench:
        other = deepcopy(state["opponent_side"]["pokemon"][0])
        other["pokemon_id"] = "bench"
        state["opponent_side"]["pokemon"][1] = other
    made = BattleObservationRuntimeSessionManager.create(session, state)
    assert made["status"] == "session_ready"
    return made["manager"]


def _usability(*, zero_move=None, zero_reason="no_pp"):
    rows = {move: {"status": "usable"} for move in MOVES}
    if zero_move is not None:
        rows[zero_move] = {"status": "unusable", "reason": zero_reason}
    return rows


def _pp(values):
    return [
        {"slot_index": index, "move_id": MOVES[index], "current_pp": current, "max_pp": maximum}
        for index, (current, maximum) in enumerate(values)
    ]


def _d0(manager, session="leppa-pp"):
    snapshot = manager.capture_runtime_state_snapshot(session)
    state = snapshot["state"]
    owner = {
        "session_id": session,
        "side": "self",
        "slot_index": state["self_side"]["active_slot_index"],
        "pokemon_id": state["self_side"]["pokemon"][state["self_side"]["active_slot_index"]]["pokemon_id"],
    }
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)


def test_response_set_without_pp_remains_backward_compatible_and_only_pp_is_incomplete():
    manager = _manager()
    result = admit_current_opponent_response_set_observation(
        runtime_session_manager=manager,
        captured_session_id="leppa-pp",
        move_ids=MOVES,
        move_usability=_usability(),
        turn_number=1,
    )
    assert result["status"] == "resolved"
    opponent = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    record = opponent["current_opponent_response_set"]
    assert set(record) == {"moveset_completeness", "move_ids", "provenance"}
    assert record["move_ids"] == MOVES
    snapshot, d0 = _d0(manager)
    pp = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
    )
    assert pp["status"] == "incomplete"
    assert pp["reason"] == "current_opponent_move_pp_snapshot_unknown"


def test_valid_exact_ordered_pp_snapshot_is_reduced_and_strictly_resolved():
    manager = _manager()
    slots = _pp([(12, 20), (0, 35), (40, 40), (15, 20)])
    result = admit_current_opponent_response_set_observation(
        runtime_session_manager=manager,
        captured_session_id="leppa-pp",
        move_ids=MOVES,
        move_usability=_usability(zero_move="tackle"),
        move_pp_slots=slots,
        turn_number=1,
    )
    assert result["status"] == "resolved", result
    state = manager.read_state()["state"]
    record = state["opponent_side"]["pokemon"][0]["current_opponent_response_set"]
    assert record["move_pp_slots"] == slots
    snapshot, d0 = _d0(manager)
    pp = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
    )
    assert pp["status"] == "resolved", pp
    assert list(pp["ordered_move_ids"]) == MOVES
    assert list(pp["ordered_pp_slots"]) == slots
    assert pp["response_observation_source_sequence"] == record["provenance"]["source_sequence"]


@pytest.mark.parametrize(
    ("slots", "usability"),
    [
        (
            [
                {"slot_index": 1, "move_id": "water-gun", "current_pp": 1, "max_pp": 10},
                {"slot_index": 0, "move_id": "tackle", "current_pp": 1, "max_pp": 10},
                {"slot_index": 2, "move_id": "growl", "current_pp": 1, "max_pp": 10},
                {"slot_index": 3, "move_id": "tail-whip", "current_pp": 1, "max_pp": 10},
            ],
            _usability(),
        ),
        (
            [
                {"slot_index": 0, "move_id": "water-gun", "current_pp": -1, "max_pp": 10},
                {"slot_index": 1, "move_id": "tackle", "current_pp": 1, "max_pp": 10},
                {"slot_index": 2, "move_id": "growl", "current_pp": 1, "max_pp": 10},
                {"slot_index": 3, "move_id": "tail-whip", "current_pp": 1, "max_pp": 10},
            ],
            _usability(),
        ),
        (
            [
                {"slot_index": 0, "move_id": "water-gun", "current_pp": 1, "max_pp": 0},
                {"slot_index": 1, "move_id": "tackle", "current_pp": 1, "max_pp": 10},
                {"slot_index": 2, "move_id": "growl", "current_pp": 1, "max_pp": 10},
                {"slot_index": 3, "move_id": "tail-whip", "current_pp": 1, "max_pp": 10},
            ],
            _usability(),
        ),
        (
            [
                {"slot_index": 0, "move_id": "water-gun", "current_pp": 11, "max_pp": 10},
                {"slot_index": 1, "move_id": "tackle", "current_pp": 1, "max_pp": 10},
                {"slot_index": 2, "move_id": "growl", "current_pp": 1, "max_pp": 10},
                {"slot_index": 3, "move_id": "tail-whip", "current_pp": 1, "max_pp": 10},
            ],
            _usability(),
        ),
        (_pp([(0, 10), (1, 10), (1, 10), (1, 10)]), _usability()),
        (_pp([(1, 10), (1, 10), (1, 10), (1, 10)]), _usability(zero_move="water-gun")),
    ],
)
def test_invalid_or_contradictory_pp_snapshot_is_not_admitted(slots, usability):
    manager = _manager()
    result = admit_current_opponent_response_set_observation(
        runtime_session_manager=manager,
        captured_session_id="leppa-pp",
        move_ids=MOVES,
        move_usability=usability,
        move_pp_slots=slots,
        turn_number=1,
    )
    assert result["status"] == "incomplete"
    state = manager.read_state()["state"]
    assert "current_opponent_response_set" not in state["opponent_side"]["pokemon"][0]


@pytest.mark.parametrize("mutation", ["duplicate_slot", "wrong_move", "reordered"])
def test_strict_pp_authority_rejects_tampered_reducer_pp_record(mutation):
    manager = _manager()
    slots = _pp([(12, 20), (0, 35), (40, 40), (15, 20)])
    result = admit_current_opponent_response_set_observation(
        runtime_session_manager=manager,
        captured_session_id="leppa-pp",
        move_ids=MOVES,
        move_usability=_usability(zero_move="tackle"),
        move_pp_slots=slots,
        turn_number=1,
    )
    assert result["status"] == "resolved"
    state = deepcopy(manager.read_state()["state"])
    rows = state["opponent_side"]["pokemon"][0]["current_opponent_response_set"]["move_pp_slots"]
    if mutation == "duplicate_slot":
        rows[1]["slot_index"] = 0
    elif mutation == "wrong_move":
        rows[1]["move_id"] = "growl"
    else:
        rows[0], rows[1] = rows[1], rows[0]
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": state,
        "state_fingerprint": state_fingerprint(state),
    }
    owner = {
        "session_id": state["session_id"],
        "side": "self",
        "slot_index": state["self_side"]["active_slot_index"],
        "pokemon_id": state["self_side"]["pokemon"][state["self_side"]["active_slot_index"]]["pokemon_id"],
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    pp = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
    )
    assert pp["status"] == "rejected"


def test_combined_response_admission_keeps_move_switch_and_pp_on_one_sequence():
    manager = _manager("leppa-combined", bench=True)
    slots = _pp([(12, 20), (0, 35), (40, 40), (15, 20)])
    result = admit_current_combined_opponent_response_universe_observation(
        runtime_session_manager=manager,
        captured_session_id="leppa-combined",
        move_ids=MOVES,
        move_usability=_usability(zero_move="tackle"),
        move_pp_slots=slots,
        permission="permitted",
        targets=[{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}],
        turn_number=1,
    )
    assert result["status"] == "resolved", result
    sequence = result["shared_observation_sequence"]
    assert result["move_observation"]["observation_sequence"] == sequence
    assert result["switch_observation"]["observation_sequence"] == sequence
    assert result["move_observation"]["payload"]["move_pp_slots"] == slots
    state = manager.read_state()["state"]
    record = state["opponent_side"]["pokemon"][0]["current_opponent_response_set"]
    assert record["provenance"]["source_sequence"] == sequence
    snapshot, d0 = _d0(manager, "leppa-combined")
    pp = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
    )
    assert pp["status"] == "resolved"
    assert pp["response_observation_source_sequence"] == sequence


def test_strict_pp_authority_rejects_foreign_identity_and_marks_old_sequence_incomplete():
    manager = _manager()
    result = admit_current_opponent_response_set_observation(
        runtime_session_manager=manager,
        captured_session_id="leppa-pp",
        move_ids=MOVES,
        move_usability=_usability(),
        move_pp_slots=_pp([(1, 10), (2, 10), (3, 10), (4, 10)]),
        turn_number=1,
    )
    assert result["status"] == "resolved"
    snapshot, d0 = _d0(manager)
    stale_state = deepcopy(snapshot["state"])
    stale_state["last_applied_observation_sequence"] += 1
    stale_snapshot = {
        **snapshot,
        "state": stale_state,
        "state_fingerprint": state_fingerprint(stale_state),
    }
    stale_d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=stale_snapshot,
        decision_owner=d0["decision_owner"],
    )
    stale = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=stale_d0, runtime_snapshot=stale_snapshot,
    )
    assert stale["status"] == "incomplete"
    assert stale["reason"] == "current_opponent_response_set_not_fresh"

    foreign = deepcopy(snapshot)
    foreign["state"] = deepcopy(snapshot["state"])
    foreign["state"]["opponent_side"]["pokemon"][0]["pokemon_id"] = "foreign"
    foreign["state_fingerprint"] = state_fingerprint(foreign["state"])
    rejected = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=d0, runtime_snapshot=foreign,
    )
    assert rejected["status"] == "rejected"
