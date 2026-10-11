from copy import deepcopy
import pytest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
import ui.main_window as main_window_module
from ui.main_window import MainWindow
from ui.widgets.battle_decision_phase_dialog import BattleDecisionPhaseDialog
from llm.advisor_battle_decision_phase import KEY
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from scripts.verify_showdown_integration import fixture_snapshot


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_phase_dialog_requires_explicit_phase_turn_and_replacement_side(app):
    dialog = BattleDecisionPhaseDialog()
    assert dialog.confirmation is None
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog.phase_combo.setCurrentIndex(2)
    dialog.turn_spin.setValue(1)
    assert dialog.confirmation is None
    dialog.side_combo.setCurrentIndex(1)
    assert dialog.confirmation == {"phase": "faint_replacement", "requesting_sides": ["self"], "turn_number": 1}
    dialog.phase_combo.setCurrentIndex(1)
    assert dialog.confirmation["requesting_sides"] == ["self", "opponent"]
    dialog.close()


@pytest.mark.parametrize("accept", [False, True])
def test_phase_menu_routes_explicit_confirmation_through_runtime(app, monkeypatch, accept):
    snapshot = fixture_snapshot()
    owner = BattleObservationRuntimeSessionManager.create(snapshot["session_id"], snapshot["state"])["manager"]
    window = MainWindow()
    window._observation_runtime_session_manager = owner
    monkeypatch.setattr(MainWindow, "_active_session_id", lambda self: snapshot["session_id"])
    retired = []
    monkeypatch.setattr(window, "_retire_advice_presentation_authority", lambda: retired.append(True))
    class Confirm:
        def __init__(self, **kwargs): self.confirmation = {"phase": "move_selection", "requesting_sides": ["self", "opponent"], "turn_number": 1}
        def exec(self): return QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected
    monkeypatch.setattr(main_window_module, "BattleDecisionPhaseDialog", Confirm)
    before = deepcopy(owner.capture_runtime_state_snapshot(snapshot["session_id"]))
    window._record_battle_decision_phase_action.trigger()
    after = owner.capture_runtime_state_snapshot(snapshot["session_id"])
    if accept:
        assert after["state"][KEY]["phase"] == "move_selection"
        assert retired == [True] and len(owner.read_applied_ledger()) == 1
        window._record_battle_decision_phase_action.trigger()
        assert retired == [True] and len(owner.read_applied_ledger()) == 1
    else:
        assert after == before and retired == []
    assert window._showdown_shadow_worker is None
    window.close()
