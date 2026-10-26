"""Offline coordinator checks: zero native starts and zero optimizer updates."""
from copy import deepcopy

import pytest

from advisor.learned_selfplay_retry import classify_refresh, ResolvedRequestRateGuard
from advisor.learned_selfplay_pilot import StartBudget
from scripts.pilot_foundation_selfplay_exploration import verify_resume_state


def pair(kind='disabled', actor='self'):
    views = {}
    for side, owner in (('self', 'p1'), ('opponent', 'p2')):
        views[side] = {'side': side, 'episode_id': 'battle', 'revision': 8, 'turn': 5,
            'state_sha256': 'a'*64, 'public_history_sha256': 'b'*64,
            'own_request': {'side': {'id': owner, 'pokemon': [{'ident': owner+': slot-0', 'active': True}]},
                'active': [{'moves': [{'id': 'protect', 'pp': 5, 'maxpp': 8, 'disabled': False},
                                      {'id': 'tackle', 'pp': 8, 'maxpp': 16, 'disabled': False}]}]},
            'action_mask': [i in (1, 6, 7) for i in range(35)],
            'choices': ['switch 1','switch 2']+['unused']*4+['move 1','move 2']+['unused']*27}
    old = views[actor]['own_request']['active'][0]
    old['maybeDisabled' if kind=='disabled' else 'maybeTrapped'] = True
    q = {'ordinal': 8, 'decision_id': '8', 'before': views, 'actions': {'self': 7, 'opponent': 7},
        'result': {'action_rejected': True, 'decisions': 7, 'revision': 9,
            'terminated': False, 'truncated': False, 'winner': None, 'rewards': {'self': 0, 'opponent': 0}},
        'after': deepcopy(views)}
    q['actions'][actor] = 6 if kind=='disabled' else 1
    for v in q['after'].values(): v['revision'] += 1
    a = q['after'][actor]
    a['own_request']['update'] = True
    a['action_mask'][q['actions'][actor]] = False
    active = a['own_request']['active'][0]
    if kind=='disabled': active['moves'][0]['disabled'] = True
    else: active['trapped'] = True
    n = {'ordinal': 9, 'decision_id': '9', 'before': deepcopy(q['after']),
        'actions': {'self': 7, 'opponent': 7}, 'after': deepcopy(q['after']),
        'result': {**q['result'], 'action_rejected': False, 'decisions': 8, 'revision': 10}}
    for v in n['after'].values(): v['revision'] += 1
    return q, n


@pytest.mark.parametrize('kind', ['disabled', 'trapped'])
@pytest.mark.parametrize('actor', ['self', 'opponent'])
def test_resolution_requires_actual_commit_both_owners(kind, actor):
    q,n = pair(kind, actor)
    proof = classify_refresh(q,n,7)
    assert proof['classification']=='RESOLVED_REQUEST_REFRESH'
    assert proof['confirmed'][0]['side']==actor
    assert classify_refresh(q,n,None)['classification']=='UNRESOLVED'


@pytest.mark.parametrize('mutation', ['reward', 'native_gap', 'no_commit', 'revision_gap',
    'ordinal_duplicate', 'battle', 'actor', 'turn', 'history', 'state', 'request', 'illegal',
    'no_confirmed_disable', 'no_uncertainty', 'PP_consumed', 'terminal', 'no_update'])
def test_incomplete_or_conflicting_proof_remains_unresolved(mutation):
    q,n = pair()
    if mutation=='reward': q['result']['rewards']['self']=1
    elif mutation=='native_gap': n['result']['decisions']=9
    elif mutation=='no_commit': n['result']['action_rejected']=True
    elif mutation=='revision_gap': n['after']['self']['revision']+=1
    elif mutation=='ordinal_duplicate': n['ordinal']=8
    elif mutation=='battle': n['before']['self']['episode_id']='other'
    elif mutation=='actor': n['before']['self']['side']='opponent'
    elif mutation=='turn': q['after']['self']['turn']+=1
    elif mutation=='history': q['after']['self']['public_history_sha256']='new'
    elif mutation=='state': q['after']['self']['state_sha256']='new'
    elif mutation=='request': n['before']['self']['own_request']['side']['id']='p2'
    elif mutation=='illegal': n['actions']['self']=6
    elif mutation=='no_confirmed_disable':
        q['after']['self']['own_request']['active'][0]['moves'][0]['disabled']=False
        n['before']=deepcopy(q['after'])
    elif mutation=='no_uncertainty': q['before']['self']['own_request']['active'][0].pop('maybeDisabled')
    elif mutation=='PP_consumed':
        q['after']['self']['own_request']['active'][0]['moves'][0]['pp']-=1
        n['before']=deepcopy(q['after'])
    elif mutation=='terminal': q['result']['terminated']=True
    elif mutation=='no_update':
        q['after']['self']['own_request'].pop('update');n['before']=deepcopy(q['after'])
    assert classify_refresh(q,n,7)['classification']=='UNRESOLVED'


