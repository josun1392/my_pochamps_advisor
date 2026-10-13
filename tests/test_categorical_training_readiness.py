"""Small native readiness checks; no performance or multi-seed training study."""
from copy import deepcopy
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
gym = pytest.importorskip("gymnasium")
pytest.importorskip("sb3_contrib")
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from advisor.learned_public_categories import (
    RequestIdentityCategoricalEncoder as PublicCategoricalEncoder,
    REQUEST_IDENTITY_VERSION as VERSION, CONTEXT, ACTION, BASE_ACTION,
)
from advisor.learned_public_categories_policy import PublicCategoricalPolicy
from advisor.learned_objective import UNDISCOUNTED, objective_contract, experiment_objective, require_resume_objective
from advisor.learned_policy import LearnedPolicy
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_parallel import LearningEnvFactory
from scripts.train_showdown_autonomous import save_checkpoint, validate_config, optimizer_steps

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    path = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not path:
        pytest.skip("external pinned native engine required")
    return path


def test_explicit_new_objective_and_invalid_or_legacy_gamma_rejected():
    experiment = {"gamma": 1.0, "gae_lambda": 0.95, "objective": UNDISCOUNTED}
    assert experiment_objective(experiment, VERSION)["duration_preference"] == "none"
    with pytest.raises(ValueError, match="requires_new_public"):
        experiment_objective(experiment, "showdown-learned-observation-v3")
    for gamma in (True, 0.5, float("nan")):
        with pytest.raises(ValueError):
            objective_contract(gamma, .95)
    with pytest.raises(ValueError, match="gamma_objective"):
        experiment_objective({**experiment, "objective": "discounted"}, VERSION)
    config = {"schema_version": "showdown-autonomous-training-v1", "max_runtime_seconds": 60,
              "experiments": [{**experiment, "encoder_version": VERSION, "seed": 73011, "steps": 4096}]}
    validate_config(config)
    assert experiment_objective({}, "showdown-learned-observation-v3")["gamma"] == .99


def test_public_equivalent_hidden_move_item_ability_and_rng_isolation(checkout):
    from advisor.showdown_environment import ShowdownEnvironment
    from scripts.verify_showdown_integration import fixture_scenarios
    original = fixture_scenarios()[0]
    for team in original["teams"].values():
        for pokemon in team:
            pokemon["gender"] = "N" if pokemon["species"] == "Rotom-Wash" else "M"
    changed = deepcopy(original)
    changed["teams"]["opponent"][0].update(ability="Swarm", item="Choice Scarf", moves=["U-turn", "Iron Head", "Protect"])
    encoder = PublicCategoricalEncoder(CATALOG)
    with ShowdownEnvironment(checkout) as env:
        env.reset(original); before = env.observation("self", include_history=True)
        env.reset(changed, seed=[901,802,703,604]); after = env.observation("self", include_history=True)
    for view in (before, after):
        view.pop("episode_id")
        opponent = view["state"]["opponent_side"]
        row = opponent["pokemon"][opponent["active_identity"]]
        assert row["known_item"] == row["current_ability"] == {"knowledge": "unknown"}
        assert row["known_moves"] == []
    assert before == after
    assert before["action_mask"] == after["action_mask"] and before["choices"] == after["choices"]
    np.testing.assert_array_equal(encoder.encode(before), encoder.encode(after))


def test_timeout_bootstrap_equals_actual_public_continuation_and_keeps_execution_closed(checkout):
    encoder = PublicCategoricalEncoder(CATALOG)
    with ShowdownLearningEnv(checkout, encoder, max_decisions=1, curriculum_version="showdown-learning-curriculum-v8", opponents=("max_power",)) as limited:
        with ShowdownLearningEnv(checkout, encoder, max_decisions=256, curriculum_version="showdown-learning-curriculum-v8", opponents=("max_power",)) as continued:
            a, _ = limited.reset(seed=971); b, _ = continued.reset(seed=971)
            np.testing.assert_array_equal(a, b)
            action = int(np.flatnonzero(limited.action_masks())[-1])
            timeout, reward, terminal, truncated, info = limited.step(action)
            actual, _, terminal_b, truncated_b, _ = continued.step(action)
            assert not terminal and truncated and not terminal_b and not truncated_b and reward == 0
            assert info["native_outcome"]["winner"] is None
            assert not any(limited.current["action_mask"])  # execution view stays closed
            assert limited.native.timeout_bootstrap_observation("self")["action_mask"] == continued.current["action_mask"]
            np.testing.assert_array_equal(timeout, actual)
            assert "native_seed" not in json.dumps(info) and "team_sha256" not in json.dumps(info)
            rows = limited.drain_completed()
            assert rows[0]["truncated"] and not rows[0]["terminated"] and rows[0]["winner"] is None
            identity = rows[0]["episode_identity"]
            from advisor.learned_scenarios import scenario
            from advisor.learned_encoder import fingerprint
            case = scenario(identity["split"], identity["case_index"], version=identity["curriculum_version"])
            assert fingerprint(case) == identity["scenario_sha256"]
            assert case["seed"] == identity["native_seed"] and case["preview"] == identity["preview"]


