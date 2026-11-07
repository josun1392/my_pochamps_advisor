"""Mock-only mixture/receipt tests: no native, rollout, learning or optimizer."""
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
import json
import numpy as np
import pytest
from advisor import experimental_minority_opponent as impl
from advisor.learned_train_opponents import TrainFoundationOpponent, KEY
from advisor.learned_opponent_quality import QualityActor,global_rng_digest
from advisor.learned_execution_alignment import content_hash
from scripts.audit_minority_opponent_mix import analyze_results

MODEL='a'*64


class Parent:
    model_id=MODEL
    metadata={'combat_foundation':True}


def identity(index,seed=116051):
    episode={'split':'train','case_index':index,'scenario_id':'synthetic',
        'scenario_sha256':'b'*64,'team_sha256':{'self':'c'*64,'opponent':'d'*64},'native_seed':[1,2,3,4]}
    actor=TrainFoundationOpponent(Parent(),impl.manifest(seed,MODEL),episode,worker=0,segment=0,legacy_seed=index+91)
    return {'episode_id':f'synthetic{index}','worker':0,'episode_identity':episode,
        'opponent_mode':actor.mode,'TRAIN_foundation_opponent':actor.identity()}


def test_exact_episode3to1_assignment_has_no_global_draws_or_mutation():
    before=global_rng_digest();old={'schema_version':'mock','opponents':['league_s0'],'other':[1]}
    adapter=impl.training_adapter(old,116051,MODEL)
    assert old=={'schema_version':'mock','opponents':['league_s0'],'other':[1]}
    assert {k:v for k,v in adapter.items() if k!=KEY}==old
    for block in range(8):
        assert [impl.verify_training_identity(identity(i),116051,MODEL) for i in range(4*block,4*block+4)]==impl.SLOTS
    assert before==global_rng_digest()
    with pytest.raises(ValueError):impl.training_adapter(adapter,116051,MODEL)


@pytest.mark.parametrize('defect',['mode','manifest','model','case','worker','team'])
def test_actual_opponent_identity_mismatch_fails_closed(defect):
    x=identity(3)
    if defect=='mode':x['opponent_mode']='argmax'
    elif defect=='manifest':x['TRAIN_foundation_opponent']['manifest']['policy_slots'][3]='foundation_argmax'
    elif defect=='model':x['TRAIN_foundation_opponent']['model_SHA256']='e'*64
    elif defect=='case':x['TRAIN_foundation_opponent']['session']['case_index']=4
    elif defect=='worker':x['worker']=1
    else:x['TRAIN_foundation_opponent']['session']['team_sha256']['self']='e'*64
    with pytest.raises(ValueError):impl.verify_training_identity(x,116051,MODEL)


@pytest.mark.parametrize('seed',[0,116052,116091,True])
def test_unapproved_training_seed_rejected(seed):
    with pytest.raises(ValueError):impl.manifest(seed,MODEL)


def test_quality_rng_default_is_preserved_new_evaluation_namespace_is_separate():
    kwargs={'case':0,'seat':'p1','role':'rival','record':lambda *a:None}
    a=QualityActor(Parent(),'foundation_masked_sample',**kwargs)
    b=QualityActor(Parent(),'foundation_masked_sample',**kwargs,rng_namespace=116091)
    assert a.address['seed_namespace']==116081 and b.address['seed_namespace']==116091 and a.seed!=b.seed
    assert a.seed==int.from_bytes(sha256(content_hash(a.address).encode()).digest()[:16],'big')


def test_PPO_to_native_join_uses_predecision_link_not_postreset_episode(tmp_path,monkeypatch):
    reference=tmp_path/'reference';reference.write_bytes(b'fixture')
    recorder=impl.Recorder(tmp_path/'rollouts',None,reference)
    monkeypatch.setattr(impl.AuditedSignalRecorder,'end',lambda self,m,c:setattr(self,'pending',('mock',c)))
    obs=np.zeros((2,4,2),np.float32);actions=np.ones((2,4,1))*6;masks=np.zeros((2,4,35),bool);masks[:,:,6]=True
    recorder.links=[]
    for t in range(2):
        infos=[{'episode_id':'new-after-terminal','pilot_public_link':{'episode_id':'actual-before-terminal',
            'action':6,'feature_SHA256':sha256(obs[t,w].tobytes()).hexdigest(),'decision_id':f'{t}:{w}',
            'native_trace':'mock','native_ordinal':t}} for w in range(4)]
        recorder.step(infos,[True]*4)
    model=SimpleNamespace(n_steps=2,n_envs=4,observation_space=SimpleNamespace(shape=(2,)),
        rollout_buffer=SimpleNamespace(observations=obs,actions=actions,action_masks=masks,returns=np.zeros((2,4))))
    recorder.end(model,0)
    joined=json.loads((tmp_path/'rollouts/mock.native_join.json').read_text())
    assert len(joined['rows'])==8 and {x['episode_id'] for x in joined['rows']}=={'actual-before-terminal'}
    assert json.loads((tmp_path/'rollouts/first_rollout_provenance.json').read_text())['status']=='OPPONENT_MIXTURE_CHANGED_NO_BIT_EQUALITY_CLAIM'


@pytest.mark.parametrize('primary_gain',[False,True])
def test_sampled_rival_only_gain_never_passes_primary(primary_gain):
    cases=[{'index':i,'pair':i//4} for i in range(320)];rows=[]
    for rival in ['foundation_argmax','foundation_masked_sample']:
        for model in ['Foundation','A_s1','A_s2','Am_s1','Am_s2']:
            for c in cases:
                for seat in ['p1','p2']:
                    win=model.startswith('Am') and (primary_gain or rival=='foundation_masked_sample')
                    rows.append({'policy':model,'rival':rival,'seat':seat,'case':c['index'],
                        'record':{'return':1 if win else -1,'winner':'self' if win else 'opponent',
                            'truncated':False,'native_choice_rejections':0,'value_discounted_return_mse':None}})
    results,verdict=analyze_results(rows,cases)
    assert results['foundation_masked_sample']['team_pair_clusters']==80
    assert results['foundation_argmax']['outcomes']['Foundation']['visited_state_terminal_value_MSE'] is None
    assert verdict==('MIXED_OPPONENT_CONTROLLED_EXPERIMENT_COMPLETE' if primary_gain else 'DEVELOPMENT_SIGNAL_NOT_CONFIRMED')
    with pytest.raises(ValueError):analyze_results(rows[:-1],cases)
