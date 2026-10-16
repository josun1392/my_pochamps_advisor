"""Integrated V5 public forward, private loss-only labels and native PPO proof."""
from copy import deepcopy
import os
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
import torch
import gymnasium as gym
from stable_baselines3.common.vec_env import DummyVecEnv,SubprocVecEnv
from advisor.learned_combat_v5 import (VERSION,DIMENSION,OLD_DIM,HP_EXTRA,HISTORY_EXTRA,TACTICAL,
    SIZES,FAMILIES,APPEARANCE_SUPPORT_VERSION,IntegratedCombatV5Encoder,tactical_features)
from advisor.learned_combat_v5_policy import (IntegratedCombatV5Policy,transfer_combat_v5_weights,transfer_combat_v5_appearance_weights,OLD_CONTEXT,NEW_CONTEXT)
from advisor.learned_combat_v5_aux import (IntegratedCombatV5PPO,supervision_targets,supervised_loss,next_public_family)
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder,CONTEXT
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy
from advisor.learned_public_categories import ACTION
from advisor.learned_policy import LearnedPolicy
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_parallel import LearningEnvFactory
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_action_signals import require_public_equivalence
from scripts.verify_showdown_integration import fixture_scenarios
from scripts.train_showdown_autonomous import save_checkpoint,optimizer_steps,BudgetCallback

CATALOG=Path(__file__).resolve().parents[1]/"models/showdown_mc_domain_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    c=os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not c:pytest.skip("external pinned engine required")
    return c


@pytest.fixture(scope="module")
def views(checkout):
    result=[]
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0])
        for i in range(4):
            result += [env.observation(s,include_history=True) for s in ("self","opponent")]
            if any(v["terminated"] for v in result[-2:]):break
            actions={s:next((a for a in (8,6,7,1,2,26) if env.observation(s)["action_mask"][a])) for s in ("self","opponent")}
            env.step(actions,revision=env.observation("self")["revision"])
    return result


def model(encoder,policy=IntegratedCombatV5Policy,seed=101):
    class Spaces(gym.Env):
        action_space=gym.spaces.Discrete(35)
        observation_space=gym.spaces.Box(-2,4,(encoder.dimension,),dtype=np.float32)
    torch.set_num_threads(1)
    return IntegratedCombatV5PPO(policy,Spaces(),n_steps=2,batch_size=2,n_epochs=1,
        gamma=1.,gae_lambda=.95,ent_coef=.01,learning_rate=5e-5,zero_avoiding_beta=.001,seed=seed,device="cpu")


def outputs(policy,x,mask):
    with torch.no_grad():
        d=policy.get_distribution(x,action_masks=mask)
        return d.distribution.logits.clone(),d.distribution.probs.clone(),policy.predict_values(x).clone()


def test_public_contract_old_prefix_hp_history_and_nominal_not_damage(views):
    e=IntegratedCombatV5Encoder(CATALOG);old=StrategicPublicCategoricalEncoder(CATALOG)
    for v in views:
        x=e.encode(v);assert x.shape==(DIMENSION,) and np.isfinite(x).all()
        np.testing.assert_array_equal(x[:OLD_DIM],old.encode(v))
        t=x[OLD_DIM+HP_EXTRA+HISTORY_EXTRA:OLD_DIM+HP_EXTRA+HISTORY_EXTRA+35*TACTICAL].reshape(35,TACTICAL)
        assert not t[:,8].any()  # exact damage explicitly unavailable
        assert (t[np.array(v['action_mask'],bool)&(np.arange(35)!=26),9]==1).all()
    assert e.base.catalog_fingerprint==old.catalog_fingerprint


