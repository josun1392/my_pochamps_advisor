from advisor.damage.ability_modifiers import (
    get_atk_ability_modifier,
    get_def_ability_modifier,
    get_final_def_ability_modifier,
)

def test_huge_power_doubles_physical():
    assert get_atk_ability_modifier("huge-power", "physical") == 8192

def test_huge_power_no_effect_on_special():
    assert get_atk_ability_modifier("huge-power", "special") == 4096

def test_pure_power_doubles_physical():
    assert get_atk_ability_modifier("pure-power", "physical") == 8192

def test_hustle_x15_physical():
    assert get_atk_ability_modifier("hustle", "physical") == 6144

def test_hustle_no_effect_on_special():
    assert get_atk_ability_modifier("hustle", "special") == 4096

def test_unknown_ability_returns_neutral():
    assert get_atk_ability_modifier("static", "physical") == 4096

def test_fur_coat_halves_physical():
    assert get_def_ability_modifier("fur-coat", "physical") == 2048

def test_fur_coat_no_effect_special():
    assert get_def_ability_modifier("fur-coat", "special") == 4096

def test_ice_scales_halves_special():
    assert get_def_ability_modifier("ice-scales", "special") == 2048

def test_ice_scales_no_effect_physical():
    assert get_def_ability_modifier("ice-scales", "physical") == 4096

def test_multiscale_full_hp_halves():
    assert get_final_def_ability_modifier("multiscale", 1.0) == 2048

def test_multiscale_not_full_no_effect():
    assert get_final_def_ability_modifier("multiscale", 0.99) == 4096

def test_shadow_shield_full_hp_halves():
    assert get_final_def_ability_modifier("shadow-shield", 1.0) == 2048

def test_unknown_def_ability_returns_neutral():
    assert get_def_ability_modifier("static", "physical") == 4096
