from copy import deepcopy

from llm.advisor_predictive_probabilistic_self_stage_effect_uncertainty import (
    compose_predictive_probabilistic_self_stage_effect_uncertainty,
)


def _owner(side, pokemon_id):
    return {"session_id": "secondary", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _candidate():
    owner = _owner("self", "attacker")
    return {"candidate_id": "attack:metal-claw", "action_type": "attack", "session_id": "secondary", "source_branch_fingerprint": "preview", "decision_owner": owner}


def _authority(*, stage=0, numerator=10, status="resolved"):
    attacker, target = _owner("self", "attacker"), _owner("opponent", "target")
    if status != "resolved":
        return {"status": status, "reason": "authority_unavailable"}
    current = {"status": "known", "value": stage, "provenance": "runtime_battle_state_v1"}
    stages = {"attack": current, "defense": {"status": "unknown"}, "special-attack": {"status": "unknown"}, "special-defense": {"status": "unknown"}, "speed": {"status": "unknown"}, "accuracy": {"status": "unknown"}, "evasion": {"status": "unknown"}}
    return {
        "status": "resolved", "schema_version": "runtime-d0-probabilistic-self-stage-effect-authority-v1",
        "session_id": "secondary", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview",
        "decision_owner": attacker, "attacker": attacker, "target": target,
        "move": {"move_id": "metal-claw"},
        "capability_resolution": {"status": "resolved", "move_id": "metal-claw", "probability": {"numerator": numerator, "denominator": 100}, "effect": {"owner": "self", "stat": "attack", "delta": 1}, "suppressed": numerator == 0},
        "current_stage_authority": {"status": "resolved", "schema_version": "runtime-current-stage-authority-v1", "session_id": "secondary", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "owner": attacker, "stages": stages},
        "current_attack_stage": current,
    }


def _interval(*, route="target", rolls=(20,) * 16):
    return {"completeness": "exact_complete", "session_id": "secondary", "source_branch_fingerprint": "preview", "decision_owner": _owner("self", "attacker"), "move_id": "metal-claw", "target_routing": route, "exact_damage_rolls": rolls}


def test_metal_claw_branches_exact_probability_and_hypothetical_stage_without_mutation():
    authority, interval = _authority(), _interval()
    original = deepcopy((authority, interval))
    result = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=interval, runtime_authority=authority)
    assert [row["branch"] for row in result["branches"]] == ["no_effect", "effect"]
    assert result["branches"][0]["conditional_secondary_probability"] == {"numerator": 90, "denominator": 100}
    assert result["branches"][1]["conditional_secondary_probability"] == {"numerator": 10, "denominator": 100}
    assert result["branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == 1
    assert result["guaranteed_effects"] == () and result["possible_effects"][0]["previous_stage"] == 0
    assert (authority, interval) == original


def test_nonzero_cap_substitute_and_suppression_have_correct_branch_semantics():
    nonzero = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(stage=4))
    capped = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(route="substitute"), runtime_authority=_authority(stage=6))
    suppressed = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(numerator=0))
    assert nonzero["branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == 5
    assert capped["branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == 6
    assert [row["branch"] for row in suppressed["branches"]] == ["no_effect"] and suppressed["possible_effects"] == ()


def test_miss_or_non_damaging_leaf_and_unavailable_authority_fail_closed():
    miss = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(rolls=(0,) * 16), runtime_authority=_authority())
    unsupported = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(status="unsupported"))
    stale = _authority(); stale["source_branch_fingerprint"] = "stale"
    rejected = compose_predictive_probabilistic_self_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=stale)
    assert miss["status"] == "rejected" and unsupported["status"] == "unsupported" and rejected["status"] == "rejected"
