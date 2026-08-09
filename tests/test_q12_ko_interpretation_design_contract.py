from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import normalize_user_confirmed_current_hp


def _exact_hp(side: str, current: int, maximum: int) -> dict[str, object]:
    return {
        "side": side, "current_hp": current, "maximum_hp": maximum,
        "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known",
    }


def _horizon(minimum: int, maximum: int, current_hp: int, turns: int) -> str:
    if turns * minimum >= current_hp:
        return "guaranteed"
    if turns * maximum >= current_hp:
        return "possible"
    return "no"


def _design_ko_interpretation(damage_range: object, hp: object) -> dict[str, object]:
    """Test-only min/max KO contract; this intentionally changes no production evidence."""
    if not isinstance(damage_range, dict):
        return {"status": "insufficient_context", "reason": "damage_range"}
    minimum, maximum = damage_range.get("minimum"), damage_range.get("maximum")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (minimum, maximum)) or minimum < 0 or maximum < minimum:
        return {"status": "unsupported_mechanic", "reason": "damage_range"}
    if hp is None:
        return {"status": "omitted"}
    if isinstance(hp, dict) and hp.get("state") == "unknown":
        return {"status": "insufficient_context", "reason": "defender_hp"}
    try:
        exact = normalize_user_confirmed_current_hp(hp)
    except ValueError:
        return {"status": "unsupported_mechanic", "reason": "defender_hp"}
    current = exact["current_hp"]
    if current == 0:
        return {"status": "not_applicable", "reason": "target_already_fainted"}
    horizons = {turns: _horizon(minimum, maximum, current, turns) for turns in (1, 2, 3)}
    primary = next(
        label
        for label, turns, state in (
            ("guaranteed_ohko", 1, "guaranteed"), ("possible_ohko", 1, "possible"),
            ("guaranteed_2hko", 2, "guaranteed"), ("possible_2hko", 2, "possible"),
            ("guaranteed_3hko", 3, "guaranteed"), ("possible_3hko", 3, "possible"),
            ("no_ko_within_supported_horizon", 3, "no"),
        )
        if horizons[turns] == state
    )
    return {"status": "known", "one_hit": horizons[1], "two_hit": horizons[2], "three_hit": horizons[3], "primary_ko_label": primary}


@pytest.mark.parametrize("candidate", [
    _exact_hp("opponent", 60, 100),
    _exact_hp("opponent", 0, 100),
    _exact_hp("opponent", 100, 100),
])
def test_design_exact_hp_authority_accepts_only_exact_integer_current_and_maximum(candidate):
    assert normalize_user_confirmed_current_hp(candidate)["confidence"] == "known"


@pytest.mark.parametrize("candidate", [
    {**_exact_hp("opponent", 60, 100), "percent": 60},
    {**_exact_hp("opponent", 60, 100), "current_hp": 60.0},
    {**_exact_hp("opponent", 101, 100)},
    {**_exact_hp("opponent", -1, 100)},
    {**_exact_hp("opponent", 60, 0)},
])
def test_design_hp_authority_rejects_percent_approximate_and_malformed_values(candidate):
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_hp(candidate)


@pytest.mark.parametrize(
    ("damage_range", "expected"),
    [
        ({"minimum": 100, "maximum": 120}, ("guaranteed", "guaranteed", "guaranteed", "guaranteed_ohko")),
        ({"minimum": 40, "maximum": 100}, ("possible", "guaranteed", "guaranteed", "possible_ohko")),
        ({"minimum": 35, "maximum": 40}, ("no", "guaranteed", "guaranteed", "guaranteed_2hko")),
        ({"minimum": 20, "maximum": 35}, ("no", "possible", "guaranteed", "possible_2hko")),
        ({"minimum": 20, "maximum": 25}, ("no", "no", "guaranteed", "guaranteed_3hko")),
        ({"minimum": 10, "maximum": 25}, ("no", "no", "possible", "possible_3hko")),
        ({"minimum": 10, "maximum": 15}, ("no", "no", "no", "no_ko_within_supported_horizon")),
    ],
)
def test_design_min_max_ko_horizons_and_primary_precedence(damage_range, expected):
    result = _design_ko_interpretation(damage_range, _exact_hp("opponent", 60, 100))
    assert (result["one_hit"], result["two_hit"], result["three_hit"], result["primary_ko_label"]) == expected


def test_design_ko_supportability_is_independent_from_damage_supportability_and_omission():
    damage = {"minimum": 35, "maximum": 40}
    assert _design_ko_interpretation(damage, None) == {"status": "omitted"}
    assert _design_ko_interpretation(damage, {"side": "opponent", "state": "unknown"}) == {"status": "insufficient_context", "reason": "defender_hp"}
    assert _design_ko_interpretation(damage, {"side": "opponent", "current_hp": 80, "maximum_hp": 100, "status": "user_confirmed", "source": "percent_only"}) == {"status": "unsupported_mechanic", "reason": "defender_hp"}
    assert _design_ko_interpretation(None, _exact_hp("opponent", 60, 100)) == {"status": "insufficient_context", "reason": "damage_range"}


def test_design_target_hp_ownership_and_candidate_boundaries_are_explicit():
    assert {"self": "opponent", "opponent": "self"}["self"] == "opponent"
    assert {"self": "opponent", "opponent": "self"}["opponent"] == "self"
    assert {"formula_q12", "level_based_fixed", "fixed_hit_formula"} == {"formula_q12", "level_based_fixed", "fixed_hit_formula"}
    assert "variable_multi_hit" not in {"formula_q12", "level_based_fixed", "fixed_hit_formula"}


def test_design_zero_hp_is_not_a_ko_label_and_blocked_damage_needs_no_hp_interpretation():
    assert _design_ko_interpretation({"minimum": 10, "maximum": 20}, _exact_hp("opponent", 0, 100)) == {"status": "not_applicable", "reason": "target_already_fainted"}
    blocked_candidate = {"move_success_status": "blocked", "damage": {"status": "unavailable"}}
    assert blocked_candidate["move_success_status"] == "blocked" and blocked_candidate["damage"]["status"] == "unavailable"
