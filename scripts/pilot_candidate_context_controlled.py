"""One bounded, residual-only set/local TRAIN study. No automatic restart."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
import os
import time
import traceback

import numpy as np
import torch

from advisor.experimental_context_training import (
    VERSION, SEEDS, STEPS, ADAM_CAP, contract, initialize, validate_model,
    frozen_digest, save, ResidualActor, TrainCases, paired_development,
)
from advisor.learned_execution_alignment import digest, content_hash, durable_json
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_policy import LearnedPolicy
from advisor.learned_fixed_micro import MATCHUP_VERSION, seed4
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only

BASELINE = '80a98384ed30ca986c0e5195d37c5d2fc4d42a97'
PARENT_SHA = '9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf'
ARTIFACTS = Path.home()/'.codex/artifacts'
PARENT = ARTIFACTS/'pokeadvice-combat-foundation-v1-long-training/seed95017-stage1/experiment_00/checkpoint_0028_ppo_1048576_4e3232dd/model.zip'
FIXED16K = ARTIFACTS/'foundation-frozen-micro-ppo-curve-16k-v1-20261027/checkpoint_16384/model.zip'
CHECKOUT = ARTIFACTS/'foundation-move-slot-equivariance-matched-v1-20261029/native_runtime_942cda71'
RUNTIME = ARTIFACTS/'foundation-move-slot-equivariance-matched-v1-20261029/evaluation_revision_04/native_runtime_manifest.json'
OWNED = ['advisor/experimental_context_training.py','scripts/pilot_candidate_context_controlled.py',
         'tests/test_experimental_context_training.py','docs/experimental_context_controlled_train.md']


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def exclusion_only():
    """Sealed team/seed identifiers only, never outcomes or actor observations."""
    from advisor.learned_diverse_micro import team_keys
    keys, seeds, ids, bindings = set(), set(), set(), {}
    for study in ('foundation-prospective-sealed-policy-evaluation-source-v1-20261031',
                  'foundation-16k-independent-confirmation-v1-20261102'):
        p = ARTIFACTS/study/'source_manifest.json';s=read(p)
        asset=p.parent/s['team_asset']['path']
        if digest(asset)!=s['team_asset']['sha256']:raise ValueError('sealed_exclusion_identity_changed')
        bindings[str(p)],bindings[str(asset)]=digest(p),digest(asset)
        for t in read(asset)['teams']:keys.update(team_keys(t).values())
        for c in s['cases']:
            ids.add(c['case_id']);seeds.update(tuple(v) for v in c['native_seeds'].values())
    return keys,seeds,ids,bindings


def prepare(root):
    from advisor.learned_full_roster import load_bank, study_identity
    from advisor.learned_diverse_micro import team_keys
    from advisor.showdown_bridge import ShowdownBridge
    if root.exists():raise ValueError('existing_context_pilot_inspect_do_not_overwrite')
    root.mkdir(parents=True)
    torch.set_num_threads(1)
    excluded,seeds,ids,bindings=exclusion_only()
    bank=load_bank()['teams']['train'];chosen=[];used=set(excluded)
    order=sorted(range(len(bank)),key=lambda i:content_hash([VERSION,'teams',i]))
    for i in order:
        k=team_keys(bank[i])
        if used.intersection(k.values()):continue
        chosen.append(i);used.update(k.values())
        if len(chosen)==32:break
    if len(chosen)!=32:raise ValueError('TRAIN_source_coverage_blocked')
    templates={'train':[],'development':[]}
    for scope,indices in [('train',chosen[:16]),('development',chosen[16:])]:
        for pair in range(8):
            ii=indices[pair*2:pair*2+2]
            preview=[(np.random.default_rng(seed4(f'{VERSION}:{scope}:{pair}:{side}')).permutation(6)[:3]+1).tolist() for side in range(2)]
            for direction in (0,1):
                own,foe=(direction,1-direction)
                scenario={'scenario_id':f'{VERSION}:{scope}:{pair}:{direction}',
                    'teams':{'self':deepcopy(bank[ii[own]]),'opponent':deepcopy(bank[ii[foe]])},
                    'preview':{'self':preview[own],'opponent':preview[foe]},'seed':[1,2,3,4],
                    'history':[],'assumptions':['V8 TRAIN-only native-valid teams; fixed ordered bring-three; experimental development, not sealed evidence.']}
                templates[scope].append({'pair':pair,'direction':direction,'bank_indices':[ii[own],ii[foe]],
                    'team_keys':[team_keys(bank[j]) for j in ii],'scenario':scenario})
    cases=[]
    for t in templates['development']:
        for rep in range(4):
            i=len(cases);s=deepcopy(t['scenario']);s.update(scenario_id=f'{VERSION}:DEV:{i}',seed=seed4(f'{VERSION}:DEV:{i}'))
            if tuple(s['seed']) in seeds or s['scenario_id'] in ids:raise ValueError('development_sealed_overlap')
            cases.append({'index':i,'pair':t['pair'],'direction':t['direction'],'replicate':rep,
                'rival':'league_s0','scenario':s,'scenario_sha256':content_hash(s)})
    catalog=str(ROOT/'models/showdown_mc_domain_v1/catalog.json')
    parent=LearnedPolicy(PARENT,catalog,expected_model_id=PARENT_SHA)
    ShowdownBridge(CHECKOUT)._verify_checkout()  # Git pin only; no native battle.
    bindings.update({str(PARENT):digest(PARENT),str(PARENT.with_suffix('.json')):digest(PARENT.with_suffix('.json')),
                     str(FIXED16K):digest(FIXED16K),str(FIXED16K.with_suffix('.json')):digest(FIXED16K.with_suffix('.json')),
                     str(RUNTIME):digest(RUNTIME)})
    capture=ARTIFACTS/'foundation-exact-update-capture-v1-20261023/public_decisions.jsonl'
    probes=[json.loads(line)['public_before'] for line in capture.read_text(encoding='utf-8').splitlines()[:64]]
    bindings[str(capture)]=digest(capture);durable_json(root/'TRAIN_probes.json',probes)
    p=parent.model
    if p.lr_schedule(1.)!=p.lr_schedule(.5):raise ValueError('nonconstant_parent_LR_requires_global_schedule_contract')
    plan={'schema_version':VERSION,'baseline_HEAD':BASELINE,'frozen_KST':datetime.now().astimezone().isoformat(),
        'seeds':list(SEEDS),'arm_order':['A_s1','B_s1','A_s2','B_s2'],
        'modes':{'A':'set','B':'local'},'per_arm_transitions':STEPS,'total_transition_cap':65536,
        'per_arm_Adam_cap':ADAM_CAP,'parent':{'path':str(PARENT),'sha256':PARENT_SHA,
          'parameters':tensor_digest(p.policy.state_dict()),'Adam':optimizer_digest(p.policy),'Adam_step':optimizer_clock(p.policy)},
        'PPO':{k:getattr(p,k) for k in ('n_steps','batch_size','n_epochs','gamma','gae_lambda','ent_coef','vf_coef','max_grad_norm','target_kl','zero_avoiding_beta')},
        'learning_rate':p.lr_schedule(1.),'catalog':catalog,'checkout':str(CHECKOUT),'bank':study_identity(),
        'runtime_manifest':str(RUNTIME),
        'training_templates':templates['train'],'development_templates':templates['development'],
        'case_identity':content_hash(templates),'development_cases':cases,'development_start_cap':512,
        'development_method':'T1_argmax_both_actual_seats_both_roster_owners_frozen_Foundation_argmax',
        'excluded_native_seeds':[list(s) for s in sorted(seeds)],'excluded_case_ids':sorted(ids),
        'excluded_team_key_count':len(excluded),'input_SHA256':bindings,
        'TRAIN_probes_SHA256':digest(root/'TRAIN_probes.json'),'train_start_cap_per_arm':4096,
        'workers':4,'CPU_percent':50,'memory_mib':12288,'wall_cap_seconds':7200,'device':'cpu',
        'residual_contracts':{m:contract(m) for m in ('set','local')},
        'source_SHA256':{name:digest(ROOT/name) for name in OWNED+[
          'advisor/learned_legal_set_context.py','advisor/learned_fixed_micro.py','advisor/learned_selfplay_pilot.py',
          'advisor/learned_gym.py','advisor/learned_policy.py','advisor/learned_combat_foundation.py',
          'advisor/learned_ppo_contract_audit.py','scripts/train_showdown_autonomous.py','scripts/evaluate_showdown_policy.py']},
        'statistics':{'bootstrap_seed':116055,'draws':20000,'cluster':'TRAIN_development_complete_team_pair_keep_directions_seats_RNG_seeds_paired'},
        'analysis_endpoint':'final16384_only_no_checkpoint_selection','automatic_restarts':0,
        'runtime_adapter':{'schema_version':MATCHUP_VERSION,'catalog':catalog,'checkout':str(CHECKOUT),
          'opponents':['league_s0'],'micro_budget':{'transitions':16384,'Adam':512,'starts':4096,'targets':[4096,8192,12288,16384]}}}
    durable_json(root/'plan.json',plan)
    durable_json(root/'preparation.json',{'plan_SHA256':digest(root/'plan.json'),'sealed_exclusion_only':True,
        'TRAIN_pairs':8,'TRAIN_domain_development_pairs':8,'training_complete_teams':16,
        'development_complete_teams':16,'development_games':512,'sealed_team_case_seed_overlap':0,
        'PPO':0,'native_starts':0})
    print(json.dumps({'prepared':str(root),'plan_SHA256':digest(root/'plan.json')}))


def verify(root):
    p=read(root/'plan.json')
    if (p['schema_version']!=VERSION or p['seeds']!=list(SEEDS) or p['per_arm_transitions']!=STEPS
            or p['total_transition_cap']!=65536 or p['development_start_cap']!=512
            or p['workers']!=4 or p['CPU_percent']!=50 or p['memory_mib']!=12288 or p['device']!='cpu'
            or p['wall_cap_seconds']!=7200 or p['automatic_restarts']!=0):raise ValueError('context_pilot_plan_contract')
    for name,wanted in p['source_SHA256'].items():
        if digest(ROOT/name)!=wanted:raise ValueError('context_source_changed:'+name)
    for name,wanted in p['input_SHA256'].items():
        if digest(name)!=wanted:raise ValueError('context_preserved_input_changed:'+name)
    runtime=read(p['runtime_manifest'])
    if Path(runtime['root']).resolve()!=Path(p['checkout']).resolve():raise ValueError('context_native_runtime_binding')
    for name,wanted in runtime['files'].items():
        if digest(Path(runtime['root'])/name)!=wanted:raise ValueError('context_native_runtime_changed:'+name)
    if digest(root/'TRAIN_probes.json')!=p['TRAIN_probes_SHA256']:raise ValueError('context_probe_binding')
    return p


def probes(actor, parent, views):
    from advisor.learned_tactical_diagnostics import action_class
    differences=[];families=Counter();initial=Counter();ent=[];kls=[];deltas=[]
    for v in views:
        a=parent.infer(v);b=actor.infer(v)
        x=np.array(a['action_probabilities']);y=np.array(b['action_probabilities']);mask=np.array(v['action_mask'],bool)
        kl=float(np.sum(x[mask]*np.log(np.maximum(x[mask],1e-30)/np.maximum(y[mask],1e-30))))
        entropy=float(-np.sum(y[mask]*np.log(np.maximum(y[mask],1e-30))))
        features=torch.tensor(parent.encoder.encode(v))[None]
        with torch.no_grad():
            before=parent.model.policy.mlp_extractor.forward_actor(features)
            after=actor.model.policy.mlp_extractor.forward_actor(features)
        delta=float((before-after).abs()[0,torch.tensor(mask)].max())
        if a['discounted_return_estimate']!=b['discounted_return_estimate']:raise ValueError('frozen_critic_probe_changed')
        differences.append({'episode_id':v['episode_id'],'revision':v['revision'],'initial_action':a['action_index'],
            'final_action':b['action_index'],'max_legal_logit_delta':delta,'KL_parent_to_residual':kl,
            'max_probability_change':float(abs(x-y).max()),'entropy':entropy,'value':b['discounted_return_estimate']})
        families[action_class(v,b['action_index'])]+=1;initial[action_class(v,a['action_index'])]+=1
        ent.append(entropy);kls.append(kl);deltas.append(delta)
    return {'views':len(views),'argmax_changes':sum(r['initial_action']!=r['final_action'] for r in differences),
            'argmax_change_fraction':np.mean([r['initial_action']!=r['final_action'] for r in differences]).item(),
            'initial_argmax_families':dict(initial),'final_argmax_families':dict(families),
            'mean_entropy':float(np.mean(ent)),'mean_KL':float(np.mean(kls)),
            'max_legal_logit_delta':max(deltas),'rows':differences}


def train_arm(plan,root,label,seed,parent,runtime):
    from advisor.learned_fixed_micro import training_vector
    from advisor.learned_selfplay_pilot import StartBudget
    from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
    from scripts.train_showdown_autonomous import BudgetCallback,require_finite_ppo
    folder=root/label;folder.mkdir();m=initialize(parent.model,plan['modes'][label[0]])
    fixed=plan['parent']['parameters'];start=m.num_timesteps;updates=0;segments=[];last_path=None
    budget=StartBudget(folder/'TRAIN_starts',4096,root/'STOP')
    (folder/'Adam_intents').mkdir()
    def reserve(optimizer,args,kwargs):
        nonlocal updates
        validate_model(m,plan['modes'][label[0]],fixed)
        if updates>=ADAM_CAP:raise RuntimeError('residual_Adam_cap')
        durable_json(folder/'Adam_intents'/f'{updates:04d}.json',{'index':updates,'before':optimizer_clock(m.policy)})
        updates+=1
    hook=m.policy.optimizer.register_step_pre_hook(reserve)
    began=time.perf_counter()
    try:
        for segment in range(16):
            if runtime.stopping():raise RuntimeError('context_STOP_or_deadline')
            if digest(root/'plan.json')!=read(root/'started.json')['plan_SHA256']:raise ValueError('context_plan_changed')
            sr=folder/'segments'/f'{segment:02d}';sr.mkdir(parents=True)
            vector,_=training_vector(plan['runtime_adapter'],sr,parent,
                case_factory=lambda worker:TrainCases(plan,seed,segment,worker),start_budget=budget)
            recorder=AuditedSignalRecorder(folder/'rollouts',parent.encoder)
            callback=BudgetCallback(runtime,collect_diagnostics=True,signal_recorder=recorder)
            m.set_env(vector,force_reset=True)
            if segment==0:m.set_random_seed(seed)
            before=m.num_timesteps
            try:
                m.learn(total_timesteps=1024,reset_num_timesteps=False,callback=callback)
                require_finite_ppo(m,rollout=True)
                if m.num_timesteps-before!=1024 or m.num_timesteps-start>STEPS:raise ValueError('context_transition_budget')
                records={'segment':segment,'new_collected':m.num_timesteps-start,'new_Adam':updates,
                    'slots':[(segment*4+w)%16 for w in range(4)],'transitions_per_slot':256,
                    'metrics':{k:float(v) if np.isfinite(v) else None for k,v in m.logger.name_to_value.items() if isinstance(v,(int,float,np.number))},
                    'completed':[e for batch in vector.env_method('drain_completed') for e in batch],
                    'tactical_counts':vector.env_method('drain_tactical_counts'),
                    'public_counts':vector.env_method('drain_public_behavior_counts'),'callback':callback.measurements}
            finally:recorder.close();vector.close()
            validate_model(m,plan['modes'][label[0]],fixed)
            if optimizer_digest(parent.model.policy)!=plan['parent']['Adam']:raise ValueError('original_Adam_mutated')
            audits=[read(p) for p in (folder/'rollouts').glob('*.audit.json')]
            if len(audits)!=(segment+1)*2:raise ValueError('context_rollout_audit_missing')
            current=sorted([a for a in audits if before<int(a['model_timesteps_end'])<=m.num_timesteps],
                           key=lambda a:a['model_timesteps_end'])
            if ([a['model_timesteps_end'] for a in current]!=[before+512,before+1024]
                    or any(a['transitions']!=512 for a in current)):
                raise ValueError('context_worker_transition_quota')
            identities=list((sr/'native_training').glob('worker_*/identity_*.json'))
            if len(identities)<8:raise ValueError('context_native_identities_missing')
            for file in identities:
                identity=read(file);worker=identity['worker'];episode=identity['episode_identity']
                template=plan['training_templates'][(segment*4+worker)%16]['scenario']
                if (episode['team_sha256']!={s:content_hash(template['teams'][s]) for s in ('self','opponent')}
                        or episode['opponent_model_id']!=PARENT_SHA or identity['opponent_mode']!='argmax'):
                    raise ValueError('context_actual_team_or_opponent_exposure_changed')
            records['verified_native_roster_identities']=len(identities)
            records['verified_rollout_transitions']=sum(a['transitions'] for a in current)
            segments.append(records)
            if (segment+1)%4==0:
                last_path=save(m,parent.encoder,folder/f'checkpoint_{m.num_timesteps-start}',
                    {'plan_SHA256':digest(root/'plan.json'),'new_collected':m.num_timesteps-start,
                     'new_trained':len(audits)*512,'new_Adam':updates,'seed':seed,'mode':plan['modes'][label[0]]})
            atomic_json(folder/'training_progress.json',{'segments':segments,'latest':last_path,
                'new_collected':m.num_timesteps-start,'new_trained':len(audits)*512,'new_Adam':updates,'starts':budget.count})
            atomic_json(root/'progress.json',{'phase':'training','arm':label,'arm_transitions':m.num_timesteps-start,
                'completed_arms':len(list(root.glob('*_s*/endpoint.json'))),'seconds':time.perf_counter()-began,
                'transitions_per_second':(m.num_timesteps-start)/(time.perf_counter()-began),'unix':time.time()})
        actor=ResidualActor(last_path,plan['catalog'])
        if tensor_digest(actor.model.policy.state_dict())!=tensor_digest(m.policy.state_dict()) or optimizer_digest(actor.model.policy)!=optimizer_digest(m.policy):
            raise ValueError('context_checkpoint_optimizer_restore')
        durable_json(folder/'endpoint.json',{'path':last_path,'sha256':actor.model_id,'new_transitions':STEPS,
            'new_Adam':updates,'frozen_SHA256':frozen_digest(m.policy),'optimizer_SHA256':optimizer_digest(m.policy),
            'residual_L2':sum(float(p.detach().square().sum()) for p in m.policy.mlp_extractor.legal_set_residual.parameters())**.5,
            'TRAIN_starts':budget.count,'seconds':time.perf_counter()-began,'train_seed':seed})
        return actor
    except BaseException:
        # Preserve the last optimizer boundary without claiming partial rollout
        # observations were trained or using it as the planned final endpoint.
        validate_model(m,plan['modes'][label[0]],fixed)
        save(m,parent.encoder,folder/'partial_checkpoint',{'new_collected':m.num_timesteps-start,
            'new_trained':512*len(list((folder/'rollouts').glob('*.audit.json'))),'new_Adam_intents':updates,'status':'PARTIAL'})
        raise
    finally:hook.remove()


def evaluate_development(plan,root,actors,parent,runtime):
    from scripts.evaluate_showdown_policy import evaluate
    from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases,persist_evaluation_batch
    from advisor.learned_selfplay_pilot import StartBudget
    from advisor.learned_fixed_micro import EpisodeRival
    from advisor.learned_difficulty_calibration import PublicRetryAudit
    directory=root/'development';directory.mkdir()
    cases={c['index']:c for c in plan['development_cases']}
    budget=StartBudget(root/'DEV_starts',512,root/'STOP');bindings={k:{'sha256':v.model_id} for k,v in actors.items()}
    begin=time.perf_counter()
    # Guard all optimizers in evaluation; no model selection or fitting here.
    def no_update(*args,**kwargs):raise RuntimeError('development_optimizer_forbidden')
    handles=[a.model.policy.optimizer.register_step_pre_hook(no_update) for a in [parent,*actors.values()]]
    try:
        for name,actor in actors.items():
            for seat in ('p1','p2'):
                for offset in range(0,64,16):
                    provider=FrozenEvalCases(cases,budget,name,'league_s0',seat,digest(root/'plan.json'))
                    rival=EpisodeRival('league_s0',parent);rival.reset(0);monitors={}
                    def observer(e):
                        side='self' if seat=='p1' else 'opponent';ep=e['before'][side]['episode_id']
                        monitors.setdefault(ep,PublicRetryAudit(ep)).observe(e)
                    def progress(rows):
                        persist_evaluation_batch(directory,rows,bindings,cases,name,'league_s0',seat,digest(root/'plan.json'))
                        atomic_json(root/'progress.json',{'phase':'TRAIN_domain_development','valid':len(list(directory.glob('*.receipt.json'))),
                            'starts':budget.count,'target':512,'seconds':time.perf_counter()-begin,'unix':time.time()})
                    evaluate(plan['checkout'],plan['catalog'],{name:actor},cases=16,offset=offset,
                        curriculum_version='showdown-learning-curriculum-v8',rivals={'league_s0':rival},candidate_seat=seat,
                        case_provider=provider,stopping=runtime.stopping,tactical_diagnostics=True,
                        transition_observer=observer,per_game_progress=True,progress=progress)
        rows=[read(p) for p in directory.glob('*.receipt.json')]
        if budget.count!=512 or len(rows)!=512:raise ValueError('development_count_or_duplicate')
        result=paired_development(rows,plan['development_cases'])
        durable_json(root/'development_analysis.json',result)
        return result
    finally:
        for h in handles:h.remove()


def run(root):
    if (root/'started.json').exists() or (root/'completion.json').exists():raise ValueError('already_started_no_duplicate')
    plan=verify(root)
    gate=read(root/'offline_gate.json')
    if gate['status']!='PASS' or gate['plan_SHA256']!=digest(root/'plan.json'):raise ValueError('offline_training_gate_missing')
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=32)
    runtime=RuntimeLimit(root,7200);torch.set_num_threads(1);enforce_local_network_only();begin=time.perf_counter()
    durable_json(root/'started.json',{'PID':os.getpid(),'parent_PID':os.getppid(),'unix':time.time(),
        'KST':datetime.now().astimezone().isoformat(),'plan_SHA256':digest(root/'plan.json'),'auto_restart':False})
    try:
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=PARENT_SHA)
        actors={}
        for rep,seed in enumerate(SEEDS,1):
            for condition in ('A','B'):
                label=f'{condition}_s{rep}'
                actors[label]=train_arm(plan,root,label,seed,parent,runtime)
                durable_json(root/label/'TRAIN_policy_probes.json',probes(actors[label],parent,read(root/'TRAIN_probes.json')))
                if tensor_digest(parent.model.policy.state_dict())!=plan['parent']['parameters']:raise ValueError('parent_weight_mutation')
        result=evaluate_development(plan,root,actors,parent,runtime)
        verify(root)
        if optimizer_digest(parent.model.policy)!=plan['parent']['Adam']:raise ValueError('parent_Adam_mutation')
        endpoints={name:read(root/name/'endpoint.json') for name in actors}
        if sum(e['new_transitions'] for e in endpoints.values())!=65536:raise ValueError('study_transition_accounting')
        durable_json(root/'execution_complete.json',{'status':'CONTROLLED_PILOT_COMPLETE','new_transitions':65536,
            'development_games':512,'endpoints':endpoints,'development':result,'resources':job.usage(),
            'seconds':time.perf_counter()-begin,'original_model_Adam_preserved':True,'promotion':False})
    except BaseException as error:
        atomic_json(root/'failure.json',{'status':'PARTIAL','type':type(error).__name__,'error':str(error),
            'traceback':traceback.format_exc(),'seconds':time.perf_counter()-begin,'resources':job.usage()})
        raise
    finally:runtime.finished.set()


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('mode',choices=['prepare','run']);a.add_argument('--output',type=Path,required=True)
    args=a.parse_args();prepare(args.output) if args.mode=='prepare' else run(args.output)
