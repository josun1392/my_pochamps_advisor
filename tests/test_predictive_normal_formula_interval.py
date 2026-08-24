from copy import deepcopy

from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval, normal_formula_eligibility
from tests.test_predictive_water_gun_interval import _fixture


def _run(move: dict, *, hp: int = 100, substitute: str = "known_inactive", substitute_hp=None):
    state, owner, target, damage, provenance = _fixture(hp, substitute, substitute_hp)
    damage["move"] = deepcopy(move)
    if move["category"] == "physical":
        damage["battle_context"]["current_state"]["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "none"}]}
    return build_predictive_normal_formula_interval(branch_state=state, decision_owner=owner, target_owner=target, snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50)


def test_metadata_gate_is_generic_and_excludes_non_simple_shapes() -> None:
    assert normal_formula_eligibility({"move_id": "surf", "category": "special", "power": 90, "type": "water"}) == {"status": "eligible", "move_id": "surf"}
    assert normal_formula_eligibility({"move_id": "bullet-seed", "category": "physical", "power": 25, "type": "grass", "min_hits": 2, "max_hits": 5})["reason"] == "not_simple_normal_formula_move"
    assert normal_formula_eligibility({"move_id": "drain-punch", "category": "physical", "power": 75, "type": "fighting", "drain": 50})["status"] == "eligible"


def test_special_physical_and_secondary_effect_representatives_use_one_interval_path() -> None:
    surf = _run({"move_id": "surf", "category": "special", "power": 90, "type": "water"})
    tackle = _run({"move_id": "tackle", "category": "physical", "power": 40, "type": "normal"})
    thunderbolt = _run({"move_id": "thunderbolt", "category": "special", "power": 90, "type": "electric"})
    assert all(result["completeness"] == "exact_complete" and len(result["exact_damage_rolls"]) == 16 for result in (surf, tackle, thunderbolt))
    assert surf["native_evaluator_result"]["damage_model"] == tackle["native_evaluator_result"]["damage_model"] == "single_hit_formula"
    assert thunderbolt["scope"]["secondary_effect"] == "unmodeled"


def test_interval_preserves_ko_and_substitute_semantics_without_move_specific_logic() -> None:
    move = {"move_id": "surf", "category": "special", "power": 90, "type": "water"}
    guaranteed = _run(move, hp=1); possible = _run(move, hp=38); survival = _run(move, hp=100)
    substitute = _run(move, substitute="known_active", substitute_hp=30)
    assert guaranteed["guaranteed_facts"]["guaranteed_target_KO"]
    assert possible["guaranteed_facts"]["possible_target_KO"]
    assert survival["guaranteed_facts"]["guaranteed_target_survival"]
    assert substitute["target_routing"] == "substitute" and substitute["guaranteed_facts"]["guaranteed_substitute_break"]
