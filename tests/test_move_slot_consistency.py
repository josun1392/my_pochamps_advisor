import numpy as np
import pytest
import torch
from torch import nn

from advisor.learned_move_slot_consistency import (
    transform, consistency_loss, consistency_contract, validate_contract, PERMUTATION,
    DIMENSION, CONTEXT, OLD_DIM, ACTION, BASE_ACTION, BASE_CONTEXT, ENTITY,
    ENTITY_NUMERIC, BITS, REFERENCE_BITS, PREFIX, REF_WIDTH, HP_EXTRA, HISTORY_EXTRA, TACTICAL,
)
from advisor.learned_public_categories import token_bits


def fixture():
    x = torch.zeros(2, DIMENSION)
    entities = x[:, BASE_CONTEXT:BASE_CONTEXT + 24 * ENTITY].reshape(2, 24, ENTITY)
    start = ENTITY_NUMERIC + BITS['species'] + BITS['abilities'] + BITS['items']
    entities[:, 0, [63, 64, 67, 69]] = 1
    for i in range(4):
        entities[:, 0, start + i * BITS['moves']:start + (i+1) * BITS['moves']] = torch.tensor(token_bits(3+i, BITS['moves']))
    rows = x[:, CONTEXT:OLD_DIM].reshape(2, 35, ACTION)
    for group in (6, 10, 27, 31):
        for i in range(4):
            rows[:, group+i, BASE_ACTION-1:BASE_ACTION-1 + REFERENCE_BITS] = torch.tensor(token_bits(1, REFERENCE_BITS))
            offset = BASE_ACTION-1+REFERENCE_BITS
            rows[:, group+i, offset:offset + BITS['moves']] = torch.tensor(token_bits(3+i, BITS['moves']))
            rows[:, group+i, 0] = i + 10
    rows[:, 6:10, -1] = 1
    for begin, width in ((OLD_DIM+HP_EXTRA+HISTORY_EXTRA, TACTICAL), (PREFIX, REF_WIDTH)):
        x[:, begin:begin+35*width] = torch.arange(35).repeat_interleave(width)
    return x


def test_complete_binding_involution_and_all_row_blocks():
    x = fixture(); before = x.clone()
    y, perm, eligible = transform(x)
    assert eligible.all() and perm.tolist() == PERMUTATION and torch.equal(x, before)
    z, _, _ = transform(y)
    assert torch.equal(z, x)
    for begin, width in ((CONTEXT, ACTION), (OLD_DIM+HP_EXTRA+HISTORY_EXTRA, TACTICAL), (PREFIX, REF_WIDTH)):
        assert torch.equal(y[:, begin:begin+35*width].reshape(2,35,width), x[:, begin:begin+35*width].reshape(2,35,width)[:,perm])
    assert torch.equal(y[:, OLD_DIM:OLD_DIM+HP_EXTRA+HISTORY_EXTRA], x[:, OLD_DIM:OLD_DIM+HP_EXTRA+HISTORY_EXTRA])
    assert torch.equal(y[:, PREFIX+35*REF_WIDTH:], x[:, PREFIX+35*REF_WIDTH:])
    assert torch.equal(y[:, BASE_CONTEXT+ENTITY:BASE_CONTEXT+24*ENTITY], x[:, BASE_CONTEXT+ENTITY:BASE_CONTEXT+24*ENTITY])


@pytest.mark.parametrize('kind', ['unknown', 'extra_move', 'no_move', 'wrong_record', 'duplicate', 'unsupported_action'])
def test_ambiguous_or_unestablished_observations_excluded(kind):
    x = fixture(); rows=x[:,CONTEXT:OLD_DIM].reshape(2,35,ACTION)
    start=ENTITY_NUMERIC+BITS['species']+BITS['abilities']+BITS['items']
    if kind == 'unknown': x[:,BASE_CONTEXT+start:BASE_CONTEXT+start+BITS['moves']] = 0
    if kind == 'extra_move': x[:,BASE_CONTEXT+start+4*BITS['moves']:BASE_CONTEXT+start+5*BITS['moves']] = torch.tensor(token_bits(9,10))
    if kind == 'no_move': rows[:,:, -1]=0;rows[:,26,-1]=1
    if kind == 'wrong_record': x[:,BASE_CONTEXT+67]=0
    if kind == 'duplicate':
        offset=BASE_ACTION-1+REFERENCE_BITS
        rows[:,7,offset:offset+BITS['moves']]=rows[:,6,offset:offset+BITS['moves']]
    if kind == 'unsupported_action': rows[:,14,-1]=1
    y,_,valid=transform(x)
    assert not valid.any() and torch.equal(y,x)


