from __future__ import annotations

import pytest

from advisor.damage.field import Field, SideField


def test_default_field_is_inactive_champions_doubles() -> None:
    field = Field()

    assert field.weather == "none"
    assert field.terrain == "none"
    assert field.is_doubles is True
    assert field.defender_side == SideField()


def test_with_weather_is_immutable() -> None:
    field = Field()
    updated = field.with_weather("sun")

    assert field.weather == "none"
    assert updated.weather == "sun"


def test_with_terrain_is_immutable() -> None:
    field = Field()
    updated = field.with_terrain("electric")

    assert field.terrain == "none"
    assert updated.terrain == "electric"


def test_invalid_weather_raises() -> None:
    with pytest.raises(ValueError):
        Field(weather="hail")  # type: ignore[arg-type]


def test_invalid_terrain_raises() -> None:
    with pytest.raises(ValueError):
        Field(terrain="mud")  # type: ignore[arg-type]


def test_side_field_validates_hazard_layers() -> None:
    with pytest.raises(ValueError):
        SideField(spikes=4)
