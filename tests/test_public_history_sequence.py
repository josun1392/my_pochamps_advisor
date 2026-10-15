"""Public causal sequence, old V4 preservation and stateless native PPO proof."""
from copy import deepcopy
import os
import numpy as np
import pytest
import torch

from advisor.learned_history_sequence import (
    VERSION,ABLATED_VERSION,PublicHistorySequenceEncoder,history_sequence,
    OLD_DIMENSION,ROW,CAPACITY,META,FIELDS,EVENT_IDS,
)
from advisor.learned_history_sequence_policy import (
    PublicHistorySequencePolicy,transfer_history_sequence_weights,OLD_CONTEXT,NEW_CONTEXT,
)
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder,CONTEXT
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy
from advisor.learned_public_categories import ACTION
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_environment import ShowdownEnvironment
from scripts.verify_showdown_integration import fixture_scenarios
from scripts.train_showdown_autonomous import save_checkpoint,optimizer_steps
from tests.test_public_categorical_observation import model,CATALOG


@pytest.fixture(scope="module")
def native_views():
    checkout=os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:pytest.skip("pinned native engine required")
    views=[]
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0])
        for i in range(4):
            for side in ("self","opponent"):views.append(env.observation(side,include_history=True))
            actions={}
            for side,preferred in (("self",6),("opponent",7)):
                mask=env.observation(side)['action_mask']
                actions[side]=preferred if mask[preferred] else int(np.flatnonzero(mask)[0])
            env.step(actions,revision=env.observation("self")["revision"])
    return views


def decode(row):
    result={};offset=0
    for name,width in FIELDS:
        result[name]=int(np.dot(row[offset:offset+width],2**np.arange(width)));offset+=width
    result['numeric']=row[offset:]
    return result


def transport(history,side="self"):
    return {"side":side,"public_history":history}


def test_order_actor_recipient_known_unknown_and_no_retroactive_identity():
    base=StrategicPublicCategoricalEncoder(CATALOG)
    h=["|start","|switch|p1a: A|Charizard, L50|100/100","|switch|p2a: B|Scizor, L50|100/100","|turn|1",
       "|move|p1a: A|Flamethrower|p2a: B","|-damage|p2a: B|50/100","|-crit|p2a: B"]
    x,c=history_sequence(transport(h),base);rows=x[:-META].reshape(CAPACITY,ROW)
    move,damage=decode(rows[4]),decode(rows[5])
    assert move['event']==EVENT_IDS['move'] and move['actor']!=move['recipient']
    assert move['numeric'][7:11].tolist()==[1,0,0,1]
    assert damage['actor']==1 and damage['recipient']==move['recipient']
    assert damage['numeric'][3:5].tolist()==[.5,1]
    assert damage['actor_species']==1  # absent source announcement is Unknown
    unknown,_=history_sequence(transport(["|-activate|p2a: B|Unmodeled Public Effect"]),base)
    assert unknown[-3]==0 and unknown[-1]==1 and decode(unknown[:ROW])['actor_species']==1
    future=h+["|replace|p2a: Z|Zoroark, L50|50/100"]
    y,_=history_sequence(transport(future),base);new=y[:-META].reshape(CAPACITY,ROW)
    assert np.array_equal(rows[:7],new[:7])
    replacement=decode(new[7])
    assert replacement['actor_species']==base.token('species','Zoroark')
    assert replacement['recipient']==move['recipient']
    assert replacement['actor']!=replacement['recipient']
    # Re-encoding a prefix after a later view cannot retain future knowledge.
    assert np.array_equal(x,history_sequence(transport(h),base)[0])
    reentry,_=history_sequence(transport(future+["|switch|p2a: B|Scizor, L50|100/100"]),base)
    assert decode(reentry[:-META].reshape(CAPACITY,ROW)[8])['actor']!=move['recipient']
    reversed_events=h[:-2]+[h[-1],h[-2]]
    assert not np.array_equal(x,history_sequence(transport(reversed_events),base)[0])
    # Only the displayed fraction is carried, not a new exact-HP feature.
    assert np.array_equal(history_sequence(transport(['|-heal|p1a: A|153/153']),base)[0],
                          history_sequence(transport(['|-heal|p1a: A|185/185']),base)[0])


