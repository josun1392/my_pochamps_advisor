from advisor.damage.ability_modifiers import get_atk_ability_modifier

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
