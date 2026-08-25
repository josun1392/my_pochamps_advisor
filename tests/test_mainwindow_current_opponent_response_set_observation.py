from llm.advisor_current_opponent_response_set_observation import admit_current_opponent_response_set_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


MOVES = ["tackle", "scratch", "growl", "tail-whip"]


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    created = BattleObservationRuntimeSessionManager.create("s", state)
    assert created["status"] == "session_ready"
    return created["manager"]


def _usability(**overrides):
    return {move: {"status": overrides.get(move, "usable")} for move in MOVES}


def test_explicit_current_confirmation_reaches_existing_reducer_response_authority():
    manager = _manager()
    result = admit_current_opponent_response_set_observation(runtime_session_manager=manager, captured_session_id="s", move_ids=MOVES, move_usability=_usability(scratch="unusable"), turn_number=1)
    assert result["status"] == "resolved"
    state = manager.read_state()["state"]
    opponent = state["opponent_side"]["pokemon"][0]
    assert opponent["current_opponent_response_set"]["moveset_completeness"] == "complete"
    assert opponent["current_move_usability"]["scratch"]["status"] == "known_unusable"
    assert opponent["known_move_ids"] == MOVES


def test_unknown_or_missing_explicit_confirmation_does_not_create_response_authority():
    manager = _manager()
    result = admit_current_opponent_response_set_observation(runtime_session_manager=manager, captured_session_id="s", move_ids=MOVES, move_usability=_usability(scratch="unknown"), turn_number=1)
    assert result == {"status": "incomplete", "reason": "unknown_move_usability", "observation": None, "runtime_fingerprint": None, "active_opponent": None}
    opponent = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    assert "current_opponent_response_set" not in opponent


def test_stale_session_rejects_without_transferring_confirmation():
    manager = _manager()
    result = admit_current_opponent_response_set_observation(runtime_session_manager=manager, captured_session_id="other", move_ids=MOVES, move_usability=_usability(), turn_number=1)
    assert result["status"] == "rejected"
    assert "current_opponent_response_set" not in manager.read_state()["state"]["opponent_side"]["pokemon"][0]
