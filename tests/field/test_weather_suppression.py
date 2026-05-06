from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls


def _ctx(*, weather: str = "sun", attacker_ability: str | None = None) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=120,
        defense_stat=100,
        move_type="fire",
        move_id="flamethrower",
        attacker_types=("fire",),
        defender_types=("electric",),
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(weather=weather),  # type: ignore[arg-type]
        attacker_ability=get_ability(attacker_ability),
    )


def test_air_lock_suppresses_weather_damage_modifier() -> None:
    no_weather = calc_damage_rolls(_ctx(weather="none"))
    air_lock = calc_damage_rolls(_ctx(weather="sun", attacker_ability="air-lock"))

    assert air_lock == no_weather


def test_cloud_nine_does_not_remove_weather_condition() -> None:
    field = Field(weather="sun")
    no_weather = calc_damage_rolls(_ctx(weather="none"))
    cloud_nine = calc_damage_rolls(_ctx(weather=field.weather, attacker_ability="cloud-nine"))

    assert field.weather == "sun"
    assert cloud_nine == no_weather
