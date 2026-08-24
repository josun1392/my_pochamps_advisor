from copy import deepcopy

from advisor.probabilistic_self_stage_effect_capabilities import resolve_probabilistic_self_stage_effect_capability
from advisor.probabilistic_target_stage_effect_capabilities import resolve_probabilistic_target_stage_effect_capability
from llm.advisor_deterministic_move_stage_effect_metadata import build_deterministic_move_stage_effect_metadata


def _move(**overrides):
    value = {
        "move_id": "shadow-ball", "category": "special", "power": 80, "target": "selected-pokemon",
        "effect_chance": 20, "stat_changes": [{"stat": "special-defense", "change": -1}],
    }
    value.update(overrides)
    return value


def _source(*, attacker="pressure", attacker_applicability=None, target="pressure", target_interaction=None, item=None):
    attacker_row = {"status": "known", "value": attacker}
    target_row = {"status": "known", "value": target}
    if attacker_applicability is not None:
        attacker_row["applicability"] = {"status": attacker_applicability}
    if target_interaction is not None:
        target_row["interaction"] = {"status": target_interaction}
    return {"attacker_ability": attacker_row, "target_ability": target_row, "target_item": {"status": "known_absent"} if item is None else item}


def test_catalogued_shadow_ball_resolves_exact_target_effect_and_future_leaf_requirements():
    result = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source())

    assert result["status"] == "resolved"
    assert result["rule_id"] == "shadow-ball-target-special-defense-drop-v1"
    assert result["probability"] == {"numerator": 20, "denominator": 100}
    assert result["effect"] == {"owner": "target", "stat": "special-defense", "delta": -1}
    assert result["conditions"] == {"requires_successful_damaging_hit": True, "blocked_by_substitute": True, "target_must_survive": True}
    assert result["required_runtime_slots"] == ("target.special-defense",)
    assert [row["state"] for row in result["ledger"]] == ["known_neutral", "known_neutral", "known_neutral"]


def test_sheer_force_and_shield_dust_require_exact_applicability_or_interaction():
    sheer = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(attacker="sheer-force", attacker_applicability="applicable"))
    sheer_unknown = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(attacker="sheer-force", attacker_applicability="unknown"))
    dust = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(target="shield-dust", target_interaction="affecting"))
    dust_unknown = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(target="shield-dust", target_interaction="unknown"))

    assert sheer["status"] == dust["status"] == "resolved"
    assert sheer["probability"] == dust["probability"] == {"numerator": 0, "denominator": 100}
    assert sheer["suppressed_by"] == ("attacker_ability",) and dust["suppressed_by"] == ("target_ability",)
    assert sheer_unknown["status"] == "incomplete" and sheer_unknown["reason"] == "sheer_force_applicability_unknown"
    assert dust_unknown["status"] == "incomplete" and dust_unknown["reason"] == "shield_dust_interaction_unknown"


def test_covert_cloak_and_exact_item_absence_are_distinct_and_unknown_fails_closed():
    cloak = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(item={"status": "known", "value": "covert-cloak"}))
    absent = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source())
    unknown = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(item={"status": "unknown"}))

    assert cloak["status"] == "resolved" and cloak["probability"] == {"numerator": 0, "denominator": 100}
    assert cloak["suppressed_by"] == ("target_item",)
    assert absent["ledger"][2]["reason"] == "target_item_proven_absent"
    assert unknown["status"] == "incomplete" and unknown["reason"] == "target_item_unknown"


def test_uncatalogued_or_conflicting_authority_fails_closed_and_existing_stage_contracts_stay_separate():
    source, move = _source(), _move()
    original = deepcopy((source, move))
    unsupported_move = resolve_probabilistic_target_stage_effect_capability(move=_move(move_id="crunch"), source_authority=source)
    conflict = resolve_probabilistic_target_stage_effect_capability(move=_move(effect_chance=10), source_authority=source)
    unknown_ability = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority={**source, "target_ability": {"status": "unknown"}})
    uncatalogued_ability = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(target="overgrow"))
    unsupported_item = resolve_probabilistic_target_stage_effect_capability(move=_move(), source_authority=_source(item={"status": "known", "value": "leftovers"}))
    deterministic = build_deterministic_move_stage_effect_metadata({"move_id": "acid-spray", "category": "special", "stat_changes": [{"stat": "special-defense", "change": -2}], "effect_chance": 100})
    self_effect = resolve_probabilistic_self_stage_effect_capability(move={"move_id": "metal-claw", "category": "physical", "power": 50, "effect_chance": 10, "stat_changes": [{"stat": "attack", "change": 1}]}, source_authority={"attacker_ability": {"status": "known", "value": "pressure"}})

    assert (source, move) == original
    assert unsupported_move["status"] == conflict["status"] == uncatalogued_ability["status"] == unsupported_item["status"] == "unsupported"
    assert unknown_ability["status"] == "incomplete" and unknown_ability["reason"] == "target_ability_unknown"
    assert deterministic["status"] == "deterministic" and self_effect["probability"] == {"numerator": 10, "denominator": 100}
