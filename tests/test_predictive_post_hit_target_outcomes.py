from llm.advisor_predictive_post_hit_target_outcomes import resolve_predictive_post_hit_target_outcomes


def _interval():
    return {
        "session_id": "session", "source_branch_fingerprint": "branch",
        "decision_owner": {"side": "self", "pokemon_id": "own"},
        "move_id": "thunderbolt", "target_hp_before": 10,
        "exact_damage_rolls": tuple(range(10, 26)),
    }


def _post(interval):
    return {
        "status": "resolved", "schema_version": "deterministic-predictive-normal-formula-post-hit-v1",
        "session_id": interval["session_id"], "source_branch_fingerprint": interval["source_branch_fingerprint"],
        "decision_owner": interval["decision_owner"], "move_id": interval["move_id"],
        "branches": tuple({"raw_damage": damage, "actual_damage": 9} for damage in interval["exact_damage_rolls"]),
    }


def test_exact_post_hit_outcomes_preserve_raw_rolls_and_reject_foreign_post_hit_authority():
    interval = _interval()
    resolved = resolve_predictive_post_hit_target_outcomes(interval=interval, post_hit=_post(interval))
    assert resolved["status"] == "resolved"
    assert all(row["raw_damage"] == interval["exact_damage_rolls"][index] and row["actual_damage"] == 9 and row["target_post_hit_hp"] == 1 and row["target_survived"] is True for index, row in enumerate(resolved["outcomes"]))

    foreign = _post(interval)
    foreign["source_branch_fingerprint"] = "foreign"
    assert resolve_predictive_post_hit_target_outcomes(interval=interval, post_hit=foreign) == {
        "status": "rejected", "reason": "post_hit_target_outcome_binding_mismatch",
    }
