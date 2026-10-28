"""Degree-balanced matchup schedules and paired analysis, not a PPO backend."""
from collections import Counter
from copy import deepcopy
import numpy as np

from advisor.learned_fixed_micro import MATCHUP_VERSION as VERSION, seed4
from advisor.learned_diverse_micro import team_keys
from advisor.learned_execution_alignment import content_hash

SEEDS=(104039,104041)
MODELS=('Foundation','A_s1','B_s1','A_s2','B_s2')
CAP={'transitions':16384,'Adam':512,'starts':4096,'targets':[4096,8192,12288,16384]}


def factorization():
    """15 disjoint perfect matchings on 16 identities; round0 is prior pairing."""
    wheel=list(range(0,16,2))+list(range(15,0,-2));rounds=[]
    for _ in range(15):
        rounds.append([sorted((wheel[i],wheel[-i-1])) for i in range(8)])
        wheel=[wheel[0],wheel[-1],*wheel[1:-1]]
    return rounds


def schedule(condition):
    if condition not in ('A','B'):raise ValueError('matchup_condition')
    rounds=factorization();segments=[]
    for r in range(4):
        matching=rounds[0 if condition=='A' else r]
        rival={a:b for a,b in matching}|{b:a for a,b in matching}
        for group in range(4):
            segments.append({'index':len(segments),'round':r,'group':group,
                'transitions':1024,'rollouts':2,'worker_steps':256,
                'slots':[{'worker':w,'own':4*group+w,'opponent':rival[4*group+w]} for w in range(4)]})
    return segments


def exposure(schedule_rows):
    own=Counter();foe=Counter();directed=Counter()
    for segment in schedule_rows:
        for slot in segment['slots']:
            n=segment['worker_steps'];a,b=slot['own'],slot['opponent']
            own[a]+=n;foe[b]+=n;directed[a,b]+=n
    return {'own':dict(own),'opponent':dict(foe),
            'directed':{f'{a}:{b}':v for (a,b),v in directed.items()}}


def make_scenario(rosters,own,foe,*,identity,seed):
    if own==foe:raise ValueError('self_mirror_not_in_matchup_design')
    return {'scenario_id':identity,'teams':{'self':deepcopy(rosters[own]['team']),'opponent':deepcopy(rosters[foe]['team'])},
        'preview':{'self':deepcopy(rosters[own]['preview']),'opponent':deepcopy(rosters[foe]['preview'])},
        'seed':list(seed),'history':[],
        'assumptions':['Native V8 frozen rosters and ordered bring-three; controlled matchup only.']}


class SlotCases:
    """One immutable ordered matchup for exactly256 collected steps per worker."""
    def __init__(self,plan,condition,seed,segment,worker):
        if condition not in ('A','B') or seed not in SEEDS or not 0<=segment<16 or not 0<=worker<4:
            raise ValueError('invalid_matchup_slot')
        self.plan,self.condition,self.seed,self.segment,self.worker=plan,condition,seed,segment,worker
        self.slot=plan['schedules'][condition][segment]['slots'][worker];self.ordinal=0
        self.identity={'sha256':content_hash({'version':VERSION,'slot':self.slot,'rosters':plan['training_rosters']})}
        self.contract={'selection_mode':'fixed_ordered_three_matchup_slot_v1'}

    def __call__(self,split,index):
        if split!='train' or type(index)is not int or index<0:raise ValueError('matchup_TRAIN_only')
        ordinal=self.ordinal;self.ordinal+=1
        # No condition/model identity in RNG. Downstream episode counts may
        # diverge after different matchups; matched seeds do not force same RNG use.
        rng=seed4(f'{VERSION}:TRAIN:{self.seed}:segment{self.segment}:worker{self.worker}:episode{ordinal}')
        return make_scenario(self.plan['training_rosters'],self.slot['own'],self.slot['opponent'],
            identity=f'{VERSION}:{self.condition}:{self.seed}:{self.segment}:{self.worker}:{ordinal}',seed=rng)


