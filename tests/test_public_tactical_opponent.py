"""Focused pure contracts; these tests do not start native games or PPO."""
from copy import deepcopy
from types import SimpleNamespace
import json
import os
from pathlib import Path

import pytest

from advisor.learned_public_tactical_opponent import (
    VERSION, exchange_utility, rank_exchanges, PublicTacticalOpponent,
    response_hypotheses,
)


def profile(action=6, kind="attack", hp=.8, outgoing=(.3,.3), incoming=(.2,.2), heal=0):
    return {"action":action,"kind":kind,"hp":hp,"outgoing":outgoing,
            "incoming":incoming,"heal":heal,"orders":("own_first","foe_first")}


def test_switch_consumes_one_turn_and_does_not_attack_on_entry():
    a=profile();s=profile(1,"switch")
    assert exchange_utility(a,.9,.3,.2,"own_first") > exchange_utility(s,.9,.3,.2,"own_first")


def test_priority_order_can_change_immediate_depletion():
    p=profile(hp=.2,outgoing=(.5,.5),incoming=(.4,.4))
    assert exchange_utility(p,.4,.5,.4,"own_first")==1
    assert exchange_utility(p,.4,.5,.4,"foe_first")==-1


def test_heal_at_full_hp_pays_opportunity_cost():
    heal=profile(7,"recovery",hp=1,heal=.5)
    assert exchange_utility(heal,.9,.3,.2,"own_first") < exchange_utility(profile(hp=1),.9,.3,.2,"own_first")


def test_survival_can_prefer_switch_without_claiming_it_is_optimal():
    attack=profile(hp=.2,outgoing=(.2,.2),incoming=(.5,.5))
    switch=profile(1,"switch",hp=1,outgoing=(.6,.6),incoming=(.1,.1))
    picked,rows=rank_exchanges({6:[attack],1:[switch]},.9,6)
    assert picked==1 and len(rows)==2
    assert all(r["scenario_count"]==8 for r in rows)


def test_ties_preserve_baseline_and_input_is_immutable():
    choices={6:[profile()],7:[profile(7)]};before=deepcopy(choices)
    assert rank_exchanges(choices,.8,7)[0]==7 and before==choices


def test_no_empty_or_nonfinite_estimate_silently_becomes_score():
    with pytest.raises(ValueError):rank_exchanges({},.8,6)
    with pytest.raises(ValueError):rank_exchanges({6:[profile(incoming=(float('nan'),.2))]},.8,6)


def view(allowed=(6,7)):
    mask=[False]*35
    for a in allowed:mask[a]=True
    return {"episode_id":"public","revision":1,"action_mask":mask,
            "choices":[f"move {i}" if mask[i] else None for i in range(35)],
            "public_history":[],"side":"self","own_request":{},"state":{}}


def test_wait_never_needs_private_or_catalog_information():
    p=PublicTacticalOpponent.__new__(PublicTacticalOpponent)
    assert p.act(view((26,)))==26


@pytest.mark.parametrize("key",["teams","native_state","opponent_request","checkpoint","seed","future_seed","auxiliary_labels"])
def test_privileged_top_level_input_fails_closed(key):
    p=PublicTacticalOpponent.__new__(PublicTacticalOpponent);v=view();v[key]={"private":1}
    with pytest.raises(ValueError,match="privileged"):p.act(v)


def test_mask_is_authoritative_even_when_estimator_prefers_other_action(monkeypatch):
    p=PublicTacticalOpponent.__new__(PublicTacticalOpponent)
    p.base=SimpleNamespace(act=lambda _:6);p._last_key=None
    monkeypatch.setattr(p,"_profiles",lambda v,b:({7:[profile(7)]},.8,{"basis":"test"}))
    from collections import Counter
    p.counts=Counter();p.last_decision=None
    assert p.act(view((6,)))==6
    assert p.last_decision["fallback"]=="no_comparable_baseline_profile"


