"""One frozen 1,280-game research pilot, no learning or automatic retries."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import argparse
import json
import os
from pathlib import Path
import sys
import time
import traceback
import zipfile
from hashlib import sha256

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import numpy as np
from advisor.learned_execution_alignment import content_hash, digest, durable_json, masked_sample
from advisor.learned_fixed_micro import seed4
from advisor.learned_opponent_quality import VERSION, QualityActor, QualityTrace, analyze, global_rng_digest
from advisor.learned_selfplay_pilot import StartBudget, read
from advisor.learned_train_opponents import POLICIES
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only
from scripts.build_independent_development_teams import verify_bindings
from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases, persist_evaluation_batch

PLAN = 'plan_revision_02.json'


def freeze(root):
    root = Path(root); scope = read(root/'scope.json')
    if (root/PLAN).exists(): raise ValueError('quality_plan_already_frozen')
    source = read(root/'source_ready.json')
    if source['status'] != 'SOURCE_READY' or source['teams'] != 160 or source['pairs'] != 80:
        raise ValueError('quality_source_not_ready')
    manifest = read(root/'source_manifest.json')
    if source['manifest_SHA256'] != digest(root/'source_manifest.json'):
        raise ValueError('quality_source_manifest_changed')
    verify_bindings({str(root/n): a['sha256'] for n,a in manifest['assets'].items()})
    verify_bindings(manifest['source_bindings'])
    previous = root.parent/'actionable-decision-advantage-normalization-v1-20261107'
    prior = read(previous/'plan_revision_02.json')
    registry = root.parent/'train-opponent-policy-diversity-harness-v1-20261107/original_inputs_before.json'
    verify_bindings(read(registry))
    teams = read(root/'teams.json')['teams']; cases = []
    for pair in range(80):
        for direction in (0, 1):
            for replicate in (0, 1):
                index = len(cases); a,b = (2*pair+direction, 2*pair+1-direction)
                preview = {side: (np.random.default_rng(seed4(f'{VERSION}:preview:{pair}:{replicate}:{i}')).permutation(6)[:3]+1).tolist()
                           for side,i in [('self',a),('opponent',b)]}
                scenario = {'scenario_id':f'{VERSION}:quality:{index}',
                    'teams':{'self':deepcopy(teams[a]),'opponent':deepcopy(teams[b])}, 'preview':preview,
                    'seed':seed4(f'{VERSION}:native:{pair}:{direction}:{replicate}'),
                    'history':[], 'assumptions':['T1 research quality source, no sealed outcomes or learning.']}
                cases.append({'index':index,'pair':pair,'direction':direction,'replicate':replicate,
                    'rival':'foundation_argmax','scenario':scenario,'scenario_sha256':content_hash(scenario)})
    durable_json(root/'cases.json',cases)
    parent = prior['parent']
    if digest(parent['path']) != parent['sha256']: raise ValueError('quality_Foundation_changed')
    with zipfile.ZipFile(parent['path']) as z:
        if z.testzip() is not None: raise ValueError('quality_corrupt_Foundation')
        adam = sha256(z.read('policy.optimizer.pth')).hexdigest()
    code = ['advisor/learned_opponent_quality.py','advisor/learned_train_opponents.py',
            'scripts/pilot_opponent_quality.py','scripts/evaluate_showdown_policy.py']
    plan = {'version':VERSION,'scope':scope,'source_manifest_SHA256':digest(root/'source_manifest.json'),
        'parent':parent,'parent_Adam_archive_SHA256':adam,'catalog':prior['catalog'],
        'checkout':prior['checkout'],'runtime_manifest':prior['runtime_manifest'],
        'preservation_registry':str(registry),'model_order':list(POLICIES),'cases':320,
        'games':1280,'games_per_policy':640,'team_pairs':80,
        'execution_order':'seat,pairs_of_16_cases,policy; per-game durable results; no restarts',
        'bindings':{str(root/'scope.json'):digest(root/'scope.json'),
            str(root/'source_manifest.json'):digest(root/'source_manifest.json'),
            str(root/'cases.json'):digest(root/'cases.json'),
            str(registry):digest(registry),prior['runtime_manifest']:digest(prior['runtime_manifest']),
            prior['catalog']:digest(prior['catalog']),parent['path']:parent['sha256']},
        'code':{str(REPO/n):digest(REPO/n) for n in code},
        'frozen_KST':datetime.now().astimezone().isoformat()}
    durable_json(root/PLAN,plan)
    return plan


def verify(root):
    plan = read(root/PLAN); s = plan['scope']
    if (plan['version'] != VERSION or plan['games'] != 1280 or plan['cases'] != 320
            or s['native_start_cap'] != 1280 or s['workers'] != 1 or s['GPU'] is not False
            or s['CPU_percent'] != 50 or s['RAM_mib'] != 12288
            or s['screening'] != {'nonargmax_multilegal_min':.05,'win_difference_min':-.1,
                                  'not_noninferiority_or_learning_proof':True}):
        raise ValueError('quality_frozen_contract_changed')
    verify_bindings({**plan['bindings'],**plan['code']})
    verify_bindings(read(plan['preservation_registry']))
    source = read(root/'source_manifest.json'); verify_bindings(source['source_bindings'])
    verify_bindings({str(root/a['path']):a['sha256'] for a in source['assets'].values()})
    runtime = read(plan['runtime_manifest'])
    verify_bindings({str(Path(runtime['root'])/p):h for p,h in runtime['files'].items()})
    return plan


class Dispatch:
    def act(self, view): return self.actor.act(view)
    @property
    def model_id(self): return self.actor.model_id


def audit(root, plan):
    """Read-only raw receipts/decisions plus pair-cluster analysis, no inference."""
    verify(root); directory = root/'evaluation'; cases = read(root/'cases.json')
    lookup = {c['index']:c for c in cases}; ps = digest(root/PLAN)
    rows = [read(p) for p in (directory/'receipts').glob('*.receipt.json')]
    starts = [read(p) for p in (directory/'starts').glob('*.json')]
    if len(starts) != 1280 or len({s['key'] for s in starts}) != 1280 or {s['key'] for s in starts} != {r['key'] for r in rows}:
        raise ValueError('quality_start_result_mismatch')
    if sorted(s['ordinal'] for s in starts)!=list(range(1280)) or any(s['plan_SHA256']!=ps for s in starts):
        raise ValueError('quality_start_ordinal_or_plan')
    for sub,maximum in [('receipts',1280),('decisions',1280),('initial_public',2560),('initial_native',1280),('trace_receipts',1280)]:
        if len(list((directory/sub).iterdir()))!=maximum:raise ValueError('quality_extra_or_missing_files:'+sub)
    sampled = []; totals = Counter(); pergame = {}; families = Counter(); all_stats = {}
    for row in rows:
        rec = row['record']; key = row['key'].replace(':','_'); c = lookup[row['case']]
        if (row['plan_SHA256'] != ps or row['record_SHA256'] != content_hash(rec)
                or rec['initial_native_seed'] != c['scenario']['seed']
                or rec['canonical_scenario_sha256'] != c['scenario_sha256']
                or row['model_SHA256'] != plan['parent']['sha256']):
            raise ValueError('quality_case_or_model_provenance')
        from scripts.evaluate_showdown_policy import seat_scenario
        side = 'self' if row['seat']=='p1' else 'opponent'
        winner = 'self' if rec['raw_native_winner']==side else 'opponent' if rec['raw_native_winner'] else None
        if (rec['native_scenario_sha256'] != content_hash(seat_scenario(c['scenario'],row['seat']))
                or rec['winner'] != winner or rec['return'] != (1 if winner=='self' else -1 if winner else 0)):
            raise ValueError('quality_native_seat_outcome')
        tr = read(directory/'trace_receipts'/(key+'.json'))
        if tr['trace_SHA256'] != digest(tr['trace_path']) or tr['record_SHA256'] != row['record_SHA256']:
            raise ValueError('quality_trace_digest')
        generators = {}; pending = {}; counts = Counter(); nonargmax = 0
        for line in Path(tr['trace_path']).read_text(encoding='utf-8').splitlines():
            e = json.loads(line)
            if e['phase']=='selected_before_native_step':
                role=e['role']; counts[role]+=1; pending[role]=e
                if role not in generators: generators[role]=np.random.default_rng(e['rng_seed'])
                rng=generators[role]
                if content_hash(rng.bit_generator.state)!=e['rng_before_SHA256']:raise ValueError('quality_RNG_cursor')
                u = float(rng.random()) if e['mode']=='T1_sample' else None
                if e['uniform']!=u or content_hash(rng.bit_generator.state)!=e['rng_after_SHA256']:
                    raise ValueError('quality_RNG_draw')
                expected = masked_sample(e['probabilities'],e['mask'],u) if u is not None else int(np.argmax(e['probabilities']))
                legal=np.array(e['mask'],bool); probs=np.array(e['probabilities']); logits=np.array([v if v is not None else -np.inf for v in e['legal_logits']])
                exp=np.exp(logits[legal]-max(logits[legal]));exp/=exp.sum()
                if (expected!=e['action'] or e['argmax']!=int(probs.argmax()) or not legal[e['action']]
                        or int(legal.sum())!=e['legal_count'] or not e['global_RNG_unchanged']
                        or not np.allclose(probs[legal],exp,rtol=2e-5,atol=2e-6)
                        or e['model_SHA256']!=plan['parent']['sha256']):
                    raise ValueError('quality_same_logits_or_legal_selection')
                if role=='candidate':
                    families[(row['policy'],e['selected_family'],e['argmax_family'])]+=1
                    all_stats.setdefault(row['policy'],[]).append(e)
                    nonargmax+=e['action']!=e['argmax']
                    if row['policy']=='foundation_masked_sample':sampled.append(e)
            else:
                if set(pending)!={'candidate','rival'} or e['result']['action_rejected'] or e['result']['truncated']:
                    raise ValueError('quality_execution_missing_or_rejected')
                if e['actions'][side]!=pending['candidate']['action'] or e['actions']['opponent' if side=='self' else 'self']!=pending['rival']['action']:
                    raise ValueError('quality_executed_action_mismatch')
                pending={}; counts['executed']+=1
        if pending or not counts['candidate']==counts['rival']==counts['executed']==rec['decisions']:
            raise ValueError('quality_decision_counts')
        pergame[row['key']]=nonargmax;totals.update(counts)
        native = read(directory/'initial_native'/(key+'.json'))
        other = 'foundation_masked_sample' if row['policy']=='foundation_argmax' else 'foundation_argmax'
        paired = read(directory/'initial_native'/(key.replace(row['policy'],other,1)+'.json'))
        if any(native[k]!=paired[k] for k in ('native_checkpoint_digest','native_state_SHA256','canonical_scenario_sha256','native_scenario_sha256','case','candidate_seat')):
            raise ValueError('quality_initial_native_pair_mismatch')
        for role in ('candidate','rival'):
            first = read(directory/'initial_public'/(key+'_'+role+'.json'))
            pairfirst = read(directory/'initial_public'/(key.replace(row['policy'],other,1)+'_'+role+'.json'))
            if (first['view'] != pairfirst['view'] or first['proof']['legal_logits']!=pairfirst['proof']['legal_logits']
                    or first['proof']['probabilities']!=pairfirst['proof']['probabilities']):
                raise ValueError('quality_initial_public_logits_mismatch')
    result = analyze(rows,cases,sampled,draws=plan['scope']['bootstrap_draws'],seed=plan['scope']['bootstrap_seed'])
    pair_of_case={c['index']:c['pair'] for c in cases}
    multi=np.zeros(80);different=np.zeros(80)
    for e in sampled:
        if e['legal_count']>1:
            pair=pair_of_case[e['case']];multi[pair]+=1;different[pair]+=e['action']!=e['argmax']
    ix=np.random.default_rng(plan['scope']['bootstrap_seed']).integers(0,80,(20000,80))
    result['diversity_cluster95CI']=np.quantile(different[ix].sum(1)/multi[ix].sum(1),[.025,.975]).tolist()
    result['decision_summary']={p:{'decisions':len(rr),'entropy_mean':float(np.mean([e['entropy'] for e in rr])),
        'mean_nonargmax_per_game':float(np.mean([v for k,v in pergame.items() if k.startswith(p+':')]))}
        for p,rr in all_stats.items()}
    result['family_comparisons']=[{'policy':p,'selected':s,'same_state_argmax':a,'count':n} for (p,s,a),n in sorted(families.items())]
    result['per_game_nonargmax']=pergame
    result['seats']={p:{s:{'games':sum(r['policy']==p and r['seat']==s for r in rows),
        'wins':sum(r['policy']==p and r['seat']==s and r['record']['winner']=='self' for r in rows)}
        for s in ('p1','p2')} for p in POLICIES}
    if read(directory/'model_before.json') != read(directory/'model_after.json'):
        raise ValueError('quality_model_or_Adam_mutation')
    with zipfile.ZipFile(plan['parent']['path']) as z:
        if z.testzip() is not None or sha256(z.read('policy.optimizer.pth')).hexdigest()!=plan['parent_Adam_archive_SHA256']:
            raise ValueError('quality_original_Adam_archive_changed')
    durable_json(root/'analysis.json',result)
    proof={'status':'PASS','starts':len(starts),'results':len(rows),'per_policy':dict(Counter(r['policy'] for r in rows)),
        'initial_native_pairs':640,'initial_public_pairs':1280,'decision_totals':dict(totals),
        'missing_duplicate_rejection_truncation_retry':0,'original_files_verified':len(read(plan['preservation_registry'])),
        'native_truth_in_actor':False,'new_PPO_Adam_rollout_model_save':0,'model_SHA256':plan['parent']['sha256'],
        'Adam_archive_SHA256':plan['parent_Adam_archive_SHA256'],'plan_SHA256':ps,'analysis_SHA256':digest(root/'analysis.json')}
    durable_json(root/'audit_complete.json',proof)
    return result,proof


def run(root):
    root=Path(root)
    if any((root/n).exists() for n in ('started.json','completion.json','owner_failure.json')):
        raise ValueError('quality_existing_owner_do_not_duplicate')
    gate=read(root/'offline_gate.json')
    if gate['status']!='PASS' or gate['plan_SHA256']!=digest(root/PLAN):
        raise ValueError('quality_missing_offline_gate')
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=32)
    limit=RuntimeLimit(root,3600); network=enforce_local_network_only();began=time.perf_counter()
    durable_json(root/'started.json',{'PID':os.getpid(),'KST':datetime.now().astimezone().isoformat(),
        'unix':time.time(),'automatic_restarts':0,'plan_SHA256':digest(root/PLAN)})
    try:
        plan=verify(root)
        import torch
        from sb3_contrib import MaskablePPO
        from advisor.learned_policy import LearnedPolicy
        from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
        from scripts.evaluate_showdown_policy import evaluate
        torch.set_num_threads(1)
        def forbidden(*a,**k):raise RuntimeError('quality_no_learning_model_save_or_Adam')
        MaskablePPO.learn=MaskablePPO.collect_rollouts=MaskablePPO.save=forbidden
        torch.optim.Adam.step=forbidden
        rng=global_rng_digest()
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=plan['parent']['sha256'])
        if global_rng_digest()!=rng:raise ValueError('quality_checkpoint_loader_changed_RNG')
        def identity():return {'parameters':tensor_digest(parent.model.policy.state_dict()),
            'Adam':optimizer_digest(parent.model.policy),'Adam_step':optimizer_clock(parent.model.policy)}
        if identity()!={'parameters':plan['parent']['parameters'],'Adam':plan['parent']['Adam'],'Adam_step':plan['parent']['Adam_step']}:
            raise ValueError('quality_loaded_parent_or_Adam_identity')
        directory=root/'evaluation'
        for sub in ('receipts','decisions','initial_public','initial_native','trace_receipts'):(directory/sub).mkdir(parents=True,exist_ok=False)
        durable_json(directory/'model_before.json',identity())
        budget=StartBudget(directory/'starts',1280,root/'STOP');cases=read(root/'cases.json');lookup={c['index']:c for c in cases}
        candidate,rival=Dispatch(),Dispatch();holder={};completed=0
        bindings={p:plan['parent'] for p in POLICIES};ps=digest(root/PLAN)
        for seat in ('p1','p2'):
            for offset in range(0,320,16):
                for policy in POLICIES:
                    provider=FrozenEvalCases(lookup,budget,policy,'foundation_argmax',seat,ps)
                    def provide(split,index):
                        scenario=provider(split,index)
                        tr=QualityTrace(directory,policy,seat,index);holder['trace']=tr
                        candidate.actor=QualityActor(parent,policy,case=index,seat=seat,role='candidate',record=tr.selection)
                        rival.actor=QualityActor(parent,'foundation_argmax',case=index,seat=seat,role='rival',record=tr.selection)
                        return scenario
                    provide.identity=provider.identity
                    def progress(records):
                        nonlocal completed
                        for rec in records:
                            key=f'{policy}:foundation_argmax:{seat}:{rec["case"]}'
                            if not (directory/'receipts'/(key.replace(':','_')+'.receipt.json')).exists():
                                if holder['trace'].case!=rec['case']:raise ValueError('quality_cumulative_progress_lost_game')
                                holder['trace'].finish(rec)
                        completed+=persist_evaluation_batch(directory/'receipts',records,bindings,lookup,policy,'foundation_argmax',seat,ps)
                        if completed%8==0:
                            atomic_json(root/'progress.json',{'PID':os.getpid(),'completed':completed,'target':1280,
                                'games_per_second':completed/(time.perf_counter()-began),'starts':budget.count,'resources':job.usage()})
                    evaluate(plan['checkout'],plan['catalog'],{policy:candidate},cases=16,offset=offset,
                        rivals={'foundation_argmax':rival},case_provider=provide,candidate_seat=seat,
                        stopping=limit.stopping,transition_observer=lambda e:holder['trace'].observe(e),
                        initial_state_observer=lambda e:holder['trace'].initial(e),
                        per_game_progress=True,progress=progress)
        if completed!=1280 or budget.count!=1280:raise ValueError('quality_incomplete_game_count')
        durable_json(directory/'model_after.json',identity())
        durable_json(root/'execution_complete.json',{'games':completed,'starts':budget.count,'seconds':time.perf_counter()-began})
        result,proof=audit(root,plan)
        resource={'seconds':time.perf_counter()-began,'resources':job.usage(),'network':network}
        durable_json(root/'owner_resources.json',resource)
        lines=['# OPPONENT_DIVERSITY_QUALITY_PILOT_V1',f"판정: {result['verdict']}",
            '신규 PPO·Adam·학습 rollout·모델 저장/승격 0. 독립 PCG64 샘플링만 변경했다.',
            '|정책|승|패|무|승률|terminal return|','|---|---:|---:|---:|---:|---:|']
        for p,o in result['outcomes'].items():lines.append(f"|{p}|{o['wins']}|{o['losses']}|{o['draws']}|{o['win_rate']:.4%}|{o['terminal_return']:+.6f}|")
        lines += [f"sample−argmax return {result['sample_minus_argmax_return']:+.8f}, 80팀쌍95% CI {result['return_cluster95CI']}.",
            f"승률 차이 {100*result['win_difference']:+.4f}%p, CI {[100*x for x in result['win_difference_cluster95CI']]}%p.",
            f"복수 합법 행동 결정의 비-argmax 선택률 {result['nonargmax_multilegal_rate']:.4%}, 군집CI {result['diversity_cluster95CI']}.",
            '같은 샘플링 방문 상태·동일 logits의 argmax를 비교했다. 경로가 갈라진 후 native 상태/RNG가 같다고 가정하지 않는다.',
            '80팀쌍 내 소유권·두 native RNG·실제 양좌석·두 정책을 유지한 20,000 bootstrap(seed116085). 학습효과·비열등성의 입증이 아니다.',
            f'전수 감사: {json.dumps(proof,ensure_ascii=False)}',f'결정 요약: {json.dumps(result["decision_summary"],ensure_ascii=False)}',
            f'자원: {json.dumps(resource)}',f'자료: {root}',
            '완전팀·roster·결합 기술집합은 과거 source와 중복0. 개별 세트·species 미학습을 뜻하지 않는다. source_statistics.json에 구성 차이를 보존했다.',
            '후속 혼합 PPO·추가 평가·승격은 별도 승인 전 실행하지 않는다. Git 마감은 최종 검증 후 별도 영수증에 기록한다.']
        with (root/'REPORT_KO.md').open('x',encoding='utf-8') as f:f.write('\n\n'.join(lines)+'\n')
        durable_json(root/'completion.json',{'status':'COMPLETE','verdict':result['verdict'],'games':1280,'native_starts':1280,
            'new_PPO_Adam_rollout_model_save':0,'audit_SHA256':digest(root/'audit_complete.json'),
            'analysis_SHA256':digest(root/'analysis.json'),'report_SHA256':digest(root/'REPORT_KO.md'),
            'KST':datetime.now().astimezone().isoformat()})
    except BaseException:
        durable_json(root/'owner_failure.json',{'PID':os.getpid(),'trace':traceback.format_exc(),
            'KST':datetime.now().astimezone().isoformat(),'automatic_retry':False,'additional_authorization':False})
        raise
    finally:
        limit.finished.set()
        durable_json(root/'owner_exit.json',{'PID':os.getpid(),'completion':(root/'completion.json').exists(),
            'failure':(root/'owner_failure.json').exists(),'seconds':time.perf_counter()-began,'resources':job.usage()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('--freeze',action='store_true')
    args=parser.parse_args();freeze(args.root) if args.freeze else run(args.root)
