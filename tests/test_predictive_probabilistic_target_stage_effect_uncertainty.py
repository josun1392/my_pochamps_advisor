from copy import deepcopy

from llm.advisor_predictive_probabilistic_target_stage_effect_uncertainty import (
    compose_predictive_probabilistic_target_stage_effect_uncertainty,
)


def _owner(side, pokemon_id):
    return {"session_id": "target-secondary", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _candidate():
    attacker = _owner("self", "attacker")
    return {"candidate_id": "attack:shadow-ball", "action_type": "attack", "session_id": "target-secondary", "source_branch_fingerprint": "preview", "decision_owner": attacker}


def _authority(*, stage=0, numerator=20, substitute="known_inactive", status="resolved"):
    attacker, target = _owner("self", "attacker"), _owner("opponent", "target")
    if status != "resolved":
        return {"status": status, "reason": "authority_unavailable"}
    current = {"status": "known", "value": stage, "provenance": "runtime_battle_state_v1"}
    stages = {"attack": {"status": "unknown"}, "defense": {"status": "unknown"}, "special-attack": {"status": "unknown"}, "special-defense": current, "speed": {"status": "unknown"}, "accuracy": {"status": "unknown"}, "evasion": {"status": "unknown"}}
    target_substitute = {"status": "known", "state": substitute}
    if substitute == "known_active":
        target_substitute["substitute_hp"] = 25
    return {
        "status": "resolved", "schema_version": "runtime-d0-probabilistic-target-stage-effect-authority-v1",
        "session_id": "target-secondary", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview",
        "decision_owner": attacker, "attacker": attacker, "target": target, "move": {"move_id": "shadow-ball"},
        "capability_resolution": {"status": "resolved", "move_id": "shadow-ball", "probability": {"numerator": numerator, "denominator": 100}, "effect": {"owner": "target", "stat": "special-defense", "delta": -1}, "suppressed": numerator == 0},
        "current_stage_authority": {"status": "resolved", "schema_version": "runtime-current-stage-authority-v1", "session_id": "target-secondary", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "owner": target, "stages": stages},
        "current_target_special_defense_stage": current, "target_substitute_authority": target_substitute,
    }


def _interval(*, hp=100, rolls=(20,) * 16, route="target"):
    return {"completeness": "exact_complete", "session_id": "target-secondary", "source_branch_fingerprint": "preview", "decision_owner": _owner("self", "attacker"), "move_id": "shadow-ball", "target_routing": route, "target_hp_before": hp, "exact_damage_rolls": rolls}


def test_surviving_shadow_ball_rolls_branch_exact_twenty_eighty_and_preserve_current_stage():
    authority, interval = _authority(), _interval()
    original = deepcopy((authority, interval))
    result = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=interval, runtime_authority=authority)

    leaf = result["damage_roll_leaves"][0]
    assert result["status"] == "resolved" and len(result["damage_roll_leaves"]) == 16
    assert leaf["secondary_eligibility"] == "eligible"
    assert [branch["branch"] for branch in leaf["secondary_branches"]] == ["no_effect", "effect"]
    assert leaf["secondary_branches"][0]["conditional_secondary_probability"] == {"numerator": 80, "denominator": 100}
    assert leaf["secondary_branches"][1]["conditional_secondary_probability"] == {"numerator": 20, "denominator": 100}
    assert leaf["secondary_branches"][1]["hypothetical_stage_effect"] == {"owner": "target", "stat": "special-defense", "previous_stage": 0, "delta": -1, "resulting_stage": -1}
    assert result["guaranteed_effects"] == () and result["possible_effects"][0]["roll_index"] == 0
    assert (authority, interval) == original


def test_nonzero_and_capped_target_stages_use_canonical_forward_stage_composition():
    nonzero = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(stage=3))
    capped = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(stage=-6))

    assert nonzero["damage_roll_leaves"][0]["secondary_branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == 2
    assert capped["damage_roll_leaves"][0]["secondary_branches"][1]["hypothetical_stage_effect"]["resulting_stage"] == -6


def test_ko_rolls_do_not_branch_and_roll_identity_and_multiplicity_are_retained():
    rolls = (80, 100, 110, 80, 100, 110, 80, 100, 110, 80, 100, 110, 80, 100, 110, 80)
    result = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(hp=100, rolls=rolls), runtime_authority=_authority())

    survivor, ko = result["damage_roll_leaves"][0], result["damage_roll_leaves"][1]
    assert survivor["target_survived"] is True and len(survivor["secondary_branches"]) == 2
    assert ko["target_survived"] is False and ko["secondary_eligibility"] == "target_fainted" and ko["secondary_branches"] == ()
    assert [(row["roll_index"], row["random_factor_percent"], row["roll_probability"]) for row in result["damage_roll_leaves"]] == [(index, 85 + index, {"numerator": 1, "denominator": 16}) for index in range(16)]
    assert len([row for row in result["damage_roll_leaves"] if row["damage"] == 80]) == 6


def test_substitute_and_resolved_suppressors_are_no_effect_only_without_possible_drop():
    substitute = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(substitute="known_active"))
    sheer_force = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(numerator=0))

    for result, eligibility in ((substitute, "blocked_by_substitute"), (sheer_force, "suppressed")):
        leaf = result["damage_roll_leaves"][0]
        assert leaf["secondary_eligibility"] == eligibility
        assert leaf["secondary_branches"] == ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 100, "denominator": 100}},)
        assert result["possible_effects"] == ()


def test_incomplete_unsupported_and_stale_or_non_direct_inputs_fail_closed():
    incomplete = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(status="incomplete"))
    unsupported = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(status="unsupported"))
    stale = _authority(); stale["source_branch_fingerprint"] = "stale"
    wrong_route = compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(route="substitute"), runtime_authority=_authority())

    assert incomplete["status"] == "incomplete" and unsupported["status"] == "unsupported"
    assert compose_predictive_probabilistic_target_stage_effect_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=stale)["status"] == "rejected"
    assert wrong_route["status"] == "rejected"
