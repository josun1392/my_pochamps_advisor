from PySide6.QtWidgets import QApplication
import inspect
from types import SimpleNamespace

from llm.advisor_recommendation_readiness import build_recommendation_readiness
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _prepared(*candidates):
    return {"status": "ready", "candidates": list(candidates)}


def test_readiness_projects_only_canonical_missing_inputs_and_known_routes():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["attacker.current_hp", "field.weather"]}, "action_order": {"status": "insufficient_context", "missing_inputs": ["opponent.grounded"]}},
        {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["attacker.current_hp"]}},
    ))
    assert readiness["status"] == "incomplete"
    assert readiness["missing"] == [
        {"path": "attacker.current_hp", "label": "Current HP needed", "action": "current_hp"},
        {"path": "field.weather", "label": "Weather not confirmed", "action": "current_field_state"},
        {"path": "opponent.grounded", "label": "Groundedness not confirmed", "action": "current_field_state"},
    ]
    assert readiness["action"] == "current_hp"


def test_readiness_distinguishes_unsupported_and_ignores_irrelevant_unknown_state():
    ready = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "known"}, "unavailable_reasons": ["unrelated_unknown"]},
    ))
    assert ready == {"status": "ready", "missing": [], "unsupported": [], "action": None}

    unsupported = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "unsupported_mechanic", "unsupported_reason": "status_move"}},
    ))
    assert unsupported["status"] == "unsupported"
    assert unsupported["missing"] == []

    item = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["defender.item"]}},
    ))
    assert item["missing"] == [{"path": "defender.item", "label": "Held item unknown", "action": "current_item"}]
    assert item["action"] == "current_item"


def test_panel_exposes_readiness_and_routes_only_existing_confirmation_actions():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.readiness_input_requested.connect(emitted.append)
    panel.set_recommendation_readiness({"status": "incomplete", "missing": [{"label": "Current type needed", "action": "current_type"}], "unsupported": [], "action": "current_type"})
    assert "Current type needed" in panel.readiness_label.text()
    assert panel.readiness_input_button.isVisible() is False  # parent is not shown
    panel._request_readiness_input()
    assert emitted == ["current_type"]
    panel.clear_recommendation_readiness()
    assert "has not been checked" in panel.readiness_label.text()


def test_panel_groups_multiple_readiness_gaps_with_distinct_routes_and_unavailable_reasons():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.readiness_input_requested.connect(emitted.append)
    panel.set_recommendation_readiness({
        "status": "incomplete",
        "missing": [
            {"label": "Current HP needed", "action": "current_hp"},
            {"label": "Held item unknown", "action": "current_item"},
            {"label": "Toxic progression authority missing", "action": None},
            {"label": "Current HP needed", "action": "current_hp"},
        ],
        "unsupported": ["This selected mechanic is not supported yet"],
        "action": "current_item",
    })
    text = panel.readiness_label.text()
    assert "Can confirm: Current HP needed; Held item unknown" in text
    assert "Still unavailable: Toxic progression authority missing" in text
    assert "Unsupported: This selected mechanic is not supported yet" in text
    assert panel.readiness_input_button.text() == "Open: Current HP needed"
    assert [button.text() for button in panel._readiness_extra_input_buttons] == ["Open: Held item unknown"]
    panel._request_readiness_input()
    panel._readiness_extra_input_buttons[0].click()
    assert emitted == ["current_hp", "current_item"]
    panel.clear_recommendation_readiness()
    assert panel._readiness_extra_input_buttons == []


def test_main_window_readiness_uses_frozen_preparation_without_a_provider_call():
    source = inspect.getsource(MainWindow._check_structured_recommendation_readiness)
    assert "prepare_ui_recommendation_cycle" in source
    assert "build_recommendation_readiness" in source
    assert "run_structured_ui_recommendation" not in source


def test_item_shortcut_reuses_existing_item_profile_flow_with_identity_check():
    source = inspect.getsource(MainWindow._open_readiness_input)
    assert 'action == "current_item"' in source
    assert 'self._on_item_profile_requested("team_my", slot_index)' in source
    assert "current_session != session_id" in source
    assert 'self.selected_slots.get("team_my") != slot_index' in source
    assert "getattr(view, \"en\", None) != pokemon_id" in source
    assert "self._check_structured_recommendation_readiness()" in source


def test_existing_readiness_routes_refresh_the_current_canonical_projection():
    source = inspect.getsource(MainWindow._open_readiness_input)
    assert "handler()" in source
    assert 'getattr(self, "_recommendation_readiness_owner", None) is not None' in source
    assert "self._check_structured_recommendation_readiness()" in source


def test_paired_hp_apply_validates_each_owner_and_filters_stale_side_before_snapshot():
    apply_source = inspect.getsource(MainWindow._open_current_hp_dialog)
    payload_source = inspect.getsource(MainWindow._build_llm_battle_input)
    assert "dialog.current_hp_confirmations" in apply_source
    assert "owner != self._current_hp_owner_for_side(entry[\"side\"])" in apply_source
    assert "owner != self._current_hp_owner_for_side(side)" in payload_source


def test_hp_owner_identity_changes_when_a_replacement_occupies_the_same_side():
    panels = {
        ("team_my", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="pikachu")),
        ("team_enemy", 1): SimpleNamespace(pokemon_view=SimpleNamespace(en="eevee")),
    }
    window = SimpleNamespace(
        selected_slots={"team_my": 0, "team_enemy": 1},
        _active_session_id=lambda: "s",
        _slot_panel=lambda column, slot: panels[(column, slot)],
    )
    owner = MainWindow._current_hp_owner_for_side(window, "self")
    panels[("team_my", 0)].pokemon_view = SimpleNamespace(en="raichu")
    assert owner == ("s", 0, "pikachu")
    assert MainWindow._current_hp_owner_for_side(window, "self") == ("s", 0, "raichu")
