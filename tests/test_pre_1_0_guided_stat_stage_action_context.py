from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from llm.advisor_recommendation_readiness import build_recommendation_readiness
from ui.main_window import MainWindow
from ui.widgets.current_stat_stage_dialog import CurrentStatStageDialog


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("path,side,stat", [
    ("attacker.attack_stage", "self", "attack"),
    ("attacker.special-attack_stage", "self", "special-attack"),
    ("attacker.defense_stage", "self", "defense"),
    ("defender.attack_stage", "opponent", "attack"),
    ("defender.defense_stage", "opponent", "defense"),
    ("defender.special-defense_stage", "opponent", "special-defense"),
])
def test_exact_stage_paths_drive_guided_text_and_dialog_prefill(path, side, stat) -> None:
    _app()
    captured = []
    row = {"path": path, "label": "stage needed", "action": "current_stat_stage"}
    harness = SimpleNamespace(_guided_readiness={"status": "incomplete", "action": "current_stat_stage", "missing": [row]},
                              _current_stat_stage_confirmations={},
                              _open_current_stat_stage_dialog=lambda **kwargs: captured.append(kwargs))
    assert MainWindow._selected_guided_readiness_entry(harness) is row
    message, action, label = MainWindow._guided_readiness_prompt(harness)
    assert action == "current_stat_stage"
    assert label in message and "랭크" in label
    MainWindow._open_readiness_input(harness, action)
    assert captured[-1]["initial_side"] == side
    assert captured[-1]["initial_stat"] == stat
    assert harness._current_stat_stage_confirmations == {}


def test_same_action_uses_winning_missing_row_and_item_priority_is_unchanged() -> None:
    _app()
    captured = []
    rows = [
        {"path": "attacker.boosts", "label": "Attacker stat stages needed", "action": "current_stat_stage"},
        {"path": "defender.defense_stage", "label": "Defender Defense stage needed", "action": "current_stat_stage"},
        {"path": "attacker.attack_stage", "label": "Attacker Attack stage needed", "action": "current_stat_stage"},
    ]
    harness = SimpleNamespace(_guided_readiness={"status": "incomplete", "action": "current_stat_stage", "missing": rows},
                              _current_stat_stage_confirmations={},
                              _open_current_stat_stage_dialog=lambda **kwargs: captured.append(kwargs))
    assert MainWindow._selected_guided_readiness_entry(harness) is rows[1]
    assert "상대 포켓몬의 방어 랭크" in MainWindow._guided_readiness_prompt(harness)[0]
    MainWindow._open_readiness_input(harness, "current_stat_stage")
    assert (captured[-1]["initial_side"], captured[-1]["initial_stat"]) == ("opponent", "defense")

    harness._guided_readiness["missing"].insert(0, {
        "path": "attacker.condition", "label": "Attacker current condition needed", "action": "current_condition"
    })
    assert MainWindow._selected_guided_readiness_entry(harness)["action"] == "current_stat_stage"

    readiness = build_recommendation_readiness(prepared_cycle={"status": "ready", "candidates": [{
        "mechanics_result": {"status": "insufficient_context", "missing_inputs": ["defender.defense_stage", "defender.item"]},
    }]})
    assert readiness["action"] == "current_item"
    assert [row["path"] for row in readiness["missing"]] == ["defender.defense_stage", "defender.item"]
    harness._guided_readiness = readiness
    assert MainWindow._selected_guided_readiness_entry(harness) is readiness["missing"][1]
    message, action, label = MainWindow._guided_readiness_prompt(harness)
    assert action == "current_item"
    assert label == "현재 지닌 도구"
    assert label in message


@pytest.mark.parametrize("selected_action", ["current_condition", "current_hp", "current_type", "current_ability"])
def test_canonical_action_selects_first_matching_row(selected_action) -> None:
    rows = [
        {"path": "defender.defense_stage", "action": "current_stat_stage"},
        {"path": "first", "action": selected_action},
        {"path": "second", "action": selected_action},
    ]
    harness = SimpleNamespace(_guided_readiness={"action": selected_action, "missing": rows})
    assert MainWindow._selected_guided_readiness_entry(harness) is rows[1]


@pytest.mark.parametrize("selected_action", [None, "not_in_missing"])
def test_missing_canonical_action_never_invents_an_action_family(selected_action) -> None:
    harness = SimpleNamespace(_guided_readiness={"action": selected_action, "missing": [
        {"path": "defender.defense_stage", "action": "current_stat_stage"},
    ]})
    assert MainWindow._selected_guided_readiness_entry(harness) is None


def test_generic_or_invalid_prefill_stays_safe_and_only_apply_confirms() -> None:
    _app()
    saved = {("self", "attack"): {"side": "self", "stat": "attack", "stage": 0,
                                   "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}}
    dialog = CurrentStatStageDialog(current_stages=saved, initial_side="opponent", initial_stat="defense")
    assert (dialog.side_combo.currentData(), dialog.stat_combo.currentData(), dialog.stage_spin.value()) == ("opponent", "defense", 0)
    assert "self attack: +0" in dialog.summary_label.text()
    assert dialog.current_stat_stage_confirmation is None
    assert list(saved) == [("self", "attack")]
    dialog.reject()
    assert dialog.current_stat_stage_confirmation is None

    invalid = CurrentStatStageDialog(initial_side="opponent", initial_stat="future-stat")
    assert (invalid.side_combo.currentData(), invalid.stat_combo.currentData()) == ("self", "attack")
    assert invalid.current_stat_stage_confirmation is None
    invalid.reject()

    malformed = CurrentStatStageDialog(initial_side=[], initial_stat="defense")  # type: ignore[arg-type]
    assert (malformed.side_combo.currentData(), malformed.stat_combo.currentData()) == ("self", "attack")
    malformed.reject()

    generic = CurrentStatStageDialog()
    assert (generic.side_combo.currentData(), generic.stat_combo.currentData()) == ("self", "attack")
    generic.reject()

    applied = CurrentStatStageDialog(initial_side="opponent", initial_stat="defense")
    applied.stage_spin.setValue(0)
    applied._save_and_accept()
    assert applied.current_stat_stage_confirmation == {
        "side": "opponent", "stat": "defense", "stage": 0,
        "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known",
    }


def test_generic_stage_missing_has_no_specific_prefill() -> None:
    _app()
    captured = []
    harness = SimpleNamespace(_guided_readiness={"status": "incomplete", "action": "current_stat_stage", "missing": [
        {"path": "attacker.boosts", "label": "Attacker stat stages needed", "action": "current_stat_stage"}
    ]}, _current_stat_stage_confirmations={},
        _open_current_stat_stage_dialog=lambda **kwargs: captured.append(kwargs))
    assert "현재 랭크 변화" in MainWindow._guided_readiness_prompt(harness)[0]
    MainWindow._open_readiness_input(harness, "current_stat_stage")
    assert captured[-1]["initial_side"] is None
    assert captured[-1]["initial_stat"] is None