def test_trainer_opt_in_identifier_leaves_legacy_baseline_names_unchanged():
    from advisor.learned_baselines import VisibleBaseline
    from scripts.train_showdown_autonomous import validate_config
    c={"schema_version":"showdown-autonomous-training-v1","max_runtime_seconds":60,
       "experiments":[{"seed":1,"steps":1024,"opponents":[VERSION]}]}
    assert validate_config(c)==c
    with pytest.raises(ValueError,match="invalid_baseline"):VisibleBaseline(VERSION)


def test_evaluator_keeps_legacy_heuristic_identifier_and_seeding():
    from scripts.evaluate_public_tactical_opponent import rival_policy
    candidate=SimpleNamespace(model_id=VERSION)
    assert rival_policy(VERSION,candidate)is candidate
    assert rival_policy('tactical_heuristic',candidate)=='tactical_heuristic'
    with pytest.raises(ValueError):rival_policy('not_approved',candidate)


def test_unrevealed_response_is_legal_hypothesis_not_revelation():
    moves={m:{'referenceSupported':True,'power':n}for m,n in [('tackle',40),('ember',40),('secret',999)]}
    metadata={m:{'simpleExchange':True}for m in moves};revealed=['tackle'];before=deepcopy(revealed)
    h=response_hypotheses(revealed,['tackle','ember'],moves,metadata,{'secret':100,'ember':3},{})
    assert [r['move']for r in h]==['tackle','ember'] and revealed==before
    assert h[0]['basis']=='public_revealed' and 'hypothesis'in h[1]['basis']
    assert all(r['currently_selectable']=='unknown'for r in h)


def test_case_cluster_analysis_keeps_rivals_and_actual_seats():
    from scripts.evaluate_public_tactical_opponent import slots,analyze,RIVALS
    cases=[{'scope':'train','index':1,'scenario_sha256':'a'}, {'scope':'heldout','index':2,'scenario_sha256':'b'}]
    rows=[{'slot':s,'record':{'winner':'opponent'if s['rival']==RIVALS[0]else'self','truncated':False,'native_choice_rejections':0}}for s in slots(cases)]
    a=analyze(rows,cases);d=next(r for r in a['paired']if r['scope']=='all'and'comparison'in r)
    assert a['games']==8 and d['delta']==-1 and d['case_cluster_95']==[-1,-1]
    with pytest.raises(ValueError):analyze(rows[:-1],cases)


@pytest.fixture
def native_owner(monkeypatch):
    checkout=os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    out=os.environ.get("POKEADVICE_TACTICAL_ARTIFACTS")
    if not checkout or not out:pytest.skip("explicit pinned engine and shared native-start budget required")
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_encoder import fingerprint
    ledger=Path(out)/"native_starts.jsonl"
    original=ShowdownEnvironment.reset
    def counted_reset(env,scenario,*args,**kwargs):
        rows=ledger.read_text(encoding='utf-8').splitlines() if ledger.exists() else []
        assert len(rows)<128,"development_start_limit"
        with ledger.open('a',encoding='utf-8')as f:
            f.write(json.dumps({'ordinal':len(rows),'phase':'contracts','scenario_sha256':fingerprint(scenario)})+'\n')
            f.flush();os.fsync(f.fileno())
        return original(env,scenario,*args,**kwargs)
    monkeypatch.setattr(ShowdownEnvironment,'reset',counted_reset)
    return checkout,Path(out)


@pytest.mark.parametrize('side',['self','opponent'])
def test_native_hidden_variant_keeps_same_public_action(native_owner,side):
    from scripts.verify_showdown_integration import fixture_scenarios
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_action_signals import require_public_equivalence
    checkout,out=native_owner;scenario=fixture_scenarios()[0]
    unseen='opponent' if side=='self' else 'self';views=[];decisions=[]
    with ShowdownEnvironment(checkout)as env:
        for variant in range(2):
            s=deepcopy(scenario)
            s['teams'][unseen][0]['item']='Choice Scarf' if variant else 'Scope Lens'
            s['teams'][unseen][0]['moves']=['Protect','Swords Dance'] if unseen=='opponent' and variant else s['teams'][unseen][0]['moves']
            env.reset(s);v=env.observation(side,include_history=True)
            p=PublicTacticalOpponent(3,checkout=checkout);before=deepcopy(v)
            decisions.append(p.act(v));assert v==before and v['action_mask'][decisions[-1]]
            views.append(v)
    require_public_equivalence(*views);assert decisions[0]==decisions[1]
    (out/f'privacy_{side}.json').write_text(json.dumps({'views':views,'actions':decisions}),encoding='utf-8')


