from copy import deepcopy

from llm.advisor_predictive_critical_damage_context import materialize_predictive_critical_damage_contexts
from llm.advisor_predictive_critical_hit_uncertainty import compose_predictive_critical_hit_uncertainty
from llm.advisor_predictive_hit_miss_uncertainty import compose_predictive_hit_miss_uncertainty
from tests.test_predictive_critical_damage_context import _context


def _pair():
    state, owner, target, damage, provenance = _context(stages=(-2, 2))
    paired = materialize_predictive_critical_damage_contexts(
        branch_state=state, decision_owner=owner, target_owner=target,
        snapshot_damage_input=damage, stat_provenance=provenance, trusted_level=50,
    )
    candidate = {"candidate_id": "attack:tackle", "action_type": "attack", "session_id": paired["session_id"], "source_branch_fingerprint": paired["source_branch_fingerprint"], "decision_owner": paired["decision_owner"]}
    return state, candidate, paired


def _probability(paired, numerator=1, denominator=24):
    return {
        "status": "resolved", "schema_version": "strict-critical-hit-probability-v1",
        "session_id": paired["session_id"], "source_runtime_fingerprint": "runtime-fingerprint",
        "source_branch_fingerprint": paired["source_branch_fingerprint"], "decision_owner": paired["decision_owner"],
        "attacker": paired["attacker"], "target": paired["target"], "move_id": paired["move_id"],
        "critical_probability": {"numerator": numerator, "denominator": denominator},
    }


def _facts(candidate, *, ko):
    return {
        "status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1",
        "candidate_id": candidate["candidate_id"], "action_type": "attack", "session_id": candidate["session_id"],
        "source_branch_fingerprint": candidate["source_branch_fingerprint"], "decision_owner": candidate["decision_owner"],
        "horizon": "immediate_action_consequence", "guaranteed_own_fainted": False,
        "guaranteed_opponent_fainted": ko, "exact_own_hp": 100, "possible_opponent_ko": False,
        "substitute_facts": {}, "provenance": "test",
    }


def _compose(*, numerator=1, denominator=24, non_critical_ko=False, critical_ko=True):
    _, candidate, paired = _pair()
    normal = {"interval": paired["non_critical_context"], "guaranteed_facts": _facts(candidate, ko=non_critical_ko)}
    critical = {"interval": paired["critical_context"], "guaranteed_facts": _facts(candidate, ko=critical_ko)}
    return candidate, paired, compose_predictive_critical_hit_uncertainty(
        candidate=candidate, strict_critical_hit_probability=_probability(paired, numerator, denominator),
        paired_damage_contexts=paired, non_critical_consequences=normal, critical_consequences=critical,
    )


def test_critical_branch_cardinality_preserves_exact_conditional_fraction_boundaries():
    _, _, zero = _compose(numerator=0, denominator=1)
    _, _, intermediate = _compose(numerator=1, denominator=2)
    _, _, certain = _compose(numerator=1, denominator=1)
    assert [branch["branch"] for branch in zero["branches"]] == ["non_critical"]
    assert [branch["branch"] for branch in intermediate["branches"]] == ["non_critical", "critical"]
    assert [branch["branch"] for branch in certain["branches"]] == ["critical"]
    assert intermediate["critical_probability"] == {"numerator": 1, "denominator": 2}


def test_crit_only_ko_is_possible_not_guaranteed_and_leaf_contexts_remain_distinct():
    _, paired, result = _compose(numerator=1, denominator=2, non_critical_ko=False, critical_ko=True)
    assert result["guaranteed_facts"]["guaranteed_opponent_fainted"] is None
    assert result["guaranteed_facts"]["possible_opponent_ko"] is True
    normal, critical = result["branches"]
    assert normal["damage_context"] == paired["non_critical_context"]
    assert critical["damage_context"] == paired["critical_context"]
    assert min(critical["damage_context"]["exact_damage_rolls"]) > min(normal["damage_context"]["exact_damage_rolls"])


def test_hit_miss_keeps_miss_outside_critical_consequences_and_intersects_both_dimensions():
    candidate, paired, critical = _compose(numerator=1, denominator=2, non_critical_ko=True, critical_ko=True)
    hit_probability = {
        "status": "resolved", "schema_version": "strict-deterministic-hit-probability-v1", "result": "exact_regular_accuracy",
        "session_id": paired["session_id"], "source_runtime_fingerprint": "runtime-fingerprint", "source_branch_fingerprint": paired["source_branch_fingerprint"],
        "decision_owner": paired["decision_owner"], "attacker": paired["attacker"], "target": paired["target"], "move_id": paired["move_id"],
        "probability_percent": 80, "raw_accuracy_threshold": 80,
    }
    result = compose_predictive_hit_miss_uncertainty(
        candidate=candidate, strict_hit_probability=hit_probability,
        hit_consequences={"critical_hit_uncertainty": critical, "guaranteed_facts": critical["guaranteed_facts"]},
        miss_baseline={"attacker_current_hp": 100, "target_current_hp": 100},
    )
    hit, miss = result["branches"]
    assert [branch["branch"] for branch in hit["consequences"]["critical_hit_uncertainty"]["branches"]] == ["non_critical", "critical"]
    assert miss["consequences"]["target_damage"] == 0 and miss["consequences"]["hit_triggered_post_hit"] is None
    assert result["guaranteed_facts"]["guaranteed_opponent_fainted"] is None
    assert result["guaranteed_facts"]["possible_opponent_ko"] is True


def test_unavailable_or_stale_critical_authority_fails_closed_without_mutation():
    state, candidate, paired = _pair()
    before = deepcopy((state, paired))
    consequences = {"guaranteed_facts": _facts(candidate, ko=False)}
    for status in ("incomplete", "unsupported", "rejected"):
        result = compose_predictive_critical_hit_uncertainty(
            candidate=candidate, strict_critical_hit_probability={"status": status, "reason": "unavailable"}, paired_damage_contexts=paired,
            non_critical_consequences=consequences, critical_consequences=consequences,
        )
        assert result["status"] == status
    stale = deepcopy(_probability(paired)); stale["source_branch_fingerprint"] = "stale"
    result = compose_predictive_critical_hit_uncertainty(
        candidate=candidate, strict_critical_hit_probability=stale, paired_damage_contexts=paired,
        non_critical_consequences=consequences, critical_consequences=consequences,
    )
    assert result["status"] == "rejected"
    assert (state, paired) == before
