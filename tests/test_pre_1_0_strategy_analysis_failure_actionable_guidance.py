from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.widgets.guided_turn_workspace import GuidedTurnWorkspace
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _prompt(readiness: dict) -> str:
    return MainWindow._guided_strategy_failure_prompt(SimpleNamespace(_guided_readiness=readiness))


def test_failure_guidance_classifies_existing_readiness_without_raw_bridge_reason() -> None:
    actionable = _prompt({
        "status": "incomplete",
        "missing": [{"label": "Current HP needed", "action": "current_hp"}],
        "unsupported": [],
    })
    assert "현재 정보만으로는 분석을 완료하기 어렵습니다" in actionable
    assert "현재 HP" in actionable
    assert "알고 있다면 입력" in actionable
    assert "모르면 그대로" in actionable

    non_actionable = _prompt({
        "status": "incomplete",
        "missing": [{"label": "Required deterministic authority is unavailable", "action": None}],
        "unsupported": [],
    })
    assert "분석 제한 · 추가 정보 미확인" in non_actionable
    assert "현재 직접 입력할 수 없는 정보" in non_actionable
    assert "다른 기술을 검토" in non_actionable
    assert "현재 판단으로 진행" in non_actionable

    unsupported = _prompt({"status": "unsupported", "missing": [], "unsupported": ["x"]})
    assert "아직 완전히 지원되지 않습니다" in unsupported
    assert "정보가 확인되지" not in unsupported

    ready = _prompt({"status": "ready", "missing": [], "unsupported": []})
    assert "필요한 정보는 확인되었지만" in ready
    assert "정보가 부족" not in ready

    unavailable = _prompt({"status": "unavailable"})
    assert "현재 상태에서는 분석을 완료하지 못했습니다" in unavailable
    assert "지원되지" not in unavailable


def test_actionable_failure_reuses_guided_readiness_cta_and_unknown_escape() -> None:
    _app()
    stage = GuidedTurnWorkspace()
    harness = SimpleNamespace(_guided_readiness={
        "status": "incomplete",
        "missing": [{"label": "Current HP needed", "action": "current_hp"}],
        "unsupported": [],
    })
    message, action, label = MainWindow._guided_readiness_prompt(harness)
    emitted: list[str] = []
    stage.readiness_input_requested.connect(emitted.append)
    stage.set_readiness(message, action, label, basis=("session", 1), allow_unknown=True)

    assert "현재 HP" in stage.readiness_label.text()
    assert stage.readiness_input_button.text() == "현재 HP 입력"
    assert not stage.readiness_input_button.isHidden()
    assert not stage.readiness_skip_button.isHidden()

    stage.readiness_input_button.click()
    assert emitted == ["current_hp"]

    stage.readiness_skip_button.click()
    assert emitted == ["current_hp"]
    assert stage.readiness_input_button.isHidden()
    assert stage.readiness_skip_button.isHidden()
    assert "모르는 정보는 입력하지 않아도 됩니다" in stage.readiness_label.text()
    stage.close()


def test_non_actionable_incomplete_has_unknown_escape_without_fake_input_route() -> None:
    _app()
    stage = GuidedTurnWorkspace()
    harness = SimpleNamespace(_guided_readiness={
        "status": "incomplete",
        "missing": [{"label": "Required deterministic authority is unavailable", "action": None}],
        "unsupported": [],
    })
    message, action, label = MainWindow._guided_readiness_prompt(harness)
    basis = ("session", 1)
    stage.set_readiness(message, action, label, basis=basis, allow_unknown=True)
    assert action is None
    assert "추가 정보 미확인" in stage.readiness_label.text()
    assert "현재 직접 입력할 수 없는 정보" in stage.readiness_label.text()
    assert "다른 기술을 검토" in stage.readiness_label.text()
    assert stage.readiness_input_button.isHidden()
    assert not stage.readiness_skip_button.isHidden()

    stage.readiness_skip_button.click()
    assert stage._dismissed_readiness_basis == basis
    assert stage.readiness_input_button.isHidden()
    assert stage.readiness_skip_button.isHidden()
    assert "모르는 정보는 입력하지 않아도 됩니다" in stage.readiness_label.text()
    stage.close()


def test_non_actionable_unknown_escape_is_presentation_only_for_live_session() -> None:
    app = _app()
    window = MainWindow()
    window.my_team_column.panels[0].pokemon_view = SimpleNamespace(en="garchomp")
    window.opponent_team_column.panels[0].pokemon_view = SimpleNamespace(en="pikachu")
    session_id = window.begin_new_battle()
    assert session_id == "ui-session-1"
    manager = window._observation_runtime_session_manager
    assert manager is not None
    guided = window.center_column.guided_turn_workspace
    basis = ("ui-session-1", 1, "sparse")

    before = {
        "runtime": manager.capture_runtime_state_snapshot(session_id),
        "observations": manager.read_collection_snapshot(),
        "ledger": manager.read_applied_ledger(),
        "decision_owners": deepcopy(window._c6_decision_capture_owners),
        "transition_owners": deepcopy(window._c6_transition_capture_owners),
        "hp_confirmations": deepcopy(window._current_hp_confirmations),
    }

    guided.set_readiness(
        "추가 정보 미확인 · 현재 직접 입력할 수 없는 정보입니다.",
        None,
        None,
        basis=basis,
        allow_unknown=True,
    )
    guided.readiness_skip_button.click()
    app.processEvents()

    after = {
        "runtime": manager.capture_runtime_state_snapshot(session_id),
        "observations": manager.read_collection_snapshot(),
        "ledger": manager.read_applied_ledger(),
        "decision_owners": deepcopy(window._c6_decision_capture_owners),
        "transition_owners": deepcopy(window._c6_transition_capture_owners),
        "hp_confirmations": deepcopy(window._current_hp_confirmations),
    }
    assert after == before
    assert guided._dismissed_readiness_basis == basis
    assert guided.readiness_skip_button.isHidden()
    window.close()


def test_unknown_escape_is_only_offered_for_incomplete_status() -> None:
    _app()
    stage = GuidedTurnWorkspace()
    for readiness in (
        {"status": "unsupported", "missing": [], "unsupported": ["x"]},
        {"status": "ready", "missing": [], "unsupported": []},
        {"status": "unavailable", "missing": [], "unsupported": []},
    ):
        harness = SimpleNamespace(_guided_readiness=readiness)
        message, action, label = MainWindow._guided_readiness_prompt(harness)
        stage.set_readiness(message, action, label, basis=("session", readiness["status"]), allow_unknown=False)
        assert stage.readiness_input_button.isHidden()
        assert stage.readiness_skip_button.isHidden()
    stage.close()


def test_internal_authority_label_is_plain_language_only() -> None:
    assert LLMAdvicePanel._readiness_user_label(
        "Required deterministic authority is unavailable", None
    ) == "현재 직접 확인할 수 없는 추가 전투 정보"
    assert "권한" not in LLMAdvicePanel._readiness_user_label(
        "Required deterministic authority is unavailable", None
    )
