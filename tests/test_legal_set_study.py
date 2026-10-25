"""Frozen matched settings and observational audit; no native collection here."""
from copy import deepcopy
import json
import os
from pathlib import Path
import numpy as np
import pytest
import torch
from stable_baselines3.common.logger import configure
from advisor.learned_legal_set_study import matched_configs,game_slots,analyze,SEEDS,POLICIES
from advisor.learned_legal_set_context import legal_set_context_contract,legal_set_training_contract,extend_foundation_legal_set_context
from advisor.learned_ppo_contract_audit import AuditedSignalRecorder,VERSION
from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock


def configs():
    base={'envs':4,'cpu_percent':50,'memory_mib':12288,'device':'cpu','vector_backend':'subproc',
      'transition_budget_scope':'trained_rollouts_v1','checkpoint_evaluation_mode':'disabled_for_frozen_study_v1',
      'validation_selection_mode':'diagnostic_fixed_budget_v1','checkpoint_steps':16384,'ppo_update_audit':VERSION,
      'experiments':[{'steps':65536,'initial_model_id':'a'*64,'fresh_optimizer':False,'opponents':['same']}]}
    result={}
    for key in POLICIES[1:]:
        c=deepcopy(base);e=c['experiments'][0];e.update(name=key,seed=int(key[2:]))
        if key.startswith('B'):e.update(actor_set_context=legal_set_context_contract(),legal_set_training=legal_set_training_contract())
        result[key]=c
    return result


def test_only_residual_architecture_changes_and_exact_budget():
    assert matched_configs(configs(),'a'*64)['trained_transitions']==262144
    for field,value in [('gamma',.99),('fresh_optimizer',True),('steps',32768),('masked_temperature',{}),('opponents',['other'])]:
        c=configs();c[f'B_{SEEDS[0]}']['experiments'][0][field]=value
        # Even an empty unrecognized intervention key cannot equal the control.
        with pytest.raises(ValueError):matched_configs(c,'a'*64)
    c=configs();c[f'B_{SEEDS[0]}']['experiments'][0].pop('legal_set_training')
    with pytest.raises(ValueError):matched_configs(c,'a'*64)


def cases():return [{'scope':'train' if i<96 else 'heldout','index':i,'scenario_sha256':str(i)} for i in range(192)]


def test_five_models_5760_argmax_both_seats_and_case_cluster_primary():
    slots=game_slots(cases());assert len(slots)==5760 and len({tuple(s.values()) for s in slots})==5760
    for model in POLICIES:
        own=[s for s in slots if s['policy']==model]
        assert len(own)==1152 and sum(s['scope']=='heldout' for s in own)==576 and sum(s['seat']=='p1' for s in own)==576
    small=[cases()[0],cases()[96]]
    rows=[{'slot':s,'record':{'winner':'self' if s['policy'].startswith('B') else 'opponent','truncated':False}} for s in game_slots(small)]
    r=analyze(rows,small,resamples=64)
    assert r['conclusion']=='CANDIDATE_FOR_LARGER_INDEPENDENT_VALIDATION'
    for wrong in (rows[:-1],rows+rows[:1]):
        with pytest.raises(ValueError):analyze(wrong,small,resamples=64)


@pytest.mark.parametrize('treatment',[False,True])
def test_audit_does_not_change_actual_updates_and_B_restart(tmp_path,treatment):
    parent=os.environ.get('POKEADVICE_LEGAL_SET_PARENT');capture=os.environ.get('POKEADVICE_LEGAL_SET_CAPTURE_DIR')
    if not parent or not capture:pytest.skip('trusted existing native capture required; never collect fixtures')
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_combat_foundation import FoundationCombatEncoder
    from advisor.learned_legal_set_study import checkpoint_integrity
    from scripts.train_showdown_autonomous import save_checkpoint
    from tests.test_temperature_schedule import rng,restore_rng
    cat=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
    source=LearnedPolicy(parent,cat).model
    before=(tensor_digest(source.policy.state_dict()),optimizer_digest(source.policy))
    a=extend_foundation_legal_set_context(source) if treatment else deepcopy(source)
    b=deepcopy(a);saved=torch.load(Path(capture)/'actual/training.pt',map_location='cpu',weights_only=False)
    for model in (a,b):
        model.set_logger(configure(format_strings=[]));model._current_progress_remaining=.5
        buffer=model.rollout_buffer
        for key,value in saved['buffer'].items():setattr(buffer,key,value.copy() if isinstance(value,np.ndarray) else value)
        xx=buffer.observations.reshape(-1,28822);mm=buffer.action_masks.reshape(-1,35);aa=buffer.actions.reshape(-1).astype(int)
        vv=[];lp=[]
        with torch.no_grad():
            for start in range(0,len(xx),128):
                v,l,_=model.policy.evaluate_actions(torch.as_tensor(xx[start:start+128]),torch.as_tensor(aa[start:start+128]),action_masks=mm[start:start+128])
                vv.append(v.flatten().numpy());lp.append(l.numpy())
        buffer.values=np.concatenate(vv).reshape(128,4);buffer.log_probs=np.concatenate(lp).reshape(128,4)
        # Explicit bootstrap fixture, not a claim of replaying the old episode.
        model._last_obs=xx[:4].copy();model._last_episode_starts=np.zeros(4,bool)
        with torch.no_grad():last=model.policy.predict_values(torch.as_tensor(model._last_obs))
        buffer.compute_returns_and_advantage(last,model._last_episode_starts)
        model._auxiliary_rows=deepcopy(saved['loss_only_auxiliary_labels']);model._auxiliary_observations=xx.copy()
        model._aux_groups=model._aux_weights=None
    audit=AuditedSignalRecorder(tmp_path/'audit',None)
    audit.infos=[[{'done':False} for _ in range(4)] for _ in range(128)]
    audit.end(b,optimizer_clock(b.policy))
    state=rng();a.train();restore_rng(state);b.train()
    audit.settled(optimizer_clock(b.policy),b)
    assert tensor_digest(a.policy.state_dict())==tensor_digest(b.policy.state_dict())
    assert optimizer_digest(a.policy)==optimizer_digest(b.policy)
    assert before==(tensor_digest(source.policy.state_dict()),optimizer_digest(source.policy))
    receipt=json.loads(next((tmp_path/'audit').glob('*.audit.json')).read_text())
    assert receipt['preupdate_logp_error']==0 and receipt['GAE_error']<2e-6
    for batch in receipt['minibatches']:
        ratio=np.exp(np.asarray(batch['new_logp'])-np.asarray(batch['old_logp']))
        assert len(ratio)==len(batch['actions']) and np.isfinite(ratio).all()
        assert abs(float(ratio.mean())-batch['ratio_mean'])<1e-6
    assert receipt['Adam_after']>receipt['Adam_before']
    if treatment:
        assert receipt['residual_parameter_delta_L2']>0 and receipt['residual_clipped_gradient_max']>0
        path=save_checkpoint(b,FoundationCombatEncoder(cat),tmp_path/'saved',{})
        restored=LearnedPolicy(path,cat).model
        assert optimizer_digest(restored.policy)==optimizer_digest(b.policy)
        checkpoint_integrity(path,__import__('hashlib').sha256(Path(path).read_bytes()).hexdigest(),optimizer_clock(b.policy))
    assert not audit.active and 'evaluate_actions' not in b.policy.__dict__ and 'get' not in b.rollout_buffer.__dict__
