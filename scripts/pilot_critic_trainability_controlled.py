"""Two authorized critic-trainable arms, then one frozen 6400-game comparison."""
from pathlib import Path
import sys
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import gzip
import hashlib
import json
import os
import time
import traceback

import numpy as np
import torch

from advisor.experimental_critic_training import (
    VERSION, EXTRA, allowed, contract, initialize, validate_model, frozen_digest,
    save, CriticTrainableActor, CriticSignalRecorder,
)
from advisor.experimental_context_training import ResidualActor, TrainCases, initialize as initialize_A
from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_policy import LearnedPolicy
from advisor.learned_fixed_micro import seed4, EpisodeRival
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only

BASELINE = '6fe7e7daedce04c711f44ba4ec8e52f2be289261'
PLAN = 'plan_revision_02.json'
VALIDATION = 'TRAIN_validation_revision_02.json'
MODELS = ('Foundation', 'A_s1', 'A_s2', 'Aprime_s1', 'Aprime_s2')
ART = Path.home() / '.codex/artifacts'
OLD = ART / 'experimental-candidate-context-controlled-train-pilot-v1-20261105/study'
OWNED = ['advisor/experimental_critic_training.py', 'advisor/learned_frozen_evaluation_trace.py',
         'scripts/pilot_critic_trainability_controlled.py', 'tests/test_experimental_critic_training.py',
         'docs/experimental_critic_trainability.md']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(bindings):
    for path, expected in bindings.items():
        if any(v in str(path).replace('\\', '/').lower() for v in (
                'config/env.example', 'config/.env', 'logs/token_usage.jsonl', 'docs/handoff_capsule_v1.1.md')):
            raise ValueError('protected_file_not_an_input')
        if digest(path) != expected:
            raise ValueError('frozen_binding_changed:' + str(path))


def cases_for(teams):
    rows = []
    for pair in range(80):
        previews = [(np.random.default_rng(seed4(f'{VERSION}:preview:{pair}:{s}')).permutation(6)[:3]+1).tolist()
                    for s in range(2)]
        for direction in (0, 1):
            for rep in range(4):
                index = len(rows); own, other = direction, 1-direction
                scenario = {'scenario_id': f'{VERSION}:DEV:{index}',
                    'teams': {'self': deepcopy(teams[2*pair+own]), 'opponent': deepcopy(teams[2*pair+other])},
                    'preview': {'self': previews[own], 'opponent': previews[other]},
                    'seed': seed4(f'{VERSION}:DEV:{index}'), 'history': [],
                    'assumptions': ['T1-admitted TRAIN-domain development source; not sealed; fixed ordered three.']}
                rows.append({'index': index, 'pair': pair, 'direction': direction, 'replicate': rep,
                    'rival': 'league_s0', 'scenario': scenario, 'scenario_sha256': content_hash(scenario)})
    return rows


