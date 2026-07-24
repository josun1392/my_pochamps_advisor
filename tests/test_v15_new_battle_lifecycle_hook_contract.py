from ui.main_window import MainWindow


class _Harness:
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    begin_new_battle = MainWindow.begin_new_battle
    def __init__(self):
        self._battle_session_sequence = 0; self._current_battle_session_id = self._current_state_session_id = "ui-session-0"
        self._current_condition_confirmations = {}; self._current_ability_confirmations = {}; self._current_stat_stage_confirmations = {}; self._current_hp_confirmations = {}; self._item_event_confirmations = []; self._current_field_state_confirmation = None; self._battle_counter_confirmation = None; self._consecutive_use_confirmation = None


def test_application_new_battle_entry_rolls_once_per_call():
    window = _Harness()
    assert window.begin_new_battle() == "ui-session-1"
    assert window._battle_session_sequence == 1
    assert window.begin_new_battle() == "ui-session-2"
