"""Corrected V5 public references, proper predictions and native PPO persistence."""
from copy import deepcopy
from pathlib import Path
import json,os
import gymnasium as gym
import numpy as np
import pytest
import torch
from stable_baselines3.common.vec_env import DummyVecEnv,SubprocVecEnv
from advisor.learned_combat_v5_strategic import VERSION,StrategicCombatV5Encoder,public_species_candidates,PREFIX,REF_WIDTH,priors
from advisor.learned_combat_v5_strategic_policy import StrategicCombatV5Policy,transfer_strategic_combat_v5_weights
from advisor.learned_combat_v5_strategic_aux import StrategicCombatV5PPO,supervised_loss,next_public_action,supervision_targets
from advisor.learned_combat_v5_references import reference_features,conditional_rolls,WIDTH
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy
from advisor.learned_policy import LearnedPolicy
from advisor.learned_parallel import LearningEnvFactory
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_action_signals import require_public_equivalence
from advisor.learned_public_boosts import public_boosts
from scripts.verify_showdown_integration import fixture_scenarios
from scripts.train_showdown_autonomous import save_checkpoint,optimizer_steps,BudgetCallback
from tests.test_integrated_combat_v5 import outputs

CAT=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'

@pytest.fixture(scope='module')
def checkout():
    path=os.environ.get('POKEADVICE_SHOWDOWN_CHECKOUT')
    if not path:pytest.skip('pinned native checkout required')
    return path

@pytest.fixture(scope='module')
def views(checkout):
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0]);a=[env.observation(s,include_history=True) for s in ('self','opponent')]
        env.step({'self':8,'opponent':8},revision=0)
        return a+[env.observation(s,include_history=True) for s in ('self','opponent')]

def model(e,policy=StrategicCombatV5Policy):
    class Spaces(gym.Env):
        action_space=gym.spaces.Discrete(35)
        observation_space=gym.spaces.Box(-2,4,(e.dimension,),dtype=np.float32)
    torch.set_num_threads(1)
    return StrategicCombatV5PPO(policy,Spaces(),n_steps=2,batch_size=2,n_epochs=1,gamma=1,gae_lambda=.95,ent_coef=.01,zero_avoiding_beta=.001,seed=119,device='cpu')

def test_version_prior_identity_and_v4_transfer(views):
    e=StrategicCombatV5Encoder(CAT);old=StrategicPublicCategoricalEncoder(CAT)
    source=model(old,StrategicPublicCategoricalPolicy);target=model(e)
    transfer_strategic_combat_v5_weights(target.policy,source.policy,e,old)
    assert not target.policy.optimizer.state
    for v in views:
        x=e.encode(v);assert len(x)==28822 and np.isfinite(x).all()
        np.testing.assert_array_equal(x[:old.dimension],old.encode(v))
        mask=np.array(v['action_mask'],bool)[None]
        for a,b in zip(outputs(target.policy,torch.tensor(x)[None],mask),outputs(source.policy,torch.tensor(old.encode(v))[None],mask)):
            torch.testing.assert_close(a,b,atol=5e-6,rtol=0)
    assert priors()[0]['training_teams']==256

@pytest.mark.parametrize('side',['self','opponent'])
def test_native_public_isolation(checkout,side):
    e=StrategicCombatV5Encoder(CAT);other='opponent' if side=='self' else 'self';s=fixture_scenarios()[0]
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);a=env.observation(side,include_history=True)
        s['teams'][other][0]['item']='Choice Scarf';s['teams'][other][0]['moves']=['Protect']
        env.reset(s);b=env.observation(side,include_history=True)
        require_public_equivalence(a,b);np.testing.assert_array_equal(e.encode(a),e.encode(b))
        for key in ('native_state','opponent_request','auxiliary_labels','future_seed'):
            c=deepcopy(a);c[key]={'private':1}
            with pytest.raises(ValueError):e.encode(c)

def test_only_real_illusion_can_expand_species(views):
    v=deepcopy(views[0]);c=public_species_candidates(v)
    assert len(c)==1
    v['state']['opponent_side']['preview'].append({'details':'Zoroark, L50'})
    assert 'zoroark' in public_species_candidates(v)
    v['state']['opponent_side']['preview'].append({'details':'Blissey, L50'})
    assert 'blissey' not in public_species_candidates(v)

