from types import SimpleNamespace

from ui.main_window import MainWindow


class _Harness:
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    _selected_identity = MainWindow._selected_identity
    _active_session_id = MainWindow._active_session_id
    _retire_advice_presentation_authority = MainWindow._retire_advice_presentation_authority
    _reset_battle_presentation = MainWindow._reset_battle_presentation
    def __init__(self):
        self._battle_session_sequence = 0; self._observation_runtime_session_manager = None
        self.selected_slots = {"team_my": 0, "team_enemy": 0}
        self._panels = {("team_my", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="pikachu")), ("team_enemy", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="eevee"))}
        self._active_advice_owner = self._active_advice_request_token = self._active_advice_terminal_token = None
        self._current_condition_confirmations = {"self": {"x": 1}}; self._current_ability_confirmations = {"self": {"x": 1}}
        self._current_stat_stage_confirmations = {("self", "attack"): {"x": 1}}; self._current_hp_confirmations = {"self": {"x": 1}}
        self._item_event_confirmations = [{"side": "self"}]; self._current_field_state_confirmation = {"weather": "rain"}
        self._battle_counter_confirmation = {"x": 1}; self._consecutive_use_confirmation = {"x": 1}

    def _slot_panel(self, column, slot): return self._panels[(column, slot)]


def test_rollover_is_monotonic_and_clears_battle_local_context_without_request_token():
    window = _Harness(); window._advice_request_sequence = 7
    assert window._begin_new_battle_session() == "ui-session-1"
    assert window._begin_new_battle_session() == "ui-session-2"
    assert window._advice_request_sequence == 7
    assert window._current_hp_confirmations == {} and window._item_event_confirmations == []
    assert window._current_field_state_confirmation is None
