from __future__ import annotations

import random
from typing import Sequence


class RNG:
    """Seedable RNG wrapper matching Showdown's high-level interface shape.

    This uses Python's Mersenne Twister, not Pokemon Showdown's sim/prng.ts
    implementation. Bit-level PRNG parity is out of scope for PR #3.4-D.
    """

    def __init__(self, seed: int | None = None):
        self._r = random.Random(seed)

    def random(self, n: int) -> int:
        """Return an integer in [0, n), matching Showdown random(n)."""
        if n <= 0:
            raise ValueError("n must be positive")
        return self._r.randrange(n)

    def weighted_choice(self, weights: Sequence[int]) -> int:
        """Return an index sampled proportional to integer weights."""
        total = sum(weights)
        if total <= 0:
            raise ValueError("weights must sum to positive value")
        roll = self._r.randrange(total)
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if roll < cumulative:
                return i
        return len(weights) - 1
