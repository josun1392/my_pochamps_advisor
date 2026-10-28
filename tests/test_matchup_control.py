"""Pure/toy contracts: no native battles, Foundation updates or model writes."""
from collections import Counter
from copy import deepcopy
import json
import numpy as np
import pytest
from advisor.learned_matchup_control import (VERSION,SEEDS,MODELS,CAP,SlotCases,
    factorization,schedule,exposure,evaluation_cases,validate_design,paired_analysis)
from advisor.learned_diverse_micro import team_keys


def rosters(offset,partition):
    rows=[]
    for i in range(16):
        team=[{'species':f'Species{i+offset}_{j}','moves':[f'm{j}_{k}'for k in range(4)]}for j in range(6)]
        rows.append({'team':team,'preview':[3,1,6],'partition':partition,'bank_index':i,
            'team_keys':team_keys(team)})
    return rows


def plan():
    a,b=rosters(0,'train'),rosters(100,'validation')
    return {'schema_version':VERSION,'micro_budget':deepcopy(CAP),'training_seeds':list(SEEDS),
        'opponents':['league_s0'],'evaluation_games':2560,'workers':4,'CPU_percent':50,
        'memory_mib':8192,'device':'cpu','teacher_enabled':False,'training_rosters':a,'independent_rosters':b,
        'models':list(MODELS),'training_total_cap':65536,'Adam_total_cap':2048,
        'schedules':{c:schedule(c)for c in ('A','B')},'evaluation_cases':evaluation_cases(a,b)}


def rows(p):
    return [{'policy':m,'case':c['index'],'seat':s,'record':{'winner':'self'if c['replicate']%2 else'opponent','truncated':False}}
        for m in MODELS for c in p['evaluation_cases']for s in ('p1','p2')]


def test_all120_unordered_edges_partition_into15_legal_perfect_matchings():
    rounds=factorization()
    assert len(rounds)==15 and rounds[0]==[[i,i+1]for i in range(0,16,2)]
    edges=[tuple(x)for r in rounds for x in r]
    assert len(edges)==len(set(edges))==120
    assert all(sorted(x for edge in r for x in edge)==list(range(16))for r in rounds)


def test_exact_transition_exposure_same_roles_and_reciprocal_ownership():
    p=plan();assert validate_design(p)
    margins={}
    for c in ('A','B'):
        x=exposure(p['schedules'][c]);margins[c]=x
        assert x['own']==x['opponent']=={i:1024 for i in range(16)}
        assert sum(x['own'].values())==16384
        assert len(x['directed'])==(16 if c=='A' else 64)
        for k,v in x['directed'].items():
            a,b=k.split(':');assert x['directed'][f'{b}:{a}']==v
    assert margins['A']['own']==margins['B']['own'] and margins['A']['opponent']==margins['B']['opponent']
    for segment in range(16):
        assert [s['own']for s in p['schedules']['A'][segment]['slots']]==[s['own']for s in p['schedules']['B'][segment]['slots']]


def test_slot_scenarios_keep_own_identity_preview_and_matched_rng():
    p=plan()
    for segment in range(16):
        for w in range(4):
            a,b=[SlotCases(p,c,SEEDS[0],segment,w)for c in ('A','B')]
            for index in range(3):
                x,y=a('train',index),b('train',index)
                assert x['teams']['self']==y['teams']['self'] and x['preview']['self']==y['preview']['self']
                assert x['seed']==y['seed']
                if segment<4:assert x['teams']['opponent']==y['teams']['opponent']
                else:assert x['teams']['opponent']!=y['teams']['opponent']
    with pytest.raises(ValueError):SlotCases(p,'A',SEEDS[0],0,0)('validation',0)


def test_held_matchups_never_share_reverse_edge_and_identity_split_is_separate():
    p=plan();cs=p['evaluation_cases']
    used={tuple(sorted(map(int,k.split(':'))))for c in ('A','B')for k in exposure(p['schedules'][c])['directed']}
    held={tuple(c['roster_indices'])for c in cs if c['scope']=='new_matchup'}
    assert len(used)==32 and len(held)==8 and not used&held
    assert len(cs)==256 and Counter(c['scope']for c in cs)=={'new_matchup':128,'new_identity':128}
    for pair in range(16):
        group=[c for c in cs if c['pair']==pair]
        assert {c['direction']for c in group}=={0,1} and len(group)==16
        assert len({tuple(c['scenario']['seed'])for c in group})==8