def test_conditional_damage_public_coverage_and_missing_types(views):
    e=StrategicCombatV5Encoder(CAT)
    for v in views:
        r,t=reference_features(v,e.base,priors()[0]['native_moves'])
        assert r.shape==(35,24) and t.shape==(35,18)
        assert np.isfinite(r).all()
        assert not r[~np.array(v['action_mask'],bool)].any()
        assert r[6,2] and r[6,0]>0
        c=deepcopy(v);role='p2' if v['side']=='self' else 'p1'
        identity=c['state']['opponent_side']['active_identity']
        c['public_history'].append(f'|-start|{identity}|typechange|[from] move: Reflect Type|[of] {role}a: slot-0')
        a,_=reference_features(c,e.base,priors()[0]['native_moves']);assert not a[:,2].any()

def test_reference_hp_pinch_and_native_formula_owner():
    args=(50,90,150,120,'Fire',('Fire','Flying'),('Bug','Steel'),False,'flamethrower','none','none',False,False,False,'blaze','','','',False)
    normal=conditional_rolls(*args,155,155,1.)
    pinch=conditional_rolls(*args,30,155,1.)
    assert pinch[0]>normal[1]

@pytest.mark.parametrize('side,move',[('self','Flamethrower'),('opponent','Bullet Punch')])
def test_conditional_reference_matches_native_fixed_context(checkout,side,move):
    import subprocess
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0]);saved=env.save()
    # Coordinator-only oracle verifies the declared conditional formula. No
    # checkpoint/private actual stats are ever supplied to inference features.
    oracle=Path(__file__).resolve().parents[1]/'tools/showdown_bridge/damage-oracle.cjs'
    query={'case_id':side,'checkpoint':saved,'side':side,'move':move,'critical':False}
    native=json.loads(subprocess.check_output(['node',str(oracle),checkout],input=json.dumps([query]),text=True))[0]
    c=native['context'];a,d=c['attacker'],c['defender'];stats='atk' if c['is_physical'] else 'spa';defence='def' if c['is_physical'] else 'spd'
    actual=conditional_rolls(c['level'],c['move_power'],a['stats'][stats],d['stats'][defence],c['move_type'].title(),tuple(t.title() for t in a['types']),tuple(t.title() for t in d['types']),c['is_physical'],move.lower().replace(' ',''),'none','none',False,False,False,a['ability'],d['ability'],a['item'] or '',d['item'] or '',False,a['hp'],a['max_hp'],d['hp']/d['max_hp'])
    assert actual==(min(native['rolls']),max(native['rolls']))

def test_action_permutation_and_masks(views):
    from advisor.learned_combat_v5 import OLD_DIM,HP_EXTRA,HISTORY_EXTRA,TACTICAL
    from advisor.learned_strategic_public import CONTEXT
    from advisor.learned_public_categories import ACTION
    e=StrategicCombatV5Encoder(CAT);m=model(e);x=torch.tensor(e.encode(views[0]))[None];y=x.clone();perm=np.random.default_rng(19).permutation(35)
    for start,width in ((CONTEXT,ACTION),(OLD_DIM+HP_EXTRA+HISTORY_EXTRA,TACTICAL),(PREFIX,REF_WIDTH)):
        y[:,start:start+35*width]=x[:,start:start+35*width].reshape(1,35,width)[:,perm].reshape(1,-1)
    mask=np.array(views[0]['action_mask'],bool)[None];a=outputs(m.policy,x,mask);b=outputs(m.policy,y,mask[:,perm])
    torch.testing.assert_close(a[1][:,perm],b[1],atol=5e-7,rtol=0);torch.testing.assert_close(a[2],b[2],atol=5e-7,rtol=0)
    assert not a[1][~torch.tensor(mask)].any()

@pytest.mark.parametrize('events,expected',[
    (['|cant|p2a: slot-0|par'], -1),(['|faint|p2a: slot-0'],-1),(['|drag|p2a: slot-1|Garchomp'], -1),
    (['|switch|p2a: slot-1|Garchomp'],1024),(['|move|p2a: slot-0|Flamethrower|p1a: slot-0'],'move'),
    (['|move|p2a: slot-0|Flamethrower|p1a: slot-0|[from] move: Sleep Talk'],-1)])
def test_executed_label_timing(events,expected):
    e=StrategicCombatV5Encoder(CAT)
    assert next_public_action(events,'p2',e)==(e.token('moves','Flamethrower') if expected=='move' else expected)

