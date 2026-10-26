"""Single bounded native PPO continuation and predeclared paired evaluation."""
import argparse
from datetime import datetime, timezone
from functools import partial
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from advisor.learned_selfplay_pilot import read, VERSION, RIVALS, PilotEnvFactory
from advisor.learned_execution_alignment import digest, content_hash, durable_json
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, process_alive, enforce_local_network_only


def verify(plan_path):
    plan = read(plan_path)
    if (plan['schema_version'] != VERSION or plan['trained_transitions'] != 65536
            or plan['optimizer_step_cap'] != 2048 or plan['training_start_cap'] != 8192
            or plan['evaluation_start_cap'] != 4096 or plan['workers'] != 4
            or plan['memory_mib'] != 8192 or plan['device'] != 'cpu'):
        raise ValueError('pilot_plan_contract')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip() != plan['source_HEAD']:
        raise ValueError('pilot_source_HEAD_changed')
    for path, expected in plan['source_hashes'].items():
        if digest(REPO / path) != expected:
            raise ValueError('pilot_source_changed:' + path)
    for path, expected in plan['input_hashes'].items():
        if digest(path) != expected:
            raise ValueError('pilot_frozen_input_changed:' + path)
    return plan


class FrozenEvalCases:
    def __init__(self, rows, budget, policy, rival, seat, plan_sha):
        self.rows, self.budget = rows, budget
        self.policy, self.rival, self.seat, self.plan_sha = policy, rival, seat, plan_sha

    def __call__(self, split, index):
        if split != 'validation' or index not in self.rows:
            raise ValueError('pilot_frozen_eval_case_access')
        row = self.rows[index]
        key = f'{self.policy}:{self.rival}:{self.seat}:{index}'
        self.budget.reserve({'key': key, 'case': index, 'policy': self.policy,
            'rival': self.rival, 'seat': self.seat, 'scenario_SHA256': row['scenario_sha256'],
            'plan_SHA256': self.plan_sha})
        from copy import deepcopy
        return deepcopy(row['scenario'])


def evaluation_worker(plan_path, worker):
    import numpy as np
    import torch
    from sb3_contrib import MaskablePPO
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
    from advisor.learned_selfplay_pilot import StartBudget
    from advisor.learned_difficulty_calibration import PublicRetryAudit, AttemptRateGuard
    from scripts.evaluate_showdown_policy import evaluate
    plan = verify(plan_path); root = Path(plan['output'])
    enforce_local_network_only(); torch.set_num_threads(1)
    def forbidden(*a, **k): raise RuntimeError('evaluation_only_no_optimizer_or_training')
    MaskablePPO.learn = MaskablePPO.collect_rollouts = MaskablePPO.save = forbidden
    torch.optim.Adam.step = forbidden
    rows = read(plan['evaluation_cases'])['cases'][worker*64:(worker+1)*64]
    lookup = {row['index']: row for row in rows}
    directory = root / 'evaluation' / f'worker_{worker}'
    budget = StartBudget(directory, 1024, root / 'STOP')
    bindings = read(root / 'endpoint.json')
    players = {kind: LearnedPolicy(binding['path'], plan['catalog'], expected_model_id=binding['sha256'])
               for kind, binding in bindings.items()}
    rivals = {'foundation_argmax': players['parent'],
              'v4_argmax': LearnedPolicy(plan['reference_V4']['path'], plan['catalog'], expected_model_id=plan['reference_V4']['sha256']),
              'tactical_heuristic': 'tactical_heuristic', 'champions_heuristic': 'champions_heuristic'}
    models = {**players, 'v4_argmax': rivals['v4_argmax']}
    before = {key: {'parameters': tensor_digest(m.model.policy.state_dict()), 'Adam': optimizer_digest(m.model.policy)} for key,m in models.items()}
    completed = 0; started = time.monotonic(); rate = AttemptRateGuard()
    for seat in ('p1', 'p2'):
        for rival in RIVALS:
            for kind, player in players.items():
                monitor = [None, None]
                def observer(event):
                    episode = next(iter(event['before'].values()))['episode_id']
                    if monitor[0] != episode:
                        monitor[:] = [episode, PublicRetryAudit(episode)]
                    monitor[1].observe(event); rate.observe(event['result']['action_rejected'])
                def progress(records):
                    nonlocal completed
                    record = records[-1]; index = record['case']; case = lookup[index]
                    if (record['canonical_scenario_sha256'] != case['scenario_sha256']
                            or record['candidate_seat'] != seat or record['initial_native_seed'] != case['scenario']['seed']):
                        raise ValueError('pilot_evaluation_case_seat_seed_mismatch')
                    key = f'{kind}:{rival}:{seat}:{index}'
                    path = directory / (key.replace(':', '_') + '.receipt.json')
                    durable_json(path, {'key': key, 'policy': kind, 'rival': rival, 'seat': seat, 'case': index,
                        'model_SHA256': bindings[kind]['sha256'], 'record': record,
                        'record_SHA256': content_hash(record), 'plan_SHA256': digest(plan_path)})
                    completed += 1
                    if completed % 8 == 0:
                        atomic_json(directory / 'progress.json', {'status': 'running', 'PID': os.getpid(), 'completed': completed,
                            'target': 1024, 'games_per_second': completed/(time.monotonic()-started)})
                evaluate(plan['checkout'], plan['catalog'], {kind: player}, split='validation', cases=64,
                    offset=rows[0]['index'], curriculum_version='showdown-learning-curriculum-v8',
                    rivals={rival: rivals[rival]}, candidate_seat=seat,
                    case_provider=FrozenEvalCases(lookup, budget, kind, rival, seat, digest(plan_path)),
                    stopping=lambda: (root/'STOP').exists(), tactical_diagnostics=True,
                    transition_observer=observer, progress=progress)
    after = {key: {'parameters': tensor_digest(m.model.policy.state_dict()), 'Adam': optimizer_digest(m.model.policy)} for key,m in models.items()}
    if before != after or completed != 1024 or budget.count != 1024:
        raise ValueError('pilot_evaluation_count_or_model_mutation')
    durable_json(directory / 'complete.json', {'PID': os.getpid(), 'completed': completed, 'before': before, 'after': after,
        'seconds': time.monotonic()-started, 'training': 0, 'optimizer_updates': 0})


