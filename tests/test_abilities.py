from __future__ import annotations

from advisor.damage.abilities import get_ability, is_weather_suppressed, load_abilities_catalog


def test_chlorophyll_lookup() -> None:
    ability = get_ability("chlorophyll")
    assert ability is not None
    assert ability.weather == "sun"
    assert ability.multiplier_q12 == 8192


def test_missing_ability_lookup() -> None:
    assert get_ability(None) is None
    assert get_ability("nonexistent") is None


def test_weather_suppression_lookup() -> None:
    assert is_weather_suppressed("cloud-nine", None)
    assert is_weather_suppressed("air-lock", None)
    assert is_weather_suppressed(None, None) is False


def test_stubbed_ability_is_not_implemented() -> None:
    ability = get_ability("huge-power")
    assert ability is not None
    assert ability.implemented is False


def test_catalog_contains_full_smogon_registry() -> None:
    catalog = load_abilities_catalog()
    assert len(catalog) >= 300
    assert sum(1 for ability in catalog.values() if ability.implemented) >= 28
