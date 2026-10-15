"""Bounded categorical V4 public projection, transfer and native learning proof."""
from copy import deepcopy
import json
import os
from pathlib import Path
import numpy as np
import pytest
import torch

from advisor.learned_public_categories import RuntimeAbilityCategoricalEncoder, CONTEXT as OLD_CONTEXT, ACTION
from advisor.learned_public_categories_policy import PublicCategoricalPolicy, LATENT_CONTEXT
from advisor.learned_strategic_public import (
    StrategicPublicCategoricalEncoder, VERSION, EFFECTS, EXTRA, CONTEXT, strategic_features,
)
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy, transfer_strategic_public_weights
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_environment import ShowdownEnvironment
from scripts.train_showdown_autonomous import save_checkpoint, optimizer_steps, require_finite_ppo, validate_config
from scripts.verify_showdown_integration import fixture_scenarios
from tests.test_public_categorical_observation import model, CATALOG


@pytest.fixture(scope="module")
def checkout():
    path = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not path:
        pytest.skip("pinned native checkout required")
    return path


@pytest.fixture(scope="module")
def enc():
    return StrategicPublicCategoricalEncoder(CATALOG)


def public_view(history, side="self", request=None):
    from advisor.showdown_observation import project_policy_observation
    return project_policy_observation({"schema_version":"showdown-policy-observation-v1", "side":side,
        "own_request":request or {}}, history)


@pytest.mark.parametrize("side", ["self", "opponent"])
@pytest.mark.parametrize("effect", EFFECTS)
def test_public_start_end_switch_faint_unknown_and_reset(enc, side, effect):
    role = "p1" if side == "self" else "p2"
    actor = role + "a: Charizard"
    history = ["|start", f"|switch|{actor}|Charizard, L50|100/100"]
    row = lambda h: enc.project(public_view(h, side))["active"][0]
    assert row([])["effects"][effect] is None
    if effect != "trapped":
        assert row(history)["effects"][effect] is False
    start = (f"|-mustrecharge|{actor}" if effect == "recharge" else
             f"|-activate|{actor}|trapped" if effect == "trapped" else
             f"|-start|{actor}|ability: Flash Fire" if effect == "flashfire" else
             f"|-start|{actor}|move: {effect}")
    assert row(history + [start])["effects"][effect] is True
    # Non-retroactive: the prefix still encodes the earlier absence/Unknown.
    assert row(history)["effects"][effect] is not True
    end = (f"|cant|{actor}|recharge" if effect == "recharge" else f"|-end|{actor}|{effect}")
    assert row(history + [start, end])["effects"][effect] is False
    switched = row(history + [start, f"|switch|{role}a: Gengar|Gengar, L50|100/100"])
    assert switched["effects"][effect] is (None if effect == "trapped" else False)
    assert row(history + [start, f"|faint|{actor}"])["effects"][effect] is False
    reset = row(history + [start, "|start"])
    assert reset["effects"][effect] is None


