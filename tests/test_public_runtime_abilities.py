from copy import deepcopy
from pathlib import Path
import json,os
import pytest
np=pytest.importorskip("numpy");torch=pytest.importorskip("torch")
from advisor.learned_public_categories import RuntimeAbilityCategoricalEncoder,RequestIdentityCategoricalEncoder,RUNTIME_ABILITY_VERSION,BITS,UNKNOWN,ABSENT
from advisor.learned_public_categories_policy import PublicCategoricalPolicy,transfer_runtime_ability_weights
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_environment import ShowdownEnvironment
from scripts.build_showdown_runtime_categories import build,OUTPUT
from scripts.train_showdown_autonomous import save_checkpoint,validate_config
from tests.test_public_categorical_observation import model
from scripts.verify_showdown_integration import fixture_scenarios
ROOT=Path(__file__).resolve().parents[1];CATALOG=ROOT/"models/showdown_mc_domain_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    p=os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not p:pytest.skip("pinned native checkout required")
    return p


def test_append_only_complete_registry_and_deterministic_builder(checkout):
    assert build(checkout)==json.loads(OUTPUT.read_text(encoding="utf-8"))==build(checkout)
    old,new=RequestIdentityCategoricalEncoder(CATALOG),RuntimeAbilityCategoricalEncoder(CATALOG)
    assert len(new.tokens["abilities"])==321 and new.dimension==old.dimension==15576
    assert all(new.tokens[k][n]==i for k,v in old.tokens.items() for n,i in v.items())
    assert len(set(new.tokens["abilities"].values()))==321 and max(new.tokens["abilities"].values())<2**BITS["abilities"]
    assert new.token("abilities","simple")==293
    for value in ({},{"knowledge":"unknown"},""):assert new.token("abilities",value)==UNKNOWN
    assert new.token("abilities",None)==ABSENT
    assert new.token("abilities","noability") not in {UNKNOWN,ABSENT}
    for value in ("future-fake-ability","simple<script>","@simple@","As One"):
        with pytest.raises(ValueError):new.token("abilities",value)
    with pytest.raises(ValueError):old.token("abilities","simple")


@pytest.mark.parametrize("route",["simple","worry","role","swap"])
def test_actual_native_public_runtime_routes_and_masks(checkout,route):
    s=fixture_scenarios()[0]
    if route=="simple": species,ability,moves="Audino","Klutz",["Simple Beam","Thunder"]
    elif route=="worry":species,ability,moves="Whimsicott","Infiltrator",["Worry Seed","Grassy Terrain"]
    else:species,ability,moves="Mr. Mime","Soundproof",["Role Play" if route=="role" else "Skill Swap","Psychic"]
    # Avoid duplicating an existing species in either legal six.
    s["teams"]["self"][0]={"species":species,"ability":ability,"moves":moves,"level":50,"gender":"M","nature":"Hardy","evs":{"hp":32,"spa":32,"spe":2}}
    old,new=RequestIdentityCategoricalEncoder(CATALOG),RuntimeAbilityCategoricalEncoder(CATALOG)
    m=model(new)
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);before=env.observation("self",include_history=True)
        np.testing.assert_array_equal(old.encode(before),new.encode(before))
        hidden=before["state"]["opponent_side"];assert hidden["pokemon"][hidden["active_identity"]]["current_ability"]=={"knowledge":"unknown"}
        result=env.step({"self":6,"opponent":7},revision=before["revision"])
        assert not result["action_rejected"]
        after=env.observation("self",include_history=True);untouched=deepcopy(after)
        x=new.encode(after);np.testing.assert_array_equal(x,new.encode(after));assert after==untouched
        target=after["state"]["opponent_side"] if route in {"simple","worry"} else after["state"]["self_side"]
        expected="simple" if route=="simple" else "insomnia" if route=="worry" else "technician"
        assert target["pokemon"][target["active_identity"]]["current_ability"]==expected
        if route=="simple":
            with pytest.raises(ValueError):old.encode(after)
        with torch.no_grad():
            mask=np.asarray(after["action_mask"],bool)[None,:];t=torch.tensor(x)[None,:]
            p=m.policy.get_distribution(t,action_masks=mask).distribution.probs.numpy()
            np.testing.assert_array_equal(p,m.policy.get_distribution(t,action_masks=mask).distribution.probs.numpy())
            assert np.isfinite(p).all() and not np.any(p[~mask])
        assert after["action_mask"]==untouched["action_mask"]


