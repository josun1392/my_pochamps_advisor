"""Offline contracts; no native starts, model updates or evaluation games."""
from copy import deepcopy
import pytest
from advisor.learned_diverse_micro import (DIVERSE_VERSION, CAP, SEEDS, MODELS,
    team_keys, build_templates, evaluation_cases, validate_plan, paired_analysis)
from advisor.learned_fixed_micro import FixedMicroCases, micro_budget


def bank():
    def team(n):return [{'species':f'Species{n}_{i}','moves':[f'm{n}_{i}_{j}' for j in range(4)]} for i in range(6)]
    return {'train':[team(i) for i in range(32)],'validation':[team(i+100) for i in range(32)]}


def plan():
    ts=build_templates(bank())
    return {'schema_version':DIVERSE_VERSION,'training_seeds':list(SEEDS),'seed':SEEDS[0],
        'micro_prior_transitions':0,'micro_budget':deepcopy(CAP),'opponents':['league_s0'],
        'evaluation_games':2048,'workers':4,'memory_mib':8192,'CPU_percent':50,'device':'cpu',
        'teacher_enabled':False,'templates':ts,'training_template_indices':list(range(16)),
        'evaluation_cases':evaluation_cases(ts)}


def rows(p):
    return [{'policy':m,'case':c['index'],'seat':s,'record':{'winner':'self' if c['replicate']%2 else 'opponent','truncated':False}}
        for m in MODELS for c in p['evaluation_cases'] for s in ('p1','p2')]


def test_freeze_reproducible_no_reciprocal_pair_leakage():
    p=plan();assert p==plan() and validate_plan(p)
    train={team_keys(team)['unordered'] for t in p['templates'] if t['scope']=='train' for team in t['scenario']['teams'].values()}
    independent={team_keys(team)['unordered'] for t in p['templates'] if t['scope']=='independent' for team in t['scenario']['teams'].values()}
    assert len(train)==len(independent)==16 and not train&independent
    assert len(p['evaluation_cases'])==256
    for pair in range(16):
        cs=[c for c in p['evaluation_cases'] if c['pair']==pair]
        assert len(cs)==16 and {c['direction'] for c in cs}=={0,1}
        assert len({tuple(c['scenario']['seed']) for c in cs})==8


def test_budget_exact_opt_in_and_unrelated_historical_defaults_unchanged():
    p=plan();assert micro_budget(p)==CAP
    micro_budget(p)['targets'].append(32768);assert micro_budget(p)==CAP
    assert micro_budget({})['transitions']==4096
    for key,value in [('micro_prior_transitions',4096),('opponents',['league_s0','league_anchor']),
                      ('micro_budget',{**CAP,'Adam':513})]:
        with pytest.raises(ValueError):micro_budget({**p,key:value})


@pytest.mark.parametrize('bad',('direction','seed','split','preview','opponent'))
def test_fail_closed_contract_mutations(bad):
    p=plan()
    if bad=='direction':p['templates'][1]['scenario']['teams']['self']=deepcopy(p['templates'][0]['scenario']['teams']['self'])
    if bad=='seed':p['training_seeds'][1]+=1
    if bad=='split':p['templates'][16]['partition']='train'
    if bad=='preview':p['templates'][0]['scenario']['preview']['self']=[1,1,2]
    if bad=='opponent':p['opponents']=['tactical_heuristic']
    with pytest.raises(ValueError):validate_plan(p)


def test_training_sampler_visits_only_all_train_directions():
    p=plan();sampler=FixedMicroCases(p)
    seen=set()
    for i in range(32):
        s=sampler('train',i);seen.add(team_keys(s['teams']['self'])['ordered'])
        assert s==FixedMicroCases(deepcopy(p))('train',i)
        assert s['seed']!=p['templates'][i%16]['scenario']['seed']
    assert len(seen)==16
    with pytest.raises(ValueError):sampler('validation',0)