def accepted_row(ordinal, decisions, episode='battle'):
    q,n=pair()
    row=deepcopy(n);row['ordinal']=ordinal
    for stage,rev in [('before',ordinal),('after',ordinal+1)]:
        for v in row[stage].values():v['revision']=rev;v['episode_id']=episode
    row['result']['revision']=ordinal+1;row['result']['decisions']=decisions
    return row


def test_raw_rejections_survive_resolution_and_window_accounting():
    g=ResolvedRequestRateGuard()
    g.observe(accepted_row(7,7))
    q,n=pair();g.observe(q)
    assert g.statistics()['unresolved_rejections']==1
    g.observe(n)
    assert g.rejections==1 and g.resolved==1 and g.windows[0]['unresolved']==0
    assert g.statistics()['raw_attempts']==3


def test_unproved_six_of_512_still_stop_without_boundary_deferral():
    g=ResolvedRequestRateGuard();decision=0
    for i in range(512):
        row=accepted_row(i,decision+1)
        if i in (10,100,200,300,400,511):
            row['result'].update(action_rejected=True,decisions=decision)
        else:decision+=1
        if i==511:
            with pytest.raises(ValueError,match='unresolved_interval_retry'):g.observe(row)
        else:g.observe(row)
    assert g.rejections==6 and g.resolved==0


def test_eight_same_request_guard_is_not_bypassed(tmp_path):
    from test_bounded_selfplay_pilot import trace_fixture
    from advisor.learned_difficulty_calibration import PublicRetryAudit
    w,r,submit=trace_fixture(tmp_path,PublicRetryAudit(17),ResolvedRequestRateGuard())
    try:
        for _ in range(7):submit(True)
        with pytest.raises(ValueError,match='native_progress_alert'):submit(True)
        assert w.rate.rejections==7 and r.ordinal==8
    finally:w.stream.close();w.raw.close()


def test_recovery_start_offsets_and_additional_budget_are_separate(tmp_path):
    b=StartBudget(tmp_path/'new',2,tmp_path/'STOP',1258)
    assert b.reserve({})==1258 and b.reserve({})==1259 and b.count==2
    with pytest.raises(RuntimeError,match='budget'):b.reserve({})
    assert StartBudget(tmp_path/'new',2,tmp_path/'STOP',1258).count==2


def test_resume_rejects_wrong_parent_clock_or_counter(tmp_path):
    from advisor.learned_execution_alignment import digest
    path=tmp_path/'checkpoint.zip';path.write_bytes(b'unchanged')
    r={'checkpoint_path':str(path),'checkpoint_SHA256':digest(path),'checkpoint_trained':57344,
       'checkpoint_Adam_steps':34560}
    s={'latest':str(path),'latest_model_sha256':digest(path),'trained_rollout_transitions':57344,
       'experiment_steps':57344,'transitions':57344,'optimizer_steps':34560,'launches':1}
    verify_resume_state({'recovery':r},s)
    for key in ('trained_rollout_transitions','experiment_steps','transitions','optimizer_steps','launches'):
        bad={**s,key:s[key]+1}
        with pytest.raises(ValueError,match='durable_state'):verify_resume_state({'recovery':r},bad)


def test_optimizer_cap_counts_lost_192_steps_without_any_optimizer_computation():
    from advisor.learned_selfplay_signal_audit import require_step_budget
    p={'parent':{'optimizer_steps':32768},'recovery':{
       'checkpoint_Adam_steps':34560,'prior_actual_steps':1984}}
    require_step_budget(p,34560)
    require_step_budget(p,34815)
    assert 1984+34816-34560==2240
    with pytest.raises(ValueError,match='step_cap'):require_step_budget(p,34816)
    with pytest.raises(ValueError,match='step_cap'):require_step_budget(p,34559)