def analyze(plan, root):
    import numpy as np
    records = [read(p) for p in (root/'evaluation').glob('worker_*/*.receipt.json')]
    if len(records) != 4096 or len({r['key'] for r in records}) != 4096:
        raise ValueError('pilot_evaluation_missing_or_duplicate')
    cases = read(plan['evaluation_cases'])['cases']
    expected = {f'{p}:{r}:{s}:{c["index"]}' for p in ('parent','candidate') for r in RIVALS for s in ('p1','p2') for c in cases}
    if {r['key'] for r in records} != expected:
        raise ValueError('pilot_evaluation_slot_set')
    starts = [read(p) for p in (root/'evaluation').glob('worker_*/start_*.json')]
    if len(starts) != 4096 or {r['key'] for r in starts} != expected:
        raise ValueError('pilot_evaluation_start_receipts')
    bindings = read(root/'endpoint.json')
    lookup = {r['key']: r for r in records}
    for row in records:
        if (content_hash(row['record']) != row['record_SHA256']
                or row['model_SHA256'] != bindings[row['policy']]['sha256']):
            raise ValueError('pilot_evaluation_record_SHA')
    def score(row):return float(row['record']['winner']=='self' and not row['record']['truncated'])
    differences=[]
    for case in cases:
        key=case['index']; differences.append(np.mean([score(lookup[f'candidate:{r}:{s}:{key}'])-score(lookup[f'parent:{r}:{s}:{key}']) for r in RIVALS for s in ('p1','p2')]))
    rng=np.random.default_rng(plan['bootstrap_seed']);draws=rng.integers(0,256,size=(20000,256))
    delta=np.asarray(differences);ci=np.quantile(delta[draws].mean(1),[.025,.975])
    summaries={}
    for p in ('parent','candidate'):
        summaries[p]={}
        for rival in (*RIVALS,'all'):
            rows=[x['record'] for x in records if x['policy']==p and (rival=='all' or x['rival']==rival)]
            summaries[p][rival]={'n':len(rows),'wins':sum(x['winner']=='self' and not x['truncated'] for x in rows),
                'losses':sum(x['winner']=='opponent' and not x['truncated'] for x in rows),
                'draws':sum(x['winner'] is None and not x['truncated'] for x in rows),
                'truncations':sum(x['truncated'] for x in rows),'native_rejections':sum(x['native_choice_rejections'] for x in rows)}
    per_rival={}
    for r in RIVALS:
        d=np.asarray([np.mean([score(lookup[f'candidate:{r}:{s}:{c["index"]}'])-score(lookup[f'parent:{r}:{s}:{c["index"]}']) for s in ('p1','p2')]) for c in cases])
        per_rival[r]={'difference':float(d.mean()),'case_cluster_95CI':np.quantile(d[draws].mean(1),[.025,.975]).tolist()}
    censored=any(x['record']['truncated'] for x in records)
    status=('IMPROVEMENT_SIGNAL_REQUIRES_INDEPENDENT_CONFIRMATION' if ci[0]>0 and not censored
            else 'NO_IMPROVEMENT' if ci[1]<0 and not censored else 'INCONCLUSIVE')
    result={'status':status,'primary_argmax_difference':float(delta.mean()),'case_cluster_95CI':ci.tolist(),
            'independent_team_pair_clusters':256,'resamples':20000,'summaries':summaries,'per_rival':per_rival,
            'training_seed_repetitions':1,'training_seed_population_CI':None,'truncation_present':censored,
            'new_model_promotion':False,'evaluation_games':len(records)}
    durable_json(root/'analysis.json',result)
    return result