def test_last_six_turns_tail_cap_episode_reset_and_padding():
    base=StrategicPublicCategoricalEncoder(CATALOG)
    h=['|start']
    for turn in range(1,9):h += [f'|turn|{turn}','|-crit|p1a: A']
    x,c=history_sequence(transport(h),base)
    rows=x[:-META].reshape(CAPACITY,ROW);present=rows[:,-12]
    assert present.sum()==12  # turns3..8 inclusive
    assert c['tail_truncated'] is False and not rows[12:].any()
    new=['|start','|turn|1','|-miss|p1a: Z|p2a: K']
    assert np.array_equal(history_sequence(transport(h+new),base)[0],history_sequence(transport(new),base)[0])
    overflowing=['|start','|turn|1']+['|-crit|p1a: A']*100
    x,c=history_sequence(transport(overflowing),base)
    assert c['tail_truncated'] and c['encoded_events']==CAPACITY and x[-2]==1
    with pytest.raises(ValueError,match='noncausal'):
        history_sequence(transport(['|turn|2','|turn|1']),base)
    for event in ('split','request','seed','sideupdate','input'):
        with pytest.raises(ValueError,match='private_protocol'):
            history_sequence(transport([f'|{event}|secret']),base)
    with pytest.raises(ValueError):history_sequence(transport(['|-ability|p1a: A|InventedAbility']),base)


def test_native_pain_split_single_target_tags_and_supported_two_target_form():
    base=StrategicPublicCategoricalEncoder(CATALOG)
    h=['|start','|switch|p1a: A|Chandelure, L50|107/143','|switch|p2a: B|Falinks, L50|84/100 brn','|turn|2',
       '|move|p1a: A|Pain Split|p2a: B',
       '|-sethp|p2a: B|77/100 brn|[from] move: Pain Split|[silent]',
       '|-sethp|p1a: A|117/143|[from] move: Pain Split']
    encoded,_=history_sequence(transport(h),base)
    rows=encoded[:-META].reshape(CAPACITY,ROW)
    assert rows[:,-12].sum()==7
    assert decode(rows[5])['numeric'][3:5].tolist()==pytest.approx([.77,1])
    assert decode(rows[6])['numeric'][3:5].tolist()==pytest.approx([117/143,1])
    combined,_=history_sequence(transport(h[:5]+['|-sethp|p1a: A|117/143|p2a: B|77/100 brn']),base)
    rows=combined[:-META].reshape(CAPACITY,ROW)
    assert rows[:,-12].sum()==7 and decode(rows[5])['recipient']!=decode(rows[6])['recipient']


def test_actual_native_pain_split_and_episode_reset_both_seats():
    checkout=os.environ.get('POKEADVICE_SHOWDOWN_CHECKOUT')
    if not checkout:pytest.skip('pinned native engine required')
    s=fixture_scenarios()[0]
    s['teams']['self'][0],s['teams']['self'][5]=s['teams']['self'][5],s['teams']['self'][0]
    s['teams']['self'][0]['moves']=['Pain Split','Shadow Ball','Protect']
    e=PublicHistorySequenceEncoder(CATALOG)
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        first={side:e.encode(env.observation(side,include_history=True)) for side in ('self','opponent')}
        result=env.step({'self':6,'opponent':7},revision=env.observation('self')['revision'])
        assert not result['action_rejected']
        for side in ('self','opponent'):
            view=env.observation(side,include_history=True)
            assert any('|-sethp|' in line and 'Pain Split' in line for line in view['public_history'])
            e.encode(view)
        env.reset(s)
        for side in ('self','opponent'):
            assert np.array_equal(first[side],e.encode(env.observation(side,include_history=True)))