@pytest.mark.parametrize('mutation',('schedule','roster','seed','budget','preview','opponent'))
def test_fail_closed_design(mutation):
    p=plan()
    if mutation=='schedule':p['schedules']['B'][0]['slots'][0]['opponent']=2
    elif mutation=='roster':p['independent_rosters'][0]=deepcopy(p['training_rosters'][0])
    elif mutation=='seed':p['training_seeds'][1]+=1
    elif mutation=='budget':p['micro_budget']['Adam']+=1
    elif mutation=='preview':p['training_rosters'][0]['preview']=[1,1,2]
    else:p['opponents']=['league_anchor']
    with pytest.raises(ValueError,match='MATCHUP_CONTROL_BLOCKED'):validate_design(p)


@pytest.mark.parametrize('bad',('duplicate','missing'))
def test_evaluation_slot_set_exact(bad):
    p=plan();r=rows(p)
    if bad=='missing':r.pop()
    else:r[-1]=r[0]
    with pytest.raises(ValueError):paired_analysis(r,p['evaluation_cases'],draws=10)


def test_pair_cluster_preserves_both_repetitions_and_does_not_select_best_seed():
    p=plan();r=rows(p);a=paired_analysis(r,p['evaluation_cases'],draws=500)
    assert a['verdict']=='NO_OBSERVED_GENERALIZATION'
    assert a['new_matchup']['team_pair_clusters']==8
    for row in r:
        c=p['evaluation_cases'][row['case']]
        if row['policy'] in ('B_s1','B_s2')and c['pair']==0:row['record']['winner']='self'
    a=paired_analysis(r,p['evaluation_cases'],draws=500)
    assert a['new_matchup']['comparisons']['B_mean_minus_A_mean']['difference']==.0625
    assert a['new_matchup']['comparisons']['B_mean_minus_A_mean']['team_pair_cluster_95CI'][0]==0
    assert a['verdict']=='CONTROLLED_COMPARISON_INCONCLUSIVE'


def test_new_matchup_signal_is_not_new_identity_signal():
    p=plan();r=rows(p)
    for row in r:
        if row['policy']in('B_s1','B_s2')and p['evaluation_cases'][row['case']]['scope']=='new_matchup':row['record']['winner']='self'
    a=paired_analysis(r,p['evaluation_cases'],draws=100)
    assert a['verdict']=='RECOMBINATION_TRANSFER_SIGNAL' and not a['unseen_team_signal']


def test_vector_factory_is_explicit_and_old_callers_cannot_inject_new_slots(tmp_path,monkeypatch):
    import advisor.learned_fixed_micro as owner
    import advisor.learned_gym as gym_owner
    import advisor.learned_combat_foundation as foundation
    import stable_baselines3.common.vec_env as vec
    from advisor.learned_selfplay_pilot import StartBudget
    p={**plan(),'checkout':'unused','catalog':'unused'}
    with pytest.raises(ValueError,match='fixed_slot'):owner.training_vector(p,tmp_path,None)
    monkeypatch.setattr(vec,'DummyVecEnv',lambda fs:[f()for f in fs])
    monkeypatch.setattr(gym_owner,'ShowdownLearningEnv',lambda *a,**k:k)
    monkeypatch.setattr(foundation,'FoundationCombatEncoder',lambda c:c)
    monkeypatch.setattr(foundation,'install_environment_profile',lambda env:None)
    monkeypatch.setattr(owner,'AuditedPilotEnv',lambda env,*args:env)
    budget=StartBudget(tmp_path/'starts',4096,tmp_path/'STOP')
    result,b=owner.training_vector(p,tmp_path/'segment',None,case_factory=lambda w:SlotCases(p,'B',SEEDS[0],0,w),start_budget=budget)
    assert b is budget and b.count==4
    assert all(e['opponents']==('league_s0',)for e in result)
    with pytest.raises(ValueError):owner.training_vector({'templates':[]},tmp_path/'old',None,case_factory=lambda w:w)