def prepare(root):
    if (root/PLAN).exists():
        raise RuntimeError('existing_plan_do_not_replace')
    ready = read(root/'source_ready.json'); assert ready['status'] == 'SOURCE_READY'
    assert digest(root/'source_manifest.json') == ready['manifest_SHA256']
    source = read(root/'source_manifest.json')
    verify({str(root/a['path']): a['sha256'] for a in source['assets'].values()})
    verify(source['source_bindings'])
    teams = read(root/'teams.json')['teams']; assert len(teams) == 160 and len(source['pairs']) == 80
    prior = read(OLD/'plan.json'); bindings = {str(OLD/'plan.json'): digest(OLD/'plan.json')}
    # Public-only, never optimized frozen-policy TRAIN captures. No native/private snapshots are read.
    capture = ART/'foundation-decision-snapshot-counterfactual-pilot-v1-20261025/run/capture'
    old_completion = read(capture.parent.parent/'completion.json')
    assert old_completion['new_trained_PPO_transitions'] == old_completion['optimizer_updates'] == 0
    from advisor.learned_combat_foundation import FoundationCombatEncoder
    encoder = FoundationCombatEncoder(prior['catalog'])
    validation, exclusions = [], []
    for root_record in read(capture/'capture_manifest.json')['roots']:
        public_path = capture/'public'/(root_record['id']+'.json')
        join_path = capture/'joins'/(root_record['id']+'.json')
        public, joined = read(public_path), read(join_path)
        if public['policy_id'] != prior['parent']['sha256'] or not joined['joined']:
            raise ValueError('TRAIN_validation_provenance')
        current = hashlib.sha256(encoder.encode(public['observation']).tobytes()).hexdigest()
        if current != joined['observation_sha256']:
            exclusions.append({'id':joined['id'],'reason':'public_transport_no_longer_reproduces_captured_features',
                'recorded_feature_SHA256':joined['observation_sha256'],'current_feature_SHA256':current})
            continue
        validation.append({'id': joined['id'], 'observation': public['observation'],
            'feature_SHA256': joined['observation_sha256'], 'GAE_target': joined['return_target'],
            'recorded_value': joined['value'], 'episode': joined['episode_id'],
            'label_scope': 'retained_frozen_policy_GAE_target_not_terminal_truth_or_optimal_action'})
        bindings[str(public_path)], bindings[str(join_path)] = digest(public_path), digest(join_path)
    assert len(validation) == 15 and len(exclusions) == 1
    bindings[str(capture/'capture_manifest.json')] = digest(capture/'capture_manifest.json')
    bindings[str(capture.parent.parent/'completion.json')] = digest(capture.parent.parent/'completion.json')
    durable_json(root/VALIDATION, validation)
    durable_json(root/'TRAIN_validation_exclusions_revision_02.json', exclusions)
    # Existing frozen cases from revision 01 remain byte-identical.
    if (root/'cases.json').exists():
        assert read(root/'cases.json') == cases_for(teams)
    else:
        durable_json(root/'cases.json', cases_for(teams))
    controls = {}
    for rep in (1, 2):
        end = read(OLD/f'A_s{rep}/endpoint.json')
        assert (end['new_transitions'], end['new_Adam'], end['train_seed']) == (16384, 512, (116051,116053)[rep-1])
        controls[f'A_s{rep}'] = {'path': end['path'], 'sha256': end['sha256']}
        for p in (Path(end['path']), Path(end['path']).parent/'residual_metadata.json', OLD/f'A_s{rep}/endpoint.json'):
            bindings[str(p)] = digest(p)
        first = next((OLD/f'A_s{rep}/rollouts').glob('rollout_1049088_*.audit.npz'))
        controls[f'A_s{rep}']['first_rollout'] = str(first)
        bindings[str(first)] = digest(first)
    registry = ART/'candidate-context-frozen-development-replication-v1-20261105/preserved_file_bindings.json'
    verify(read(registry)); bindings[str(registry)] = digest(registry)
    for p in (root/'source_manifest.json', root/VALIDATION, root/'TRAIN_validation_exclusions_revision_02.json',
              root/'cases.json', Path(prior['parent']['path']),
              Path(prior['parent']['path']).with_suffix('.json'), Path(prior['catalog']), Path(prior['runtime_manifest'])):
        bindings[str(p)] = digest(p)
    old_seeds = {tuple(s) for s in prior['excluded_native_seeds']}
    old_seeds.update(tuple(c['scenario']['seed']) for c in prior['development_cases'])
    # Previous Q_dev_new identity metadata only, never results.
    old_cases = read(ART/'candidate-context-q-dev-new-frozen-policy-evaluation-v1-20261106/cases.json')
    old_seeds.update(tuple(c['scenario']['seed']) for c in old_cases)
    cases = read(root/'cases.json')
    assert not {tuple(c['scenario']['seed']) for c in cases} & old_seeds
    assert len({tuple(c['scenario']['seed']) for c in cases}) == 640
    code = {str(REPO/p): digest(REPO/p) for p in OWNED}
    for folder, pattern in [('advisor','learned*.py'), ('advisor','showdown*.py'), ('tools/showdown_bridge','*.cjs')]:
        code.update({str(p): digest(p) for p in (REPO/folder).glob(pattern)})
    for p in ('advisor/experimental_context_training.py','scripts/train_showdown_autonomous.py',
              'scripts/evaluate_showdown_policy.py','scripts/pilot_foundation_selfplay_exploration.py'):
        code[str(REPO/p)] = digest(REPO/p)
    plan = {'version': VERSION, 'baseline_HEAD': BASELINE, 'frozen_KST': datetime.now().astimezone().isoformat(),
        'training_seeds': [116051,116053], 'arm_order': ['Aprime_s1','Aprime_s2'],
        'control_retraining': 0, 'training_plan': str(OLD/'plan.json'), 'parent': prior['parent'],
        'controls': controls, 'catalog': prior['catalog'], 'checkout': prior['checkout'],
        'runtime_manifest': prior['runtime_manifest'], 'preservation_registry': str(registry),
        'trainable_contract': contract(), 'resources': {'CPU_percent':50,'memory_mib':12288,'workers':4,'GPU':False},
        'new_transitions':32768,'new_Adam':1024,'per_arm_transitions':16384,'per_arm_Adam':512,
        'new_evaluation_starts':6400,'games_per_model':1280,'team_pairs':80,
        'evaluation': {'rival':'frozen Foundation argmax','candidate':'T=1 argmax',
            'owners':2,'RNG':4,'seats':['p1','p2'],'endpoint':'fixed_final16384_only',
            'seed_namespace':VERSION,'first_actions_and_executions':'Trace_v1'},
        'analysis': {'primary':'Aprime_minus_A_terminal_return_two_seed_mean','clusters':80,
            'bootstrap_seed':116063,'draws':20000,'decision':'lower95CI>0: CONTROLLED_EXPERIMENT_COMPLETE with development signal; otherwise DEVELOPMENT_SIGNAL_NOT_CONFIRMED',
            'training_seed_uncertainty':'two repetitions only; not estimated by treating them as extra team pairs'},
        'TRAIN_validation': {'rows':len(validation),'episodes':len({v['episode'] for v in validation}),
            'unused':'never consumed by PPO optimizer; old frozen TRAIN diagnostic captures, previously inspected, not a new sealed panel',
            'target':'recorded frozen-policy GAE targets, not true state value or action labels',
            'common_input':'same 15 exact-feature public inputs for Foundation/A/Aprime and every fixed checkpoint; 1 nonreproducing historical transport excluded before training',
            'limitations':'small and previously diagnosed; evaluation-visited terminal MSE is separate and policy-dependent'},
        'bindings':bindings,'code':code,'automatic_restarts':0,'wall_seconds':7200,'promotion':False}
    plan['pre_execution_revision']={'revision':2,'parent_plan':str(root/'plan.json'),
        'parent_plan_SHA256':digest(root/'plan.json'),
        'reason':'exclude one historical TRAIN validation public transport with mismatched feature SHA; no native or optimizer executed; source/cases/model/PPO/budgets unchanged'}
    durable_json(root/PLAN,plan)