def test_public_boundaries_v4_prefix_and_control_consistency(native_views):
    old=StrategicPublicCategoricalEncoder(CATALOG)
    a,b=PublicHistorySequenceEncoder(CATALOG),PublicHistorySequenceEncoder(CATALOG,ABLATED_VERSION)
    assert a.dimension==b.dimension==21328 and old.dimension==15692
    assert a.tokens==b.tokens==old.tokens
    for view in native_views:
        before=deepcopy(view)
        x=a.encode(view);y=b.encode(view)
        assert np.array_equal(x[:OLD_DIMENSION],old.encode(view))
        assert np.array_equal(y[:OLD_DIMENSION],old.encode(view)) and not y[OLD_DIMENSION:].any()
        assert view==before
        changed=deepcopy(view)
        changed['own_request']={'unrelated_private_request':'never_read_by_sequence'}
        assert np.array_equal(history_sequence(view,old)[0],history_sequence(changed,old)[0])
        for forbidden in ('seed','checkpoint','native_state','scenario','teams','queue'):
            with pytest.raises(ValueError):a.encode({**view,forbidden:{}})


def test_transfer_initial_equality_gru_order_gradients_and_action_permutation(native_views):
    old=StrategicPublicCategoricalEncoder(CATALOG);source=model(old,StrategicPublicCategoricalPolicy)
    before={k:v.clone() for k,v in source.policy.state_dict().items()}
    initial=[]
    for seed,version in ((91,VERSION),(92,ABLATED_VERSION),(93,VERSION)):
        e=PublicHistorySequenceEncoder(CATALOG,version);m=model(e,PublicHistorySequencePolicy)
        torch.manual_seed(seed)
        transfer_history_sequence_weights(m.policy,source.policy,e,old)
        assert not m.policy.optimizer.state
        initial.append({k:v.clone() for k,v in m.policy.state_dict().items()})
        for view in native_views:
            a=torch.tensor(old.encode(view))[None];b=torch.tensor(e.encode(view))[None]
            mask=np.asarray(view['action_mask'],dtype=bool)[None]
            with torch.no_grad():
                assert torch.allclose(source.policy.mlp_extractor.forward_actor(a),m.policy.mlp_extractor.forward_actor(b),atol=2e-6,rtol=1e-6)
                assert torch.allclose(source.policy.predict_values(a),m.policy.predict_values(b),atol=2e-6,rtol=1e-6)
                pa=source.policy.get_distribution(a,action_masks=mask).distribution.probs
                pb=m.policy.get_distribution(b,action_masks=mask).distribution.probs
                assert torch.allclose(pa,pb,atol=1e-6) and not pb[~torch.tensor(mask)].any()
                perm=torch.arange(34,-1,-1);z=b.clone()
                z[:,CONTEXT:OLD_DIMENSION]=b[:,CONTEXT:OLD_DIMENSION].reshape(1,35,ACTION)[:,perm].flatten(1)
                assert torch.allclose(m.policy.mlp_extractor.forward_actor(z),m.policy.mlp_extractor.forward_actor(b)[:,perm],atol=1e-6)
    assert all(all(torch.equal(v,d[k]) for k,v in initial[0].items()) for d in initial[1:])
    e=PublicHistorySequenceEncoder(CATALOG);m=model(e,PublicHistorySequencePolicy)
    transfer_history_sequence_weights(m.policy,source.policy,e,old)
    v=deepcopy(native_views[0]);h=v['public_history']+['|-crit|p1a: slot-0','|-crit|p2a: slot-0']
    a=torch.tensor(np.concatenate((old.encode(v),history_sequence(transport(h),old)[0])))[None]
    b=torch.tensor(np.concatenate((old.encode(v),history_sequence(transport(h[:-2]+h[-2:][::-1]),old)[0])))[None]
    with torch.no_grad():
        first=m.policy.mlp_extractor._public_rows(a)[0][:,-NEW_CONTEXT:]
        other=m.policy.mlp_extractor._public_rows(b)[0][:,-NEW_CONTEXT:]
        assert not torch.equal(first,other)
        assert torch.equal(first,m.policy.mlp_extractor._public_rows(a)[0][:,-NEW_CONTEXT:])
    for update in range(3):
        m.policy.optimizer.zero_grad();mask=np.asarray(v['action_mask'],dtype=bool)[None]
        action=int(np.flatnonzero(mask[0])[0]);dist=m.policy.get_distribution(a,action_masks=mask)
        loss=-dist.log_prob(torch.tensor([action])).mean()+(m.policy.predict_values(a)-.6).square().mean()
        loss.backward()
        if update==0:
            assert m.policy.mlp_extractor.context[0].weight.grad[:,-NEW_CONTEXT:].abs().sum()>0
            assert m.policy.mlp_extractor.critic[0].weight.grad[:,OLD_CONTEXT:OLD_CONTEXT+NEW_CONTEXT].abs().sum()>0
        else:assert sum(p.grad.abs().sum() for p in m.policy.mlp_extractor.history_gru.parameters())>0
        m.policy.optimizer.step()
    assert all(torch.equal(v,source.policy.state_dict()[k]) for k,v in before.items())


