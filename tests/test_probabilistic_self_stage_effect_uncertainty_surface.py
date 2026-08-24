from copy import deepcopy

from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import present_strategy_explanation


OWNER = {"session_id": "secondary-surface", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}


def _secondary(*, suppressed=False):
    numerator = 0 if suppressed else 10
    branches = ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 100, "denominator": 100}},) if suppressed else (
        {"branch": "no_effect", "conditional_secondary_probability": {"numerator": 90, "denominator": 100}},
        {"branch": "effect", "conditional_secondary_probability": {"numerator": 10, "denominator": 100}, "hypothetical_stage_effect": {"owner": "self", "stat": "attack", "previous_stage": 0, "delta": 1, "resulting_stage": 1}},
    )
    return {"status": "resolved", "schema_version": "deterministic-predictive-probabilistic-self-stage-effect-uncertainty-v1", "move_id": "metal-claw", "effect_probability": {"numerator": numerator, "denominator": 100}, "shared_successful_hit_consequence": "inherited_from_enclosing_hit_leaf", "branches": branches, "guaranteed_effects": (), "possible_effects": () if suppressed else (branches[-1]["hypothetical_stage_effect"],)}


def _orchestration(secondary):
    facts = {"guaranteed_opponent_fainted": None, "possible_opponent_ko": True}
    hit = {"status": "resolved", "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1", "move_id": "metal-claw", "probability_percent": 80, "branches": ({"branch": "hit", "probability_percent": 80, "consequences": {"probabilistic_self_stage_effect_uncertainty": secondary}}, {"branch": "miss", "probability_percent": 20, "consequences": {"target_damage": 0, "hit_triggered_stage_effects": None}}), "guaranteed_facts": facts}
    return {"schema_version": "deterministic-strategy-orchestration-result-v1", "status": "resolved", "session_id": "secondary-surface", "decision_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "selection_completeness": "complete", "candidates": [{"candidate_id": "attack:metal-claw", "action_type": "attack", "evidence_class": "hit_miss_uncertainty", "facts": facts, "uncertainty": hit}], "ranking": {"status": "resolved", "preferred_frontier": ["attack:metal-claw"], "pairwise_matrix": []}}


def test_metal_claw_conditional_effect_survives_surface_without_becoming_guaranteed():
    orchestration = _orchestration(_secondary())
    original = deepcopy(orchestration)
    explanation = explain_detached_strategy(orchestration=orchestration)
    presentation = present_strategy_explanation(explanation=explanation)
    summary = explanation["candidates"][0]["probabilistic_self_stage_effect_summaries"]
    row = presentation["candidates"][0]

    assert orchestration == original
    assert len(summary) == 1 and summary[0]["branch_path"] == "hit"
    assert summary[0]["conditional_on"] == "successful_damaging_hit"
    assert summary[0]["uncertainty"]["effect_probability"] == {"numerator": 10, "denominator": 100}
    assert summary[0]["uncertainty"]["branches"][0]["conditional_secondary_probability"] == {"numerator": 90, "denominator": 100}
    assert summary[0]["uncertainty"]["branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == 1
    assert row["probabilistic_self_stage_effect_summaries"] == summary
    assert "hit 성공 명중 후 Attack +1 가능: 10/100 (미발동 90/100)" in row["uncertainty_labels"]
    assert "guaranteed_attack_stage" not in row["guaranteed_facts"]


def test_sheer_force_suppression_keeps_provenance_without_possible_attack_increase():
    explanation = explain_detached_strategy(orchestration=_orchestration(_secondary(suppressed=True)))
    row = present_strategy_explanation(explanation=explanation)["candidates"][0]
    summary = row["probabilistic_self_stage_effect_summaries"]

    assert summary[0]["uncertainty"]["effect_probability"] == {"numerator": 0, "denominator": 100}
    assert [branch["branch"] for branch in summary[0]["uncertainty"]["branches"]] == ["no_effect"]
    assert "hit 성공 명중 후 Attack +1: 억제됨 (0/100)" in row["uncertainty_labels"]


def test_crit_leaf_summaries_remain_distinct_without_changing_outer_hit_semantics():
    orchestration = _orchestration(_secondary())
    hit = orchestration["candidates"][0]["uncertainty"]["branches"][0]
    hit["consequences"] = {"critical_hit_uncertainty": {"status": "resolved", "schema_version": "deterministic-predictive-critical-hit-uncertainty-v1", "move_id": "metal-claw", "critical_probability": {"numerator": 1, "denominator": 24}, "branches": ({"branch": "non_critical", "consequences": {"probabilistic_self_stage_effect_uncertainty": _secondary()}}, {"branch": "critical", "consequences": {"probabilistic_self_stage_effect_uncertainty": _secondary()}}), "guaranteed_facts": {}}}

    explanation = explain_detached_strategy(orchestration=orchestration)
    row = explanation["candidates"][0]

    assert [item["branch_path"] for item in row["probabilistic_self_stage_effect_summaries"]] == ["hit/non_critical", "hit/critical"]
    assert row["hit_miss_uncertainty"]["probability_percent"] == 80
    assert row["critical_hit_uncertainty"]["critical_probability"] == {"numerator": 1, "denominator": 24}


def test_malformed_leaf_secondary_fails_closed_instead_of_becoming_a_neutral_effect():
    orchestration = _orchestration(_secondary())
    orchestration["candidates"][0]["uncertainty"]["branches"][0]["consequences"]["probabilistic_self_stage_effect_uncertainty"] = "unknown"

    result = explain_detached_strategy(orchestration=orchestration)

    assert result == {"status": "rejected", "reason": "invalid_probabilistic_self_stage_effect_uncertainty_evidence"}
