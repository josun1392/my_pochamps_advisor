from copy import deepcopy

from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import present_strategy_explanation


OWNER = {"session_id": "thunderbolt-surface", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}
TARGET = {"session_id": "thunderbolt-surface", "side": "opponent", "slot_index": 0, "pokemon_id": "target"}


def _leaf(index, *, ko=False, blocked=None):
    if ko:
        return {"roll_index": index, "random_factor_percent": 85 + index, "damage": 100, "roll_probability": {"numerator": 1, "denominator": 16}, "target_post_hit_hp": 0, "target_survived": False, "secondary_eligibility": "target_fainted", "secondary_branches": ()}
    if blocked:
        return {"roll_index": index, "random_factor_percent": 85 + index, "damage": 20, "roll_probability": {"numerator": 1, "denominator": 16}, "target_post_hit_hp": 80, "target_survived": True, "secondary_eligibility": blocked, "secondary_branches": ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 100, "denominator": 100}},)}
    condition = {"schema_version": "detached-hypothetical-current-condition-v1", "owner": TARGET, "previous_condition": {"status": "known_none"}, "resulting_condition": "paralysis", "provenance": "thunderbolt_successful_damage_roll_secondary_v1"}
    return {"roll_index": index, "random_factor_percent": 85 + index, "damage": 20, "roll_probability": {"numerator": 1, "denominator": 16}, "target_post_hit_hp": 80, "target_survived": True, "secondary_eligibility": "eligible", "secondary_branches": ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 90, "denominator": 100}}, {"branch": "effect", "conditional_secondary_probability": {"numerator": 10, "denominator": 100}, "hypothetical_target_condition": condition})}


def _secondary(*, blocked=None, ko_indices=()):
    leaves = tuple(_leaf(index, ko=index in ko_indices, blocked=blocked) for index in range(16))
    eligible = next((leaf for leaf in leaves if leaf["secondary_eligibility"] == "eligible"), None)
    possible = () if eligible is None else ({"roll_index": eligible["roll_index"], "hypothetical_target_condition": eligible["secondary_branches"][1]["hypothetical_target_condition"]},)
    return {"status": "resolved", "schema_version": "deterministic-predictive-thunderbolt-paralysis-uncertainty-v1", "move_id": "thunderbolt", "effect_probability": {"numerator": 0 if blocked == "ineligible_or_suppressed" else 10, "denominator": 100}, "current_target_condition_authority": {"status": "resolved", "schema_version": "runtime-current-condition-authority-v1", "session_id": OWNER["session_id"], "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "owner": TARGET, "condition": {"status": "known_none"}}, "damage_roll_leaves": leaves, "possible_conditions": possible, "guaranteed_conditions": ()}


def _orchestration(secondary):
    facts = {"guaranteed_opponent_fainted": None, "possible_opponent_ko": True}
    hit = {"status": "resolved", "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1", "move_id": "thunderbolt", "probability_percent": 80, "branches": ({"branch": "hit", "probability_percent": 80, "consequences": {"thunderbolt_paralysis_uncertainty": secondary}}, {"branch": "miss", "probability_percent": 20, "consequences": {"target_damage": 0}}), "guaranteed_facts": facts}
    return {"schema_version": "deterministic-strategy-orchestration-result-v1", "status": "resolved", "session_id": OWNER["session_id"], "decision_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "selection_completeness": "complete", "candidates": [{"candidate_id": "attack:thunderbolt", "action_type": "attack", "evidence_class": "hit_miss_uncertainty", "facts": facts, "uncertainty": hit}], "ranking": {"status": "resolved", "preferred_frontier": ["attack:thunderbolt"], "pairwise_matrix": []}}


def test_surviving_thunderbolt_rolls_surface_conditional_ten_ninety_without_guaranteeing_paralysis():
    orchestration = _orchestration(_secondary())
    original = deepcopy(orchestration)
    explanation = explain_detached_strategy(orchestration=orchestration)
    row = present_strategy_explanation(explanation=explanation)["candidates"][0]
    summary = row["thunderbolt_paralysis_summaries"]
    assert orchestration == original
    assert summary[0]["branch_path"] == "hit" and summary[0]["conditional_on"] == "surviving_direct_damage_roll"
    assert summary[0]["uncertainty"]["effect_probability"] == {"numerator": 10, "denominator": 100}
    assert summary[0]["uncertainty"]["damage_roll_leaves"][0]["secondary_branches"][1]["hypothetical_target_condition"]["resulting_condition"] == "paralysis"
    assert summary[0]["uncertainty"]["current_target_condition_authority"]["condition"] == {"status": "known_none"}
    assert "hit 생존 피해 roll 16/16개에서 상대 마비 가능: 10/100 (미발동 90/100)" in row["uncertainty_labels"]
    assert "guaranteed_target_condition" not in row["guaranteed_facts"]


def test_ko_and_blocked_or_ineligible_leaves_surface_no_possible_paralysis():
    ko = explain_detached_strategy(orchestration=_orchestration(_secondary(ko_indices={0})))
    ko_leaf = ko["candidates"][0]["thunderbolt_paralysis_summaries"][0]["uncertainty"]["damage_roll_leaves"][0]
    substitute = present_strategy_explanation(explanation=explain_detached_strategy(orchestration=_orchestration(_secondary(blocked="blocked_by_substitute"))))["candidates"][0]
    zero = present_strategy_explanation(explanation=explain_detached_strategy(orchestration=_orchestration(_secondary(blocked="ineligible_or_suppressed"))))["candidates"][0]
    assert ko_leaf["secondary_eligibility"] == "target_fainted" and ko_leaf["secondary_branches"] == ()
    assert substitute["thunderbolt_paralysis_summaries"][0]["uncertainty"]["possible_conditions"] == ()
    assert zero["thunderbolt_paralysis_summaries"][0]["uncertainty"]["possible_conditions"] == ()
    assert any("대타로 차단됨" in label for label in substitute["uncertainty_labels"])
    assert any("적용 불가 또는 억제됨" in label for label in zero["uncertainty_labels"])


def test_critical_paths_remain_distinct_and_malformed_status_secondary_fails_closed():
    orchestration = _orchestration(_secondary())
    hit = orchestration["candidates"][0]["uncertainty"]["branches"][0]
    hit["consequences"] = {"critical_hit_uncertainty": {"status": "resolved", "schema_version": "deterministic-predictive-critical-hit-uncertainty-v1", "move_id": "thunderbolt", "critical_probability": {"numerator": 1, "denominator": 24}, "branches": ({"branch": "non_critical", "consequences": {"thunderbolt_paralysis_uncertainty": _secondary()}}, {"branch": "critical", "consequences": {"thunderbolt_paralysis_uncertainty": _secondary()}}), "guaranteed_facts": {}}}
    explanation = explain_detached_strategy(orchestration=orchestration)
    assert [summary["branch_path"] for summary in explanation["candidates"][0]["thunderbolt_paralysis_summaries"]] == ["hit/non_critical", "hit/critical"]
    malformed = _orchestration(_secondary())
    malformed["candidates"][0]["uncertainty"]["branches"][0]["consequences"]["thunderbolt_paralysis_uncertainty"] = "unknown"
    assert explain_detached_strategy(orchestration=malformed) == {"status": "rejected", "reason": "invalid_thunderbolt_paralysis_uncertainty_evidence"}
