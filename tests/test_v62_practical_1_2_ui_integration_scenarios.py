"""Sanitized Practical 1.2 readiness and explicit-capture integration scenarios."""

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_recommendation_readiness import build_recommendation_readiness
from ui.main_window import MainWindow
from ui.widgets.current_hp_dialog import CurrentHPDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _prepared(*candidates):
    return {"status": "ready", "candidates": list(candidates)}


def _missing(*paths, unsupported=False):
    mechanics = {"status": "insufficient_context", "missing_inputs": list(paths)}
    candidate = {"mechanics_result": mechanics}
    if unsupported:
        candidate["move_success"] = {"status": "unsupported_mechanic", "unsupported_reason": "status_move"}
    return candidate


def test_readiness_multi_gap_presentation_preserves_routes_until_each_canonical_gap_is_resolved():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    requested: list[str] = []
    panel.readiness_input_requested.connect(requested.append)

    prepared = _prepared(
        _missing("attacker.current_hp", "defender.item", "attacker.toxic_progression", unsupported=True),
    )
    initial = build_recommendation_readiness(prepared_cycle=prepared)
    prepared["candidates"][0]["mechanics_result"]["missing_inputs"] = []
    assert initial["missing"][0]["path"] == "attacker.current_hp"
    panel.set_recommendation_readiness(initial)
    assert initial["status"] == "incomplete"
    assert "Can confirm: Current HP needed; Held item unknown" in panel.readiness_label.text()
    assert "Still unavailable: Toxic progression authority missing" in panel.readiness_label.text()
    assert "Unsupported: This selected mechanic is not supported yet" in panel.readiness_label.text()
    panel._request_readiness_input()
    panel._readiness_extra_input_buttons[0].click()
    assert requested == ["current_hp", "current_item"]

    after_hp = build_recommendation_readiness(prepared_cycle=_prepared(
        _missing("defender.item", "attacker.toxic_progression", unsupported=True),
    ))
    panel.set_recommendation_readiness(after_hp)
    assert "Current HP needed" not in panel.readiness_label.text()
    assert "Held item unknown" in panel.readiness_label.text()
    assert "Toxic progression authority missing" in panel.readiness_label.text()

    ready = build_recommendation_readiness(prepared_cycle=_prepared({"mechanics_result": {"status": "known"}}))
    panel.set_recommendation_readiness(ready)
    assert ready["status"] == "ready"
    assert panel._readiness_extra_input_buttons == []
    assert panel._readiness_action is None


def test_paired_hp_confirmation_applies_only_valid_active_owners_and_cancel_is_read_only(monkeypatch):
    owners = {
        "self": ("session", 0, "pikachu"),
        "opponent": ("session", 1, "eevee"),
    }
    updates: list[str] = []
    window = SimpleNamespace(
        _current_hp_confirmations={},
        _current_hp_confirmation_owners={},
        _recommendation_readiness_owner=("session", 0, "pikachu"),
        _current_hp_owner_for_side=lambda side: owners[side],
        _update_current_hp_summary=lambda: updates.append("summary"),
        _check_structured_recommendation_readiness=lambda: updates.append("readiness"),
    )

    class AcceptedPairDialog:
        def __init__(self, **_kwargs):
            self.current_hp_confirmations = [
                {"side": "self", "current_hp": 40, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"},
                {"side": "opponent", "current_hp": 70, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"},
            ]

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module, "CurrentHPDialog", AcceptedPairDialog)
    MainWindow._open_current_hp_dialog(window)
    assert window._current_hp_confirmations == {
        "self": {"side": "self", "current_hp": 40, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
        "opponent": {"side": "opponent", "current_hp": 70, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
    }
    assert window._current_hp_confirmation_owners == owners
    assert updates == ["summary", "readiness"]

    before = dict(window._current_hp_confirmations)

    class CancelledDialog:
        def __init__(self, **_kwargs):
            self.current_hp_confirmations = []

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(main_window_module, "CurrentHPDialog", CancelledDialog)
    MainWindow._open_current_hp_dialog(window)
    assert window._current_hp_confirmations == before


def test_stale_paired_hp_record_is_rejected_without_blocking_the_other_active_side(monkeypatch):
    owners = {
        "self": ("session", 0, "pikachu"),
        "opponent": ("session", 1, "eevee"),
    }
    window = SimpleNamespace(
        _current_hp_confirmations={},
        _current_hp_confirmation_owners={},
        _recommendation_readiness_owner=None,
        _current_hp_owner_for_side=lambda side: owners[side],
        _update_current_hp_summary=lambda: None,
        _check_structured_recommendation_readiness=lambda: None,
    )

    class PartlyStaleDialog:
        def __init__(self, **_kwargs):
            self.current_hp_confirmations = [
                {"side": "self", "current_hp": 40, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"},
                {"side": "opponent", "current_hp": 70, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"},
            ]

        def exec(self):
            owners["opponent"] = ("session", 1, "vaporeon")
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_module, "CurrentHPDialog", PartlyStaleDialog)
    MainWindow._open_current_hp_dialog(window)
    assert set(window._current_hp_confirmations) == {"self"}
    assert window._current_hp_confirmation_owners["self"] == ("session", 0, "pikachu")


def test_item_readiness_route_rejects_a_replacement_before_the_existing_item_flow(monkeypatch):
    cleared: list[bool] = []
    opened: list[tuple[str, int]] = []
    refreshed: list[bool] = []
    panel = SimpleNamespace(pokemon_view=SimpleNamespace(en="pikachu"))
    window = SimpleNamespace(
        _recommendation_readiness_owner=("session", 0, "pikachu"),
        selected_slots={"team_my": 0},
        center_column=SimpleNamespace(llm_advice_panel=SimpleNamespace(clear_recommendation_readiness=lambda: cleared.append(True))),
        _slot_panel=lambda _column, _slot: panel,
        _on_item_profile_requested=lambda column, slot: opened.append((column, slot)),
        _check_structured_recommendation_readiness=lambda: refreshed.append(True),
    )
    monkeypatch.setattr(MainWindow, "_active_session_id", lambda _self: "session")
    MainWindow._open_readiness_input(window, "current_item")
    assert opened == [("team_my", 0)]
    assert refreshed == [True]
    assert cleared == []

    window._recommendation_readiness_owner = ("session", 0, "pikachu")
    panel.pokemon_view = SimpleNamespace(en="raichu")
    MainWindow._open_readiness_input(window, "current_item")
    assert opened == [("team_my", 0)]
    assert refreshed == [True]
    assert cleared == [True]
    assert window._recommendation_readiness_owner is None


def test_paired_hp_dialog_never_converts_a_percent_or_mutates_unchecked_side():
    QApplication.instance() or QApplication([])
    dialog = CurrentHPDialog(current_hp={})
    dialog.confirm_self.setChecked(True)
    dialog.self_current_spin.setValue(51)
    dialog.self_maximum_spin.setValue(100)
    dialog.confirm_opponent.setChecked(False)
    dialog._save()
    assert dialog.current_hp_confirmations == [
        {"side": "self", "current_hp": 51, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
    ]
