from copy import deepcopy
import pytest

from advisor.learned_adam_study import matched_configs, game_slots, analyze, endpoint_clock, POLICIES
from scripts.train_showdown_autonomous import checkpoint_validation_enabled


def configs():
    base = {"envs": 4, "cpu_percent": 50, "memory_mib": 12288, "device": "cpu",
        "vector_backend": "subproc", "transition_budget_scope": "trained_rollouts_v1",
        "checkpoint_evaluation_mode": "disabled_for_frozen_study_v1",
        "validation_selection_mode": "diagnostic_fixed_budget_v1", "training_subset": "same",
        "experiments": [{"steps": 65536, "initial_model_id": "a"*64,
            "gamma": 1., "opponents": ["same"]}]}
    result = {}
    for key in POLICIES[1:]:
        c = deepcopy(base)
        c["experiments"][0].update(name=key, seed=int(key[2:]), fresh_optimizer=key.startswith("B"))
        result[key] = c
    return result


def test_only_optimizer_state_changes_and_exact_budget():
    assert matched_configs(configs(), "a"*64)["trained_transitions"] == 262144
    for field, value in (("gamma", .99), ("learning_rate", .01), ("fresh_optimizer", False),
                         ("steps", 32768), ("seed", 98112), ("parent_policy_anchor", {})):
        changed = configs()
        changed["B_98111"]["experiments"][0][field] = value
        with pytest.raises(ValueError):
            matched_configs(changed, "a"*64)


def test_validation_disable_is_opt_in_fixed_budget_only():
    assert checkpoint_validation_enabled({})
    assert not checkpoint_validation_enabled(configs()["A_98111"])
    for extra in ({"validation_selection_mode": "best_and_plateau"}, {"final_test_cases": 1},
                  {"checkpoint_evaluation_mode": "typo"}):
        with pytest.raises(ValueError):
            checkpoint_validation_enabled({**configs()["A_98111"], **extra})


def cases():
    return [{"scope": "train" if i < 96 else "heldout", "index": i,
             "scenario_sha256": str(i)} for i in range(192)]


def test_exact_argmax_pairing_budget_and_heldout_count():
    slots = game_slots(cases())
    assert len(slots) == 5760
    assert len({tuple(s.values()) for s in slots}) == len(slots)
    for policy in POLICIES:
        own = [s for s in slots if s["policy"] == policy]
        assert len(own) == 1152 and sum(s["scope"] == "heldout" for s in own) == 576
        assert sum(s["seat"] == "p1" for s in own) == 576
    with pytest.raises(ValueError):
        game_slots([{**cases()[0], "sampled": True}])


def test_paired_statistics_preserve_seeds_and_parent_retention():
    small = [cases()[0], cases()[96]]
    rows = [{"slot": s, "record": {"winner": "self" if s["policy"].startswith("B") else "opponent",
                                  "truncated": False}} for s in game_slots(small)]
    result = analyze(rows, small, resamples=64)
    primary = next(r for r in result["paired_differences"] if r["scope"] == "all"
        and r["rival"] == "all" and r["comparison"] == "mean_seed(B-A)")
    assert primary["delta"] == 1 and primary["case_cluster_95"] == [1, 1]
    assert {r["comparison"] for r in result["paired_differences"]} >= {"B_98111-A_98111", "B_98519-A_98519"}
    assert any(r["new_win"] == 6 for r in result["parent_win_retention_and_acquisition"])
    with pytest.raises(ValueError):
        analyze(rows[:-1], small, resamples=64)
    with pytest.raises(ValueError):
        analyze(rows+rows[:1], small, resamples=64)


def test_optimizer_endpoint_uses_actual_updates_not_assumed_full_epochs():
    assert endpoint_clock("A_98111", {"total_steps": 1114112, "optimizer_steps": 34816}) == 34816
    assert endpoint_clock("B_98111", {"total_steps": 1114112, "optimizer_steps": 1900}) == 1900
    for metadata in ({"total_steps": 1114112, "optimizer_steps": 34816},
                     {"total_steps": 1114111, "optimizer_steps": 2048},
                     {"total_steps": 1114112, "optimizer_steps": 0}):
        with pytest.raises(ValueError):
            endpoint_clock("B_98111", metadata)