@pytest.mark.parametrize("side",["self","opponent"])
def test_hidden_requests_never_change_public_features_or_masks(checkout,side):
    e=IntegratedCombatV5Encoder(CATALOG)
    with ShowdownEnvironment(checkout) as env:
        s=fixture_scenarios()[0];env.reset(s);a=env.observation(side,include_history=True)
        other="opponent" if side=="self" else "self"
        s['teams'][other][0]['item']='Choice Scarf'
        # Select a legal alternative without changing public preview/entry facts.
        s['teams'][other][0]['moves']=['Protect']
        env.reset(s);b=env.observation(side,include_history=True)
        require_public_equivalence(a,b)
        np.testing.assert_array_equal(e.encode(a),e.encode(b))
        for key in ('native_state','teams','future_seed','opponent_request'):
            polluted=deepcopy(a);polluted[key]={"secret":1}
            with pytest.raises(ValueError):e.encode(polluted)


def test_pretrained_transfer_both_heads_and_scratch_independence(views):
    e=IntegratedCombatV5Encoder(CATALOG);o=StrategicPublicCategoricalEncoder(CATALOG)
    source=model(o,StrategicPublicCategoricalPolicy,99)
    # Scratch construction cannot call the model loader or transfer owner.
    with patch.object(LearnedPolicy,'__init__',side_effect=AssertionError('no checkpoint initialization')):
        a=model(e,seed=103);b=model(e,seed=103);c=model(e,seed=107)
    assert all(torch.equal(p,b.policy.state_dict()[k]) for k,p in a.policy.state_dict().items())
    assert any(not torch.equal(p,c.policy.state_dict()[k]) for k,p in a.policy.state_dict().items())
    before={k:p.clone() for k,p in source.policy.state_dict().items()}
    transfer_combat_v5_weights(a.policy,source.policy,e,o)
    assert not a.policy.optimizer.state
    assert all(torch.equal(p,before[k]) for k,p in source.policy.state_dict().items())
    for v in views:
        x=torch.tensor(e.encode(v))[None];y=torch.tensor(o.encode(v))[None];mask=np.array(v['action_mask'],bool)[None]
        for left,right in zip(outputs(a.policy,x,mask),outputs(source.policy,y,mask)):
            torch.testing.assert_close(left,right,atol=5e-6,rtol=0)
    assert not a.policy.mlp_extractor.context[0].weight[:,OLD_CONTEXT:].any()


def test_action_row_permutation_mask_and_value(views):
    e=IntegratedCombatV5Encoder(CATALOG);m=model(e)
    x=torch.tensor(e.encode(views[0]))[None];mask=np.array(views[0]['action_mask'],bool)[None]
    perm=np.random.default_rng(11).permutation(35);y=x.clone()
    y[:,CONTEXT:OLD_DIM]=x[:,CONTEXT:OLD_DIM].reshape(1,35,ACTION)[:,perm].reshape(1,-1)
    offset=OLD_DIM+HP_EXTRA+HISTORY_EXTRA
    y[:,offset:offset+35*TACTICAL]=x[:,offset:offset+35*TACTICAL].reshape(1,35,TACTICAL)[:,perm].reshape(1,-1)
    a=outputs(m.policy,x,mask);b=outputs(m.policy,y,mask[:,perm])
    torch.testing.assert_close(a[1][:,perm],b[1],atol=5e-7,rtol=0)
    torch.testing.assert_close(a[2],b[2],atol=5e-7,rtol=0)
    assert not a[1][~torch.tensor(mask)].any()


def test_next_public_labels_are_executed_not_cancelled_or_forced(views):
    e=IntegratedCombatV5Encoder(CATALOG)
    assert next_public_family(['|cant|p2a: B|flinch','|move|p1a: A|Surf|p2a: B'],'p2',e.catalog,e.tactics)==-1
    assert next_public_family(['|drag|p2a: B|Scizor|100/100'],'p2',e.catalog,e.tactics)==-1
    assert next_public_family(['|move|p2a: B|Roost|p2a: B'],'p2',e.catalog,e.tactics)==FAMILIES.index('recovery')
    assert next_public_family(['|switch|p2a: B|Scizor|100/100'],'p2',e.catalog,e.tactics)==FAMILIES.index('switch')
    target=supervision_targets(views[0],views[1],[],e)
    assert target['action']==-1 and target['moves_complete']
    assert target['abilities']==e.token('abilities','Technician') and target['items']==2
    wrong=deepcopy(views[1]);wrong['own_request']['side']['id']='p1'
    with pytest.raises(ValueError,match='wrong_owner'):supervision_targets(views[0],wrong,[],e)


