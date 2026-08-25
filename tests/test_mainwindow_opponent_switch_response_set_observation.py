from copy import deepcopy
from inspect import getsource

from llm.advisor_current_opponent_switch_response_set_observation import admit_current_opponent_switch_response_set_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_d0_opponent_switch_response_authority import freeze_runtime_d0_opponent_switch_response_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
from ui.main_window import MainWindow


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "self", "opponent")["state"]
    bench = deepcopy(state["opponent_side"]["pokemon"][0])
    bench["pokemon_id"] = "bench"
    state["opponent_side"]["pokemon"][1] = bench
    created = BattleObservationRuntimeSessionManager.create("s", state)
    assert created["status"] == "session_ready"
    return created["manager"]


def _authority(manager):
    state = manager.read_state()["state"]
    snapshot = {"status": "runtime_snapshot_ready", "session_id": "s", "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "self"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    return freeze_runtime_d0_opponent_switch_response_authority(strategy_d0=d0, runtime_snapshot=snapshot)


def _targets(availability="alive"):
    return [{"slot_index": 1, "pokemon_id": "bench", "availability": availability}]


def test_explicit_complete_confirmation_reaches_live_switch_response_authority():
    manager = _manager()
    result = admit_current_opponent_switch_response_set_observation(runtime_session_manager=manager, captured_session_id="s", permission="permitted", targets=_targets(), turn_number=1)

    assert result["status"] == "resolved"
    authority = _authority(manager)
    assert authority["status"] == "resolved"
    assert authority["selectable_response_action_ids"] == ("opponent_switch:s:1:bench",)


def test_blocked_and_unknown_confirmation_keep_their_explicit_safe_semantics():
    blocked = _manager()
    assert admit_current_opponent_switch_response_set_observation(runtime_session_manager=blocked, captured_session_id="s", permission="blocked", targets=_targets(), turn_number=1)["status"] == "resolved"
    assert _authority(blocked)["selectable_response_action_ids"] == ()

    unknown = _manager()
    assert admit_current_opponent_switch_response_set_observation(runtime_session_manager=unknown, captured_session_id="s", permission="unknown", targets=_targets("unknown"), turn_number=1)["status"] == "resolved"
    assert _authority(unknown)["status"] == "incomplete"


def test_missing_target_or_stale_session_never_creates_switch_authority():
    manager = _manager()
    missing = admit_current_opponent_switch_response_set_observation(runtime_session_manager=manager, captured_session_id="s", permission="permitted", targets=[], turn_number=1)
    assert missing["status"] == "incomplete"
    assert _authority(manager)["status"] == "incomplete"

    stale = admit_current_opponent_switch_response_set_observation(runtime_session_manager=manager, captured_session_id="other", permission="permitted", targets=_targets(), turn_number=1)
    assert stale["status"] == "rejected"


def test_window_wiring_uses_explicit_reducer_known_targets_not_panel_inference():
    source = getsource(MainWindow._open_current_opponent_switch_response_set_confirmation)
    assert "admit_current_opponent_switch_response_set_observation" in source
    assert "capture_runtime_state_snapshot" in source
    assert "_slot_panel" not in source