def outputs(policy, x, masks):
    with torch.no_grad():
        logits = policy.mlp_extractor.forward_actor(x)
        distribution = policy.get_distribution(x, action_masks=masks)
        return logits.cpu(), distribution.distribution.probs.cpu(), policy.predict_values(x).flatten().cpu()


def validation_metrics(actor, rows, parent=None):
    x = np.stack([actor.encoder.encode(r['observation']) for r in rows])
    for a, r in zip(x, rows):
        if hashlib.sha256(a.tobytes()).hexdigest() != r['feature_SHA256']:
            raise ValueError('TRAIN_validation_public_features_changed')
    masks = np.array([r['observation']['action_mask'] for r in rows], bool)
    z,p,v = outputs(actor.model.policy, torch.tensor(x), masks)
    targets = np.array([r['GAE_target'] for r in rows])
    result = {'rows':len(rows),'GAE_target_MSE':float(np.mean((v.numpy()-targets)**2)),
        'values':v.tolist(),'argmax':p.argmax(1).tolist(),'label_scope':'retained_frozen_policy_GAE_not_terminal_truth'}
    if parent is not None:
        zz,pp,vv = outputs(parent.model.policy, torch.tensor(x), masks)
        result.update(max_probability_delta=float((p-pp).abs().max()), argmax_changes=int((p.argmax(1)!=pp.argmax(1)).sum()),
            parent_to_child_KL=float((pp*(pp.clamp(min=1e-30).log()-p.clamp(min=1e-30).log())).sum(1).mean()),
            max_value_change=float((v-vv).abs().max()))
    return result


