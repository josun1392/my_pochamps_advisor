"""Production reachability for explicit Sleep/Freeze progression observations."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLabel

import ui.main_window as main_window_module
from llm.advisor_champions_sleep_freeze_action_gate import freeze_champions_status_action_gate
from llm.advisor_champions_status_progression import valid_progression
from llm.advisor_current_condition_observation import admit_current_condition_observation
from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_status_progression_observation import admit_champions_status_progression_observation
from ui.main_window import MainWindow
from ui.widgets.current_condition_dialog import CurrentConditionDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel
from ui.widgets.status_progression_dialog import SleepFreezeProgressionDialog


SESSION = "sleep-freeze-progression-production"


def _manager(*, condition: str | None = "sleep", condition_turn: int = 1, session: str = SESSION):
    state = create_unknown_bootstrap_battle_state(session, "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    created = BattleObservationRuntimeSessionManager.create(session, state)
    assert created["status"] == "session_ready", created
    manager = created["manager"]
    if condition is not None:
        result = admit_current_condition_observation(
            runtime_session_manager=manager,
            captured_session_id=session,
            side="self",
            condition=condition,
            turn_number=condition_turn,
        )
        assert result["status"] == "resolved", result
    return manager


def _owner(manager, side="self"):
    state = manager.read_state()["state"]
    side_state = state[f"{side}_side"]
    slot = side_state["active_slot_index"]
    pokemon = side_state["pokemon"][slot]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}


def _pokemon(manager, side="self"):
    state = manager.read_state()["state"]
    side_state = state[f"{side}_side"]
    return side_state["pokemon"][side_state["active_slot_index"]]


def _admit(manager, *, side="self", established=1, attempts=0, duration=None, turn=1, session=SESSION):
    return admit_champions_status_progression_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        side=side,
        established_turn=established,
        prior_attempts=attempts,
        sleep_duration=duration,
        turn_number=turn,
    )


@pytest.mark.parametrize(
    "condition,duration",
    [
        ("sleep", 2),
        ("sleep", 3),
        ("sleep", None),
        ("freeze", None),
    ],
)
def test_explicit_sleep_freeze_progression_admission(condition, duration):
    manager = _manager(condition=condition)
    result = _admit(manager, duration=duration)

    assert result["status"] == "resolved", result
    assert result["runtime_committed"] is True
    row = _pokemon(manager)["champions_status_progression"]
    assert row["condition"] == condition
    assert row["prior_attempts"] == 0
    assert row["sleep_duration"] == duration
    assert valid_progression(row, _owner(manager))
    observation = result["observation"]
    assert observation["event_kind"] == "champions_status_progression_observed"
    assert observation["payload"]["sleep_duration"] == duration


def test_freeze_rejects_sleep_duration_without_mutation():
    manager = _manager(condition="freeze")
    before = deepcopy(manager.read_state())
    before_collection = deepcopy(manager.read_collection_snapshot())
    before_sequence = manager.last_allocated_sequence

    result = _admit(manager, duration=2)

    assert result["status"] == "rejected"
    assert result["reason"] == "freeze_sleep_duration_must_be_none"
    assert manager.read_state() == before
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence


def test_active_owner_and_origin_are_derived_from_runtime_condition_provenance():
    manager = _manager(condition="sleep")
    condition_provenance = deepcopy(_pokemon(manager)["condition_provenance"])

    result = _admit(manager, established=1, attempts=0, duration=3)

    assert result["status"] == "resolved", result
    assert result["owner"] == _owner(manager)
    expected_origin = f"{condition_provenance['source_observation_id']}:sleep-freeze-episode"
    assert result["origin_id"] == expected_origin
    assert result["observation"]["payload"]["origin_id"] == expected_origin
    assert set(result["observation"]["payload"]) == {"condition", "origin_id", "established_turn", "prior_attempts", "sleep_duration"}
    assert result["progression"]["condition_observation"] == condition_provenance


def test_missing_or_non_sleep_freeze_current_condition_fails_closed():
    missing = _manager(condition=None)
    before = deepcopy(missing.read_state())
    result = _admit(missing)
    assert result["status"] == "incomplete"
    assert missing.read_state() == before

    burn = _manager(condition="burn")
    before = deepcopy(burn.read_state())
    result = _admit(burn)
    assert result["status"] == "rejected"
    assert result["reason"] == "current_condition_not_sleep_or_freeze"
    assert burn.read_state() == before


def test_stale_session_and_invalid_side_fail_closed_without_sequence_allocation():
    manager = _manager(condition="sleep")
    before_sequence = manager.last_allocated_sequence
    before = deepcopy(manager.read_state())

    stale = _admit(manager, session="foreign-session")
    wrong_side = _admit(manager, side="third-side")

    assert stale["status"] == "rejected"
    assert wrong_side["status"] == "rejected"
    assert manager.last_allocated_sequence == before_sequence
    assert manager.read_state() == before


def test_exact_retry_is_idempotent_without_sequence_collection_or_fingerprint_change():
    manager = _manager(condition="sleep")
    first = _admit(manager, duration=3)
    assert first["status"] == "resolved", first
    before_sequence = manager.last_allocated_sequence
    before_collection = deepcopy(manager.read_collection_snapshot())
    before_snapshot = manager.capture_runtime_state_snapshot(SESSION)

    retry = _admit(manager, duration=3)

    assert retry["status"] == "resolved"
    assert retry["idempotent"] is True
    assert retry["runtime_committed"] is False
    assert manager.last_allocated_sequence == before_sequence
    assert manager.read_collection_snapshot() == before_collection
    after_snapshot = manager.capture_runtime_state_snapshot(SESSION)
    assert after_snapshot["state_fingerprint"] == before_snapshot["state_fingerprint"]


def test_monotonic_prior_attempt_update_and_decrease_rejection():
    manager = _manager(condition="sleep")
    first = _admit(manager, attempts=0, duration=None, turn=1)
    assert first["status"] == "resolved", first

    later = _admit(manager, attempts=1, duration=None, turn=2)
    assert later["status"] == "resolved", later
    assert _pokemon(manager)["champions_status_progression"]["prior_attempts"] == 1

    before = deepcopy(manager.read_state())
    before_sequence = manager.last_allocated_sequence
    stale = _admit(manager, attempts=0, duration=None, turn=3)
    assert stale["status"] == "rejected"
    assert stale["reason"] == "stale_champions_status_progression"
    assert manager.read_state() == before
    assert manager.last_allocated_sequence == before_sequence


def test_known_sleep_duration_cannot_be_rerolled_but_unknown_can_become_known():
    manager = _manager(condition="sleep")
    assert _admit(manager, duration=None)["status"] == "resolved"
    learned = _admit(manager, duration=2, turn=2)
    assert learned["status"] == "resolved", learned
    assert _pokemon(manager)["champions_status_progression"]["sleep_duration"] == 2

    before = deepcopy(manager.read_state())
    before_sequence = manager.last_allocated_sequence
    reroll = _admit(manager, duration=3, turn=3)
    assert reroll["status"] == "rejected"
    assert reroll["reason"] == "champions_sleep_duration_reroll_rejected"
    assert manager.read_state() == before
    assert manager.last_allocated_sequence == before_sequence


def test_changed_condition_episode_uses_new_origin_and_does_not_reuse_old_progression():
    manager = _manager(condition="sleep")
    first = _admit(manager, established=1, duration=3)
    assert first["status"] == "resolved"
    old_origin = first["origin_id"]
    old_condition_observation = deepcopy(first["progression"]["condition_observation"])

    condition = admit_current_condition_observation(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        side="self",
        condition="sleep",
        turn_number=2,
    )
    assert condition["status"] == "resolved"
    new_provenance = deepcopy(_pokemon(manager)["condition_provenance"])
    assert new_provenance != old_condition_observation

    second = _admit(manager, established=2, duration=None, turn=2)
    assert second["status"] == "resolved", second
    assert second["origin_id"] != old_origin
    assert second["progression"]["condition_observation"] == new_provenance
    assert _pokemon(manager)["champions_status_progression"]["origin_id"] == second["origin_id"]


def test_fresh_committed_d0_is_consumed_by_existing_sleep_gate():
    manager = _manager(condition="sleep")
    for side in ("self", "opponent"):
        ability = admit_current_state_observation(
            runtime_session_manager=manager,
            captured_session_id=SESSION,
            event_kind="current_ability_observed",
            payload={"ability": "pressure"},
            side=side,
            turn_number=1,
        )
        assert ability["status"] == "resolved", ability

    result = _admit(manager, established=1, attempts=0, duration=3, turn=1)
    assert result["status"] == "resolved", result
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    actor = result["owner"]
    gate = freeze_champions_status_action_gate(
        strategy_d0=result["strategy_d0"],
        runtime_snapshot=result["runtime_snapshot"],
        actor=actor,
        action_id="action:sleep:1",
        move_id="tackle",
        action_order={},
    )
    assert gate["status"] == "resolved", gate
    assert gate["progression"]["origin_id"] == result["origin_id"]


class _FakePanel:
    def __init__(self):
        self.status_progression_count = None
        self.clear_readiness_calls = 0
        self.structured_request_button = SimpleNamespace(setDisabled=lambda _value: None)

    def set_status_progression_count(self, count):
        self.status_progression_count = count

    def clear_recommendation_readiness(self):
        self.clear_readiness_calls += 1

    def set_running(self, _value):
        pass


class _Status:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class _FakeProgressionDialog:
    def __init__(self, *, result, confirmation, **_kwargs):
        self._result = result
        self.progression_confirmation = deepcopy(confirmation)

    def exec(self):
        return self._result


def _ui_window(manager):
    window = MainWindow.__new__(MainWindow)
    window._observation_runtime_session_manager = manager
    window._current_trusted_turn_number = 1
    window._status_progression_confirmations = {}
    window._current_condition_confirmations = {}
    window._recommendation_readiness_owner = (manager.session_id, 0, "self-a")
    window._active_advice_owner = "structured"
    window._active_advice_request_token = 1
    window._active_advice_terminal_token = 1
    panel = _FakePanel()
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    status = _Status()
    window.statusBar = lambda: status
    return window, panel, status


def test_open_cancel_ui_is_not_observation_and_origin_is_not_exposed(monkeypatch):
    manager = _manager(condition="sleep")
    window, panel, _status = _ui_window(manager)
    before = (deepcopy(manager.read_state()), deepcopy(manager.read_collection_snapshot()), manager.last_allocated_sequence)

    monkeypatch.setattr(
        main_window_module,
        "SleepFreezeProgressionDialog",
        lambda **kwargs: _FakeProgressionDialog(
            result=QDialog.DialogCode.Rejected,
            confirmation={"side": "self", "established_turn": 1, "prior_attempts": 0, "sleep_duration": 3},
            **kwargs,
        ),
    )
    MainWindow._open_status_progression_dialog(window)

    assert (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence) == before
    assert window._status_progression_confirmations == {}
    assert panel.clear_readiness_calls == 0

    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = SleepFreezeProgressionDialog(current_conditions={"self": "sleep", "opponent": "unknown"})
    assert not hasattr(dialog, "origin_id")
    assert "origin" not in dialog._summary().lower()


def test_ui_apply_commits_only_on_confirmation_and_does_not_execute_pending_action(monkeypatch):
    manager = _manager(condition="sleep")
    window, panel, _status = _ui_window(manager)
    monkeypatch.setattr(
        main_window_module,
        "SleepFreezeProgressionDialog",
        lambda **kwargs: _FakeProgressionDialog(
            result=QDialog.DialogCode.Accepted,
            confirmation={"side": "self", "established_turn": 1, "prior_attempts": 0, "sleep_duration": None},
            **kwargs,
        ),
    )

    MainWindow._open_status_progression_dialog(window)

    assert window._status_progression_confirmations == {
        "self": {"established_turn": 1, "prior_attempts": 0, "sleep_duration": None}
    }
    assert panel.status_progression_count == 1
    assert panel.clear_readiness_calls == 1
    kinds = [row["event_kind"] for row in manager.read_collection_snapshot()["ordered_observations"]]
    assert "champions_status_progression_observed" in kinds
    assert "pending_status_action_execution_observed" not in kinds


def test_new_battle_clears_ui_local_progression_state():
    manager = _manager(condition="sleep", session="ui-session-0")
    window, panel, _status = _ui_window(manager)
    window._battle_session_sequence = 0
    window._status_progression_confirmations = {
        "self": {"established_turn": 1, "prior_attempts": 0, "sleep_duration": 3}
    }
    window.selected_slots = {"team_my": 0, "team_enemy": 0}
    self_panel = SimpleNamespace(pokemon_view=SimpleNamespace(en="self-a"))
    opponent_panel = SimpleNamespace(pokemon_view=SimpleNamespace(en="opponent-a"))
    window._panels = {
        ("team_my", 0): self_panel,
        ("team_enemy", 0): opponent_panel,
    }
    window.my_team_column = SimpleNamespace(panels=[self_panel])
    window.opponent_team_column = SimpleNamespace(panels=[opponent_panel])
    window._current_ability_confirmations = {}
    window._current_persistent_effect_confirmations = {}
    window._structured_ability_confirmations = {}
    window._current_type_confirmations = {}
    window._structured_type_confirmations = {}
    window._current_stat_stage_confirmations = {}
    window._current_final_stat_confirmations = {}
    window._structured_final_stat_confirmations = {}
    window._current_hp_confirmations = {}
    window._current_hp_confirmation_owners = {}
    window._current_observed_damage_confirmation = None
    window._structured_observed_damage_confirmations = []
    window._contact_result_action_ids = {}
    window._item_event_confirmations = []
    window._current_field_state_confirmation = None
    window._grounded_context_confirmation = {"self": {"status": "unknown"}, "opponent": {"status": "unknown"}}
    window._battle_counter_confirmation = None
    window._consecutive_use_confirmation = None
    window._slot_panel = lambda column, slot: window._panels[(column, slot)]
    window._loaded_roster_identities = MainWindow._loaded_roster_identities.__get__(window, MainWindow)
    window._retire_advice_presentation_authority = MainWindow._retire_advice_presentation_authority.__get__(window, MainWindow)
    window._reset_battle_presentation = MainWindow._reset_battle_presentation.__get__(window, MainWindow)
    window._update_current_persistent_effect_summary = lambda: None
    window._update_status_progression_summary = MainWindow._update_status_progression_summary.__get__(window, MainWindow)

    new_session = MainWindow._begin_new_battle_session(window)

    assert new_session == "ui-session-1"
    assert window._status_progression_confirmations == {}
    assert panel.status_progression_count == 0


def test_existing_current_condition_dialog_contract_remains_progression_free():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = CurrentConditionDialog(current_conditions={})
    assert not hasattr(dialog, "established_turn_spin")
    assert not hasattr(dialog, "prior_attempts_spin")
    assert not hasattr(dialog, "sleep_duration_combo")
    labels = [label.text().lower() for label in dialog.findChildren(QLabel)]
    assert any("does not record application events" in text for text in labels)