def test_native_switch_label_remains_bound_to_predecision_opponent(checkout):
    e=IntegratedCombatV5Encoder(CATALOG)
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0]);a=env.observation('self',include_history=True);b=env.observation('opponent',include_history=True)
        env.step({'self':8,'opponent':1},revision=0);after=env.observation('self',include_history=True)
        y=supervision_targets(a,b,after['public_history'][len(a['public_history']):],e)
        assert y['action']==FAMILIES.index('switch')
        assert y['abilities']==e.token('abilities','Technician')  # outgoing Scizor, not incoming Garchomp


@pytest.mark.parametrize('species,ability,stone,expected',[
    ('Glimmora','Toxic Debris','Glimmoranite','Adaptability'),
    ('Gardevoir','Trace','Gardevoirite','Pixilate')])
@pytest.mark.parametrize('side',['self','opponent'])
def test_current_transformed_ability_uses_native_public_dex(checkout,species,ability,stone,expected,side):
    e=IntegratedCombatV5Encoder(CATALOG);other='opponent' if side=='self' else 'self'
    s=fixture_scenarios()[0]
    s['teams'][other][0]={'species':species,'ability':ability,'item':stone,'moves':['Protect'],'level':50,
        'nature':'Serious','evs':{'hp':11,'atk':11,'def':11,'spa':11,'spd':11,'spe':11}}
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        own=env.observation(side,include_history=True);foe=env.observation(other,include_history=True)
        assert foe['action_mask'][10]
        env.step({side:8,other:10},revision=0)
        public=env.observation(side,include_history=True);private=env.observation(other,include_history=True)
        x=e.encode(public);offset=OLD_DIM+HP_EXTRA+HISTORY_EXTRA+35*TACTICAL
        token=e.token('abilities',expected)
        assert x[offset+token]==1
        target=supervision_targets(public,private,[],e)
        assert target['abilities']==token
        m=model(e)
        with torch.no_grad():
            _,_,_,_,_,_,_,supports,known,_=m.policy.mlp_extractor.components(torch.tensor(x)[None])
        assert supports['abilities'][0,token]
        if species=='Gardevoir':
            assert known['abilities'].item()==1  # prior Trace reveal is historical, not a current fact
            assert target['unknown_abilities']


def test_current_type_nominal_index_and_unknown_are_separate(views):
    e=IntegratedCombatV5Encoder(CATALOG);v=deepcopy(views[0])
    a=tactical_features(v,e.base)
    assert a[6,1]==1 and a[6,0]>0  # public Fire vs Bug/Steel prior
    v['public_history'].append('|-start|p2a: slot-0|typechange|Water')
    b=tactical_features(v,e.base)
    assert b[6,0]==pytest.approx(a[6,0]/8)
    v['public_history'].append('|-start|p2a: slot-0|typechange|[from] move: Reflect Type|[of] p1a: slot-0')
    c=tactical_features(v,e.base)
    assert c[6,0]==0 and c[6,1]==0 and c[6,8]==0 and c[6,9]==1