@pytest.mark.parametrize("backend", ["dummy", "subproc"])
def test_upstream_sb3_real_timeout_terminal_observation_and_gae_bootstrap(checkout, backend, monkeypatch):
    factory = LearningEnvFactory(checkout, str(CATALOG), VERSION, 0, "showdown-learning-curriculum-v8", ("max_power",), {}, max_decisions=1)
    vector = DummyVecEnv([factory]) if backend == "dummy" else SubprocVecEnv([factory], start_method="spawn")
    try:
        torch.set_num_threads(1)
        model = MaskablePPO(PublicCategoricalPolicy, vector, gamma=1.0, gae_lambda=.95, n_steps=2, batch_size=2, n_epochs=1, seed=947, device="cpu")
        monkeypatch.setattr(model.policy, "predict_values", lambda obs: torch.full((len(obs),1), .25, device=obs.device))
        class Probe(BaseCallback):
            def _on_step(self):
                for info in self.locals["infos"]:
                    assert info["TimeLimit.truncated"] is True
                    assert info["native_outcome"]["rewards"]["self"] == 0
                    assert info["native_outcome"]["winner"] is None
                    final = info["terminal_observation"]
                    assert final.shape == (PublicCategoricalEncoder.dimension,)
                    assert final[CONTEXT:].reshape(35,ACTION)[:, -1].any()
                return True
        model.learn(2, callback=Probe())
        # No custom GAE/reward handling: upstream adds gamma*V(final)=.25.
        np.testing.assert_allclose(model.rollout_buffer.rewards, .25)
        np.testing.assert_allclose(model.rollout_buffer.returns, .25)
        assert model.rollout_buffer.gamma == 1.0 and model.rollout_buffer.gae_lambda == .95
    finally:
        vector.close()


def test_gamma_one_small_native_learning_raw_bits_save_and_resume(checkout, tmp_path):
    encoder = PublicCategoricalEncoder(CATALOG)
    env = ShowdownLearningEnv(checkout, encoder, curriculum_version="showdown-learning-curriculum-v8", opponents=("max_power",))
    vector = DummyVecEnv([lambda: env])
    try:
        torch.set_num_threads(1)
        m = MaskablePPO(PublicCategoricalPolicy, vector, gamma=1.0, gae_lambda=.95, n_steps=16, batch_size=16, n_epochs=1, seed=953, device="cpu")
        x = torch.tensor(encoder.encode(env.current))[None]
        np.testing.assert_array_equal(m.policy.extract_features(x).detach().numpy(), x.numpy())
        raw = x[0,CONTEXT:].reshape(35,ACTION)[:,BASE_ACTION-1:-1]
        assert torch.all((raw==0)|(raw==1))
        before = {k:v.clone() for k,v in m.policy.state_dict().items()}
        m.learn(32)
        assert optimizer_steps(m) > 0 and m.num_timesteps == 32
        assert any(not torch.equal(v,before[k]) for k,v in m.policy.state_dict().items())
        for embedding in m.policy.mlp_extractor.embeddings.values():
            assert embedding.weight.grad is not None and embedding.weight.grad.abs().sum() > 0
        path = save_checkpoint(m, encoder, tmp_path/"gamma_one", {})
        restored = LearnedPolicy(path, CATALOG)
        assert restored.metadata["training_objective"] == objective_contract(1.0,.95)
        require_resume_objective(restored.model, {"gamma":1.0,"gae_lambda":.95}, VERSION)
        with pytest.raises(ValueError, match="no_silent_gamma"):
            require_resume_objective(restored.model, {"gamma":.99}, VERSION)
        old_updates = optimizer_steps(restored.model)
        restored.model.set_env(vector); restored.model.learn(16, reset_num_timesteps=False)
        assert optimizer_steps(restored.model) > old_updates
        metadata = Path(path).with_suffix(".json"); data=json.loads(metadata.read_text()); data["gamma"] = .99; metadata.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="training_objective_mismatch"):
            LearnedPolicy(path, CATALOG)
    finally:
        vector.close()