def test_native_revealed_immunity_changes_attack_with_evidence(native_owner):
    from scripts.verify_showdown_integration import fixture_scenarios
    from advisor.showdown_environment import ShowdownEnvironment
    checkout,out=native_owner;s=fixture_scenarios()[0]
    s['teams']['self'][0],s['teams']['self'][1]=s['teams']['self'][1],s['teams']['self'][0]
    s['teams']['self'][0]['moves']=['Earthquake','Protect','Dragon Claw']
    # Sand Veil is natively legal and the reused reference supports its
    # damage-neutral effect here. Rough Skin is deliberately unsupported.
    s['teams']['self'][0]['ability']='Sand Veil'
    s['teams']['opponent'][0],s['teams']['opponent'][2]=s['teams']['opponent'][2],s['teams']['opponent'][0]
    with ShowdownEnvironment(checkout)as env:
        env.reset(s);v=env.observation('self',include_history=True)
        r=env.step({'self':6,'opponent':6},revision=v['revision']);assert not r['action_rejected']
        v=env.observation('self',include_history=True);p=PublicTacticalOpponent(3,checkout=checkout)
        action=p.act(v);proof=deepcopy(p.last_decision)
        (out/'public_immunity_pre_execution.json').write_text(json.dumps({'before':v,'decision':proof}),encoding='utf-8')
        assert any('Levitate' in e for e in v['public_history'])
        assert action!=6 and proof['baseline_action']==6 and proof['disagrees']
        rows={r['action']:r for r in proof['comparisons']}
        assert max(rows[6]['conditional_hypotheses'][0]['outgoing'])==0
        from advisor.learned_combat_v5_references import reference_features
        import numpy as np
        original=deepcopy(v)
        default=reference_features(v,p.reference,p.native_moves)
        known=v['state']['opponent_side']['pokemon'][v['state']['opponent_side']['active_identity']]['known_moves']
        explicit=reference_features(v,p.reference,p.native_moves,incoming_move_hypotheses=known)
        for a,b in zip(default,explicit):np.testing.assert_array_equal(a,b)
        assert v==original  # Hypotheses never rewrite the real public known list.
        result=env.step({'self':action,'opponent':6},revision=v['revision'])
        after=env.observation('self',include_history=True)
        assert not result['action_rejected']
        if action>=6:
            foe=after['state']['opponent_side'];assert foe['pokemon'][foe['active_identity']]['hp_fraction']<1
        else:
            assert after['state']['self_side']['active_identity']!=v['state']['self_side']['active_identity']
        (out/'public_immunity_example.json').write_text(json.dumps({'before':v,'decision':proof,'after':after,'result':result}),encoding='utf-8')


def test_pinned_metadata_excludes_unmodeled_party_and_stat_changes(native_owner):
    checkout,_=native_owner;p=PublicTacticalOpponent(1,checkout=checkout)
    for move in ('uturn','voltswitch','dragontail','explosion','flareblitz','closecombat'):
        assert not p.exchange_metadata[move]['simpleExchange']
    assert p.exchange_metadata['earthquake']['simpleExchange']


def test_native_training_factory_opt_in_without_learning(native_owner):
    from advisor.learned_parallel import LearningEnvFactory
    checkout,_=native_owner
    catalog=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
    factory=LearningEnvFactory(checkout,str(catalog),'showdown-learned-observation-v1',0,
        'showdown-learning-curriculum-v8',(VERSION,),{})
    env=factory()
    try:
        assert isinstance(env.opponent,PublicTacticalOpponent)
        own=env.native.observation('opponent',include_history=True)
        assert own['side']=='opponent'
        before=deepcopy(own);action=env.opponent.act(own)
        assert own==before and own['action_mask'][action]
        assert not {'opponent_selection','coordinator_v5_supervision','teams','checkpoint','future_seed'}&set(own)
    finally:env.close()
