from copy import deepcopy

from llm.advisor_deterministic_move_stage_effect_metadata import build_deterministic_move_stage_effect_metadata
from llm.advisor_predictive_normal_formula_interval import normal_formula_eligibility


def _move(move_id, category, changes, chance=100):
    return {"move_id": move_id, "category": category, "power": 80, "type": "fire", "stat_changes": changes, "effect_chance": chance}


def test_catalogued_self_target_and_atomic_multi_stat_effects_are_detached() -> None:
    flame = build_deterministic_move_stage_effect_metadata(_move("flame-charge", "physical", [{"stat": "speed", "change": 1}]))
    acid = build_deterministic_move_stage_effect_metadata(_move("acid-spray", "special", [{"stat": "special-defense", "change": -2}]))
    close = build_deterministic_move_stage_effect_metadata(_move("close-combat", "physical", [{"stat": "defense", "change": -1}, {"stat": "special-defense", "change": -1}]))
    assert flame["effects"] == [{"owner": "self", "stat": "speed", "delta": 1}]
    assert acid["effects"] == [{"owner": "target", "stat": "special-defense", "delta": -2}]
    assert acid["conditions"] == {"requires_successful_damaging_hit": True, "blocked_by_substitute": True, "target_must_survive": True}
    assert close["effects"] == [{"owner": "self", "stat": "defense", "delta": -1}, {"owner": "self", "stat": "special-defense", "delta": -1}]
    frozen = deepcopy(close); close["effects"][0]["delta"] = 3
    assert frozen["effects"][0]["delta"] == -1


def test_probabilistic_unknown_and_no_effect_are_distinct() -> None:
    psychic = build_deterministic_move_stage_effect_metadata(_move("psychic", "special", [{"stat": "special-defense", "change": -1}], chance=10))
    unknown = build_deterministic_move_stage_effect_metadata(_move("mystery", "special", [{"stat": "speed", "change": 1}], chance=None))
    water = build_deterministic_move_stage_effect_metadata({"move_id": "water-gun", "category": "special", "stat_changes": [], "effect_chance": None})
    assert psychic["status"] == "probabilistic"
    assert unknown["status"] == "unknown"
    assert water["status"] == "no_effect"


def test_generic_normal_formula_eligibility_carries_stage_classification_without_blocking_direct_damage() -> None:
    flame = normal_formula_eligibility(_move("flame-charge", "physical", [{"stat": "speed", "change": 1}]))
    psychic = normal_formula_eligibility(_move("psychic", "special", [{"stat": "special-defense", "change": -1}], chance=10))
    water = normal_formula_eligibility({"move_id": "water-gun", "category": "special", "power": 40, "type": "water", "stat_changes": [], "effect_chance": None})
    assert flame["status"] == "eligible" and flame["stage_effect_authority"]["status"] == "deterministic"
    assert psychic["status"] == "eligible" and psychic["stage_effect_authority"]["status"] == "probabilistic"
    assert water["stage_effect_authority"]["status"] == "no_effect"
