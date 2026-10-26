"""Offline contract tests: no native starts, PPO or optimizer updates."""
from copy import deepcopy
import pickle
import gzip
import json
from types import SimpleNamespace

import numpy as np
import pytest

from advisor.learned_selfplay_pilot import (
    StartBudget, FrozenPublicActor, PilotEnvFactory, exploration_gate, OPPONENTS, NativePublicTrace,
)


def view():
    return {'side':'opponent','own_request':{'side':{'id':'p2'}},
            'action_mask':[i in (6,7) for i in range(35)],'choices':[str(i) for i in range(35)]}


class Actor:
    model_id='a'*64
    def __init__(self):self.received=[]
    def infer(self, observation):
        self.received.append(deepcopy(observation))
        p=[0.]*35;p[6]=.25;p[7]=.75
        return {'action_index':7,'action_probabilities':p}


def test_frozen_argmax_and_sampling_reproducible_and_legal():
    a,b=Actor(),Actor()
    fixed=FrozenPublicActor(a,'argmax',4)
    sampled=FrozenPublicActor(a,'T1_sample',4)
    same=FrozenPublicActor(b,'T1_sample',4)
    assert all(fixed.act(view())==7 for _ in range(20))
    x=[sampled.act(view()) for _ in range(100)]
    assert x==[same.act(view()) for _ in range(100)] and set(x)=={6,7}
    assert sampled.model_id=='a'*64 and sampled.last['mode']=='T1_sample'


@pytest.mark.parametrize('key',['native_state','teams','seed','opponent_request','future','labels'])
def test_private_root_rejected_before_actor(key):
    a=Actor();s=FrozenPublicActor(a,'T1_sample',1)
    with pytest.raises(ValueError):s.act({**view(),key:{'hidden':True}})
    assert not a.received


def test_request_owner_and_unknown_boundary():
    a=Actor();s=FrozenPublicActor(a,'argmax',1)
    v=view();v['own_request']['side']['id']='p1'
    with pytest.raises(ValueError):s.act(v)
    v=view();v['state']={'opponent_side':{'known_item':{'knowledge':'unknown'}}}
    assert s.act(v)==7
    assert a.received[-1]['state']==v['state']


def test_hidden_coordinator_mutation_has_no_policy_input_or_output():
    v=view();a=Actor();s=FrozenPublicActor(a,'argmax',1)
    hidden={'teams':'first','future_rng':42}
    before=s.act(v);hidden.update(teams='different',future_rng=99)
    assert s.act(deepcopy(v))==before and a.received[0]==a.received[1]


def test_budget_intents_unique_count_and_reopen(tmp_path):
    b=StartBudget(tmp_path/'starts',2,tmp_path/'STOP')
    assert b.reserve({'role':'first'})==0
    b=StartBudget(tmp_path/'starts',2,tmp_path/'STOP')
    assert b.reserve({'role':'second'})==1
    with pytest.raises(RuntimeError,match='budget'):b.reserve({})
    assert len(list((tmp_path/'starts').glob('start_*.json')))==2


def test_STOP_blocks_only_new_intents(tmp_path):
    b=StartBudget(tmp_path/'starts',2,tmp_path/'STOP')
    b.reserve({});(tmp_path/'STOP').touch()
    with pytest.raises(RuntimeError,match='STOP'):b.reserve({})
    assert b.count==1


def test_first_rollout_gate_passes_only_real_legal_exploration():
    p=np.zeros((512,35));p[:,:10]=.1;m=p>0
    a=np.arange(512)%10
    assert exploration_gate(p,m,a,['attack','switch']*256)['passed']
    assert not exploration_gate(p,m,np.zeros(512,int),['attack']*512)['passed']
    assert not exploration_gate(p,m,a,['wait','replacement']*256)['passed']
    m[:,1]=False
    with pytest.raises(ValueError):exploration_gate(p,m,a,['attack']*512)


def test_factory_spawn_contains_only_paths_and_identities():
    f=PilotEnvFactory('checkout','catalog','encoder',0,'showdown-learning-curriculum-v8',
        OPPONENTS,{'league_s0':('parent.zip','a'*64),'league_anchor':('parent.zip','a'*64)},pilot_root='output')
    assert pickle.loads(pickle.dumps(f))==f
    assert not any(hasattr(x,'policy') for x in f.__dict__.values())


def trace_fixture(tmp_path, retry, rate):
    views={s:{'side':s,'episode_id':'episode','revision':0,'state':{},'public_history':[],
        'own_request':{},'action_mask':[i==6 for i in range(35)],'choices':[str(i) for i in range(35)]}
        for s in ('self','opponent')}
    path=tmp_path/'trace.gz';raw=path.open('xb');stream=gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)
    w=SimpleNamespace(stream=stream,raw=raw,directory=tmp_path,trace_path=path,episode=7,
                      retry=retry,rate=rate,last_result=None)
    r=NativePublicTrace(w);r._before=views
    class Native:
        def observation(self,side,include_history=True):return views[side]
        def checkpoint(self):raise AssertionError('hidden native truth forbidden')
    def submit(rejected):
        r.pending={'ordinal':r.ordinal,'actions':{'self':6,'opponent':6}}
        r._before['self']['revision']+=1
        result={'action_rejected':rejected,'decisions':0}
        r.native_after(Native(),result)
    return w,r,submit


def test_rate_guard_still_stops_at_512_but_persists_trigger_row(tmp_path):
    from advisor.learned_difficulty_calibration import AttemptRateGuard
    retry=SimpleNamespace(observe=lambda event:None)
    w,r,submit=trace_fixture(tmp_path,retry,AttemptRateGuard())
    try:
        for i in range(511):submit(i in (10,100,200,300,400,500))
        with pytest.raises(ValueError,match='interval_retry_rate_above_one_percent'):
            submit(False)  # Aggregate rate alarm need not be a current rejection.
        assert w.rate.attempts==512 and w.rate.rejections==6 and r.ordinal==512
        proof=json.loads(next(tmp_path.glob('guard_failure_*.json')).read_text())
        assert proof['row']['result']['action_rejected'] is False
        assert proof['rate_attempts']==512 and proof['rate_rejections']==6
        assert proof['guard_behavior_changed'] is False
    finally:w.stream.close();w.raw.close()
    with gzip.open(w.trace_path,'rt') as f:assert len(list(f))==512


def test_unresolved_eight_rejections_still_stop_and_are_saved(tmp_path):
    from advisor.learned_difficulty_calibration import AttemptRateGuard,PublicRetryAudit
    w,r,submit=trace_fixture(tmp_path,PublicRetryAudit(17),AttemptRateGuard())
    try:
        for _ in range(7):submit(True)
        with pytest.raises(ValueError,match='native_progress_alert'):submit(True)
        assert r.ordinal==8 and w.rate.attempts==7  # Original guard ordering.
        proof=json.loads(next(tmp_path.glob('guard_failure_*.json')).read_text())
        assert proof['row']['result']['action_rejected'] is True
    finally:w.stream.close();w.raw.close()
    with gzip.open(w.trace_path,'rt') as f:assert len(list(f))==8