def test_native_mask_mismatch_and_empty_fail_closed():
    x=fixture(); mask=x[:,CONTEXT:OLD_DIM].reshape(2,35,ACTION)[:,:,-1].clone()
    mask[:,0]=1
    with pytest.raises(ValueError,match='mask_mismatch'):transform(x,mask)
    x[:,CONTEXT:OLD_DIM].reshape(2,35,ACTION)[:,:,-1]=0
    with pytest.raises(ValueError,match='native_mask'):transform(x)


def test_unknown_unused_capacity_is_not_absence_or_extra_move():
    x=fixture()
    start=BASE_CONTEXT+ENTITY_NUMERIC+BITS['species']+BITS['abilities']+BITS['items']+40
    for i in range(12):x[:,start+i*10]=1  # Native populated record uses Unknown=1.
    y,_,valid=transform(x)
    assert valid.all() and torch.equal(x[:,start:start+120],y[:,start:start+120])


def test_objective_loader_rejects_removed_or_mismatched_metadata():
    from types import SimpleNamespace
    from advisor.learned_move_slot_consistency import validate_loaded
    from advisor.learned_regularized_ppo import checkpoint_algorithm
    with pytest.raises(ValueError):validate_loaded(SimpleNamespace(move_slot_consistency=consistency_contract()),{})
    with pytest.raises(ValueError):checkpoint_algorithm({'move_slot_consistency':consistency_contract()})


def test_detached_owner_requires_actual_matching_survival_evidence(tmp_path):
    import json,sys
    from types import SimpleNamespace
    from advisor.learned_execution_alignment import digest
    from advisor.learned_move_slot_study import validate_detached_owner
    job=SimpleNamespace(inherited_job=True)
    with pytest.raises(RuntimeError):validate_detached_owner({},job)
    p=tmp_path/'probe.json';l=tmp_path/'launcher.json'
    p.write_text(json.dumps({'PID':123,'phase':'survived_launcher_exit','inherited_job':True,
        'completed_unix':109.,'executable':sys.executable}))
    l.write_text(json.dumps({'probe_PID':123,'launcher_exit_unix':100.,'training':0,'native':0}))
    plan={'detached_survival_proof':str(p),'detached_probe_launcher_receipt':str(l),
        'detached_survival_proof_sha256':digest(p),'detached_probe_launcher_receipt_sha256':digest(l)}
    assert validate_detached_owner(plan,job)['own_nested_CPU_RAM_job_required']
    p.write_text('{}')
    with pytest.raises(RuntimeError):validate_detached_owner(plan,job)


def test_trainer_independently_requires_validated_owner_and_keeps_old_default():
    from types import SimpleNamespace
    from scripts.train_showdown_autonomous import require_detached_owner
    job=SimpleNamespace(inherited_job=True)
    with pytest.raises(RuntimeError,match='persistence_not_verified'):require_detached_owner(job)
    with pytest.raises(RuntimeError,match='proof_invalid'):require_detached_owner(job,lambda j:{})
    assert require_detached_owner(SimpleNamespace(inherited_job=False)) is None
    proof={'own_nested_CPU_RAM_job_required':True}
    assert require_detached_owner(job,lambda j:proof) is proof


def test_JS_gradient_does_not_overwrite_distribution_or_inputs():
    x=fixture(); before=x.clone()
    class Actor(nn.Module):
        def __init__(self):
            super().__init__();self.weight=nn.Parameter(torch.tensor(.03))
        def forward_actor(self, x):
            start=BASE_CONTEXT+ENTITY_NUMERIC+BITS['species']+BITS['abilities']+BITS['items']
            context=x[:,start:start+1]
            slots=x[:,CONTEXT:OLD_DIM].reshape(-1,35,ACTION)[:,:,0]
            return slots*self.weight*(1+context)
    class Policy:
        action_net=nn.Identity()
        mlp_extractor=Actor()
        action_dist=object()
    p=Policy(); identity=p.action_dist
    mask=x[:,CONTEXT:OLD_DIM].reshape(2,35,ACTION)[:,:,-1]
    loss,m=consistency_loss(p,x,mask);loss.backward()
    assert 0 < loss < np.log(2) and p.mlp_extractor.weight.grad.abs()>0
    assert torch.equal(before,x) and p.action_dist is identity and m['eligible']==2


def test_single_legal_move_safe_zero_and_contract_strict():
    x=fixture();m=x[:,CONTEXT:OLD_DIM].reshape(2,35,ACTION)[:,:,-1];m.zero_();m[:,6]=1
    class Extractor:
        def forward_actor(self, x):return x[:,CONTEXT:OLD_DIM].reshape(-1,35,ACTION)[:,:,0]
    class Policy:mlp_extractor=Extractor();action_net=nn.Identity()
    loss,_=consistency_loss(Policy(),x,m)
    assert loss==0 and torch.isfinite(loss)
    c=consistency_contract();c['coefficient']=.02
    with pytest.raises(ValueError):validate_contract(c)


