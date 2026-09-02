from llm.advisor_guts_status_attack_ability import (
    resolve_guts_status_attack_ability_applicability,
    validate_guts_status_attack_ability_applicability,
)


def test_guts_applicability_accepts_exact_major_conditions_and_physical_attacks():
    for condition in ("burn", "poison", "toxic", "paralysis", "sleep", "freeze"):
        result = resolve_guts_status_attack_ability_applicability(
            ability="guts",
            attacker_condition=condition,
            condition_source="runtime_strategy_d0_v1",
            move_category="physical",
            suppression_status="active",
        )
        assert result["status"] == "resolved"
        assert result["outcome"] == "applicable"
        assert result["modifier_q12"] == 6144
        assert result["burn_penalty_bypassed"] is (condition == "burn")
        assert validate_guts_status_attack_ability_applicability(result)


def test_guts_applicability_preserves_nonapplicable_and_fail_closed_cases():
    special = resolve_guts_status_attack_ability_applicability(
        ability="guts",
        attacker_condition="burn",
        condition_source="runtime_strategy_d0_v1",
        move_category="special",
        suppression_status="active",
    )
    suppressed = resolve_guts_status_attack_ability_applicability(
        ability="guts",
        attacker_condition="burn",
        condition_source="runtime_strategy_d0_v1",
        move_category="physical",
        suppression_status="suppressed",
    )
    unknown = resolve_guts_status_attack_ability_applicability(
        ability="guts",
        attacker_condition="burn",
        condition_source="runtime_strategy_d0_v1",
        move_category="physical",
        suppression_status="unknown",
    )
    invalid = resolve_guts_status_attack_ability_applicability(
        ability="guts",
        attacker_condition="burn",
        condition_source="forged",
        move_category="physical",
        suppression_status="active",
    )

    assert special["outcome"] == "not_applicable"
    assert special["modifier_q12"] == 4096
    assert suppressed["outcome"] == "not_applicable"
    assert suppressed["burn_penalty_bypassed"] is False
    assert unknown["status"] == "incomplete"
    assert invalid["status"] == "rejected"
    forged = {**special, "modifier_q12": 6144}
    assert not validate_guts_status_attack_ability_applicability(forged)
