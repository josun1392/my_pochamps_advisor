"""One authorized two-seed actionable-normalization study, no automatic restart."""
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from datetime import datetime
from copy import deepcopy
import argparse,json,os,random,time,traceback
import numpy as np
import torch

from advisor import experimental_actionable_advantage as impl
from advisor.experimental_context_training import ResidualActor,initialize as initialize_A
from advisor.learned_policy import LearnedPolicy
from advisor.learned_execution_alignment import durable_json,digest
from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock
from advisor.learned_fixed_micro import seed4
from advisor.learning_resources import WindowsJob,RuntimeLimit,enforce_local_network_only
from scripts.pilot_critic_trainability_controlled import train_arm,evaluate_models,outputs,verify
from advisor.learned_execution_alignment import content_hash

VERSION=impl.VERSION
PLAN='plan_revision_02.json'
GATE='offline_gate_revision_02.json'
BASELINE='6e3f6d651d75a4655822d365b9195b3289b1a0ff'
ART=Path.home()/'.codex/artifacts'
OLD=ART/'experimental-candidate-context-controlled-train-pilot-v1-20261105/study'
CRITIC=ART/'critic-trainability-controlled-v1-20261106'
OWNED=['advisor/experimental_actionable_advantage.py','advisor/learned_combat_foundation.py',
       'scripts/pilot_critic_trainability_controlled.py','scripts/pilot_actionable_advantage.py',
       'tests/test_actionable_advantage.py','docs/actionable_advantage_normalization.md']


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def cases_for(teams):
    rows=[]
    for pair in range(80):
        previews=[(np.random.default_rng(seed4(f'{VERSION}:preview:{pair}:{s}')).permutation(6)[:3]+1).tolist() for s in (0,1)]
        for direction in (0,1):
            for replicate in range(4):
                index=len(rows);other=1-direction
                scenario={'scenario_id':f'{VERSION}:DEV:{index}',
                    'teams':{'self':deepcopy(teams[2*pair+direction]),'opponent':deepcopy(teams[2*pair+other])},
                    'preview':{'self':previews[direction],'opponent':previews[other]},
                    'seed':seed4(f'{VERSION}:DEV:{index}'),'history':[],
                    'assumptions':['T1 new TRAIN-domain development source, not sealed; fixed ordered three.']}
                rows.append({'index':index,'pair':pair,'direction':direction,'replicate':replicate,
                    'rival':'league_s0','scenario':scenario,'scenario_sha256':content_hash(scenario)})
    return rows


