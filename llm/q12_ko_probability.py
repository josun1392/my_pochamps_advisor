"""Exact cumulative Formula Q12 KO probabilities from retained damage rolls."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from llm.q12_ko_interpretation import resolve_exact_defender_current_hp


_HORIZONS = ((1, "ohko_result"), (2, "two_hko_result"), (3, "three_hko_result"))


def _exact_rolls(mechanics_result: Mapping[str, Any]) -> tuple[int, ...] | None:
    rolls = mechanics_result.get("exact_damage_rolls")
    if not isinstance(rolls, tuple) or not rolls:
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in rolls):
        return ()
    damage_range = mechanics_result.get("damage_range")
    if not isinstance(damage_range, Mapping) or (damage_range.get("minimum"), damage_range.get("maximum")) != (min(rolls), max(rolls)):
        return ()
    return rolls


def _probability_by_turns(*, rolls: tuple[int, ...], current_hp: int, turns: int) -> Fraction:
    totals = Counter({0: 1})
    outcomes = Counter(rolls)
    for _ in range(turns):
        next_totals: Counter[int] = Counter()
        for total, total_count in totals.items():
            for damage, outcome_count in outcomes.items():
                next_totals[total + damage] += total_count * outcome_count
        totals = next_totals
    return Fraction(sum(count for total, count in totals.items() if total >= current_hp), len(rolls) ** turns)


def _fraction_evidence(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def evaluate_exact_q12_ko_probability(*, mechanics_result: Mapping[str, Any], current_hp_context: Any, defender_side: str, ko_interpretation: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Derive formula-only exact cumulative probabilities without affecting usability."""
    if defender_side not in {"self", "opponent"}:
        raise ValueError("invalid defender side")
    if mechanics_result.get("status") != "known":
        return None
    if mechanics_result.get("damage_model") != "single_hit_formula":
        return None
    rolls = _exact_rolls(mechanics_result)
    if rolls is None:
        return {"ko_probability_supportability": "unsupported_mechanic", "reason": "exact_damage_rolls"}
    if not rolls:
        return {"ko_probability_supportability": "unsupported_mechanic", "reason": "exact_damage_rolls"}
    hp = resolve_exact_defender_current_hp(current_hp_context=current_hp_context, defender_side=defender_side)
    if hp is None:
        return None
    if "ko_supportability" in hp:
        return {"ko_probability_supportability": hp["ko_supportability"], **{key: value for key, value in hp.items() if key != "ko_supportability"}}
    probabilities = {turns: _probability_by_turns(rolls=rolls, current_hp=hp["current_hp"], turns=turns) for turns, _ in _HORIZONS}
    if isinstance(ko_interpretation, Mapping) and ko_interpretation.get("ko_supportability") == "complete":
        for turns, label_key in _HORIZONS:
            label = ko_interpretation.get(label_key)
            probability = probabilities[turns]
            if (label == "guaranteed" and probability != 1) or (label == "possible" and not 0 < probability < 1) or (label == "no" and probability != 0):
                return {"ko_probability_supportability": "unsupported_mechanic", "reason": "deterministic_ko_inconsistency"}
    return {
        "ko_probability_supportability": "complete",
        "defender_hp_authority": hp["defender_hp_authority"],
        "damage_roll_distribution_basis": "server_owned_exact_damage_rolls",
        "probability_model": "independent_repeated_noncritical_damage_rolls",
        **{f"ko_by_{turns}": _fraction_evidence(probabilities[turns]) for turns, _ in _HORIZONS},
    }
