"""Native train-subset provenance and unchanged fresh categorical PPO seams."""
import json
import os
from hashlib import sha256
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
from advisor.learned_encoder import fingerprint
from advisor.learned_full_roster import load_bank, study_identity
from advisor.learned_training_subset import NativeTrainingSubset, SubsetProbeBank, VERSION
from advisor.learned_evaluation_bank import EvaluationCaseBank
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"
ENCODER = "showdown-public-categorical-observation-v3"


def subset(tmp_path, count=1, **changes):
    indices = list(range(count))
    c = {"schema_version": VERSION, "engine_commit": SHOWDOWN_COMMIT,
         "format_id": FORMAT_ID, "parent_curriculum": "showdown-learning-curriculum-v8",
         "parent_split": "train", "parent_bank_sha256": study_identity()["bank_sha256"],
         "team_indices": indices,
         "team_sha256": [fingerprint(load_bank()["teams"]["train"][i]) for i in indices],
         "selection_mode": "shared_fixed_ordered3" if count == 1 else "independent_random_ordered3",
         "preview": [1, 2, 3] if count == 1 else None, "seed_namespace": "test-ladder-v1",
         **changes}
    path = tmp_path / "subset.json"
    path.write_text(json.dumps(c), encoding="utf-8")
    return path, sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("count", [1, 16])
def test_native_membership_deterministic_seed_and_no_original_mutation(tmp_path, count):
    path, identity = subset(tmp_path, count)
    p = NativeTrainingSubset(path, identity)
    before = fingerprint(load_bank())
    assert p("train", 173) == p("train", 173)
    assert p("train", 173)["seed"] != p.probe("validation", 173)["seed"]
    assert len(p.teams) == count
    cases = [p("train", i) for i in range(100)]
    assert {fingerprint(t) for c in cases for t in c["teams"].values()} <= set(p.identity["team_sha256"])
    if count == 1:
        assert all(c["teams"]["self"] == c["teams"]["opponent"] and
                   c["preview"] == {"self": [1, 2, 3], "opponent": [1, 2, 3]} for c in cases)
    else:
        assert len({tuple(c["preview"]["self"]) for c in cases}) > 10
    cases[0]["teams"]["self"][0]["moves"].clear()
    assert fingerprint(load_bank()) == before
    with pytest.raises(ValueError, match="partition"):
        p("test", 173)
    with pytest.raises(ValueError, match="invalid_subset"):
        p("train", True)


@pytest.mark.parametrize("changes", [
    {"parent_split": "test"}, {"engine_commit": "future"}, {"team_indices": [0, 0]},
    {"team_sha256": ["wrong"]}, {"selection_mode": "oracle_best_three"},
])
def test_subset_fail_closed(tmp_path, changes):
    path, identity = subset(tmp_path, **changes)
    with pytest.raises(ValueError):
        NativeTrainingSubset(path, identity)
    with pytest.raises(ValueError, match="hash"):
        NativeTrainingSubset(path, "wrong")


def test_probe_bank_explicitly_separates_heldout(tmp_path):
    path, identity = subset(tmp_path)
    p = NativeTrainingSubset(path, identity)
    bank = {"schema_version": "showdown-experimental-evaluation-bank-v1",
            "scope": "validation", "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID, "native_validated": True,
            "panels": {"heldout": load_bank()["teams"]["train"][16:18]}}
    file = tmp_path / "heldout.json"
    file.write_text(json.dumps(bank), encoding="utf-8")
    probe = SubsetProbeBank(p, EvaluationCaseBank(file, sha256(file.read_bytes()).hexdigest(), scope="validation"))
    assert "probe" in probe("validation", 12)["scenario_id"]
    assert "heldout" in probe("validation", 13)["scenario_id"]
    bank["panels"]["heldout"] = p.teams
    file.write_text(json.dumps(bank))
    with pytest.raises(ValueError, match="overlap"):
        SubsetProbeBank(p, EvaluationCaseBank(file, sha256(file.read_bytes()).hexdigest(), scope="validation"))