def test_unknown_copy_trap_source_departure_and_separate_supreme(enc):
    h = ["|start", "|switch|p1a: Gengar|Gengar, L50|100/100", "|switch|p2a: Charizard|Charizard, L50|100/100"]
    p = lambda x: enc.project(public_view(x))
    assert p(h)["active"][0]["supreme_activation"] is None
    activated = h + ["|-activate|p1a: Gengar|ability: Supreme Overlord", "|-start|p1a: Gengar|fallen2|[silent]"]
    assert p(activated)["active"][0]["supreme_activation"] is True
    assert p(activated)["active"][0]["supreme_fallen"] == 2
    assert all(x is not True for x in p(activated)["active"][0]["effects"].values())
    trapped = h + ["|-activate|p2a: Charizard|trapped"]
    assert p(trapped)["active"][1]["effects"]["trapped"] is True
    assert p(trapped + ["|switch|p1a: Lapras|Lapras, L50|100/100"])["active"][1]["effects"]["trapped"] is None
    copied = h + ["|move|p1a: Gengar|Baton Pass|p1a: Gengar", "|switch|p1a: Lapras|Lapras, L50|100/100"]
    assert "silent_passed_volatiles" in p(copied)["unsupported"]
    assert p(copied)["active"][0]["effects"]["substitute"] is None
    # maybeTrapped is not established trapping or its absence.
    assert enc.project(public_view(h, request={"active":[{"maybeTrapped":True}]}))["active"][0]["effects"]["trapped"] is None
    request={"side":{"pokemon":[{"ident":"p1: Gengar","details":"Gengar, L50","condition":"100/100","active":True}]}}
    roost=h+["|-singleturn|p1a: Gengar|move: Roost"]
    assert enc.project(public_view(roost,request=request))["active"][0]["types"] is None
    assert enc.project(public_view(roost+["|turn|2"],request=request))["active"][0]["types"]==("Ghost","Poison")


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_types_illusion_transform_expiration_weather_and_terrain(enc, side):
    role = "p1" if side == "self" else "p2"
    foe = "p2" if role == "p1" else "p1"
    h = [f"|poke|{foe}|Zoroark, L50", "|start", f"|switch|{role}a: Ditto|Ditto, L50|100/100",
         f"|switch|{foe}a: Charizard|Charizard, L50|100/100"]
    project = lambda history: enc.project(public_view(history, side))
    assert project(h)["active"][1]["types"] is None
    changed = h + [f"|-start|{foe}a: Charizard|typechange|Water"]
    assert project(changed)["active"][1]["types"] == ("Water",)
    revealed = changed + [f"|replace|{foe}a: Zoroark|Zoroark, L50|100/100"]
    assert project(revealed)["active"][1]["types"] == ("Water",)
    transformed = revealed + [f"|-transform|{role}a: Ditto|{foe}a: Zoroark"]
    assert project(transformed)["active"][0]["types"] == ("Water",)
    added = transformed + [f"|-start|{role}a: Ditto|typeadd|Ghost"]
    assert project(added)["active"][0]["types"] == ("Water", "Ghost")
    restored = added + [f"|-end|{role}a: Ditto|typechange|[silent]"]
    assert project(restored)["active"][0]["types"] == ("Normal",)
    no_payload = h + [f"|-start|{role}a: Ditto|typechange|[from] move: Reflect Type|[of] {foe}a: Charizard"]
    assert project(no_payload)["active"][0]["types"] is None
    assert "typechange_without_public_type_payload" in project(no_payload)["unsupported"]
    with pytest.raises(ValueError):
        project(h + [f"|-start|{role}a: Ditto|typechange|Invented"])
    for weather in ("Snowscape", "Hail", "SunnyDay", "RainDance", "Sandstorm", "none"):
        v = public_view(h + [f"|-weather|{weather}"], side)
        assert project(v["public_history"])["weather"] == (None if weather == "none" else weather.lower())
    # Existing terrain owner remains authoritative; the V4 layer does not duplicate it.
    v = public_view(h + ["|-fieldstart|move: Grassy Terrain"], side)
    assert v["state"]["field"]["terrain"] == "grassyterrain"
    v = public_view(h + ["|-fieldstart|move: Grassy Terrain", "|-fieldend|move: Grassy Terrain"], side)
    assert v["state"]["field"]["terrain"] is None


