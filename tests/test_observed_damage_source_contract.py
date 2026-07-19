import pytest

from llm.advisor_client import normalize_observed_previous_damage_confirmation


def _snapshot(**overrides):
    value = {"damage": 60, "damage_category": "physical", "damage_kind": "direct_move_damage", "source_side": "opponent", "target_side": "self"}
    value.update(overrides)
    return value


def test_normalizes_valid_confirmed_direct_damage():
    assert normalize_observed_previous_damage_confirmation(_snapshot())["confidence"] == "known"


@pytest.mark.parametrize("damage", [0, -1, True])
def test_rejects_non_positive_or_boolean_damage(damage):
    with pytest.raises(ValueError): normalize_observed_previous_damage_confirmation(_snapshot(damage=damage))


@pytest.mark.parametrize("overrides", [{"damage_category": "status"}, {"source_side": "self"}, {"target_side": "opponent"}, {"damage_kind": "recoil"}])
def test_rejects_invalid_source_category_or_indirect_kind(overrides):
    with pytest.raises(ValueError): normalize_observed_previous_damage_confirmation(_snapshot(**overrides))
