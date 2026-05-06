import pytest
from advisor.damage.status_effects import (
    burn_atk_modifier,
    frostbite_spa_modifier,
    paralysis_spe_modifier,
    Q12_ONE, Q12_HALF,
)

def test_burn_reduces_atk_without_guts():
    assert burn_atk_modifier("burn", "static") == Q12_HALF

def test_burn_with_guts_no_drop():
    assert burn_atk_modifier("burn", "guts") == Q12_ONE

def test_frostbite_reduces_spa():
    assert frostbite_spa_modifier("frostbite") == Q12_HALF
    assert frostbite_spa_modifier("healthy") == Q12_ONE

def test_paralysis_with_quick_feet_no_drop():
    assert paralysis_spe_modifier("paralysis", "quick-feet") == Q12_ONE
    assert paralysis_spe_modifier("paralysis", "static") == Q12_HALF