def test_frozen_provider_exposes_required_immutable_batch_identity(tmp_path):
    from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases
    rows={7:{'scenario_sha256':'a'*64,'scenario':{'seed':9}}}
    b=StartBudget(tmp_path/'starts',1,tmp_path/'STOP')
    f=FrozenEvalCases(rows,b,'parent','foundation_argmax','p1','b'*64)
    assert f.identity['case_count']==1 and f.identity['plan_SHA256']=='b'*64
    copy=f('validation',7);copy['seed']=10
    assert rows[7]['scenario']['seed']==9 and b.count==1


def test_cumulative_evaluation_callback_persists_all64_once(tmp_path):
    from scripts.pilot_foundation_selfplay_exploration import persist_evaluation_batch
    lookup={i:{'scenario_sha256':str(i),'scenario':{'seed':i+1000}} for i in range(64)}
    records=[{'case':i,'canonical_scenario_sha256':str(i),'initial_native_seed':i+1000,
              'candidate_seat':'p1','policy':'parent','opponent':'foundation_argmax'} for i in range(64)]
    args=({'parent':{'sha256':'a'*64}},lookup,'parent','foundation_argmax','p1','b'*64)
    assert persist_evaluation_batch(tmp_path,records[:16],*args)==16
    assert persist_evaluation_batch(tmp_path,records,*args)==48
    assert persist_evaluation_batch(tmp_path,records,*args)==0
    assert len(list(tmp_path.glob('*.receipt.json')))==64
    bad=deepcopy(records);bad[0]['unexpected_modified_outcome']='changed'
    with pytest.raises(ValueError,match='receipt_conflict'):persist_evaluation_batch(tmp_path,bad,*args)
    with pytest.raises(ValueError,match='duplicate_evaluation'):persist_evaluation_batch(tmp_path,records+records[:1],*args)


@pytest.mark.parametrize('seat',['p1','p2'])
@pytest.mark.parametrize('per_game',[False,True])
def test_maintained_evaluator_return_and_batch_callback_without_native(tmp_path,monkeypatch,seat,per_game):
    from types import SimpleNamespace
    from scripts import evaluate_showdown_policy as evaluator
    from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases,persist_evaluation_batch
    from advisor.learned_encoder import fingerprint
    from advisor import learned_tactical_curriculum
    class FakeEnvironment:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def observation(self,side,**kw):
            return {'public_history':[],'revision':0,'action_mask':[i==6 for i in range(35)],'request_state':'move'}
        def step(self,*a,**kw):
            return {'winner':'self','rewards':{'self':1,'opponent':-1},'terminated':True,
                    'truncated':False,'action_rejected':False}
    monkeypatch.setattr(evaluator,'ShowdownEnvironment',FakeEnvironment)
    monkeypatch.setattr(learned_tactical_curriculum,'reset_learning_episode',lambda *a:{})
    rows={i:{'scenario':{'seed':i,'teams':{'self':['own'],'opponent':['other']}},
             'scenario_sha256':fingerprint({'seed':i,'teams':{'self':['own'],'opponent':['other']}})} for i in range(64)}
    directory=tmp_path/'receipts';directory.mkdir()
    provider=FrozenEvalCases(rows,StartBudget(tmp_path/'intents',64,tmp_path/'STOP'),'parent','rival',seat,'p')
    completed=[]
    def progress(batch):
        completed.append(persist_evaluation_batch(directory,batch,{'parent':{'sha256':'model'}},rows,
                                                  'parent','rival',seat,'p'))
    result=evaluator.evaluate('unused','unused',{'parent':SimpleNamespace(act=lambda v:6,model_id='model')},
        cases=64,rivals={'rival':SimpleNamespace(act=lambda v:6,model_id='rival')},case_provider=provider,
        candidate_seat=seat,progress=progress,per_game_progress=per_game)
    assert completed==([1]*64+[0] if per_game else [64]) and len(result['records'])==64
    assert result['evaluation_case_bank']==provider.identity
    assert len(list(directory.glob('*.receipt.json')))==64