@pytest.mark.parametrize("route", ["substitute", "taunt", "encore", "confusion", "trapped", "recharge", "healblock", "throatchop", "flashfire", "snowscape", "types"])
def test_real_native_routes_both_seats(checkout, enc, route):
    spec = {
        "substitute": ("Gengar", "Cursed Body", "Substitute"),
        "taunt": ("Gengar", "Cursed Body", "Taunt"),
        "encore": ("Alakazam", "Synchronize", "Encore"),
        "confusion": ("Gengar", "Cursed Body", "Confuse Ray"),
        "trapped": ("Gengar", "Cursed Body", "Mean Look"),
        "recharge": ("Charizard", "Blaze", "Hyper Beam"),
        "healblock": ("Gengar", "Cursed Body", "Psychic Noise"),
        "throatchop": ("Audino", "Klutz", "Throat Chop"),
        "flashfire": ("Charizard", "Blaze", "Flamethrower"),
        "snowscape": ("Abomasnow", "Soundproof", "Snowscape"),
        "types": ("Inteleon", "Torrent", "Soak"),
    }[route]
    s = fixture_scenarios()[0]
    species, ability, move = spec
    s["teams"]["self"][0] = {"species":species,"ability":ability,"moves":[move,"Protect"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}}
    # Avoid duplicate Gengar/Tyranitar in the complete legal six.
    duplicates = [p for p in s["teams"]["self"][1:] if p["species"] != species]
    if len(duplicates) != 5:
        duplicates.append({"species":"Charizard","ability":"Blaze","moves":["Protect"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}})
    s["teams"]["self"] = [s["teams"]["self"][0], *duplicates]
    if route == "flashfire":
        s["teams"]["opponent"][0] = {"species":"Arcanine","ability":"Flash Fire","moves":["Howl","Protect"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}}
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        # Encore needs an earlier successful move; avoid Protect blocking it.
        if route == "encore":
            env.step({"self":7,"opponent":7}, revision=env.observation("self")["revision"])
        v = env.observation("self", include_history=True)
        result = env.step({"self":6,"opponent":6 if route == "flashfire" else 7}, revision=v["revision"])
        assert not result["action_rejected"]
        for side in ("self", "opponent"):
            view = env.observation(side, include_history=True)
            before = deepcopy(view)
            features = enc.encode(view)
            assert features.shape == (enc.dimension,) and np.isfinite(features).all()
            assert view == before
            projected = enc.project(view)
            own_index = 0 if side == "self" else 1
            target = own_index if route in {"substitute", "recharge"} else 1-own_index
            if route == "snowscape":
                assert projected["weather"] == "snowscape" and features[8] == 1
                assert RuntimeAbilityCategoricalEncoder(CATALOG).encode(view)[8] == 0
            elif route == "types":
                assert projected["active"][target]["types"] == ("Water",)
            else:
                assert projected["active"][target]["effects"][route] is True, view["public_history"]