def gate(root):
    plan=read(root/PLAN);verify({**plan['bindings'],**plan['code']})
    torch.set_num_threads(1)
    parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
    rows=read(root/VALIDATION);x=torch.tensor(np.stack([parent.encoder.encode(r['observation']) for r in rows]))
    masks=np.array([r['observation']['action_mask'] for r in rows],bool)
    A=initialize_A(parent.model,'set');new=initialize(parent.model)
    for left,right in zip(outputs(A.policy,x,masks),outputs(new.policy,x,masks)):
        if not torch.equal(left,right):raise ValueError('initial_A_Aprime_outputs_not_bit_identical')
    if A.policy.optimizer.defaults != new.policy.optimizer.defaults or A.policy.optimizer.state or new.policy.optimizer.state:
        raise ValueError('fresh_Adam_defaults_mismatch')
    assert tensor_digest(A.policy.state_dict()) == tensor_digest(new.policy.state_dict())
    before=(tensor_digest(parent.model.policy.state_dict()),optimizer_digest(parent.model.policy))
    saved=save(new,parent.encoder,root/'initial_parent_revision_02',{'new_transitions':0,'new_Adam':0,'plan_SHA256':digest(root/PLAN)})
    restored=CriticTrainableActor(saved,plan['catalog'])
    assert optimizer_digest(restored.model.policy)==optimizer_digest(new.policy)
    trainable={n:p.numel() for n,p in new.policy.named_parameters() if p.requires_grad}
    durable_json(root/'offline_gate.json',{'status':'PASS','plan_SHA256':digest(root/PLAN),
        'initial_outputs':'BIT_IDENTICAL_logits_probabilities_value_argmax_masks',
        'initial_weights_identical':True,'fresh_Adam':True,'optimizer_defaults':str(new.policy.optimizer.defaults),
        'critic_trainable_names':trainable,'trainable_parameters':sum(trainable.values()),
        'residual_parameters':sum(v for n,v in trainable.items() if n in EXTRA),
        'parent_preserved':before==(tensor_digest(parent.model.policy.state_dict()),optimizer_digest(parent.model.policy)),
        'validation':validation_metrics(parent,rows),'native_battles':0,'optimizer_updates':0})


