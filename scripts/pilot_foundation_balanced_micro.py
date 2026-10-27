"""Reciprocal roster ownership micro, composed from maintained experiment owners."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from copy import deepcopy
import json
import os
import time
import traceback
import numpy as np
from advisor.learned_fixed_micro import seed4
from advisor.learned_selfplay_pilot import OPPONENTS,StartBudget
from advisor.learned_execution_alignment import content_hash,digest,durable_json
from advisor.learning_resources import atomic_json,WindowsJob,RuntimeLimit
from scripts.pilot_foundation_fixed_micro import train,eval_phase,read

VERSION='foundation-balanced-bidirectional-micro-v1'
PARENT='9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf'
# Static roster comparison only, before any new outcomes. Same brought species;
# retain the full native-valid six, all original sets and original move slots.
SPECS=[('train',729,3774,['Sableye','Krookodile','Umbreon']),
       ('train',2818,3685,['Morpeko','Ditto','Clefable']),
       ('development',1198,3919,['Blastoise','Runerigus','Infernape']),
       ('development',2325,2564,['Hatterene','Blastoise','Aggron']),
       ('independent',827,1224,['Blastoise','Empoleon','Scrafty']),
       ('independent',3120,3718,['Slurpuff','Blastoise','Milotic'])]


def frozen_cases(templates,phase):
    indices=([4,5,6,7]if phase=='development'else [8,9,10,11]if phase=='precheck'
             else [0,1,2,3,8,9,10,11])
    repetitions=4 if phase!='final'else 2
    cases=[]
    for rival in OPPONENTS:
        for t in indices:
            template=templates[t]
            for rep in range(repetitions):
                i=len(cases);scenario=deepcopy(template['scenario'])
                scenario.update(scenario_id=f'{VERSION}:{phase}:{i}',
                    seed=seed4(f'{VERSION}:{phase}:pair{template["pair"]}:{rival}:rep{rep}'))
                cases.append({'index':i,'scope':template['scope'],'family':str(template['pair']),
                    'pair':template['pair'],'direction':template['direction'],'replicate':rep,
                    'rival':rival,'scenario':scenario,'scenario_sha256':content_hash(scenario)})
    assert len(cases)==64
    return cases


def gate(rows,cases):
    """Predeclared point-estimate design gate, not superiority inference."""
    lookup={c['index']:c for c in cases}
    expected={(c['index'],s)for c in cases for s in ('p1','p2')}
    if len(rows)!=128 or {(r['case'],r['seat'])for r in rows}!=expected:
        raise ValueError('balanced_gate_receipt_missing_or_duplicate')
    def fraction(rs):return sum(r['record']['winner']=='self'and not r['record']['truncated']for r in rs)/len(rs)
    whole=fraction(rows)
    directions={d:fraction([r for r in rows if lookup[r['case']]['direction']==d])for d in (0,1)}
    pair_directions={f'{p}:{d}':fraction([r for r in rows if lookup[r['case']]['pair']==p and lookup[r['case']]['direction']==d])
        for p in sorted({c['pair']for c in cases})for d in (0,1)}
    opportunities={d:dict(sum((Counter(r['record']['tactical_counts'])for r in rows if lookup[r['case']]['direction']==d),Counter()))for d in (0,1)}
    meaningful=all(v.get('available:attack',0)>=16 and v.get('available:switch',0)>=16 and
        sum(v.get('available:'+k,0)for k in ('setup','defense','recovery'))>=8 for v in opportunities.values())
    passed=(.35<=whole<=.75 and all(.20<=v<=.80 for v in directions.values())and
        all(.10<=v<=.90 for v in pair_directions.values())and meaningful and not any(r['record']['truncated']for r in rows))
    return {'passed':passed,'winrate':whole,'directions':directions,'pair_directions':pair_directions,
        'meaningful_opportunities':meaningful,'opportunities':opportunities}


def paired(rows,cases,draws=20000):
    by={(r['policy'],r['case'],r['seat']):r['record']for r in rows}
    expected={(m,c['index'],s)for m in ('Foundation','Micro')for c in cases for s in ('p1','p2')}
    if len(rows)!=256 or set(by)!=expected:raise ValueError('balanced_final_missing_or_duplicate')
    out={};rng=np.random.default_rng(104028)
    for scope in ('train','independent','all'):
        chosen=[c for c in cases if scope=='all'or c['scope']==scope]
        groups={}
        for c in chosen:groups.setdefault((c['pair'],c['rival'],c['replicate']),[]).append(c)
        deltas=[];strata={}
        for (pair,rival,rep),cs in groups.items():
            if {c['direction']for c in cs}!={0,1}:raise ValueError('reciprocal_cluster_missing')
            ds=[int(by['Micro',c['index'],s]['winner']=='self'and not by['Micro',c['index'],s]['truncated'])-
                int(by['Foundation',c['index'],s]['winner']=='self'and not by['Foundation',c['index'],s]['truncated'])for c in cs for s in ('p1','p2')]
            strata.setdefault((pair,rival),[]).append(len(deltas));deltas.append(np.mean(ds))
        x=np.asarray(deltas);samples=np.zeros(draws)
        for ids in strata.values():
            vals=x[ids];samples+=vals[rng.integers(0,len(vals),size=(draws,len(vals)))].sum(1)/len(x)
        counts={}
        for m in ('Foundation','Micro'):
            rs=[by[m,c['index'],s]for c in chosen for s in ('p1','p2')]
            counts[m]=dict(Counter('truncation'if r['truncated']else r['winner']or'draw'for r in rs))
        out[scope]={'outcomes':counts,'difference':float(x.mean()),'conditional_cluster_95CI':np.quantile(samples,[.025,.975]).tolist(),
            'clusters':len(x),'games_per_model':len(chosen)*2}
    out['verdict']=('BALANCED_MICRO_LEARNING_COMPLETE'if out['train']['difference']>0 and out['independent']['conditional_cluster_95CI'][0]>0
        else'MICRO_INCONCLUSIVE')
    return out


def prepare(root,parent,checkout):
    from advisor.learned_full_roster import load_bank,study_identity
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock
    if root.exists():raise ValueError('balanced_output_already_exists_inspect_first')
    bank=load_bank()['teams']['train'];templates=[]
    for pair,(scope,a,b,names)in enumerate(SPECS):
        teams=[deepcopy(bank[i])for i in (a,b)]
        previews=[[next(j+1 for j,p in enumerate(t)if p['species']==name)for name in names]for t in teams]
        for d in (0,1):
            scenario={'scenario_id':f'{VERSION}:template:{pair}:{d}','teams':dict(zip(('self','opponent'),[teams[d],teams[1-d]])),
                'preview':dict(zip(('self','opponent'),[previews[d],previews[1-d]])),'history':[],'seed':[1,2,3,4],
                'assumptions':['V8 TRAIN full six unchanged; fixed ordered three; reciprocal roster ownership; no teacher.']}
            templates.append({'scope':scope,'pair':pair,'direction':d,'indices':[a,b],
                'team_SHA256':[content_hash(t)for t in teams],'scenario':scenario})
    if len({h for t in templates for h in t['team_SHA256']})!=12:raise ValueError('complete_roster_partition_overlap')
    catalog=str(ROOT/'models/showdown_mc_domain_v1/catalog.json')
    actor=LearnedPolicy(parent,catalog,expected_model_id=PARENT);m=actor.model
    if type(m).__name__!='FoundationCombatPPO'or(m.n_steps,m.batch_size,m.n_epochs)!=(128,128,4)or optimizer_clock(m.policy)!=32768:
        raise ValueError('parent_PPO_Adam_contract')
    files=['advisor/learned_fixed_micro.py','scripts/pilot_foundation_fixed_micro.py',
        'scripts/pilot_foundation_balanced_micro.py','advisor/learned_gym.py','advisor/learned_combat_foundation.py',
        'advisor/learned_selfplay_pilot.py','advisor/learned_ppo_contract_audit.py','scripts/train_showdown_autonomous.py','scripts/evaluate_showdown_policy.py']
    plan={'schema_version':VERSION,'seed':104028,'checkout':str(checkout),'catalog':catalog,
        'parent':{'path':str(parent),'sha256':PARENT,'parameters':tensor_digest(m.policy.state_dict()),
            'Adam':optimizer_digest(m.policy),'Adam_step':optimizer_clock(m.policy)},
        'bank_identity':study_identity(),'templates':templates,'training_template_indices':[0,1,2,3],
        'teacher_enabled':False,'source_hashes':{p:digest(ROOT/p)for p in files},
        'budgets':{'development':256,'precheck':128,'final':256,'TRAIN_starts':512,'PPO':4096,'Adam':128},
        'PPO':{'n_steps':m.n_steps,'batch_size':m.batch_size,'epochs':m.n_epochs,'gamma':m.gamma,'GAE':m.gae_lambda,
            'LR':m.lr_schedule(1.),'entropy':m.ent_coef,'uniform_KL':m.zero_avoiding_beta},
        'mixture':{'league_s0':.25,'league_anchor':.25,'tactical_heuristic':.25,'champions_heuristic':.25},
        'gate':'overall35-75%; direction20-80%; pair-direction10-90%; no truncations; each direction >=16 attack/switch opportunities and >=8 recovery/setup/defense opportunities',
        'selection':'one static configuration only; same three species; higher shared move overlap; no outcome-based replacements',
        'resource':{'CPU':50,'RAM_mib':8192,'workers':4,'GPU':False},
        'primary':'paired independent-team Micro-Foundation difference; cluster both reciprocal directions and actual seats, strata pair/rival; conditional fixed pairs and one training seed'}
    root.mkdir(parents=True);durable_json(root/'plan.json',plan)
    for phase in ('development','precheck','final'):
        folder=root/phase;folder.mkdir();phaseplan={**plan,'schema_version':VERSION+':'+phase,'evaluation_cases':frozen_cases(templates,phase)}
        durable_json(folder/'plan.json',phaseplan)
    print(json.dumps({'prepared':str(root),'SHA256':digest(root/'plan.json')}))


def receipts(root):return [read(p)for p in(root/'evaluation').glob('*.receipt.json')]


def run(root):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest
    from advisor.learning_resources import enforce_local_network_only
    if(root/'started.json').exists()or(root/'completion.json').exists():raise ValueError('balanced_already_started_do_not_duplicate')
    plan=read(root/'plan.json')
    if any(digest(ROOT/p)!=h for p,h in plan['source_hashes'].items()):raise ValueError('balanced_frozen_source_changed')
    for phase in ('development','precheck','final'):
        pp=read(root/phase/'plan.json')
        if (pp['evaluation_cases']!=frozen_cases(plan['templates'],phase)or pp['parent']!=plan['parent']
                or pp['schema_version']!=VERSION+':'+phase):raise ValueError('balanced_phase_contract_changed')
    job=WindowsJob(memory_mib=8192,cpu_percent=50,active_process_limit=32);runtime=RuntimeLimit(root,3600)
    started=time.perf_counter();torch.set_num_threads(1);enforce_local_network_only()
    durable_json(root/'started.json',{'pid':os.getpid(),'unix':time.time(),'plan_SHA256':digest(root/'plan.json')})
    try:
        parent=LearnedPolicy(plan['parent']['path'],plan['catalog'],expected_model_id=PARENT)
        gates={}
        for phase in ('development','precheck'):
            folder=root/phase;pp=read(folder/'plan.json');budget=StartBudget(folder/'starts',plan['budgets'][phase],root/'STOP')
            eval_phase(pp,folder,'Foundation',parent,parent,budget,runtime)
            gates[phase]=gate(receipts(folder),pp['evaluation_cases']);durable_json(folder/'gate.json',gates[phase])
            if not gates[phase]['passed']:
                atomic_json(root/'completion.json',{'verdict':'BALANCE_GATE_BLOCKED','gates':gates,'PPO':0,'Adam':0,
                    'seconds':time.perf_counter()-started,'resources':job.usage()});return
        folder=root/'final';pp=read(folder/'plan.json');budget=StartBudget(folder/'starts',256,root/'STOP')
        eval_phase(pp,folder,'Foundation',parent,parent,budget,runtime)
        candidate=train(plan,root,parent,runtime)
        eval_phase(pp,folder,'Micro',candidate,parent,budget,runtime)
        if tensor_digest(parent.model.policy.state_dict())!=plan['parent']['parameters']or optimizer_digest(parent.model.policy)!=plan['parent']['Adam']:
            raise ValueError('immutable_parent_modified')
        results=paired(receipts(folder),pp['evaluation_cases']);durable_json(root/'analysis.json',results)
        atomic_json(root/'completion.json',{'verdict':results['verdict'],'PPO':4096,'Adam':read(root/'endpoint.json')['new_Adam'],
            'gates':gates,'final_valid_games':len(receipts(folder)),'seconds':time.perf_counter()-started,'resources':job.usage()})
    except BaseException as error:
        atomic_json(root/'failure.json',{'type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),
            'seconds':time.perf_counter()-started,'resources':job.usage()});raise
    finally:runtime.finished.set()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--parent',type=Path);p.add_argument('--checkout',type=Path);a=p.parse_args()
    prepare(a.output,a.parent,a.checkout)if a.mode=='prepare'else run(a.output)
