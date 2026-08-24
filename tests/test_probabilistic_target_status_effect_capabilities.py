from copy import deepcopy

from advisor.probabilistic_self_stage_effect_capabilities import resolve_probabilistic_self_stage_effect_capability
from advisor.probabilistic_target_stage_effect_capabilities import resolve_probabilistic_target_stage_effect_capability
from advisor.probabilistic_target_status_effect_capabilities import resolve_probabilistic_target_status_effect_capability


def _move(**overrides):
    value = {"move_id": "thunderbolt", "category": "special", "power": 90, "target": "selected-pokemon", "effect_chance": 10, "ailment": "paralysis"}
    value.update(overrides)
    return value


def _source(*, condition=None, types=None, attacker="pressure", attacker_applicability=None, target="pressure", target_interaction=None, item=None):
    attacker_row = {"status": "known", "value": attacker}
    target_row = {"status": "known", "value": target}
    if attacker_applicability is not None:
        attacker_row["applicability"] = {"status": attacker_applicability}
    if target_interaction is not None:
        target_row["interaction"] = {"status": target_interaction}
    return {
        "target_condition": {"status": "known_none"} if condition is None else condition,
        "target_types": {"status": "known", "values": ["water"]} if types is None else types,
        "attacker_ability": attacker_row,
        "target_ability": target_row,
        "target_item": {"status": "known_absent"} if item is None else item,
    }


def test_catalogued_thunderbolt_resolves_exact_target_paralysis_with_leaf_requirements():
    result = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source())

    assert result["status"] == "resolved"
    assert result["rule_id"] == "thunderbolt-target-paralysis-v1"
    assert result["probability"] == {"numerator": 10, "denominator": 100}
    assert result["effect"] == {"owner": "target", "condition": "paralysis"}
    assert result["conditions"] == {"requires_successful_damaging_hit": True, "blocked_by_substitute": True, "target_must_survive": True}
    assert result["eligible"] is True and result["suppressed"] is False
    assert [row["state"] for row in result["ledger"]] == ["known_neutral"] * 5


def test_condition_and_electric_type_are_explicit_eligibility_facts_not_neutral_defaults():
    present = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(condition={"status": "known_present", "condition": "burn"}))
    electric = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(types={"status": "known", "values": ["electric"]}))
    unknown_condition = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(condition={"status": "unknown"}))
    unknown_types = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(types={"status": "unknown"}))

    assert present["status"] == electric["status"] == "resolved"
    assert present["probability"] == electric["probability"] == {"numerator": 0, "denominator": 100}
    assert present["ineligible_by"] == ("target_condition",)
    assert electric["ineligible_by"] == ("target_types",)
    assert unknown_condition["status"] == "incomplete" and unknown_condition["reason"] == "target_current_condition_unknown"
    assert unknown_types["status"] == "incomplete" and unknown_types["reason"] == "target_types_unknown"


def test_suppressors_require_exact_authority_and_preserve_proven_item_absence():
    sheer = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(attacker="sheer-force", attacker_applicability="applicable"))
    dust = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(target="shield-dust", target_interaction="affecting"))
    cloak = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(item={"status": "known", "value": "covert-cloak"}))
    unknown_sheer = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(attacker="sheer-force"))
    unknown_item = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(item={"status": "unknown"}))

    assert sheer["probability"] == dust["probability"] == cloak["probability"] == {"numerator": 0, "denominator": 100}
    assert sheer["suppressed_by"] == ("attacker_ability",)
    assert dust["suppressed_by"] == ("target_ability",)
    assert cloak["suppressed_by"] == ("target_item",)
    assert unknown_sheer["status"] == "incomplete" and unknown_sheer["reason"] == "sheer_force_applicability_unknown"
    assert unknown_item["status"] == "incomplete" and unknown_item["reason"] == "target_item_unknown"


def test_unknown_or_uncatalogued_relevant_authority_fails_closed_without_mutating_inputs():
    source, move = _source(), _move()
    original = deepcopy((source, move))
    unsupported_move = resolve_probabilistic_target_status_effect_capability(move=_move(move_id="thunder"), source_authority=source)
    conflict = resolve_probabilistic_target_status_effect_capability(move=_move(effect_chance=30), source_authority=source)
    unknown_ability = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority={**source, "target_ability": {"status": "unknown"}})
    limber = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(target="limber"))
    neutral_item = resolve_probabilistic_target_status_effect_capability(move=_move(), source_authority=_source(item={"status": "known_absent"}))
    shadow = resolve_probabilistic_target_stage_effect_capability(move={"move_id": "shadow-ball", "category": "special", "power": 80, "target": "selected-pokemon", "effect_chance": 20, "stat_changes": [{"stat": "special-defense", "change": -1}]}, source_authority={"attacker_ability": {"status": "known", "value": "pressure"}, "target_ability": {"status": "known", "value": "pressure"}, "target_item": {"status": "known_absent"}})
    metal = resolve_probabilistic_self_stage_effect_capability(move={"move_id": "metal-claw", "category": "physical", "power": 50, "effect_chance": 10, "stat_changes": [{"stat": "attack", "change": 1}]}, source_authority={"attacker_ability": {"status": "known", "value": "pressure"}})

    assert (source, move) == original
    assert unsupported_move["status"] == conflict["status"] == limber["status"] == "unsupported"
    assert unknown_ability["status"] == "incomplete" and unknown_ability["reason"] == "target_ability_unknown"
    assert neutral_item["status"] == "resolved" and neutral_item["probability"] == {"numerator": 10, "denominator": 100}
    assert shadow["probability"] == {"numerator": 20, "denominator": 100}
    assert metal["probability"] == {"numerator": 10, "denominator": 100}
