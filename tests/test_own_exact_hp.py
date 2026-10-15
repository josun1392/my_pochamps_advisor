"""Owner-request HP binding, matched ablation and unchanged V4 inference."""
from copy import deepcopy
import os
import numpy as np
import pytest
import torch

from advisor.learned_own_hp import (
    OwnExactHPCategoricalEncoder, VERSION, ABLATED_VERSION, OLD_DIMENSION,
    EXTRA, SCALE, own_hp_features,
)
from advisor.learned_own_hp_policy import (
    OwnExactHPCategoricalPolicy, transfer_own_hp_weights, OLD_LATENT_CONTEXT,
)
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder, CONTEXT
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy
from advisor.learned_public_categories import ACTION
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_environment import ShowdownEnvironment
from scripts.verify_showdown_integration import fixture_scenarios
from scripts.train_showdown_autonomous import save_checkpoint, optimizer_steps
from tests.test_public_categorical_observation import model, CATALOG


@pytest.fixture(scope="module")
def views():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned native engine required")
    scenario = fixture_scenarios()[0]
    for team in scenario["teams"].values():
        for p in team:
            p["gender"] = "N" if p["species"] == "Rotom-Wash" else "M"
    result = {}
    with ShowdownEnvironment(checkout) as env:
        for side in ("self", "opponent"):
            result[side] = []
            for hp in (0, 32):
                s = deepcopy(scenario)
                s["teams"][side][0]["evs"] = {"hp":hp,"atk":0,"def":0,"spa":16,"spd":0,"spe":16}
                env.reset(s)
                result[side].append(env.observation(side, include_history=True))
    return result


def test_native_hp_alias_both_seats_and_unchanged_prefix(views):
    old = StrategicPublicCategoricalEncoder(CATALOG)
    treatment = OwnExactHPCategoricalEncoder(CATALOG)
    control = OwnExactHPCategoricalEncoder(CATALOG, ABLATED_VERSION)
    assert treatment.tokens == control.tokens == old.tokens
    assert old.dimension == 15692 and treatment.dimension == control.dimension == 15716
    assert treatment.catalog_fingerprint != control.catalog_fingerprint != old.catalog_fingerprint
    for side, (a, b) in views.items():
        assert np.array_equal(old.encode(a), old.encode(b))
        assert a["action_mask"] == b["action_mask"]
        assert not np.array_equal(treatment.encode(a), treatment.encode(b))
        assert np.array_equal(control.encode(a), control.encode(b))
        for v in (a, b):
            before = deepcopy(v)
            assert np.array_equal(treatment.encode(v)[:OLD_DIMENSION], old.encode(v))
            assert np.count_nonzero(control.encode(v)[OLD_DIMENSION:]) == 0
            hp = own_hp_features(v)
            roster = v["own_request"]["side"]["pokemon"]
            for i, p in enumerate(sorted(roster, key=lambda x:x["ident"])):
                current, maximum = map(int, p["condition"].split()[0].split("/"))
                assert list(hp[i]) == [current/SCALE, maximum/SCALE, 1, 1]
            assert np.count_nonzero(hp[len(roster):]) == 0
            reordered = deepcopy(v)
            reordered["own_request"]["side"]["pokemon"].reverse()
            assert np.array_equal(hp, own_hp_features(reordered))
            assert v == before
        if side == "self":
            assert [next(p["condition"] for p in v["own_request"]["side"]["pokemon"] if p["active"]) for v in (a,b)] == ["153/153", "185/185"]


def test_unknown_faint_padding_and_authenticated_binding(views):
    view = deepcopy(views["self"][0])
    roster = view["own_request"]["side"]["pokemon"]
    ident = roster[1]["ident"]
    roster[1]["condition"] = "0 fnt"
    index = sorted(p["ident"] for p in roster).index(ident)
    assert list(own_hp_features(view)[index]) == [0, 0, 1, 0]
    roster[1]["condition"] = ""
    assert list(own_hp_features(view)[index]) == [0, 0, 0, 0]
    # Old public projection may contain exact-looking values; never fill from it.
    view["own_request"] = {}
    assert not own_hp_features(view).any()
    view = deepcopy(views["self"][0])
    view["own_request"]["side"]["id"] = "p2"
    with pytest.raises(ValueError, match="unauthenticated"):
        OwnExactHPCategoricalEncoder(CATALOG, ABLATED_VERSION).encode(view)
    view = deepcopy(views["self"][0])
    view["own_request"]["side"]["pokemon"][0]["ident"] = "p2: hidden"
    with pytest.raises(ValueError, match="identity"):
        own_hp_features(view)


