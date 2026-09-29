"""Roster item setup stays local unless the exact runtime active item is confirmed."""

from copy import deepcopy
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from ui.main_window import MainWindow
from ui.widgets.item_profile_dialog import item_button_text, item_profile_from_option


def _window() -> MainWindow:
    QApplication.instance() or QApplication([])
    window = MainWindow()
    for column, names in ((window.my_team_column, ("pikachu", "eevee")),
                          (window.opponent_team_column, ("raichu", "garchomp"))):
        for slot, pokemon_id in enumerate(names):
            column.panels[slot].pokemon_view = SimpleNamespace(
                en=pokemon_id,
                ko=pokemon_id.title(),
                types_en=["normal"],
                types_ko=["노말"],
                base_stats={
                    "hp": 80, "attack": 80, "defense": 80,
                    "special-attack": 80, "special-defense": 80, "speed": 80,
                },
                abilities_en=["test-ability"],
                abilities_ko=["테스트특성"],
            )
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


def _accept_presented(monkeypatch, window: MainWindow, column_name: str, slot: int,
                      *, result_profile: dict | None | object = Ellipsis) -> dict:
    captured = {}

    class Dialog:
        def __init__(self, **kwargs):
            captured.update({
                key: deepcopy(value) for key, value in kwargs.items() if key != "parent"
            })
            self.item_profile = deepcopy(
                kwargs["current_profile"] if result_profile is Ellipsis else result_profile
            )

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module, "ItemProfileDialog", Dialog)
    window._on_item_profile_requested(column_name, slot)
    return captured


def _current_structured_input(window: MainWindow) -> dict:
    manager = window._observation_runtime_session_manager
    session_id = window._active_session_id()
    snapshot = manager.capture_runtime_state_snapshot(session_id)
    projection = build_runtime_advice_state_projection(snapshot["state"])
    return window._build_current_structured_analysis_battle_input(
        session_id=session_id,
        runtime_projection=projection,
    )


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


