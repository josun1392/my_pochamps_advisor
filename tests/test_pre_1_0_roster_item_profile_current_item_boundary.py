"""Roster item setup stays local unless the exact runtime active item is confirmed."""

from copy import deepcopy
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from ui.main_window import MainWindow
from ui.widgets.item_profile_dialog import item_button_text, item_profile_from_option


def _window() -> MainWindow:
    QApplication.instance() or QApplication([])
    window = MainWindow()
    for column, names in ((window.my_team_column, ("pikachu", "eevee")),
                          (window.opponent_team_column, ("raichu", "garchomp"))):
        for slot, pokemon_id in enumerate(names):
            column.panels[slot].pokemon_view = SimpleNamespace(en=pokemon_id, ko=pokemon_id.title())
    return window


def _save(monkeypatch, window: MainWindow, column_name: str, slot: int, profile: dict | None,
          *, accepted: bool = True, click_button: bool = False) -> None:
    class Dialog:
        def __init__(self, **_kwargs):
            self.item_profile = deepcopy(profile)

        def exec(self):
            return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected

    monkeypatch.setattr(main_window_module, "ItemProfileDialog", Dialog)
    if click_button:
        window._slot_panel(column_name, slot).item_button.click()
    else:
        window._on_item_profile_requested(column_name, slot)


def _item(window: MainWindow, option: str, role: str = "my_active") -> dict:
    return item_profile_from_option(option, role_key=role, item_options=window._legal_item_options())


def test_prebattle_two_roster_items_save_independently_without_selection_or_observation(monkeypatch) -> None:
    window = _window()
    first, second = _item(window, "leftovers"), _item(window, "focus-sash")
    selected = dict(window.selected_slots)
    _save(monkeypatch, window, "team_my", 0, first)
    _save(monkeypatch, window, "team_my", 1, second, click_button=True)
    panels = window.my_team_column.panels
    assert panels[0].item_profile == first and panels[1].item_profile == second
    assert panels[0].item_profile["item_id"] != panels[1].item_profile["item_id"]
    assert panels[0].item_button.text() == item_button_text(first)
    assert panels[1].item_button.text() == item_button_text(second)
    assert window.selected_slots == selected
    assert window._observation_runtime_session_manager is None
    _save(monkeypatch, window, "team_my", 1, _item(window, "none"), accepted=False)
    assert panels[1].item_profile == second and window.selected_slots == selected
    window.close()


def test_bench_item_during_battle_changes_only_its_card_not_active_runtime_or_evidence(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    _save(monkeypatch, window, "team_my", 0, _item(window, "leftovers"))
    before_state, before_collection = manager.read_state(), manager.read_collection_snapshot()
    selected = dict(window.selected_slots)
    own_bench = _item(window, "focus-sash")
    opponent_bench = _item(window, "leftovers", "opponent_active")
    _save(monkeypatch, window, "team_my", 1, own_bench, click_button=True)
    _save(monkeypatch, window, "team_enemy", 1, opponent_bench, click_button=True)
    assert window.my_team_column.panels[1].item_profile == own_bench
    assert window.opponent_team_column.panels[1].item_profile == opponent_bench
    assert window.my_team_column.panels[1].item_button.text() == item_button_text(own_bench)
    assert window.opponent_team_column.panels[1].item_button.text() == item_button_text(opponent_bench, role_key="opponent_active")
    assert window.selected_slots == selected
    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection
    assert [row["event_kind"] for row in manager.read_collection_snapshot()["ordered_observations"]] == ["current_item_observed"]
    assert not window.read_c6_decision_capture_snapshot()["actor_captures"]
    assert not window.read_c6_observed_transition_snapshot()["actor_transitions"]
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 0
    assert state["self_side"]["pokemon"][0]["known_item"] == "leftovers"
    window.close()


def test_active_item_and_explicit_no_item_use_existing_current_observation(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    profile = _item(window, "leftovers")
    _save(monkeypatch, window, "team_my", 0, profile)
    assert window.my_team_column.panels[0].item_profile == profile
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["known_item"] == "leftovers"
    observations = manager.read_collection_snapshot()["ordered_observations"]
    assert [row["event_kind"] for row in observations] == ["current_item_observed"]
    assert observations[0]["payload"] == {"status": "known", "item": "leftovers"}
    no_item = _item(window, "none")
    _save(monkeypatch, window, "team_my", 0, no_item)
    assert window.my_team_column.panels[0].item_profile == no_item
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["known_item"] is None
    observations = manager.read_collection_snapshot()["ordered_observations"]
    assert [row["event_kind"] for row in observations] == ["current_item_observed", "current_item_observed"]
    assert observations[-1]["payload"] == {"status": "known_absent"}
    window.close()


def test_cancel_and_rejected_active_admission_leave_card_and_runtime_unchanged(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    panel = window.my_team_column.panels[0]
    previous_profile, previous_button = deepcopy(panel.item_profile), panel.item_button.text()
    before_state, before_collection = manager.read_state(), manager.read_collection_snapshot()
    _save(monkeypatch, window, "team_my", 0, _item(window, "leftovers"), accepted=False)
    assert panel.item_profile == previous_profile and panel.item_button.text() == previous_button
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection
    window.set_current_turn_number(None)
    _save(monkeypatch, window, "team_my", 0, _item(window, "leftovers"))
    assert panel.item_profile == previous_profile and panel.item_button.text() == previous_button
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection
    window.close()


def test_active_unknown_is_local_only_and_does_not_claim_known_absence(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()
    unknown = _item(window, "unknown")
    _save(monkeypatch, window, "team_my", 0, unknown)
    assert window.my_team_column.panels[0].item_profile == unknown
    assert manager.read_collection_snapshot() == before
    assert is_unknown_battle_fact(manager.read_state()["state"]["self_side"]["pokemon"][0]["known_item"])
    window.close()
