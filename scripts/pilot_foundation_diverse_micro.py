"""Two fresh-rollout Foundation continuations and one frozen paired panel."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import subprocess
import time
import traceback
import numpy as np

from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learned_diverse_micro import (DIVERSE_VERSION, MODELS, SEEDS, CAP,
    team_keys, build_templates, evaluation_cases, validate_plan, paired_analysis)
from advisor.learned_selfplay_pilot import StartBudget
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def model_identity(actor):
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
    m=actor.model
    return {'path':str(actor.model_path) if hasattr(actor,'model_path') else None,
        'sha256':actor.model_id,'parameters':tensor_digest(m.policy.state_dict()),
        'Adam':optimizer_digest(m.policy),'Adam_step':optimizer_clock(m.policy),
        'num_timesteps':m.num_timesteps,'PPO_epoch_counter':m._n_updates}


def prior_plan_audit(directory):
    """Plans only, never read performance results to choose scenarios."""
    files={};known=set();seeds=set();errors=[]
    def visit(x):
        if isinstance(x,dict):
            ts=x.get('teams')
            if isinstance(ts,dict):
                for team in ts.values():
                    if isinstance(team,list) and len(team)==6 and all(isinstance(p,dict) and 'species'in p and 'moves'in p for p in team):
                        known.update(team_keys(team).values())
            if isinstance(x.get('seed'),list) and len(x['seed'])==4 and all(type(v)is int for v in x['seed']):
                seeds.add(tuple(x['seed']))
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    for folder in sorted(directory.glob('foundation*')):
        if not folder.is_dir() or 'sealed' in folder.name.lower():continue
        for p in sorted(folder.rglob('plan.json')):
            if 'sealed' in str(p).lower() or p.stat().st_size>20_000_000:continue
            try:
                value=read(p);visit(value);files[str(p)]=digest(p)
            except (ValueError,OSError) as e:errors.append({'path':str(p),'error':str(e)})
    return {'files':files,'known_team_keys':sorted(known),'native_seeds':sorted(seeds),
        'errors':errors,'scope':'available nonsealed foundation plan.json files only; not proof a previously unlisted team was never evaluated'}


def prepare(output, prior):
    import torch
    from advisor.learned_full_roster import load_bank, study_identity
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import optimizer_clock
    if output.exists():raise ValueError('existing_diverse_artifacts_inspect_do_not_overwrite')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!='ca6a49559f16dcaa08d368ba999a1c76a1d5c1c2':
        raise ValueError('diverse_baseline_HEAD_mismatch')
    torch.set_num_threads(1);enforce_local_network_only()
    old=read(prior/'plan.json');ref=old['frozen_reference'];end=read(prior/'endpoint.json')
    parent=LearnedPolicy(ref['path'],old['catalog'],expected_model_id=ref['sha256'])
    fixed=LearnedPolicy(end['path'],old['catalog'],expected_model_id=end['sha256'])
    actual=model_identity(parent);actual['path']=ref['path']
    for key in ('sha256','parameters','Adam'):
        if actual[key]!=ref[key]:raise ValueError('original_Foundation_identity:'+key)
    if optimizer_clock(parent.model.policy)!=32768 or optimizer_clock(fixed.model.policy)!=33280:
        raise ValueError('diverse_original_Adam_clock')
    m=parent.model
    settings={'n_steps':m.n_steps,'batch_size':m.batch_size,'n_epochs':m.n_epochs,'gamma':m.gamma,
        'gae_lambda':m.gae_lambda,'learning_rate':m.lr_schedule(1.),'ent_coef':m.ent_coef,
        'vf_coef':m.vf_coef,'clip_range':m.clip_range(1.),'max_grad_norm':m.max_grad_norm,
        'target_kl':m.target_kl,'zero_avoiding_beta':m.zero_avoiding_beta,
        'auxiliary':m.auxiliary_metadata()}
    if (type(m).__name__!='FoundationCombatPPO' or (m.n_steps,m.batch_size,m.n_epochs,m.n_envs)!=(128,128,4,4)
            or m.gamma!=1 or m.gae_lambda!=.95 or m.lr_schedule(1.)!=5e-5 or m.zero_avoiding_beta!=.001):
        raise ValueError('diverse_historical_PPO_settings')
    audit=prior_plan_audit(output.parent)
    excluded={v for t in old['templates'] for team in t['scenario']['teams'].values() for v in team_keys(team).values()}
    templates=build_templates(load_bank()['teams'],excluded)
    cs=evaluation_cases(templates)
    if any(tuple(c['scenario']['seed']) in set(map(tuple,audit['native_seeds'])) for c in cs):
        raise ValueError('diverse_prior_case_seed_overlap')
    # Copies load separately for both seeds; no parameters or Adam object shared.
    clone=LearnedPolicy(ref['path'],old['catalog'],expected_model_id=ref['sha256'])
    other=model_identity(clone);other['path']=ref['path']
    if actual!=other or any(a.data_ptr()==b.data_ptr() for a,b in zip(m.policy.parameters(),clone.model.policy.parameters())):
        raise ValueError('diverse_clone_or_Adam_identity')
    probes=[]
    for p in sorted((prior/'rollouts').glob('public_*.json'))[:16]:
        view=read(p)['observation'];raw=[]
        for player in (parent,clone):
            handle=player.model.policy.action_net.register_forward_pre_hook(lambda layer,args:raw.append(args[0].detach().cpu().numpy().copy()))
            try:player.infer(view)
            finally:handle.remove()
        a=parent.infer(view);b=clone.infer(view)
        probes.append({'path':str(p),'sha256':digest(p),
            'raw_logit_max_error':float(np.max(abs(raw[0]-raw[1]))),
            'probability_max_error':max(abs(x-y) for x,y in zip(a['action_probabilities'],b['action_probabilities'])),
            'value_error':abs(a['discounted_return_estimate']-b['discounted_return_estimate'])})
    if not probes or any(p['raw_logit_max_error']!=0 or p['probability_max_error']!=0 or p['value_error']!=0 for p in probes):
        raise ValueError('diverse_initial_policy_equivalence')
    sources=['advisor/learned_diverse_micro.py','scripts/pilot_foundation_diverse_micro.py',
        'advisor/learned_fixed_micro.py','scripts/pilot_foundation_fixed_micro.py',
        'advisor/learned_selfplay_pilot.py','advisor/learned_gym.py','advisor/learned_ppo_contract_audit.py',
        'advisor/learned_combat_foundation.py','advisor/learned_combat_v5_strategic_aux.py',
        'advisor/learned_combat_v5_strategic_policy.py','advisor/showdown_observation.py',
        'advisor/showdown_environment.py','tools/showdown_bridge/environment.cjs',
        'scripts/train_showdown_autonomous.py','scripts/evaluate_showdown_policy.py',
        'scripts/pilot_foundation_selfplay_exploration.py']
    original_files=[Path(ref['path']),Path(end['path']),prior/'plan.json',prior/'endpoint.json',prior/'closure.json',prior/'raw_preservation_manifest.json']
    original_files += [p.parent/n for p in [Path(ref['path']),Path(end['path'])] for n in ('model.json','encoder.json') if (p.parent/n).exists()]
    plan={'schema_version':DIVERSE_VERSION,'baseline_HEAD':'ca6a49559f16dcaa08d368ba999a1c76a1d5c1c2',
        'parent':actual,'fixed16K':{'path':end['path'],'sha256':end['sha256']},
        'catalog':old['catalog'],'checkout':old['checkout'],'bank_identity':study_identity(),
        'training_seeds':list(SEEDS),'seed':SEEDS[0],'micro_prior_transitions':0,'micro_budget':CAP,
        'templates':templates,'training_template_indices':[i for i,t in enumerate(templates) if t['scope']=='train'],
        'evaluation_cases':cs,'evaluation_games':2048,'models':list(MODELS),
        'opponents':['league_s0'],'opponent_weights':[1.],'opponent_mode':'frozen_Foundation_argmax',
        'workers':4,'CPU_percent':50,'memory_mib':8192,'device':'cpu','teacher_enabled':False,
        'PPO':settings,'training_source':'fresh current-seed on-policy rollouts only',
        'initialization':'each seed independently reloads original Foundation parameters and Adam; fresh native episodes and rollout RNG; not uninterrupted resume',
        'preview':'one deterministic ordered three per full roster, reciprocal owner directions; no learned preview',
        'partition_scope':'8 TRAIN pairs (16 full teams), 8 validation pairs (16 full teams); no shared complete teams or joint species/movesets; individual species/sets may recur; parent-unseen not claimed',
        'primary':'independent-team Diverse_A/B minus Foundation, plus equal-seed mean; compare Fixed16K on same panel',
        'selection':'fixed16384 endpoint; no case replacement, interim-win gate or validation-best choice',
        'uncertainty':'20000 team-pair clustered bootstrap, seed2026102809; keep directions/RNG/seats/models and both training repetitions together; only two training seeds',
        'decision':'signal if both independent deltas positive and combined cluster CI lower>0, no truncations; neither positive -> no observed transfer; otherwise inconclusive',
        'source_hashes':{p:digest(ROOT/p) for p in sources},
        'input_hashes':{str(p):digest(p) for p in original_files}}
    validate_plan(plan)
    output.mkdir(parents=True)
    durable_json(output/'prior_plan_audit.json',audit)
    known=set(audit['known_team_keys'])
    coverage=[]
    for t in templates[::2]:
        coverage.append({'pair':t['pair'],'scope':t['scope'],'partition':t['partition'],'indices':t['indices'],
            'previous_plan_team_match':[b['unordered'] in known for b in t['team_keys']],
            'species':[[p['species'] for p in team] for team in t['scenario']['teams'].values()],
            'selected_slots':t['scenario']['preview']})
    durable_json(output/'coverage.json',{'pairs':coverage,'prior_plan_files':len(audit['files']),
        'prior_plan_parse_errors':audit['errors'],'known_prior_team_matching_not_performance_selected':True,
        'initial_clone_equivalence':probes,'parameters':sum(p.numel() for p in m.policy.parameters()),
        'native_validation_authority':'maintained load_bank hash-bound V8 native-valid team bank; no new generator or legality approximation',
        'prior_micro_full_team_overlap':0,'prior_native_evaluation_seed_overlap':0})
    durable_json(output/'plan.json',plan)
    for i,name in enumerate(('seed_A','seed_B')):
        directory=output/name;directory.mkdir()
        durable_json(directory/'plan.json',{**plan,'seed':SEEDS[i]})
    durable_json(output/'freeze.json',{'frozen_at_UTC':datetime.now(timezone.utc).isoformat(),
        'files':{str(p.relative_to(output)):digest(p) for p in output.rglob('*.json')},
        'PPO_cap':32768,'Adam_cap':1024,'evaluation_start_cap':2048,'new_native_prechecks':0})
    print(json.dumps({'prepared':str(output),'plan_SHA256':digest(output/'plan.json'),
        'train_pairs':8,'independent_pairs':8,'PPO_cap':32768,'evaluation_cap':2048}),flush=True)


def verify(root):
    plan=read(root/'plan.json');validate_plan(plan)
    for f,h in read(root/'freeze.json')['files'].items():
        if digest(root/f)!=h:raise ValueError('diverse_frozen_artifact_changed:'+f)
    hashes=deepcopy(plan['source_hashes'])
    revision=root/'execution_revision_02.json'
    if revision.exists():
        r=read(revision)
        path='scripts/pilot_foundation_diverse_micro.py'
        if (r['schema_version']!='diverse-micro-detached-nested-job-proof-v1'
                or r['parent_plan_SHA256']!=digest(root/'plan.json')
                or r['original_runner_SHA256']!=hashes[path]
                or r['source_hashes'].keys()!={path}
                or r['scientific_changes']!=[] or r['prior_native_starts']!=0
                or r['prior_optimizer_updates']!=0
                or digest(root/'persistence_probe_result.json')!=r['persistence_probe_SHA256']
                or read(root/'persistence_probe_result.json')['phase']!='survived_launcher_exit'):
            raise ValueError('diverse_detached_operational_revision')
        hashes.update(r['source_hashes'])
    for f,h in hashes.items():
        if digest(ROOT/f)!=h:raise ValueError('diverse_source_changed:'+f)
    for f,h in plan['input_hashes'].items():
        if digest(f)!=h:raise ValueError('diverse_original_changed:'+f)
    return plan


def eval_panel(root,plan,players,parent,runtime):
    from scripts.evaluate_showdown_policy import evaluate
    from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases, persist_evaluation_batch
    from advisor.learned_fixed_micro import EpisodeRival
    from advisor.learned_difficulty_calibration import PublicRetryAudit
    from advisor.learned_response_predictor import public_input
    budget=StartBudget(root/'EVAL_starts',2048,root/'STOP');directory=root/'evaluation';directory.mkdir()
    lookup={c['index']:c for c in plan['evaluation_cases']};p_sha=digest(root/'plan.json')
    bindings={k:{'sha256':v.model_id} for k,v in players.items()}
    started=time.perf_counter()
    for name,actor in players.items():
        for seat in ('p1','p2'):
            side='self' if seat=='p1' else 'opponent'
            for offset in range(0,256,32):
                provider=FrozenEvalCases(lookup,budget,name,'league_s0',seat,p_sha)
                rival=EpisodeRival('league_s0',parent);rival.reset(0)
                monitor=[None,None];first=set()
                def observer(event):
                    v=event['before'][side];public_input(v)
                    if monitor[0]!=v['episode_id']:monitor[:]=[v['episode_id'],PublicRetryAudit(v['episode_id'])]
                    monitor[1].observe(event)
                    if name=='Foundation' and v['episode_id'] not in first:
                        first.add(v['episode_id']);p=root/'evaluation_roots'/f'{offset+len(first)-1}_{seat}.json'
                        p.parent.mkdir(exist_ok=True)
                        durable_json(p,{'view':v,'case':offset+len(first)-1,'seat':seat})
                def progress(rows):
                    persist_evaluation_batch(directory,rows,bindings,lookup,name,'league_s0',seat,p_sha)
                    n=len(list(directory.glob('*.receipt.json')))
                    atomic_json(root/'evaluation_progress.json',{'policy':name,'seat':seat,'valid':n,
                        'starts':budget.count,'target':2048,'seconds':time.perf_counter()-started,
                        'games_per_second':n/(time.perf_counter()-started),'unix':time.time()})
                evaluate(plan['checkout'],plan['catalog'],{name:actor},cases=32,offset=offset,
                    curriculum_version='showdown-learning-curriculum-v8',rivals={'league_s0':rival},
                    candidate_seat=seat,case_provider=provider,stopping=runtime.stopping,
                    tactical_diagnostics=True,integrated_diagnostics=True,transition_observer=observer,
                    per_game_progress=True,progress=progress)
    if budget.count!=2048:raise ValueError('diverse_evaluation_start_total')


def run(root):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from scripts.pilot_foundation_fixed_micro import train
    if (root/'started.json').exists() or (root/'completion.json').exists():
        raise ValueError('diverse_already_started_inspect_do_not_duplicate')
    plan=verify(root)
    job=WindowsJob(memory_mib=8192,cpu_percent=50,active_process_limit=32)
    # A persistent outer desktop Job can remain after breakaway from the
    # short-lived tool Job. Do not confuse its presence with tool lifetime.
    # Require the actual detached-child survival proof before accepting it;
    # our own nested Job still enforces CPU/RAM and child-tree containment.
    if job.inherited_job and not (root/'execution_revision_02.json').exists():
        raise ValueError('diverse_requires_verified_detached_job_owner')
    runtime=RuntimeLimit(root,3600);start=time.perf_counter()
    torch.set_num_threads(1);network=enforce_local_network_only()
    durable_json(root/'started.json',{'PID':os.getpid(),'parent_PID':os.getppid(),'unix':time.time(),
        'inherited_job':job.inherited_job,'own_bounded_job':True,
        'execution_revision_SHA256':digest(root/'execution_revision_02.json') if (root/'execution_revision_02.json').exists() else None,
        'plan_SHA256':digest(root/'plan.json'),'workers':4,'CPU_percent':50,'RAM_mib':8192})
    try:
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
        original=model_identity(parent);bindings={'Foundation':plan['parent'],'Fixed16K':plan['fixed16K']}
        for folder,name in (('seed_A','Diverse_A'),('seed_B','Diverse_B')):
            phase=time.perf_counter();actor=train(read(root/folder/'plan.json'),root/folder,parent,runtime)
            end=read(root/folder/'endpoint.json')
            if end['new_transitions']!=16384 or end['new_Adam']>512:raise ValueError('diverse_training_budget')
            if end['initial_Adam_identity']!=plan['parent']['Adam']:raise ValueError('diverse_restored_Adam')
            bindings[name]={'path':end['path'],'sha256':end['sha256']}
            durable_json(root/folder/'timing.json',{'seconds':time.perf_counter()-phase,
                'transitions_per_second':16384/(time.perf_counter()-phase),'resources':job.usage()})
        durable_json(root/'evaluation_bindings.json',bindings)
        players={k:parent if k=='Foundation' else LearnedPolicy(b['path'],plan['catalog'],expected_model_id=b['sha256']) for k,b in bindings.items()}
        before={k:model_identity(v) for k,v in players.items()}
        eval_start=time.perf_counter();eval_panel(root,plan,players,parent,runtime)
        after={k:model_identity(v) for k,v in players.items()}
        if before!=after or model_identity(parent)!=original:raise ValueError('diverse_evaluation_model_or_Adam_mutation')
        rows=[read(p) for p in (root/'evaluation').glob('*.receipt.json')]
        analysis=paired_analysis(rows,plan['evaluation_cases']);durable_json(root/'analysis.json',analysis)
        verify(root)
        durable_json(root/'completion.json',{'status':'COMPLETE','verdict':analysis['verdict'],
            'PPO_transitions':32768,'new_Adam':sum(read(root/f/'endpoint.json')['new_Adam'] for f in ('seed_A','seed_B')),
            'evaluation_games':len(rows),'evaluation_starts':len(list((root/'EVAL_starts').glob('start_*.json'))),
            'evaluation_seconds':time.perf_counter()-eval_start,'wall_seconds':time.perf_counter()-start,
            'resources':job.usage(),'evaluation_model_Adam_before':before,'evaluation_model_Adam_after':after,
            'network':network,'no_promotion':True})
        print(json.dumps({'complete':analysis['verdict'],'seconds':time.perf_counter()-start}),flush=True)
    except BaseException as e:
        atomic_json(root/'failure.json',{'type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),
            'wall_seconds':time.perf_counter()-start,'resources':job.usage()});raise
    finally:runtime.finished.set()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--prior',type=Path);a=p.parse_args()
    prepare(a.output,a.prior) if a.mode=='prepare' else run(a.output)
