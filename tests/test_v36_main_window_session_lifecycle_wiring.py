from copy import deepcopy
from types import SimpleNamespace
import ast
import inspect

import pytest

import ui.main_window as main_window_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from ui.main_window import MainWindow


class _Button:
    def __init__(self): self.disabled = []
    def setDisabled(self, value): self.disabled.append(value)


class _Panel:
    def __init__(self):
        self.events = []; self.structured_request_button = _Button()
    def set_running(self, value): self.events.append(("running", value))
    def set_mode_advice_text(self, mode, text): self.events.append(("text", mode, text))
    def set_error(self, message): self.events.append(("error", message))


class _Status:
    def __init__(self): self.messages = []
    def showMessage(self, message): self.messages.append(message)


class _Thread:
    def __init__(self): self.deleted = 0
    def deleteLater(self): self.deleted += 1


class _Harness:
    _active_session_id = MainWindow._active_session_id
    _selected_identity = MainWindow._selected_identity
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    begin_new_battle = MainWindow.begin_new_battle
    _retire_advice_presentation_authority = MainWindow._retire_advice_presentation_authority
    _reset_battle_presentation = MainWindow._reset_battle_presentation
    _capture_structured_observed_damage_confirmation = MainWindow._capture_structured_observed_damage_confirmation
    _trusted_turn_context_snapshot = MainWindow._trusted_turn_context_snapshot
    _begin_advice_request = MainWindow._begin_advice_request
    _is_current_advice_request = MainWindow._is_current_advice_request
    _claim_current_advice_terminal = MainWindow._claim_current_advice_terminal
    _clear_current_advice_request = MainWindow._clear_current_advice_request
    _is_current_structured_session = MainWindow._is_current_structured_session
    _on_structured_recommendation_finished = MainWindow._on_structured_recommendation_finished
    _on_structured_recommendation_failed = MainWindow._on_structured_recommendation_failed
    _cleanup_structured_worker = MainWindow._cleanup_structured_worker
    _delete_advice_thread_once = staticmethod(MainWindow._delete_advice_thread_once)

    def __init__(self, active=True, identities=True):
        self._battle_session_sequence = 0
        self._observation_runtime_session_manager = None
        self.selected_slots = {"team_my": 0, "team_enemy": 0}
        my = "pikachu" if identities else None; opponent = "eevee" if identities else None
        self._panels = {
            ("team_my", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en=my)),
            ("team_enemy", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en=opponent)),
        }
        if active:
            initial = create_unknown_bootstrap_battle_state("ui-session-0", "pikachu", "eevee")["state"]
            self._observation_runtime_session_manager = BattleObservationRuntimeSessionManager.create("ui-session-0", initial)["manager"]
        self._current_trusted_turn_number = None
        self._advice_request_sequence = 0
        self._active_advice_owner = self._active_advice_request_token = self._active_advice_terminal_token = None
        self._is_closing = False
        self._structured_thread = self._structured_worker = None
        self._current_condition_confirmations = {"old": 1}; self._current_ability_confirmations = {"old": 1}
        self._structured_ability_confirmations = {}; self._current_stat_stage_confirmations = {}
        self._current_final_stat_confirmations = {}; self._structured_final_stat_confirmations = {}
        self._current_hp_confirmations = {}; self._current_observed_damage_confirmation = {"old": 1}
        self._structured_observed_damage_confirmations = []; self._item_event_confirmations = [{"old": 1}]
        self._current_field_state_confirmation = {"old": 1}; self._battle_counter_confirmation = {"old": 1}; self._consecutive_use_confirmation = {"old": 1}
        self.panel, self.status = _Panel(), _Status()
        self.center_column = SimpleNamespace(llm_advice_panel=self.panel)

    def _slot_panel(self, column, slot): return self._panels[(column, slot)]
    def statusBar(self): return self.status