def test_proper_priors_gradients_and_prediction_decision_path(views):
    e=StrategicCombatV5Encoder(CAT);m=model(e);x=torch.tensor(np.stack([e.encode(views[0])]*2));mask=np.array([views[0]['action_mask']]*2,bool)
    y=supervision_targets(views[0],views[1],['|move|p2a: slot-0|Bullet Punch|p1a: slot-0'],e)
    z,s,_,_=m.policy.opponent_predictions(x)
    prior=m.policy.opponent_prior_predictions(x)
    for k in z:
        p=z[k].sigmoid()*s[k] if k=='moves' else z[k].masked_fill(~s[k].bool(),-1e8).softmax(1)
        torch.testing.assert_close(p,prior[k],atol=1e-6,rtol=1e-4)
    loss,_=supervised_loss(m.policy,x,[y,y]);loss.backward()
    assert sum(p.grad.abs().sum() for p in m.policy.mlp_extractor.prediction_heads.parameters() if p.grad is not None)>0
    assert m.policy.mlp_extractor.history_gru.weight_ih_l0.grad is None
    m.policy.zero_grad();d=m.policy.get_distribution(x,action_masks=mask);(-d.distribution.logits[:,6].mean()).backward()
    assert all(p.grad is None for p in m.policy.mlp_extractor.prediction_heads.parameters())
    before=outputs(m.policy,x,mask)
    with torch.no_grad():m.policy.mlp_extractor.prediction_heads['head_action'].bias[e.token('moves','Bullet Punch')]+=4
    after=outputs(m.policy,x,mask)
    assert not torch.equal(before[1],after[1])

def test_sparse_moves_do_not_inflate_switch_probability(views):
    e=StrategicCombatV5Encoder(CAT);m=model(e);x=torch.tensor(e.encode(views[0]))[None]
    prior=m.policy.opponent_prior_predictions(x)['action'][0]
    counts={int(k):v for k,v in priors()[0]['executed_action_counts'].items()}
    assert float(prior[-1])==pytest.approx((counts[1024]+1)/(sum(counts.values())+2),abs=1e-7)
    assert prior[-1]<.1 and float(prior.sum())==pytest.approx(1.)

def test_public_boost_swap_copy_caps_unknown_and_reset():
    a='p1a: A';b='p2a: B';h=[f'|switch|{a}|Salazzle|100/100',f'|switch|{b}|Gardevoir|100/100',
      f'|-boost|{b}|spa|2',f'|-unboost|{a}|spa|2',f'|-swapboost|{b}|{a}|atk, spa|[from] move: Power Swap']
    r=public_boosts(h);assert r[a]['spa']==2 and r[b]['spa']==-2
    h+=[f'|-copyboost|{b}|{a}',f'|-boost|{a}|spa|6'];r=public_boosts(h);assert r[b]['spa']==2 and r[a]['spa']==6
    h+=[f'|-invertboost|{a}',f'|-clearnegativeboost|{a}'];assert public_boosts(h)[a]['spa']==0
    h+=[f'|switch|{a}|Salazzle|100/100'];assert public_boosts(h)[a]['spa']==0
    assert public_boosts([f'|-boost|{a}|spa|2'])[a]['spa'] is None
    assert public_boosts([f'|switch|{a}|Salazzle|100/100',f'|-copyboost|{a}|{b}'])[a]['spa'] is None

@pytest.mark.parametrize('side',['self','opponent'])
def test_native_power_swap_reference_stages(checkout,side):
    other='opponent' if side=='self' else 'self';s=fixture_scenarios()[0]
    s['teams'][side][0]={'species':'Salazzle','ability':'Corrosion','item':'','moves':['Overheat','Protect'],'nature':'Serious','level':50,'evs':{'hp':22,'atk':0,'def':22,'spa':0,'spd':22,'spe':0}}
    s['teams'][other][0]={'species':'Gardevoir','ability':'Synchronize','item':'','moves':['Power Swap','Protect'],'nature':'Calm','level':50,'evs':{'hp':32,'atk':0,'def':2,'spa':0,'spd':32,'spe':0}}
    e=StrategicCombatV5Encoder(CAT)
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);result=env.step({side:6,other:6},revision=0)
        assert not result['action_rejected'] and not result['terminated']
        v=env.observation(side,include_history=True);st=public_boosts(v['public_history']);own=v['state']['self_side']['active_identity'];foe=v['state']['opponent_side']['active_identity']
        assert st[own]['spa']==0 and st[foe]['spa']==-2
        # The versioned reference fixes the public swap; the immutable V4
        # summary still reports the historical -2 and is not reinterpreted.
        assert v['state']['self_side']['pokemon'][own]['stat_stages']['spa']==-2
        x=e.encode(v);assert np.isfinite(x).all()
        ns=env.save()['native_state'];idx=0 if side=='self' else 1
        assert ns['sides'][idx]['pokemon'][0]['boosts']['spa']==st[own]['spa']

