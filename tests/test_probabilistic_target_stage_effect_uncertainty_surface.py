from copy import deepcopy

from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import present_strategy_explanation


OWNER = {"session_id": "target-secondary-surface", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}


def _leaf(index, *, eligible=True, ko=False, blocked=None):
    if ko:
        return {"roll_index": index, "random_factor_percent": 85 + index, "damage": 100, "roll_probability": {"numerator": 1, "denominator": 16}, "target_post_hit_hp": 0, "target_survived": False, "secondary_eligibility": "target_fainted", "secondary_branches": ()}
    if blocked:
        return {"roll_index": index, "random_factor_percent": 85 + index, "damage": 20, "roll_probability": {"numerator": 1, "denominator": 16}, "target_post_hit_hp": 80, "target_survived": True, "secondary_eligibility": blocked, "secondary_branches": ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 100, "denominator": 100}},)}
    branches = (
        {"branch": "no_effect", "conditional_secondary_probability": {"numerator": 80, "denominator": 100}},
        {"branch": "effect", "conditional_secondary_probability": {"numerator": 20, "denominator": 100}, "hypothetical_stage_effect": {"owner": "target", "stat": "special-defense", "previous_stage": 0, "delta": -1, "resulting_stage": -1}},
    )
    return {"roll_index": index, "random_factor_percent": 85 + index, "damage": 20, "roll_probability": {"numerator": 1, "denominator": 16}, "target_post_hit_hp": 80, "target_survived": True, "secondary_eligibility": "eligible", "secondary_branches": branches}


def _secondary(*, blocked=None, ko_indices=()):
    leaves = tuple(_leaf(index, ko=index in ko_indices, blocked=blocked) for index in range(16))
    eligible = next((leaf for leaf in leaves if leaf["secondary_eligibility"] == "eligible"), None)
    possible = () if blocked or eligible is None else ({"roll_index": eligible["roll_index"], "effect": eligible["secondary_branches"][1]["hypothetical_stage_effect"]},)
    return {"status": "resolved", "schema_version": "deterministic-predictive-probabilistic-target-stage-effect-uncertainty-v1", "move_id": "shadow-ball", "effect_probability": {"numerator": 0 if blocked == "suppressed" else 20, "denominator": 100}, "damage_roll_leaves": leaves, "possible_effects": possible, "guaranteed_effects": ()}


def _orchestration(secondary):
    facts = {"guaranteed_opponent_fainted": None, "possible_opponent_ko": True}
    hit = {"status": "resolved", "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1", "move_id": "shadow-ball", "probability_percent": 80, "branches": ({"branch": "hit", "probability_percent": 80, "consequences": {"probabilistic_target_stage_effect_uncertainty": secondary}}, {"branch": "miss", "probability_percent": 20, "consequences": {"target_damage": 0, "hit_triggered_stage_effects": None}}), "guaranteed_facts": facts}
    return {"schema_version": "deterministic-strategy-orchestration-result-v1", "status": "resolved", "session_id": OWNER["session_id"], "decision_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "selection_completeness": "complete", "candidates": [{"candidate_id": "attack:shadow-ball", "action_type": "attack", "evidence_class": "hit_miss_uncertainty", "facts": facts, "uncertainty": hit}], "ranking": {"status": "resolved", "preferred_frontier": ["attack:shadow-ball"], "pairwise_matrix": []}}


def test_surviving_shadow_ball_rolls_surface_conditional_twenty_eighty_without_guaranteeing_drop():
    orchestration = _orchestration(_secondary())
    original = deepcopy(orchestration)
    explanation = explain_detached_strategy(orchestration=orchestration)
    row = present_strategy_explanation(explanation=explanation)["candidates"][0]
    summary = row["probabilistic_target_stage_effect_summaries"]

    assert orchestration == original
    assert summary[0]["branch_path"] == "hit" and summary[0]["conditional_on"] == "surviving_direct_damage_roll"
    assert summary[0]["uncertainty"]["effect_probability"] == {"numerator": 20, "denominator": 100}
    assert summary[0]["uncertainty"]["damage_roll_leaves"][0]["secondary_branches"][0]["conditional_secondary_probability"] == {"numerator": 80, "denominator": 100}
    assert summary[0]["uncertainty"]["damage_roll_leaves"][0]["secondary_branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == -1
    assert "hit 생존 피해 roll 16/16개에서 상대 SpD -1 가능: 20/100 (미발동 80/100)" in row["uncertainty_labels"]
    assert "guaranteed_target_special_defense_stage" not in row["guaranteed_facts"]


def test_ko_roll_has_no_target_secondary_and_substitute_or_suppression_has_no_possible_drop():
    ko = explain_detached_strategy(orchestration=_orchestration(_secondary(ko_indices={0})))
    ko_leaf = ko["candidates"][0]["probabilistic_target_stage_effect_summaries"][0]["uncertainty"]["damage_roll_leaves"][0]
    substitute = present_strategy_explanation(explanation=explain_detached_strategy(orchestration=_orchestration(_secondary(blocked="blocked_by_substitute"))))["candidates"][0]
    suppressed = present_strategy_explanation(explanation=explain_detached_strategy(orchestration=_orchestration(_secondary(blocked="suppressed"))))["candidates"][0]

    assert ko_leaf["secondary_eligibility"] == "target_fainted" and ko_leaf["secondary_branches"] == ()
    assert substitute["probabilistic_target_stage_effect_summaries"][0]["uncertainty"]["possible_effects"] == ()
    assert suppressed["probabilistic_target_stage_effect_summaries"][0]["uncertainty"]["possible_effects"] == ()
    assert any("대타로 차단됨" in label for label in substitute["uncertainty_labels"])
    assert any("억제됨 (0/100)" in label for label in suppressed["uncertainty_labels"])


def test_critical_paths_remain_distinct_and_malformed_target_secondary_fails_closed():
    orchestration = _orchestration(_secondary())
    hit = orchestration["candidates"][0]["uncertainty"]["branches"][0]
    hit["consequences"] = {"critical_hit_uncertainty": {"status": "resolved", "schema_version": "deterministic-predictive-critical-hit-uncertainty-v1", "move_id": "shadow-ball", "critical_probability": {"numerator": 1, "denominator": 24}, "branches": ({"branch": "non_critical", "consequences": {"probabilistic_target_stage_effect_uncertainty": _secondary()}}, {"branch": "critical", "consequences": {"probabilistic_target_stage_effect_uncertainty": _secondary()}}), "guaranteed_facts": {}}}

    explanation = explain_detached_strategy(orchestration=orchestration)
    assert [summary["branch_path"] for summary in explanation["candidates"][0]["probabilistic_target_stage_effect_summaries"]] == ["hit/non_critical", "hit/critical"]
    malformed = _orchestration(_secondary())
    malformed["candidates"][0]["uncertainty"]["branches"][0]["consequences"]["probabilistic_target_stage_effect_uncertainty"] = "unknown"
    assert explain_detached_strategy(orchestration=malformed) == {"status": "rejected", "reason": "invalid_probabilistic_target_stage_effect_uncertainty_evidence"}
