from llm.advisor_full_hp_defender_ability import (
    resolve_full_hp_defender_ability_applicability,
    validate_full_hp_defender_ability_applicability,
)
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result
from llm.advisor_exact_immediate_action_pair_outcome_ledger import _full_hp_defender_ability_leaf


def _resolve(**overrides):
    values = {
        "ability": "multiscale", "current_hp": 100, "max_hp": 100,
        "hp_source": "runtime_strategy_d0_v1", "suppression_status": "active",
        "bypass_result": "not_bypassed", "source_hit": {"hit_index": 1, "path_id": "test:hit:1"},
    }
    values.update(overrides)
    return resolve_full_hp_defender_ability_applicability(**values)


def test_full_hp_family_is_exact_and_shadow_shield_has_distinct_bypass_policy():
    multiscale = _resolve()
    shadow = _resolve(ability="shadow-shield")
    assert multiscale["status"] == shadow["status"] == "resolved"
    assert multiscale["outcome"] == shadow["outcome"] == "applicable"
    assert multiscale["modifier_q12"] == shadow["modifier_q12"] == 2048
    assert multiscale["bypass_policy"] == "mold_breaker_breakable"
    assert shadow["bypass_policy"] == "mold_breaker_immune"
    assert validate_full_hp_defender_ability_applicability(multiscale)
    assert validate_full_hp_defender_ability_applicability(shadow)


def test_full_hp_family_never_uses_ratio_or_invalid_hp_as_neutral_authority():
    assert _resolve(current_hp=99)["outcome"] == "not_applicable"
    assert _resolve(current_hp=None)["status"] == "rejected"
    assert _resolve(current_hp=True)["status"] == "rejected"
    assert _resolve(current_hp=101)["status"] == "rejected"
    assert _resolve(hp_source="ratio")["status"] == "rejected"


def test_suppression_and_bypass_disable_only_the_relevant_policy():
    assert _resolve(bypass_result="bypassed")["outcome"] == "not_applicable"
    assert _resolve(suppression_status="suppressed")["outcome"] == "not_applicable"
    assert _resolve(ability="shadow-shield", bypass_result="bypassed")["outcome"] == "not_applicable"
    forged = _resolve()
    forged["modifier_q12"] = 4096
    assert not validate_full_hp_defender_ability_applicability(forged)


def test_direct_damage_keeps_shadow_shield_distinct_from_multiscale_bypass_and_crit():
    baseline = _modifier_result(category="special", move_type="normal", move_id="swift", power=60)
    multiscale = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, ability="mold-breaker", defender_ability="multiscale")
    shadow = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, ability="mold-breaker", defender_ability="shadow-shield")
    suppressed = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, ability="neutralizing-gas", defender_ability="shadow-shield")
    critical = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_ability="multiscale", is_critical=True)
    assert multiscale["full_hp_defender_ability_evidence"]["bypass_result"] == "bypassed"
    assert multiscale["damage_range"] == baseline["damage_range"]
    assert shadow["full_hp_defender_ability_evidence"]["bypass_result"] == "not_bypassed"
    assert shadow["damage_range"]["maximum"] < baseline["damage_range"]["maximum"]
    assert suppressed["full_hp_defender_ability_evidence"]["suppression_status"] == "suppressed"
    assert suppressed["damage_range"] == baseline["damage_range"]
    assert critical["full_hp_defender_ability_evidence"]["modifier_q12"] == 2048


def test_ledger_rejects_forged_per_hit_full_hp_evidence():
    evidence = _resolve()
    hit = {"hit_index": 1, "pre_hp": 100, "target_max_hp": 100, "full_hp_defender_ability": evidence}
    assert _full_hp_defender_ability_leaf((hit,)) is None
    for field, value in (("defender_current_hp", 99), ("defender_max_hp", 99), ("defender_hp_source", "forged"), ("full_hp", False), ("modifier_q12", 4096), ("bypass_result", "bypassed")):
        forged = {**evidence, field: value}
        assert _full_hp_defender_ability_leaf(({**hit, "full_hp_defender_ability": forged},)) == "pair_final_full_hp_defender_ability_consequence_invalid"
