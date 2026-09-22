"""Production UI wiring for explicitly observed Sleep/Freeze pending-action results."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_champions_sleep_freeze_action_gate import SELF_THAW_MOVES, SLEEP_EXCEPTIONS
from llm.advisor_current_condition_observation import admit_current_condition_observation
from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_status_progression_observation import admit_champions_status_progression_observation
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel
from ui.widgets.pending_status_action_result_dialog import SleepFreezeActionResultDialog
from ui.widgets.status_progression_dialog import SleepFreezeProgressionDialog


SESSION = "pending-status-ui"


def _manager(
    *,
    condition: str = "sleep",
    side: str = "self",
    progression: bool = True,
    prior: int = 0,
    duration: int | None = None,
    session: str = SESSION,
):
    state = create_unknown_bootstrap_battle_state(session, "self-a", "opponent-a")["state"]
    for name in ("self", "opponent"):
        state[f"{name}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    created = BattleObservationRuntimeSessionManager.create(session, state)
    assert created["status"] == "session_ready"
    manager = created["manager"]
    condition_result = admit_current_condition_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        side=side,
        condition=condition,
        turn_number=1,
    )
    assert condition_result["status"] == "resolved", condition_result
    if progression:
        progression_result = admit_champions_status_progression_observation(
            runtime_session_manager=manager,
            captured_session_id=session,
            side=side,
            established_turn=1,
            prior_attempts=prior,
            sleep_duration=duration,
            turn_number=1,
        )
        assert progression_result["status"] == "resolved", progression_result
    return manager


def _pokemon(manager, side="self"):
    state = manager.read_state()["state"]
    side_state = state[f"{side}_side"]
    return side_state["pokemon"][side_state["active_slot_index"]]


class _Panel:
    def __init__(self):
        self.clear_readiness_calls = 0
        self.progression_count = None
        self.condition_count = None

    def clear_recommendation_readiness(self):
        self.clear_readiness_calls += 1

    def set_status_progression_count(self, value):
        self.progression_count = value

    def set_current_condition_count(self, value):
        self.condition_count = value


class _Status:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


def _window(manager, *, side="self", turn=2):
    window = MainWindow.__new__(MainWindow)
    window._observation_runtime_session_manager = manager
    window._current_trusted_turn_number = turn
    window._status_progression_confirmations = {
        side: {"established_turn": 1, "prior_attempts": _pokemon(manager, side).get("champions_status_progression", {}).get("prior_attempts", 0), "sleep_duration": _pokemon(manager, side).get("champions_status_progression", {}).get("sleep_duration")}
    } if isinstance(_pokemon(manager, side).get("champions_status_progression"), dict) else {}
    window._current_condition_confirmations = {side: {"condition_type": _pokemon(manager, side).get("condition")}}
    window._recommendation_readiness_owner = (manager.session_id, 0, _pokemon(manager, side)["pokemon_id"])
    window._active_advice_owner = "structured"
    window._active_advice_request_token = 7
    window._active_advice_terminal_token = 7
    panel = _Panel()
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    status = _Status()
    window.statusBar = lambda: status
    return window, panel, status


def _set_exact_abilities(manager, *, turn=1):
    for side in ("self", "opponent"):
        result = admit_current_state_observation(
            runtime_session_manager=manager,
            captured_session_id=manager.session_id,
            event_kind="current_ability_observed",
            payload={"ability": "pressure"},
            side=side,
            turn_number=turn,
        )
        assert result["status"] == "resolved", result


def _submit(window, *, side="self", move="tackle", result="remained_asleep", session=None):
    return MainWindow._submit_pending_status_action_result(
        window,
        {"side": side, "move_id": move, "result": result},
        captured_session_id=session or window._observation_runtime_session_manager.session_id,
    )


@pytest.mark.parametrize(
    "condition,result_code,move,outcome,condition_after,attempt_after,derived_kind",
    [
        ("sleep", "remained_asleep", "tackle", "blocked_sleep", "sleep", 1, "champions_status_progression_derived"),
        ("freeze", "remained_frozen", "tackle", "blocked_freeze", "freeze", 1, "champions_status_progression_derived"),
        ("sleep", "woke_and_executed", "tackle", "wake_and_execute", None, None, "champions_status_condition_cleared_derived"),
        ("freeze", "natural_thaw", "tackle", "natural_thaw_and_execute", None, None, "champions_status_condition_cleared_derived"),
        ("sleep", "executed_while_asleep", sorted(SLEEP_EXCEPTIONS)[0], "sleep_exception_execute", "sleep", 0, None),
        ("freeze", "self_thaw_move", sorted(SELF_THAW_MOVES)[0], "self_thaw_move_execute", None, None, "champions_status_condition_cleared_derived"),
    ],
)
def test_all_six_actual_result_paths_reach_canonical_owner(
    condition, result_code, move, outcome, condition_after, attempt_after, derived_kind
):
    manager = _manager(condition=condition, duration=3 if condition == "sleep" else None)
    window, panel, _status = _window(manager)

    result = _submit(window, move=move, result=result_code)

    assert result["status"] == "resolved", result
    assert result["runtime_committed"] is True
    assert result["observation"]["payload"]["outcome_class"] == outcome
    pokemon = _pokemon(manager)
    assert pokemon.get("condition") == condition_after
    if attempt_after is None:
        assert pokemon.get("champions_status_progression") is None
    else:
        assert pokemon["champions_status_progression"]["prior_attempts"] == attempt_after
    if derived_kind is None:
        assert result["derived_observations"] == []
    else:
        assert [row["event_kind"] for row in result["derived_observations"]] == [derived_kind]
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    assert panel.clear_readiness_calls == 1


@pytest.mark.parametrize(
    "condition,result_code,expected_mass",
    [
        ("sleep", "remained_asleep", (1, 1)),
        ("freeze", "remained_frozen", (3, 4)),
    ],
)
def test_ui_retains_exact_pre_observation_gate_and_reconciles_after_runtime_commit(
    condition, result_code, expected_mass
):
    manager = _manager(condition=condition, duration=None)
    _set_exact_abilities(manager)
    window, _panel, _status = _window(manager)
    before = manager.capture_runtime_state_snapshot(manager.session_id)
    before_state = deepcopy(manager.read_state())

    result = _submit(window, result=result_code)

    assert result["status"] == "resolved", result
    assert result["runtime_committed"] is True
    reconciliation = result["rng_reconciliation"]
    assert reconciliation["status"] == "resolved"
    assert reconciliation["source_prediction_kind"] == "sleep_freeze_action_gate"
    assert reconciliation["probability_normalization"] == "none_preserve_original_mass"
    assert reconciliation["compatible_original_probability_mass"] == {
        "numerator": expected_mass[0], "denominator": expected_mass[1],
    }
    if condition == "sleep":
        assert reconciliation["match_outcome"] == "multiple_compatible_branches"
        assert "sleep_duration" in reconciliation["unresolved_hidden_dimensions"]
    retained = next(iter(window._historical_sleep_freeze_action_gates.values()))
    assert retained["source_runtime_fingerprint"] == before["state_fingerprint"]
    assert retained["predictive_gate"]["source_runtime_fingerprint"] == before["state_fingerprint"]
    assert result["runtime_snapshot"]["state_fingerprint"] != before["state_fingerprint"]
    assert manager.read_state() != before_state
    assert reconciliation["source_observations"][0]["event_kind"] == "pending_status_action_execution_observed"
    assert len(reconciliation["source_observations"]) == 1
    assert result["derived_observations"]
    assert all(row["event_kind"] != "pending_status_action_execution_observed" for row in result["derived_observations"])


def test_turn_change_retires_historical_sleep_freeze_gate_storage():
    manager = _manager(condition="freeze")
    window, _panel, _status = _window(manager)
    window._historical_sleep_freeze_action_gates = {("old",): {"status": "resolved"}}

    MainWindow.set_current_turn_number(window, 3)

    assert window._historical_sleep_freeze_action_gates == {}


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_actor_side_is_resolved_from_canonical_runtime(side):
    manager = _manager(condition="sleep", side=side, duration=3)
    window, _panel, _status = _window(manager, side=side)

    result = _submit(window, side=side)

    assert result["status"] == "resolved", result
    assert result["observation"]["side"] == side
    assert result["observation"]["pokemon_id"] == _pokemon(manager, side)["pokemon_id"]


def test_condition_comes_from_runtime_not_ui_result_choice():
    manager = _manager(condition="sleep", duration=3)
    window, _panel, _status = _window(manager)
    before = deepcopy(manager.read_state())

    result = _submit(window, result="remained_frozen")

    assert result["status"] == "rejected"
    assert result["reason"] == "observed_result_not_valid_for_current_condition"
    assert manager.read_state() == before


@pytest.mark.parametrize(
    "condition,result_code,move",
    [
        ("sleep", "executed_while_asleep", "tackle"),
        ("freeze", "self_thaw_move", "tackle"),
    ],
)
def test_invalid_move_specific_claims_are_rejected_by_canonical_catalog(condition, result_code, move):
    manager = _manager(condition=condition, duration=3 if condition == "sleep" else None)
    window, panel, _status = _window(manager)
    before = deepcopy(manager.read_state())

    result = _submit(window, result=result_code, move=move)

    assert result["status"] == "rejected"
    assert manager.read_state() == before
    assert panel.clear_readiness_calls == 0


def test_missing_progression_is_incomplete_without_runtime_or_readiness_mutation():
    manager = _manager(condition="sleep", progression=False)
    window, panel, status = _window(manager)
    before_state = deepcopy(manager.read_state())
    before_collection = deepcopy(manager.read_collection_snapshot())

    result = _submit(window)

    assert result["status"] == "incomplete"
    assert result["reason"] == "champions_status_progression_unavailable"
    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection
    assert panel.clear_readiness_calls == 0
    assert "progression" in status.messages[-1].lower()


def test_changed_condition_episode_makes_old_progression_fail_closed():
    manager = _manager(condition="sleep", duration=3)
    changed = admit_current_condition_observation(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        side="self",
        condition="sleep",
        turn_number=2,
    )
    assert changed["status"] == "resolved"
    window, panel, _status = _window(manager, turn=3)
    before = deepcopy(manager.read_state())

    result = _submit(window)

    assert result["status"] == "rejected"
    assert result["reason"] == "champions_status_progression_foreign_or_stale"
    assert manager.read_state() == before
    assert panel.clear_readiness_calls == 0


def test_open_and_cancel_are_not_observations(monkeypatch):
    manager = _manager(condition="sleep", duration=3)
    window, panel, _status = _window(manager)
    before_state = deepcopy(manager.read_state())
    before_collection = deepcopy(manager.read_collection_snapshot())
    before_sequence = manager.last_allocated_sequence

    class CancelDialog:
        confirmation = {"side": "self", "move_id": "tackle", "result": "remained_asleep"}
        def __init__(self, **_kwargs): pass
        def exec(self): return QDialog.DialogCode.Rejected

    monkeypatch.setattr(main_window_module, "SleepFreezeActionResultDialog", CancelDialog)
    MainWindow._open_pending_status_action_result_dialog(window)

    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence
    assert panel.clear_readiness_calls == 0


def test_dialog_exposes_only_human_inputs_and_no_internal_identity_fields():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = SleepFreezeActionResultDialog(current_conditions={"self": "sleep", "opponent": "freeze"})

    assert not hasattr(dialog, "action_id")
    assert not hasattr(dialog, "decision_point")
    assert not hasattr(dialog, "execution_state")
    assert not hasattr(dialog, "blocker")
    assert not hasattr(dialog, "outcome_class")
    dialog.move_id_edit.setText("tackle")
    dialog._save_and_accept()
    assert set(dialog.confirmation) == {"side", "move_id", "result"}


def test_exact_blocked_retry_reuses_identity_without_duplicate_or_second_increment():
    manager = _manager(condition="sleep", duration=3)
    window, panel, _status = _window(manager)
    first = _submit(window)
    assert first["status"] == "resolved"
    context = deepcopy(manager.read_state()["state"]["pending_status_action_execution_context"])
    sequence = manager.last_allocated_sequence
    collection = deepcopy(manager.read_collection_snapshot())

    retry = _submit(window)

    assert retry["status"] == "resolved"
    assert retry["reason"] == "duplicate_pending_status_action"
    assert retry["runtime_committed"] is False
    assert manager.last_allocated_sequence == sequence
    assert manager.read_collection_snapshot() == collection
    assert _pokemon(manager)["champions_status_progression"]["prior_attempts"] == 1
    after_context = manager.read_state()["state"]["pending_status_action_execution_context"]
    assert after_context["action_id"] == context["action_id"]
    assert after_context["decision_point"] == context["decision_point"]
    assert panel.clear_readiness_calls == 1


@pytest.mark.parametrize(
    "condition,result_code",
    [("sleep", "woke_and_executed"), ("freeze", "natural_thaw")],
)
def test_exact_clear_retry_reaches_duplicate_after_condition_is_cleared(condition, result_code):
    manager = _manager(condition=condition, duration=3 if condition == "sleep" else None)
    window, _panel, _status = _window(manager)
    first = _submit(window, result=result_code)
    assert first["status"] == "resolved"
    sequence = manager.last_allocated_sequence
    collection = deepcopy(manager.read_collection_snapshot())

    retry = _submit(window, result=result_code)

    assert retry["status"] == "resolved"
    assert retry["reason"] == "duplicate_pending_status_action"
    assert manager.last_allocated_sequence == sequence
    assert manager.read_collection_snapshot() == collection


def test_same_action_conflicting_result_rejects_without_new_sequence_or_observation():
    manager = _manager(condition="sleep", duration=3)
    window, _panel, _status = _window(manager)
    first = _submit(window)
    assert first["status"] == "resolved"
    sequence = manager.last_allocated_sequence
    collection = deepcopy(manager.read_collection_snapshot())
    state = deepcopy(manager.read_state())

    conflict = _submit(window, result="woke_and_executed")

    assert conflict["status"] == "rejected"
    assert conflict["reason"] == "conflicting_pending_status_action_retry"
    assert manager.last_allocated_sequence == sequence
    assert manager.read_collection_snapshot() == collection
    assert manager.read_state() == state


def test_unrelated_later_observation_makes_exact_retry_stale():
    manager = _manager(condition="sleep", duration=3)
    window, panel, _status = _window(manager)
    assert _submit(window)["status"] == "resolved"
    ability = admit_current_state_observation(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        event_kind="current_ability_observed",
        payload={"ability": "pressure"},
        side="self",
        turn_number=3,
    )
    assert ability["status"] == "resolved"
    before = deepcopy(manager.read_state())

    retry = _submit(window)

    assert retry["status"] == "rejected"
    assert retry["reason"] == "stale_pending_status_action_duplicate"
    assert manager.read_state() == before
    assert panel.clear_readiness_calls == 1


def test_sleep_exception_preserves_progression_exactly():
    move = sorted(SLEEP_EXCEPTIONS)[0]
    manager = _manager(condition="sleep", prior=1, duration=3)
    before = deepcopy(_pokemon(manager)["champions_status_progression"])
    window, _panel, _status = _window(manager)

    result = _submit(window, move=move, result="executed_while_asleep")

    assert result["status"] == "resolved"
    assert _pokemon(manager)["condition"] == "sleep"
    assert _pokemon(manager)["champions_status_progression"] == before


def test_failed_confirmation_does_not_retire_recommendation_but_success_does():
    failed_manager = _manager(condition="sleep", progression=False)
    failed_window, failed_panel, _ = _window(failed_manager)
    owner_before = failed_window._recommendation_readiness_owner
    assert _submit(failed_window)["status"] == "incomplete"
    assert failed_window._recommendation_readiness_owner == owner_before
    assert failed_panel.clear_readiness_calls == 0

    manager = _manager(condition="sleep", duration=3)
    window, panel, _ = _window(manager)
    assert _submit(window)["status"] == "resolved"
    assert window._recommendation_readiness_owner is None
    assert window._active_advice_owner is None
    assert panel.clear_readiness_calls == 1


def test_deterministic_identity_is_session_bound_and_requires_no_ui_cache():
    first = _manager(condition="sleep", duration=3, session="pending-ui-a")
    first_window, _, _ = _window(first)
    first_window._current_trusted_turn_number = 2
    first_snapshot = first.capture_runtime_state_snapshot("pending-ui-a")
    first_actor = MainWindow._resolve_pending_status_actor(first_window, first_snapshot, session_id="pending-ui-a", side="self")
    first_identity = MainWindow._resolve_pending_status_action_identity(
        first_window,
        captured_session_id="pending-ui-a",
        owner=first_actor["owner"],
        move_id="tackle",
        turn_number=2,
        runtime_snapshot=first_snapshot,
    )

    second = _manager(condition="sleep", duration=3, session="pending-ui-b")
    second_window, _, _ = _window(second)
    second_window._current_trusted_turn_number = 2
    second_snapshot = second.capture_runtime_state_snapshot("pending-ui-b")
    second_actor = MainWindow._resolve_pending_status_actor(second_window, second_snapshot, session_id="pending-ui-b", side="self")
    second_identity = MainWindow._resolve_pending_status_action_identity(
        second_window,
        captured_session_id="pending-ui-b",
        owner=second_actor["owner"],
        move_id="tackle",
        turn_number=2,
        runtime_snapshot=second_snapshot,
    )

    assert first_identity["status"] == second_identity["status"] == "resolved"
    assert first_identity["action_id"] != second_identity["action_id"]
    assert first_identity["decision_point"] != second_identity["decision_point"]
    assert not hasattr(first_window, "_pending_status_action_ids")


def test_progression_ui_remains_separate_and_unchanged():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = SleepFreezeProgressionDialog(current_conditions={"self": "sleep"})
    assert hasattr(dialog, "established_turn_spin")
    assert hasattr(dialog, "prior_attempts_spin")
    assert hasattr(dialog, "sleep_duration_combo")
    assert not hasattr(dialog, "move_id_edit")
    assert not hasattr(dialog, "result_combo")


def test_only_explicit_action_result_button_emits_action_result_request():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    requests = []
    panel.pending_status_action_result_requested.connect(lambda: requests.append("pending"))

    panel.status_progression_button.click()
    panel.current_condition_button.click()
    assert requests == []

    panel.pending_status_action_result_button.click()
    assert requests == ["pending"]