def test_v2_weight_copy_fresh_optimizer_save_load_and_contracts(checkout,tmp_path):
    old,new=RequestIdentityCategoricalEncoder(CATALOG),RuntimeAbilityCategoricalEncoder(CATALOG)
    a,b=model(old),model(new)
    transfer_runtime_ability_weights(b.policy,a.policy,new,old)
    assert all(torch.equal(a.policy.state_dict()[k],v) for k,v in b.policy.state_dict().items())
    assert not b.policy.optimizer.state
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0]);view=env.observation("self",include_history=True)
        np.testing.assert_array_equal(old.encode(view),new.encode(view))
    pa=save_checkpoint(a,old,tmp_path/"old",{});pb=save_checkpoint(b,new,tmp_path/"new",{})
    ia,ib=LearnedPolicy(pa,CATALOG).infer(view),LearnedPolicy(pb,CATALOG).infer(view)
    assert ia["action_probabilities"]==ib["action_probabilities"] and ia["discounted_return_estimate"]==ib["discounted_return_estimate"]
    assert ib["encoder_version"]==RUNTIME_ABILITY_VERSION
    metadata=Path(pb).with_suffix(".json");data=json.loads(metadata.read_text());data["encoder_version"]=old.version;metadata.write_text(json.dumps(data))
    with pytest.raises(ValueError):LearnedPolicy(pb,CATALOG)


def test_native_hidden_information_isolation(checkout):
    s=fixture_scenarios()[0]
    for team in s["teams"].values():
        for p in team:p["gender"]="N" if p["species"]=="Rotom-Wash" else "M"
    changed=deepcopy(s);changed["teams"]["opponent"][0].update(ability="Swarm",item="Choice Scarf",moves=["U-turn","Iron Head"])
    encoder=RuntimeAbilityCategoricalEncoder(CATALOG)
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);a=env.observation("self",include_history=True)
        env.reset(changed,seed=[44,55,66,77]);b=env.observation("self",include_history=True)
    np.testing.assert_array_equal(encoder.encode(a),encoder.encode(b));assert a["action_mask"]==b["action_mask"]


def test_v3_opt_in_and_gamma_resume_contract():
    from advisor.learned_objective import experiment_objective
    e={"encoder_version":RUNTIME_ABILITY_VERSION,"gamma":1.0,"gae_lambda":.95,"seed":73011,"steps":1024,"fresh_optimizer":True}
    validate_config({"schema_version":"showdown-autonomous-training-v1","max_runtime_seconds":60,"experiments":[e]})
    assert experiment_objective(e,RUNTIME_ABILITY_VERSION)["gamma"]==1


def test_public_encoding_failure_audit_is_coordinator_only(tmp_path):
    from advisor.learned_gym import ShowdownLearningEnv
    env=object.__new__(ShowdownLearningEnv);env.encoder=RuntimeAbilityCategoricalEncoder(CATALOG)
    env.diagnostic_directory=tmp_path;env._episode_identity={"case_index":17}
    v={"episode_id":"public-owner","revision":4}
    with pytest.raises((ValueError,KeyError)):env._encode_public(v)
    # A missing state is a ValueError before any privileged access.
    files=list(tmp_path.glob("*.json"));assert len(files)==1
    audit=json.loads(files[0].read_text());assert audit["public_observation"]==v and "native_state" not in audit


def test_v3_real_native_updates_embedding_and_optimizer_resume(checkout,tmp_path):
    from advisor.learned_gym import ShowdownLearningEnv
    from stable_baselines3.common.vec_env import DummyVecEnv
    from sb3_contrib import MaskablePPO
    from scripts.train_showdown_autonomous import optimizer_steps
    encoder=RuntimeAbilityCategoricalEncoder(CATALOG)
    vector=DummyVecEnv([lambda:ShowdownLearningEnv(checkout,encoder,curriculum_version="showdown-learning-curriculum-v8",opponents=["max_power"])])
    try:
        m=MaskablePPO(PublicCategoricalPolicy,vector,seed=19,n_steps=8,batch_size=8,n_epochs=1,gamma=1,gae_lambda=.95,device="cpu")
        initial=m.policy.mlp_extractor.embeddings["category_abilities"].weight.detach().clone()
        m.learn(32)
        assert optimizer_steps(m)==4 and torch.any(initial!=m.policy.mlp_extractor.embeddings["category_abilities"].weight)
        path=save_checkpoint(m,encoder,tmp_path/"resume",{})
        loaded=LearnedPolicy(path,CATALOG);assert optimizer_steps(loaded.model)==4
        loaded.model.set_env(vector);loaded.model.learn(8,reset_num_timesteps=False)
        assert optimizer_steps(loaded.model)==5 and loaded.model.num_timesteps==40
    finally:vector.close()