def evaluation_cases(training_rosters,independent_rosters):
    cases=[]
    for scope,rosters,pairs in (('new_matchup',training_rosters,factorization()[4]),
                              ('new_identity',independent_rosters,[[i,i+1]for i in range(0,16,2)])):
        for j,(a,b) in enumerate(pairs):
            pair=j if scope=='new_matchup' else j+8
            for direction,(own,foe) in enumerate(((a,b),(b,a))):
                for rep in range(8):
                    i=len(cases);s=make_scenario(rosters,own,foe,identity=f'{VERSION}:EVAL:{i}',
                        seed=seed4(f'{VERSION}:EVAL:{pair}:rep{rep}'))
                    cases.append({'index':i,'scope':scope,'pair':pair,'direction':direction,'replicate':rep,
                        'roster_indices':[a,b],'rival':'league_s0','scenario':s,'scenario_sha256':content_hash(s)})
    return cases


def validate_design(plan):
    if (plan['schema_version']!=VERSION or plan['micro_budget']!=CAP or tuple(plan['training_seeds'])!=SEEDS
            or plan['opponents']!=['league_s0'] or plan['evaluation_games']!=2560
            or plan['models']!=list(MODELS) or plan['training_total_cap']!=65536 or plan['Adam_total_cap']!=2048
            or plan['workers']!=4 or plan['CPU_percent']!=50 or plan['memory_mib']!=8192
            or plan['device']!='cpu' or plan['teacher_enabled'] is not False):
        raise ValueError('MATCHUP_CONTROL_BLOCKED:study_contract')
    train,ind=plan['training_rosters'],plan['independent_rosters']
    if len(train)!=16 or len(ind)!=16:raise ValueError('MATCHUP_CONTROL_BLOCKED:team_count')
    keys=[]
    for rosters,partition in ((train,'train'),(ind,'validation')):
        hashes=set();joint=set()
        for row in rosters:
            team=row['team'];p=row['preview'];h=team_keys(team)
            if row['partition']!=partition or row['team_keys']!=h or len(team)!=6 or len(p)!=3 or len(set(p))!=3 or not all(1<=i<=6 for i in p):
                raise ValueError('MATCHUP_CONTROL_BLOCKED:roster_binding')
            if any(not 1<=len(x['moves'])<=4 for x in team):raise ValueError('MATCHUP_CONTROL_BLOCKED:move_slots')
            hashes.add(h['unordered']);joint.add(h['joint_movesets'])
        if len(hashes)!=16:raise ValueError('MATCHUP_CONTROL_BLOCKED:duplicate_team')
        keys.append((hashes,joint))
    if keys[0][0]&keys[1][0] or keys[0][1]&keys[1][1]:raise ValueError('MATCHUP_CONTROL_BLOCKED:identity_leakage')
    for condition in ('A','B'):
        if plan['schedules'][condition]!=schedule(condition):raise ValueError('MATCHUP_CONTROL_BLOCKED:schedule_changed')
        x=exposure(plan['schedules'][condition])
        if x['own']!={i:1024 for i in range(16)} or x['opponent']!={i:1024 for i in range(16)}:
            raise ValueError('MATCHUP_CONTROL_BLOCKED:exposure_not_balanced')
        if any(x['directed'].get(f'{b}:{a}')!=v for key,v in x['directed'].items() for a,b in [map(int,key.split(':'))]):
            raise ValueError('MATCHUP_CONTROL_BLOCKED:owner_direction_imbalance')
    if plan['evaluation_cases']!=evaluation_cases(train,ind):raise ValueError('MATCHUP_CONTROL_BLOCKED:evaluation_changed')
    used={tuple(sorted(map(int,k.split(':')))) for c in ('A','B')for k in exposure(plan['schedules'][c])['directed']}
    held={tuple(c['roster_indices']) for c in plan['evaluation_cases'] if c['scope']=='new_matchup'}
    if used&held:raise ValueError('MATCHUP_CONTROL_BLOCKED:reverse_pair_leakage')
    return True


