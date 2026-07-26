from copy import deepcopy
from types import SimpleNamespace
import inspect

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import (
    RUNTIME_ADVICE_STATE_VERSION,
    build_runtime_advice_state_projection,
    normalize_runtime_advice_state_projection,
)
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input
from ui.main_window import MainWindow


def _state(session="s"):
    return create_unknown_bootstrap_battle_state(session, "pikachu", "eevee")["state"]


def _manager(session="s"):
    return BattleObservationRuntimeSessionManager.create(session, _state(session))["manager"]


def _input(projection, session="s"):
    return {
        "pokemon": {
            "my_active": {"slot_index": 0, "name_en": "pikachu", "name_ko": "Pikachu"},
            "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "Eevee"},
        },
        "item_profiles": {"my_active": {}, "opponent_active": {}},
        "moves": {"my_selected_move": {}},
        "current_state_session_id": session,
        "runtime_advice_state": projection,
    }


def test_projection_uses_detached_active_runtime_state_and_is_deterministic():
    manager = _manager(); before = manager.read_state(); first = build_runtime_advice_state_projection(before["state"]); second = build_runtime_advice_state_projection(deepcopy(before["state"]))
    assert first["status"] == second["status"] == "runtime_projection_ready"
    assert first["runtime_advice_state"] == second["runtime_advice_state"] and first["runtime_fingerprint"] == before["state_fingerprint"]
    first["runtime_advice_state"]["self"]["active_pokemon"]["pokemon_id"] = "changed"
    assert manager.read_state() == before


def test_projection_contains_identity_and_explicit_unknown_without_defaults():
    projected = build_runtime_advice_state_projection(_state())["runtime_advice_state"]
    active = projected["self"]["active_pokemon"]
    assert active["pokemon_id"] == "pikachu" and active["current_hp"] == {"status": "unknown"}
    assert active["fainted"] == {"status": "unknown"} and projected["field"]["weather"] == {"status": "unknown"}


def test_projection_distinguishes_unknown_known_value_and_known_absent():
    state = _state(); pokemon = state["self_side"]["pokemon"][0]
    pokemon.update(current_hp=42, max_hp=100, fainted=False, condition=None, known_item="berry")
    state["field"].update(weather=None, terrain="electric")
    state["self_side"]["side_conditions"] = []
    active = build_runtime_advice_state_projection(state)["runtime_advice_state"]["self"]["active_pokemon"]
    field = build_runtime_advice_state_projection(state)["runtime_advice_state"]["field"]
    assert active["current_hp"] == {"status": "known", "value": 42} and active["fainted"] == {"status": "known", "value": False}
    assert active["condition"] == {"status": "known_absent"} and active["item"] == {"status": "known", "value": "berry"}
    assert field["weather"] == {"status": "known_absent"} and field["self_side_conditions"] == {"status": "known_absent"}


def test_projection_is_non_mutating_and_excludes_raw_runtime_internals():
    manager = _manager(); before = manager.read_state(); result = build_runtime_advice_state_projection(before["state"]); text = repr(result["runtime_advice_state"])
    assert manager.read_state() == before and manager.last_allocated_sequence == 0 and manager.read_applied_ledger() == {}
    assert all(term not in text for term in ("state_fingerprint", "persistence", "ledger", "commands", "coordinator"))
    assert "runtime_fingerprint" not in result["runtime_advice_state"]


def test_projection_rejects_invalid_state_and_session_mismatch_handoff():
    assert build_runtime_advice_state_projection({})["status"] == "invalid_runtime_state"
    projected = build_runtime_advice_state_projection(_state())["runtime_advice_state"]
    try:
        normalize_runtime_advice_state_projection(projected, "other")
    except ValueError:
        pass
    else:
        assert False, "foreign projection must be rejected"


