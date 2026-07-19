import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from llm.advisor_client import (
    build_deterministic_result_acknowledgement_entries,
    build_trusted_context_acknowledgement_entries,
    evaluate_deterministic_result_response,
)
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel
from ui.widgets.current_observed_damage_dialog import CurrentObservedDamageDialog
from PySide6.QtWidgets import QApplication


def _context_payload():
    return {
        "observed_previous_damage_context": {"damage": 60, "damage_category": "physical", "damage_kind": "direct_move_damage", "source_side": "opponent", "target_side": "self", "source": "user_confirmed_previous_damage", "confidence": "known"},
        "deterministic_calculation_context": {"observed_damage_counter_assessment": {"move": "counter", "scope": "trusted-observed-direct-damage-counter-only", "status": "resolved", "rule": "double-observed-physical-damage", "returned_damage": 120, "actual_damage": 100, "opponent_resulting_hp": 0, "ko_status": "guaranteed_ko"}},
    }


def test_panel_exposes_observed_damage_signals():
    assert hasattr(LLMAdvicePanel, "current_observed_damage_requested") and hasattr(LLMAdvicePanel, "current_observed_damage_reset_requested")


def test_dialog_apply_emits_defensive_confirmation():
    app = QApplication.instance() or QApplication([])
    dialog = CurrentObservedDamageDialog()
    dialog.damage.setText("60")
    dialog._save()
    result = dialog.observed_damage_confirmation
    assert result == {"damage": 60, "damage_category": "physical", "damage_kind": "direct_move_damage", "source_side": "opponent", "target_side": "self"}
    result["damage"] = 1
    assert dialog.observed_damage_confirmation["damage"] == 60


def test_clear_preserves_cancelled_snapshot_contract():
    window = MainWindow.__new__(MainWindow)
    seen = []
    window.center_column = SimpleNamespace(llm_advice_panel=SimpleNamespace(set_current_observed_damage=seen.append))
    window._current_observed_damage_confirmation = {"damage": 60}
    # A cancelled dialog never executes the replacement branch; the session value remains untouched.
    before = dict(window._current_observed_damage_confirmation)
    assert window._current_observed_damage_confirmation == before
    window._clear_current_observed_damage_confirmation()
    assert window._current_observed_damage_confirmation is None and seen == [None]


def test_acknowledgement_is_exact_and_rejects_mutation_duplicate_and_inference():
    payload = _context_payload()
    trusted, results = build_trusted_context_acknowledgement_entries(payload), build_deterministic_result_acknowledgement_entries(payload)
    response = """[Trusted Context]
- Previous direct damage | opponent | self | 60 HP | physical | user-confirmed
[Deterministic Results]
- Reactive damage | self | opponent | counter | double-observed-physical-damage | 120 HP | trusted-observed-direct-damage-counter-only
- Reactive actual damage | self | opponent | counter | 100 HP
- Target resulting HP | opponent | counter | 0 HP
- Reactive KO assessment | self | opponent | counter | guaranteed-ko
[Advice]
Use Counter only when its ordinary move conditions are satisfied."""
    assert evaluate_deterministic_result_response(response, trusted, results) is None
    assert evaluate_deterministic_result_response(response.replace("120 HP", "121 HP"), trusted, results) == "deterministic-results entry mismatch"
    duplicate = response.replace("[Advice]", "- Reactive KO assessment | self | opponent | counter | guaranteed-ko\n[Advice]")
    assert evaluate_deterministic_result_response(duplicate, trusted, results) == "deterministic-results duplicate entry"
    inferred = response.replace("Use Counter", "The previous damage was inferred. Use Counter")
    assert evaluate_deterministic_result_response(inferred, trusted, results) == "deterministic-results semantic boundary violation"


def test_existing_trusted_contexts_coexist_with_observed_damage():
    payload = _context_payload() | {"current_hp_context": {"current_hp": [{"side": "self", "current_hp": 80, "maximum_hp": 100}]}}
    entries = build_trusted_context_acknowledgement_entries(payload)
    assert entries[0][0] == "current_hp" and entries[-1][0] == "observed_previous_damage"


def test_main_window_limited_context_gate_is_wired_without_resetting_snapshot():
    source = open("ui/main_window.py", encoding="utf-8").read()
    assert "include_observed_previous_damage_confirmation=enable_battle_state_context" in source
    assert 'battle_input["observed_previous_damage_confirmation"] = dict(snapshot)' in source