def prepare(root):
    if (root/PLAN).exists():raise RuntimeError('existing_plan_do_not_replace')
    if (root/'plan.json').exists():
        original=read(root/'plan.json');assert original['version']==VERSION
        revised=deepcopy(original);revised['plan_file']=PLAN
        revised['code']={p:digest(p) for p in original['code']}
        revised['bindings'][str(root/'plan.json')]=digest(root/'plan.json')
        for name in ('pre_execution_revision_01_source_manifest.json','legacy_checkpoint_rng_caveat.json'):
            revised['bindings'][str(root/name)]=digest(root/name)
        revised['pre_execution_revision']={'revision':2,'parent_plan_SHA256':digest(root/'plan.json'),
            'reason':'isolate verification-loader RNG effects to match original A, before any rollout/update; no source/cases/seed/PPO/budget change',
            'KST':datetime.now().astimezone().isoformat()}
        durable_json(root/PLAN,revised)
        return
    preflight=read(root/'preflight_result.json');assert preflight['status']=='INTERVENTION_JUSTIFIED'
    ready=read(root/'source_ready.json');assert ready['status']=='SOURCE_READY'
    source=read(root/'source_manifest.json');assert digest(root/'source_manifest.json')==ready['manifest_SHA256']
    verify({str(root/a['path']):a['sha256'] for a in source['assets'].values()});verify(source['source_bindings'])
    teams=read(root/'teams.json')['teams'];assert len(teams)==160 and len(source['pairs'])==80
    prior=read(OLD/'plan.json');controls={};bindings={str(OLD/'plan.json'):digest(OLD/'plan.json')}
    for rep in (1,2):
        end=read(OLD/f'A_s{rep}/endpoint.json');assert end['new_transitions']==16384 and end['new_Adam']==512
        first=next((OLD/f'A_s{rep}/rollouts').glob('rollout_1049088_*.audit.npz'))
        controls[f'A_s{rep}']={'path':end['path'],'sha256':end['sha256'],'first_rollout':str(first)}
        for p in (Path(end['path']),Path(end['path']).parent/'residual_metadata.json',first,
                  Path(str(first).removesuffix('.audit.npz')+'.jsonl.gz')):bindings[str(p)]=digest(p)
    # Protect all previous models/Adam, including the just-completed critic study.
    registry=ART/'candidate-context-frozen-development-replication-v1-20261105/preserved_file_bindings.json'
    preserved=read(registry)
    for p in CRITIC.glob('**/*.zip'):preserved[str(p)]=digest(p)
    for p in CRITIC.glob('**/*metadata.json'):preserved[str(p)]=digest(p)
    for p in (CRITIC/'completion.json',CRITIC/'final_closure.json',CRITIC/'analysis.json'):preserved[str(p)]=digest(p)
    verify(preserved);durable_json(root/'preserved_file_bindings.json',preserved)
    for p in (root/'source_manifest.json',root/'preflight_contract.json',root/'preflight_result.json',
              root/'preserved_file_bindings.json',Path(prior['parent']['path']),Path(prior['parent']['path']).with_suffix('.json'),
              Path(prior['catalog']),Path(prior['runtime_manifest'])):bindings[str(p)]=digest(p)
    cases=cases_for(teams)
    old_seeds={tuple(x) for x in prior['excluded_native_seeds']}
    old_seeds.update(tuple(c['scenario']['seed']) for c in prior['development_cases'])
    for path in (CRITIC/'cases.json',ART/'candidate-context-q-dev-new-frozen-policy-evaluation-v1-20261106/cases.json'):
        old_seeds.update(tuple(c['scenario']['seed']) for c in read(path))
    assert len(cases)==640 and len({tuple(c['scenario']['seed']) for c in cases})==640
    assert not {tuple(c['scenario']['seed']) for c in cases}&old_seeds
    durable_json(root/'cases.json',cases);bindings[str(root/'cases.json')]=digest(root/'cases.json')
    code={str(REPO/p):digest(REPO/p) for p in OWNED}
    for folder,pattern in [('advisor','learned*.py'),('advisor','showdown*.py'),('tools/showdown_bridge','*.cjs')]:
        code.update({str(p):digest(p) for p in (REPO/folder).glob(pattern)})
    for p in ('advisor/experimental_context_training.py','advisor/experimental_critic_training.py',
              'scripts/train_showdown_autonomous.py','scripts/evaluate_showdown_policy.py','scripts/pilot_foundation_selfplay_exploration.py'):
        code[str(REPO/p)]=digest(REPO/p)
    plan={'version':VERSION,'baseline_HEAD':BASELINE,'frozen_KST':datetime.now().astimezone().isoformat(),
        'plan_file':PLAN,'treatment_prefix':'An','TRAIN_validation_enabled':False,
        'training_plan':str(OLD/'plan.json'),'controls':controls,'training_seeds':[116051,116053],
        'parent':prior['parent'],'catalog':prior['catalog'],'checkout':prior['checkout'],'runtime_manifest':prior['runtime_manifest'],
        'PPO':prior['PPO'],'learning_rate':prior['learning_rate'],'normalization_contract':impl.contract(),
        'new_transitions':32768,'new_Adam':1024,'control_retraining':0,'new_evaluation_starts':6400,
        'games_per_model':1280,'team_pairs':80,'model_order':['Foundation','A_s1','A_s2','An_s1','An_s2'],
        'analysis':{'primary':'An_minus_A_terminal_return_two_seed_mean','bootstrap_seed':116073,'draws':20000,
            'cluster':'80 team pairs retain owners/RNG/real seats/both continuation repetitions',
            'decision':'positive lower95CI development signal only; otherwise DEVELOPMENT_SIGNAL_NOT_CONFIRMED'},
        'evaluation':{'rival':'frozen Foundation argmax','candidate':'T=1 argmax','owners':2,'RNG':4,'seats':['p1','p2']},
        'resources':{'CPU_percent':50,'workers':4,'memory_mib':12288,'GPU':False},'wall_seconds':7200,
        'preservation_registry':str(root/'preserved_file_bindings.json'),'bindings':bindings,'code':code,
        'automatic_restarts':0,'promotion':False,'independent_development_not_sealed':True}
    durable_json(root/PLAN,plan)