def test_native_transfer_logits_value_masks_permutation_and_trainability(checkout, enc):
    old = RuntimeAbilityCategoricalEncoder(CATALOG)
    a, b = model(old), model(enc, StrategicPublicCategoricalPolicy)
    transfer_strategic_public_weights(b.policy, a.policy, enc, old)
    assert not b.policy.optimizer.state
    xnew = b.policy.mlp_extractor
    assert torch.count_nonzero(xnew.context[0].weight[:, LATENT_CONTEXT:]) == 0
    assert torch.count_nonzero(xnew.critic[0].weight[:, LATENT_CONTEXT:LATENT_CONTEXT+EXTRA]) == 0
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0])
        views = [env.observation(s, include_history=True) for s in ("self","opponent")]
    for v in views:
        # Include real protocol snow and type/volatile variations, no hidden inputs.
        for extra in ([], ["|-weather|Snowscape"], ["|-start|p1a: Charizard|Substitute", "|-start|p2a: Scizor|typechange|Water"]):
            v = deepcopy(v);v["public_history"] += extra
            # Update the existing projection exactly as the native boundary does.
            from advisor.showdown_observation import project_policy_observation
            v = project_policy_observation(v, v["public_history"])
            t, u = torch.tensor(old.encode(v))[None,:], torch.tensor(enc.encode(v))[None,:]
            with torch.no_grad():
                torch.testing.assert_close(a.policy.mlp_extractor.forward_actor(t), b.policy.mlp_extractor.forward_actor(u), rtol=1e-5, atol=2e-6)
                torch.testing.assert_close(a.policy.predict_values(t), b.policy.predict_values(u), rtol=1e-5, atol=2e-6)
                mask = np.asarray(v["action_mask"], bool)[None,:]
                dist = b.policy.get_distribution(u, action_masks=mask).distribution.probs
                assert not torch.any(dist[~torch.tensor(mask)])
                perm = torch.randperm(35)
                shuffled = torch.cat((u[:,:CONTEXT],u[:,CONTEXT:].reshape(1,35,ACTION)[:,perm].flatten(1)),dim=1)
                torch.testing.assert_close(b.policy.mlp_extractor.forward_actor(shuffled),b.policy.mlp_extractor.forward_actor(u)[:,perm])
                torch.testing.assert_close(b.policy.predict_values(shuffled),b.policy.predict_values(u))
                bad=u.clone();bad[:,OLD_CONTEXT]=.5
                with pytest.raises(ValueError,match="nonbinary_strategic"):
                    b.policy.predict_values(bad)
    before = xnew.context[0].weight.detach().clone()
    b.policy.optimizer.zero_grad()
    loss = b.policy.mlp_extractor.forward_actor(u).sum() + b.policy.predict_values(u).sum()
    loss.backward()
    assert xnew.context[0].weight.grad[:,LATENT_CONTEXT:].abs().sum() > 0
    assert xnew.critic[0].weight.grad[:,LATENT_CONTEXT:LATENT_CONTEXT+EXTRA].abs().sum() > 0
    b.policy.optimizer.step()
    assert torch.any(before[:,LATENT_CONTEXT:] != xnew.context[0].weight[:,LATENT_CONTEXT:])


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_public_hidden_isolation_and_privileged_rejection(checkout, enc, side):
    s = fixture_scenarios()[0]
    for team in s["teams"].values():
        for p in team:p["gender"]="N" if p["species"]=="Rotom-Wash" else "M"
    changed = deepcopy(s)
    if side == "self":
        changed["teams"]["opponent"][0].update(ability="Swarm",item="Choice Scarf",moves=["U-turn","Iron Head"])
    else:
        changed["teams"]["self"][0].update(ability="Solar Power",item="Choice Scarf",moves=["Flamethrower","Protect"])
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);a=env.observation(side,include_history=True)
        env.reset(changed,seed=[22,33,44,55]);b=env.observation(side,include_history=True)
    np.testing.assert_array_equal(enc.encode(a),enc.encode(b))
    assert a["own_request"]==b["own_request"] and a["action_mask"]==b["action_mask"]
    m=model(enc,StrategicPublicCategoricalPolicy)
    with torch.no_grad():
        torch.testing.assert_close(m.policy.predict_values(torch.tensor(enc.encode(a))[None,:]),m.policy.predict_values(torch.tensor(enc.encode(b))[None,:]))
    for field in ("seed","checkpoint","native_state","scenario","teams","queue"):
        with pytest.raises(ValueError):enc.encode({**a,field:{}})
    invalid=deepcopy(a);invalid["state"]["field"]["weather"]="snow"
    with pytest.raises(ValueError,match="unsupported_public_weather"):
        enc.encode(invalid)


def test_native_weather_expiration_and_transform_identity(checkout, enc):
    s=fixture_scenarios()[0]
    s["teams"]["self"][0]={"species":"Abomasnow","ability":"Soundproof","moves":["Snowscape","Swords Dance"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}}
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        env.step({"self":6,"opponent":7},revision=env.observation("self")["revision"])
        assert enc.project(env.observation("self",include_history=True))["weather"]=="snowscape"
        for _ in range(5):
            env.step({"self":7,"opponent":7},revision=env.observation("self")["revision"])
        assert enc.project(env.observation("self",include_history=True))["weather"] is None
    s=fixture_scenarios()[0]
    s["teams"]["self"][0]={"species":"Ditto","ability":"Limber","moves":["Transform"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}}
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        env.step({"self":6,"opponent":7},revision=env.observation("self")["revision"])
        for side in ("self","opponent"):
            v=env.observation(side,include_history=True)
            assert any("|-transform|" in p for p in v["public_history"])
            row=enc.project(v)["active"][0 if side=="self" else 1]
            assert row["types"]==("Bug","Steel")
            # Exact current types do not rewrite its observed Ditto identity.
            assert row["details"].startswith("Ditto")
            enc.encode(v)


