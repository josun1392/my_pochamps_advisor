"""Fixed-array/metadata tests only; no native steps or Adam updates."""
from copy import deepcopy
from types import SimpleNamespace
import json
import numpy as np
import pytest
import torch
from gymnasium import spaces
from stable_baselines3.common.buffers import RolloutBuffer

from advisor.learned_gae_lambda import (
    lambda_contract, validate_contract, validate_foundation_gae, validate_loaded,
    gae_arrays, FoundationCombatPPO, GaeOneFoundationPPO,
)


@pytest.mark.parametrize('lam',[.95,1.])
def test_independent_GAE_matches_maintained_buffer_with_terminal_and_cutoff(lam):
    b=RolloutBuffer(4,spaces.Box(-10,10,(2,),dtype=np.float32),spaces.Discrete(35),
        device='cpu',gae_lambda=lam,gamma=1.,n_envs=2)
    b.values[:]=np.array([[.2,-.1],[.4,.3],[.1,.5],[.6,.2]],np.float32)
    # env0 ends at t1, resets at t2; env1 ends at last step. Env0 final is a cutoff.
    b.rewards[:]=np.array([[0,0],[1,0],[0,0],[0,-1]],np.float32)
    b.episode_starts[:]=np.array([[1,1],[0,0],[1,0],[0,0]],np.float32)
    last=torch.tensor([.7,123.]);dones=np.array([False,True])
    expected=gae_arrays(b.values,b.rewards,b.episode_starts,last.numpy(),dones,lam)
    b.compute_returns_and_advantage(last,dones)
    assert np.array_equal(expected,b.advantages)
    assert np.array_equal(b.returns,b.values+b.advantages)
    if lam==1.:
        assert np.allclose(b.returns[:,0],[1,1,.7,.7])
        assert np.allclose(b.returns[:,1],[-1]*4)


def test_timeout_reward_correction_is_bootstrapped_once_not_draw():
    # Maintained MaskablePPO adds gamma*V(public_timeout) to reward before GAE.
    v=np.array([[.2]],np.float32);r=np.array([[.6]],np.float32)
    a=gae_arrays(v,r,np.ones_like(v),np.array([999.]),np.array([True]),1.)
    assert np.allclose(a+v,.6)  # done stops a second final-value bootstrap.


def model_shell(cls,lam,marker=None):
    m=object.__new__(cls);m.gae_lambda=lam;m.gamma=1.;m.max_grad_norm=.5
    m.rollout_buffer=SimpleNamespace(gae_lambda=lam,gamma=1.)
    if marker is not None:m.gae_lambda_experiment=marker
    return m


def test_historical_guard_is_not_enabled_by_attribute_or_lambda_change():
    for lam,marker in [(1.,None),(1.,lambda_contract()),(.95,lambda_contract())]:
        m=model_shell(FoundationCombatPPO,lam,marker)
        with pytest.raises(ValueError):m.train()
    validate_foundation_gae(model_shell(FoundationCombatPPO,.95))


def test_opt_in_exact_type_buffer_and_budget_fail_closed():
    m=model_shell(GaeOneFoundationPPO,1.,lambda_contract());validate_foundation_gae(m)
    m.gae_lambda_trained=65536;m.n_steps=128;m.n_envs=4
    with pytest.raises(ValueError,match='training_budget'):m.train()
    m.rollout_buffer.gae_lambda=.95
    with pytest.raises(ValueError,match='buffer_contract'):validate_foundation_gae(m)
    class Other(GaeOneFoundationPPO):pass
    with pytest.raises(ValueError):validate_foundation_gae(model_shell(Other,1.,lambda_contract()))