def paired_analysis(rows,cases,*,draws=20000,seed=2026102811):
    by={(r['policy'],r['case'],r['seat']):r['record'] for r in rows}
    expected={(m,c['index'],s)for m in MODELS for c in cases for s in ('p1','p2')}
    if len(rows)!=2560 or set(by)!=expected:raise ValueError('matchup_evaluation_missing_or_duplicate')
    rng=np.random.default_rng(seed);result={}
    for scope in ('new_matchup','new_identity','all'):
        cs=[c for c in cases if scope=='all' or c['scope']==scope];pairs=sorted({c['pair']for c in cs})
        means={};outcomes={}
        for m in MODELS:
            rs=[by[m,c['index'],s]for c in cs for s in ('p1','p2')]
            outcomes[m]={'games':len(rs),'wins':sum(r['winner']=='self'and not r['truncated']for r in rs),
                'losses':sum(r['winner']=='opponent'and not r['truncated']for r in rs),
                'draws':sum(r['winner']is None and not r['truncated']for r in rs),'truncations':sum(r['truncated']for r in rs)}
            means[m]=np.asarray([np.mean([float(by[m,c['index'],s]['winner']=='self'and not by[m,c['index'],s]['truncated'])
                for c in cs if c['pair']==p for s in ('p1','p2')])for p in pairs])
        ix=rng.integers(0,len(pairs),size=(draws,len(pairs)));contrasts={}
        differences={**{m+'_minus_Foundation':means[m]-means['Foundation']for m in MODELS[1:]},
            'B_s1_minus_A_s1':means['B_s1']-means['A_s1'],'B_s2_minus_A_s2':means['B_s2']-means['A_s2'],
            'B_mean_minus_A_mean':(means['B_s1']+means['B_s2']-means['A_s1']-means['A_s2'])/2,
            'B_mean_minus_Foundation':(means['B_s1']+means['B_s2'])/2-means['Foundation']}
        for name,d in differences.items():contrasts[name]={'difference':float(d.mean()),'team_pair_cluster_95CI':np.quantile(d[ix].mean(1),[.025,.975]).tolist(),
            'pair_differences':dict(zip(map(str,pairs),map(float,d)))}
        result[scope]={'outcomes':outcomes,'comparisons':contrasts,'team_pair_clusters':len(pairs)}
    primary=result['new_matchup']['comparisons'];secondary=result['new_identity']['comparisons']
    censored=any(v['truncations']for v in result['all']['outcomes'].values())
    recombination=not censored and all(primary[f'B_s{s}_minus_A_s{s}']['difference']>0 for s in (1,2))and primary['B_mean_minus_A_mean']['team_pair_cluster_95CI'][0]>0
    independent=not censored and all(secondary[f'B_s{s}_minus_Foundation']['difference']>0 for s in (1,2))and secondary['B_mean_minus_Foundation']['team_pair_cluster_95CI'][0]>0
    no_gain=not censored and all(primary[f'B_s{s}_minus_A_s{s}']['difference']<=0 and secondary[f'B_s{s}_minus_Foundation']['difference']<=0 for s in (1,2))
    result.update(verdict='UNSEEN_TEAM_GENERALIZATION_SIGNAL'if independent else'RECOMBINATION_TRANSFER_SIGNAL'if recombination else'NO_OBSERVED_GENERALIZATION'if no_gain else'CONTROLLED_COMPARISON_INCONCLUSIVE',
        recombination_signal=recombination,unseen_team_signal=independent,
        uncertainty='paired team-pair clusters keep ownership directions/RNG/seats/models/both seeds together; only two continuation seeds, not a seed-population CI')
    return result