def gate(root):
    p=read(root/PLAN);verify({**p['bindings'],**p['code']});torch.set_num_threads(1)
    parent=LearnedPolicy(p['parent']['path'],p['catalog'],expected_model_id=p['parent']['sha256'])
    a=initialize_A(parent.model,'set');n=impl.initialize(parent.model)
    views=read(OLD/'TRAIN_probes.json')
    if isinstance(views,dict):views=views['observations']
    x=torch.tensor(np.stack([parent.encoder.encode(v) for v in views]));masks=np.array([v['action_mask'] for v in views],bool)
    for left,right in zip(outputs(a.policy,x,masks),outputs(n.policy,x,masks)):
        if not torch.equal(left,right):raise ValueError('actionable_initial_outputs_not_bit_identical')
    assert tensor_digest(a.policy.state_dict())==tensor_digest(n.policy.state_dict())
    assert not n.policy.optimizer.state and a.policy.optimizer.defaults==n.policy.optimizer.defaults
    path=impl.save(n,parent.encoder,root/'initial_parent_revision_02',{'new_transitions':0,'new_Adam':0,'plan_SHA256':digest(root/PLAN)})
    rng=(torch.get_rng_state().clone(),np.random.get_state(),random.getstate())
    reload=impl.ActionableActor(path,p['catalog']);assert optimizer_digest(reload.model.policy)==optimizer_digest(n.policy)
    now=np.random.get_state()
    assert torch.equal(rng[0],torch.get_rng_state()) and rng[2]==random.getstate()
    assert rng[1][0]==now[0] and np.array_equal(rng[1][1],now[1]) and rng[1][2:]==now[2:]
    durable_json(root/GATE,{'status':'PASS','plan_SHA256':digest(root/PLAN),
        'initial_outputs':'BIT_IDENTICAL_logits_probabilities_values_masks_argmax','views':len(views),
        'initial_parameters_identical':True,'fresh_Adam':True,'Adam_step':0,'trainable_parameters':4160,
        'critic_encoder_prediction_frozen':True,'new_native_PPO_Adam':0,
        'verification_loader_RNG_preserved':True,
        'normalization_intervention_gate_SHA256':digest(root/'preflight_result.json')})


def run(root):
    if any((root/n).exists() for n in ('started.json','failure.json','execution_complete.json')):
        raise RuntimeError('existing_owner_do_not_restart')
    p=read(root/PLAN);gate_result=read(root/GATE)
    assert gate_result['status']=='PASS' and gate_result['plan_SHA256']==digest(root/PLAN)
    verify({**p['bindings'],**p['code']})
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=32);runtime=RuntimeLimit(root,7200)
    network=enforce_local_network_only();torch.set_num_threads(1);began=time.perf_counter()
    durable_json(root/'started.json',{'PID':os.getpid(),'parent_PID':os.getppid(),'KST':datetime.now().astimezone().isoformat(),
        'unix':time.time(),'plan_SHA256':digest(root/PLAN),'automatic_restarts':0})
    try:
        native=read(p['runtime_manifest']);runtime_bindings={str(Path(native['root'])/f):h for f,h in native['files'].items()}
        verify(runtime_bindings);verify(read(p['preservation_registry']))
        parent=LearnedPolicy(p['parent']['path'],p['catalog'],expected_model_id=p['parent']['sha256'])
        actors={'Foundation':parent,**{n:ResidualActor(b['path'],p['catalog']) for n,b in p['controls'].items()}}
        for rep,seed in enumerate(p['training_seeds'],1):
            actors[f'An_s{rep}']=train_arm(root,p,f'An_s{rep}',seed,parent,runtime,implementation=impl)
        evaluate_models(root,p,actors,runtime)
        verify({**p['bindings'],**p['code']});verify(read(p['preservation_registry']));verify(runtime_bindings)
        durable_json(root/'owner_resources.json',{'seconds':time.perf_counter()-began,'resources':job.usage(),'network':network})
        durable_json(root/'owner_exit.json',{'status':'SUCCESS','unix':time.time(),'execution_complete':True})
    except BaseException:
        durable_json(root/'failure.json',{'status':'PARTIAL','trace':traceback.format_exc(),'automatic_retry':False,
            'seconds':time.perf_counter()-began,'resources':job.usage()})
        raise
    finally:runtime.finished.set()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','gate','run'))
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    {'prepare':prepare,'gate':gate,'run':run}[args.phase](args.output.resolve())