def test_metadata_and_loader_cannot_silently_remove_training_objective():
    from advisor.learned_regularized_ppo import checkpoint_algorithm
    from advisor.learned_combat_foundation import foundation_contract
    from advisor.learned_combat_v5_strategic_aux import auxiliary_contract
    from advisor.learned_objective import objective_contract
    c=lambda_contract();bad=deepcopy(c);bad['gae_lambda']=.9
    with pytest.raises(ValueError):validate_contract(bad)
    meta={'gae_lambda_experiment':c,'gae_lambda_trained':512,'gamma':1.,'gae_lambda':1.,
        'training_objective':objective_contract(1.,1.),'combat_foundation':foundation_contract(),
        'encoder_version':foundation_contract()['encoder'],'integrated_auxiliary':auxiliary_contract()}
    assert checkpoint_algorithm(meta) is GaeOneFoundationPPO
    m=model_shell(GaeOneFoundationPPO,1.,c);m.gae_lambda_trained=512;validate_loaded(m,meta)
    with pytest.raises(ValueError):validate_loaded(m,{})
    for field,value in [('gae_lambda',.95),('move_slot_consistency',{}),('gamma',.99)]:
        altered=deepcopy(meta);altered[field]=value
        with pytest.raises(ValueError):checkpoint_algorithm(altered)
    with pytest.raises(ValueError):validate_loaded(model_shell(FoundationCombatPPO,1.),{})


def test_advantage_normalization_and_actor_value_gradients_without_optimizer():
    logits=torch.tensor([[.2,.1,-.3],[.4,-.4,.8]],requires_grad=True)
    mask=torch.tensor([[1,1,0],[1,0,1]],dtype=torch.bool)
    dist=torch.distributions.Categorical(logits=logits.masked_fill(~mask,-1e8))
    chosen=torch.tensor([0,2]);old=dist.log_prob(chosen).detach()
    advantage=torch.tensor([1.2,-.7]);n=(advantage-advantage.mean())/(advantage.std()+1e-8)
    assert abs(float(n.mean()))<1e-6 and abs(float(n.std())-1)<1e-6
    value=torch.tensor([.1,-.1],requires_grad=True);target=torch.tensor([1.,-1.])
    ratio=(dist.log_prob(chosen)-old).exp()
    loss=-torch.minimum(n*ratio,n*ratio.clamp(.8,1.2)).mean()+.5*((value-target)**2).mean()
    loss.backward()
    assert torch.isfinite(logits.grad).all() and logits.grad[mask].abs().sum()>0
    assert not logits.grad[~mask].any() and value.grad.abs().sum()>0


def test_matched_config_isolates_lambda_and_evaluation_budget():
    from advisor.learned_gae_study import matched_configs,game_slots,POLICIES,SEEDS
    from advisor.learned_gae_lambda import VERSION,PARENT_SHA
    from advisor.learned_ppo_contract_audit import VERSION as AUDIT
    configs={}
    for key in POLICIES[1:]:
        c={'envs':4,'cpu_percent':50,'memory_mib':12288,'device':'cpu','vector_backend':'subproc',
            'transition_budget_scope':'trained_rollouts_v1','checkpoint_evaluation_mode':'disabled_for_frozen_study_v1',
            'checkpoint_steps':16384,'ppo_update_audit':AUDIT,'gae_matched_rollout':VERSION,
            'experiments':[{'name':key,'seed':int(key[2:]),'steps':65536,'initial_model_id':PARENT_SHA,
                'fresh_optimizer':False,'gae_lambda':1. if key.startswith('B') else .95}]}
        if key.startswith('B'):
            c['experiments'][0]['gae_lambda_experiment']=lambda_contract();c['gae_first_rollout_reference']='reference'
        configs[key]=c
    assert matched_configs(configs,PARENT_SHA)['max_new_Adam']==8192
    bad=deepcopy(configs);bad[f'B_{SEEDS[0]}']['experiments'][0]['fresh_optimizer']=True
    with pytest.raises(ValueError):matched_configs(bad,PARENT_SHA)
    cases=[{'scope':'train' if i<96 else 'heldout','index':i,'scenario_sha256':str(i)}for i in range(192)]
    slots=game_slots(cases);assert len(slots)==5760
    for key in POLICIES:
        own=[s for s in slots if s['policy']==key]
        assert len(own)==1152 and sum(s['scope']=='heldout'for s in own)==576