def train_arm(root,plan,label,seed,parent,runtime,*,implementation=None):
    from advisor.learned_fixed_micro import training_vector
    from advisor.learned_selfplay_pilot import StartBudget
    from scripts.train_showdown_autonomous import BudgetCallback,require_finite_ppo
    if implementation is not None:
        initialize,validate_model,frozen_digest,save,allowed,loader,recorder_type = (
            implementation.initialize,implementation.validate_model,implementation.frozen_digest,
            implementation.save,implementation.allowed,implementation.Actor,implementation.Recorder)
    else:
        from advisor.experimental_critic_training import (
            initialize,validate_model,frozen_digest,save,allowed,CriticTrainableActor as loader,
            CriticSignalRecorder as recorder_type)
    plan_file=plan.get('plan_file',PLAN);prefix=plan.get('treatment_prefix','Aprime')
    old=read(plan['training_plan']);folder=root/label;folder.mkdir()
    adapter = (implementation.training_adapter(old['runtime_adapter'], seed, parent.model_id)
               if implementation is not None and hasattr(implementation, 'training_adapter')
               else old['runtime_adapter'])
    model=initialize(parent.model);fixed=frozen_digest(model.policy);start=model.num_timesteps
    budget=StartBudget(folder/'TRAIN_starts',4096,root/'STOP');(folder/'Adam_intents').mkdir()
    updates=0;previous={};segments=[];began=time.perf_counter();raw={}
    log=(folder/'optimizer_updates.jsonl').open('x',encoding='utf-8')
    def grad_hook(name):
        def capture(g):
            raw[name]=float(g.detach().square().sum())
            return g
        return capture
    hooks=[p.register_hook(grad_hook(n)) for n,p in model.policy.named_parameters() if p.requires_grad]
    def before_step(optimizer,args,kwargs):
        nonlocal updates,previous
        validate_model(model,fixed)
        if updates>=512 or optimizer_clock(model.policy)!=updates:raise RuntimeError('critic_Adam_cap_or_clock')
        previous={n:p.detach().clone() for n,p in model.policy.named_parameters() if allowed(n)}
        durable_json(folder/'Adam_intents'/f'{updates:04d}.json',{'index':updates,'before':optimizer_clock(model.policy)})
        updates+=1
    def after_step(optimizer,args,kwargs):
        validate_model(model,fixed)
        if optimizer_clock(model.policy)!=updates:raise ValueError('critic_Adam_not_advanced')
        row={'step':updates,'frozen_SHA256':fixed,'groups':{}}
        for group,accept in [('residual_actor',lambda n:n in EXTRA),('critic_only',lambda n:allowed(n) and n not in EXTRA)]:
            parameters=[(n,p) for n,p in model.policy.named_parameters() if accept(n)]
            row['groups'][group]={'raw_gradient_L2':sum(v for n,v in raw.items() if accept(n))**.5,
                'clipped_gradient_L2':sum(float(p.grad.square().sum()) for n,p in parameters if p.grad is not None)**.5,
                'parameter_delta_L2':sum(float((p.detach()-previous[n]).square().sum()) for n,p in parameters)**.5}
        log.write(json.dumps(row,allow_nan=False)+'\n');log.flush();raw.clear()
    hooks += [model.policy.optimizer.register_step_pre_hook(before_step),model.policy.optimizer.register_step_post_hook(after_step)]
    last=None
    try:
        for segment in range(16):
            if runtime.stopping():raise RuntimeError('critic_STOP_or_deadline')
            verify({str(root/plan_file):read(root/'started.json')['plan_SHA256']})
            sr=folder/'segments'/f'{segment:02d}';sr.mkdir(parents=True)
            vector,_=training_vector(adapter,sr,parent,
                case_factory=lambda worker:TrainCases(old,seed,segment,worker),start_budget=budget)
            reference=plan['controls'][label.replace(prefix,'A')]['first_rollout']
            recorder=recorder_type(folder/'rollouts',parent.encoder,reference)
            callback=BudgetCallback(runtime,collect_diagnostics=True,signal_recorder=recorder)
            model.set_env(vector,force_reset=True)
            if segment==0:model.set_random_seed(seed)
            before=model.num_timesteps
            try:
                model.learn(total_timesteps=1024,reset_num_timesteps=False,callback=callback)
                require_finite_ppo(model,rollout=True)
                if model.num_timesteps-before!=1024:raise ValueError('critic_transition_accounting')
                completed=[e for batch in vector.env_method('drain_completed') for e in batch]
                record={'segment':segment,'new_collected':model.num_timesteps-start,'new_Adam':updates,
                    'completed':completed,'slots':[(segment*4+w)%16 for w in range(4)],'transitions_per_slot':256,
                    'metrics':{k:float(v) for k,v in model.logger.name_to_value.items() if isinstance(v,(int,float,np.number)) and np.isfinite(v)},
                    'tactical_counts':vector.env_method('drain_tactical_counts'),
                    'public_counts':vector.env_method('drain_public_behavior_counts'),'callback':callback.measurements}
            finally:
                recorder.close();vector.close()
            validate_model(model,fixed)
            if optimizer_digest(parent.model.policy)!=plan['parent']['Adam']:raise ValueError('Foundation_Adam_changed')
            audits=[read(p) for p in (folder/'rollouts').glob('*.audit.json')]
            if len(audits)!=(segment+1)*2 or updates!=(segment+1)*32:raise ValueError('critic_rollout_or_Adam_quota')
            identities=list((sr/'native_training').glob('worker_*/identity_*.json'))
            if len(identities)<8:raise ValueError('critic_native_training_identities_missing')
            for p in identities:
                identity=read(p);episode=identity['episode_identity']
                template=old['training_templates'][(segment*4+identity['worker'])%16]['scenario']
                if (episode['team_sha256']!={s:content_hash(template['teams'][s]) for s in ('self','opponent')}
                        or episode['opponent_model_id']!=plan['parent']['sha256']):
                    raise ValueError('critic_training_exposure_or_opponent_changed')
                if implementation is not None and hasattr(implementation, 'verify_training_identity'):
                    implementation.verify_training_identity(identity, seed, parent.model_id)
                elif identity['opponent_mode']!='argmax':
                    raise ValueError('critic_training_exposure_or_opponent_changed')
            record['verified_native_roster_identities']=len(identities);segments.append(record)
            if (segment+1)%4==0:
                last=save(model,parent.encoder,folder/f'checkpoint_{model.num_timesteps-start}',
                    {'plan_SHA256':digest(root/plan_file),'new_collected':model.num_timesteps-start,
                     'new_trained':len(audits)*512,'new_Adam':updates,'seed':seed})
                check=loader(last,plan['catalog'])
                assert tensor_digest(check.model.policy.state_dict())==tensor_digest(model.policy.state_dict())
                assert optimizer_digest(check.model.policy)==optimizer_digest(model.policy)
                if plan.get('TRAIN_validation_enabled',True):
                    durable_json(folder/f'validation_{model.num_timesteps-start}.json',
                        validation_metrics(check,read(root/VALIDATION),parent))
            atomic_json(folder/'training_progress.json',{'segments':segments,'latest':last,
                'new_collected':model.num_timesteps-start,'new_trained':len(audits)*512,'new_Adam':updates,'starts':budget.count})
            elapsed=time.perf_counter()-began
            atomic_json(root/'progress.json',{'phase':'training','arm':label,'arm_transitions':model.num_timesteps-start,
                'completed_arms':len(list(root.glob(f'{prefix}_s*/endpoint.json'))),'seconds':elapsed,
                'transitions_per_second':(model.num_timesteps-start)/elapsed,'unix':time.time()})
        if updates!=512 or model.num_timesteps-start!=16384:raise ValueError('critic_endpoint_budget')
        actor=loader(last,plan['catalog'])
        durable_json(folder/'endpoint.json',{'path':last,'sha256':actor.model_id,'new_transitions':16384,'new_Adam':updates,
            'frozen_SHA256':fixed,'optimizer_SHA256':optimizer_digest(model.policy),'TRAIN_starts':budget.count,
            'completed_native_battles':sum(len(s['completed']) for s in segments),'seed':seed,'seconds':time.perf_counter()-began})
        return actor
    except BaseException:
        validate_model(model,fixed)
        save(model,parent.encoder,folder/'partial_checkpoint',{'status':'PARTIAL','new_collected':model.num_timesteps-start,
            'new_trained':512*len(list((folder/'rollouts').glob('*.audit.json'))),'new_Adam_intents':updates})
        raise
    finally:
        for h in hooks:h.remove()
        log.flush();os.fsync(log.fileno());log.close()