@pytest.mark.parametrize('version',[VERSION,ABLATED_VERSION])
def test_native_masked_updates_save_reload_optimizer_restart(version,tmp_path):
    from advisor.learned_gym import ShowdownLearningEnv
    from advisor.learned_regularized_ppo import RegularizedMaskablePPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    checkout=os.environ.get('POKEADVICE_SHOWDOWN_CHECKOUT')
    if not checkout:pytest.skip('pinned native engine required')
    torch.set_num_threads(1);e=PublicHistorySequenceEncoder(CATALOG,version)
    vector=DummyVecEnv([lambda:ShowdownLearningEnv(checkout,e,curriculum_version='showdown-learning-curriculum-v8',opponents=['max_power'])])
    try:
        m=RegularizedMaskablePPO(PublicHistorySequencePolicy,vector,seed=87011,n_steps=8,batch_size=8,n_epochs=1,
            gamma=1,gae_lambda=.95,ent_coef=.01,zero_avoiding_beta=.001,device='cpu')
        initial={k:v.clone() for k,v in m.policy.state_dict().items()}
        m.learn(32)
        assert optimizer_steps(m)==4 and all(torch.isfinite(p).all() for p in m.policy.parameters())
        assert any(not torch.equal(v,m.policy.state_dict()[k]) for k,v in initial.items())
        path=save_checkpoint(m,e,tmp_path/version,{})
        restored=LearnedPolicy(path,CATALOG)
        assert restored.encoder.version==version and restored.model.zero_avoiding_beta==.001
        assert optimizer_steps(restored.model)==4
        for key,state in m.policy.optimizer.state_dict()['state'].items():
            for name,value in state.items():assert torch.equal(value,restored.model.policy.optimizer.state_dict()['state'][key][name])
        restored.model.set_env(vector);restored.model.learn(8,reset_num_timesteps=False)
        assert optimizer_steps(restored.model)==5 and restored.model.num_timesteps==40
    finally:vector.close()


@pytest.mark.parametrize('side',['self','opponent'])
def test_native_hidden_equivalence_both_heads(side):
    checkout=os.environ.get('POKEADVICE_SHOWDOWN_CHECKOUT')
    if not checkout:pytest.skip('pinned native engine required')
    scenario=fixture_scenarios()[0]
    for team in scenario['teams'].values():
        for p in team:p['gender']='N' if p['species']=='Rotom-Wash' else 'M'
    changed=deepcopy(scenario);target='opponent' if side=='self' else 'self'
    changed['teams'][target][0].update(ability='Swarm' if side=='self' else 'Solar Power',item='Choice Scarf',
        moves=['U-turn','Iron Head'] if side=='self' else ['Flamethrower','Protect'])
    with ShowdownEnvironment(checkout) as env:
        env.reset(scenario);a=env.observation(side,include_history=True)
        env.reset(changed,seed=[22,33,44,55]);b=env.observation(side,include_history=True)
    e=PublicHistorySequenceEncoder(CATALOG);m=model(e,PublicHistorySequencePolicy)
    assert a['public_history']==b['public_history'] and a['own_request']==b['own_request'] and a['action_mask']==b['action_mask']
    assert np.array_equal(e.encode(a),e.encode(b))
    with torch.no_grad():
        x=torch.tensor(e.encode(a))[None];y=torch.tensor(e.encode(b))[None]
        assert torch.equal(m.policy.mlp_extractor.forward_actor(x),m.policy.mlp_extractor.forward_actor(y))
        assert torch.equal(m.policy.predict_values(x),m.policy.predict_values(y))