@pytest.mark.parametrize('side',['self','opponent'])
def test_versioned_appearance_support_keeps_illusion_and_public_mega_domain(checkout,side):
    old=IntegratedCombatV5Encoder(CATALOG)
    fixed=IntegratedCombatV5Encoder(CATALOG,version=APPEARANCE_SUPPORT_VERSION)
    assert old.catalog_fingerprint=='f8e1917d3ee9992e6fcc94229a89fe36f2d4e187cbf8f3f7edb439ff95e9a755'
    assert fixed.catalog_fingerprint!=old.catalog_fingerprint and fixed.dimension==old.dimension
    other='opponent' if side=='self' else 'self';s=fixture_scenarios()[0]
    def member(species,ability,item):
        return {'species':species,'ability':ability,'item':item,'moves':['Protect'],'level':50,
            'nature':'Serious','evs':{'hp':11,'atk':11,'def':11,'spa':11,'spd':11,'spe':11}}
    s['teams'][other][0]=member('Kangaskhan','Scrappy','Kangaskhanite')
    s['teams'][other][2]=member('Zoroark','Illusion','')
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);env.step({side:8,other:10},revision=0)
        public=env.observation(side,include_history=True);private=env.observation(other,include_history=True)
        x=old.encode(public);y=fixed.encode(public)
        target=supervision_targets(public,private,[],fixed)['abilities'];assert target==fixed.token('abilities','Parental Bond')
        offset=OLD_DIM+HP_EXTRA+HISTORY_EXTRA+35*TACTICAL
        assert not x[offset+target] and y[offset+target]
        assert y[offset+fixed.token('abilities','Illusion')]
        assert np.all(y[offset:offset+SIZES['abilities']]>=x[offset:offset+SIZES['abilities']])
        np.testing.assert_array_equal(x[:offset],y[:offset])


def test_appearance_v2_transfer_save_reload_and_v1_remain_separate(views,tmp_path):
    old=StrategicPublicCategoricalEncoder(CATALOG)
    encoder=IntegratedCombatV5Encoder(CATALOG,version=APPEARANCE_SUPPORT_VERSION)
    source=model(old,StrategicPublicCategoricalPolicy);target=model(encoder)
    transfer_combat_v5_weights(target.policy,source.policy,encoder,old)
    for v in views:
        mask=np.array(v['action_mask'],bool)[None]
        for a,b in zip(outputs(target.policy,torch.tensor(encoder.encode(v))[None],mask),
                       outputs(source.policy,torch.tensor(old.encode(v))[None],mask)):
            torch.testing.assert_close(a,b,atol=5e-6,rtol=0)
    saved=save_checkpoint(target,encoder,tmp_path/'v2',{});loaded=LearnedPolicy(saved,CATALOG)
    assert loaded.encoder.version==APPEARANCE_SUPPORT_VERSION
    assert loaded.encoder.catalog_fingerprint==encoder.catalog_fingerprint
    assert type(loaded.model) is IntegratedCombatV5PPO
    assert not loaded.model.policy.optimizer.state


def test_explicit_v1_to_v2_migration_preserves_parameters_not_encoder_identity(views):
    old=IntegratedCombatV5Encoder(CATALOG);new=IntegratedCombatV5Encoder(CATALOG,version=APPEARANCE_SUPPORT_VERSION)
    source=model(old);target=model(new,seed=207)
    transfer_combat_v5_appearance_weights(target.policy,source.policy,new,old)
    assert not target.policy.optimizer.state
    for k,v in source.policy.state_dict().items():torch.testing.assert_close(v,target.policy.state_dict()[k],atol=0,rtol=0)
    for v in views:
        x=old.encode(v);y=new.encode(v)
        np.testing.assert_array_equal(x,y)  # ordinary fixtures have no affected appearance boundary
        mask=np.array(v['action_mask'],bool)[None]
        for a,b in zip(outputs(source.policy,torch.tensor(x)[None],mask),outputs(target.policy,torch.tensor(y)[None],mask)):
            torch.testing.assert_close(a,b,atol=0,rtol=0)
    with pytest.raises(ValueError,match='migration_required'):
        transfer_combat_v5_appearance_weights(source.policy,target.policy,old,new)


def test_bounded_native_prediction_diagnostics_both_seats(checkout,tmp_path):
    from scripts.evaluate_showdown_policy import evaluate
    from advisor.learned_evaluation_bank import EvaluationCaseBank
    e=IntegratedCombatV5Encoder(CATALOG);m=model(e);path=save_checkpoint(m,e,tmp_path/'eval_model',{});p=LearnedPolicy(path,CATALOG)
    for seat in ('p1','p2'):
        rows=evaluate(checkout,CATALOG,{'v5':p},cases=1,offset=88000009,curriculum_version='showdown-learning-curriculum-v8',
            rivals={'max_power':'max_power'},candidate_seat=seat,integrated_diagnostics=True)['records']
        d=rows[0]['v5_prediction_metrics']
        assert 0<d['sampled_public_decisions']<=8
        assert d['categorical']['action']['n']>0
        assert np.isfinite(d['categorical']['action']['nll_sum'])
        assert d['moves']['unknown_cells']>0 and np.isfinite(d['moves']['bce_sum'])