def analyze(rows,cases,draws=20000,seed=116063,*,treatment_prefix='Aprime'):
    models=('Foundation','A_s1','A_s2',f'{treatment_prefix}_s1',f'{treatment_prefix}_s2')
    by={(r['policy'],r['case'],r['seat']):r['record'] for r in rows}
    expected={(m,c['index'],s) for m in models for c in cases for s in ('p1','p2')}
    if len(rows)!=len(expected) or set(by)!=expected:raise ValueError('critic_evaluation_missing_or_duplicate')
    if any(r['truncated'] or r['native_choice_rejections'] for r in by.values()):raise ValueError('critic_invalid_native_result')
    pairs=sorted({c['pair'] for c in cases});rng=np.random.default_rng(seed)
    indices=rng.integers(0,len(pairs),(draws,len(pairs)));means={};wins={};outcomes={}
    for m in models:
        rr=[by[m,c['index'],s] for c in cases for s in ('p1','p2')]
        value_errors=[r['value_discounted_return_mse'] for r in rr if r['value_discounted_return_mse'] is not None]
        outcomes[m]={'games':len(rr),'wins':sum(r['winner']=='self' for r in rr),
            'losses':sum(r['winner']=='opponent' for r in rr),'draws':sum(r['winner'] is None for r in rr),
            'visited_state_terminal_value_MSE':float(np.mean(value_errors)) if value_errors else None}
        means[m]=np.array([np.mean([by[m,c['index'],s]['return'] for c in cases if c['pair']==p for s in ('p1','p2')]) for p in pairs])
        wins[m]=np.array([np.mean([by[m,c['index'],s]['winner']=='self' for c in cases if c['pair']==p for s in ('p1','p2')]) for p in pairs])
    differences=[means[f'{treatment_prefix}_s{i}']-means[f'A_s{i}'] for i in (1,2)]
    win_differences=[wins[f'{treatment_prefix}_s{i}']-wins[f'A_s{i}'] for i in (1,2)]
    contrasts={}
    for name,d,w in [('s1',differences[0],win_differences[0]),('s2',differences[1],win_differences[1]),
                      ('two_seed_mean',np.mean(differences,axis=0),np.mean(win_differences,axis=0))]:
        contrasts[name]={f'{treatment_prefix}_minus_A_terminal_return':float(d.mean()),'cluster95CI':np.quantile(d[indices].mean(1),[.025,.975]).tolist(),
            'win_fraction_difference':float(w.mean()),'win_cluster95CI':np.quantile(w[indices].mean(1),[.025,.975]).tolist(),
            'pair_differences':d.tolist()}
    foundation={}
    for m in models[1:]:
        d=means[m]-means['Foundation'];w=wins[m]-wins['Foundation']
        parent_rows=[(by['Foundation',c['index'],s],by[m,c['index'],s]) for c in cases for s in ('p1','p2')]
        foundation[m]={'return_difference':float(d.mean()),'cluster95CI':np.quantile(d[indices].mean(1),[.025,.975]).tolist(),
            'win_difference':float(w.mean()),'win_cluster95CI':np.quantile(w[indices].mean(1),[.025,.975]).tolist(),
            'parent_win_retained':sum(a['winner']=='self' and b['winner']=='self' for a,b in parent_rows),
            'parent_win_lost':sum(a['winner']=='self' and b['winner']!='self' for a,b in parent_rows),
            'parent_loss_to_child_win':sum(a['winner']=='opponent' and b['winner']=='self' for a,b in parent_rows)}
    primary=contrasts['two_seed_mean']['cluster95CI']
    return {'outcomes':outcomes,'comparisons':contrasts,'Foundation_contrasts':foundation,
        'team_pair_clusters':len(pairs),'verdict':'CONTROLLED_EXPERIMENT_COMPLETE' if primary[0]>0 else 'DEVELOPMENT_SIGNAL_NOT_CONFIRMED',
        'uncertainty':'clustered evaluation-case interval conditional on two trained repetitions, not seed-population uncertainty',
        'value_MSE_limit':'visited states differ by policy; GAE validation and terminal evaluation MSE are distinct'}


