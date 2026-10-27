"""New synthetic native fixtures, metered separately from actual TRAIN coverage.

No learned policy, original hidden state, PPO or optimizer is used here.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

from advisor.learning_resources import atomic_json
from advisor.learned_action_search_teacher import validate_public_teacher_target
from advisor.learned_public_native_teacher import PublicNativeTeacher, support_conditions
from advisor.showdown_environment import ShowdownEnvironment
from scripts.pilot_foundation_integrated_micro import MicroLedger


def scenario(side):
    def p(species,ability,moves,item='',evs=None,nature='Hardy'):
        return {'species':species,'ability':ability,'moves':moves,'item':item,'level':50,
            'evs':evs or {'hp':2,'atk':32,'spe':32},'nature':nature}
    ghosts=[p('Gourgeist','Pickup',['Explosion','Protect']),p('Metagross','Clear Body',['Explosion','Protect'])]
    own=ghosts+[p('Heracross','Guts',['Seismic Toss','Protect','Swords Dance','Megahorn'],item='Leftovers',
        evs={'hp':32,'spd':32,'atk':2},nature='Sassy')]
    other=deepcopy(ghosts)+[p('Charizard','Blaze',['Hyper Beam','Protect','Flamethrower','Air Slash'],
        item='Sitrus Berry',evs={'hp':32,'def':32,'spd':2},nature='Adamant')]
    fillers=[p('Garchomp','Rough Skin',['Protect']),p('Dragonite','Inner Focus',['Protect']),p('Gengar','Cursed Body',['Protect'])]
    teams={'self':own+deepcopy(fillers),'opponent':other+deepcopy(fillers)}
    if side=='opponent':teams={'self':teams['opponent'],'opponent':teams['self']}
    return {'scenario_id':'synthetic-public-terminal-proof-'+side,'teams':teams,
        'preview':{'self':[1,2,3],'opponent':[1,2,3]},'seed':[31,37,41,43]}


def move(view,mid):
    slots=view['own_request'].get('active',[{}])[0].get('moves',[])
    for i,m in enumerate(slots):
        if m['id']==mid and view['action_mask'][6+i]:return 6+i
    raise AssertionError('fixture intended native move unavailable: '+mid)


def prefix(env,side,ledger):
    other='opponent'if side=='self'else'self'
    ledger.reserve('TRAIN_start',1);env.reset(scenario(side))
    for _ in range(8):
        views={s:env.observation(s,include_history=True)for s in ('self','opponent')}
        if ('Heracross' in views[side]['own_request']['side']['pokemon'][0]['details'] and
               'Charizard' in views[other]['own_request']['side']['pokemon'][0]['details']):break
        actions={}
        for s,v in views.items():
            if v['action_mask'][26]:actions[s]=26
            elif v['request_state']=='switch':actions[s]=next(i for i in range(6)if v['action_mask'][i])
            else:actions[s]=move(v,'explosion')
        ledger.reserve('transition',1);r=env.step(actions,revision=views[side]['revision'])
        assert not r['action_rejected'] and not r['terminated']
    else:raise AssertionError('failed to reach synthetic final pair')
    pairs=[('seismictoss','hyperbeam'),('protect','recharge'),
        ('seismictoss','hyperbeam'),('protect','recharge'),('seismictoss','hyperbeam'),
        ('protect','recharge'),('seismictoss','hyperbeam')]
    for own_mid,foe_mid in pairs:
        v=env.observation(side,include_history=True);f=env.observation(other,include_history=True)
        ledger.reserve('transition',1)
        r=env.step({side:move(v,own_mid),other:move(f,foe_mid)},revision=v['revision'])
        assert not r['action_rejected'] and not r['terminated'] and not r['truncated']
    return env.observation(side,include_history=True)


@pytest.mark.parametrize('side',['self','opponent'])
def test_native_public_hypotheses_terminal_proof_both_seats(side):
    config_path=os.environ.get('POKEADVICE_PUBLIC_NATIVE_TEACHER_PLAN')
    if not config_path:pytest.skip('explicit metered native fixture contract required')
    cfg=json.loads(Path(config_path).read_text())
    output=Path(cfg['native_fixture_directory'])/(side+'.json')
    completed = output.exists()
    ledger=MicroLedger(cfg['ledger'])
    cached=Path(cfg['native_fixture_directory'])/(side+'_public.json')
    if cached.exists():
        view=json.loads(cached.read_text())['view']
    else:
        with ShowdownEnvironment(cfg['checkout'],max_decisions=64)as env:
            view=prefix(env,side,ledger)
        cached.parent.mkdir(parents=True,exist_ok=True)
        atomic_json(cached,{'scope':'synthetic_native_prefix_fixture','view':view})
    teacher=PublicNativeTeacher(checkout=cfg['checkout'],catalog=cfg['catalog'],ledger_path=cfg['ledger'],
        allow_native_execution=not completed)
    reason,conditions=support_conditions(view,teacher.catalog)
    assert reason is None,reason
    result=teacher.assess(view,policy_id='synthetic-native-fixture',learning_step=0)
    assert result['status']=='abstain' and result['reason']=='causal_public_history_witness_unavailable'
    target=validate_public_teacher_target(result,view,policy_id='synthetic-native-fixture',learning_step=0)
    assert target is None
    assert result['native_evidence']['complete_HP_domain']
    assert len(result['native_evidence']['hypotheses'])>=32
    contradicted=deepcopy(view);contradicted['own_request']['active'][0]['moves'][0]['pp']-=1
    with pytest.raises(ValueError):validate_public_teacher_target(result,contradicted,
        policy_id='synthetic-native-fixture',learning_step=0)
    unknown=deepcopy(view)
    row=unknown['state']['opponent_side']['pokemon'][unknown['state']['opponent_side']['active_identity']]
    row['known_item']='focussash'
    unknown['public_history'].append('|-item|'+row['identity']+'|Focus Sash')
    assert teacher.assess(unknown,policy_id='synthetic-native-fixture',learning_step=0)['status']=='abstain'
    output.parent.mkdir(parents=True,exist_ok=True)
    receipt = output.with_name(side+'_admission_checked.json') if completed else output
    atomic_json(receipt,{'scope':'synthetic_native_fixture_NOT_preserved_TRAIN_coverage',
        'side':side,'view':view,'provider_result':result,
        'native_counts':dict(MicroLedger(cfg['ledger']).counts)})


def test_completed_native_receipts_current_source_and_existing_consumer_no_Adam(tmp_path):
    config_path=os.environ.get('POKEADVICE_PUBLIC_NATIVE_TEACHER_PLAN')
    if not config_path:pytest.skip('explicit retained native proof receipts required')
    import torch
    from advisor.learned_action_signals import require_public_equivalence
    from advisor.showdown_observation import project_policy_observation
    from advisor.learned_offline import public_teacher_loss
    from advisor.learned_policy import LearnedPolicy
    from scripts.train_showdown_autonomous import optimizer_steps
    cfg=json.loads(Path(config_path).read_text())
    ledger_before=Path(cfg['ledger']).read_bytes()
    teacher=PublicNativeTeacher(checkout=cfg['checkout'],catalog=cfg['catalog'],ledger_path=cfg['ledger'])
    current_proofs={}; history_counterexamples={}
    for side in ('self','opponent'):
        saved=json.loads((Path(cfg['native_fixture_directory'])/(side+'.json')).read_text())
        v=saved['view'];result=saved['provider_result'];worlds=result['native_evidence']['hypotheses']
        assert len({(r['max_hp'],r['current_hp'],r['ability'])for r in worlds})==len(worlds)
        assert {r['ability']for r in worlds}=={'blaze','solarpower'}
        foe_id=v['state']['opponent_side']['active_identity']
        first_hp=next(line.split('|')[3]for line in v['public_history']
            if line.startswith('|-damage|'+foe_id+'|'))
        # Pinned Champions display floors HP percent; Seismic Toss at level50
        # deals fixed50. This is an audit counterexample, not a new calculator.
        h=min(r['max_hp']for r in worlds)
        expected=(h-50)*100//h;observed=int(first_hp.split('/')[0])
        assert expected!=observed
        history_counterexamples[side]={'hypothesis_max_HP':h,'first_fixed_damage':50,
            'expected_native_percent_after_first_hit':expected,'observed_public_percent':observed}
        for row in (worlds[0],worlds[-1]):
            candidate=project_policy_observation({**v,**row['before']},row['before']['public_history'])
            require_public_equivalence(v,candidate)
            # Native worlds differ in actual HP/ability; their player views and
            # provider outputs remain identical. Cache reuse prevents replays.
            current=teacher.assess(candidate,policy_id='synthetic-native-fixture',learning_step=0)
            assert current['status']=='abstain' and current['target']is None
            assert current['reason']=='causal_public_history_witness_unavailable'
            assert current['binding']==result['binding']
            current_proofs[side]=current
        broken=deepcopy(worlds[0]['before']);broken['own_request']['side']['pokemon'][0]['stats']['atk']+=1
        with pytest.raises(ValueError,match='contradicts'):
            require_public_equivalence(v,project_policy_observation({**v,**broken},broken['public_history']))
        unavailable=deepcopy(v)
        last=max(i for i,line in enumerate(unavailable['public_history'])if line.startswith('|-mustrecharge|'))
        del unavailable['public_history'][last]
        assert teacher.assess(unavailable,policy_id='synthetic-native-fixture',learning_step=0)['status']=='abstain'
    model_path=Path(cfg['model'])
    initial_SHA=sha256(model_path.read_bytes()).hexdigest()
    assert initial_SHA==cfg['policy_id']
    parent=LearnedPolicy(model_path,cfg['catalog'],expected_model_id=initial_SHA)
    clock=optimizer_steps(parent.model)
    bound=teacher.assess(v,policy_id=initial_SHA,learning_step=parent.model.num_timesteps)
    loss=public_teacher_loss(parent.model,parent.encoder,v,bound,
        policy_id=initial_SHA,learning_step=parent.model.num_timesteps)
    assert loss is None and optimizer_steps(parent.model)==clock
    assert sha256(model_path.read_bytes()).hexdigest()==initial_SHA
    final_ledger=Path(cfg['ledger']).read_bytes()
    assert final_ledger==ledger_before  # Cached-only final audit: no extra native.
    atomic_json(Path(cfg['native_fixture_directory'])/'final_admission_results.json',current_proofs)
    atomic_json(Path(cfg['native_fixture_directory'])/'consumer_abstention_final.json',{
        'scope':'model_only_native_proof_rejected_by_teacher_consumer',
        'teacher_loss':None,'Adam_before':clock,'Adam_after':clock,
        'causal_history_counterexamples':history_counterexamples,
        'new_Adam':0,'native_ledger_bytes_before':len(ledger_before),
        'native_ledger_bytes_after':len(final_ledger),'model_SHA256':initial_SHA})
