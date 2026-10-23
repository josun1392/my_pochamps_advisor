"""Single <=512-transition native capture, then environment-free exact replay.

Separate explicit phases prevent a failed offline analysis from collecting a
second rollout. No evaluation function is imported or called by this owner.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from advisor.learned_exact_update import (ExactUpdateCapture, clone, load_capture, compare_trees,
    restore_training, restore_policy, rng_state, restore_rng, policy_state, group, loss_terms, TERMS, atomic_torch)
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only
from advisor.learned_policy import LearnedPolicy
from advisor.learned_parent_anchor import optimizer_clock, tensor_digest, optimizer_digest

STUDY=Path(r'C:\Users\jsp33\.codex\artifacts\foundation-parent-anchor-matched-v1-20261023')
PROBES=Path(r'C:\Users\jsp33\.codex\artifacts\foundation-ppo-learning-diagnosis-v1-20261023')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()

def prepare(out):
    from advisor.learned_anchor_study import verify_plan
    original,configs=verify_plan(STUDY/'plan.json')
    config=deepcopy(configs['T_96031']);binding=read(STUDY/'frozen_endpoint_models.json')['T_96031']
    out.mkdir(parents=True,exist_ok=False)
    plan={'schema_version':'foundation-exact-update-attribution-study-v1','frozen_utc':utc(),
        'baseline_HEAD':os.popen(f'git -C "{ROOT}" rev-parse HEAD').read().strip(),
        'learner':binding,'learner_selection':'first_treatment_final_fixed_budget_convention_not_performance_selection',
        'parent':{'path':original['parent_path'],'sha256':original['parent_sha256']},
        'seed':97011,'vector_seed':107011,'transitions':512,'independent_evaluation_games':0,
        'config':config,'original_plan':str(STUDY/'plan.json'),'original_plan_sha256':sha(STUDY/'plan.json'),
        'source_sha256':{n:sha(ROOT/n) for n in ('advisor/learned_exact_update.py','scripts/diagnose_foundation_exact_update.py')},
        'immutable_files':{**original['immutable_files'],binding['path']:binding['sha256'],
            str(Path(binding['path']).with_suffix('.json')):sha(Path(binding['path']).with_suffix('.json')),
            str(PROBES/'initial_features.npy'):sha(PROBES/'initial_features.npy'),
            str(PROBES/'initial_masks.npy'):sha(PROBES/'initial_masks.npy')},
        'resources':{'workers':4,'cpu_percent':50,'memory_mib':12288,'device':'cpu','cpu_threads':1,'seconds':900},
        'offline_analysis':'all_original_minibatches_gradients; first_and_last_optimized_minibatch_independent_single_Adam_omissions',
        'primary':'exact maintained train replay before any loss attribution',
        'safety':'one native launch marker; no evaluation; no automatic retry; no original writes; no promotion'}
    lp=LearnedPolicy(binding['path'],config['catalog'],expected_model_id=binding['sha256'])
    assert optimizer_clock(lp.model.policy)==34816
    assert lp.model.parent_policy_anchor['coefficient']==.01
    assert lp.model.n_steps==128 and lp.model.n_envs==4 and lp.model.batch_size==128 and lp.model.n_epochs==4
    assert lp.model.gamma==1 and lp.model.gae_lambda==.95 and lp.model.zero_avoiding_beta==.001
    plan['initial']={'parameter_digest':tensor_digest(lp.model.policy.state_dict()),
        'Adam_digest':optimizer_digest(lp.model.policy),'Adam_clock':34816,'encoder':lp.encoder.version,
        'catalog_fingerprint':lp.encoder.catalog_fingerprint,'timesteps':lp.model.num_timesteps,
        'coefficient':lp.model.parent_policy_anchor,'parent_proof':lp.model.parent_reference_proof()}
    atomic_json(out/'plan.json',plan)
    print(json.dumps({'phase':'prepared','out':str(out),'seed':97011,'transitions':512}),flush=True)

def verify(out):
    p=read(out/'plan.json')
    assert p['transitions']==512 and p['independent_evaluation_games']==0
    for name,digest in p['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('capture_source_changed:'+name)
    for name,digest in p['immutable_files'].items():
        if sha(name)!=digest:raise ValueError('capture_input_changed:'+name)
    return p

def model_for(p):
    lp=LearnedPolicy(p['learner']['path'],p['config']['catalog'],expected_model_id=p['learner']['sha256'])
    lp.model.prepare_parent_reference()
    from stable_baselines3.common.logger import configure
    lp.model.set_logger(configure(format_strings=[]))
    return lp

def capture(out):
    p=verify(out)
    if (out/'native_started.json').exists():raise ValueError('native_capture_already_started_no_automatic_recollection')
    from advisor.learned_parallel import LearningEnvFactory
    from stable_baselines3.common.vec_env import SubprocVecEnv
    from scripts.train_showdown_autonomous import BudgetCallback, save_checkpoint
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=24)
    limit=RuntimeLimit(out,900);network=enforce_local_network_only()
    atomic_json(out/'native_started.json',{'utc':utc(),'pid':os.getpid(),'plan_sha256':sha(out/'plan.json'),'cap':512})
    config=p['config'];e=config['experiments'][0]
    references={'previous':(config['previous_model'],config['previous_model_id']),
        'historical':(e['historical_model'],e['historical_model_id'])}
    references.update({k:(v,e['frozen_opponent_ids'][k]) for k,v in e['frozen_opponents'].items()})
    factories=[LearningEnvFactory(config['checkout'],config['catalog'],e['encoder_version'],i*100000,
        config['curriculum_version'],tuple(e['opponents']),references,True,
        max_decisions=config['max_decisions'],diagnostic_directory=str(out/'public_encoding_failures'),
        terminal_transport_version=config.get('terminal_transport_version'),
        training_subset_path=config['training_subset'],training_subset_sha256=config['training_subset_sha256'],
        foundation_profile=True) for i in range(4)]
    lp=model_for(p);model=lp.model;vector=None;started=time.perf_counter()
    public_stream=(out/'public_decisions.jsonl').open('x',encoding='utf-8')
    class Callback(BudgetCallback):
        def _on_rollout_start(self):
            super()._on_rollout_start()
            self.views=self.training_env.get_attr('current');self.count=0;self.infos=[]
        def _on_step(self):
            self.count+=len(self.locals['infos'])
            if self.count>512:raise ValueError('native_transition_cap_exceeded')
            for i,(view,info) in enumerate(zip(self.views,self.locals['infos'])):
                # Only own public view reaches the encoder. Labels are segregated in training.pt.
                public_stream.write(json.dumps({'t':self.count//4-1,'env':i,'public_before':view,
                    'action':int(self.locals['actions'][i]),'done':bool(self.locals['dones'][i]),
                    'native_outcome':info.get('native_outcome'),'TimeLimit.truncated':info.get('TimeLimit.truncated',False)},allow_nan=False)+'\n')
            public_stream.flush()
            self.infos.extend(clone(self.locals['infos']))
            self.views=self.training_env.get_attr('current')
            return super()._on_step()
    callback=Callback(limit)
    try:
        vector=SubprocVecEnv(factories,start_method='spawn')
        model.set_env(vector);model.seed=p['seed'];model.set_random_seed(p['seed']);vector.seed(p['vector_seed'])
        assert tensor_digest(model.policy.state_dict())==p['initial']['parameter_digest']
        assert optimizer_digest(model.policy)==p['initial']['Adam_digest']
        before=model.num_timesteps
        with ExactUpdateCapture(model,out/'actual') as recorder:
            model.learn(total_timesteps=512,reset_num_timesteps=False,callback=callback,log_interval=None)
        if callback.count!=512 or model.num_timesteps-before!=512:raise ValueError('incomplete_single_native_rollout')
        episodes=[r for rows in vector.env_method('drain_completed') for r in rows]
        path=save_checkpoint(model,lp.encoder,out/'diagnostic_post_update_checkpoint',
            {'scope':'diagnostic_only_not_candidate_or_promoted','curriculum_version':config['curriculum_version'],
             'source_model_sha256':p['learner']['sha256'],'exact_capture_plan_sha256':sha(out/'plan.json')})
        atomic_json(out/'episodes.json',{'ended_training_episodes':episodes,'independent_evaluation_games':0})
        atomic_json(out/'capture_summary.json',{'status':'captured','utc':utc(),'native_transitions':512,
            'PPO_update_calls':recorder.training_calls,'Adam_steps':recorder.steps,'Adam_before':34816,
            'Adam_after':optimizer_clock(model.policy),'post_update_checkpoint':path,'post_update_sha256':sha(path),
            'ended_training_battles':len(episodes),'outcomes':dict(Counter('truncated' if r['truncated'] else r['winner'] or 'draw' for r in episodes)),
            'native_rejections':sum(r['native_rejected_choices'] for r in episodes),
            'wall_seconds':time.perf_counter()-started,'resources':job.usage(),'network':network})
    except BaseException as error:
        atomic_json(out/'capture_failure.json',{'utc':utc(),'error':repr(error),'recorded_native_steps':getattr(callback,'count',0),
            'no_automatic_recollection':True})
        raise
    finally:
        public_stream.close()
        if vector is not None:vector.close()
        limit.finished.set()
    verify(out)
    print(json.dumps(read(out/'capture_summary.json')),flush=True)

def replay(out):
    p=verify(out);saved=load_capture(out/'actual/training.pt');lp=model_for(p);model=lp.model
    torch.use_deterministic_algorithms(True)
    restore_training(model,saved)
    with ExactUpdateCapture(model,out/'replay') as recorder:model.train()
    checks={}
    for f in sorted((out/'actual').glob('*.pt')):
        other=out/'replay'/f.name
        checks[f.name]=compare_trees(load_capture(f),load_capture(other)) if other.exists() else {'exact':False,'missing':True}
    assert {f.name for f in (out/'actual').glob('*.pt')}=={f.name for f in (out/'replay').glob('*.pt')}
    result={'exact':all(r['exact'] for r in checks.values()),'steps':recorder.steps,'files':checks,
        'new_environment_transitions':0,'upstream':'existing ParentAnchoredFoundationPPO.train -> maintained MaskablePPO2.7.1'}
    atomic_json(out/'replay_equivalence.json',result)
    if not result['exact']:raise ValueError('exact_upstream_update_replay_failed')
    print(json.dumps(result),flush=True)

def flat_grad(values,named):
    return torch.cat([(values.get(n) if values.get(n) is not None else torch.zeros_like(v)).flatten() for n,v in named])

def forward(policy,x,masks):
    probabilities=[];values=[];logits=[];raw=[]
    def hook(_module,_inputs,value):raw.append(value.detach().clone())
    handle=policy.action_net.register_forward_hook(hook)
    try:
        with torch.no_grad():
            for i in range(0,len(x),32):
                _,v,_=policy(torch.as_tensor(x[i:i+32]),action_masks=masks[i:i+32],deterministic=True)
                probabilities.append(policy.action_dist.distribution.probs.detach().clone())
                logits.append(policy.action_dist.distribution.logits.detach().clone());values.append(v.flatten().detach().clone())
    finally:handle.remove()
    return {'probabilities':torch.cat(probabilities),'value':torch.cat(values),'masked_logits':torch.cat(logits),'raw_logits':torch.cat(raw)}

def analyze(out):
    p=verify(out)
    if not read(out/'replay_equivalence.json')['exact']:raise ValueError('attribution_requires_exact_upstream_replay')
    saved=load_capture(out/'actual/training.pt');lp=model_for(p);model=lp.model
    x=np.load(PROBES/'initial_features.npy',allow_pickle=False);masks=np.load(PROBES/'initial_masks.npy',allow_pickle=False)
    rows=[];omissions=[];selected={0,len(list((out/'actual').glob('step_*.pt')))-1}
    steps=sorted((out/'actual').glob('step_*.pt'))
    for file in steps:
        s=load_capture(file);restore_policy(model.policy,s['before']);model.policy.set_training_mode(True)
        for k,v in saved['model_attributes'].items():setattr(model,k,clone(v))
        terms,combine,outputs=loss_terms(model,saved,s)
        rawcheck=compare_trees({'value':outputs['value'],'logp':outputs['logp'],
            'probabilities':outputs['probabilities'],'masked_logits':outputs['masked_logits']},
            {k:v for k,v in s['raw_evaluate'].items() if k!='entropy'})
        assert rawcheck['exact'],'offline_raw_forward_mismatch'
        assert torch.equal(combine().detach(),s['upstream']['loss']),'offline_loss_not_exact'
        named=list(model.policy.named_parameters());params=[v for _,v in named]
        gradients={}
        for term,loss in terms.items():
            grads=torch.autograd.grad(loss,params,retain_graph=True,allow_unused=True)
            gradients[term]={n:g.detach().clone() for (n,_),g in zip(named,grads) if g is not None}
        allg=torch.autograd.grad(combine(),params,retain_graph=False,allow_unused=True)
        allg={n:g.detach().clone() for (n,_),g in zip(named,allg) if g is not None}
        check=compare_trees(allg,s['gradient_before_clip'])
        if not check['exact']:raise ValueError('offline_composite_gradient_not_exact:'+str(check))
        vectors={k:flat_grad(v,named).double() for k,v in gradients.items()}
        norms={k:float(v.norm()) for k,v in vectors.items()}
        cosines={a+':'+b:(float(torch.dot(vectors[a],vectors[b])/(norms[a]*norms[b])) if norms[a]*norms[b]>0 else None)
                 for i,a in enumerate(TERMS) for b in TERMS[i+1:]}
        group_norms={term:{g:float(sum(float(t.double().square().sum()) for n,t in grads.items() if group(n)==g)**.5)
            for g in ('actor_only','critic_only','shared','prediction')} for term,grads in gradients.items()}
        total=flat_grad(allg,named).double();clipped=flat_grad(s['gradient_after_clip'],named).double()
        summed=sum(vectors.values())
        row={'minibatch':s['index'],'epoch':s['upstream']['epoch'],'losses':{k:float(v.detach()) for k,v in terms.items()},
            'composite_gradient_exact':check,'raw_forward_exact':rawcheck,'gradient_norms':norms,'group_norms':group_norms,
            'cosines':cosines,'gradient_sum_max_abs_roundoff':float((summed-total).abs().max()),
            'total_preclip_norm':float(total.norm()),'postclip_norm':float(clipped.norm()),
            'global_clip_scale_observed':float(clipped.norm()/total.norm())}
        rows.append(row)
        if s['index'] in selected:
            atomic_torch(out/f'component_gradients_{s["index"]:02d}.pt',gradients)
            before_probe=forward(model.policy,x,masks)
            actual_after=s['after']
            after_states={}
            for omit in (None,*TERMS):
                restore_policy(model.policy,s['before']);model.policy.set_training_mode(True)
                ts,comb,_=loss_terms(model,saved,s)
                model.policy.optimizer.zero_grad(set_to_none=True);comb(omit).backward()
                norm=torch.nn.utils.clip_grad_norm_(model.policy.parameters(),model.max_grad_norm)
                model.policy.optimizer.step()
                after=policy_state(model.policy);after_states[omit or 'full']=clone(after)
                if omit is None:
                    proof=compare_trees(after,actual_after)
                    if not proof['exact']:raise ValueError('single_full_Adam_step_not_exact:'+str(proof))
                probe=forward(model.policy,x,masks)
                d=(probe['probabilities']-before_probe['probabilities'])
                grouped={g:sum(float((after['parameters'][n]-s['before']['parameters'][n]).double().square().sum())
                    for n,_ in named if group(n)==g)**.5 for g in ('actor_only','critic_only','shared','prediction')}
                ref=forward_after_full if omit is not None else probe
                omissions.append({'minibatch':s['index'],'omit':omit,'preclip_norm':float(norm),'parameter_update_L2_groups':grouped,
                    'switch_probability_delta_mean':float(d[:,:6].sum(1).mean()),
                    'probability_delta_L1_mean':float(d.abs().sum(1).mean()),
                    'argmax_changed_from_before':int((probe['probabilities'].argmax(1)!=before_probe['probabilities'].argmax(1)).sum()),
                    'raw_logit_delta_RMS':float((probe['raw_logits']-before_probe['raw_logits']).square().mean().sqrt()),
                    'value_delta_RMS':float((probe['value']-before_probe['value']).square().mean().sqrt()),
                    'probability_difference_from_full_L1_mean':float((probe['probabilities']-ref['probabilities']).abs().sum(1).mean()),
                    'switch_probability_difference_from_full':float((probe['probabilities'][:,:6]-ref['probabilities'][:,:6]).sum(1).mean()),
                    'argmax_difference_from_full':int((probe['probabilities'].argmax(1)!=ref['probabilities'].argmax(1)).sum())})
                if omit is None:forward_after_full=clone(probe)
                atomic_torch(out/f'probe_{s["index"]:02d}_{omit or "full"}.pt',{'before':before_probe,'after':probe})
            atomic_torch(out/f'offline_single_step_states_{s["index"]:02d}.pt',after_states)
        atomic_json(out/'attribution.json',{'status':'analyzing','minibatches':rows,'single_step_omissions':omissions})
    restore_policy(model.policy,saved['before']);before=forward(model.policy,x,masks)
    restore_policy(model.policy,load_capture(out/'actual/after.pt'));after=forward(model.policy,x,masks)
    atomic_torch(out/'whole_rollout_probe.pt',{'before':before,'after':after})
    result={'status':'complete','minibatches':rows,'single_step_omissions':omissions,
        'independent_evaluation_games':0,'offline_new_environment_transitions':0,
        'whole_rollout_probe':{'states':len(x),'before_switch_argmax':int((before['probabilities'].argmax(1)<6).sum()),
            'after_switch_argmax':int((after['probabilities'].argmax(1)<6).sum()),
            'switch_probability_delta_mean':float((after['probabilities'][:,:6]-before['probabilities'][:,:6]).sum(1).mean()),
            'argmax_changed':int((before['probabilities'].argmax(1)!=after['probabilities'].argmax(1)).sum())},
        'scope':'conditional_local_single_update_not_additive_loss_shares_or_long_term_strength'}
    atomic_json(out/'attribution.json',result);verify(out)
    print(json.dumps({'phase':'analyzed','minibatches':len(rows),'single_step_contrasts':len(omissions),
                      'probe':result['whole_rollout_probe']}),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=('prepare','capture','replay','analyze'));ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    if args.phase=='prepare':prepare(args.output)
    else:{'capture':capture,'replay':replay,'analyze':analyze}[args.phase](args.output)

if __name__=='__main__':main()