def test_team_keys_preserve_move_slots_and_detect_reordered_full_team():
    t=bank()['train'][0];r=list(reversed(t))
    assert team_keys(t)['ordered']!=team_keys(r)['ordered']
    assert team_keys(t)['unordered']==team_keys(r)['unordered']
    changed=deepcopy(t);changed[0]['moves'].reverse()
    assert team_keys(t)['ordered']!=team_keys(changed)['ordered']
    assert team_keys(t)['joint_movesets']==team_keys(changed)['joint_movesets']


def test_native_valid_fewer_than_four_moves_are_not_silently_padded():
    b=bank()
    for teams in b.values():
        for team in teams:team[0]['moves']=team[0]['moves'][:1]
    templates=build_templates(b)
    assert all(len(t['scenario']['teams']['self'][0]['moves'])==1 for t in templates)


@pytest.mark.parametrize('bad',('missing','duplicate'))
def test_exact_paired_model_case_seat_set(bad):
    p=plan();r=rows(p)
    if bad=='missing':r.pop()
    else:r[-1]=r[0]
    with pytest.raises(ValueError):paired_analysis(r,p['evaluation_cases'],draws=10)


def test_cluster_keeps_directions_seats_rng_and_repeated_seed_models_together():
    p=plan();r=rows(p)
    result=paired_analysis(r,p['evaluation_cases'],draws=200)
    assert result['verdict']=='NO_OBSERVED_TRANSFER'
    assert result['independent']['team_pair_clusters']==8
    assert result['independent']['comparisons']['Diverse_mean_minus_Foundation']['team_pair_cluster_95CI']==[0.,0.]
    for row in r:
        c=p['evaluation_cases'][row['case']]
        if row['policy'] in MODELS[2:] and c['scope']=='independent' and c['pair']==8:
            row['record']['winner']='self'
    result=paired_analysis(r,p['evaluation_cases'],draws=200)
    assert result['independent']['comparisons']['Diverse_mean_minus_Foundation']['difference']==.0625
    assert result['independent']['comparisons']['Diverse_mean_minus_Foundation']['team_pair_cluster_95CI'][0]==0
    assert result['verdict']=='DIVERSE_MICRO_INCONCLUSIVE'


def test_no_duplicate_launch_before_any_new_start(tmp_path):
    from scripts.pilot_foundation_diverse_micro import run
    (tmp_path/'started.json').write_text('{}',encoding='utf8')
    with pytest.raises(ValueError,match='already_started'):run(tmp_path)
    assert not (tmp_path/'TRAIN_starts').exists()


def test_single_argmax_opponent_adapter_without_native(tmp_path,monkeypatch):
    import advisor.learned_fixed_micro as owner
    import advisor.learned_gym as gym_owner
    import advisor.learned_combat_foundation as foundation
    import stable_baselines3.common.vec_env as vector
    monkeypatch.setattr(vector,'DummyVecEnv',lambda fs:[f() for f in fs])
    monkeypatch.setattr(gym_owner,'ShowdownLearningEnv',lambda *a,**kw:kw)
    monkeypatch.setattr(foundation,'FoundationCombatEncoder',lambda x:x)
    monkeypatch.setattr(foundation,'install_environment_profile',lambda env:None)
    monkeypatch.setattr(owner,'AuditedPilotEnv',lambda env,*args:env)
    p={**plan(),'checkout':'unused','catalog':'unused'}
    env,budget=owner.training_vector(p,tmp_path,object())
    assert budget.maximum==2048 and budget.count==4 and len(env)==4
    assert all(x['opponents']==('league_s0',) and x['collect_v5_supervision'] for x in env)