@pytest.mark.parametrize('side',['self','opponent'])
def test_native_mega_and_illusion_support(checkout,side):
    other='opponent' if side=='self' else 'self';s=fixture_scenarios()[0]
    def member(name,ability,item):return {'species':name,'ability':ability,'item':item,'moves':['Protect'],'level':50,'nature':'Serious','evs':{'hp':11,'atk':11,'def':11,'spa':11,'spd':11,'spe':11}}
    s['teams'][other][0]=member('Kangaskhan','Scrappy','Kangaskhanite');s['teams'][other][2]=member('Zoroark','Illusion','')
    e=StrategicCombatV5Encoder(CAT);m=model(e)
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);env.step({side:8,other:10},revision=0)
        v=env.observation(side,include_history=True);private=env.observation(other,include_history=True)
        y=supervision_targets(v,private,[],e);x=torch.tensor(e.encode(v))[None]
        with torch.no_grad():_,support,_,_=m.policy.opponent_predictions(x)
        assert y['abilities']==e.token('abilities','Parental Bond') and support['abilities'][0,y['abilities']]
        assert support['abilities'][0,e.token('abilities','Illusion')]

def test_native_heldout_prediction_scores(checkout,tmp_path):
    from scripts.evaluate_showdown_policy import evaluate
    e=StrategicCombatV5Encoder(CAT);m=model(e);path=save_checkpoint(m,e,tmp_path/'eval',{});p=LearnedPolicy(path,CAT)
    for seat in ('p1','p2'):
        row=evaluate(checkout,CAT,{'v5':p},cases=1,offset=89000009,curriculum_version='showdown-learning-curriculum-v8',rivals={'max_power':'max_power'},candidate_seat=seat,integrated_diagnostics=True)['records'][0]
        d=row['v5_prediction_metrics'];assert 0<d['sampled_public_decisions']<=8
        for k in ('action','abilities','items'):
            assert d['categorical'][k]['model']['n']>0 and np.isfinite(d['categorical'][k]['model']['nll_sum'])

@pytest.mark.parametrize('backend',['dummy','subproc'])
def test_actual_native_ppo_save_resume_and_algorithm_guard(checkout,tmp_path,backend):
    e=StrategicCombatV5Encoder(CAT);factory=LearningEnvFactory(checkout,str(CAT),VERSION,0,'showdown-learning-curriculum-v8',('max_power',),{},max_decisions=16)
    vec=DummyVecEnv([factory]) if backend=='dummy' else SubprocVecEnv([factory],start_method='spawn')
    class Budget:
        def stopping(self):return False
    try:
        m=StrategicCombatV5PPO(StrategicCombatV5Policy,vec,n_steps=16,batch_size=16,n_epochs=1,gamma=1,gae_lambda=.95,ent_coef=.01,zero_avoiding_beta=.001,seed=203,device='cpu')
        before={k:p.clone() for k,p in m.policy.state_dict().items()}
        m.learn(32,callback=BudgetCallback(Budget()));assert optimizer_steps(m)>0
        assert any(not torch.equal(v,before[k]) for k,v in m.policy.state_dict().items())
        assert np.isfinite(m.logger.name_to_value['train/v5_auxiliary_loss'])
        path=save_checkpoint(m,e,tmp_path/'saved',{});r=LearnedPolicy(path,CAT)
        assert type(r.model) is StrategicCombatV5PPO and r.model.zero_avoiding_beta==.001
        assert optimizer_steps(m)==optimizer_steps(r.model)
        r.model.set_env(vec);r.model.learn(16,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
        assert optimizer_steps(r.model)>optimizer_steps(m)
        meta=Path(path).with_suffix('.json');d=json.loads(meta.read_text());d['integrated_auxiliary']['coefficient']=.5;meta.write_text(json.dumps(d))
        with pytest.raises(ValueError,match='auxiliary_checkpoint'):LearnedPolicy(path,CAT)
    finally:vec.close()
