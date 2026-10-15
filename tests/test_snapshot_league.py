"""Matched continuation, masked regularizer persistence and real seat ownership."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest
np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
gym = pytest.importorskip("gymnasium")
from sb3_contrib import MaskablePPO
from advisor.learned_regularized_ppo import RegularizedMaskablePPO, legal_uniform_kl, regularizer_contract
from advisor.learned_snapshot_league import generation_mixture, append_generation_event, read_generation_events, validate_child

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"


class MaskedFixture(gym.Env):
    observation_space = gym.spaces.Box(-1, 1, shape=(3,), dtype=np.float32)
    action_space = gym.spaces.Discrete(4)
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        return np.array([.1, .2, .3], dtype=np.float32), {}
    def action_masks(self):
        return np.array([True, True, False, False])
    def step(self, action):
        assert self.action_masks()[action]
        self.steps += 1
        return np.array([.1, .2, .3], dtype=np.float32), float(action == 1), self.steps == 4, False, {}


def same_optimizer(a, b):
    def compare(x, y):
        if isinstance(x, torch.Tensor): return torch.equal(x, y)
        if isinstance(x, dict): return x.keys() == y.keys() and all(compare(x[k], y[k]) for k in x)
        if isinstance(x, list): return len(x) == len(y) and all(compare(v, w) for v, w in zip(x, y))
        return x == y
    return compare(a.policy.optimizer.state_dict(), b.policy.optimizer.state_dict())


def test_reverse_kl_masks_singleton_stability_and_gradient():
    logits = torch.tensor([[2., -3., 9., 0.], [4., 9., 0., 0.]], requires_grad=True)
    masks = torch.tensor([[True, True, False, False], [True, False, False, False]])
    logp = torch.log_softmax(logits.masked_fill(~masks, -1e8), -1)
    kl = legal_uniform_kl(logp, masks)
    assert kl[0] > 0 and kl[1] == 0
    kl.mean().backward()
    assert torch.all(logits.grad[~masks] == 0) and torch.all(logits.grad[1] == 0)
    assert logits.grad[0, 0] > 0 and logits.grad[0, 1] < 0
    extreme = torch.tensor([[-10000., 0., -1e8, -1e8]])
    assert torch.isfinite(legal_uniform_kl(extreme, masks[:1])).all()
    with pytest.raises(ValueError): legal_uniform_kl(logp, torch.zeros_like(masks))
    for beta in (-.1, .011, float("nan"), True):
        with pytest.raises(ValueError): regularizer_contract(beta)


def test_beta_zero_exact_upstream_update_and_adam():
    torch.set_num_threads(1)
    kwargs = dict(n_steps=16, batch_size=16, n_epochs=2, seed=19, ent_coef=.01)
    a = MaskablePPO("MlpPolicy", MaskedFixture(), **kwargs)
    b = RegularizedMaskablePPO("MlpPolicy", MaskedFixture(), zero_avoiding_beta=0, **kwargs)
    for model in (a, b):
        model.set_random_seed(19)
        model.learn(32)
    assert all(torch.equal(v, b.policy.state_dict()[k]) for k, v in a.policy.state_dict().items())
    assert same_optimizer(a, b)


def test_regularized_train_save_load_continue_keeps_actual_loss(tmp_path):
    model = RegularizedMaskablePPO("MlpPolicy", MaskedFixture(), zero_avoiding_beta=.001,
                                 n_steps=16, batch_size=16, n_epochs=2, ent_coef=.01, seed=31)
    model.learn(32)
    file = tmp_path / "regularized"
    model.save(file)
    loaded = RegularizedMaskablePPO.load(file, env=MaskedFixture())
    assert loaded.zero_avoiding_beta == .001 and same_optimizer(model, loaded)
    before = deepcopy(loaded.policy.state_dict())
    loaded.learn(16, reset_num_timesteps=False)
    assert loaded.logger.name_to_value["train/zero_avoiding_beta"] == .001
    assert loaded.logger.name_to_value["train/regularization_loss"] >= 0
    assert any(not torch.equal(v, loaded.policy.state_dict()[k]) for k, v in before.items())
    assert "evaluate_actions" not in loaded.policy.__dict__
    from advisor.learned_regularized_ppo import model_regularizer_contract
    base = MaskablePPO.load(file)
    with pytest.raises(ValueError, match="base_algorithm"): model_regularizer_contract(base)


@pytest.mark.parametrize("n,expected", [(1,[5]), (2,[1,4]), (3,[1,1,3]), (4,[1,1,1,2])])
def test_generation_weights_anchor_and_recent(n, expected):
    fixed = ["max_power", "champions_heuristic", "tactical_heuristic", "previous", "historical"]
    snapshots = [dict(path=f"f{i}.zip", sha256=str(i)*64) for i in range(n)]
    mix = generation_mixture(fixed, snapshots)
    assert mix["opponents"][:5] == fixed and len(mix["opponents"]) == 10
    assert [mix["opponents"].count(f"league_s{i}") for i in range(n)] == expected
    assert sum(mix["nominal_episode_probabilities"].values()) == pytest.approx(1)
    assert len(mix["frozen_opponents"]) <= 4


def test_append_only_lineage_and_invalid_generation(tmp_path):
    file = tmp_path / "events.jsonl"
    append_generation_event(file, {"event":"start", "generation":0})
    append_generation_event(file, {"event":"complete", "generation":0})
    assert len(read_generation_events(file)) == 2
    file.write_text(file.read_text().replace('"generation": 0', '"generation": 3'))
    with pytest.raises(ValueError, match="corrupted"): read_generation_events(file)
    parent = dict(sha256="a", model_timesteps=1024, optimizer_steps=32,
                  encoder_version="V3", catalog_fingerprint="same", training_objective="same")
    child = {**parent, "sha256":"b", "model_timesteps":2048, "optimizer_steps":64}
    validate_child(parent, child, 1024)
    with pytest.raises(ValueError): validate_child(parent, child, 2048)


def test_v2_64_team_subset_exclusion_and_legacy_unchanged(tmp_path):
    from tests.test_learnability_ladder import subset
    from advisor.learned_training_subset import NativeTrainingSubset, VERSION_64
    path, digest = subset(tmp_path, count=64, schema_version=VERSION_64)
    source = NativeTrainingSubset(path, digest)
    assert len(source.teams) == 64 and "subset-v2" in source("train", 7)["scenario_id"]
    assert source("train", 7) == source("train", 7)
    c = json.loads(path.read_text()); c["schema_version"] = "showdown-native-training-subset-v1"
    path.write_text(json.dumps(c))
    with pytest.raises(ValueError): NativeTrainingSubset(path, sha256(path.read_bytes()).hexdigest())


def test_seat_swap_real_team_preview_order_and_history_guard():
    from scripts.evaluate_showdown_policy import seat_scenario, native_heal_failures, FIXTURE_SEAT_CONTRACT
    case = dict(teams={"self":["A","B"], "opponent":["C","D"]},
                preview={"self":[2,1], "opponent":[1,2]}, seed=[1,2,3,4], history=[])
    swapped = seat_scenario(case, "p2")
    assert swapped["teams"]["opponent"] == case["teams"]["self"]
    assert swapped["preview"]["opponent"] == [2,1] and swapped["seed"] == case["seed"]
    assert seat_scenario(swapped,"p2") == case and case["teams"]["self"] == ["A","B"]
    assert seat_scenario(case,"p2",FIXTURE_SEAT_CONTRACT) == case
    with pytest.raises(ValueError): seat_scenario(case,"p1","unversioned")
    with pytest.raises(ValueError): seat_scenario({**case, "history":["|turn|1"]},"p2")
    history=["|move|p2a: X|Recover|p2a: X", "|-fail|p2a: X|heal"]
    assert native_heal_failures(history,"p2")[0] == 1 and native_heal_failures(history)[0] == 0


def test_native_regularized_categorical_loader_and_frozen_opponent(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("pinned engine required")
    from stable_baselines3.common.vec_env import DummyVecEnv
    from advisor.learned_gym import ShowdownLearningEnv, OPAQUE_TERMINAL
    from advisor.learned_action_encoder import make_encoder
    from advisor.learned_public_categories_policy import PublicCategoricalPolicy
    from scripts.train_showdown_autonomous import save_checkpoint
    from advisor.learned_policy import LearnedPolicy
    encoder = make_encoder(CATALOG,"showdown-public-categorical-observation-v3")
    vector = DummyVecEnv([lambda: ShowdownLearningEnv(checkout, encoder,
        curriculum_version="showdown-learning-curriculum-v8", opponents=["max_power"], terminal_transport_version=OPAQUE_TERMINAL)])
    try:
        model = RegularizedMaskablePPO(PublicCategoricalPolicy, vector, zero_avoiding_beta=.001,
            n_steps=16, batch_size=16, n_epochs=2, seed=11, gamma=1, gae_lambda=.95, ent_coef=.01)
        model.learn(32)
        file = save_checkpoint(model, encoder, tmp_path/"model", {})
        loaded = LearnedPolicy(file, CATALOG)
        assert type(loaded.model) is RegularizedMaskablePPO and same_optimizer(model,loaded.model)
        frozen = deepcopy(loaded.model.policy.state_dict())
        view = vector.get_attr("current")[0]
        assert loaded.act(view) == int(model.predict(encoder.encode(view), action_masks=view["action_mask"], deterministic=True)[0])
        model.learn(16, reset_num_timesteps=False)
        assert all(torch.equal(v, loaded.model.policy.state_dict()[k]) for k,v in frozen.items())
        loaded.model.set_env(vector)
        loaded.model.learn(16, reset_num_timesteps=False)
        assert loaded.model.logger.name_to_value["train/zero_avoiding_beta"] == .001
    finally:
        vector.close()


@pytest.mark.parametrize("contract", ["own_team_preserving_native_seats_v1", "fixed_fixture_policy_seats_v1"])
def test_native_seat_evaluation_and_opponent_request_ownership(tmp_path, contract):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("pinned engine required")
    from scripts.evaluate_showdown_policy import evaluate
    from advisor.learned_native_curriculum import native_case
    class Bank:
        identity = {"test":"real_seat_native_public_only"}
        def __call__(self, split, index):
            return native_case("train", index, version="showdown-learning-curriculum-v8")
    from advisor.learned_baselines import VisibleBaseline
    class OwnerProbe:
        model_id = "public-owner-probe"
        def __init__(self, expected):
            self.expected = expected
            self.policy = VisibleBaseline("max_power", 1)
        def act(self, observation):
            assert observation["side"] == self.expected
            side = observation["own_request"].get("side")
            if side: assert side["id"] == ("p1" if self.expected == "self" else "p2")
            assert not {"teams", "seed", "checkpoint", "native_state"} & set(observation)
            return self.policy.act(observation)
    for seat, own, other in (("p1","self","opponent"), ("p2","opponent","self")):
        result = evaluate(checkout, CATALOG, {"probe":OwnerProbe(own)}, cases=2, offset=49259000,
                          rivals={"rival":OwnerProbe(other)}, case_provider=Bank(), candidate_seat=seat,
                          tactical_diagnostics=True, seat_contract=contract)
        assert len(result["records"]) == 2
        for row in result["records"]:
            expected = 1 if row["raw_native_winner"] == own else -1 if row["raw_native_winner"] == other else 0
            assert row["return"] == expected
            assert row["candidate_seat"] == seat
            if contract == "fixed_fixture_policy_seats_v1":
                assert row["native_scenario_sha256"] == row["canonical_scenario_sha256"]
            assert row["winner"] == ("self" if expected == 1 else "opponent" if expected == -1 else None)
