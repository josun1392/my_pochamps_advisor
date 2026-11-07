"""No native, PPO learning, or optimizer steps in these contract tests."""
import ast
from copy import deepcopy
import json

import numpy as np
import pytest
import torch
from sb3_contrib import MaskablePPO

from advisor.experimental_actionable_advantage import (
    EXTRA,ORIGINAL,ActionableFoundationPPO,ActionableActor,initialize,save,
    normalized_advantages,train_trees,validate_model,frozen_digest,
)
from advisor.experimental_context_training import initialize as initialize_A,ResidualActor
from advisor.learned_combat_foundation import FoundationCombatPPO
from advisor.learned_regularized_ppo import RegularizedMaskablePPO
from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock
from scripts.pilot_critic_trainability_controlled import outputs,analyze
from tests.test_experimental_critic_training import parent,views,CAT


def masks(counts):
    return torch.arange(35)[None,:]<torch.tensor(counts)[:,None]


def test_full_actionable_matches_original_normalization_bit_exact():
    a=torch.arange(128,dtype=torch.float32)/17
    out,eligible=normalized_advantages(a,masks([2]*128))
    assert eligible.all() and torch.equal(out,(a-a.mean())/(a.std()+1e-8))


def test_mixed_statistics_only_subset_but_all_rows_and_original_loss_mean_remain():
    a=torch.tensor([-2.,7.,.5,-3.,2.]);mask=masks([2,1,3,1,2]);before=a.clone()
    out,eligible=normalized_advantages(a,mask)
    expected=(a-a[eligible].mean())/(a[eligible].std()+1e-8)
    assert torch.equal(out,expected) and torch.equal(a,before) and len(out)==5
    assert out[~eligible].abs().sum()>0  # Forced rows not silently removed/zeroed in normal batches.
    logits=torch.zeros((5,35),requires_grad=True)
    dist=torch.distributions.Categorical(logits=logits.masked_fill(~mask,-1e8))
    actions=torch.zeros(5,dtype=torch.long);logp=dist.log_prob(actions)
    ratio=(logp-logp.detach()).exp()
    loss=-torch.minimum(out*ratio,out*ratio.clamp(.8,1.2)).mean()
    torch.testing.assert_close(loss,-out.mean())
    loss.backward()
    assert not logits.grad[~eligible].any() and logits.grad[eligible].abs().sum()>0


@pytest.mark.parametrize('eligible_count',[0,1])
def test_insufficient_actionable_samples_zero_signal_no_full_batch_fallback(eligible_count):
    a=torch.tensor([-8.,1.,4.,20.]);mask=masks([2]*eligible_count+[1]*(4-eligible_count))
    out,eligible=normalized_advantages(a,mask)
    assert int(eligible.sum())==eligible_count and torch.equal(out,torch.zeros_like(a))
    assert torch.isfinite(out).all() and not torch.equal(out,(a-a.mean())/(a.std()+1e-8))
    again,_=normalized_advantages(a,mask);assert torch.equal(out,again)


def test_constant_actionable_values_keep_original_epsilon_and_finiteness():
    a=torch.tensor([3.,3.,7.]);out,_=normalized_advantages(a,masks([2,3,1]))
    assert torch.equal(out,torch.tensor([0.,0.,4e8]))
    assert torch.isfinite(out).all()


@pytest.mark.parametrize('defect',['empty_native_mask','nonbinary','nonfinite_advantage','shape','requires_grad'])
def test_invalid_inputs_fail_closed(defect):
    a=torch.tensor([1.,2.,3.]);mask=masks([2,2,2]).float()
    if defect=='empty_native_mask':mask[0]=0
    elif defect=='nonbinary':mask[0,0]=.5
    elif defect=='nonfinite_advantage':a[0]=float('nan')
    elif defect=='shape':mask=mask[:2]
    else:a.requires_grad_(True)
    with pytest.raises(ValueError):normalized_advantages(a,mask)


