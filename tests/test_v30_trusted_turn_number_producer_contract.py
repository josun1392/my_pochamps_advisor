from types import SimpleNamespace

import pytest

from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, USED_MOVE_SOURCE, USER_TRUST
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input
from ui.main_window import MainWindow


class _Panel:
    def __init__(self, pokemon_id): self.pokemon_view = SimpleNamespace(en=pokemon_id)


class _Harness:
    set_current_turn_number = MainWindow.set_current_turn_number
    advance_turn = MainWindow.advance_turn
    _trusted_turn_context_snapshot = MainWindow._trusted_turn_context_snapshot
    _capture_structured_observed_damage_confirmation = MainWindow._capture_structured_observed_damage_confirmation
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    _begin_advice_request = MainWindow._begin_advice_request

    def __init__(self):
        self._battle_session_sequence = 0
        self._current_battle_session_id = self._current_state_session_id = "ui-session-0"
        self._current_trusted_turn_number = None
        self._observation_collection = ObservationCollection("ui-session-0")
        self._observation_sequence = self._advice_request_sequence = 0
        self._active_advice_owner = self._active_advice_request_token = self._active_advice_terminal_token = None
        self._is_closing = False
        self.selected_slots = {"team_my": 0, "team_enemy": 1}
        self._panels = {("team_my", 0): _Panel("pikachu"), ("team_enemy", 1): _Panel("eevee")}
        self._current_condition_confirmations = self._current_ability_confirmations = self._structured_ability_confirmations = {}
        self._current_stat_stage_confirmations = self._current_final_stat_confirmations = self._structured_final_stat_confirmations = {}
        self._current_hp_confirmations = self._item_event_confirmations = []
        self._current_observed_damage_confirmation = self._current_field_state_confirmation = None
        self._structured_observed_damage_confirmations = []
        self._battle_counter_confirmation = self._consecutive_use_confirmation = None

    def _slot_panel(self, column, slot): return self._panels[(column, slot)]


def _battle(session="ui-session-0"):
    return {"current_state_session_id": session, "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_selected_move": {"move_id": "tackle"}}}


def test_explicit_turn_owner_validation_advance_and_request_counter_are_independent():
    window = _Harness()
    assert window._trusted_turn_context_snapshot()["status"] == "unavailable"
    for invalid in (0, -1, True, 1.5, "3"):
        with pytest.raises(ValueError): window.set_current_turn_number(invalid)
    with pytest.raises(ValueError): window.advance_turn()
    window.set_current_turn_number(2)
    assert window.advance_turn() == 3
    window._begin_advice_request("structured")
    assert (window._current_trusted_turn_number, window._advice_request_sequence) == (3, 1)
    window._battle_counter_confirmation = {"rage_fist_hits_received": 4}
    assert window._current_trusted_turn_number == 3


def test_observations_keep_explicit_turn_and_sequence_is_independent():
    window = _Harness(); window.set_current_turn_number(2)
    first = window._capture_structured_observed_damage_confirmation({"damage": 10})
    second = window._capture_structured_observed_damage_confirmation({"damage": 11})
    window.set_current_turn_number(3)
    third = window._capture_structured_observed_damage_confirmation({"damage": 12})
    assert (first["turn_number"], second["turn_number"], third["turn_number"]) == (2, 2, 3)
    assert [first["observation_sequence"], second["observation_sequence"], third["observation_sequence"]] == [1, 2, 3]
    window.set_current_turn_number(None)
    assert window._capture_structured_observed_damage_confirmation({"damage": 13})["turn_number"] is None


def test_new_battle_resets_turn_and_turn_snapshot_context_is_detached():
    window = _Harness(); window.set_current_turn_number(3)
    context = window._trusted_turn_context_snapshot()
    frozen = build_turn_snapshot_from_battle_input(_battle(), trusted_turn_context=context).to_dict()
    window._begin_new_battle_session()
    assert window._current_trusted_turn_number is None
    assert frozen["current_state"]["trusted_turn_context"]["turn_number"] == 3
    assert build_turn_snapshot_from_battle_input(_battle(), trusted_turn_context={**context, "session_id": "old"}).to_dict().get("current_state", {}).get("trusted_turn_context") is None


def test_collection_and_contract_only_lifecycle_producers_validate_turn_numbers():
    collection = ObservationCollection("s")
    for invalid in (0, -1, True, 1.5, "1"):
        result = collection.add_confirmation_result({"status": "confirmed", "observation": {"observation_id": str(invalid), "observation_sequence": 1, "event_kind": "used_move_observed", "session_id": "s", "turn_number": invalid}})
        assert result["status"] == "invalid_observation"
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}})
    args = dict(event_kind="used_move_observed", payload={"move_id": "tackle"}, session_id="s", source=USED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", observation_id="same")
    assert boundary.confirm(**args, turn_number=2)["status"] == "confirmed"
    assert boundary.confirm(**args, turn_number=2)["status"] == "duplicate"
    assert boundary.confirm(**args, turn_number=3)["status"] == "conflicting_confirmation"