def evaluate_models(root,plan,actors,runtime):
    from advisor.learned_frozen_evaluation_trace import Trace,Provider
    from advisor.learned_selfplay_pilot import StartBudget
    from scripts.pilot_foundation_selfplay_exploration import persist_evaluation_batch
    from scripts.evaluate_showdown_policy import evaluate
    directory=root/'evaluation';directory.mkdir()
    for n in ('receipts','decisions','initial_public','trace_receipts'):(directory/n).mkdir()
    trace=Trace(directory);budget=StartBudget(directory/'starts',6400,root/'STOP')
    prefix=plan.get('treatment_prefix','Aprime')
    models=('Foundation','A_s1','A_s2',f'{prefix}_s1',f'{prefix}_s2')
    cases=read(root/'cases.json');lookup={c['index']:c for c in cases};plan_sha=digest(root/plan.get('plan_file',PLAN))
    bindings={n:{'sha256':a.model_id} for n,a in actors.items()};before={n:{'parameters':tensor_digest(a.model.policy.state_dict()),
        'Adam':optimizer_digest(a.model.policy),'clock':optimizer_clock(a.model.policy)} for n,a in actors.items()}
    durable_json(directory/'model_before.json',before);completed=0;begin=time.perf_counter()
    def forbidden(*a,**k):raise RuntimeError('evaluation_optimizer_forbidden')
    handles=[a.model.policy.optimizer.register_step_pre_hook(forbidden) for a in actors.values()]
    for n,a in actors.items():
        original=a.infer;a.infer=lambda view,name=n,actor=a,f=original:trace.infer(name,actor,f,view)
    try:
        for name in models:
            for seat in ('p1','p2'):
                for offset in range(0,640,16):
                    if runtime.stopping():raise RuntimeError('evaluation_STOP_or_deadline')
                    provider=Provider(lookup,budget,name,'league_s0',seat,plan_sha,trace=trace)
                    rival=EpisodeRival('league_s0',actors['Foundation']);rival.reset(0)
                    def progress(records):
                        nonlocal completed
                        for record in records:
                            key=f'{name}_league_s0_{seat}_{record["case"]}'
                            if not (directory/'receipts'/(key+'.receipt.json')).exists():trace.finish(record)
                        completed+=persist_evaluation_batch(directory/'receipts',records,bindings,lookup,name,'league_s0',seat,plan_sha)
                        if any(r['truncated'] or r['native_choice_rejections'] for r in records):raise ValueError('invalid_evaluation_no_replacement')
                        elapsed=time.perf_counter()-begin
                        atomic_json(root/'progress.json',{'phase':'evaluation','model':name,'seat':seat,'valid':completed,
                            'starts':budget.count,'target':6400,'evaluation_seconds':elapsed,'games_per_second':completed/elapsed,'unix':time.time()})
                    evaluate(plan['checkout'],plan['catalog'],{name:actors[name]},cases=16,offset=offset,
                        curriculum_version='showdown-learning-curriculum-v8',rivals={'league_s0':rival},
                        candidate_seat=seat,case_provider=provider,stopping=runtime.stopping,
                        tactical_diagnostics=True,transition_observer=trace.observe,per_game_progress=True,progress=progress)
        rows=[read(p) for p in (directory/'receipts').glob('*.receipt.json')]
        result=analyze(rows,cases,plan['analysis']['draws'],plan['analysis']['bootstrap_seed'],treatment_prefix=prefix)
        first={}
        for rep in (1,2):
            matched=different=terminal=0
            for c in cases:
                for seat in ('p1','p2'):
                    aa=[]
                    for n in (f'A_s{rep}',f'{prefix}_s{rep}'):
                        tr=read(directory/'trace_receipts'/f'{n}_league_s0_{seat}_{c["index"]}.json')
                        aa.append(tr['first'])
                    a,b=aa
                    if (a['public_input_SHA256'],a['feature_SHA256'],a['mask'])!=(b['public_input_SHA256'],b['feature_SHA256'],b['mask']):
                        raise ValueError('initial_evaluation_inputs_not_paired')
                    matched+=1;different+=a['action']!=b['action']
                    terminal+=a['action']!=b['action'] and next(r for r in rows if r['policy']==f'A_s{rep}' and r['case']==c['index'] and r['seat']==seat)['record']['return']!=next(r for r in rows if r['policy']==f'{prefix}_s{rep}' and r['case']==c['index'] and r['seat']==seat)['record']['return']
            first[f's{rep}']={'matched':matched,'different_first_actions':different,'different_first_and_terminal':terminal,
                'causal_limit':'subsequent decisions differ; not first-action causal attribution'}
        result['first_actions']=first
        durable_json(root/'analysis.json',result)
        after={n:{'parameters':tensor_digest(a.model.policy.state_dict()),'Adam':optimizer_digest(a.model.policy),'clock':optimizer_clock(a.model.policy)} for n,a in actors.items()}
        assert before==after and completed==budget.count==6400
        durable_json(directory/'model_after.json',after)
        durable_json(root/'execution_complete.json',{'status':'EXECUTION_COMPLETE','new_trained':32768,'new_Adam':1024,
            'evaluation_games':6400,'evaluation_starts':budget.count,'evaluation_seconds':time.perf_counter()-begin,'promotion':False})
    finally:
        trace.close()
        for h in handles:h.remove()


