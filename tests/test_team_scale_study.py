from copy import deepcopy
from hashlib import sha256
import json
import pytest

from advisor.learned_team_scale import require_matched_configs, checkpoint_alerts
from advisor.learned_training_subset import (
    NativeTrainingSubset, full_native_training_population, VERSION_FULL,
)


def configs():
    result = []
    for population, seed in (("A", 96021), ("B", 96021), ("B", 96022), ("A", 96022)):
        result.append((f"{population}_{seed}", {
            "envs": 4, "cpu_percent": 50, "memory_mib": 12288,
            "transition_budget_scope": "trained_rollouts_v1",
            "training_subset": population, "training_subset_sha256": population * 64,
            "experiments": [{"name": f"{population}_{seed}", "seed": seed,
                "steps": 262144, "initial_model_id": "f" * 64, "fresh_optimizer": False,
                "gamma": 1, "opponents": ["max_power", "frozen", "frozen"]}]}))
    return result


def test_matched_population_is_the_only_training_change():
    assert require_matched_configs(configs(), "f" * 64)["trained_transitions"] == 1048576
    for mutate in (
        lambda c: c[1][1]["experiments"][0].update(gamma=.99),
        lambda c: c[1][1]["experiments"][0].update(fresh_optimizer=True),
        lambda c: c[1][1]["experiments"][0].update(opponents=["max_power"]),
        lambda c: c[1][1].update(cpu_percent=75),
        lambda c: c[1][1]["experiments"][0].update(seed=96023),
    ):
        changed = deepcopy(configs())
        mutate(changed)
        with pytest.raises(ValueError):
            require_matched_configs(changed, "f" * 64)


def write(tmp_path, value):
    path = tmp_path / "population.json"
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    return path, sha256(raw).hexdigest()


def test_full_population_exact_train_identity_and_reproducibility(tmp_path):
    from advisor.learned_full_roster import load_bank
    from advisor.learned_encoder import fingerprint
    contract = full_native_training_population(seed_namespace="team-scale-v1")
    assert contract == full_native_training_population(seed_namespace="team-scale-v1")
    assert contract["schema_version"] == VERSION_FULL
    population = NativeTrainingSubset(*write(tmp_path, contract))
    assert len(population.teams) == 4096
    assert population("train", 102210000) == population("train", 102210000)
    case = population("train", 102210000)
    for preview in case["preview"].values():
        assert len(preview) == len(set(preview)) == 3
        assert set(preview) <= set(range(1, 7))
    assert len(contract["team_sha256"]) == len(set(contract["team_sha256"])) == 4096
    validation = {fingerprint(t) for t in load_bank()["teams"]["validation"]}
    assert not set(contract["team_sha256"]) & validation
    with pytest.raises(ValueError, match="partition_access_denied"):
        population("validation", 0)


def test_full_population_rejects_reordered_or_partial_membership(tmp_path):
    contract = full_native_training_population(seed_namespace="test")
    for value in ("reorder", "partial", "false_membership"):
        broken = deepcopy(contract)
        if value == "reorder":
            broken["team_indices"].reverse()
            broken["team_sha256"].reverse()
        elif value == "partial":
            broken["team_indices"].pop()
            broken["team_sha256"].pop()
        else:
            broken["membership"] = "assumed_all"
        with pytest.raises(ValueError):
            NativeTrainingSubset(*write(tmp_path, broken))


def test_operational_guard_does_not_select_by_wins():
    state = {"trained_rollout_transitions": 65536}
    metadata = {"training_metrics": {"ppo": {"train/approx_kl": .02}},
                "episode_outcomes_this_checkpoint": {"self": 0, "opponent": 1000}}
    assert checkpoint_alerts(metadata, state, {"trained": 32768}) == []
    metadata["training_metrics"]["ppo"]["train/approx_kl"] = .11
    assert "KL_above_0.1" in checkpoint_alerts(metadata, state, None)
