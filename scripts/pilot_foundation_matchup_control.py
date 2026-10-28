"""Controlled matchup PPO: existing native/Gym/PPO/audit/checkpoint owners."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
import json
import os
import subprocess
import time
import traceback
import numpy as np

from advisor.learned_matchup_control import (VERSION,SEEDS,MODELS,CAP,SlotCases,
    schedule,exposure,evaluation_cases,validate_design,paired_analysis)
from advisor.learned_diverse_micro import team_keys,choose_teams
from advisor.learned_execution_alignment import content_hash,digest,durable_json
from advisor.learning_resources import WindowsJob,RuntimeLimit,atomic_json,enforce_local_network_only
from scripts.pilot_foundation_diverse_micro import model_identity,prior_plan_audit


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def prepare(output,prior):
    import torch
    from advisor.learned_full_roster import load_bank,study_identity
    from advisor.learned_policy import LearnedPolicy
    if output.exists():raise ValueError('existing_matchup_study_inspect_do_not_overwrite')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if head!='414dddce77eae3188924ed0caa1def7486619115':raise ValueError('matchup_baseline_HEAD')
    torch.set_num_threads(1);enforce_local_network_only()
    old=read(prior/'plan.json');ref=old['parent']
    parent=LearnedPolicy(ref['path'],old['catalog'],expected_model_id=ref['sha256'])
    identity=model_identity(parent);identity['path']=ref['path']
    if identity!=ref:raise ValueError('matchup_original_weights_Adam_or_clock')
    m=parent.model
    if type(m).__name__!='FoundationCombatPPO' or (m.n_steps,m.batch_size,m.n_epochs,m.n_envs)!=(128,128,4,4):
        raise ValueError('matchup_original_PPO_architecture')
    for key in ('gamma','gae_lambda','ent_coef','vf_coef','max_grad_norm','target_kl','zero_avoiding_beta'):
        if getattr(m,key)!=old['PPO'][key]:raise ValueError('matchup_PPO_changed:'+key)
    if m.lr_schedule(1.)!=old['PPO']['learning_rate'] or m.auxiliary_metadata()!=old['PPO']['auxiliary']:
        raise ValueError('matchup_LR_or_auxiliary_changed')
    rosters=[]
    for t in sorted((t for t in old['templates'] if t['scope']=='train' and t['direction']==0),key=lambda t:t['pair']):
        for s,i in zip(('self','opponent'),t['indices']):
            team=deepcopy(t['scenario']['teams'][s])
            rosters.append({'partition':'train','bank_index':i,'team':team,'preview':t['scenario']['preview'][s],
                'team_keys':team_keys(team),'previously_trained':True})
    audit=prior_plan_audit(output.parent)
    if audit['errors']:raise ValueError('matchup_prior_plan_audit_incomplete')
    excluded=set(audit['known_team_keys'])|{h for r in rosters for h in r['team_keys'].values()}
    bank=load_bank()['teams']['validation'];ii=choose_teams(bank,'MATCHUP_CONTROL:independent',excluded)
    from advisor.learned_fixed_micro import seed4
    independent=[]
    for i in ii:
        team=deepcopy(bank[i]);rng=np.random.default_rng(seed4(f'{VERSION}:preview:validation:{i}'))
        independent.append({'partition':'validation','bank_index':i,'team':team,
            'preview':[int(x) for x in rng.permutation(6)[:3]+1],'team_keys':team_keys(team),
            'previous_plan_match':False})
    cases=evaluation_cases(rosters,independent)
    if {tuple(c['scenario']['seed'])for c in cases}&set(map(tuple,audit['native_seeds'])):
        raise ValueError('matchup_prior_evaluation_seed_overlap')
    clones=[LearnedPolicy(ref['path'],old['catalog'],expected_model_id=ref['sha256'])for _ in range(2)]
    for clone in clones:
        other=model_identity(clone);other['path']=ref['path']
        if other!=ref or any(a.data_ptr()==b.data_ptr()for a,b in zip(parent.model.policy.parameters(),clone.model.policy.parameters())):
            raise ValueError('matchup_independent_clone_or_Adam')
    probes=[]
    for f in sorted((prior/'evaluation_roots').glob('*.json'))[:16]:
        v=read(f)['view'];raw=[];proof=[]
        for player in (parent,*clones):
            hook=player.model.policy.action_net.register_forward_pre_hook(lambda layer,args:raw.append(args[0].detach().cpu().numpy().copy()))
            try:proof.append(player.infer(v))
            finally:hook.remove()
        error=max(float(np.max(abs(z-raw[0])))for z in raw)
        pe=max(abs(x-y)for q in proof for x,y in zip(proof[0]['action_probabilities'],q['action_probabilities']))
        ve=max(abs(q['discounted_return_estimate']-proof[0]['discounted_return_estimate'])for q in proof)
        if error or pe or ve:raise ValueError('matchup_initial_output_not_equal')
        probes.append({'source':str(f),'SHA256':digest(f),'logit_error':error,'probability_error':pe,'value_error':ve})
    if len(probes)!=16:raise ValueError('matchup_initial_public_probes_missing')
    proof=prior/'persistence_probe_result.json'
    if read(proof)['phase']!='survived_launcher_exit':raise ValueError('matchup_detached_launch_proof_missing')
    sources=['advisor/learned_matchup_control.py','scripts/pilot_foundation_matchup_control.py',
        'advisor/learned_fixed_micro.py','advisor/learned_selfplay_pilot.py','advisor/learned_diverse_micro.py',
        'scripts/pilot_foundation_diverse_micro.py','advisor/learned_gym.py','advisor/learned_combat_foundation.py',
        'advisor/learned_combat_v5_strategic_aux.py','advisor/learned_combat_v5_strategic_policy.py',
        'advisor/learned_ppo_contract_audit.py','advisor/learned_signal_recorder.py',
        'advisor/learned_selfplay_retry.py','advisor/showdown_environment.py','advisor/showdown_observation.py',
        'tools/showdown_bridge/environment.cjs','scripts/train_showdown_autonomous.py',
        'scripts/evaluate_showdown_policy.py','scripts/pilot_foundation_selfplay_exploration.py']
    inputs={str(prior/f):digest(prior/f)for f in ('plan.json','closure.json','evaluation_bindings.json','coverage.json')}
    inputs.update({ref['path']:digest(ref['path']),str(proof):digest(proof)})
    for b in read(prior/'evaluation_bindings.json').values():
        inputs[b['path']]=digest(b['path'])
        for name in ('model.json','encoder.json'):
            p=Path(b['path']).parent/name
            if p.exists():inputs[str(p)]=digest(p)
    plan={'schema_version':VERSION,'baseline_HEAD':head,'parent':ref,'catalog':old['catalog'],
        'checkout':old['checkout'],'bank_identity':study_identity(),'training_rosters':rosters,
        'independent_rosters':independent,'schedules':{c:schedule(c)for c in ('A','B')},
        'training_seeds':list(SEEDS),'models':list(MODELS),'micro_budget':CAP,
        'opponents':['league_s0'],'opponent_mode':'frozen_Foundation_argmax','teacher_enabled':False,
        'temperature':1,'parent_KL':False,'fresh_Adam':False,
        'PPO':old['PPO'],'training_total_cap':65536,'Adam_total_cap':2048,
        'evaluation_cases':cases,'evaluation_games':2560,'workers':4,'CPU_percent':50,
        'memory_mib':8192,'device':'cpu','deadline_seconds':5400,
        'exposure_unit':'exact collected on-policy learner decisions, per own and opponent roster; completed battle counts may differ and are recorded separately',
        'exposure_per_team_per_role':1024,'common_segment_contract':{
            'segments':16,'steps_per_worker':256,'rollouts_per_segment':2,'n_steps':128,
            'transitions_per_segment':1024,'fresh_native_at_boundary':True,
            'unfinished_episode':'retain last rollout standard public value bootstrap; close without fabricated terminal reward; next rollout begins new episodes',
            'RNG':'policy/Adam/NumPy/Torch continue between segments; set_random_seed only at first segment; paired native namespace excludes condition'},
        'matchup_coverage':{'A_unordered':8,'B_unordered':32,'B_opponents_per_team':4,'new_matchup_unordered':8},
        'primary':'B-A on held-out unordered matchups of known training rosters; per-seed and equal-seed mean',
        'secondary':'A/B minus Foundation on excluded full team identities, not new-matchup performance',
        'statistics':'20000 paired team-pair bootstrap seed2026102811; retain ownership/RNG/seats/all models/both seeds; only2 training seeds',
        'decision':'both primary point effects positive and combined CI lower>0 -> recombination signal; unseen B-vs-parent separately; all nonpositive -> no_observed; otherwise inconclusive',
        'no_promotion':True,'automatic_restarts':0,'prior':str(prior),
        'detached_launch_proof':str(proof),'source_hashes':{s:digest(ROOT/s)for s in sources},'input_hashes':inputs}
    validate_design(plan)
    if plan['PPO']!=old['PPO']:raise ValueError('matchup_hyperparameters_changed')
    output.mkdir(parents=True)
    durable_json(output/'plan.json',plan);durable_json(output/'prior_plan_audit.json',audit)
    durable_json(output/'preflight_equivalence.json',{'public_states':probes,'parameters':sum(z.numel()for z in m.policy.parameters()),
        'weights_and_Adam':ref,'exposure':{c:exposure(plan['schedules'][c])for c in ('A','B')},
        'initial_roster_inputs_same':True,'new_native_starts':0,'new_PPO':0})
    for rep,seed in enumerate(SEEDS,1):
        for condition in ('A','B'):
            d=output/f'{condition}_s{rep}';d.mkdir()
            durable_json(d/'plan.json',{'parent_plan_SHA256':digest(output/'plan.json'),'condition':condition,'seed':seed,'cap':CAP})
    durable_json(output/'freeze.json',{'at_UTC':datetime.now(timezone.utc).isoformat(),
        'files':{str(f.relative_to(output)):digest(f)for f in output.rglob('*.json')},
        'PPO_cap':65536,'Adam_cap':2048,'evaluation_cap':2560})
    print(json.dumps({'prepared':str(output),'plan_SHA256':digest(output/'plan.json'),'exposure_per_team_per_role':1024}),flush=True)


def verify(root):
    plan=read(root/'plan.json');validate_design(plan)
    for p,h in read(root/'freeze.json')['files'].items():
        if digest(root/p)!=h:raise ValueError('matchup_frozen_file_changed:'+p)
    for p,h in plan['source_hashes'].items():
        if digest(ROOT/p)!=h:raise ValueError('matchup_source_changed:'+p)
    for p,h in plan['input_hashes'].items():
        if digest(p)!=h:raise ValueError('matchup_input_changed:'+p)
    return plan


def train_arm(plan,root,arm,condition,seed,parent,runtime):
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import optimizer_digest,optimizer_clock,tensor_digest
    from advisor.learned_fixed_micro import training_vector
    from advisor.learned_selfplay_pilot import StartBudget
    from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
    from advisor.learned_exact_update import rng_state
    from scripts.train_showdown_autonomous import BudgetCallback,save_checkpoint,require_finite_ppo
    folder=root/arm;candidate=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
    m=candidate.model;initial=model_identity(candidate);expected={**plan['parent'],'path':initial['path']}
    if initial!=expected:raise ValueError('matchup_initial_model_or_Adam')
    m.seed=seed;start_steps=m.num_timesteps;updates=0;checkpoints=[];segments=[]
    budget=StartBudget(folder/'TRAIN_starts',CAP['starts'],root/'STOP')
    (folder/'Adam_intents').mkdir()
    def reserve(optimizer,args,kwargs):
        nonlocal updates
        if updates>=512:raise RuntimeError('matchup_Adam_cap')
        durable_json(folder/'Adam_intents'/f'{updates:04d}.json',{'index':updates,'Adam_before':optimizer_clock(m.policy)})
        updates+=1
    hook=m.policy.optimizer.register_step_pre_hook(reserve)
    try:
        for index in range(16):
            if runtime.stopping():raise RuntimeError('matchup_STOP_before_segment')
            segment=plan['schedules'][condition][index];sroot=folder/'segments'/f'{index:02d}';sroot.mkdir(parents=True)
            vector,_=training_vector(plan,sroot,parent,case_factory=lambda w:SlotCases(plan,condition,seed,index,w),start_budget=budget)
            before_adam=optimizer_digest(m.policy)
            m.set_env(vector,force_reset=True)
            if index==0:m.set_random_seed(seed)
            if optimizer_digest(m.policy)!=before_adam:raise ValueError('matchup_env_reset_mutated_Adam')
            recorder=AuditedSignalRecorder(folder/'rollouts',candidate.encoder)
            callback=BudgetCallback(runtime,collect_diagnostics=True,signal_recorder=recorder)
            before=m.num_timesteps
            try:
                m.learn(total_timesteps=1024,reset_num_timesteps=False,callback=callback)
                require_finite_ppo(m,rollout=True)
                if m.num_timesteps-before!=1024 or m.num_timesteps-start_steps>16384:
                    raise ValueError('matchup_transition_or_segment_budget')
                completed=[e for batch in vector.env_method('drain_completed')for e in batch]
                cursors=vector.env_method('episode_cursor')
                records={'index':index,'collected_transitions':m.num_timesteps-start_steps,'new_Adam':updates,
                    'Adam_clock':optimizer_clock(m.policy),'slots':segment['slots'],'exposure_per_slot':256,
                    'completed':completed,'ending_public_episode_cursor':cursors,
                    'metrics':{k:float(v)if np.isfinite(v)else None for k,v in m.logger.name_to_value.items()if isinstance(v,(int,float,np.number))},
                    'callback':callback.measurements,'tactical_counts':vector.env_method('drain_tactical_counts')}
            finally:recorder.close();vector.close()
            # Every episode in a fixed slot must retain the exact roster binding.
            identities=list((sroot/'native_training').glob('worker_*/identity_*.json'))
            if len(identities)<8:raise ValueError('matchup_missing_native_slot_identities')
            for f in identities:
                identity=read(f);slot=segment['slots'][identity['worker']];e=identity['episode_identity']
                if e['team_sha256']!={side:content_hash(plan['training_rosters'][slot[k]]['team'])for side,k in (('self','own'),('opponent','opponent'))}:
                    raise ValueError('matchup_roster_changed_inside_decision_quota')
                if e['opponent_model_id']!=plan['parent']['sha256'] or identity['opponent_mode']!='argmax':
                    raise ValueError('matchup_opponent_changed')
            audits=[read(f)for f in(folder/'rollouts').glob('*.audit.json')
                if before<int(read(f)['model_timesteps_end'])<=m.num_timesteps]
            audits.sort(key=lambda x:x['model_timesteps_end'])
            if [x['model_timesteps_end']for x in audits]!=[before+512,before+1024]:
                raise ValueError('matchup_missing_or_duplicate_slot_rollouts')
            with np.load(audits[0]['capture'],allow_pickle=False)as z:
                if not z['episode_starts'][0].all():raise ValueError('matchup_cross_segment_episode_leakage')
            if any(a['transitions']!=512 for a in audits):raise ValueError('matchup_rollout_quota')
            records['verified_rollout_boundaries']=[{'end':a['model_timesteps_end'],
                'SHA256':a['capture_SHA256'],'transitions':a['transitions']}for a in audits]
            segments.append(records);steps=m.num_timesteps-start_steps
            path=save_checkpoint(m,candidate.encoder,folder/f'checkpoint_{steps}',{
                'matchup_plan_SHA256':digest(root/'plan.json'),'condition':condition,'continuation_seed':seed,
                'model_seed':seed,'curriculum_version':'showdown-learning-curriculum-v8',
                'source_parent_SHA256':plan['parent']['sha256'],'new_trained_transitions':steps,
                'new_Adam_updates':updates,'teacher_enabled':False})
            import torch
            rng_path=Path(path).parent/'training_rng.pt'
            with rng_path.open('xb')as stream:torch.save(rng_state(),stream)
            checkpoints.append({'steps':steps,'path':path,'sha256':digest(path),'Adam':optimizer_digest(m.policy),
                'Adam_clock':optimizer_clock(m.policy),'rng_path':str(rng_path),'rng_SHA256':digest(rng_path),
                'next_segment':index+1,'main_endpoint_boundary':steps%4096==0})
            atomic_json(folder/'training_progress.json',{'segments':segments,'checkpoints':checkpoints,
                'trained_transitions':steps,'new_Adam':updates,'TRAIN_starts':budget.count})
            atomic_json(root/'progress.json',{'phase':'training','arm':arm,'arm_steps':steps,'arm_Adam':updates,
                'completed_arms':len(list(root.glob('*/endpoint.json'))),'unix':time.time()})
        if m.num_timesteps-start_steps!=16384:raise ValueError('matchup_incomplete_arm')
    finally:hook.remove()
    restored=LearnedPolicy(checkpoints[-1]['path'],plan['catalog'],expected_model_id=checkpoints[-1]['sha256'])
    if tensor_digest(restored.model.policy.state_dict())!=tensor_digest(m.policy.state_dict()) or optimizer_digest(restored.model.policy)!=optimizer_digest(m.policy):
        raise ValueError('matchup_checkpoint_Adam_reload')
    durable_json(folder/'endpoint.json',{'path':checkpoints[-1]['path'],'sha256':restored.model_id,
        'trained_transitions':16384,'new_Adam':updates,'initial':initial,'final':model_identity(restored),
        'exposure':exposure(plan['schedules'][condition]),'condition':condition,'seed':seed})
    return restored


def eval_panel(root,plan,players,parent,runtime):
    from scripts.evaluate_showdown_policy import evaluate
    from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases,persist_evaluation_batch
    from advisor.learned_selfplay_pilot import StartBudget
    from advisor.learned_fixed_micro import EpisodeRival
    from advisor.learned_difficulty_calibration import PublicRetryAudit
    from advisor.learned_selfplay_retry import ResolvedRequestRateGuard
    from advisor.learned_response_predictor import public_input
    directory=root/'evaluation';directory.mkdir();lookup={c['index']:c for c in plan['evaluation_cases']}
    budget=StartBudget(root/'EVAL_starts',2560,root/'STOP');bindings={k:{'sha256':v.model_id}for k,v in players.items()}
    started=time.perf_counter();rate=ResolvedRequestRateGuard()
    for name,actor in players.items():
        for seat in ('p1','p2'):
            side='self'if seat=='p1'else'opponent'
            for offset in range(0,256,32):
                provider=FrozenEvalCases(lookup,budget,name,'league_s0',seat,digest(root/'plan.json'))
                rival=EpisodeRival('league_s0',parent);rival.reset(0);monitor=[None,None];first=set()
                def observer(event):
                    v=event['before'][side];public_input(v)
                    if monitor[0]!=v['episode_id']:monitor[:]=[v['episode_id'],PublicRetryAudit(v['episode_id'])]
                    monitor[1].observe(event);rate.observe(event)
                    if name=='Foundation'and v['episode_id']not in first:
                        first.add(v['episode_id']);index=offset+len(first)-1
                        p=root/'evaluation_roots'/f'{index}_{seat}.json';p.parent.mkdir(exist_ok=True)
                        durable_json(p,{'view':v,'case':index,'seat':seat})
                def progress(rows):
                    persist_evaluation_batch(directory,rows,bindings,lookup,name,'league_s0',seat,digest(root/'plan.json'))
                    n=len(list(directory.glob('*.receipt.json')))
                    atomic_json(root/'evaluation_progress.json',{'policy':name,'seat':seat,'valid':n,'starts':budget.count,
                        'target':2560,'seconds':time.perf_counter()-started,'games_per_second':n/(time.perf_counter()-started),'unix':time.time()})
                evaluate(plan['checkout'],plan['catalog'],{name:actor},cases=32,offset=offset,
                    curriculum_version='showdown-learning-curriculum-v8',rivals={'league_s0':rival},candidate_seat=seat,
                    case_provider=provider,stopping=runtime.stopping,tactical_diagnostics=True,integrated_diagnostics=True,
                    transition_observer=observer,per_game_progress=True,progress=progress)
    if budget.count!=2560:raise ValueError('matchup_evaluation_count')
    durable_json(root/'evaluation_retry_audit.json',rate.statistics())


def run(root):
    import torch
    from advisor.learned_policy import LearnedPolicy
    if(root/'started.json').exists()or(root/'completion.json').exists():raise ValueError('matchup_already_started_do_not_duplicate')
    plan=verify(root);job=WindowsJob(memory_mib=8192,cpu_percent=50,active_process_limit=32)
    runtime=RuntimeLimit(root,5400);start=time.perf_counter();torch.set_num_threads(1);network=enforce_local_network_only()
    durable_json(root/'started.json',{'PID':os.getpid(),'parent_PID':os.getppid(),'unix':time.time(),
        'own_bounded_job':True,'inherited_outer_job':job.inherited_job,'plan_SHA256':digest(root/'plan.json'),
        'detached_proof_SHA256':digest(plan['detached_launch_proof']),'automatic_restarts':0})
    try:
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
        frozen=model_identity(parent);bindings={'Foundation':plan['parent']}
        for rep,seed in enumerate(SEEDS,1):
            for condition in ('A','B'):
                arm=f'{condition}_s{rep}';begin=time.perf_counter()
                actor=train_arm(plan,root,arm,condition,seed,parent,runtime)
                end=read(root/arm/'endpoint.json');bindings[arm]={'path':end['path'],'sha256':end['sha256']}
                durable_json(root/arm/'timing.json',{'seconds':time.perf_counter()-begin,
                    'transitions_per_second':16384/(time.perf_counter()-begin),'resources':job.usage()})
                if model_identity(parent)!=frozen:raise ValueError('matchup_frozen_parent_mutated')
                verify(root)
        durable_json(root/'evaluation_bindings.json',bindings)
        players={k:parent if k=='Foundation'else LearnedPolicy(b['path'],plan['catalog'],expected_model_id=b['sha256'])for k,b in bindings.items()}
        before={k:model_identity(v)for k,v in players.items()};evstart=time.perf_counter()
        eval_panel(root,plan,players,parent,runtime)
        after={k:model_identity(v)for k,v in players.items()}
        if before!=after:raise ValueError('matchup_evaluation_mutated_model_Adam')
        rows=[read(p)for p in(root/'evaluation').glob('*.receipt.json')]
        analysis=paired_analysis(rows,plan['evaluation_cases']);durable_json(root/'analysis.json',analysis)
        verify(root)
        durable_json(root/'completion.json',{'status':'COMPLETE','verdict':analysis['verdict'],'PPO_transitions':65536,
            'new_Adam':sum(read(root/a/'endpoint.json')['new_Adam']for a in MODELS[1:]),'evaluation_games':len(rows),
            'evaluation_starts':len(list((root/'EVAL_starts').glob('start_*.json'))),
            'evaluation_seconds':time.perf_counter()-evstart,'wall_seconds':time.perf_counter()-start,
            'resources':job.usage(),'evaluation_models_before':before,'evaluation_models_after':after,
            'network':network,'no_promotion':True})
        print(json.dumps({'COMPLETE':analysis['verdict'],'PPO':65536,'evaluation':len(rows)}),flush=True)
    except BaseException as e:
        atomic_json(root/'failure.json',{'error':str(e),'type':type(e).__name__,'traceback':traceback.format_exc(),
            'seconds':time.perf_counter()-start,'resources':job.usage()});raise
    finally:runtime.finished.set()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--prior',type=Path);a=p.parse_args()
    prepare(a.output,a.prior)if a.mode=='prepare'else run(a.output)