def test_native_illusion_appearance_is_not_current_type_authority(checkout, enc):
    s=fixture_scenarios()[0]
    s["teams"]["opponent"][0]={"species":"Zoroark","ability":"Illusion","item":"Focus Sash","moves":["Dark Pulse","Protect"],"level":50,"nature":"Hardy","evs":{"hp":32,"spe":32,"def":2}}
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        other=env.observation("self",include_history=True)
        own=env.observation("opponent",include_history=True)
        assert enc.project(other)["active"][1]["types"] is None
        assert enc.project(own)["active"][0]["types"]==("Dark",)
        enc.encode(other);enc.encode(own)
        env.step({"self":6,"opponent":6},revision=other["revision"])
        other=env.observation("self",include_history=True)
        assert any("|replace|" in p for p in other["public_history"])
        assert enc.project(other)["active"][1]["types"]==("Dark",)
        enc.encode(other)


def test_native_mega_public_form_types_without_private_state(checkout, enc):
    s=fixture_scenarios()[0]
    s["teams"]["self"][0]["item"]="Charizardite X"
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        initial=env.observation("self",include_history=True)
        assert initial["action_mask"][10]
        env.step({"self":10,"opponent":7},revision=initial["revision"])
        for side in ("self","opponent"):
            v=env.observation(side,include_history=True)
            row=enc.project(v)["active"][0 if side=="self" else 1]
            assert row["types"]==("Fire","Dragon")
            enc.encode(v)


def test_regularized_native_train_save_load_resume_and_old_compatibility(checkout, enc, tmp_path):
    from advisor.learned_gym import ShowdownLearningEnv
    from advisor.learned_regularized_ppo import RegularizedMaskablePPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    vector = DummyVecEnv([lambda:ShowdownLearningEnv(checkout,enc,curriculum_version="showdown-learning-curriculum-v8",opponents=["max_power"])])
    try:
        m=RegularizedMaskablePPO(StrategicPublicCategoricalPolicy,vector,seed=31,n_steps=8,batch_size=8,n_epochs=1,gamma=1,gae_lambda=.95,ent_coef=.01,zero_avoiding_beta=.001,device="cpu")
        m.learn(32)
        require_finite_ppo(m,rollout=True)
        assert optimizer_steps(m)==4
        path=save_checkpoint(m,enc,tmp_path/"new",{})
        loaded=LearnedPolicy(path,CATALOG)
        assert loaded.encoder.version==VERSION and type(loaded.model) is RegularizedMaskablePPO
        assert optimizer_steps(loaded.model)==4
        loaded.model.set_env(vector);loaded.model.learn(8,reset_num_timesteps=False)
        require_finite_ppo(loaded.model,rollout=True)
        assert optimizer_steps(loaded.model)==5 and loaded.model.num_timesteps==40
        assert loaded.model.logger.name_to_value["train/zero_avoiding_beta"]==.001
        assert loaded.model.logger.name_to_value["train/regularization_loss"]>0
        assert loaded.model.policy.optimizer.state
        old=RuntimeAbilityCategoricalEncoder(CATALOG)
        old_path=save_checkpoint(model(old),old,tmp_path/"old",{})
        assert LearnedPolicy(old_path,CATALOG).encoder.catalog_fingerprint=="ab559de5b33e209867333403d45eabb6c3a73ee944bded7ad599ba1f3d3319a2"
        metadata=Path(path).with_suffix(".json");data=json.loads(metadata.read_text());data["encoder_version"]=old.version;metadata.write_text(json.dumps(data))
        with pytest.raises(ValueError):LearnedPolicy(path,CATALOG)
    finally:vector.close()


def test_source_trainer_opt_in_requires_fresh_transfer_optimizer(enc):
    e={"encoder_version":VERSION,"seed":31,"steps":1024,"gamma":1,"gae_lambda":.95,"transfer_model":"model.zip","fresh_optimizer":True}
    validate_config({"schema_version":"showdown-autonomous-training-v1","max_runtime_seconds":60,"experiments":[e]})
    e["fresh_optimizer"]=False
    with pytest.raises(ValueError):
        validate_config({"schema_version":"showdown-autonomous-training-v1","max_runtime_seconds":60,"experiments":[e]})
