"""Offline contract gates; no native execution and no optimizer step."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pytest
import torch

from advisor.experimental_critic_training import (
    EXTRA, allowed, initialize, validate_model, frozen_digest, save, CriticTrainableActor,
)
from advisor.experimental_context_training import initialize as initialize_A, ResidualActor
from advisor.learned_policy import LearnedPolicy
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from scripts.pilot_critic_trainability_controlled import outputs, analyze, MODELS, cases_for, validation_metrics

ART = Path.home()/'.codex/artifacts'
OLD = ART/'experimental-candidate-context-controlled-train-pilot-v1-20261105/study'
CAT = Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'


@pytest.fixture(scope='module')
def parent():
    if not (OLD/'plan.json').exists():pytest.skip('retained historical artifacts unavailable')
    plan=json.loads((OLD/'plan.json').read_text())
    p=LearnedPolicy(plan['parent']['path'],CAT,expected_model_id=plan['parent']['sha256'])
    before=tensor_digest(p.model.policy.state_dict()),optimizer_digest(p.model.policy)
    yield p
    assert before==(tensor_digest(p.model.policy.state_dict()),optimizer_digest(p.model.policy))


@pytest.fixture(scope='module')
def views():
    folder=ART/'foundation-decision-snapshot-counterfactual-pilot-v1-20261025/run/capture/public'
    if not folder.exists():pytest.skip('retained public observations unavailable')
    return [json.loads(p.read_text())['observation'] for p in sorted(folder.glob('*.json'))]


def test_identical_initial_actor_critic_fresh_optimizer_and_checkpoint(parent,views,tmp_path):
    a=initialize_A(parent.model,'set');b=initialize(parent.model)
    assert tensor_digest(a.policy.state_dict())==tensor_digest(b.policy.state_dict())
    assert a.policy.optimizer.defaults==b.policy.optimizer.defaults
    assert not a.policy.optimizer.state and not b.policy.optimizer.state
    x=torch.tensor(np.stack([parent.encoder.encode(v) for v in views]))
    masks=np.array([v['action_mask'] for v in views],bool)
    for u,v in zip(outputs(a.policy,x,masks),outputs(b.policy,x,masks)):assert torch.equal(u,v)
    assert sum(p.numel() for n,p in b.policy.named_parameters() if n in EXTRA)==4160
    assert sum(p.numel() for p in a.policy.parameters())==sum(p.numel() for p in b.policy.parameters())==679099
    path=save(b,parent.encoder,tmp_path/'new',{'new_transitions':0,'new_Adam':0})
    restored=CriticTrainableActor(path,CAT)
    assert optimizer_digest(restored.model.policy)==optimizer_digest(b.policy)
    assert optimizer_clock(restored.model.policy)==0
    validate_model(restored.model,frozen_digest(b.policy))
    # Historical loader cannot silently resume the differently trainable objective.
    with pytest.raises((ValueError,FileNotFoundError)):ResidualActor(path,CAT)


def test_actor_and_critic_gradient_boundaries_without_update(parent,views):
    m=initialize(parent.model);p=m.policy
    x=torch.tensor(np.stack([parent.encoder.encode(v) for v in views]))
    frozen=frozen_digest(p)
    p.zero_grad(set_to_none=True)
    p.predict_values(x).square().mean().backward()
    critic=[v for n,v in p.named_parameters() if allowed(n) and n not in EXTRA]
    assert critic and all(v.grad is not None and torch.isfinite(v.grad).all() for v in critic)
    assert any(v.grad.abs().sum()>0 for v in critic)
    assert all(v.grad is None for n,v in p.named_parameters() if n in EXTRA or not allowed(n))
    p.zero_grad(set_to_none=True)
    z=p.mlp_extractor.forward_actor(x);(z[:,1]-z[:,2]).mean().backward()
    assert any(v.grad is not None and v.grad.abs().sum()>0 for n,v in p.named_parameters() if n in EXTRA)
    assert all(v.grad is None for n,v in p.named_parameters() if n not in EXTRA)
    assert frozen_digest(p)==frozen and optimizer_clock(p)==0
    validate_model(m,frozen)


def test_authoritative_masks_and_public_information_boundary(parent,views):
    m=initialize(parent.model)
    x=torch.tensor(np.stack([parent.encoder.encode(v) for v in views]))
    masks=np.array([v['action_mask'] for v in views],bool)
    probabilities=m.policy.get_distribution(x,action_masks=masks).distribution.probs
    assert not probabilities[~torch.tensor(masks)].any()
    wrong=masks.copy();wrong[:,26]=~wrong[:,26]
    with pytest.raises(ValueError):m.policy.get_distribution(x,action_masks=wrong)
    for key in ('native_state','future_seed','opponent_request','auxiliary_labels','scenario'):
        v=deepcopy(views[0]);v[key]={}
        with pytest.raises(ValueError):parent.encoder.encode(v)


def test_paired_analysis_keeps_training_repetitions_inside_pair_cluster():
    cases=[{'index':i,'pair':i} for i in range(3)]
    rows=[]
    for m in MODELS:
        for c in cases:
            for s in ('p1','p2'):
                won=m.startswith('Aprime')
                rows.append({'policy':m,'case':c['index'],'seat':s,'record':{
                    'winner':'self' if won else 'opponent','return':1 if won else -1,
                    'truncated':False,'native_choice_rejections':0,'value_discounted_return_mse':1.}})
    a=analyze(rows,cases,draws=100)
    assert a['team_pair_clusters']==3
    assert a['comparisons']['two_seed_mean']['Aprime_minus_A_terminal_return']==2
    assert a['comparisons']['two_seed_mean']['cluster95CI']==[2.,2.]
    with pytest.raises(ValueError):analyze(rows[:-1],cases,draws=100)
    with pytest.raises(ValueError):analyze(rows+[rows[0]],cases,draws=100)


def test_case_source_is_frozen_balanced_and_reproducible():
    teams=[[{'slot_identity':i}] for i in range(160)]
    cases=cases_for(teams)
    assert cases==cases_for(teams) and len(cases)==640
    assert len({tuple(c['scenario']['seed']) for c in cases})==640
    for p in range(80):
        cc=[c for c in cases if c['pair']==p]
        assert {(c['direction'],c['replicate']) for c in cc}=={(d,r) for d in (0,1) for r in range(4)}
        assert all(c['scenario']['teams']['self']==teams[2*p+c['direction']] for c in cc)


def test_historical_validation_transport_fails_closed(parent,views):
    with pytest.raises(ValueError,match='public_features_changed'):
        validation_metrics(parent,[{'observation':views[0],'feature_SHA256':'invalid',
                                    'GAE_target':0.}])


def test_native_evaluator_call_uses_existing_keyword_contract():
    import ast,inspect
    from scripts.evaluate_showdown_policy import evaluate
    path=Path(__file__).resolve().parents[1]/'scripts/pilot_critic_trainability_controlled.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='evaluate')
    inspect.signature(evaluate).bind(*[None for _ in call.args],**{k.arg:None for k in call.keywords})
