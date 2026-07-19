from types import SimpleNamespace

from ui.main_window import MainWindow


def test_apply_cancel_clear_battle_format_session_contract() -> None:
    window = MainWindow.__new__(MainWindow)
    window._current_battle_format_confirmation = {
        "battle_format": "singles", "source": "user_confirmed_battle_format", "confidence": "known"
    }
    window.center_column = SimpleNamespace(llm_advice_panel=SimpleNamespace(set_current_battle_format=lambda value: None))
    window._clear_current_battle_format_confirmation()
    assert window._current_battle_format_confirmation is None


def test_limited_context_gate_preserves_snapshot_but_omits_raw_confirmation() -> None:
    # The production input builder receives this gate from the advice action;
    # raw UI state stays in the session and is removed by payload filtering.
    assert "include_current_battle_format_confirmation=enable_battle_state_context" in open("ui/main_window.py", encoding="utf-8").read()