def test_native_fresh_policy_and_rollout_measurements(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned native engine required")
    from stable_baselines3.common.vec_env import DummyVecEnv
    from sb3_contrib import MaskablePPO
    from advisor.learned_action_encoder import make_encoder
    from advisor.learned_public_categories_policy import PublicCategoricalPolicy
    from advisor.learned_gym import ShowdownLearningEnv, OPAQUE_TERMINAL
    from scripts.train_showdown_autonomous import BudgetCallback, optimizer_steps
    path, identity = subset(tmp_path)
    encoder = make_encoder(CATALOG, ENCODER)
    vector = DummyVecEnv([lambda: ShowdownLearningEnv(checkout, encoder,
        curriculum_version="showdown-learning-curriculum-v8", opponents=["max_power"],
        training_subset=NativeTrainingSubset(path, identity), terminal_transport_version=OPAQUE_TERMINAL)])
    try:
        args = {"n_steps": 16, "batch_size": 16, "n_epochs": 4, "seed": 74011,
                "gamma": 1., "gae_lambda": .95, "learning_rate": 5e-5, "ent_coef": .01}
        a, b = (MaskablePPO(PublicCategoricalPolicy, vector, **args) for _ in range(2))
        assert optimizer_steps(a) == optimizer_steps(b) == 0
        assert not a.policy.optimizer.state and not b.policy.optimizer.state
        assert all(torch.equal(v, b.policy.state_dict()[k]) for k, v in a.policy.state_dict().items())
        obs = torch.as_tensor(vector.reset())
        mask = np.asarray(vector.env_method("action_masks"))
        with torch.no_grad():
            d1 = a.policy.get_distribution(obs, action_masks=mask).distribution.probs
            d2 = b.policy.get_distribution(obs, action_masks=mask).distribution.probs
        assert torch.equal(d1, d2) and not torch.any(d1[~torch.as_tensor(mask)])
        class Budget:
            def stopping(self): return False
        callback = BudgetCallback(Budget(), collect_diagnostics=True)
        a.learn(32, callback=callback)
        assert optimizer_steps(a) > 0 and a.num_timesteps == 32
        assert len(callback.measurements["rollouts"]) == 2
        assert callback.measurements["ppo_update_seconds"] > 0
        assert all(0 <= q <= 1 for row in callback.measurements["rollouts"]
                   for q in row["max_legal_action_probability_quantiles"])
        assert any(not torch.equal(v, b.policy.state_dict()[k]) for k, v in a.policy.state_dict().items())
        from advisor.learned_policy import LearnedPolicy
        from scripts.train_showdown_autonomous import save_checkpoint
        file = save_checkpoint(a, encoder, tmp_path / "saved", {"training_subset_identity": NativeTrainingSubset(path, identity).identity})
        assert LearnedPolicy(file, CATALOG).model.gamma == 1.
    finally:
        vector.close()


def test_public_move_opportunity_families():
    from advisor.learned_public_metrics import public_move_families
    assert public_move_families("swordsdance")["setup"]
    assert not public_move_families("recover")["attack"]
    assert public_move_families("flamethrower")["attack"]


def test_native_subset_spawn_and_policy_info_boundary(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned native engine required")
    from stable_baselines3.common.vec_env import SubprocVecEnv
    from advisor.learned_parallel import LearningEnvFactory
    path, identity = subset(tmp_path)
    vector = SubprocVecEnv([LearningEnvFactory(checkout, str(CATALOG), ENCODER,
        i * 100000, "showdown-learning-curriculum-v8", ("max_power",), {},
        training_subset_path=str(path), training_subset_sha256=identity) for i in range(2)], start_method="spawn")
    try:
        vector.seed(73011)
        obs = vector.reset()
        assert obs.shape == (2, 15576)
        masks = vector.env_method("action_masks")
        actions = [int(np.flatnonzero(m)[-1]) for m in masks]
        _, _, _, infos = vector.step(actions)
        assert all(not {"teams", "seed", "training_subset", "training_subset_sha256"} & set(info) for info in infos)
        cursors = vector.env_method("episode_cursor")
        assert all(cursor["episode_identity"]["training_subset_sha256"] == identity for cursor in cursors)
    finally:
        vector.close()
