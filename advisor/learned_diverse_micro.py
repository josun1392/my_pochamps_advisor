"""Frozen team diversity and paired analysis; no new model or learning rule."""
from copy import deepcopy
from hashlib import sha256
import numpy as np

from advisor.learned_execution_alignment import content_hash
from advisor.learned_fixed_micro import DIVERSE_VERSION, micro_budget, seed4

MODELS = ('Foundation', 'Fixed16K', 'Diverse_A', 'Diverse_B')
SEEDS = (104031, 104033)
CAP = {'transitions':16384, 'Adam':512, 'starts':2048,
       'targets':[4096,8192,12288,16384]}


def team_keys(team):
    """Keep exact move-slot identity, also detect reordered full-team overlap."""
    return {'ordered':content_hash(team),
            'unordered':content_hash(sorted(content_hash(p) for p in team)),
            'joint_movesets':content_hash(sorted((p['species'], sorted(p['moves'])) for p in team))}


def choose_teams(bank, split, excluded=()):
    excluded=set(excluded)
    order=sorted(range(len(bank)), key=lambda i:sha256(f'{DIVERSE_VERSION}:{split}:{i}'.encode()).digest())
    chosen=[]; used=set(excluded)
    for i in order:
        keys=team_keys(bank[i])
        if any(v in used for v in keys.values()):continue
        if len(bank[i])!=6 or any(not 1<=len(p['moves'])<=4 for p in bank[i]):
            raise ValueError('SCENARIO_COVERAGE_BLOCKED:full_six_native_move_slots')
        chosen.append(i);used.update(keys.values())
        if len(chosen)==16:return chosen
    raise ValueError('SCENARIO_COVERAGE_BLOCKED:16_distinct_teams')


def build_templates(bank, excluded=()):
    """8 TRAIN pairs and 8 disjoint validation pairs, both owner directions."""
    templates=[]; used=set(excluded)
    for scope,partition in (('train','train'),('independent','validation')):
        indices=choose_teams(bank[partition],scope,used)
        for j in range(8):
            pair=j if scope=='train' else j+8
            ii=indices[2*j:2*j+2];teams=[deepcopy(bank[partition][i]) for i in ii]
            bindings=[team_keys(t) for t in teams]
            used.update(h for b in bindings for h in b.values())
            preview=[list(np.random.default_rng(seed4(f'{DIVERSE_VERSION}:preview:{pair}:{k}')).permutation(6)[:3]+1) for k in range(2)]
            preview=[[int(x) for x in p] for p in preview]
            for direction in (0,1):
                order=(direction,1-direction)
                scenario={'scenario_id':f'{DIVERSE_VERSION}:template:{pair}:{direction}',
                    'teams':dict(zip(('self','opponent'),(deepcopy(teams[k]) for k in order))),
                    'preview':dict(zip(('self','opponent'),(preview[k] for k in order))),
                    'seed':[1,2,3,4], 'history':[],
                    'assumptions':['Pinned native V8 bank; frozen ordered three per roster; no learned preview.']}
                templates.append({'scope':scope,'pair':pair,'direction':direction,'partition':partition,
                    'indices':ii,'team_keys':bindings,'scenario':scenario})
    return templates


def evaluation_cases(templates):
    rows=[]
    for t in templates:
        for rep in range(8):
            i=len(rows);s=deepcopy(t['scenario'])
            s.update(scenario_id=f'{DIVERSE_VERSION}:EVAL:{i}',
                     seed=seed4(f'{DIVERSE_VERSION}:EVAL:pair{t["pair"]}:rep{rep}'))
            rows.append({'index':i,'scope':t['scope'],'pair':t['pair'],'direction':t['direction'],
                'replicate':rep,'rival':'league_s0','scenario':s,'scenario_sha256':content_hash(s)})
    return rows