def test_native_evaluation_value_error_uses_actual_gamma(checkout, tmp_path):
    from scripts.evaluate_showdown_policy import evaluate
    encoder = PublicCategoricalEncoder(CATALOG)
    class Spaces(gym.Env):
        action_space = gym.spaces.Discrete(35)
        observation_space = gym.spaces.Box(-2,4,(encoder.dimension,),dtype=np.float32)
    m=MaskablePPO(PublicCategoricalPolicy,Spaces(),gamma=1.0,n_steps=2,batch_size=2,seed=959,device="cpu")
    path=save_checkpoint(m,encoder,tmp_path/"evaluation",{}); player=LearnedPolicy(path,CATALOG)
    native_infer=player.infer
    def controlled_value(view):
        proof=native_infer(view);proof["discounted_return_estimate"] = .25;return proof
    player.infer=controlled_value
    result=evaluate(checkout,CATALOG,{"candidate":player},cases=1,offset=73200000,curriculum_version="showdown-learning-curriculum-v8",rivals={"max_power":"max_power"})
    row=result["records"][0]
    assert not row["truncated"] and row["value_gamma"] == 1.0
    assert row["value_discounted_return_mse"] == pytest.approx((.25-row["return"])**2)


def test_timeout_missing_public_bootstrap_fails_closed(checkout, monkeypatch):
    from advisor.showdown_environment import ShowdownEnvironment, ShowdownEnvironmentError
    from advisor.learned_scenarios import scenario
    with ShowdownEnvironment(checkout, max_decisions=1) as env:
        env.reset(scenario("train", 3401, version="showdown-learning-curriculum-v8"))
        original = env.worker.run
        def missing(request):
            response = original(request)
            for row in response["results"]:
                if row.get("truncated"):
                    row.pop("timeout_bootstrap", None)
            return response
        monkeypatch.setattr(env.worker,"run",missing)
        views={side:env.observation(side) for side in ("self","opponent")}
        actions={side:int(np.flatnonzero(view["action_mask"])[-1]) for side,view in views.items()}
        with pytest.raises(ShowdownEnvironmentError, match="invalid_environment_transition"):
            env.step(actions,revision=views["self"]["revision"])


def test_own_native_aliases_reconcile_only_in_versioned_v2_without_truth_mutation(checkout):
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_scenarios import scenario
    from advisor.learned_public_categories import PublicCategoricalEncoder as V1
    from advisor.learned_own_identity import own_player_records
    encoder=PublicCategoricalEncoder(CATALOG)
    with ShowdownEnvironment(checkout) as native:
        native.reset(scenario("train",3401,version="showdown-learning-curriculum-v8"))
        initial=native.observation("self",include_history=True)
        switch=next(i for i in range(6) if initial["action_mask"][i])
        other=native.observation("opponent")
        native.step({"self":switch,"opponent":int(np.flatnonzero(other["action_mask"])[-1])},revision=0)
        view=native.observation("self",include_history=True)
        # A native unpositioned reference (e.g. fainted target -hitcount)
        # creates this empty row separately from the positioned appearance.
        from advisor.showdown_observation import _pokemon
        active=view['state']['self_side']['active_identity']
        unpositioned='p1: '+active.split(': ',1)[-1]
        view['state']['self_side']['pokemon'][unpositioned]=_pokemon(unpositioned)
        snapshot=deepcopy(view)
        assert len({k.split(': ',1)[-1] for k in view['state']['self_side']['pokemon']}) < len(view['state']['self_side']['pokemon'])
        with pytest.raises(ValueError,match='ambiguous_own_public_identity'):
            V1(CATALOG).encode(view)
        features=encoder.encode(view)
        rows=own_player_records(view)
        assert len(rows)==len(view['own_request']['side']['pokemon'])
        assert {k for k,_ in rows}=={p['ident'] for p in view['own_request']['side']['pokemon']}
        assert sum(r['own_request_active'] for _,r in rows)==1
        assert view==snapshot and unpositioned not in native.observation('self',include_history=True)['state']['self_side']['pokemon']
        assert features.shape==(encoder.dimension,)
        assert encoder.feature_contract['version']==VERSION
        assert encoder.catalog_fingerprint != V1(CATALOG).catalog_fingerprint


def test_wait_only_empty_own_protocol_reference_removed_not_populated_ambiguity(checkout):
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_scenarios import scenario
    from advisor.showdown_observation import _pokemon
    from advisor.learned_own_identity import own_player_records
    with ShowdownEnvironment(checkout) as native:
        native.reset(scenario("train",3401,version="showdown-learning-curriculum-v8"))
        view=native.observation("self",include_history=True)
    # Native -hitcount after faint can create an entirely empty unpositioned
    # reference when the terminal request is wait. No request roster is guessed.
    side=view["state"]["self_side"]
    active=side["active_identity"]
    assert active.startswith("p1a: ")
    name=active.split(": ",1)[1]
    view["own_request"]={"wait":True}
    side["pokemon"]={active:side["pokemon"][active], "p1: "+name:_pokemon("p1: "+name)}
    snapshot=deepcopy(view)
    rows=own_player_records(view)
    assert [k for k,_ in rows]==[active] and view==snapshot
    side["pokemon"]["p1: "+name]["known_moves"]=["protect"]
    assert len(own_player_records(view))==2
    with pytest.raises(ValueError,match="ambiguous_own_public_identity"):
        PublicCategoricalEncoder(CATALOG).encode(view)
