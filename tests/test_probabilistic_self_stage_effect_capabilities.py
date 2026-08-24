from copy import deepcopy

from advisor.probabilistic_self_stage_effect_capabilities import (
    resolve_probabilistic_self_stage_effect_capability,
)
from llm.advisor_deterministic_move_stage_effect_metadata import (
    build_deterministic_move_stage_effect_metadata,
)


def _move(**overrides):
    value = {
        "move_id": "metal-claw", "category": "physical", "power": 50,
        "effect_chance": 10, "stat_changes": [{"stat": "attack", "change": 1}],
    }
    value.update(overrides)
    return value


def _source(ability="pressure", applicability=None):
    row = {"status": "known", "value": ability}
    if applicability is not None:
        row["applicability"] = {"status": applicability}
    return {"attacker_ability": row}


def test_catalogued_metal_claw_resolves_exact_self_effect_probability_and_conditions():
    result = resolve_probabilistic_self_stage_effect_capability(move=_move(), source_authority=_source())
    assert result["status"] == "resolved"
    assert result["rule_id"] == "metal-claw-self-attack-boost-v1"
    assert result["probability"] == {"numerator": 10, "denominator": 100}
    assert result["effect"] == {"owner": "self", "stat": "attack", "delta": 1}
    assert result["conditions"] == {
        "requires_successful_damaging_hit": True,
        "blocked_by_substitute": False,
        "target_must_survive": False,
    }
    assert result["ledger"][0]["state"] == "known_neutral"


def test_sheer_force_uses_exact_applicability_without_neutral_fabrication():
    suppressed = resolve_probabilistic_self_stage_effect_capability(
        move=_move(), source_authority=_source("sheer-force", "applicable"),
    )
    neutral = resolve_probabilistic_self_stage_effect_capability(
        move=_move(), source_authority=_source("sheer-force", "not_applicable"),
    )
    unknown = resolve_probabilistic_self_stage_effect_capability(
        move=_move(), source_authority=_source("sheer-force", "unknown"),
    )
    assert suppressed["status"] == "resolved" and suppressed["suppressed"] is True
    assert suppressed["probability"] == {"numerator": 0, "denominator": 100}
    assert neutral["probability"] == {"numerator": 10, "denominator": 100}
    assert unknown["status"] == "incomplete" and unknown["reason"] == "sheer_force_applicability_unknown"


def test_unknown_unsupported_and_invalid_sources_fail_closed_without_unrelated_slots():
    missing = resolve_probabilistic_self_stage_effect_capability(move=_move(), source_authority={})
    serene = resolve_probabilistic_self_stage_effect_capability(move=_move(), source_authority=_source("serene-grace"))
    other = resolve_probabilistic_self_stage_effect_capability(move=_move(), source_authority=_source("overgrow"))
    irrelevant = resolve_probabilistic_self_stage_effect_capability(
        move=_move(), source_authority={**_source(), "target_item": {"status": "unknown"}, "weather": {"status": "unknown"}},
    )
    assert missing["status"] == "incomplete" and missing["reason"] == "attacker_ability_unknown"
    assert serene["status"] == other["status"] == "unsupported"
    assert irrelevant["status"] == "resolved" and irrelevant["required_source_slots"] == ("attacker_ability",)


def test_metadata_conflicts_and_uncatalogued_moves_fail_closed():
    missing = resolve_probabilistic_self_stage_effect_capability(move={"move_id": "metal-claw"}, source_authority=_source())
    chance = resolve_probabilistic_self_stage_effect_capability(move=_move(effect_chance=20), source_authority=_source())
    stages = resolve_probabilistic_self_stage_effect_capability(move=_move(stat_changes=[{"stat": "speed", "change": 1}]), source_authority=_source())
    other = resolve_probabilistic_self_stage_effect_capability(move=_move(move_id="meteor-mash"), source_authority=_source())
    assert missing["status"] == "incomplete"
    assert chance["status"] == stages["status"] == other["status"] == "unsupported"


def test_output_is_detached_and_deterministic_stage_contract_stays_separate():
    source, move = _source(), _move()
    original = deepcopy((source, move))
    result = resolve_probabilistic_self_stage_effect_capability(move=move, source_authority=source)
    result["effect"]["delta"] = 6
    deterministic = build_deterministic_move_stage_effect_metadata({
        "move_id": "flame-charge", "category": "physical",
        "stat_changes": [{"stat": "speed", "change": 1}], "effect_chance": 100,
    })
    assert (source, move) == original
    assert deterministic["status"] == "deterministic"
