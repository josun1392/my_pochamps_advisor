"""Deterministic sampler, matched study and synthetic paired inference: no native games."""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest

from advisor.learned_opponent_curriculum import (
    BASELINE,COMPETITIVE,two_group_schedule,validate_schedule,stage_selection,next_boundary,
)
from advisor.learned_two_group_study import matched_configs,game_slots,analyze,POLICIES,SEEDS


def configs():
    base={"envs":4,"cpu_percent":50,"memory_mib":12288,"device":"cpu","vector_backend":"subproc",
        "transition_budget_scope":"trained_rollouts_v1","checkpoint_evaluation_mode":"disabled_for_frozen_study_v1",
        "validation_selection_mode":"diagnostic_fixed_budget_v1","checkpoint_steps":32768,
        "collect_opponent_selections":True,"training_subset":"same",
        "experiments":[{"steps":65536,"initial_model_id":"a"*64,"fresh_optimizer":False,"opponents":list(BASELINE),"gamma":1.}]}
    result={}
    for key in POLICIES[1:]:
        c=deepcopy(base);c['experiments'][0].update(name=key,seed=int(key[2:]))
        if key.startswith('B'):c['experiments'][0]['opponent_schedule']=two_group_schedule()
        result[key]=c
    return result


def cases():
    return [{"index":i,"scope":"train" if i<96 else "heldout","scenario_sha256":str(i),
             "rivals":["max_power",COMPETITIVE[i%6],COMPETITIVE[(i%6+1+(i//6)%2)%6]]} for i in range(192)]


def test_control_exact_legacy_modulo_and_no_RNG_effect():
    before=np.random.get_state()
    for i in range(2500):
        selected,receipt=stage_selection(None,BASELINE,i,0)
        assert selected==BASELINE[i%10] and receipt['stage'] is None
        assert receipt['probabilities']['max_power']==.1
    after=np.random.get_state()
    np.testing.assert_array_equal(before[1],after[1]);assert before[2:]==after[2:]


def test_exact_two_phase_slot_distributions_and_safe_resumed_boundaries():
    schedule=two_group_schedule()
    assert validate_schedule(schedule,BASELINE)==schedule
    for step,p in [(0,.4),(32767,.4),(32768,.1),(65536,.1)]:
        selections=[stage_selection(schedule,BASELINE,i,step)[0] for i in range(1500)]
        counts=Counter(selections)
        assert counts['max_power']/1500==p and set(counts)==set(BASELINE)
        for r,weight in Counter(BASELINE[1:]).items():
            assert counts[r]/1500==pytest.approx((1-p)*weight/9)
    assert next_boundary(schedule,1024,32768)==31744
    assert next_boundary(schedule,32768,32768)==32768
    assert next_boundary(None,1024,32768)==32768
    bad=deepcopy(schedule);bad['stages'][0]['start']=512
    with pytest.raises(ValueError):validate_schedule(bad,BASELINE)
    with pytest.raises(ValueError):stage_selection(schedule,BASELINE,1,65537)


def test_only_sampler_differs_same_Adam_and_matched_seeds():
    assert matched_configs(configs(),'a'*64)['trained_transitions']==262144
    for field,value in [('gamma',.99),('fresh_optimizer',True),('opponents',['random']),
                        ('steps',32768),('seed',99333),('parent_policy_anchor',{}),('learning_rate',.1)]:
        c=configs();c['B_99221']['experiments'][0][field]=value
        with pytest.raises(ValueError):matched_configs(c,'a'*64)


def test_exact_5760_argmax_two_seats_half_heldout_all_groups():
    slots=game_slots(cases());assert len(slots)==5760
    assert len({tuple(s.values()) for s in slots})==5760
    for policy in POLICIES:
        own=[s for s in slots if s['policy']==policy]
        assert len(own)==1152 and sum(s['scope']=='heldout' for s in own)==576
        assert sum(s['seat']=='p2' for s in own)==576
        assert Counter(s['rival'] for s in own)==Counter({'max_power':384,**dict.fromkeys(COMPETITIVE,128)})
    with pytest.raises(ValueError):game_slots([{**cases()[0],'rivals':['max_power']*3}])


def test_synthetic_primary_groups_parent_retention_and_incomplete_fail():
    small=[cases()[0],cases()[96]]
    rows=[{'slot':s,'record':{'winner':'self' if s['policy'].startswith('B') else 'opponent','truncated':False}}
          for s in game_slots(small)]
    result=analyze(rows,small,resamples=128)
    assert result['primary']=='argmax heldout all-rival mean_seed(B-A)' and result['curriculum_expansion']=='GO'
    assert set(result['opponent_groups'])=={'easy','competitive'}
    primary=next(d for d in result['paired_differences'] if d['scope']=='heldout' and d['rival']=='all'
                 and d['comparison']=='mean_seed(B-A)')
    assert primary['delta']==1 and primary['case_cluster_95']==[1,1]
    assert any(r['new_win']==6 for r in result['parent_win_retention_and_acquisition'])
    with pytest.raises(ValueError):analyze(rows[:-1],small,resamples=128)
    with pytest.raises(ValueError):analyze(rows+rows[:1],small,resamples=128)


def test_gym_schedule_is_episode_frozen_audit_only_and_keeps_policy_info(monkeypatch):
    import advisor.learned_gym as gym
    import advisor.learned_tactical_curriculum as curriculum
    class Native:
        def __init__(self,*a,**k):self.number=0
        def observation(self,side,**k):return {'episode_id':str(self.number),'revision':0,'request_state':'move',
            'action_mask':[int(i==6) for i in range(35)],'public_history':[]}
        def close(self):pass
    def reset(native,current):native.number+=1;return {}
    monkeypatch.setattr(gym,'ShowdownEnvironment',Native)
    monkeypatch.setattr(curriculum,'reset_learning_episode',reset)
    monkeypatch.setattr(gym,'scenario',lambda *a,**k:{'scenario_id':'fixture','teams':{'self':[{}]*6,'opponent':[{}]*6},
        'preview':{'self':[1,2,3],'opponent':[1,2,3]},'seed':[1,2,3,4]})
    encoder=SimpleNamespace(encode=lambda view:np.zeros(2,np.float32),dimension=2)
    env=gym.ShowdownLearningEnv('unused',encoder,opponents=BASELINE,opponent_schedule=two_group_schedule(),
        collect_opponent_selections=True,opponent_factory=lambda kind,seed:SimpleNamespace(kind=kind),
        terminal_transport_version=gym.OPAQUE_TERMINAL)
    old=env.opponent;env.set_opponent_schedule_cursor(32768)
    assert env.opponent is old and env._episode_identity['opponent_selection']['stage']==0
    features,info=env.reset(seed=1)
    assert env._episode_identity['opponent_selection']['stage']==1
    assert set(info)=={'schema_version','episode_id','revision','request_state'}
    env._native_step=lambda action:{'terminated':True,'truncated':False,'winner':'self','decisions':1,
        'rewards':{'self':1,'opponent':-1},'revision':1,'action_rejected':False}
    env.step(6)
    assert env.drain_completed()[0]['episode_identity']['opponent_selection']['learner_steps']==1
    receipts=env.drain_opponent_selections();assert len(receipts)==2 and receipts[0]['learner_steps']==0
    assert receipts[1]['learner_steps']==1 and not env.drain_opponent_selections()
    with pytest.raises(ValueError):env.set_opponent_schedule_cursor(0)
    env.close()
