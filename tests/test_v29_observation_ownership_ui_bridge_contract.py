from types import SimpleNamespace

from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input
from ui import main_window
from ui.main_window import MainWindow, StructuredRecommendationWorker


class _Panel:
    def __init__(self, pokemon_id):
        self.pokemon_view = SimpleNamespace(en=pokemon_id)


class _Dialog:
    def __init__(self, **_):
        self.observed_damage_confirmation = {"damage": 31}

    def exec(self):
        return True


class _Harness:
    _open_current_observed_damage_dialog = MainWindow._open_current_observed_damage_dialog
    _capture_structured_observed_damage_confirmation = MainWindow._capture_structured_observed_damage_confirmation
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    _update_current_observed_damage_summary = MainWindow._update_current_observed_damage_summary

    def __init__(self):
        self._battle_session_sequence = 0
        self._current_battle_session_id = self._current_state_session_id = "ui-session-0"
        self._observation_collection = ObservationCollection("ui-session-0")
        self._current_observed_damage_confirmation = None
        self._structured_observed_damage_confirmations = []
        self._observation_sequence = 0
        self.selected_slots = {"team_my": 0, "team_enemy": 1}
        self._panels = {("team_my", 0): _Panel("pikachu"), ("team_enemy", 1): _Panel("eevee")}
        self._current_condition_confirmations = {}
        self._current_ability_confirmations = {}
        self._structured_ability_confirmations = {}
        self._current_stat_stage_confirmations = {}
        self._current_final_stat_confirmations = {}
        self._structured_final_stat_confirmations = {}
        self._current_hp_confirmations = {}
        self._item_event_confirmations = []
        self._current_field_state_confirmation = None
        self._battle_counter_confirmation = None
        self._consecutive_use_confirmation = None

    def _slot_panel(self, column, slot):
        return self._panels[(column, slot)]


def _battle(session):
    return {"current_state_session_id": session, "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_selected_move": {"move_id": "tackle"}}}


def test_observed_damage_dialog_bridges_to_private_session_collection(monkeypatch):
    window = _Harness()
    monkeypatch.setattr(main_window, "CurrentObservedDamageDialog", _Dialog)

    window._open_current_observed_damage_dialog()

    frozen = window._observation_collection.snapshot(session_id="ui-session-0")
    assert frozen["status"] == "ready"
    assert frozen["ordered_observations"][0]["session_id"] == "ui-session-0"
    assert frozen["ordered_observations"][0]["damage_amount"] == 31
    handoff = build_turn_snapshot_from_battle_input(_battle("ui-session-0"), observation_snapshot=frozen).to_dict()
    assert handoff["current_state"]["canonical_observation_collection"]["ordered_observations"][0]["damage_amount"] == 31


def test_new_battle_resets_collection_without_reusing_old_evidence():
    window = _Harness()
    window._observation_collection.add_confirmation_result({"status": "confirmed", "observation": {"observation_id": "old", "observation_sequence": 1, "event_kind": "used_move_observed", "session_id": "ui-session-0", "payload": {}}})

    assert window._begin_new_battle_session() == "ui-session-1"
    assert window._observation_collection.snapshot()["session_id"] == "ui-session-1"
    assert window._observation_collection.snapshot()["ordered_observations"] == []


def test_structured_worker_copies_detached_snapshot_not_live_collection():
    frozen = {"status": "ready", "session_id": "ui-session-0", "ordered_observations": []}
    worker = StructuredRecommendationWorker([], {}, None, observation_snapshot=frozen)

    frozen["ordered_observations"].append({"observation_id": "later"})

    assert worker._observation_snapshot["ordered_observations"] == []
