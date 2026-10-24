"""Pure contracts: no native starts and no PPO transitions."""
from copy import deepcopy
import json
import os
from pathlib import Path
import pytest

from advisor.learned_public_best_response import response_value, choose_response, validate_view


def test_switch_pays_entry_damage_but_preserves_departing_actor():
    attack={'kind':'attack','hp':.2,'damage':.2,'incoming':.5,'first':0.,'potential':0.}
    switch={**attack,'kind':'switch','hp':1.,'damage':0.,'incoming':.1}
    assert response_value(switch,.8) > response_value(attack,.8)


def test_heal_never_exceeds_missing_health_and_can_fail_before_execution():
    p={'kind':'recovery','hp':1.,'heal':.5,'damage':0.,'incoming':.2,'first':1.,'potential':0.}
    assert response_value(p,1.) < 0
    assert response_value({**p,'hp':.1,'first':0.},1.) < response_value({**p,'hp':.1},1.)


def test_priority_and_ko_risk_affect_pair_value():
    p={'kind':'attack','hp':.2,'damage':.6,'incoming':.4,'first':1.,'potential':0.}
    assert response_value(p,.5) > response_value({**p,'first':0.},.5)


def test_recoil_is_paid_even_when_opponent_is_ko_and_healing_is_not_free():
    p={'kind':'attack','hp':.2,'damage':.6,'incoming':.4,'first':1.,'potential':0.}
    assert response_value({**p,'self_cost':.3},.5) < response_value(p,.5)
    q={**p,'damage':0.,'incoming':0.}
    assert response_value({**q,'foe_heal':.3},.5) < response_value(q,.5)


def test_weighted_mean_and_conservative_tail_are_not_a_win_probability():
    rows=[{'action':6,'utilities':[.4,.2],'weights':[1,1]},
          {'action':7,'utilities':[.9,-.9],'weights':[1,1]}]
    before=deepcopy(rows);action,proof=choose_response(rows,7)
    assert action==6 and rows==before
    assert all('scenario_mean' in p and 'conservative_score' in p for p in proof)


def test_ties_preserve_legal_baseline_without_random_disagreement():
    rows=[{'action':a,'utilities':[0.],'weights':[1]}for a in (6,7)]
    assert choose_response(rows,7)[0]==7
    with pytest.raises(ValueError):choose_response([],7)
    with pytest.raises(ValueError):choose_response([{'action':6,'utilities':[float('nan')],'weights':[1]}],6)


@pytest.mark.parametrize('key',['teams','scenario','checkpoint','opponent_request','future_seed','native_state','auxiliary_labels'])
def test_privileged_input_is_rejected(key):
    with pytest.raises(ValueError,match='privileged'):validate_view({key:1})


def test_mask_and_own_request_role_fail_closed():
    v={'action_mask':[0]*35,'side':'self','own_request':{'side':{'id':'p2'}}}
    with pytest.raises(ValueError):validate_view(v)
    v['action_mask'][6]=1
    with pytest.raises(ValueError,match='role'):validate_view(v)


def test_explicit_new_opponent_is_opt_in_and_legacy_baselines_unchanged():
    from scripts.train_showdown_autonomous import validate_config
    from advisor.learned_baselines import VisibleBaseline
    from advisor.learned_public_best_response import VERSION
    c={'schema_version':'showdown-autonomous-training-v1','max_runtime_seconds':60,
       'experiments':[{'seed':1,'steps':1024,'opponents':[VERSION]}]}
    assert validate_config(c)==c
    with pytest.raises(ValueError,match='invalid_baseline'):VisibleBaseline(VERSION)


def test_matched_analysis_preserves_players_seats_and_case_clusters():
    from scripts.evaluate_public_best_response import slots,analyze,RIVALS
    cases=[{'scope':s,'index':i,'scenario_sha256':str(i)}for i,s in enumerate(('train','heldout'))]
    players={'Foundation':{},'V4':{}}
    rows=[{'slot':s,'record':{'winner':'opponent'if s['rival']==RIVALS[0]else'self','truncated':False,'native_choice_rejections':0}}for s in slots(cases,players)]
    result=analyze(rows,cases,players)
    assert result['games']==16
    assert all(r['delta']==1 and r['case_cluster_95']==[1,1]for r in result['paired']if 'delta'in r)
    with pytest.raises(ValueError):analyze(rows[:-1],cases,players)


@pytest.fixture
def native_owner(monkeypatch):
    checkout=os.environ.get('POKEADVICE_BR_CHECKOUT');output=os.environ.get('POKEADVICE_BR_ARTIFACTS')
    if not checkout or not output:pytest.skip('explicit pinned engine and separate counted native budget required')
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_encoder import fingerprint
    ledger=Path(output)/'native_starts.jsonl';original=ShowdownEnvironment.reset
    def reset(env,scenario,*args,**kwargs):
        lines=ledger.read_text(encoding='utf-8').splitlines()if ledger.exists()else[]
        assert len(lines)<128,'bounded development cap'
        with ledger.open('a',encoding='utf-8')as f:
            f.write(json.dumps({'ordinal':len(lines),'phase':'contracts','scenario_sha256':fingerprint(scenario)})+'\n');f.flush();os.fsync(f.fileno())
        return original(env,scenario,*args,**kwargs)
    monkeypatch.setattr(ShowdownEnvironment,'reset',reset)
    return checkout,Path(output)


