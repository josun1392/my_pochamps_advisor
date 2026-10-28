"""Pure contract checks: no native starts, learner updates or model writes."""
from copy import deepcopy
import numpy as np
import pytest
from advisor.learned_fixed_micro import FixedMicroCases, EpisodeRival, paired_summary, seed4, micro_budget, CURVE_VERSION
from advisor.learned_selfplay_pilot import OPPONENTS


def cases():
    return [{'index':r*16+j,'scope':'seen'if j<8 else'heldout',
             'family':str((j//4)%2),'rival':rival}
            for r,rival in enumerate(OPPONENTS)for j in range(16)]


def records():
    return [{'model':m,'record':{'case':c['index'],'candidate_seat':s,
            'winner':'self'if c['index']%2 else'opponent','truncated':False}}
            for m in ('Foundation','Micro')for c in cases()for s in ('p1','p2')]


def test_train_cases_are_deterministic_disjoint_and_rival_balanced():
    plan={'seed':104027,'templates':[{'scenario':{'family':i,'seed':[0]}}for i in range(2)]}
    sampler=FixedMicroCases(plan)
    for family in range(2):
        indices=range(family*4,family*4+4)
        assert {sampler('train',i)['family']for i in indices}=={family}
        assert {OPPONENTS[i%4]for i in indices}==set(OPPONENTS)
    a=sampler('train',0);a['seed'][0]=-1
    assert sampler('train',0)==FixedMicroCases(deepcopy(plan))('train',0)
    assert seed4('TRAIN:0')!=seed4('EVAL:0')
    with pytest.raises(ValueError):sampler('test',0)
    with pytest.raises(ValueError):sampler('train',-1)


def test_paired_seats_stay_in_clusters_and_draws_not_truncations():
    rows=records()
    for row in rows:
        if row['model']=='Micro'and row['record']['candidate_seat']=='p2':
            row['record'].update(winner=None,truncated=True)
    result=paired_summary(rows,cases(),draws=1000)
    assert result['heldout']['outcomes']['Micro']=={'wins':16,'losses':16,'draws':0,'truncations':32,'games':64}
    assert result['heldout']['Micro_minus_Foundation_winrate']==-.25
    assert result['heldout']['clusters']==32
    assert result['heldout']['case_seed_cluster_95CI'][1]<=0


def test_identical_outputs_have_zero_paired_difference():
    result=paired_summary(records(),cases(),draws=1000)
    assert result['verdict']=='MICRO_INCONCLUSIVE'
    assert result['heldout']['case_seed_cluster_95CI']==[0.,0.]


@pytest.mark.parametrize('bad',('missing','duplicate'))
def test_no_missing_or_duplicate_receipts(bad):
    rows=records()
    if bad=='missing':rows.pop()
    else:rows[-1]=rows[0]
    with pytest.raises(ValueError):paired_summary(rows,cases(),draws=10)


def test_case_addressed_opponent_rng_repeats_without_model_identity_in_seed(monkeypatch):
    import advisor.learned_fixed_micro as micro
    class Fake:
        def __init__(self, actor, mode, seed):self.rng=np.random.default_rng(seed)
        def act(self, view):return int(self.rng.integers(0,35))
    monkeypatch.setattr(micro,'FrozenPublicActor',Fake)
    parent=type('Parent',(),{'model_id':'immutable'})()
    rival=EpisodeRival('league_anchor',parent)
    with pytest.raises(ValueError):rival.act({})
    rival.reset(12);a=[rival.act({})for _ in range(10)]
    rival.reset(12);assert a==[rival.act({})for _ in range(10)]


def test_training_adapter_shares_one_durable_budget_and_creates_trace_directories(tmp_path,monkeypatch):
    import advisor.learned_fixed_micro as micro
    import advisor.learned_gym as gym_owner
    import advisor.learned_combat_foundation as foundation
    import stable_baselines3.common.vec_env as vec
    monkeypatch.setattr(vec,'DummyVecEnv',lambda factories:[f()for f in factories])
    monkeypatch.setattr(gym_owner,'ShowdownLearningEnv',lambda *a,**k:k)
    monkeypatch.setattr(foundation,'FoundationCombatEncoder',lambda c:c)
    monkeypatch.setattr(foundation,'install_environment_profile',lambda env:None)
    wrappers=[]
    def wrapped(env,directory,budget,ordinal,worker,classified):
        assert directory.is_dir()and classified
        wrappers.append((budget,ordinal,worker,env))
        return env
    monkeypatch.setattr(micro,'AuditedPilotEnv',wrapped)
    plan={'seed':104027,'checkout':'no native','catalog':'no model','templates':[]}
    vector,budget=micro.training_vector(plan,tmp_path,object())
    assert len(vector)==4 and budget.count==4 and budget.maximum==512
    assert {id(w[0])for w in wrappers}=={id(budget)}
    assert [w[1]for w in wrappers]==list(range(4))
    assert all(w[3]['opponents']==OPPONENTS and w[3]['collect_v5_supervision']for w in wrappers)


def test_existing_launch_refused_before_any_new_native_start(tmp_path):
    from scripts.pilot_foundation_fixed_micro import run
    (tmp_path/'plan.json').write_text('{}',encoding='utf8')
    (tmp_path/'started.json').write_text('{}',encoding='utf8')
    with pytest.raises(ValueError,match='existing_micro_run'):
        run(tmp_path)
    assert not(tmp_path/'EVAL_starts').exists()


def test_exact_16k_resume_cap_is_opt_in_and_old_budget_is_unchanged():
    assert micro_budget({})=={'transitions':4096,'Adam':128,'starts':512,'targets':[1024,2048,3072,4096]}
    cap={'transitions':12288,'Adam':384,'starts':1024,'targets':[4096,8192,12288]}
    plan={'schema_version':CURVE_VERSION,'micro_prior_transitions':4096,'micro_budget':cap}
    assert micro_budget(plan)==cap
    micro_budget(plan)['targets'].append(99999)
    assert micro_budget(plan)==cap
    for key,value in [('schema_version','other'),('micro_prior_transitions',0),('micro_budget',{**cap,'Adam':385})]:
        with pytest.raises(ValueError):micro_budget({**plan,key:value})


def test_frozen_curve_32_case_blocks_cover_all_roots_and_seats_without_native(tmp_path,monkeypatch):
    from scripts.pilot_foundation_fixed_micro import eval_phase
    import scripts.evaluate_showdown_policy as evaluator
    calls=[]
    monkeypatch.setattr(evaluator,'evaluate',lambda *a,**kw:calls.append(kw))
    rows=[{'index':i,'scenario_sha256':str(i)}for i in range(128)]
    p={'evaluation_cases':rows,'evaluation_block_size':32,'checkout':'unused','catalog':'unused'}
    (tmp_path/'plan.json').write_text('{}',encoding='utf8')
    fake=type('Actor',(),{'model_id':'frozen'})()
    runtime=type('Runtime',(),{'stopping':lambda self:False})()
    eval_phase(p,tmp_path,'Foundation',fake,fake,None,runtime)
    assert len(calls)==8 and {c['candidate_seat']for c in calls}=={'p1','p2'}
    for seat in ('p1','p2'):
        indices=[i for c in calls if c['candidate_seat']==seat for i in range(c['offset'],c['offset']+c['cases'])]
        assert indices==list(range(128))
