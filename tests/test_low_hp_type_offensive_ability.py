import pytest

from llm.advisor_low_hp_type_offensive_ability import (
    resolve_low_hp_type_offensive_ability_applicability,
    validate_low_hp_type_offensive_ability_applicability,
)


@pytest.mark.parametrize(
    ("maximum", "active_hp", "inactive_hp"),
    ((100, 33, 34), (101, 33, 34), (299, 99, 100), (300, 100, 101)),
)
def test_exact_integer_threshold_boundaries(maximum, active_hp, inactive_hp):
    active = resolve_low_hp_type_offensive_ability_applicability(
        ability="blaze",
        effective_move_type="fire",
        current_hp=active_hp,
        max_hp=maximum,
        hp_source="runtime_strategy_d0_v1",
    )
    inactive = resolve_low_hp_type_offensive_ability_applicability(
        ability="blaze",
        effective_move_type="fire",
        current_hp=inactive_hp,
        max_hp=maximum,
        hp_source="runtime_strategy_d0_v1",
    )

    assert active["status"] == "resolved"
    assert active["threshold"]["active"] is True
    assert active["outcome"] == "applicable"
    assert active["modifier_q12"] == 6144
    assert inactive["status"] == "resolved"
    assert inactive["threshold"]["active"] is False
    assert inactive["outcome"] == "not_applicable"
    assert inactive["modifier_q12"] == 4096


@pytest.mark.parametrize(
    ("ability", "move_type"),
    (("blaze", "fire"), ("torrent", "water"), ("overgrow", "grass"), ("swarm", "bug")),
)
def test_each_family_member_requires_matching_effective_type(ability, move_type):
    matching = resolve_low_hp_type_offensive_ability_applicability(
        ability=ability,
        effective_move_type=move_type,
        current_hp=1,
        max_hp=3,
        hp_source="detached_path_local_attacker_hp_v1",
        source_hit={"hit_index": 2, "path_id": "path"},
    )
    wrong_type = resolve_low_hp_type_offensive_ability_applicability(
        ability=ability,
        effective_move_type="normal",
        current_hp=1,
        max_hp=3,
        hp_source="detached_path_local_attacker_hp_v1",
        source_hit={"hit_index": 2, "path_id": "path"},
    )

    assert matching["outcome"] == "applicable"
    assert matching["modifier_q12"] == 6144
    assert matching["source_hit"] == {"hit_index": 2, "path_id": "path"}
    assert wrong_type["outcome"] == "not_applicable"
    assert wrong_type["modifier_q12"] == 4096


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    (
        ({"current_hp": None, "max_hp": 100}, "low_hp_type_hp_authority_invalid"),
        ({"current_hp": -1, "max_hp": 100}, "low_hp_type_hp_authority_invalid"),
        ({"current_hp": 101, "max_hp": 100}, "low_hp_type_hp_authority_invalid"),
        ({"current_hp": 0, "max_hp": 0}, "low_hp_type_hp_authority_invalid"),
        ({"current_hp": 1, "max_hp": 100, "hp_source": "unknown"}, "low_hp_type_hp_source_invalid"),
    ),
)
def test_missing_or_invalid_hp_authority_rejects(kwargs, reason):
    payload = {"current_hp": 33, "max_hp": 100, "hp_source": "runtime_strategy_d0_v1"}
    payload.update(kwargs)
    result = resolve_low_hp_type_offensive_ability_applicability(
        ability="blaze",
        effective_move_type="fire",
        **payload,
    )

    assert result == {
        "status": "rejected",
        "schema_version": "low-hp-type-offensive-ability-applicability-v1",
        "reason": reason,
    }


def test_unknown_ability_and_move_type_fail_closed_without_neutral_fabrication():
    assert resolve_low_hp_type_offensive_ability_applicability(
        ability="unknown",
        effective_move_type="fire",
        current_hp=33,
        max_hp=100,
        hp_source="runtime_strategy_d0_v1",
    )["reason"] == "low_hp_type_attacker_ability_unknown"
    assert resolve_low_hp_type_offensive_ability_applicability(
        ability="blaze",
        effective_move_type="unknown",
        current_hp=33,
        max_hp=100,
        hp_source="runtime_strategy_d0_v1",
    )["reason"] == "low_hp_type_effective_move_type_unknown"


def test_forged_threshold_modifier_source_and_hit_records_reject():
    valid = resolve_low_hp_type_offensive_ability_applicability(
        ability="torrent",
        effective_move_type="water",
        current_hp=33,
        max_hp=100,
        hp_source="detached_path_local_attacker_hp_v1",
        source_hit={"hit_index": 1, "path_id": "hit-1"},
    )
    assert validate_low_hp_type_offensive_ability_applicability(valid)

    forged_threshold = {**valid, "threshold": {**valid["threshold"], "active": False}}
    forged_modifier = {**valid, "modifier_q12": 5324}
    forged_source = {**valid, "hp_source": "runtime"}
    forged_hit = {**valid, "source_hit": {"hit_index": 0, "path_id": "hit-1"}}

    assert not validate_low_hp_type_offensive_ability_applicability(forged_threshold)
    assert not validate_low_hp_type_offensive_ability_applicability(forged_modifier)
    assert not validate_low_hp_type_offensive_ability_applicability(forged_source)
    assert not validate_low_hp_type_offensive_ability_applicability(forged_hit)