def validate_plan(plan):
    if (plan['schema_version']!=DIVERSE_VERSION or tuple(plan['training_seeds'])!=SEEDS
            or plan['micro_prior_transitions']!=0 or micro_budget(plan)!=CAP
            or plan['opponents']!=['league_s0'] or plan['evaluation_games']!=2048
            or plan['workers']!=4 or plan['memory_mib']!=8192 or plan['CPU_percent']!=50
            or plan['device']!='cpu' or plan['teacher_enabled'] is not False):
        raise ValueError('diverse_study_contract')
    ts=plan['templates']
    if len(ts)!=32 or plan['training_template_indices']!=[i for i,t in enumerate(ts) if t['scope']=='train']:
        raise ValueError('diverse_template_membership')
    full={};joint={}
    for scope in ('train','independent'):
        subset=[t for t in ts if t['scope']==scope]
        pairs={t['pair'] for t in subset}
        if len(pairs)!=8 or any({t['direction'] for t in subset if t['pair']==p}!={0,1} for p in pairs):
            raise ValueError('diverse_pair_directions')
        for pair in pairs:
            a,b=sorted((t for t in subset if t['pair']==pair),key=lambda t:t['direction'])
            for field in ('teams','preview'):
                if (a['scenario'][field]['self']!=b['scenario'][field]['opponent']
                        or a['scenario'][field]['opponent']!=b['scenario'][field]['self']):
                    raise ValueError('diverse_reciprocal_owner_binding')
        full[scope]=set();joint[scope]=set()
        for t in subset:
            if t['partition']!=('train' if scope=='train' else 'validation'):
                raise ValueError('diverse_partition')
            for side in ('self','opponent'):
                team=t['scenario']['teams'][side]; keys=team_keys(team)
                if keys not in t['team_keys']:raise ValueError('diverse_team_binding')
                if len(team)!=6 or len(set(t['scenario']['preview'][side]))!=3 or not all(1<=x<=6 for x in t['scenario']['preview'][side]):
                    raise ValueError('diverse_preview_slots')
                full[scope].add(keys['unordered']);joint[scope].add(keys['joint_movesets'])
        if len(full[scope])!=16:raise ValueError('diverse_complete_team_uniqueness')
    if full['train']&full['independent'] or joint['train']&joint['independent']:
        raise ValueError('diverse_split_overlap')
    if plan['evaluation_cases']!=evaluation_cases(ts):raise ValueError('diverse_frozen_evaluation_changed')
    return True


def paired_analysis(records, cases, *, draws=20000, seed=2026102809):
    by={(r['policy'],r['case'],r['seat']):r['record'] for r in records}
    expected={(m,c['index'],s) for m in MODELS for c in cases for s in ('p1','p2')}
    if len(records)!=2048 or set(by)!=expected:raise ValueError('diverse_evaluation_missing_or_duplicate')
    rng=np.random.default_rng(seed);out={}
    comparisons=[(m,'Foundation') for m in MODELS[1:]]+[(m,'Fixed16K') for m in MODELS[2:]]
    for scope in ('train','independent','all'):
        cs=[c for c in cases if scope=='all' or c['scope']==scope]
        pairs=sorted({c['pair'] for c in cs})
        outcomes={};means={}
        for m in MODELS:
            rows=[by[m,c['index'],s] for c in cs for s in ('p1','p2')]
            outcomes[m]={'games':len(rows),'wins':sum(r['winner']=='self' and not r['truncated'] for r in rows),
                'losses':sum(r['winner']=='opponent' and not r['truncated'] for r in rows),
                'draws':sum(r['winner'] is None and not r['truncated'] for r in rows),
                'truncations':sum(r['truncated'] for r in rows)}
            means[m]=np.array([np.mean([int(by[m,c['index'],s]['winner']=='self' and not by[m,c['index'],s]['truncated'])
                for c in cs if c['pair']==p for s in ('p1','p2')]) for p in pairs])
        # Resample team pairs. Keep all directions, seeds, seats and models paired.
        indices=rng.integers(0,len(pairs),size=(draws,len(pairs)))
        contrasts={}
        for a,b in comparisons:
            d=means[a]-means[b]
            contrasts[f'{a}_minus_{b}']={'difference':float(d.mean()),
                'team_pair_cluster_95CI':np.quantile(d[indices].mean(1),[.025,.975]).tolist(),
                'pair_differences':dict(zip(map(str,pairs),map(float,d)))}
        combined=(means['Diverse_A']+means['Diverse_B'])/2-means['Foundation']
        contrasts['Diverse_mean_minus_Foundation']={'difference':float(combined.mean()),
            'team_pair_cluster_95CI':np.quantile(combined[indices].mean(1),[.025,.975]).tolist()}
        out[scope]={'outcomes':outcomes,'comparisons':contrasts,'team_pair_clusters':len(pairs)}
    primary=out['independent']['comparisons']
    deltas=[primary[m+'_minus_Foundation']['difference'] for m in MODELS[2:]]
    censored=any(v['truncations'] for v in out['all']['outcomes'].values())
    out['verdict']=('DIVERSE_GENERALIZATION_SIGNAL' if min(deltas)>0 and primary['Diverse_mean_minus_Foundation']['team_pair_cluster_95CI'][0]>0 and not censored
        else 'NO_OBSERVED_TRANSFER' if max(deltas)<=0 and not censored else 'DIVERSE_MICRO_INCONCLUSIVE')
    out['uncertainty']='conditional paired team-pair bootstrap; only two training seeds, no training-seed population CI; exploratory research validation'
    return out
