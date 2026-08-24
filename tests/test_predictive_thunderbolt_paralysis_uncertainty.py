from copy import deepcopy

from llm.advisor_predictive_thunderbolt_paralysis_uncertainty import compose_predictive_thunderbolt_paralysis_uncertainty


def _owner(side, pokemon_id):
    return {"session_id": "thunderbolt-secondary", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _candidate():
    return {"candidate_id": "attack:thunderbolt", "action_type": "attack", "session_id": "thunderbolt-secondary", "source_branch_fingerprint": "preview", "decision_owner": _owner("self", "attacker")}


def _authority(*, numerator=10, condition=None, substitute="known_inactive", status="resolved"):
    attacker, target = _owner("self", "attacker"), _owner("opponent", "target")
    if status != "resolved": return {"status": status, "reason": "authority_unavailable"}
    current = {"status": "known_none"} if condition is None else condition
    strict = {"status": "resolved", "schema_version": "runtime-current-condition-authority-v1", "session_id": "thunderbolt-secondary", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "owner": target, "condition": current}
    sub = {"status": "known", "state": substitute}
    if substitute == "known_active": sub["substitute_hp"] = 25
    return {"status": "resolved", "schema_version": "runtime-d0-thunderbolt-paralysis-authority-v1", "session_id": "thunderbolt-secondary", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": attacker, "attacker": attacker, "target": target, "move": {"move_id": "thunderbolt"}, "capability_resolution": {"status": "resolved", "move_id": "thunderbolt", "probability": {"numerator": numerator, "denominator": 100}, "effect": {"owner": "target", "condition": "paralysis"}, "suppressed": numerator == 0}, "current_target_condition_authority": strict, "target_type_authority": {"status": "known", "values": ["water"]}, "target_substitute_authority": sub}


def _interval(*, hp=100, rolls=(20,) * 16, route="target"):
    return {"completeness": "exact_complete", "session_id": "thunderbolt-secondary", "source_branch_fingerprint": "preview", "decision_owner": _owner("self", "attacker"), "move_id": "thunderbolt", "target_routing": route, "target_hp_before": hp, "exact_damage_rolls": rolls}


def test_surviving_thunderbolt_rolls_branch_exact_ninety_ten_with_detached_paralysis():
    authority, interval = _authority(), _interval()
    original = deepcopy((authority, interval))
    result = compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=interval, runtime_authority=authority)
    leaf = result["damage_roll_leaves"][0]
    assert result["status"] == "resolved" and len(result["damage_roll_leaves"]) == 16
    assert [row["branch"] for row in leaf["secondary_branches"]] == ["no_effect", "effect"]
    assert [row["conditional_secondary_probability"] for row in leaf["secondary_branches"]] == [{"numerator": 90, "denominator": 100}, {"numerator": 10, "denominator": 100}]
    assert leaf["secondary_branches"][1]["hypothetical_target_condition"]["resulting_condition"] == "paralysis"
    assert result["current_target_condition_authority"]["condition"] == {"status": "known_none"}
    assert result["guaranteed_conditions"] == () and len(result["possible_conditions"]) == 16 and (authority, interval) == original


def test_ko_rolls_and_zero_probability_or_substitute_have_no_possible_paralysis():
    rolls = (20, 100, 110, 20, 100, 110, 20, 100, 110, 20, 100, 110, 20, 100, 110, 20)
    ko = compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(rolls=rolls), runtime_authority=_authority())
    active = compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(substitute="known_active"))
    zero = compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(numerator=0))
    assert ko["damage_roll_leaves"][1]["secondary_eligibility"] == "target_fainted" and ko["damage_roll_leaves"][1]["secondary_branches"] == ()
    assert len(ko["possible_conditions"]) == 6
    assert active["damage_roll_leaves"][0]["secondary_eligibility"] == "blocked_by_substitute" and active["possible_conditions"] == ()
    assert zero["damage_roll_leaves"][0]["secondary_eligibility"] == "ineligible_or_suppressed" and zero["possible_conditions"] == ()


def test_incomplete_unsupported_stale_and_non_direct_inputs_fail_closed():
    stale = _authority(); stale["source_branch_fingerprint"] = "stale"
    assert compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(status="incomplete"))["status"] == "incomplete"
    assert compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=_authority(status="unsupported"))["status"] == "unsupported"
    assert compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(), runtime_authority=stale)["status"] == "rejected"
    assert compose_predictive_thunderbolt_paralysis_uncertainty(candidate=_candidate(), interval=_interval(route="substitute"), runtime_authority=_authority())["status"] == "rejected"
