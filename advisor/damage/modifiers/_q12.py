from __future__ import annotations

from advisor.damage.q12 import Q12_ONE


MUL_2_25 = 9216
MUL_2_0 = 8192
MUL_1_5 = 6144
MUL_1_3 = 5325
MUL_0_75 = 3072
MUL_0_5 = 2048


def q12_mul(value_q12: int, multiplier_q12: int) -> int:
    """Multiply two Q12 values using integer floor semantics."""
    return (value_q12 * multiplier_q12) // Q12_ONE
