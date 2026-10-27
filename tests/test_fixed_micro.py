"""Pure contract checks: no native starts, learner updates or model writes."""
from copy import deepcopy
import numpy as np
import pytest
from advisor.learned_fixed_micro import FixedMicroCases, EpisodeRival, paired_summary, seed4
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