@pytest.mark.parametrize("condition", ["100/100g", "10/0", "200/100", "1/5000", "-1/100", None, "NaN", "100/100 invented"])
def test_malformed_known_hp_fails_closed(views, condition):
    view = deepcopy(views["self"][0])
    view["own_request"]["side"]["pokemon"][0]["condition"] = condition
    with pytest.raises(ValueError):
        own_hp_features(view)


def test_hidden_payload_and_opponent_hp_not_inputs(views):
    e = OwnExactHPCategoricalEncoder(CATALOG)
    for pair in views.values():
        v = pair[0]
        altered = deepcopy(v)
        altered.update(native_checkpoint={"hp":999}, hidden_opponent_set={"item":"Life Orb"}, future_rng=[1,2,3], opponent_private_request={"condition":"999/999"})
        assert np.array_equal(e.encode(v), e.encode(altered))
        own = own_hp_features(v)
        altered["state"]["opponent_side"]["pokemon"] = {}
        assert np.array_equal(own, own_hp_features(altered))


def test_transfer_actor_critic_equivalence_permutation_and_gradients(views, tmp_path):
    old = StrategicPublicCategoricalEncoder(CATALOG)
    source = model(old, StrategicPublicCategoricalPolicy)
    original = {k:v.clone() for k,v in source.policy.state_dict().items()}
    arms = []
    for version in (VERSION, ABLATED_VERSION):
        e = OwnExactHPCategoricalEncoder(CATALOG, version)
        target = model(e, OwnExactHPCategoricalPolicy)
        transfer_own_hp_weights(target.policy, source.policy, e, old)
        assert not target.policy.optimizer.state
        arms.append(target)
        for pair in views.values():
            for v in pair:
                a, b = torch.tensor(old.encode(v))[None], torch.tensor(e.encode(v))[None]
                mask = np.asarray(v["action_mask"], dtype=bool)[None]
                with torch.no_grad():
                    assert torch.allclose(source.policy.mlp_extractor.forward_actor(a), target.policy.mlp_extractor.forward_actor(b), atol=1e-6, rtol=1e-6)
                    assert torch.allclose(source.policy.predict_values(a), target.policy.predict_values(b), atol=1e-6, rtol=1e-6)
                    pa = source.policy.get_distribution(a, action_masks=mask).distribution.probs
                    pb = target.policy.get_distribution(b, action_masks=mask).distribution.probs
                    assert torch.allclose(pa, pb, atol=1e-6, rtol=1e-6)
                    assert not pb[~torch.tensor(mask)].any()
                    # Permute action rows only; entity/HP binding remains stable.
                    permutation = torch.arange(34, -1, -1)
                    permuted = b.clone()
                    permuted[:, CONTEXT:OLD_DIMENSION] = b[:, CONTEXT:OLD_DIMENSION].reshape(1,35,ACTION)[:,permutation].flatten(1)
                    logits = target.policy.mlp_extractor.forward_actor(b)
                    assert torch.allclose(target.policy.mlp_extractor.forward_actor(permuted), logits[:,permutation], atol=1e-6)
        path = save_checkpoint(target, e, tmp_path/version, {})
        loaded = LearnedPolicy(path, CATALOG)
        assert loaded.encoder.version == version
        for k,v in target.policy.state_dict().items():
            assert torch.equal(v, loaded.model.policy.state_dict()[k])
    assert all(torch.equal(a,b) for a,b in zip(arms[0].policy.parameters(), arms[1].policy.parameters()))
    target = arms[0]
    e = OwnExactHPCategoricalEncoder(CATALOG)
    v = views["self"][0]
    tensor = torch.tensor(e.encode(v))[None]
    action = int(np.flatnonzero(v["action_mask"])[0])
    distribution = target.policy.get_distribution(tensor, action_masks=np.array(v["action_mask"])[None])
    loss = -distribution.log_prob(torch.tensor([action])).mean() + target.policy.predict_values(tensor).square().mean()
    loss.backward()
    extractor = target.policy.mlp_extractor
    assert extractor.context[0].weight.grad[:, OLD_LATENT_CONTEXT:].abs().sum() > 0
    assert extractor.scorer[0].weight.grad[:, -4:].abs().sum() > 0
    assert extractor.critic[0].weight.grad[:, OLD_LATENT_CONTEXT:OLD_LATENT_CONTEXT+EXTRA].abs().sum() > 0
    target.policy.optimizer.step()
    assert optimizer_steps(target) == 1
    assert all(torch.equal(v, source.policy.state_dict()[k]) for k,v in original.items())


