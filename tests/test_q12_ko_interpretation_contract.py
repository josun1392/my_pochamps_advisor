from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_candidate_contract import evaluate_move_candidate
from llm.advisor_client import _format_validated_selected_candidate_summary
from llm.q12_ko_interpretation import evaluate_q12_ko_interpretation
from tests.test_current_type_q12_integration_contract import _Species, _snapshot


def _hp(side: str, current: int, maximum: int) -> dict[str, object]:
    return {"side": side, "current_hp": current, "maximum_hp": maximum, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"}


def _mechanics(minimum: int = 35, maximum: int = 40, model: str = "single_hit_formula") -> dict[str, object]:
    return {"status": "known", "damage_model": model, "damage_range": {"minimum": minimum, "maximum": maximum}}


@pytest.mark.parametrize(
    ("damage", "expected"),
    [
        ((60, 70), ("guaranteed", "guaranteed", "guaranteed", "guaranteed_ohko")),
        ((35, 60), ("possible", "guaranteed", "guaranteed", "possible_ohko")),
        ((30, 35), ("no", "guaranteed", "guaranteed", "guaranteed_2hko")),
        ((20, 35), ("no", "possible", "guaranteed", "possible_2hko")),
        ((20, 20), ("no", "no", "guaranteed", "guaranteed_3hko")),
        ((10, 20), ("no", "no", "possible", "possible_3hko")),
        ((10, 15), ("no", "no", "no", "no_ko_within_supported_horizon")),
    ],
)
def test_ko_interpreter_uses_server_owned_min_max_with_canonical_precedence(damage, expected):
    result = evaluate_q12_ko_interpretation(mechanics_result=_mechanics(*damage), current_hp_context={"current_hp": [_hp("opponent", 60, 100)]}, defender_side="opponent")
    assert result is not None
    assert (result["ohko_result"], result["two_hko_result"], result["three_hko_result"], result["primary_ko_label"]) == expected
    assert result["ko_supportability"] == "complete"


@pytest.mark.parametrize("model", ["single_hit_formula", "fixed_hit_formula", "level_based_fixed"])
def test_ko_interpreter_supports_only_existing_exact_total_damage_models(model):
    result = evaluate_q12_ko_interpretation(mechanics_result=_mechanics(50, 50, model), current_hp_context={"current_hp": [_hp("opponent", 50, 100)]}, defender_side="opponent")
    assert result is not None and result["primary_ko_label"] == "guaranteed_ohko"
    unsupported = evaluate_q12_ko_interpretation(mechanics_result=_mechanics(50, 50, "variable_multi_hit"), current_hp_context={"current_hp": [_hp("opponent", 50, 100)]}, defender_side="opponent")
    assert unsupported == {"ko_supportability": "not_applicable", "reason": "unsupported_damage_model"}


def test_ko_hp_authority_is_exact_target_side_only_and_omission_preserves_compatibility():
    mechanics = _mechanics()
    assert evaluate_q12_ko_interpretation(mechanics_result=mechanics, current_hp_context=None, defender_side="opponent") is None
    assert evaluate_q12_ko_interpretation(mechanics_result=mechanics, current_hp_context={"current_hp": [{"side": "opponent", "state": "unknown"}]}, defender_side="opponent") == {"ko_supportability": "insufficient_context", "missing_inputs": ["opponent.current_hp"]}
    assert evaluate_q12_ko_interpretation(mechanics_result=mechanics, current_hp_context={"current_hp": [_hp("self", 1, 100)]}, defender_side="opponent") == {"ko_supportability": "insufficient_context", "missing_inputs": ["opponent.current_hp"]}
    assert evaluate_q12_ko_interpretation(mechanics_result=mechanics, current_hp_context={"current_hp": [{**_hp("opponent", 101, 100)}]}, defender_side="opponent") == {"ko_supportability": "unsupported_mechanic", "reason": "defender_hp_authority"}


def test_ko_target_fainted_and_upstream_damage_boundaries_do_not_change_candidate_usability():
    assert evaluate_q12_ko_interpretation(mechanics_result=_mechanics(), current_hp_context={"current_hp": [_hp("opponent", 0, 100)]}, defender_side="opponent") == {"ko_supportability": "not_applicable", "reason": "target_already_fainted"}
    assert evaluate_q12_ko_interpretation(mechanics_result={"status": "insufficient_context"}, current_hp_context={"current_hp": [_hp("opponent", 60, 100)]}, defender_side="opponent") == {"ko_supportability": "not_applicable", "reason": "damage_supportability"}


def test_candidate_attaches_ko_evidence_after_direct_damage_without_changing_partial_damage_status():
    turn_snapshot = _snapshot()
    battle_snapshot = {"current_hp_context": {"current_hp": [_hp("self", 100, 100), _hp("opponent", 60, 100)]}}
    candidate = evaluate_move_candidate(
        slot_index=0, move="flamethrower", battle_snapshot=battle_snapshot,
        repositories={"flamethrower": {"move_id": "flamethrower", "category": "special", "power": 90, "type": "fire"}},
        turn_snapshot=turn_snapshot, selectable_moves=("flamethrower",), species_repository=_Species(),
    )
    interpretation = candidate["mechanics_result"]["ko_interpretation"]
    assert candidate["status"] == "partial"
    assert interpretation["ko_supportability"] == "complete"
    assert interpretation["defender_hp_authority"] == "exact_current_hp"


def test_blocked_candidate_short_circuits_before_ko_evidence_and_selected_presentation_is_bounded():
    blocked = {"move_success": {"status": "blocked"}, "mechanics_result": {"status": "unavailable"}}
    assert "ko_interpretation" not in blocked["mechanics_result"]
    evidence = {"mechanics_result": {**_mechanics(35, 60), "ko_interpretation": {"ko_supportability": "complete", "primary_ko_label": "possible_ohko"}}}
    selected = {"selected_action": {"move": "flamethrower"}, "explanation_code": "clear_ranked_winner", "evidence": evidence}
    lines = _format_validated_selected_candidate_summary(selected)
    assert "KO 판정: 난수 1타 가능" in lines
    assert not any("확률" in line or "%" in line for line in lines)
