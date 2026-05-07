from advisor.probability.composer import KOProbability, compose_turn, compute_ko_probability, compute_ko_probability_with_effects, guaranteed_ko_turn
from advisor.probability.multi_hit import (
    compute_multihit_damage_distribution,
    compute_multihit_distribution,
    multihit_damage_distribution,
    nhko_chance,
    nhko_curve,
)
from advisor.probability.residual import ResidualSpec, apply_residual_damage
from advisor.probability.rolls import ROLL_FACTORS_Q12, roll_distribution, roll_outcomes
from advisor.probability.single_hit import crit_integrated_ko_chance, single_hit_ko_chance

__all__ = [
    "KOProbability",
    "ROLL_FACTORS_Q12",
    "ResidualSpec",
    "apply_residual_damage",
    "compose_turn",
    "compute_ko_probability",
    "compute_ko_probability_with_effects",
    "compute_multihit_damage_distribution",
    "compute_multihit_distribution",
    "crit_integrated_ko_chance",
    "guaranteed_ko_turn",
    "multihit_damage_distribution",
    "nhko_chance",
    "nhko_curve",
    "roll_distribution",
    "roll_outcomes",
    "single_hit_ko_chance",
]