def test_fresh_segment_uses_maintained_SB3_episode_start_without_optimizer_update():
    import gymnasium as gym
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from advisor.learned_parent_anchor import optimizer_digest
    class Toy(gym.Env):
        observation_space=gym.spaces.Box(-10,10,(1,),dtype=np.float32)
        action_space=gym.spaces.Discrete(35)
        def __init__(self,value):self.value=value
        def reset(self,seed=None,options=None):return np.array([self.value],np.float32),{}
        def step(self,action):raise AssertionError('no rollout collection authorized in this unit test')
    old=DummyVecEnv([lambda:Toy(1)for _ in range(4)])
    new=DummyVecEnv([lambda:Toy(7)for _ in range(4)])
    try:
        m=MaskablePPO('MlpPolicy',old,n_steps=128,batch_size=128,n_epochs=4,device='cpu',gamma=1,gae_lambda=.95)
        m.num_timesteps=512;m._last_obs=np.ones((4,1),np.float32);m._last_episode_starts=np.zeros(4,bool)
        before=optimizer_digest(m.policy);m.set_env(new,force_reset=True)
        m._setup_learn(1024,reset_num_timesteps=False)
        assert m.num_timesteps==512 and m._last_episode_starts.all()
        np.testing.assert_array_equal(m._last_obs,np.full((4,1),7,np.float32))
        assert optimizer_digest(m.policy)==before
    finally:old.close();new.close()


def test_duplicate_launch_refused_before_any_native_start(tmp_path):
    from scripts.pilot_foundation_matchup_control import run
    (tmp_path/'started.json').write_text('{}',encoding='utf8')
    with pytest.raises(ValueError,match='already_started'):run(tmp_path)
    assert not(tmp_path/'EVAL_starts').exists()


def test_five_models_exact_2560_real_seat_slots_and_receipt_storage_without_native(tmp_path,monkeypatch):
    import scripts.pilot_foundation_matchup_control as runner
    import scripts.evaluate_showdown_policy as evaluator
    import advisor.learned_response_predictor as boundary
    import advisor.learned_difficulty_calibration as guards
    import advisor.learned_selfplay_retry as rates
    p={**plan(),'checkout':'unused','catalog':'unused'}
    (tmp_path/'plan.json').write_text(json.dumps(p),encoding='utf8')
    monkeypatch.setattr(boundary,'public_input',lambda v:v)
    monkeypatch.setattr(guards,'PublicRetryAudit',lambda e:type('Guard',(),{'observe':lambda self,event:None})())
    monkeypatch.setattr(rates,'ResolvedRequestRateGuard',lambda:type('Rate',(),{'observe':lambda self,event:None,'statistics':lambda self:{'raw_rejections':0}})())
    players={m:type('Actor',(),{'model_id':m})()for m in MODELS};runtime=type('Runtime',(),{'stopping':lambda self:False})()
    calls=[]
    def evaluate(checkout,catalog,policies,**kw):
        name=next(iter(policies));seat=kw['candidate_seat'];side='self'if seat=='p1'else'opponent'
        calls.append((name,seat,kw['offset']));rs=[]
        for i in range(kw['offset'],kw['offset']+kw['cases']):
            case=kw['case_provider']('validation',i)
            kw['transition_observer']({'before':{side:{'episode_id':f'{seat}:{i}','side':side}},'result':{}})
            rs.append({'case':i,'policy':name,'opponent':'league_s0','candidate_seat':seat,
                'canonical_scenario_sha256':p['evaluation_cases'][i]['scenario_sha256'],'initial_native_seed':case['seed'],
                'winner':'self','truncated':False})
        kw['progress'](rs)
    monkeypatch.setattr(evaluator,'evaluate',evaluate)
    runner.eval_panel(tmp_path,p,players,players['Foundation'],runtime)
    rows=[json.loads(f.read_text())for f in(tmp_path/'evaluation').glob('*.receipt.json')]
    assert len(calls)==80 and len(rows)==2560
    assert len({(r['policy'],r['case'],r['seat'])for r in rows})==2560
    assert len(list((tmp_path/'evaluation_roots').glob('*.json')))==512
