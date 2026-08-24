from copy import deepcopy

from advisor.damage.crit import select_critical_damage_stages
from llm.advisor_predictive_critical_damage_context import materialize_predictive_critical_damage_contexts
from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval
from tests.test_predictive_water_gun_interval import _fixture


def _context(*, category="physical", stages=(0, 0), ability=None):
    state, owner, target, damage, provenance = _fixture()
    move_type = "normal" if category == "physical" else "water"
    damage["move"] = {"move_id": "tackle" if category == "physical" else "water-gun", "category": category, "power": 40, "type": move_type}
    current = damage["battle_context"]["current_state"]
    if category == "physical":
        current["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "none"}]}
        offensive, defensive = "attack", "defense"
    else:
        offensive, defensive = "special-attack", "special-defense"
    current["stat_stage_context"] = {"current_stages": [
        {"side": "self", "stat": offensive, "stage": stages[0], "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"},
        {"side": "opponent", "stat": defensive, "stage": stages[1], "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"},
    ]}
    if ability is not None:
        current["ability_context"] = {"current_abilities": [{"side": "self", "ability": ability}]}
    return state, owner, target, damage, provenance


def _materialize(*, category="physical", stages=(0, 0), ability=None):
    state, owner, target, damage, provenance = _context(category=category, stages=stages, ability=ability)
    return materialize_predictive_critical_damage_contexts(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50,
    )


def test_canonical_critical_stage_selection_preserves_advantageous_and_ignores_disadvantageous_stages():
    assert select_critical_damage_stages(-2, 2, is_critical=True) == (0, 0)
    assert select_critical_damage_stages(2, -2, is_critical=True) == (2, -2)
    assert select_critical_damage_stages(-2, 2, is_critical=False) == (-2, 2)


def test_paired_contexts_materialize_from_one_frozen_action_without_mutation():
    state, owner, target, damage, provenance = _context(stages=(-2, 2))
    before = deepcopy((state, damage, provenance))
    result = materialize_predictive_critical_damage_contexts(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50,
    )
    assert result["status"] == "resolved"
    normal, critical = result["non_critical_context"], result["critical_context"]
    assert normal["scope"]["critical"] == "non_critical_assumed"
    assert critical["scope"]["critical"] == "critical_assumed"
    assert normal["native_evaluator_result"]["stat_stage_evidence"]["offensive_stage_value"] == -2
    assert critical["native_evaluator_result"]["stat_stage_evidence"]["effective_offensive_stage_value"] == 0
    assert critical["native_evaluator_result"]["stat_stage_evidence"]["effective_defensive_stage_value"] == 0
    assert min(critical["exact_damage_rolls"]) > min(normal["exact_damage_rolls"])
    assert (state, damage, provenance) == before


def test_positive_offense_and_negative_defense_are_retained_for_physical_and_special_critical_contexts():
    for category in ("physical", "special"):
        result = _materialize(category=category, stages=(2, -2))
        evidence = result["critical_context"]["native_evaluator_result"]["stat_stage_evidence"]
        assert (evidence["effective_offensive_stage_value"], evidence["effective_defensive_stage_value"]) == (2, -2)
        assert min(result["critical_context"]["exact_damage_rolls"]) > min(result["non_critical_context"]["exact_damage_rolls"])


def test_noncritical_interval_is_unchanged_and_sniper_is_delegated_to_native_critical_damage_engine():
    state, owner, target, damage, provenance = _context(stages=(0, 0))
    legacy = build_predictive_normal_formula_interval(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50,
    )
    explicit = build_predictive_normal_formula_interval(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50, is_critical=False,
    )
    assert legacy == explicit
    standard = _materialize(stages=(0, 0))
    sniper = _materialize(stages=(0, 0), ability="sniper")
    assert min(sniper["critical_context"]["exact_damage_rolls"]) > min(standard["critical_context"]["exact_damage_rolls"])
    assert "ability_sniper_critical_damage" in sniper["critical_context"]["native_evaluator_result"]["applied_damage_modifiers"]


def test_missing_or_stale_stage_authority_fails_closed_without_neutral_fabrication():
    state, owner, target, damage, provenance = _context()
    damage["battle_context"]["current_state"].pop("stat_stage_context")
    missing = materialize_predictive_critical_damage_contexts(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50,
    )
    assert missing == {"status": "incomplete", "schema_version": "strict-predictive-critical-damage-context-v1", "reason": "critical_damage_stage_authority_unknown"}

    state, owner, target, damage, provenance = _context()
    state["active"]["self"]["pokemon_id"] = "foreign"
    stale = materialize_predictive_critical_damage_contexts(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50,
    )
    assert stale["status"] == "rejected"
