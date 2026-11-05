"""Offline gates. Never collect native fixtures; tiny copied Adam steps only."""
from copy import deepcopy
import json

import numpy as np
import pytest
import torch

from advisor.experimental_context_training import (
    EXTRA, SEEDS, contract, initialize, validate_model, frozen_digest, save, ResidualActor,
    TrainCases, paired_development,
)
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from tests.test_legal_set_context import source, evidence, outputs, assert_bits_equal, pp_pair, permuted, set_mask, CAT


@pytest.mark.parametrize('mode',['set','local'])
def test_zero_outputs_freeze_gradient_optimizer_and_checkpoint(source,evidence,tmp_path,mode):
    m=initialize(source.model,mode);p=m.policy
    assert sum(v.numel() for v in p.parameters())==679099
    assert sum(v.numel() for v in p.parameters() if v.requires_grad)==4160
    assert not p.optimizer.state
    assert p.optimizer.defaults==source.model.policy.optimizer.defaults
    views=evidence[0][:32];x=torch.tensor(np.stack([source.encoder.encode(v) for v in views]))
    masks=np.array([v['action_mask'] for v in views],bool)
    for a,b in zip(outputs(source.model.policy,x,masks),outputs(p,x,masks)):assert_bits_equal(a,b)
    frozen=frozen_digest(p);original=optimizer_digest(source.model.policy)
    row=next(c for c in evidence[1] if c['a']!=c['b']);xx,mm=pp_pair(evidence[0],row,source.encoder)
    # A differentiable public score contrast, not an optimal-action label.
    p.optimizer.zero_grad(set_to_none=True)
    z=p.mlp_extractor.forward_actor(xx)
    (z[0,row['a']]-z[0,row['b']]).backward()
    assert all(v.grad is None for n,v in p.named_parameters() if n not in EXTRA)
    assert all(v.grad is not None and torch.isfinite(v.grad).all() and v.grad.norm()>0
               for n,v in p.named_parameters() if n in EXTRA)
    torch.nn.utils.clip_grad_norm_(p.parameters(),.5,error_if_nonfinite=True)
    p.optimizer.step()
    validate_model(m,mode,frozen)
    assert optimizer_clock(p)==1 and frozen_digest(p)==frozen
    assert optimizer_digest(source.model.policy)==original
    path=save(m,source.encoder,tmp_path/mode,{'scope':'discarded_offline_contract_test_not_native_PPO'})
    restored=ResidualActor(path,CAT)
    assert optimizer_digest(restored.model.policy)==optimizer_digest(p)
    assert tensor_digest(restored.model.policy.state_dict())==tensor_digest(p.state_dict())
    for a,b in zip(outputs(p,xx,mm),outputs(restored.model.policy,xx,mm)):assert_bits_equal(a,b)
    validate_model(restored.model,mode,frozen)
    # A continued copied optimizer step still cannot touch frozen tensors.
    restored.model.policy.optimizer.zero_grad(set_to_none=True)
    restored.model.policy.mlp_extractor.forward_actor(xx).sum().backward()
    restored.model.policy.optimizer.step()
    assert optimizer_clock(restored.model.policy)==2
    validate_model(restored.model,mode,frozen)
    meta=tmp_path/mode/'residual_metadata.json'
    data=json.loads(meta.read_text());data['mode']='local' if mode=='set' else 'set'
    meta.write_text(json.dumps(data))
    with pytest.raises(ValueError):ResidualActor(path,CAT)


def test_only_context_source_differs_and_local_cannot_share_C(source,evidence):
    models={mode:initialize(source.model,mode) for mode in ('set','local')}
    assert contract('set')|{'mode':'local'}==contract('local')
    for n,v in models['set'].policy.state_dict().items():assert_bits_equal(v,models['local'].policy.state_dict()[n])
    for m in models.values():
        with torch.no_grad():m.policy.mlp_extractor.legal_set_residual.weight.copy_(.05*torch.eye(64))
    chosen={}
    for c in evidence[1]:chosen.setdefault(c['comparison'],c)
    for c in chosen.values():
        x,mask=pp_pair(evidence[0],c,source.encoder);a,b=c['a'],c['b']
        z={mode:outputs(m.policy,x,mask)[0] for mode,m in models.items()}
        torch.testing.assert_close(z['local'][0,a]-z['local'][0,b],z['local'][1,a]-z['local'][1,b],atol=4e-6,rtol=0)
        assert abs(float((z['set'][0,a]-z['set'][0,b])-(z['set'][1,a]-z['set'][1,b])))>1e-5


@pytest.mark.parametrize('mode',['set','local'])
def test_permutation_mask_and_private_boundaries(source,evidence,mode):
    m=initialize(source.model,mode)
    with torch.no_grad():m.policy.mlp_extractor.legal_set_residual.weight.copy_(.05*torch.eye(64))
    x=torch.tensor(np.stack([source.encoder.encode(v) for v in evidence[0][:16]]))
    mask=np.array([v['action_mask'] for v in evidence[0][:16]],bool)
    order=np.random.default_rng(116054).permutation(35)
    a=outputs(m.policy,x,mask);b=outputs(m.policy,permuted(x,order),mask[:,order])
    torch.testing.assert_close(a[0][:,order],b[0],atol=1e-5,rtol=0)
    torch.testing.assert_close(a[1][:,order],b[1],atol=3e-6,rtol=0)
    assert not a[1][~torch.tensor(mask)].any()
    for bad in [set_mask(x,np.zeros_like(mask)),set_mask(x,np.ones_like(mask)*.5),x*float('nan')]:
        with pytest.raises(ValueError):m.policy.get_distribution(bad)
    mismatch=mask.copy();mismatch[:,26]=~mismatch[:,26]
    with pytest.raises(ValueError):m.policy.get_distribution(x,action_masks=mismatch)
    for key in ('native_state','future_seed','opponent_request','auxiliary_labels'):
        v=deepcopy(evidence[0][0]);v[key]={}
        with pytest.raises(ValueError):source.encoder.encode(v)


def test_training_case_namespace_and_reciprocal_sampling():
    plan={'training_templates':[{'scenario':{'teams':{},'preview':{}}} for _ in range(16)],
          'case_identity':'test','excluded_native_seeds':[]}
    templates=[]
    for segment in range(16):
        for worker in range(4):
            factory=TrainCases(plan,SEEDS[0],segment,worker)
            templates.append(factory.template)
            assert factory('train',100)['seed']==factory('train',100)['seed']
            with pytest.raises(ValueError):factory('validation',100)
    assert all(templates.count(i)==4 for i in range(16))
    sample=TrainCases(plan,SEEDS[0],0,0)('train',100)['seed'];plan['excluded_native_seeds']=[sample]
    with pytest.raises(ValueError):TrainCases(plan,SEEDS[0],0,0)('train',100)


def test_development_pairing_and_draw_returns_are_not_win_differences():
    cases=[{'index':i,'pair':i//2} for i in range(4)]
    rows=[{'policy':m,'case':c['index'],'seat':s,'record':{'winner':('self' if m.startswith('A') else None),'truncated':False}}
          for m in ('A_s1','B_s1','A_s2','B_s2') for c in cases for s in ('p1','p2')]
    a=paired_development(rows,cases,draws=100)
    assert a['comparisons']['s1']['A_minus_B_terminal_return']==1
    assert a['comparisons']['s1']['A_minus_B_win_fraction']==1
    with pytest.raises(ValueError):paired_development(rows[:-1],cases,draws=100)
    with pytest.raises(ValueError):initialize(None,'local')
