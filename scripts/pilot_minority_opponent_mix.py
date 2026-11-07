"""Exactly two original-A residual runs, then a frozen two-rival comparison."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import traceback

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
import numpy as np
import torch
from advisor import experimental_minority_opponent as impl
from advisor.experimental_context_training import ResidualActor, TrainCases, EXTRA
from advisor.learned_execution_alignment import content_hash, digest, durable_json, masked_sample
from advisor.learned_fixed_micro import seed4
from advisor.learned_opponent_quality import QualityActor, QualityTrace, global_rng_digest
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_policy import LearnedPolicy
from advisor.learned_selfplay_pilot import StartBudget, read
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only
from scripts.build_independent_development_teams import verify_bindings
from scripts.pilot_critic_trainability_controlled import OLD, train_arm, analyze, outputs
from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases, persist_evaluation_batch
from scripts.pilot_opponent_quality import Dispatch

VERSION=impl.VERSION
MODELS=('Foundation','A_s1','A_s2','Am_s1','Am_s2')
RIVALS=('foundation_argmax','foundation_masked_sample')


def prepare(root):
    root=Path(root)
    if (root/'plan.json').exists():raise ValueError('mixed_plan_already_frozen')
    scope=read(root/'scope.json');old=read(OLD/'plan.json')
    source=read(root/'source_manifest.json');ready=read(root/'source_ready.json')
    assert ready['status']=='SOURCE_READY' and ready['teams']==160 and ready['pairs']==80
    assert digest(root/'source_manifest.json')==ready['manifest_SHA256']
    verify_bindings({str(root/a['path']):a['sha256'] for a in source['assets'].values()});verify_bindings(source['source_bindings'])
    teams=read(root/'teams.json')['teams'];cases=[]
    for pair in range(80):
        for direction in (0,1):
            for rep in (0,1):
                a,b=2*pair+direction,2*pair+1-direction;i=len(cases)
                preview={s:(np.random.default_rng(seed4(f'{VERSION}:preview:{pair}:{rep}:{n}')).permutation(6)[:3]+1).tolist()
                         for s,n in [('self',a),('opponent',b)]}
                scenario={'scenario_id':f'{VERSION}:DEV:{i}','teams':{'self':deepcopy(teams[a]),'opponent':deepcopy(teams[b])},
                    'preview':preview,'seed':seed4(f'{VERSION}:native:{pair}:{direction}:{rep}'),'history':[],
                    'assumptions':['New frozen development source, no sealed outcomes.']}
                cases.append({'index':i,'pair':pair,'direction':direction,'replicate':rep,
                    'scenario':scenario,'scenario_sha256':content_hash(scenario)})
    durable_json(root/'cases.json',cases)
    # Identity/schedule metadata only. Previously consumed outcomes are not read.
    forbidden={tuple(s) for s in old['excluded_native_seeds']}
    for rel in ['candidate-context-q-dev-new-frozen-policy-evaluation-v1-20261106/cases.json',
                'critic-trainability-controlled-v1-20261106/cases.json',
                'actionable-decision-advantage-normalization-v1-20261107/cases.json',
                'opponent-diversity-quality-pilot-v1-20261107/cases.json']:
        forbidden.update(tuple(c['scenario']['seed']) for c in read(root.parent/rel))
    assert len({tuple(c['scenario']['seed']) for c in cases})==320
    assert not forbidden & {tuple(c['scenario']['seed']) for c in cases}
    prior_registry=root.parent/'train-opponent-policy-diversity-harness-v1-20261107/original_inputs_before.json'
    preserved=read(prior_registry);verify_bindings(preserved)
    quality=root.parent/'opponent-diversity-quality-pilot-v1-20261107'
    preserved.update({str(p):digest(p) for p in quality.rglob('*') if p.is_file()})
    durable_json(root/'preserved_file_bindings.json',preserved)
    controls={}
    bindings={str(OLD/'plan.json'):digest(OLD/'plan.json'),str(OLD/'offline_gate.json'):digest(OLD/'offline_gate.json'),
              str(OLD/'TRAIN_probes.json'):digest(OLD/'TRAIN_probes.json')}
    for i in (1,2):
        end=read(OLD/f'A_s{i}/endpoint.json');assert (end['new_transitions'],end['new_Adam'],end['train_seed'])==(16384,512,(116051,116053)[i-1])
        first=next((OLD/f'A_s{i}/rollouts').glob('rollout_1049088_*.audit.npz'))
        controls[f'A_s{i}']={'path':end['path'],'sha256':end['sha256'],'first_rollout':str(first)}
        for p in [Path(end['path']),Path(end['path']).parent/'residual_metadata.json',first,OLD/f'A_s{i}/endpoint.json']:
            bindings[str(p)]=digest(p)
    for p in [root/'scope.json',root/'source_manifest.json',root/'cases.json',root/'preserved_file_bindings.json',
              Path(old['parent']['path']),Path(old['catalog']),Path(old['runtime_manifest']),root/'legacy_A_contract_audit.json']:
        bindings[str(p)]=digest(p)
    paths=[]
    for folder,pattern in [('advisor','learned*.py'),('advisor','showdown*.py'),('advisor','experimental*.py'),('tools/showdown_bridge','*.cjs')]:
        paths+=list((REPO/folder).glob(pattern))
    paths += [REPO/p for p in ['scripts/train_showdown_autonomous.py','scripts/evaluate_showdown_policy.py',
        'scripts/pilot_critic_trainability_controlled.py','scripts/pilot_foundation_selfplay_exploration.py',
        'scripts/pilot_minority_opponent_mix.py','scripts/audit_minority_opponent_mix.py',
        'tests/test_minority_opponent_mix.py','docs/minority_opponent_mix.md']]
    plan={'version':VERSION,'scope':scope,'baseline_HEAD':'67d4ac8995892306e43ca8f8d3afaca296585b4c',
        'plan_file':'plan.json','treatment_prefix':'Am','training_plan':str(OLD/'plan.json'),
        'controls':controls,'parent':old['parent'],'training_seeds':[116051,116053],
        'catalog':old['catalog'],'checkout':old['checkout'],'runtime_manifest':old['runtime_manifest'],
        'PPO':old['PPO'],'learning_rate':old['learning_rate'],'TRAIN_validation_enabled':False,
        'preservation_registry':str(root/'preserved_file_bindings.json'),'bindings':bindings,
        'code':{str(p):digest(p) for p in paths},'analysis':{'draws':20000,'bootstrap_seed':116095,
        'primary':'Am_minus_A_terminal_return_vs_foundation_argmax_two_seed_mean',
        'decision':'positive lower95CI primary -> development signal only; otherwise not confirmed'},
        'frozen_KST':datetime.now().astimezone().isoformat()}
    durable_json(root/'plan.json',plan)
    return plan


def verify(root):
    p=read(root/'plan.json');s=p['scope']
    if (p['version']!=VERSION or s['new_PPO_cap']!=32768 or s['new_Adam_cap']!=1024
            or s['evaluation_start_cap']!=6400 or s['opponent_slots']!=impl.SLOTS
            or p['training_seeds']!=[116051,116053] or s['GPU'] is not False):raise ValueError('mixed_scope_changed')
    verify_bindings({**p['bindings'],**p['code']});verify_bindings(read(p['preservation_registry']))
    source=read(root/'source_manifest.json');verify_bindings(source['source_bindings'])
    verify_bindings({str(root/a['path']):a['sha256'] for a in source['assets'].values()})
    native=read(p['runtime_manifest']);verify_bindings({str(Path(native['root'])/x):h for x,h in native['files'].items()})
    return p


def gate(root):
    p=verify(root);assert read(root/'legacy_A_contract_audit.json')['status']=='PASS';torch.set_num_threads(1)
    parent=LearnedPolicy(p['parent']['path'],p['catalog'],expected_model_id=p['parent']['sha256'])
    A=impl.original.initialize(parent.model,'set');Am=impl.initialize(parent.model)
    assert tensor_digest(A.policy.state_dict())==tensor_digest(Am.policy.state_dict())
    assert not A.policy.optimizer.state and not Am.policy.optimizer.state and A.policy.optimizer.defaults==Am.policy.optimizer.defaults
    views=read(OLD/'TRAIN_probes.json');views=views['observations'] if isinstance(views,dict) else views
    x=torch.tensor(np.stack([parent.encoder.encode(v) for v in views]));masks=np.array([v['action_mask'] for v in views],bool)
    for a,b in zip(outputs(A.policy,x,masks),outputs(Am.policy,x,masks)):
        assert torch.equal(a,b)
    for key,value in p['PPO'].items():assert getattr(Am,key)==value
    assert Am.lr_schedule(1.)==Am.lr_schedule(.5)==p['learning_rate']==5e-5
    assert sum(x.numel() for x in Am.policy.parameters() if x.requires_grad)==4160
    for name in EXTRA:assert not Am.policy.state_dict()[name].any()
    saved=impl.save(Am,parent.encoder,root/'initial_parent',{'new_transitions':0,'new_Adam':0,'plan_SHA256':digest(root/'plan.json')})
    rng=global_rng_digest();restored=ResidualActor(saved,p['catalog']);assert global_rng_digest()==rng
    assert tensor_digest(restored.model.policy.state_dict())==tensor_digest(Am.policy.state_dict())
    assert optimizer_digest(restored.model.policy)==optimizer_digest(Am.policy)
    assert optimizer_digest(parent.model.policy)==p['parent']['Adam']
    durable_json(root/'offline_gate.json',{'status':'PASS','plan_SHA256':digest(root/'plan.json'),
        'initial_logits_probabilities_values_masks':'BIT_IDENTICAL','public_inputs':len(views),
        'fresh_Adam_state_entries':0,'trainable_parameters':4160,'Foundation_Adam_preserved':True,
        'RNG_neutral_reload':True,'native_starts_PPO_Adam':0})


class Trace(QualityTrace):
    def __init__(self,directory,model,rival,seat,case):
        self.directory,self.policy,self.rival,self.seat,self.case=directory,model,rival,seat,case
        self.key=f'{model}_{rival}_{seat}_{case}';self.path=directory/'decisions'/(self.key+'.jsonl')
        self.stream=self.path.open('x',encoding='utf-8');self.pending,self.first,self.steps={},{},0
    def selection(self,row,view):
        row={**row,'sampling_policy':row['policy'],'policy':self.policy if row['role']=='candidate' else self.rival}
        super().selection(row,view)
    def initial(self,row):
        if self.pending or self.steps:raise ValueError('mixed_snapshot_after_decision')
        durable_json(self.directory/'initial_native'/(self.key+'.json'),row)
        baseline=self.directory/'initial_native'/f'Foundation_foundation_argmax_{self.seat}_{self.case}.json'
        if baseline.exists():
            other=read(baseline)
            if any(row[k]!=other[k] for k in ('native_checkpoint_digest','native_state_SHA256',
                    'canonical_scenario_sha256','native_scenario_sha256','case','candidate_seat')):
                raise ValueError('mixed_native_initial_state_mismatch')


def evaluate_models(root,p,actors,runtime,job):
    from scripts.evaluate_showdown_policy import evaluate
    directory=root/'evaluation'
    for sub in ('receipts','decisions','initial_public','initial_native','trace_receipts'):(directory/sub).mkdir(parents=True,exist_ok=False)
    def identities():return {n:{'parameters':tensor_digest(a.model.policy.state_dict()),'Adam':optimizer_digest(a.model.policy),
                               'Adam_step':optimizer_clock(a.model.policy)} for n,a in actors.items()}
    durable_json(directory/'model_before.json',identities())
    def forbidden(*a,**k):raise RuntimeError('mixed_evaluation_Adam_forbidden')
    handles=[a.model.policy.optimizer.register_step_pre_hook(forbidden) for a in actors.values()]
    budget=StartBudget(directory/'starts',6400,root/'STOP');cases=read(root/'cases.json');lookup={c['index']:c for c in cases}
    candidate,rival=Dispatch(),Dispatch();holder={};completed=0;began=time.perf_counter();ps=digest(root/'plan.json')
    bindings={n:{'sha256':a.model_id} for n,a in actors.items()}
    try:
        for name in MODELS:
            for opponent in RIVALS:
                for seat in ('p1','p2'):
                    for offset in range(0,320,16):
                        provider=FrozenEvalCases(lookup,budget,name,opponent,seat,ps)
                        def provide(split,index):
                            scenario=provider(split,index);tr=Trace(directory,name,opponent,seat,index);holder['trace']=tr
                            candidate.actor=QualityActor(actors[name],'foundation_argmax',case=index,seat=seat,
                                role='candidate',record=tr.selection,rng_namespace=116091)
                            rival.actor=QualityActor(actors['Foundation'],opponent,case=index,seat=seat,
                                role='rival',record=tr.selection,rng_namespace=116091)
                            return scenario
                        provide.identity=provider.identity
                        def progress(records):
                            nonlocal completed
                            for rec in records:
                                key=f'{name}:{opponent}:{seat}:{rec["case"]}'
                                if not (directory/'receipts'/(key.replace(':','_')+'.receipt.json')).exists():
                                    if holder['trace'].case!=rec['case']:raise ValueError('mixed_progress_result_loss')
                                    holder['trace'].finish(rec)
                            completed+=persist_evaluation_batch(directory/'receipts',records,bindings,lookup,name,opponent,seat,ps)
                            if completed%8==0:atomic_json(root/'progress.json',{'phase':'evaluation','PID':os.getpid(),
                                'model':name,'opponent':opponent,'valid':completed,'starts':budget.count,'target':6400,
                                'games_per_second':completed/(time.perf_counter()-began),'seconds':time.perf_counter()-began,'resources':job.usage()})
                        evaluate(p['checkout'],p['catalog'],{name:candidate},cases=16,offset=offset,
                            rivals={opponent:rival},candidate_seat=seat,case_provider=provide,stopping=runtime.stopping,
                            transition_observer=lambda e:holder['trace'].observe(e),
                            initial_state_observer=lambda e:holder['trace'].initial(e),per_game_progress=True,progress=progress)
        assert completed==budget.count==6400
        after=identities();assert read(directory/'model_before.json')==after
        durable_json(directory/'model_after.json',after)
        durable_json(root/'execution_complete.json',{'new_trained':32768,'new_Adam':1024,'games':6400,
            'native_evaluation_starts':budget.count,'evaluation_seconds':time.perf_counter()-began})
    finally:
        for h in handles:h.remove()


def run(root):
    root=Path(root)
    if any((root/n).exists() for n in ('started.json','failure.json','completion.json')):raise ValueError('mixed_existing_owner_do_not_restart')
    p=read(root/'plan.json');assert read(root/'offline_gate.json')['plan_SHA256']==digest(root/'plan.json')
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=32);runtime=RuntimeLimit(root,7200)
    network=enforce_local_network_only();torch.set_num_threads(1);began=time.perf_counter()
    durable_json(root/'started.json',{'PID':os.getpid(),'KST':datetime.now().astimezone().isoformat(),'unix':time.time(),
        'plan_SHA256':digest(root/'plan.json'),'automatic_restarts':0})
    try:
        verify(root)
        parent=LearnedPolicy(p['parent']['path'],p['catalog'],expected_model_id=p['parent']['sha256'])
        actors={'Foundation':parent,**{n:ResidualActor(a['path'],p['catalog']) for n,a in p['controls'].items()}}
        for i,seed in enumerate(p['training_seeds'],1):actors[f'Am_s{i}']=train_arm(root,p,f'Am_s{i}',seed,parent,runtime,implementation=impl)
        evaluate_models(root,p,actors,runtime,job)
        from scripts.audit_minority_opponent_mix import audit
        result=audit(root,p)
        verify(root)
        durable_json(root/'owner_resources.json',{'seconds':time.perf_counter()-began,'resources':job.usage(),'network':network})
        durable_json(root/'completion.json',{'status':'COMPLETE','verdict':result['verdict'],'new_trained':32768,
            'new_Adam':1024,'evaluation_starts':6400,'valid_games':6400,'additional_runs':0,'promotion':False,
            'audit_SHA256':digest(root/'audit_complete.json'),'analysis_SHA256':digest(root/'analysis.json'),
            'KST':datetime.now().astimezone().isoformat()})
    except BaseException:
        durable_json(root/'failure.json',{'status':'PARTIAL','trace':traceback.format_exc(),'automatic_retry':False,
            'seconds':time.perf_counter()-began,'resources':job.usage()});raise
    finally:
        runtime.finished.set();durable_json(root/'owner_exit.json',{'PID':os.getpid(),
            'completion':(root/'completion.json').exists(),'failure':(root/'failure.json').exists(),
            'seconds':time.perf_counter()-began,'resources':job.usage()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('prepare','gate','run'));parser.add_argument('root',type=Path)
    a=parser.parse_args();{'prepare':prepare,'gate':gate,'run':run}[a.phase](a.root)