def test_only_one_upstream_assignment_changes_and_existing_wrappers_stay_in_mro():
    original,changed=train_trees();reversed_tree=deepcopy(changed);count=0
    for node in ast.walk(reversed_tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='_normalize_actionable_advantage':count+=1
    for node in ast.walk(reversed_tree):
        if (isinstance(node,ast.Assign) and isinstance(node.value,ast.Call)
                and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='_normalize_actionable_advantage'):
            node.value=ast.parse(ORIGINAL,mode='eval').body
    assert count==1 and ast.dump(original,include_attributes=False)==ast.dump(reversed_tree,include_attributes=False)
    mro=ActionableFoundationPPO.mro()
    assert mro.index(FoundationCombatPPO)<mro.index(RegularizedMaskablePPO)<mro.index(MaskablePPO)
    assert 'advantages.mean()' in __import__('inspect').getsource(MaskablePPO.train)


def test_initial_outputs_frozen_boundaries_fresh_Adam_and_typed_reload(parent,views,tmp_path):
    a=initialize_A(parent.model,'set');n=initialize(parent.model)
    x=torch.tensor(np.stack([parent.encoder.encode(v) for v in views]));mask=np.array([v['action_mask'] for v in views],bool)
    assert tensor_digest(a.policy.state_dict())==tensor_digest(n.policy.state_dict())
    assert not n.policy.optimizer.state and n.policy.optimizer.defaults==a.policy.optimizer.defaults
    for aa,bb in zip(outputs(a.policy,x,mask),outputs(n.policy,x,mask)):assert torch.equal(aa,bb)
    fixed=frozen_digest(n.policy)
    n.policy.zero_grad(set_to_none=True)
    z=n.policy.mlp_extractor.forward_actor(x);(z[:,1]-z[:,2]).mean().backward()
    assert any(p.grad is not None and p.grad.abs().sum()>0 for name,p in n.policy.named_parameters() if name in EXTRA)
    assert all(p.grad is None for name,p in n.policy.named_parameters() if name not in EXTRA)
    validate_model(n,fixed);assert optimizer_clock(n.policy)==0
    path=save(n,parent.encoder,tmp_path/'typed',{'new_Adam':0,'new_transitions':0})
    import random
    numpy_before=np.random.get_state();python_before=random.getstate();torch_before=torch.get_rng_state().clone()
    restored=ActionableActor(path,CAT)
    numpy_after=np.random.get_state()
    assert numpy_before[0]==numpy_after[0] and np.array_equal(numpy_before[1],numpy_after[1]) and numpy_before[2:]==numpy_after[2:]
    assert python_before==random.getstate() and torch.equal(torch_before,torch.get_rng_state())
    assert type(restored.model) is ActionableFoundationPPO and restored.model.normalize_advantage
    assert optimizer_digest(restored.model.policy)==optimizer_digest(n.policy)
    validate_model(restored.model,fixed)
    with pytest.raises((FileNotFoundError,ValueError)):ResidualActor(path,CAT)
    raw_base=FoundationCombatPPO.load(path,device='cpu')
    with pytest.raises(ValueError,match='normalization_model_contract'):raw_base.train()


def test_shared_cluster_analysis_preserves_default_and_supports_explicit_treatment_prefix():
    cases=[{'index':0,'pair':0},{'index':1,'pair':1}]
    rows=[{'policy':m,'case':c['index'],'seat':s,'record':{'winner':'self' if m.startswith('An') else 'opponent',
        'return':1 if m.startswith('An') else -1,'truncated':False,'native_choice_rejections':0,'value_discounted_return_mse':1.}}
        for m in ('Foundation','A_s1','A_s2','An_s1','An_s2') for c in cases for s in ('p1','p2')]
    result=analyze(rows,cases,draws=100,treatment_prefix='An')
    assert result['comparisons']['two_seed_mean']['An_minus_A_terminal_return']==2
    assert result['team_pair_clusters']==2
    with pytest.raises(ValueError):analyze(rows,cases,draws=100)