def test_first_rollout_checks_public_identity_but_not_changed_GAE(tmp_path):
    import gzip
    from advisor.learned_gae_lambda import GaeSignalRecorder
    ref=tmp_path/'A';own=tmp_path/'B';ref.mkdir();own.mkdir()
    name='rollout_1049088_fixed'
    fields=('raw_logits','probabilities','native_masks','actions','old_logp',
        'values','rewards','episode_starts','last_values','last_dones')
    data={k:np.zeros(4,np.float32)for k in fields}
    for folder,adv in [(ref,0),(own,1)]:
        np.savez(folder/(name+'.audit.npz'),**data,advantages=np.full(4,adv))
        rows=[{'observation_sha256':str(i),'legal_mask_bits':64,'action':6,'old_logp':0.,
            'value':0.,'reward':0.,'episode_start':False,'done':False,'truncated':False}for i in range(512)]
        with gzip.open(folder/(name+'.jsonl.gz'),'wt',encoding='utf8')as f:
            for row in rows:f.write(json.dumps(row)+'\n')
    recorder=GaeSignalRecorder(own,None,reference=ref)
    with np.load(own/(name+'.audit.npz'))as z:
        assert recorder.compare_first(own/(name+'.audit.npz'),name,z)['public_rows_exact']==512
    altered={**data,'values':np.ones(4,np.float32)}
    np.savez(own/(name+'.audit.npz'),**altered)
    with np.load(own/(name+'.audit.npz'))as z:
        with pytest.raises(ValueError,match='execution_mismatch'):recorder.compare_first(own/(name+'.audit.npz'),name,z)


def test_paired_analysis_parent_and_seat_gates_and_missing_receipts():
    from advisor.learned_gae_study import game_slots,analyze
    cases=[{'scope':s,'index':i,'scenario_sha256':str(i)}for i,s in enumerate(('train','heldout'))]
    rows=[{'slot':s,'record':{'winner':'self'if s['policy'].startswith('B')else'opponent','truncated':False}}
        for s in game_slots(cases)]
    result=analyze(rows,cases,resamples=32)
    assert result['conclusion']=='PROMISING_REQUIRES_INDEPENDENT_CONFIRMATION'
    assert result['heldout_mean_parent_comparisons'][1]['delta']==1.
    assert all(s['delta']==1. for s in result['heldout_seat_differences'])
    with pytest.raises(ValueError):analyze(rows[:-1],cases,resamples=32)


def test_trusted_initial_save_reload_preserves_weights_Adam_and_lambda(tmp_path):
    import os
    if not os.environ.get('POKEADVICE_GAE_PARENT'):
        pytest.skip('trusted original Foundation opt-in')
    from pathlib import Path
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_gae_lambda import initial_model,PARENT_SHA
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest
    from scripts.train_showdown_autonomous import save_checkpoint
    parent=os.environ['POKEADVICE_GAE_PARENT'];catalog=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
    a=LearnedPolicy(parent,catalog,expected_model_id=PARENT_SHA)
    b=initial_model(a.model,parent,{'gae_lambda_experiment':lambda_contract(),'fresh_optimizer':False},resume=False)
    p=save_checkpoint(b,a.encoder,tmp_path/'checkpoint',{})
    loaded=LearnedPolicy(p,catalog).model
    assert type(loaded) is GaeOneFoundationPPO and loaded.gae_lambda==loaded.rollout_buffer.gae_lambda==1.
    assert tensor_digest(a.model.policy.state_dict())==tensor_digest(loaded.policy.state_dict())
    assert optimizer_digest(a.model.policy)==optimizer_digest(loaded.policy)
    assert initial_model(loaded,p,{'gae_lambda_experiment':lambda_contract()},resume=True) is loaded
    with pytest.raises(ValueError):initial_model(loaded,p,{},resume=True)
    # Zero environment transitions and zero Adam steps throughout this test.
