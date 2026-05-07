from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advisor.damage.multihit import MULTIHIT_MOVES
from advisor.probability.composer import compute_ko_probability_with_effects
from advisor.probability.residual import ResidualSpec


ITERATIONS = 100


def run_once():
    return compute_ko_probability_with_effects(
        100,
        900,
        move=MULTIHIT_MOVES["bullet-seed"],
        attacker={},
        residuals=ResidualSpec("burn", 320),
        crit_rate=Fraction(1, 24),
        crit_damage_q12=150,
        max_turns=4,
    )


def main() -> None:
    run_once()
    start = perf_counter()
    for _ in range(ITERATIONS):
        run_once()
    elapsed_ms = (perf_counter() - start) * 1000
    print(f"iterations={ITERATIONS}")
    print(f"total_ms={elapsed_ms:.3f}")
    print(f"per_call_ms={elapsed_ms / ITERATIONS:.3f}")


if __name__ == "__main__":
    main()