def test_evaluation_exact_2048_case_model_seat_bindings_without_native(tmp_path,monkeypatch):
    import json
    import scripts.pilot_foundation_diverse_micro as runner
    import scripts.evaluate_showdown_policy as evaluator
    import advisor.learned_response_predictor as boundary
    import advisor.learned_difficulty_calibration as guards
    p={**plan(),'checkout':'unused','catalog':'unused'}
    (tmp_path/'plan.json').write_text(json.dumps(p),encoding='utf8')
    players={m:type('Actor',(),{'model_id':m})() for m in MODELS}
    runtime=type('Runtime',(),{'stopping':lambda self:False})()
    monkeypatch.setattr(boundary,'public_input',lambda v:v)
    monkeypatch.setattr(guards,'PublicRetryAudit',lambda episode:type('Guard',(),{'observe':lambda self,event:None})())
    calls=[]
    def evaluate(checkout,catalog,policies,**kw):
        name=next(iter(policies));seat=kw['candidate_seat'];side='self' if seat=='p1' else 'opponent'
        calls.append((name,seat,kw['offset']));records=[]
        for i in range(kw['offset'],kw['offset']+kw['cases']):
            case=kw['case_provider']('validation',i)
            kw['transition_observer']({'before':{side:{'episode_id':f'{seat}:{i}','side':side}},'result':{}})
            records.append({'case':i,'policy':name,'opponent':'league_s0','candidate_seat':seat,
                'canonical_scenario_sha256':p['evaluation_cases'][i]['scenario_sha256'],
                'initial_native_seed':case['seed'],'winner':'self','truncated':False})
        kw['progress'](records)
    monkeypatch.setattr(evaluator,'evaluate',evaluate)
    runner.eval_panel(tmp_path,p,players,players['Foundation'],runtime)
    receipts=[json.loads(f.read_text()) for f in (tmp_path/'evaluation').glob('*.receipt.json')]
    assert len(calls)==64 and len(receipts)==2048
    assert len({(r['policy'],r['case'],r['seat']) for r in receipts})==2048
    roots=[json.loads(f.read_text()) for f in (tmp_path/'evaluation_roots').glob('*.json')]
    assert len(roots)==512 and all(r['view']['side']==('self' if r['seat']=='p1' else 'opponent') for r in roots)


def test_detached_operational_revision_requires_original_plan_and_survival_proof(tmp_path,monkeypatch):
    import json
    import scripts.pilot_foundation_diverse_micro as runner
    from advisor.learned_execution_alignment import digest
    repo=tmp_path/'repo';repo.mkdir();(repo/'scripts').mkdir()
    f='scripts/pilot_foundation_diverse_micro.py';(repo/f).write_text('new launcher contract')
    root=tmp_path/'artifact';root.mkdir()
    def write(name,value):(root/name).write_text(json.dumps(value),encoding='utf8')
    write('plan.json',{'source_hashes':{f:'previous_SHA'},'input_hashes':{}})
    write('freeze.json',{'files':{}});write('persistence_probe_result.json',{'phase':'survived_launcher_exit'})
    r={'schema_version':'diverse-micro-detached-nested-job-proof-v1',
        'parent_plan_SHA256':digest(root/'plan.json'),'original_runner_SHA256':'previous_SHA',
        'source_hashes':{f:digest(repo/f)},'scientific_changes':[],
        'prior_native_starts':0,'prior_optimizer_updates':0,
        'persistence_probe_SHA256':digest(root/'persistence_probe_result.json')}
    write('execution_revision_02.json',r)
    monkeypatch.setattr(runner,'ROOT',repo);monkeypatch.setattr(runner,'validate_plan',lambda p:True)
    assert runner.verify(root)
    for key,value in [('scientific_changes',['different reward']),('prior_native_starts',1),
                      ('original_runner_SHA256','different'),('source_hashes',{'another.py':'hash'})]:
        write('execution_revision_02.json',{**r,key:value})
        with pytest.raises(ValueError,match='operational_revision'):runner.verify(root)
    write('execution_revision_02.json',r)
    write('persistence_probe_result.json',{'phase':'not_survived'})
    with pytest.raises(ValueError,match='operational_revision'):runner.verify(root)