def _result():
    return {"presentation_model": {"status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}}


def _core_values(window):
    manager = window._observation_runtime_session_manager
    read = manager.read_state()
    return manager.session_id, manager.read_collection_snapshot(), read["state"], read["state_fingerprint"], read["state"]["last_applied_observation_sequence"], manager.last_allocated_sequence, manager.read_applied_ledger()


def test_main_window_uses_session_manager_as_single_session_authority():
    window = _Harness()
    assert window._active_session_id() == "ui-session-0"
    assert not hasattr(window, "_current_battle_session_id") and not hasattr(window, "_current_state_session_id")


def test_main_window_has_no_independent_mutable_observation_sequence():
    window = _Harness()
    assert not hasattr(window, "_observation_sequence") and window._observation_runtime_session_manager.last_allocated_sequence == 0


def test_main_window_does_not_own_raw_observation_collection():
    assert not hasattr(_Harness(), "_observation_collection")


def test_main_window_session_reads_are_derived_from_manager():
    window = _Harness(); manager = window._observation_runtime_session_manager
    assert window._active_session_id() == manager.session_id


def test_main_window_creates_session_only_from_explicit_selected_identities():
    window = _Harness(active=False)
    assert window.begin_new_battle() == "ui-session-1"
    state = window._observation_runtime_session_manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["pokemon_id"] == "pikachu"
    assert state["opponent_side"]["pokemon"][0]["pokemon_id"] == "eevee"


def test_main_window_does_not_fabricate_identity_before_valid_selection():
    window = _Harness(active=False, identities=False); before = deepcopy(window._item_event_confirmations)
    assert window.begin_new_battle() is None
    assert window._observation_runtime_session_manager is None and window._item_event_confirmations == before


def test_main_window_bootstrap_preserves_unknown_battle_facts():
    window = _Harness(active=False); window.begin_new_battle()
    pokemon = window._observation_runtime_session_manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert pokemon["current_hp"] == {"knowledge": "unknown"} and pokemon["fainted"] == {"knowledge": "unknown"}


def test_invalid_bootstrap_does_not_publish_partial_session_or_reset_ui():
    window = _Harness(active=True, identities=False); before = _core_values(window); ui_before = deepcopy(window._item_event_confirmations)
    assert window.begin_new_battle() is None
    assert _core_values(window) == before and window._item_event_confirmations == ui_before


def test_begin_new_battle_publishes_core_session_before_ui_reset():
    window = _Harness(); old = window._observation_runtime_session_manager
    assert window.begin_new_battle() == "ui-session-1"
    assert window._observation_runtime_session_manager is old and old.session_id == "ui-session-1" and window._item_event_confirmations == []


def test_successful_rollover_resets_confirmation_and_presentation():
    window = _Harness(); window.begin_new_battle()
    assert window._current_observed_damage_confirmation is None and window.panel.events[0] == ("running", False)
    assert window.status.messages[-1] == "New battle session ready"


def test_failed_rollover_preserves_old_core_and_ui_state():
    window = _Harness(); before = _core_values(window); window._panels[("team_enemy", 0)].pokemon_view.en = None
    assert window.begin_new_battle() is None and _core_values(window) == before
    assert window._item_event_confirmations == [{"old": 1}]


def test_new_battle_performs_no_save_load_or_restore(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager
    monkeypatch.setattr(manager, "save", lambda *_: pytest.fail("save"))
    monkeypatch.setattr(manager, "load", lambda *_: pytest.fail("load"))
    monkeypatch.setattr(manager, "restore", lambda *_: pytest.fail("restore"))
    assert window.begin_new_battle() == "ui-session-1"


def test_confirmation_uses_active_bundle_sequence_allocator():
    window = _Harness(); event = window._capture_structured_observed_damage_confirmation({"damage": 12})
    assert event["observation_sequence"] == 1 and window._observation_runtime_session_manager.last_allocated_sequence == 1


def test_confirmation_admission_uses_matching_captured_session():
    window = _Harness(); event = window._capture_structured_observed_damage_confirmation({"damage": 12}); manager = window._observation_runtime_session_manager
    assert manager.admit_confirmation(event["session_id"], {"status": "confirmed", "observation": event})["status"] == "added"
    assert manager.read_collection_snapshot()["ordered_observations"] == [event]


def test_stale_confirmation_does_not_advance_new_session_allocator():
    window = _Harness(); old_event = window._capture_structured_observed_damage_confirmation({"damage": 12}); window.begin_new_battle(); manager = window._observation_runtime_session_manager
    before = manager.last_allocated_sequence
    assert manager.admit_confirmation(old_event["session_id"], {"status": "confirmed", "observation": old_event})["status"] == "stale_session"
    assert manager.last_allocated_sequence == before == 0


def test_worker_collection_snapshot_is_detached():
    window = _Harness(); frozen = window._observation_runtime_session_manager.read_collection_snapshot(); frozen["ordered_observations"].append({"x": 1})
    assert window._observation_runtime_session_manager.read_collection_snapshot()["ordered_observations"] == []


def test_admission_failure_can_leave_gap_without_store_mutation():
    window = _Harness(); event = window._capture_structured_observed_damage_confirmation({"damage": 12}); before = _core_values(window)
    assert window._observation_runtime_session_manager.admit_confirmation(event["session_id"], {"status": "bad"})["status"] == "ignored"
    after = _core_values(window)
    assert after[3:] == before[3:] and after[5] == 1


def test_current_success_updates_presentation_after_token_and_session_guards():
    window = _Harness(); token = window._begin_advice_request("structured")
    window._on_structured_recommendation_finished(token, "ui-session-0", _result())
    assert any(event[0] == "text" for event in window.panel.events)


def test_old_token_current_session_success_is_suppressed():
    window = _Harness(); old = window._begin_advice_request("structured"); current = window._begin_advice_request("structured")
    window._on_structured_recommendation_finished(old, "ui-session-0", _result())
    assert window.panel.events == [] and window._active_advice_request_token == current


def test_old_session_matching_token_success_is_suppressed():
    window = _Harness(); token = window._begin_advice_request("structured"); window.begin_new_battle()
    window._active_advice_owner, window._active_advice_request_token = "structured", token
    window._on_structured_recommendation_finished(token, "ui-session-0", _result())
    assert window.panel.events[0] == ("running", False) and not any(event[0] == "text" for event in window.panel.events)


def test_stale_success_does_not_mutate_core_or_overwrite_ui():
    window = _Harness(); token = window._begin_advice_request("structured"); window.begin_new_battle(); before = _core_values(window); ui = list(window.panel.events)
    window._on_structured_recommendation_finished(token, "ui-session-0", _result())
    assert _core_values(window) == before and window.panel.events == ui


def test_stale_success_still_cleans_up_worker_and_thread():
    window = _Harness(); token = window._begin_advice_request("structured"); thread, worker = _Thread(), object(); window.begin_new_battle()
    window._cleanup_structured_worker(token, thread, worker)
    assert thread.deleted == 1


def test_current_error_updates_current_presentation():
    window = _Harness(); token = window._begin_advice_request("structured")
    window._on_structured_recommendation_failed(token, "ui-session-0", "safe error")
    assert ("error", "safe error") in window.panel.events


def test_old_session_error_is_suppressed():
    window = _Harness(); token = window._begin_advice_request("structured"); window.begin_new_battle(); window._active_advice_owner, window._active_advice_request_token = "structured", token; ui = list(window.panel.events)
    window._on_structured_recommendation_failed(token, "ui-session-0", "old error")
    assert window.panel.events == ui


def test_stale_error_does_not_overwrite_status_or_button_state():
    window = _Harness(); token = window._begin_advice_request("structured"); window.begin_new_battle(); window._active_advice_owner, window._active_advice_request_token = "structured", token; before = (list(window.status.messages), list(window.panel.structured_request_button.disabled))
    window._on_structured_recommendation_failed(token, "ui-session-0", "old error")
    assert (window.status.messages, window.panel.structured_request_button.disabled) == before


def test_stale_error_does_not_modify_token_log():
    window = _Harness(); token = window._begin_advice_request("structured"); window.begin_new_battle(); window._active_advice_owner, window._active_advice_request_token = "structured", token
    window._on_structured_recommendation_failed(token, "ui-session-0", "old error")
    assert "token_usage" not in inspect.getsource(MainWindow._on_structured_recommendation_failed)


def test_stale_error_still_cleans_up_worker_and_thread():
    window = _Harness(); token = window._begin_advice_request("structured"); thread, worker = _Thread(), object(); window.begin_new_battle()
    window._cleanup_structured_worker(token, thread, worker)
    assert thread.deleted == 1


def test_lifecycle_wiring_has_no_autosave_startup_or_import_hooks():
    source = inspect.getsource(main_window_module)
    assert not any(token in source for token in ("autosave", "startup recovery", "cross_session_import"))
    assert "QFileDialog" not in inspect.getsource(MainWindow._begin_new_battle_session)


def test_rollover_wiring_never_calls_provider_or_persistence():
    imports = ast.parse(inspect.getsource(main_window_module))
    modules = [node.module for node in ast.walk(imports) if isinstance(node, ast.ImportFrom) and node.module]
    assert "llm.advisor_observation_replay_persistence_commands" not in modules


def test_ui_does_not_expose_raw_runtime_store_or_commands():
    public = {name for name in dir(MainWindow) if not name.startswith("_")}
    assert not ({"store", "runtime", "commands", "persistence", "rollback", "save", "load", "restore"} & public)