@pytest.mark.parametrize('side',['self','opponent'])
def test_native_public_equivalent_hidden_sets_leave_probabilities_identical(native_owner,side):
    from advisor.learned_public_best_response import PublicBestResponseOpponent
    from advisor.learned_action_signals import require_public_equivalence
    from advisor.showdown_environment import ShowdownEnvironment
    from scripts.verify_showdown_integration import fixture_scenarios
    checkout,out=native_owner;s=fixture_scenarios()[0];unknown='opponent'if side=='self'else'self'
    views=[];proofs=[]
    with ShowdownEnvironment(checkout)as env:
        for variant in range(2):
            c=deepcopy(s);p=c['teams'][unknown][0]
            p['item']='Choice Scarf'if variant else'Scope Lens'
            p['ability']=('Swarm'if variant else'Technician')if unknown=='opponent'else('Solar Power'if variant else'Blaze')
            if variant:p['moves']=['Protect','Swords Dance']if unknown=='opponent'else['Protect','Swords Dance']
            env.reset(c);v=env.observation(side,include_history=True);original=deepcopy(v)
            policy=PublicBestResponseOpponent(3,checkout=checkout);a=policy.act(v)
            assert v==original and v['action_mask'][a]
            assert not policy.last_decision['fallback']
            views.append(v);proofs.append(deepcopy(policy.last_decision))
        require_public_equivalence(*views)
        assert proofs[0]['action_probabilities']==proofs[1]['action_probabilities']
        assert proofs[0]['comparisons']==proofs[1]['comparisons']
    (out/f'privacy_{side}.json').write_text(json.dumps({'views':views,'proofs':proofs}),encoding='utf-8')


@pytest.mark.parametrize('side',['self','opponent'])
def test_native_general_attack_and_revealed_immunity_use_correct_actor(native_owner,side):
    from advisor.learned_public_best_response import PublicBestResponseOpponent
    from advisor.showdown_environment import ShowdownEnvironment
    from scripts.verify_showdown_integration import fixture_scenarios
    checkout,out=native_owner;s=fixture_scenarios()[0]
    if side=='opponent':s['teams']['self'],s['teams']['opponent']=s['teams']['opponent'],s['teams']['self']
    other='opponent'if side=='self'else'self'
    with ShowdownEnvironment(checkout)as env:
        env.reset(s);v=env.observation(side,include_history=True);policy=PublicBestResponseOpponent(3,checkout=checkout)
        a=policy.act(v);proof=deepcopy(policy.last_decision)
        assert proof['comparisons'] and not proof['fallback'] and v['action_mask'][a]
        result=env.step({side:a,other:6},revision=v['revision'])
        assert not result['action_rejected']
        (out/f'general_{side}.json').write_text(json.dumps({'before':v,'proof':proof,'result':result,'after':env.observation(side,include_history=True)}),encoding='utf-8')
    s=fixture_scenarios()[0]
    s['teams']['self'][0],s['teams']['self'][1]=s['teams']['self'][1],s['teams']['self'][0]
    s['teams']['self'][0]['moves']=['Earthquake','Protect','Dragon Claw']
    s['teams']['opponent'][0],s['teams']['opponent'][2]=s['teams']['opponent'][2],s['teams']['opponent'][0]
    if side=='opponent':s['teams']['self'],s['teams']['opponent']=s['teams']['opponent'],s['teams']['self']
    with ShowdownEnvironment(checkout)as env:
        env.reset(s);v=env.observation(side,include_history=True)
        result=env.step({side:6,other:6},revision=v['revision']);assert not result['action_rejected']
        v=env.observation(side,include_history=True);policy=PublicBestResponseOpponent(3,checkout=checkout);a=policy.act(v)
        proof=deepcopy(policy.last_decision);rows={r['action']:r for r in proof['comparisons']}
        assert 6 in rows and a!=6
        assert all(p['conditional_pair']['damage']==0 for p in rows[6]['pairs']if p['response']['kind']!='switch')
        (out/f'immunity_{side}.json').write_text(json.dumps({'before':v,'proof':proof}),encoding='utf-8')


def test_native_factory_explicit_opt_in_without_ppo(native_owner):
    from advisor.learned_parallel import LearningEnvFactory
    from advisor.learned_public_best_response import PublicBestResponseOpponent,VERSION
    checkout,_=native_owner
    catalog=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
    env=LearningEnvFactory(checkout,str(catalog),'showdown-learned-observation-v1',0,
        'showdown-learning-curriculum-v8',(VERSION,),{})()
    try:
        assert isinstance(env.opponent,PublicBestResponseOpponent)
        v=env.native.observation('opponent',include_history=True)
        a=env.opponent.act(v);assert v['side']=='opponent'and v['action_mask'][a]
    finally:env.close()