def test_auxiliary_gradients_and_predictions_connected_to_actor(views):
    e=IntegratedCombatV5Encoder(CATALOG);m=model(e)
    x=torch.tensor(np.stack([e.encode(views[0])]*2));mask=np.array([views[0]['action_mask']]*2,bool)
    targets=[supervision_targets(views[0],views[1],['|move|p2a: slot-0|Bullet Punch|p1a: slot-0'],e)]*2
    before=outputs(m.policy,x,mask)
    loss,metrics=supervised_loss(m.policy,x,targets);loss.backward()
    for h in m.policy.mlp_extractor.prediction_heads.values():assert h.weight.grad is not None and h.weight.grad.abs().sum()>0
    assert m.policy.mlp_extractor.history_gru.weight_ih_l0.grad is not None
    # No private truth is used in forward even if targets are changed.
    targets2=deepcopy(targets);targets2[0]['items']=e.token('items','Choice Scarf')
    after=outputs(m.policy,x,mask)
    for a,b in zip(before,after):torch.testing.assert_close(a,b,atol=0,rtol=0)
    with torch.no_grad():m.policy.mlp_extractor.prediction_heads['head_action'].bias[0]+=4
    changed=outputs(m.policy,x,mask)
    assert not torch.equal(before[1],changed[1])


@pytest.mark.parametrize('backend',['dummy','subproc'])
@pytest.mark.parametrize('version',[VERSION,APPEARANCE_SUPPORT_VERSION])
def test_real_native_ppo_checkpoint_optimizer_and_auxiliary_restart(checkout,tmp_path,backend,version):
    e=IntegratedCombatV5Encoder(CATALOG,version=version)
    factory=LearningEnvFactory(checkout,str(CATALOG),version,0,'showdown-learning-curriculum-v8',('max_power',),{},max_decisions=16)
    vec=DummyVecEnv([factory]) if backend=='dummy' else SubprocVecEnv([factory],start_method='spawn')
    class Budget:
        def stopping(self):return False
    try:
        m=IntegratedCombatV5PPO(IntegratedCombatV5Policy,vec,n_steps=16,batch_size=16,n_epochs=1,gamma=1,gae_lambda=.95,
            ent_coef=.01,learning_rate=5e-5,zero_avoiding_beta=.001,seed=109,device='cpu')
        old={k:v.clone() for k,v in m.policy.state_dict().items()}
        m.learn(32,callback=BudgetCallback(Budget()))
        assert m.num_timesteps==32 and optimizer_steps(m)>0
        assert any(not torch.equal(v,old[k]) for k,v in m.policy.state_dict().items())
        assert np.isfinite(m.logger.name_to_value['train/v5_auxiliary_loss'])
        path=save_checkpoint(m,e,tmp_path/'saved',{});r=LearnedPolicy(path,CATALOG)
        assert type(r.model) is IntegratedCombatV5PPO and r.model.zero_avoiding_beta==.001
        assert optimizer_steps(r.model)==optimizer_steps(m)
        for k,v in m.policy.state_dict().items():torch.testing.assert_close(v,r.model.policy.state_dict()[k],atol=0,rtol=0)
        r.model.set_env(vec);r.model.learn(16,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
        assert optimizer_steps(r.model)>optimizer_steps(m)
        metadata=Path(path).with_suffix('.json')
        import json
        d=json.loads(metadata.read_text());d.pop('integrated_auxiliary');metadata.write_text(json.dumps(d))
        with pytest.raises(ValueError,match='auxiliary_checkpoint'):LearnedPolicy(path,CATALOG)
    finally:vec.close()