def owned_run(plan_path):
    import torch
    from scripts import train_showdown_autonomous as trainer
    from advisor import learned_ppo_contract_audit as audit
    from advisor.learned_selfplay_signal_audit import PilotSignalRecorder
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import optimizer_clock
    plan = verify(plan_path); root=Path(plan['output']); root.mkdir(exist_ok=True,parents=True)
    if (root/'control.json').exists():
        raise RuntimeError('pilot_already_started_no_automatic_restart')
    job=WindowsJob(memory_mib=8192,cpu_percent=50,active_process_limit=24)
    if job.inherited_job:raise RuntimeError('pilot_requires_independent_desktop_owner')
    network=enforce_local_network_only();torch.set_num_threads(1)
    durable_json(root/'control.json',{'PID':os.getpid(),'parent_PID':os.getppid(),'inherited_job':False,'own_job':True,
        'started_UTC':datetime.now(timezone.utc).isoformat(),'plan_SHA256':digest(plan_path),
        'CPU_percent':50,'RAM_mib':8192,'workers':4,'GPU':False,'automatic_restarts':0})
    outer=RuntimeLimit(root,5400)
    try:
        # Only this explicit experiment entry point installs these adapters.
        old_factory,old_recorder=trainer.LearningEnvFactory,audit.AuditedSignalRecorder
        trainer.LearningEnvFactory=partial(PilotEnvFactory,pilot_root=str(root))
        audit.AuditedSignalRecorder=partial(PilotSignalRecorder,pilot_root=str(root))
        def progress(event):
            if outer.stopping():(root/'training'/'STOP').touch()
            if event['phase']=='checkpoint_committed':verify(plan_path)
            atomic_json(root/'progress.json',{'phase':'training',**event,'PID':os.getpid(),
                'recorded_UTC':datetime.now(timezone.utc).isoformat(),'resources':job.usage()})
        try:
            trainer.run(read(plan['training_config']),root/'training',event_callback=progress,resource_job=job)
        finally:
            trainer.LearningEnvFactory=old_factory;audit.AuditedSignalRecorder=old_recorder
        state=read(root/'training'/'state.json')
        if state['status']!='complete' or state['trained_rollout_transitions']!=65536:
            durable_json(root/'partial.json',{'reason':'training_not_complete','state':state,'resources':job.usage()});return
        endpoints=[]
        for path in (root/'training'/'experiment_00').glob('checkpoint_*/model.json'):
            metadata=read(path)
            if metadata['stage']=='ppo':endpoints.append((metadata['total_steps'],path,metadata))
        _,meta_path,metadata=max(endpoints,key=lambda x:x[0]);path=meta_path.with_suffix('.zip')
        restored=LearnedPolicy(path,plan['catalog'],expected_model_id=digest(path))
        clock=optimizer_clock(restored.model.policy)
        if not 0<clock-plan['parent']['optimizer_steps']<=2048:raise ValueError('pilot_optimizer_accounting')
        durable_json(root/'endpoint.json',{'parent':{'path':plan['parent']['path'],'sha256':plan['parent']['sha256']},
            'candidate':{'path':str(path),'sha256':digest(path),'optimizer_steps':clock}})
        durable_json(root/'training_complete.json',{'trained_transitions':65536,'collected_transitions':state['transitions'],
            'new_optimizer_steps':clock-plan['parent']['optimizer_steps'],'endpoint':str(path),'checkpoint_reload':'pass','resources':job.usage()})
        del restored
        import gc;gc.collect()
        logs=[];processes=[]
        for i in range(4):
            log=(root/f'evaluation_worker_{i}.log').open('xb');logs.append(log)
            processes.append(subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--plan',str(plan_path),'--eval-worker',str(i)],
                cwd=REPO,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
        while any(p.poll() is None for p in processes):
            if outer.stopping() or any(p.poll() not in (None,0) for p in processes):raise RuntimeError('pilot_evaluation_worker_failure_or_STOP')
            finished=sum(len(list((root/'evaluation'/f'worker_{i}').glob('*.receipt.json'))) for i in range(4))
            atomic_json(root/'progress.json',{'phase':'evaluation','completed':finished,'target':4096,'PID':os.getpid(),
                'resources':job.usage(),'recorded_UTC':datetime.now(timezone.utc).isoformat()})
            time.sleep(5)
        for log in logs:log.close()
        if any(p.returncode!=0 for p in processes):raise RuntimeError('pilot_evaluation_failed')
        verify(plan_path);result=analyze(plan,root)
        durable_json(root/'execution_complete.json',{'status':result['status'],'trained_transitions':65536,
            'evaluation_games':4096,'analysis_SHA256':digest(root/'analysis.json'),'resources':job.usage(),
            'network':network,'model_promotion':False,'ended_UTC':datetime.now(timezone.utc).isoformat()})
    finally:outer.finished.set()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--owned',action='store_true');parser.add_argument('--eval-worker',type=int)
    args=parser.parse_args()
    try:
        if args.eval_worker is not None:evaluation_worker(args.plan,args.eval_worker)
        elif args.owned:owned_run(args.plan)
        else:raise RuntimeError('explicit_independent_owned_launch_required')
    except BaseException as error:
        root=Path(read(args.plan)['output'])
        atomic_json(root/(f'failure_eval_{args.eval_worker}.json' if args.eval_worker is not None else 'failure.json'),
            {'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc(),
             'automatic_restart':False,'recorded_UTC':datetime.now(timezone.utc).isoformat()})
        raise
