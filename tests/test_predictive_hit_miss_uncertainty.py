from copy import deepcopy

from llm.advisor_predictive_hit_miss_uncertainty import compose_predictive_hit_miss_uncertainty
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_strict_hit_probability_assessment
from tests.test_runtime_hit_modifier_authority import _d0, _hustle, _owner, _state


def _move(*, accuracy=100, category="physical", move_id="tackle"):
    return {"move_id": move_id, "category": category, "accuracy": accuracy}


def _probability(*, accuracy=100, category="physical", attacker_stage=0, target_stage=0):
    state = _state()
    _hustle(state)
    state["self_side"]["pokemon"][0]["stat_stages"]["accuracy"] = attacker_stage
    state["opponent_side"]["pokemon"][0]["stat_stages"]["evasion"] = target_stage
    snapshot, d0 = _d0(state)
    probability = build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"),
        selected_move=_move(accuracy=accuracy, category=category),
    )
    candidate = {
        "candidate_id": "attack:tackle", "action_type": "attack", "session_id": state["session_id"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": _owner(state),
    }
    return state, candidate, probability


def _hit_facts(candidate, *, ko=True, own_hp=90, possible=False):
    return {
        "status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1",
        "candidate_id": candidate["candidate_id"], "action_type": "attack", "session_id": candidate["session_id"],
        "source_branch_fingerprint": candidate["source_branch_fingerprint"], "decision_owner": candidate["decision_owner"],
        "horizon": "immediate_action_consequence", "evidence_class": "hit_only_test",
        "guaranteed_own_fainted": False, "guaranteed_opponent_fainted": ko,
        "exact_own_hp": own_hp, "possible_opponent_ko": possible, "substitute_facts": {}, "provenance": "test",
    }


def _compose(state, candidate, probability, *, ko=True, own_hp=90, possible=False):
    facts = _hit_facts(candidate, ko=ko, own_hp=own_hp, possible=possible)
    consequence = {"interval": {"scope": {"hit": "assumed"}}, "post_hit": {"life_orb_recoil": 10}, "stage_effects": {"effects": ("speed+1",)}, "guaranteed_facts": facts}
    return compose_predictive_hit_miss_uncertainty(
        candidate=candidate, strict_hit_probability=probability, hit_consequences=consequence,
        miss_baseline={"attacker_current_hp": 100, "target_current_hp": 100},
    )


def test_hit_only_and_miss_only_cardinality_preserve_exact_probability_boundary():
    state, candidate, guaranteed = _probability(category="special")
    hit_only = _compose(state, candidate, guaranteed)
    assert hit_only["status"] == "resolved"
    assert [branch["branch"] for branch in hit_only["branches"]] == ["hit"]
    assert hit_only["probability_percent"] == 100

    state, candidate, zero = _probability(accuracy=1, attacker_stage=-6)
    miss_only = _compose(state, candidate, zero)
    assert [branch["branch"] for branch in miss_only["branches"]] == ["miss"]
    assert miss_only["raw_accuracy_threshold"] == miss_only["probability_percent"] == 0


def test_intermediate_hustle_branches_are_detached_and_miss_has_no_hit_effects():
    state, candidate, probability = _probability(accuracy=100)
    original_state, original_probability = deepcopy(state), deepcopy(probability)
    result = _compose(state, candidate, probability)
    assert probability["probability_percent"] == 80
    assert [(branch["branch"], branch["probability_percent"]) for branch in result["branches"]] == [("hit", 80), ("miss", 20)]
    hit, miss = result["branches"]
    assert hit["consequences"]["post_hit"] == {"life_orb_recoil": 10}
    assert miss["consequences"] == {"target_damage": 0, "hit_triggered_post_hit": None, "hit_triggered_stage_effects": None, "attacker_hp_after": 100, "target_hp_after": 100}
    assert state == original_state and probability == original_probability


def test_global_facts_are_intersection_safe_and_possible_ko_remains_branch_local():
    state, candidate, probability = _probability(accuracy=100)
    result = _compose(state, candidate, probability, ko=True)
    assert result["branches"][0]["branch_facts"]["guaranteed_opponent_fainted"] is True
    assert result["guaranteed_facts"]["guaranteed_opponent_fainted"] is None
    assert result["guaranteed_facts"]["possible_opponent_ko"] is True
    assert result["guaranteed_facts"]["exact_own_hp"] is None


def test_incomplete_unsupported_stale_and_binding_mismatch_fail_closed():
    state, candidate, probability = _probability(accuracy=100)
    for status, reason in (("incomplete", "hustle_applicability_unknown"), ("unsupported", "unsupported_ability"), ("rejected", "stale_runtime_d0")):
        unavailable = {"status": status, "reason": reason}
        result = compose_predictive_hit_miss_uncertainty(candidate=candidate, strict_hit_probability=unavailable, hit_consequences={"guaranteed_facts": _hit_facts(candidate)}, miss_baseline={"attacker_current_hp": 100})
        assert result["status"] == status and result["reason"] == reason
    foreign = deepcopy(probability)
    foreign["source_branch_fingerprint"] = "other"
    assert _compose(state, candidate, foreign)["status"] == "rejected"