def test_live_active_dialog_derives_unknown_and_unchanged_save_is_noop(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    before_state = manager.read_state()
    before_collection = manager.read_collection_snapshot()

    captured = _accept_presented(monkeypatch, window, "team_my", 0)

    assert captured["current_profile"]["status"] == "unknown"
    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection
    assert window.my_team_column.panels[0].item_profile["status"] == "unknown"
    window.close()


def test_live_active_dialog_runtime_truth_beats_none_and_stale_panel(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    leftovers = _item(window, "leftovers")
    scarf = _item(window, "choice-scarf")
    no_item = _item(window, "none")

    _save(monkeypatch, window, "team_my", 0, leftovers)
    one_observation = deepcopy(manager.read_collection_snapshot())
    panel = window.my_team_column.panels[0]

    panel.item_profile = None
    captured = _accept_presented(monkeypatch, window, "team_my", 0)
    assert captured["current_profile"]["item_id"] == "leftovers"
    assert manager.read_collection_snapshot() == one_observation

    panel.item_profile = scarf
    captured = _accept_presented(monkeypatch, window, "team_my", 0)
    assert captured["current_profile"]["item_id"] == "leftovers"
    assert manager.read_collection_snapshot() == one_observation

    _save(monkeypatch, window, "team_my", 0, no_item)
    absent_observations = deepcopy(manager.read_collection_snapshot())
    panel.item_profile = scarf
    captured = _accept_presented(monkeypatch, window, "team_my", 0)
    assert captured["current_profile"]["status"] == "none"
    assert manager.read_collection_snapshot() == absent_observations
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["known_item"] is None
    window.close()


def test_real_semantic_item_changes_still_use_current_item_admission(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    leftovers = _item(window, "leftovers")
    no_item = _item(window, "none")

    _save(monkeypatch, window, "team_my", 0, no_item)
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["known_item"] is None

    _save(monkeypatch, window, "team_my", 0, leftovers)
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["known_item"] == "leftovers"

    _save(monkeypatch, window, "team_my", 0, no_item)
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["known_item"] is None
    assert [row["payload"]["status"] for row in manager.read_collection_snapshot()["ordered_observations"]] == [
        "known_absent", "known", "known_absent"
    ]
    window.close()


def test_explicit_unknown_never_erases_trusted_runtime_item(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    leftovers = _item(window, "leftovers")
    unknown = _item(window, "unknown")

    _save(monkeypatch, window, "team_my", 0, leftovers)
    before_collection = deepcopy(manager.read_collection_snapshot())
    _save(monkeypatch, window, "team_my", 0, unknown)

    assert manager.read_collection_snapshot() == before_collection
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["known_item"] == "leftovers"
    assert window.my_team_column.panels[0].item_profile["status"] == "unknown"
    window.close()


def test_active_reset_is_local_only_and_reopen_uses_runtime_truth(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    leftovers = _item(window, "leftovers")
    _save(monkeypatch, window, "team_my", 0, leftovers)
    before_state = deepcopy(manager.read_state())
    before_collection = deepcopy(manager.read_collection_snapshot())

    _accept_presented(monkeypatch, window, "team_my", 0, result_profile=None)

    assert window.my_team_column.panels[0].item_profile is None
    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection

    captured = _accept_presented(monkeypatch, window, "team_my", 0)
    assert captured["current_profile"]["item_id"] == "leftovers"
    assert manager.read_collection_snapshot() == before_collection
    window.close()


def test_consumed_absence_unchanged_save_preserves_runtime_provenance(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    state = manager.read_state()["state"]
    active = state["self_side"]["pokemon"][0]
    active["known_item"] = None
    active["known_item_provenance"] = {
        "event_kind": "item_consumption_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "source_observation_id": "test-consume",
        "source_sequence": 1,
    }
    recreated = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert recreated["status"] == "session_ready"
    window._observation_runtime_session_manager = recreated["manager"]
    manager = window._observation_runtime_session_manager
    before = deepcopy(manager.read_state())

    captured = _accept_presented(monkeypatch, window, "team_my", 0)

    assert captured["current_profile"]["status"] == "none"
    after = manager.read_state()
    assert after == before
    provenance = after["state"]["self_side"]["pokemon"][0]["known_item_provenance"]
    assert provenance["event_kind"] == "item_consumption_observed"
    assert manager.read_collection_snapshot()["ordered_observations"] == []
    window.close()


def test_current_structured_input_uses_runtime_item_over_stale_panel(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    panel = window.my_team_column.panels[0]

    panel.item_profile = _item(window, "none")
    battle_input = _current_structured_input(window)
    assert battle_input["item_profiles"]["my_active"]["status"] == "unknown"

    _save(monkeypatch, window, "team_my", 0, _item(window, "leftovers"))
    panel.item_profile = _item(window, "choice-scarf")
    battle_input = _current_structured_input(window)
    assert battle_input["item_profiles"]["my_active"]["item_id"] == "leftovers"

    _save(monkeypatch, window, "team_my", 0, _item(window, "none"))
    panel.item_profile = _item(window, "choice-scarf")
    battle_input = _current_structured_input(window)
    assert battle_input["item_profiles"]["my_active"]["status"] == "none"
    window.close()


def test_opponent_live_dialog_uses_runtime_known_item_and_unchanged_save_is_noop(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    leftovers = _item(window, "leftovers", "opponent_active")
    _save(monkeypatch, window, "team_enemy", 0, leftovers)
    before = deepcopy(manager.read_collection_snapshot())
    window.opponent_team_column.panels[0].item_profile = None

    captured = _accept_presented(monkeypatch, window, "team_enemy", 0)

    assert captured["current_profile"]["item_id"] == "leftovers"
    assert manager.read_collection_snapshot() == before
    assert manager.read_state()["state"]["opponent_side"]["pokemon"][0]["known_item"] == "leftovers"
    window.close()


def test_runtime_known_unrepresentable_item_fails_closed_before_dialog(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    state = manager.read_state()["state"]
    active = state["self_side"]["pokemon"][0]
    active["known_item"] = "not-in-current-item-options"
    active["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known",
        "source_observation_id": "test-known",
        "source_sequence": 1,
    }
    recreated = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert recreated["status"] == "session_ready"
    window._observation_runtime_session_manager = recreated["manager"]

    class Dialog:
        def __init__(self, **_kwargs):
            raise AssertionError("unsupported runtime item must fail before opening dialog")

    monkeypatch.setattr(main_window_module, "ItemProfileDialog", Dialog)
    window._on_item_profile_requested("team_my", 0)

    assert "cannot be represented safely" in window.statusBar().currentMessage()
    runtime = window._observation_runtime_session_manager.read_state()["state"]
    assert runtime["self_side"]["pokemon"][0]["known_item"] == "not-in-current-item-options"
    window.close()


def test_target_no_longer_current_active_after_dialog_emits_no_item_observation(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    before_collection = deepcopy(manager.read_collection_snapshot())
    selected = _item(window, "leftovers")

    class Dialog:
        def __init__(self, **_kwargs):
            self.item_profile = deepcopy(selected)

        def exec(self):
            state = manager.read_state()["state"]
            state["self_side"]["active_slot_index"] = 1
            recreated = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
            assert recreated["status"] == "session_ready"
            window._observation_runtime_session_manager = recreated["manager"]
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module, "ItemProfileDialog", Dialog)
    window._on_item_profile_requested("team_my", 0)

    assert window._observation_runtime_session_manager.read_collection_snapshot() == before_collection
    runtime = window._observation_runtime_session_manager.read_state()["state"]
    assert runtime["self_side"]["active_slot_index"] == 1
    assert is_unknown_battle_fact(runtime["self_side"]["pokemon"][1]["known_item"])
    window.close()


def test_bench_stale_no_item_after_becoming_active_does_not_override_runtime_unknown_structured_input() -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    bench = window.my_team_column.panels[1]
    bench.item_profile = _item(window, "none")

    manager = window._observation_runtime_session_manager
    state = manager.read_state()["state"]
    assert is_unknown_battle_fact(state["self_side"]["pokemon"][1]["known_item"])
    state["self_side"]["active_slot_index"] = 1
    recreated = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert recreated["status"] == "session_ready"
    window._observation_runtime_session_manager = recreated["manager"]
    window.select_slot("team_my", 1)

    battle_input = _current_structured_input(window)

    assert battle_input["pokemon"]["my_active"]["name_en"] == "eevee"
    assert battle_input["item_profiles"]["my_active"]["status"] == "unknown"
    assert is_unknown_battle_fact(
        window._observation_runtime_session_manager.read_state()["state"]["self_side"]["pokemon"][1]["known_item"]
    )
    window.close()


def test_opponent_stale_panel_item_cannot_override_runtime_known_item(monkeypatch) -> None:
    window = _window()
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    leftovers = _item(window, "leftovers", "opponent_active")
    scarf = _item(window, "choice-scarf", "opponent_active")
    _save(monkeypatch, window, "team_enemy", 0, leftovers)
    before = deepcopy(manager.read_collection_snapshot())
    window.opponent_team_column.panels[0].item_profile = scarf

    captured = _accept_presented(monkeypatch, window, "team_enemy", 0)

    assert captured["current_profile"]["item_id"] == "leftovers"
    assert manager.read_collection_snapshot() == before
    assert manager.read_state()["state"]["opponent_side"]["pokemon"][0]["known_item"] == "leftovers"
    window.close()