@pytest.mark.parametrize("version", [VERSION, ABLATED_VERSION])
def test_native_update_regularizer_checkpoint_and_optimizer_resume(version, tmp_path):
    from advisor.learned_gym import ShowdownLearningEnv
    from advisor.learned_regularized_ppo import RegularizedMaskablePPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned native engine required")
    enc = OwnExactHPCategoricalEncoder(CATALOG, version)
    vector = DummyVecEnv([lambda:ShowdownLearningEnv(checkout,enc,curriculum_version="showdown-learning-curriculum-v8",opponents=["max_power"])])
    try:
        m = RegularizedMaskablePPO(OwnExactHPCategoricalPolicy, vector, seed=86011,
            n_steps=8,batch_size=8,n_epochs=1,gamma=1,gae_lambda=.95,
            ent_coef=.01,zero_avoiding_beta=.001,device="cpu")
        before = {k:v.clone() for k,v in m.policy.state_dict().items()}
        m.learn(32)
        assert optimizer_steps(m) == 4
        assert any(not torch.equal(v, m.policy.state_dict()[k]) for k,v in before.items())
        assert all(torch.isfinite(p).all() for p in m.policy.parameters())
        path = save_checkpoint(m,enc,tmp_path/version,{})
        loaded = LearnedPolicy(path,CATALOG)
        assert type(loaded.model) is RegularizedMaskablePPO
        assert loaded.model.zero_avoiding_beta == .001 and optimizer_steps(loaded.model) == 4
        a, b = m.policy.optimizer.state_dict(), loaded.model.policy.optimizer.state_dict()
        assert a["param_groups"] == b["param_groups"]
        for k in a["state"]:
            for name, value in a["state"][k].items():
                assert torch.equal(value, b["state"][k][name])
        loaded.model.set_env(vector)
        loaded.model.learn(8,reset_num_timesteps=False)
        assert optimizer_steps(loaded.model) == 5
        assert loaded.model.num_timesteps == 40
    finally:
        vector.close()


def test_native_switch_and_own_illusion_binding():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned native engine required")
    s = fixture_scenarios()[0]
    s["teams"]["self"][0] = {"species":"Zoroark","ability":"Illusion","item":"Focus Sash",
        "moves":["Dark Pulse","Protect"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}}
    e = OwnExactHPCategoricalEncoder(CATALOG)
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        for side in ("self","opponent"):
            view = env.observation(side,include_history=True)
            assert own_hp_features(view)[:,2].sum() == 3
            e.encode(view)
        view = env.observation("self",include_history=True)
        switch = view["choices"].index("switch 2")
        result = env.step({"self":switch,"opponent":7},revision=view["revision"])
        assert not result["action_rejected"]
        for side in ("self","opponent"):
            view = env.observation(side,include_history=True)
            e.encode(view)
            rows = own_hp_features(view)
            for i,p in enumerate(sorted(view["own_request"]["side"]["pokemon"],key=lambda x:x["ident"])):
                if "/" in p["condition"]:
                    assert rows[i,1] == int(p["condition"].split()[0].split("/")[1])/SCALE


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_native_unrevealed_opponent_sets_rng_and_both_heads_isolated(side):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned native engine required")
    s = fixture_scenarios()[0]
    for team in s["teams"].values():
        for p in team:
            p["gender"] = "N" if p["species"] == "Rotom-Wash" else "M"
    changed = deepcopy(s)
    target = "opponent" if side == "self" else "self"
    changed["teams"][target][0].update(
        ability="Swarm" if side=="self" else "Solar Power",item="Choice Scarf",
        moves=["U-turn","Iron Head"] if side=="self" else ["Flamethrower","Protect"],
        evs={"hp":0,"spe":32,"atk":32})
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);a=env.observation(side,include_history=True)
        env.reset(changed,seed=[22,33,44,55]);b=env.observation(side,include_history=True)
    e=OwnExactHPCategoricalEncoder(CATALOG)
    assert a["own_request"]==b["own_request"] and a["action_mask"]==b["action_mask"]
    assert np.array_equal(e.encode(a),e.encode(b))
    m=model(e,OwnExactHPCategoricalPolicy)
    with torch.no_grad():
        x=torch.tensor(e.encode(a))[None];y=torch.tensor(e.encode(b))[None]
        assert torch.equal(m.policy.mlp_extractor.forward_actor(x),m.policy.mlp_extractor.forward_actor(y))
        assert torch.equal(m.policy.predict_values(x),m.policy.predict_values(y))
    for forbidden in ("seed","checkpoint","native_state","scenario","teams","queue"):
        with pytest.raises(ValueError):
            e.encode({**a,forbidden:{}})
