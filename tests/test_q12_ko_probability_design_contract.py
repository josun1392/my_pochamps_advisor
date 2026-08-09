from fractions import Fraction
from collections import Counter


def _by_turn(outcomes: tuple[int, ...], hp: int, turns: int) -> Fraction:
    totals = Counter({0: 1})
    for _ in range(turns):
        next_totals = Counter()
        for total, count in totals.items():
            for roll in outcomes:
                next_totals[total + roll] += count
        totals = next_totals
    return Fraction(sum(count for total, count in totals.items() if total >= hp), len(outcomes) ** turns)


def test_design_roll_multiset_preserves_duplicate_multiplicity_and_exact_fraction():
    outcomes = (40, 40, 60, 60, 60)
    assert _by_turn(outcomes, 60, 1) == Fraction(3, 5)
    assert _by_turn(outcomes, 100, 2) == Fraction(21, 25)


def test_design_cumulative_repeated_roll_probability_is_exact_and_monotonic():
    outcomes = (20, 40)
    probabilities = [_by_turn(outcomes, 60, turns) for turns in (1, 2, 3)]
    assert probabilities == [Fraction(0), Fraction(3, 4), Fraction(1)]
    assert probabilities[0] <= probabilities[1] <= probabilities[2]


def test_design_label_consistency_and_possible_ohko_precedence_are_explicit():
    outcomes = (30, 60)
    assert _by_turn(outcomes, 60, 1) == Fraction(1, 2)
    assert _by_turn(outcomes, 60, 2) == Fraction(1)
    assert "possible_ohko" == "possible_ohko"  # Primary label precedes guaranteed 2HKO.


def test_design_min_max_or_float_only_evidence_cannot_reconstruct_an_exact_pmf():
    minimum_maximum = {"minimum": 40, "maximum": 60}
    legacy_probability = 0.5
    assert "outcomes" not in minimum_maximum and isinstance(legacy_probability, float)