def run(root):
    if any((root/n).exists() for n in ('started.json','execution_complete.json','failure.json')):
        raise RuntimeError('existing_owner_do_not_restart')
    plan=read(root/PLAN);gate_result=read(root/'offline_gate.json')
    assert gate_result['status']=='PASS' and gate_result['plan_SHA256']==digest(root/PLAN)
    verify({**plan['bindings'],**plan['code']})
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=32)
    runtime=RuntimeLimit(root,7200);network=enforce_local_network_only();torch.set_num_threads(1);began=time.perf_counter()
    durable_json(root/'started.json',{'PID':os.getpid(),'parent_PID':os.getppid(),'KST':datetime.now().astimezone().isoformat(),
        'unix':time.time(),'plan_SHA256':digest(root/PLAN),'automatic_restarts':0})
    try:
        native=read(plan['runtime_manifest']);verify({str(Path(native['root'])/p):h for p,h in native['files'].items()})
        verify(read(plan['preservation_registry']))
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
        actors={'Foundation':parent}
        for n,b in plan['controls'].items():actors[n]=ResidualActor(b['path'],plan['catalog'])
        for rep,seed in enumerate(plan['training_seeds'],1):
            actors[f'Aprime_s{rep}']=train_arm(root,plan,f'Aprime_s{rep}',seed,parent,runtime)
        for n,a in actors.items():
            durable_json(root/f'TRAIN_validation_{n}.json',validation_metrics(a,read(root/VALIDATION),parent))
        evaluate_models(root,plan,actors,runtime)
        verify({**plan['bindings'],**plan['code']});verify(read(plan['preservation_registry']))
        verify({str(Path(native['root'])/p):h for p,h in native['files'].items()})
        durable_json(root/'owner_resources.json',{'seconds':time.perf_counter()-began,'resources':job.usage(),'network':network})
        durable_json(root/'owner_exit.json',{'status':'SUCCESS','execution_complete':True,'unix':time.time()})
    except BaseException:
        durable_json(root/'failure.json',{'status':'PARTIAL','trace':traceback.format_exc(),
            'seconds':time.perf_counter()-began,'resources':job.usage(),'automatic_retry':False})
        raise
    finally:runtime.finished.set()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','gate','run'))
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    {'prepare':prepare,'gate':gate,'run':run}[args.phase](args.output.resolve())
