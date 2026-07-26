from types import SimpleNamespace

from ui.main_window import MainWindow


class _Harness:
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    begin_new_battle = MainWindow.begin_new_battle
    _selected_identity = MainWindow._selected_identity
    _active_session_id = MainWindow._active_session_id
    _retire_advice_presentation_authority = MainWindow._retire_advice_presentation_authority
    _reset_battle_presentation = MainWindow._reset_battle_presentation
    def __init__(self):
        self._battle_session_sequence = 0; self._observation_runtime_session_manager = None
        self.selected_slots = {"team_my": 0, "team_enemy": 0}
        self._panels = {("team_my", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="pikachu")), ("team_enemy", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="eevee"))}
        self._active_advice_owner = self._active_advice_request_token = self._active_advice_terminal_token = None
        self._current_condition_confirmations = {}; self._current_ability_confirmations = {}; self._current_stat_stage_confirmations = {}; self._current_hp_confirmations = {}; self._item_event_confirmations = []; self._current_field_state_confirmation = None; self._battle_counter_confirmation = None; self._consecutive_use_confirmation = None

    def _slot_panel(self, column, slot): return self._panels[(column, slot)]


def test_application_new_battle_entry_rolls_once_per_call():
    window = _Harness()
    assert window.begin_new_battle() == "ui-session-1"
    assert window._battle_session_sequence == 1
    assert window.begin_new_battle() == "ui-session-2"
