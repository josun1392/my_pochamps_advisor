from advisor.damage.ability_modifiers import (
    get_atk_ability_modifier,
    get_bp_ability_modifier,
    get_def_ability_modifier,
    get_final_def_ability_modifier,
    get_spa_ability_modifier,
)
from advisor.damage.move_categories import (
    has_secondary_effect,
    is_secondary_suppressed_by,
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
    assert get_final_def_ability_modifier(
        "multiscale",
        hp_ratio=1.0,
        type_effectiveness=2.0,
        move_flags=set(),
    ) == 2048

def test_multiscale_not_full_no_effect():
    assert get_final_def_ability_modifier(
        "multiscale",
        hp_ratio=0.99,
        type_effectiveness=2.0,
        move_flags=set(),
    ) == 4096

def test_shadow_shield_full_hp_halves():
    assert get_final_def_ability_modifier(
        "shadow-shield",
        hp_ratio=1.0,
        type_effectiveness=1.0,
        move_flags=set(),
    ) == 2048

def test_filter_halves_super_effective_x2():
    assert get_final_def_ability_modifier(
        "filter",
        hp_ratio=0.5,
        type_effectiveness=2.0,
        move_flags=set(),
    ) == 3072

def test_filter_halves_super_effective_x4():
    assert get_final_def_ability_modifier(
        "filter",
        hp_ratio=0.5,
        type_effectiveness=4.0,
        move_flags=set(),
    ) == 3072

def test_filter_no_effect_neutral():
    assert get_final_def_ability_modifier(
        "filter",
        hp_ratio=0.5,
        type_effectiveness=1.0,
        move_flags=set(),
    ) == 4096

def test_filter_no_effect_resisted():
    assert get_final_def_ability_modifier(
        "filter",
        hp_ratio=0.5,
        type_effectiveness=0.5,
        move_flags=set(),
    ) == 4096

def test_solid_rock_halves_super_effective():
    assert get_final_def_ability_modifier(
        "solid-rock",
        hp_ratio=0.5,
        type_effectiveness=2.0,
        move_flags=set(),
    ) == 3072

def test_prism_armor_halves_super_effective():
    assert get_final_def_ability_modifier(
        "prism-armor",
        hp_ratio=0.5,
        type_effectiveness=2.0,
        move_flags=set(),
    ) == 3072

def test_punk_rock_halves_sound_move():
    assert get_final_def_ability_modifier(
        "punk-rock",
        hp_ratio=0.5,
        type_effectiveness=1.0,
        move_flags={"sound"},
    ) == 2048

def test_punk_rock_no_effect_without_sound():
    assert get_final_def_ability_modifier(
        "punk-rock",
        hp_ratio=0.5,
        type_effectiveness=1.0,
        move_flags=set(),
    ) == 4096

def test_filter_full_hp_neutral_no_effect():
    assert get_final_def_ability_modifier(
        "filter",
        hp_ratio=1.0,
        type_effectiveness=1.0,
        move_flags=set(),
    ) == 4096

def test_unknown_final_def_ability_returns_neutral():
    assert get_final_def_ability_modifier(
        "static",
        hp_ratio=1.0,
        type_effectiveness=2.0,
        move_flags={"sound"},
    ) == 4096

def test_unknown_def_ability_returns_neutral():
    assert get_def_ability_modifier("static", "physical") == 4096

def test_blaze_fire_at_one_third_boosts_spa():
    assert get_spa_ability_modifier(
        "blaze",
        move_type="fire",
        hp_current=33,
        hp_max=100,
    ) == 6144

def test_blaze_fire_above_one_third_no_effect():
    assert get_spa_ability_modifier(
        "blaze",
        move_type="fire",
        hp_current=34,
        hp_max=100,
    ) == 4096

def test_blaze_wrong_type_at_one_third_no_effect():
    assert get_spa_ability_modifier(
        "blaze",
        move_type="water",
        hp_current=33,
        hp_max=100,
    ) == 4096

def test_blaze_full_hp_no_effect():
    assert get_spa_ability_modifier(
        "blaze",
        move_type="fire",
        hp_current=100,
        hp_max=100,
    ) == 4096

def test_overgrow_grass_at_one_third_boosts_atk():
    assert get_atk_ability_modifier(
        "overgrow",
        "physical",
        move_type="grass",
        hp_current=33,
        hp_max=100,
    ) == 6144

def test_torrent_water_below_threshold_boosts_spa():
    assert get_spa_ability_modifier(
        "torrent",
        move_type="water",
        hp_current=25,
        hp_max=100,
    ) == 6144

def test_swarm_bug_at_one_third_boosts_atk():
    assert get_atk_ability_modifier(
        "swarm",
        "physical",
        move_type="bug",
        hp_current=33,
        hp_max=100,
    ) == 6144

def test_defeatist_at_half_halves_atk():
    assert get_atk_ability_modifier(
        "defeatist",
        "physical",
        move_type="flying",
        hp_current=50,
        hp_max=100,
    ) == 2048

def test_defeatist_above_half_no_effect():
    assert get_atk_ability_modifier(
        "defeatist",
        "physical",
        move_type="flying",
        hp_current=51,
        hp_max=100,
    ) == 4096

def test_defeatist_at_one_third_still_halves_spa():
    assert get_spa_ability_modifier(
        "defeatist",
        move_type="fire",
        hp_current=33,
        hp_max=100,
    ) == 2048

def test_hustle_physical_fire_keeps_existing_modifier():
    assert get_atk_ability_modifier(
        "hustle",
        "physical",
        move_type="fire",
        hp_current=33,
        hp_max=100,
    ) == 6144

def test_unknown_ability_at_one_third_returns_neutral():
    assert get_atk_ability_modifier(
        "static",
        "physical",
        move_type="fire",
        hp_current=33,
        hp_max=100,
    ) == 4096

def test_solar_power_sun_boosts_spa():
    assert get_spa_ability_modifier("solar-power", weather="sun") == 6144

def test_solar_power_no_weather_no_effect():
    assert get_spa_ability_modifier("solar-power") == 4096

def test_solar_power_rain_no_effect():
    assert get_spa_ability_modifier("solar-power", weather="rain") == 4096

def test_plus_with_plus_minus_ally_boosts_spa():
    assert get_spa_ability_modifier("plus", ally_has_plus_minus=True) == 6144

def test_plus_without_plus_minus_ally_no_effect():
    assert get_spa_ability_modifier("plus", ally_has_plus_minus=False) == 4096

def test_minus_matches_plus_condition():
    assert get_spa_ability_modifier("minus", ally_has_plus_minus=True) == 6144

def test_technician_boosts_bp_40():
    assert get_bp_ability_modifier("technician", base_power=40, move_flags=set()) == 6144

def test_technician_boosts_bp_60():
    assert get_bp_ability_modifier("technician", base_power=60, move_flags=set()) == 6144

def test_technician_no_effect_bp_61():
    assert get_bp_ability_modifier("technician", base_power=61, move_flags=set()) == 4096

def test_technician_no_effect_bp_100():
    assert get_bp_ability_modifier("technician", base_power=100, move_flags=set()) == 4096

def test_tough_claws_boosts_contact():
    assert get_bp_ability_modifier("tough-claws", base_power=80, move_flags={"contact"}) == 5325

def test_tough_claws_no_effect_without_contact():
    assert get_bp_ability_modifier("tough-claws", base_power=80, move_flags=set()) == 4096

def test_iron_fist_boosts_punch():
    assert get_bp_ability_modifier("iron-fist", base_power=40, move_flags={"contact", "punch"}) == 4915

def test_iron_fist_no_effect_without_punch():
    assert get_bp_ability_modifier("iron-fist", base_power=120, move_flags={"contact"}) == 4096

def test_unknown_bp_ability_returns_neutral():
    assert get_bp_ability_modifier("static", base_power=40, move_flags={"contact"}) == 4096

def test_strong_jaw_boosts_bite_moves_only():
    assert get_bp_ability_modifier("strong-jaw", base_power=80, move_flags={"bite"}) == 6144
    assert get_bp_ability_modifier("strong-jaw", base_power=80, move_flags={"contact"}) == 4096

def test_mega_launcher_boosts_pulse_moves_only():
    assert get_bp_ability_modifier("mega-launcher", base_power=85, move_flags={"pulse"}) == 6144
    assert get_bp_ability_modifier("mega-launcher", base_power=85, move_flags={"bullet"}) == 4096

def test_reckless_boosts_recoil_moves_only():
    assert get_bp_ability_modifier("reckless", base_power=120, move_flags={"recoil"}) == 4915
    assert get_bp_ability_modifier("reckless", base_power=120, move_flags={"contact"}) == 4096

def test_reckless_does_not_boost_struggle():
    assert get_bp_ability_modifier(
        "reckless",
        base_power=50,
        move_flags={"contact", "recoil"},
        move_id="struggle",
    ) == 4096

def test_punk_rock_attacker_boosts_sound_moves_only():
    assert get_bp_ability_modifier("punk-rock", base_power=140, move_flags={"sound"}) == 5325
    assert get_bp_ability_modifier("punk-rock", base_power=100, move_flags=set()) == 4096

def test_sheer_force_boosts_secondary_effect_moves():
    assert get_bp_ability_modifier("sheer-force", base_power=80, move_flags={"has_secondary"}) == 5325

def test_sheer_force_no_effect_without_secondary():
    assert get_bp_ability_modifier("sheer-force", base_power=100, move_flags=set()) == 4096

def test_sheer_force_iron_head_boosts_bp_and_suppresses_flinch():
    assert has_secondary_effect("iron-head")
    assert get_bp_ability_modifier("sheer-force", base_power=80, move_flags={"has_secondary"}) == 5325
    assert is_secondary_suppressed_by("iron-head", attacker_ability="sheer-force")

def test_sheer_force_fire_blast_boosts_bp_and_suppresses_burn():
    assert has_secondary_effect("fire-blast")
    assert get_bp_ability_modifier("sheer-force", base_power=110, move_flags={"has_secondary"}) == 5325
    assert is_secondary_suppressed_by("fire-blast", attacker_ability="sheer-force")

def test_sheer_force_earthquake_has_no_bp_boost_or_suppression():
    assert not has_secondary_effect("earthquake")
    assert get_bp_ability_modifier("sheer-force", base_power=100, move_flags=set()) == 4096
    assert not is_secondary_suppressed_by("earthquake", attacker_ability="sheer-force")

def test_sheer_force_body_slam_boosts_bp_and_suppresses_paralysis():
    assert has_secondary_effect("body-slam")
    assert get_bp_ability_modifier("sheer-force", base_power=85, move_flags={"has_secondary"}) == 5325
    assert is_secondary_suppressed_by("body-slam", attacker_ability="sheer-force")

def test_kings_rock_non_sheer_force_flinch_is_not_suppressed():
    assert not is_secondary_suppressed_by(
        "earthquake",
        attacker_ability=None,
        attacker_item="king's-rock",
    )

def test_transistor_boosts_special_electric_moves_only():
    assert get_spa_ability_modifier("transistor", move_type="electric") == 5325
    assert get_spa_ability_modifier("transistor", move_type="water") == 4096

def test_transistor_boosts_physical_electric_moves():
    assert get_atk_ability_modifier("transistor", "physical", move_type="electric") == 5325

def test_transistor_no_effect_on_physical_non_electric_moves():
    assert get_atk_ability_modifier("transistor", "physical", move_type="normal") == 4096
