"""One frozen teacher-free micro: existing PPO, native Gym and paired evaluator."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
import time
import traceback
import numpy as np

from advisor.learning_resources import atomic_json, WindowsJob, RuntimeLimit
from advisor.learned_execution_alignment import durable_json, digest, content_hash
from advisor.learned_fixed_micro import VERSION, FixedMicroCases, EpisodeRival, training_vector, paired_summary, seed4
from advisor.learned_selfplay_pilot import OPPONENTS, MODES, StartBudget


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))


def prepare(output, parent, checkout):
    from advisor.learned_full_roster import load_bank, study_identity
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
    if output.exists():raise ValueError('existing_micro_artifacts_inspect_do_not_overwrite')
    output.mkdir(parents=True)
    bank=load_bank()['teams']['train']
    # Fixed coverage-based choices, before policy inference or battle outcomes.
    specifications=[('seen','bulk_recovery',24,71,[3,4,1],[3,5,6]),
        ('seen','fire_pressure',35,405,[2,1,4],[3,2,5]),
        ('heldout','bulk_recovery',64,110,[6,1,4],[4,1,2]),
        ('heldout','fire_pressure',66,446,[3,2,4],[6,4,5])]
    templates=[]
    for scope,family,a,b,own,foe in specifications:
        scenario={'scenario_id':f'{VERSION}:{scope}:{family}','teams':{'self':deepcopy(bank[a]),'opponent':deepcopy(bank[b])},
            'preview':{'self':own,'opponent':foe},'seed':[1,2,3,4],'history':[],
            'assumptions':['Frozen V8 TRAIN-only native-valid teams, fixed ordered bring-three; no learned preview.']}
        templates.append({'scope':scope,'family':family,'indices':[a,b],
            'team_SHA256':{s:content_hash(t)for s,t in scenario['teams'].items()},'scenario':scenario})
    if len({h for t in templates for h in t['team_SHA256'].values()})!=8:
        raise ValueError('micro_train_heldout_complete_team_overlap')
    cases=[]
    for r,rival in enumerate(OPPONENTS):
        for j in range(16):
            template=templates[j//4];i=r*16+j
            scenario=deepcopy(template['scenario'])
            scenario.update(scenario_id=f'{VERSION}:EVAL:{i}',seed=seed4(f'{VERSION}:EVAL:{i}'))
            cases.append({'index':i,'scope':template['scope'],'family':template['family'],'rival':rival,
                'scenario':scenario,'scenario_sha256':content_hash(scenario)})
    catalog=str(ROOT/'models/showdown_mc_domain_v1/catalog.json')
    actor=LearnedPolicy(parent,catalog,expected_model_id='9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf')
    m=actor.model
    if (type(m).__name__!='FoundationCombatPPO' or (m.n_steps,m.batch_size,m.n_epochs)!=(128,128,4)
            or m.gamma!=1 or m.gae_lambda!=.95 or optimizer_clock(m.policy)!=32768):
        raise ValueError('micro_parent_PPO_or_Adam_contract_mismatch')
    plan={'schema_version':VERSION,'seed':104027,'checkout':str(checkout),'catalog':catalog,
        'parent':{'path':str(parent),'sha256':actor.model_id,'parameters':tensor_digest(m.policy.state_dict()),
            'Adam':optimizer_digest(m.policy),'Adam_step':optimizer_clock(m.policy)},
        'bank_identity':study_identity(),'templates':templates,'evaluation_cases':cases,
        'training_steps':4096,'Adam_cap':128,'TRAIN_start_cap':512,'evaluation_start_cap':256,
        'workers':4,'vector':'DummyVecEnv_four_native_workers','CPU_percent':50,'memory_mib':8192,'device':'cpu',
        'opponents':list(OPPONENTS),'opponent_weights':[.25]*4,'frozen_modes':MODES,
        'teacher_enabled':False,'reward':'existing_sparse_native_terminal','temperature':1,
        'PPO':{'n_steps':m.n_steps,'batch_size':m.batch_size,'n_epochs':m.n_epochs,'gamma':m.gamma,
            'gae_lambda':m.gae_lambda,'ent_coef':m.ent_coef,'learning_rate':m.lr_schedule(1.),'zero_avoiding_beta':m.zero_avoiding_beta},
        'source_hashes':{p:digest(ROOT/p)for p in ['advisor/learned_fixed_micro.py','scripts/pilot_foundation_fixed_micro.py',
            'advisor/learned_gym.py','advisor/learned_combat_foundation.py','advisor/learned_selfplay_pilot.py',
            'advisor/learned_ppo_contract_audit.py','scripts/train_showdown_autonomous.py','scripts/evaluate_showdown_policy.py']},
        'headroom_gate':'Foundation seen win fraction must be <0.90; no case replacement or schedule tuning',
        'success_rule':'complete stable run; seen delta>0 and heldout paired case-seed-stratified CI lower>0 -> demonstrated; heldout upper<0 -> no_gain; otherwise inconclusive',
        'uncertainty':'conditional on four fixed team pairs; one training seed; not team-population or training-seed replication',
        'partition_rule':'two TRAIN team pairs; two disjoint mini-heldout team pairs from TRAIN bank; no claim parent had never seen these teams',
        'native_attempt_accounting':'PPO transitions capped4096; all constructor/reset/retry starts count512; native wait/retry submissions separately recorded, not fictitious PPO decisions'}
    durable_json(output/'plan.json',plan)
    print(json.dumps({'prepared':str(output/'plan.json'),'plan_SHA256':digest(output/'plan.json'),'teams':[t['indices']for t in templates]}))


def eval_phase(plan, root, kind, player, parent, budget, runtime):
    from scripts.evaluate_showdown_policy import evaluate
    from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases, persist_evaluation_batch
    from advisor.learned_difficulty_calibration import PublicRetryAudit
    lookup={c['index']:c for c in plan['evaluation_cases']}
    bindings={kind:{'sha256':player.model_id}}
    directory=root/'evaluation';directory.mkdir(exist_ok=True)
    for r,rival_kind in enumerate(OPPONENTS):
        for seat in ('p1','p2'):
            expected=[directory/f'{kind}_{rival_kind}_{seat}_{i}.receipt.json'for i in range(r*16,r*16+16)]
            if all(p.exists()for p in expected):continue
            if any(p.exists()for p in expected):raise ValueError('partial_eval_batch_inspect_before_any_retry')
            rival=EpisodeRival(rival_kind,parent)
            class Cases(FrozenEvalCases):
                def __call__(self,split,index):
                    value=super().__call__(split,index)
                    rival.reset(int.from_bytes(sha256(f'{VERSION}:rival:{index}:{seat}'.encode()).digest()[:4],'big'))
                    self.current=index
                    return value
            provider=Cases(lookup,budget,kind,rival_kind,seat,digest(root/'plan.json'))
            retry=None
            def observer(event):
                nonlocal retry
                index=provider.current
                if retry is None or retry.episode!=index: # Monitor per actual game.
                    retry=PublicRetryAudit(index);retry.episode=index
                retry.observe(event)
                if kind=='Foundation':
                    p=root/'evaluation_roots'/f'{index}_{seat}.json'
                    if not p.exists():
                        p.parent.mkdir(exist_ok=True)
                        side='self'if seat=='p1'else'opponent'
                        durable_json(p,{'case':index,'seat':seat,'view':event['before'][side]})
            def progress(records):
                persist_evaluation_batch(directory,records,bindings,lookup,kind,rival_kind,seat,digest(root/'plan.json'))
                atomic_json(root/'evaluation_progress.json',{'policy':kind,'rival':rival_kind,'seat':seat,
                    'valid_receipts':len(list(directory.glob('*.receipt.json'))),'starts':budget.count,'unix':time.time()})
            evaluate(plan['checkout'],plan['catalog'],{kind:player},cases=16,offset=r*16,
                curriculum_version='showdown-learning-curriculum-v8',rivals={rival_kind:rival},candidate_seat=seat,
                case_provider=provider,tactical_diagnostics=True,transition_observer=observer,
                per_game_progress=True,progress=progress,stopping=runtime.stopping)


def train(plan, root, parent, runtime):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock
    from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
    from scripts.train_showdown_autonomous import BudgetCallback,save_checkpoint,require_finite_ppo
    candidate=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
    m=candidate.model
    if tensor_digest(m.policy.state_dict())!=plan['parent']['parameters']or optimizer_digest(m.policy)!=plan['parent']['Adam']:
        raise ValueError('micro_initial_weights_or_restored_Adam_mismatch')
    vector,start_budget=training_vector(plan,root,parent)
    m.set_env(vector);m.set_random_seed(plan['seed']);m._last_obs=None
    initial=m.num_timesteps;steps=0;updates=0;checkpoints=[];metrics=[]
    def reserve_step(optimizer,args,kwargs):
        nonlocal updates
        if updates>=128:raise RuntimeError('micro_Adam_cap')
        durable_json(root/'Adam_intents'/f'{updates:04d}.json',{'step':updates,'Adam_before':optimizer_clock(m.policy)})
        updates+=1
    (root/'Adam_intents').mkdir()
    hook=m.policy.optimizer.register_step_pre_hook(reserve_step)
    try:
        for target in (1024,2048,3072,4096):
            recorder=AuditedSignalRecorder(root/'rollouts',candidate.encoder)
            callback=BudgetCallback(runtime,collect_diagnostics=True,signal_recorder=recorder)
            try:m.learn(total_timesteps=1024,reset_num_timesteps=False,callback=callback)
            finally:recorder.close()
            steps=m.num_timesteps-initial
            require_finite_ppo(m,rollout=True)
            if steps>4096 or updates>128:raise ValueError('micro_budget_exceeded')
            state={'PPO_collected':steps,'Adam_updates':updates,'Adam_clock':optimizer_clock(m.policy),
                'metrics':{k:float(v)if np.isfinite(v)else None for k,v in m.logger.name_to_value.items()if isinstance(v,(int,float,np.number))},
                'callback':callback.measurements,'completed':[x for batch in vector.env_method('drain_completed')for x in batch],
                'tactical_counts':vector.env_method('drain_tactical_counts'),'public_counts':vector.env_method('drain_public_behavior_counts')}
            path=save_checkpoint(m,candidate.encoder,root/f'checkpoint_{steps:04d}',{'micro_plan_SHA256':digest(root/'plan.json'),
                'source_parent_SHA256':plan['parent']['sha256'],'micro_new_transitions':steps,'teacher_enabled':False})
            checkpoints.append({'steps':steps,'path':path,'sha256':digest(path),'Adam':optimizer_digest(m.policy)})
            metrics.append(state);atomic_json(root/'training_progress.json',{'checkpoints':checkpoints,'windows':metrics,'TRAIN_starts':start_budget.count})
            if runtime.stopping()or steps!=target:break
        if steps!=4096:raise ValueError('micro_stopped_before_planned_complete_rollouts')
    finally:
        hook.remove();vector.close()
    restored=LearnedPolicy(checkpoints[-1]['path'],plan['catalog'],expected_model_id=checkpoints[-1]['sha256'])
    if tensor_digest(restored.model.policy.state_dict())!=tensor_digest(m.policy.state_dict())or optimizer_digest(restored.model.policy)!=optimizer_digest(m.policy):
        raise ValueError('micro_checkpoint_reload_weights_or_Adam_changed')
    atomic_json(root/'endpoint.json',{'path':checkpoints[-1]['path'],'sha256':restored.model_id,
        'new_transitions':steps,'new_Adam':updates,'initial_weight_identity':plan['parent']['parameters'],
        'initial_Adam_identity':plan['parent']['Adam'],'final_Adam_identity':optimizer_digest(restored.model.policy)})
    return restored


def run(root):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest
    from advisor.learning_resources import enforce_local_network_only
    plan=read(root/'plan.json')
    if (root/'completion.json').exists():raise ValueError('micro_already_complete_do_not_duplicate')
    if (root/'started.json').exists():raise ValueError('existing_micro_run_inspect_checkpoint_do_not_duplicate')
    for p,h in plan['source_hashes'].items():
        if digest(ROOT/p)!=h:raise ValueError('frozen_micro_source_changed:'+p)
    job=WindowsJob(memory_mib=8192,cpu_percent=50,active_process_limit=32)
    runtime=RuntimeLimit(root,3600)
    started=time.perf_counter()
    durable_json(root/'started.json',{'pid':os.getpid(),'start_unix':time.time(),'plan_SHA256':digest(root/'plan.json')})
    torch.set_num_threads(1);enforce_local_network_only()
    try:
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
        eval_budget=StartBudget(root/'EVAL_starts',256,root/'STOP')
        eval_phase(plan,root,'Foundation',parent,parent,eval_budget,runtime)
        rows=[read(p)for p in(root/'evaluation').glob('*.receipt.json')]
        seen=[r['record']for r in rows if plan['evaluation_cases'][r['case']]['scope']=='seen']
        parent_seen=sum(r['winner']=='self'and not r['truncated']for r in seen)/len(seen)
        if parent_seen>=.90:raise ValueError('frozen_scenarios_insufficient_learning_headroom_no_case_replacement')
        candidate=train(plan,root,parent,runtime)
        if tensor_digest(parent.model.policy.state_dict())!=plan['parent']['parameters']or optimizer_digest(parent.model.policy)!=plan['parent']['Adam']:
            raise ValueError('frozen_parent_mutated')
        eval_phase(plan,root,'Micro',candidate,parent,eval_budget,runtime)
        rows=[{'model':r['policy'],'record':r['record']}for p in(root/'evaluation').glob('*.receipt.json')for r in[read(p)]]
        summary=paired_summary(rows,plan['evaluation_cases'])
        probes=[]
        for p in sorted((root/'evaluation_roots').glob('*.json')):
            row=read(p);v=row['view'];a=parent.infer(v);b=candidate.infer(v)
            x=np.asarray(a['action_probabilities']);y=np.asarray(b['action_probabilities'])
            probes.append({'case':row['case'],'seat':row['seat'],'max_probability_change':float(abs(x-y).max()),
                'KL_parent_to_child':float(sum(x[i]*np.log(x[i]/max(y[i],1e-30))for i in range(35)if x[i]>0)),
                'initial_argmax':a['action_index'],'final_argmax':b['action_index'],
                'initial_value':a['discounted_return_estimate'],'final_value':b['discounted_return_estimate']})
        atomic_json(root/'policy_probes.json',probes)
        atomic_json(root/'analysis.json',summary)
        atomic_json(root/'completion.json',{'status':summary['verdict'],'PPO_transitions':4096,
            'Adam_updates':read(root/'endpoint.json')['new_Adam'],'evaluation_games':len(rows),'evaluation_starts':eval_budget.count,
            'wall_seconds':time.perf_counter()-started,'resources':job.usage(),'endpoint':read(root/'endpoint.json')})
        print(json.dumps({'completed':summary['verdict'],'seconds':time.perf_counter()-started}),flush=True)
    except BaseException as error:
        atomic_json(root/'failure.json',{'type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),
            'elapsed':time.perf_counter()-started,'resources':job.usage()})
        raise
    finally:
        runtime.finished.set()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['prepare','run']);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--parent',type=Path);parser.add_argument('--checkout',type=Path);a=parser.parse_args()
    prepare(a.output,a.parent,a.checkout)if a.mode=='prepare'else run(a.output)
