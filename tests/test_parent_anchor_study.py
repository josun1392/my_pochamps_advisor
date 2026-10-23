from copy import deepcopy
import pytest
from advisor.learned_anchor_study import matched_configs, game_slots, analyze, POLICIES
from advisor.learned_parent_anchor import anchor_contract


def configs():
    base = {"envs":4,"cpu_percent":50,"memory_mib":12288,"device":"cpu",
        "transition_budget_scope":"trained_rollouts_v1", "training_subset":"same",
        "experiments":[{"steps":65536,"initial_model_id":"a"*64,"fresh_optimizer":False,
                        "gamma":1,"opponents":["same"]}]}
    result={}
    for key in POLICIES[1:]:
        c=deepcopy(base);c['experiments'][0].update(name=key,seed=int(key[2:]))
        if key.startswith('T'):c['experiments'][0]['parent_policy_anchor']=anchor_contract('a'*64,'b'*64,32768)
        result[key]=c
    return result


def test_only_anchor_differs_and_budgets_are_matched():
    assert matched_configs(configs(),'a'*64)['trained_transitions']==262144
    for field,value in [('gamma',.99),('opponents',['different']),('steps',32768),('fresh_optimizer',True)]:
        c=configs();c['T_96031']['experiments'][0][field]=value
        with pytest.raises(ValueError):matched_configs(c,'a'*64)
    c=configs();c['T_96031']['experiments'][0]['parent_policy_anchor']['coefficient']=.02
    with pytest.raises(ValueError):matched_configs(c,'a'*64)


def cases():
    return [{'scope':'train' if i<32 else 'heldout','index':i,'scenario_sha256':str(i),
             'sampled':32<=i<64} for i in range(128)]


def test_exact_case_seat_rival_stream_budget_and_pairing():
    slots=game_slots(cases())
    assert len(slots)==4480
    assert sum(s['mode']=='argmax' for s in slots)==3840
    assert all(s['rival']=='champions_heuristic' and s['scope']=='heldout' for s in slots if s['mode']!='argmax')
    assert len({tuple(s.values()) for s in slots})==4480


def test_case_cluster_analysis_retention_and_missing_fail_closed():
    small=[cases()[0],cases()[32]]
    rows=[{'slot':s,'record':{'winner':'self' if s['policy'].startswith('T') else 'opponent',
                            'truncated':False}} for s in game_slots(small)]
    result=analyze(rows,small,resamples=64)
    primary=next(r for r in result['paired_differences'] if r['mode']=='argmax' and r['scope']=='heldout'
                 and r['rival']=='all' and r['comparison']=='mean_seed(T-C)')
    assert primary['delta']==1 and primary['case_cluster_95']==[1,1]
    gain=next(r for r in result['parent_win_retention_and_acquisition'] if r['mode']=='argmax'
              and r['scope']=='heldout' and r['rival']=='all' and r['policy']=='T_96031')
    assert gain['new_win']==6 and gain['parent_win_lost']==0
    with pytest.raises(ValueError):analyze(rows[:-1],small,resamples=64)
    with pytest.raises(ValueError):analyze(rows+rows[:1],small,resamples=64)