def test_runtime_snapshot_captures_matching_state_session_and_fingerprint_detached():
    manager = _manager(); snapshot = manager.capture_runtime_state_snapshot("s"); current = manager.read_state()
    assert snapshot["status"] == "runtime_snapshot_ready" and snapshot["session_id"] == "s"
    assert snapshot["state"] == current["state"] and snapshot["state_fingerprint"] == current["state_fingerprint"]
    snapshot["state"]["session_id"] = "changed"
    assert manager.read_state() == current and manager.capture_runtime_state_snapshot("old")["status"] == "stale_session"


def test_turn_snapshot_includes_validated_runtime_advice_state_without_fingerprint():
    projection = build_runtime_advice_state_projection(_state())["runtime_advice_state"]
    snapshot = build_turn_snapshot_from_battle_input(_input(projection)).to_dict()
    current = snapshot["current_state"]["runtime_advice_state"]
    assert current == projection and current["schema_version"] == RUNTIME_ADVICE_STATE_VERSION
    assert "runtime_fingerprint" not in repr(snapshot)


class _Panel:
    def __init__(self): self.events = []; self.structured_request_button = SimpleNamespace(setDisabled=lambda value: self.events.append(("button", value)))
    def set_running(self, value): self.events.append(("running", value))
    def set_mode_advice_text(self, mode, text): self.events.append(("text", mode, text))
    def set_error(self, message): self.events.append(("error", message))


class _Harness:
    _is_current_advice_request = MainWindow._is_current_advice_request
    _claim_current_advice_terminal = MainWindow._claim_current_advice_terminal
    _is_current_structured_session = MainWindow._is_current_structured_session
    _is_current_structured_runtime_fingerprint = staticmethod(MainWindow._is_current_structured_runtime_fingerprint)
    _on_structured_recommendation_finished = MainWindow._on_structured_recommendation_finished
    _on_structured_recommendation_failed = MainWindow._on_structured_recommendation_failed

    def __init__(self):
        self._observation_runtime_session_manager = _manager()
        self._active_advice_owner, self._active_advice_request_token, self._active_advice_terminal_token = "structured", 7, None
        self._is_closing = False; self.panel = _Panel(); self.center_column = SimpleNamespace(llm_advice_panel=self.panel); self.messages = []
    def statusBar(self): return SimpleNamespace(showMessage=lambda message: self.messages.append(message))


def _result():
    return {"presentation_model": {"status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": []}}


def test_same_session_stale_fingerprint_success_and_error_are_rejected_without_terminal_claim(monkeypatch):
    window = _Harness(); manager = window._observation_runtime_session_manager; old = manager.read_state()["state_fingerprint"]
    current = manager.read_state()
    monkeypatch.setattr(manager, "capture_runtime_state_snapshot", lambda _session: {"status": "runtime_snapshot_ready", "session_id": "s", "state": deepcopy(current["state"]), "state_fingerprint": "new-revision"})
    window._on_structured_recommendation_finished(7, "s", old, _result())
    window._on_structured_recommendation_failed(7, "s", old, "late")
    assert window.panel.events == [] and window.messages == [] and window._active_advice_terminal_token is None


def test_current_fingerprint_remains_eligible_and_projection_source_has_no_provider_hook():
    window = _Harness(); fingerprint = window._observation_runtime_session_manager.read_state()["state_fingerprint"]
    window._on_structured_recommendation_finished(7, "s", fingerprint, _result())
    assert any(event[0] == "text" for event in window.panel.events)
    source = inspect.getsource(build_runtime_advice_state_projection)
    assert "call_structured_recommendation_provider" not in source and "requests." not in source


def test_main_window_structured_request_captures_projection_and_fingerprint_without_payload_exposure():
    source = inspect.getsource(MainWindow._start_structured_recommendation)
    assert "capture_runtime_state_snapshot" in source and "build_runtime_advice_state_projection" in source
    assert 'battle_input["runtime_advice_state"]' in source and "runtime_fingerprint=runtime_projection" in source
    assert "runtime_fingerprint" not in inspect.getsource(build_turn_snapshot_from_battle_input)