def test_matched_configs_and_game_budget():
    from advisor.learned_move_slot_study import matched_configs, game_slots, POLICIES, SEEDS, analyze
    from advisor.learned_ppo_contract_audit import VERSION
    configs={}
    for key in POLICIES[1:]:
        c={'envs':4,'cpu_percent':50,'memory_mib':12288,'device':'cpu','vector_backend':'subproc',
            'transition_budget_scope':'trained_rollouts_v1','checkpoint_evaluation_mode':'disabled_for_frozen_study_v1',
            'validation_selection_mode':'diagnostic_fixed_budget_v1','checkpoint_steps':16384,'ppo_update_audit':VERSION,
            'experiments':[{'name':key,'seed':int(key[2:]),'steps':65536,'initial_model_id':'a'*64,'fresh_optimizer':False}]}
        if key.startswith('B'):c['experiments'][0]['move_slot_consistency']=consistency_contract()
        configs[key]=c
    assert matched_configs(configs,'a'*64)['trained_transitions']==262144
    from copy import deepcopy
    bad=deepcopy(configs);bad[POLICIES[2]]['experiments'][0]['fresh_optimizer']=True
    with pytest.raises(ValueError):matched_configs(bad,'a'*64)
    cases=[{'scope':'train' if i<96 else 'heldout','index':i,'scenario_sha256':str(i)} for i in range(192)]
    slots=game_slots(cases)
    assert len(slots)==5760
    for policy in POLICIES:
        rows=[r for r in slots if r['policy']==policy]
        assert len(rows)==1152 and sum(r['scope']=='heldout' for r in rows)==576
        assert sum(r['seat']=='p1' for r in rows)==576
    small=[cases[0],cases[96]]
    rows=[{'slot':s,'record':{'winner':'self' if s['policy'].startswith('B') else 'opponent','truncated':False}} for s in game_slots(small)]
    assert analyze(rows,small,resamples=32)['conclusion']=='PROMISING_REQUIRES_INDEPENDENT_CONFIRMATION'
    with pytest.raises(ValueError):analyze(rows[:-1],small,resamples=32)


def test_trusted_offline_update_checkpoint_and_exact_continuation(tmp_path):
    """Trusted fixed-buffer unit replay only: zero new environment transitions."""
    import os, json, random, importlib.util
    from pathlib import Path
    from stable_baselines3.common.logger import configure
    parent=os.environ.get('POKEADVICE_SLOT_PARENT');capture=os.environ.get('POKEADVICE_SLOT_CAPTURE')
    if not parent or not capture:pytest.skip('trusted external parent/capture optional')
    from advisor.learned_move_slot_consistency import MoveSlotFoundationPPO
    from advisor.learned_combat_foundation import FoundationCombatEncoder
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock
    from scripts.train_showdown_autonomous import save_checkpoint
    spec=importlib.util.spec_from_file_location('temperature_test_helpers',Path(__file__).with_name('test_temperature_schedule.py'))
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    saved=torch.load(Path(capture)/'actual/training.pt',map_location='cpu',weights_only=False)
    m=MoveSlotFoundationPPO.load(parent,device='cpu',move_slot_consistency=consistency_contract())
    m.set_logger(configure(format_strings=[]));m._current_progress_remaining=.5
    helper.fill_buffer(m,saved,1.)
    before=tensor_digest(m.policy.state_dict());clock=optimizer_clock(m.policy)
    m.train()
    assert m.move_slot_trained==512 and optimizer_clock(m.policy)>clock
    assert tensor_digest(m.policy.state_dict())!=before and m.logger.name_to_value['train/slot_JS']>0
    catalog=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
    p=save_checkpoint(m,FoundationCombatEncoder(catalog),tmp_path/'saved',{})
    b=LearnedPolicy(p,catalog).model
    assert type(b) is MoveSlotFoundationPPO and b.move_slot_trained==512
    assert tensor_digest(m.policy.state_dict())==tensor_digest(b.policy.state_dict())
    assert optimizer_digest(m.policy)==optimizer_digest(b.policy)
    b.set_logger(configure(format_strings=[]));b._current_progress_remaining=.5
    helper.fill_buffer(m,saved,1.);helper.fill_buffer(b,saved,1.)
    state=helper.rng();m.train();helper.restore_rng(state);b.train()
    assert m.move_slot_trained==b.move_slot_trained==1024
    assert tensor_digest(m.policy.state_dict())==tensor_digest(b.policy.state_dict())
    assert optimizer_digest(m.policy)==optimizer_digest(b.policy)
    assert 'evaluate_actions' not in b.policy.__dict__
