"""Masked temperature arithmetic and actual Foundation offline recovery.

No native reset/step. Optional trusted external captures exercise the exact
674,939-parameter policy with fixed existing inputs, never new environment data.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import numpy as np
import pytest
import torch
from stable_baselines3.common.logger import configure
from sb3_contrib.common.maskable.distributions import MaskableCategoricalDistribution

from advisor.learned_temperature import (
    temperature_contract, validate_temperature, at_progress, distribution_temperature,
    TemperatureFoundationPPO, model_temperature_contract,
)
from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatPolicy
from advisor.learned_parent_anchor import optimizer_digest, optimizer_clock, tensor_digest
from advisor.learned_regularized_ppo import legal_uniform_kl, checkpoint_algorithm
from advisor.learned_temperature_study import matched_configs, game_slots, analyze, SEEDS, POLICIES


def distribution_policy():
    # Only the maintained policy's actual distribution factory is needed here.
    p = object.__new__(FoundationCombatPolicy)
    torch.nn.Module.__init__(p)
    p.action_net = torch.nn.Identity()
    p.action_dist = MaskableCategoricalDistribution(35)
    return p


@pytest.mark.parametrize('t', [1., 1.5])
def test_masked_formula_logp_entropy_KL_ratio_and_gradients(t):
    p = distribution_policy()
    z = torch.linspace(-2, 3, 70).reshape(2, 35).requires_grad_(True)
    mask = torch.zeros(2, 35, dtype=torch.bool); mask[0, [0, 6, 8, 27]] = True; mask[1, 6] = True
    with distribution_temperature(p, t):
        d = p._get_action_dist_from_latent(z); d.apply_masking(mask)
        probabilities = d.distribution.probs
        manual = (z/t).masked_fill(~mask, -torch.inf).softmax(1)
        torch.testing.assert_close(probabilities, manual, rtol=0, atol=1e-7)
        assert not probabilities[~mask].any()
        action = d.get_actions(deterministic=True)
        old = d.log_prob(action).detach()
        lp = d.log_prob(action)
        assert torch.equal(torch.exp(lp-old), torch.ones(2))
        torch.testing.assert_close(d.entropy(), -(manual*manual.clamp(min=1e-30).log()).sum(1), atol=1e-6, rtol=0)
        kl = legal_uniform_kl(d.distribution.logits, mask)
        assert kl[1] == 0 and d.entropy()[1] == 0
        (-lp.mean()).backward()
        expected = (manual.detach()-torch.nn.functional.one_hot(action, 35))/t/2
        torch.testing.assert_close(z.grad, expected, atol=1e-7, rtol=0)
    assert '_get_action_dist_from_latent' not in p.__dict__
    assert torch.equal(z.argmax(1), (z/t).argmax(1))


def test_schedule_boundaries_metadata_and_exception_restoration():
    for treatment in (False, True):
        c=temperature_contract(treatment)
        assert at_progress(c, 0)==(1.5 if treatment else 1.)
        assert at_progress(c, 48640)==(1.5 if treatment else 1.)
        assert at_progress(c, 49152)==at_progress(c, 65536)==1.
    for bad in (-1, 1, 65537, 1., True):
        with pytest.raises(ValueError): at_progress(temperature_contract(True), bad)
    with pytest.raises(ValueError):validate_temperature({**temperature_contract(True),'inference_temperature':1.5})
    p=distribution_policy()
    with pytest.raises(RuntimeError):
        with distribution_temperature(p, 1.5):raise RuntimeError('test')
    assert '_get_action_dist_from_latent' not in p.__dict__
    with pytest.raises(ValueError,match='requires_foundation_checkpoint'):
        checkpoint_algorithm({'masked_temperature':temperature_contract(True)})


def configs():
    out={}
    for key in POLICIES[1:]:
        out[key]={'envs':4,'cpu_percent':50,'memory_mib':12288,'device':'cpu','vector_backend':'subproc',
            'transition_budget_scope':'trained_rollouts_v1','checkpoint_steps':16384,
            'checkpoint_evaluation_mode':'disabled_for_frozen_study_v1','validation_selection_mode':'diagnostic_fixed_budget_v1',
            'experiments':[{'name':key,'seed':int(key[2:]),'steps':65536,'initial_model_id':'a'*64,
                'fresh_optimizer':False,'masked_temperature':temperature_contract(key.startswith('B')),'opponents':['same']}]}
    return out


def cases():return [{'scope':'train' if i<96 else 'heldout','index':i,'scenario_sha256':str(i)} for i in range(192)]


def test_only_temperature_is_different_and_evaluation_5760_paired():
    assert matched_configs(configs(), 'a'*64)['trained_transitions']==262144
    for field,value in [('fresh_optimizer',True),('steps',32768),('opponents',['other']),('parent_policy_anchor',{}),('opponent_schedule',{})]:
        c=configs();c[POLICIES[2]]['experiments'][0][field]=value
        with pytest.raises(ValueError):matched_configs(c,'a'*64)
    slots=game_slots(cases())
    assert len(slots)==5760 and len({tuple(s.values()) for s in slots})==5760
    for policy in POLICIES:
        rows=[s for s in slots if s['policy']==policy]
        assert len(rows)==1152 and sum(s['scope']=='heldout' for s in rows)==576
        assert sum(s['seat']=='p1' for s in rows)==576
    small=[cases()[0],cases()[96]]
    rows=[{'slot':s,'record':{'winner':'self' if s['policy'].startswith('B') else 'opponent','truncated':False}} for s in game_slots(small)]
    result=analyze(rows,small,resamples=32)
    primary=next(r for r in result['paired_differences'] if r['scope']=='heldout' and r['rival']=='all' and r['comparison']=='mean_seed(B-A)')
    assert primary['delta']==1 and primary['case_cluster_95']==[1,1]
    for bad in (rows[:-1],rows+rows[:1]):
        with pytest.raises(ValueError):analyze(bad,small,resamples=32)


@pytest.fixture(scope='module')
def saved_inputs():
    parent=os.environ.get('POKEADVICE_TEMPERATURE_PARENT')
    capture=os.environ.get('POKEADVICE_TEMPERATURE_CAPTURE')
    if not parent or not capture:pytest.skip('optional trusted existing Foundation/capture required; no native collection')
    torch.set_num_threads(1)
    return parent, torch.load(Path(capture)/'actual/training.pt',map_location='cpu',weights_only=False)


def fixture_model(saved_inputs, treatment=None):
    parent,saved=saved_inputs
    model=(FoundationCombatPPO.load(parent,device='cpu') if treatment is None else
           TemperatureFoundationPPO.load(parent,device='cpu',masked_temperature=temperature_contract(treatment)))
    model.set_logger(configure(format_strings=[]));model._current_progress_remaining=.5
    fill_buffer(model,saved,1.5 if treatment else 1.)
    return model


def fill_buffer(model,saved,temperature):
    b=model.rollout_buffer
    for key,value in saved['buffer'].items():
        setattr(b,key,value.copy() if isinstance(value,np.ndarray) else value)
    x=b.observations.reshape(-1,28822);mask=b.action_masks.reshape(-1,35);actions=b.actions.reshape(-1).astype(int)
    values=[];logps=[]
    with torch.no_grad():
        with distribution_temperature(model.policy,temperature):
            for start in range(0,len(x),128):
                v,lp,_=model.policy.evaluate_actions(torch.as_tensor(x[start:start+128]),torch.as_tensor(actions[start:start+128]),action_masks=mask[start:start+128])
                values.append(v.flatten().numpy());logps.append(lp.numpy())
    b.values=np.concatenate(values).reshape(128,4);b.log_probs=np.concatenate(logps).reshape(128,4)
    model._auxiliary_rows=deepcopy(saved['loss_only_auxiliary_labels'])
    model._auxiliary_observations=x.copy();model._aux_groups=None;model._aux_weights=None
    if isinstance(model,TemperatureFoundationPPO):
        model._temperature_pending={'temperature':temperature,'trained_start':model.temperature_trained,'identity':'synthetic',
            'capture':None,'capture_SHA256':None,'entropy_mean':0.,'max_probability_mean':0.,'nontrivial_count':0}


def rng():return random.getstate(),np.random.get_state(),torch.get_rng_state()
def restore_rng(r):random.setstate(r[0]);np.random.set_state(r[1]);torch.set_rng_state(r[2])


def test_actual_Foundation_T1_loss_Adam_update_is_bit_identical(saved_inputs):
    base=fixture_model(saved_inputs)
    temp=fixture_model(saved_inputs,False)
    assert tensor_digest(base.policy.state_dict())==tensor_digest(temp.policy.state_dict())
    assert optimizer_digest(base.policy)==optimizer_digest(temp.policy)
    r=rng();base.train();restore_rng(r);temp.train()
    assert tensor_digest(base.policy.state_dict())==tensor_digest(temp.policy.state_dict())
    assert optimizer_digest(base.policy)==optimizer_digest(temp.policy)
    assert temp.temperature_trained==512


def test_wrong_behavior_logp_fails_before_any_Adam_step(saved_inputs):
    m=fixture_model(saved_inputs,True)
    fill_buffer(m,saved_inputs[1],1.)  # Deliberately oldlogp from wrong distribution.
    m._temperature_pending['temperature']=1.5
    before=(tensor_digest(m.policy.state_dict()),optimizer_digest(m.policy))
    with pytest.raises(ValueError,match='preupdate_oldlogp'):m.train()
    assert before==(tensor_digest(m.policy.state_dict()),optimizer_digest(m.policy))
    assert m.temperature_trained==0
    fill_buffer(m,saved_inputs[1],1.5)
    m.rollout_buffer.log_probs[0,0]=np.nan
    with pytest.raises(ValueError,match='nonfinite_stored_logp'):m.train()
    assert before==(tensor_digest(m.policy.state_dict()),optimizer_digest(m.policy))


def test_actual_temperature_updates_save_load_continue_and_boundary(saved_inputs,tmp_path):
    from scripts.train_showdown_autonomous import save_checkpoint
    from advisor.learned_combat_foundation import FoundationCombatEncoder
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_execution_alignment import digest
    m=fixture_model(saved_inputs,True)
    old=optimizer_clock(m.policy);m.train()
    assert m.temperature_trained==512 and optimizer_clock(m.policy)>old
    assert m.logger.name_to_value['train/masked_temperature']==1.5
    assert '_get_action_dist_from_latent' not in m.policy.__dict__
    catalog=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
    p=save_checkpoint(m,FoundationCombatEncoder(catalog),tmp_path/'saved',{})
    restored=LearnedPolicy(p,catalog,expected_model_id=digest(p)).model
    assert type(restored) is TemperatureFoundationPPO and restored.temperature_trained==512
    assert optimizer_digest(restored.policy)==optimizer_digest(m.policy)
    restored.set_logger(configure(format_strings=[]))
    fill_buffer(restored,saved_inputs[1],1.5);restored.train()
    assert restored.temperature_trained==1024 and optimizer_clock(restored.policy)>old
    restored.temperature_trained=48640
    fill_buffer(restored,saved_inputs[1],1.5);restored.train()
    assert restored.temperature_trained==49152
    fill_buffer(restored,saved_inputs[1],1.);restored.train()
    assert restored.temperature_trained==49664 and restored.logger.name_to_value['train/masked_temperature']==1.
    meta=json.loads(Path(p).with_suffix('.json').read_text());meta['temperature_state']['trained_transitions']=0
    Path(p).with_suffix('.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError,match='progress_mismatch'):LearnedPolicy(p,catalog)


def test_aborted_rollout_has_no_progress_and_original_buffer_method_restored(saved_inputs,monkeypatch):
    m=fixture_model(saved_inputs,True);m._temperature_pending=None
    monkeypatch.setattr(FoundationCombatPPO,'collect_rollouts',lambda *a,**kw:False)
    before=optimizer_digest(m.policy)
    assert not m.collect_rollouts()
    assert m.temperature_trained==0 and m._temperature_pending is None
    assert optimizer_digest(m.policy)==before and 'add' not in m.rollout_buffer.__dict__
    assert '_get_action_dist_from_latent' not in m.policy.__dict__
