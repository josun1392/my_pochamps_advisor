"""Synthetic public views and mock Foundation only: no model/native execution."""
from copy import deepcopy
import json
from types import SimpleNamespace
import random

import gymnasium as gym
import numpy as np
import pytest
import torch

from advisor.learned_checkpoint_rng import isolated_checkpoint_rng, rng_neutral_load
from advisor.learned_execution_alignment import content_hash, masked_sample
from advisor.learned_selfplay_pilot import FrozenPublicActor, AuditedPilotEnv
from advisor.learned_train_opponents import (
    VERSION, KEY, TrainFoundationOpponent, validate_manifest, mixture_identity,
)

MODEL='a'*64


def manifest(policy='foundation_argmax', **kwargs):
    return {'schema_version':VERSION,'scope':'train','model_SHA256':MODEL,
            'training_seed':77,'rng_namespace':'synthetic-fixture-only',
            'policy_slots':[policy],**kwargs}


def episode(index=0):
    return {'split':'train','case_index':index,'scenario_id':f'synthetic:{index}',
            'scenario_sha256':'b'*64,'team_sha256':{'self':'c'*64,'opponent':'d'*64},
            'native_seed':[1,2,3,4],'opponent':'league_s0','opponent_model_id':MODEL}


def view(revision=0, **kwargs):
    return {'side':'opponent','episode_id':'synthetic-session','revision':revision,'turn':revision+1,
            'request_state':'move','own_request':{'side':{'id':'p2','pokemon':[]}},
            'state':{},'public_history':[],'action_schema_version':'showdown-policy-actions-v1',
            'action_mask':[int(i in (6,7,8)) for i in range(35)],
            'choices':[f'public choice {i}' for i in range(35)],**kwargs}


class FakeFoundation:
    def __init__(self, probabilities=None):
        self.model_id=MODEL;self.metadata={'combat_foundation':{'mock':True}}
        self.probabilities=probabilities or [(.25 if i in (6,8) else .5 if i==7 else 0.) for i in range(35)]
        self.inputs=[];self.override={};self.immutable_weights=[.25,-.5];self.Adam={'step':32768}
    def infer(self, observation):
        self.inputs.append(deepcopy(observation))
        return {'action_index':int(np.argmax(self.probabilities)),'action_probabilities':list(self.probabilities),
                'model_id':self.model_id,'episode_id':observation['episode_id'],
                'revision':observation['revision'],'side':observation['side'],
                'action_schema_version':'showdown-policy-actions-v1',**self.override}


def adapter(policy='foundation_argmax', *, parent=None, spec=None, ep=None, worker=0, segment=0):
    ep=ep or episode()
    return TrainFoundationOpponent(parent or FakeFoundation(),spec or manifest(policy),ep,
                                   worker=worker,segment=segment,legacy_seed=ep['case_index']+91)


def global_state():
    py=random.getstate();np_state=np.random.get_state()
    return content_hash({'python':py,'numpy':[np_state[0],np_state[1].tolist(),*np_state[2:]],
                         'torch':torch.get_rng_state().tolist()})


@pytest.fixture(autouse=True)
def isolate_test_process():
    with isolated_checkpoint_rng():yield


def test_explicit_argmax_matches_original_inputs_outputs_and_RNG_bit_exact():
    old_parent,new_parent=FakeFoundation(),FakeFoundation()
    old=FrozenPublicActor(old_parent,'argmax',91);new=adapter(parent=new_parent)
    before=global_state();weights=deepcopy(new_parent.immutable_weights);Adam=deepcopy(new_parent.Adam)
    for i in range(64):
        v=view(i)
        assert old.act(v)==new.act(v)==7
        for key,value in old.last.items():assert new.last[key]==value
        assert old.rng.bit_generator.state==new.core.rng.bit_generator.state
    assert old_parent.inputs==new_parent.inputs and new.draws==0
    assert global_state()==before and weights==new_parent.immutable_weights and Adam==new_parent.Adam


def test_sampling_uses_exact_maintained_CDF_private_rng_and_no_global_draws():
    a=adapter('foundation_masked_sample');b=adapter('foundation_masked_sample')
    expected=np.random.default_rng(a.seed);before=global_state();selected=[]
    for i in range(128):
        v=view(i);u=float(expected.random())
        action=a.act(v);selected.append(action)
        assert action==b.act(v)==masked_sample(a.parent.probabilities,v['action_mask'],u)
        assert a.last['uniform']==u and v['action_mask'][action]
        assert a.last['TRAIN_opponent']['policy']=='foundation_masked_sample'
        assert a.last['TRAIN_opponent']['rng_address']==a.address
    assert set(selected)=={6,7,8} and a.draws==a.selections==128
    assert global_state()==before
    assert all(set(x)==set(view()) for x in a.parent.inputs)


def test_native_hidden_metadata_does_not_enter_input_or_sampling_seed():
    one=episode();other=episode();other['team_sha256']['opponent']='e'*64
    other['native_seed']=[65535,9,8,7];other['scenario_sha256']='f'*64
    a=adapter('foundation_masked_sample',ep=one);b=adapter('foundation_masked_sample',ep=other)
    assert a.identity()['session_SHA256']!=b.identity()['session_SHA256']
    assert a.address==b.address and a.seed==b.seed
    assert [a.act(view(i)) for i in range(32)]==[b.act(view(i)) for i in range(32)]
    assert a.parent.inputs==b.parent.inputs
    assert all(not {'native_seed','team_sha256','TRAIN_opponent','scenario','seed'}&set(x) for x in a.parent.inputs)


def test_worker_segment_and_training_seed_address_separate_streams():
    a=adapter('foundation_masked_sample')
    b=adapter('foundation_masked_sample',worker=1)
    c=adapter('foundation_masked_sample',segment=1)
    d=adapter(spec=manifest('foundation_masked_sample',training_seed=78))
    assert len({x.seed for x in (a,b,c,d)})==4
    # Unrelated learner/global/native-fixture RNG calls cannot advance a's stream.
    expected=np.random.default_rng(a.seed)
    for i in range(16):
        random.random();np.random.rand(5);torch.rand(5)
        a.act(view(i));assert a.last['uniform']==float(expected.random())


@pytest.mark.parametrize('policy',['foundation_argmax','foundation_masked_sample'])
def test_singleton_mask_is_authoritative_and_draw_cursor_explicit(policy):
    p=[float(i==8) for i in range(35)];a=adapter(policy,parent=FakeFoundation(p))
    for i in range(12):assert a.act(view(i,action_mask=[int(j==8) for j in range(35)]))==8
    assert a.draws==(12 if policy=='foundation_masked_sample' else 0)


@pytest.mark.parametrize('mask',[[0]*35,[1]*34,[2]+[0]*34,[float('nan')]+[0]*34])
def test_invalid_mask_never_infers_or_advances_rng(mask):
    a=adapter('foundation_masked_sample');before=a.state_dict()
    with pytest.raises(ValueError):a.act(view(action_mask=mask))
    assert not a.parent.inputs and a.state_dict()==before


@pytest.mark.parametrize('key',['native_state','teams','seed','opponent_request','future','labels'])
def test_forbidden_private_root_is_rejected_before_mock_inference(key):
    a=adapter('foundation_masked_sample');before=a.state_dict()
    with pytest.raises(ValueError,match='private_predictor_input'):a.act(view(**{key:'forbidden'}))
    assert not a.parent.inputs and a.state_dict()==before


@pytest.mark.parametrize('defect',['illegal_mass','nonfinite','negative','sum','shape','argmax','model','episode','revision'])
def test_invalid_proof_never_draws_or_substitutes_a_fallback(defect):
    parent=FakeFoundation();a=adapter('foundation_masked_sample',parent=parent)
    if defect=='illegal_mass':parent.probabilities[0]=.1;parent.probabilities[7]-=.1
    elif defect=='nonfinite':parent.probabilities[7]=float('nan')
    elif defect=='negative':parent.probabilities[6]=-.25
    elif defect=='sum':parent.probabilities[7]=.7
    elif defect=='shape':parent.probabilities=parent.probabilities[:-1]
    elif defect=='argmax':parent.override['action_index']=6
    elif defect=='model':parent.override['model_id']='e'*64
    elif defect=='episode':parent.override['episode_id']='other-session'
    elif defect=='revision':parent.override['revision']=99
    before=a.state_dict()
    with pytest.raises(ValueError):a.act(view())
    assert a.state_dict()==before


@pytest.mark.parametrize('defect',['side','episode','revision','parent_model'])
def test_bound_public_session_and_model_cannot_change(defect):
    a=adapter('foundation_masked_sample');a.act(view(2));before=a.state_dict()
    v=view(3)
    if defect=='side':v.update(side='self',own_request={'side':{'id':'p1'}})
    elif defect=='episode':v['episode_id']='other-session'
    elif defect=='revision':v['revision']=1
    else:a.parent.model_id='e'*64
    with pytest.raises(ValueError):a.act(v)
    assert a.state_dict()==before


@pytest.mark.parametrize('policy',['foundation_argmax','foundation_masked_sample'])
def test_rng_checkpoint_reconstruction_matches_uninterrupted_without_real_model_load(tmp_path,policy):
    uninterrupted=adapter(policy)
    for i in range(37):uninterrupted.act(view(i))
    path=tmp_path/'rng-only.json';path.write_text(json.dumps(uninterrupted.state_dict()))
    before=global_state()
    def mock_checkpoint_reload(*args,**kwargs):
        random.seed(95017);np.random.seed(95017);torch.manual_seed(95017);torch.rand(13)
        return FakeFoundation()
    parent=rng_neutral_load(mock_checkpoint_reload,'synthetic-not-a-model')
    restored=adapter(policy,parent=parent);restored.load_state_dict(json.loads(path.read_text()))
    assert global_state()==before
    for i in range(37,101):
        assert restored.act(view(i))==uninterrupted.act(view(i))
        assert restored.last==uninterrupted.last and restored.state_dict()==uninterrupted.state_dict()
    with pytest.raises(ValueError,match='fresh_adapter'):restored.load_state_dict(json.loads(path.read_text()))


@pytest.mark.parametrize('defect',['missing','checksum','draws','rng','session','policy'])
def test_rng_restore_identity_and_cursor_are_fail_closed(defect):
    source=adapter('foundation_masked_sample');source.act(view());state=source.state_dict()
    target=adapter('foundation_masked_sample');before=target.state_dict()
    if defect=='missing':state.pop('rng_state')
    elif defect=='checksum':state['SHA256']='0'*64
    else:
        if defect=='draws':state['draws']+=1
        elif defect=='rng':state['rng_state']=np.random.PCG64(91).state
        elif defect=='session':state['identity']['session']['case_index']+=1
        elif defect=='policy':state['identity']['policy']='foundation_argmax'
        state['SHA256']=content_hash({k:v for k,v in state.items() if k!='SHA256'})
    with pytest.raises(ValueError):target.load_state_dict(state)
    assert target.state_dict()==before


@pytest.mark.parametrize('patch',[{'scope':'validation'},{'model_SHA256':'e'*64},{'policy_slots':[]},
                                 {'policy_slots':['unknown']},{'rng_namespace':''},{'training_seed':True},
                                 {'extra':1}])
def test_manifest_is_train_only_explicit_and_sha_bound(patch):
    with pytest.raises(ValueError):validate_manifest(manifest(**patch),MODEL)


@pytest.mark.parametrize('value',[None,[],{},'train'])
def test_missing_or_malformed_manifest_has_no_implicit_policy(value):
    with pytest.raises(ValueError):validate_manifest(value,MODEL)
    with pytest.raises(ValueError):mixture_identity(value)


def test_non_Foundation_or_wrong_checkpoint_never_infers():
    parent=FakeFoundation();parent.metadata={}
    with pytest.raises(ValueError,match='frozen_Foundation'):adapter(parent=parent)
    parent=FakeFoundation();parent.model_id='e'*64
    with pytest.raises(ValueError):adapter(parent=parent)
    assert not parent.inputs


def test_future_mixture_is_caller_supplied_and_no_default_ratio_is_invented():
    spec=manifest(policy_slots=['foundation_argmax','foundation_masked_sample','foundation_argmax'])
    assert mixture_identity(spec)['nominal_episode_probabilities']=={
        'foundation_argmax':2/3,'foundation_masked_sample':1/3}
    assert [adapter(spec=spec,ep=episode(i)).policy_name for i in range(3)]==spec['policy_slots']
    frozen=adapter(spec=spec);spec['policy_slots'][0]='foundation_masked_sample'
    assert frozen.policy_name=='foundation_argmax'


def test_unversioned_generator_algorithm_is_not_silently_accepted(monkeypatch):
    monkeypatch.setattr(np.random,'default_rng',lambda seed:np.random.Generator(np.random.MT19937(seed)))
    with pytest.raises(ValueError,match='versioned_PCG64'):adapter('foundation_masked_sample')


class FakeEnv(gym.Env):
    observation_space=gym.spaces.Box(-1.,1.,shape=(1,),dtype=np.float32)
    action_space=gym.spaces.Discrete(35)
    def __init__(self,parent,subset=None):
        self.encoder=SimpleNamespace(encode=lambda v:np.zeros(1,dtype=np.float32))
        self.opponent_factory=lambda kind,seed:parent
        self.opponent_kind='league_s0';self.opponent=parent;self.split='train'
        self.training_subset=subset or SimpleNamespace(seed=77,segment=0,worker=0)
        self._episode_identity=episode()
        self.current=view(side='self',own_request={'side':{'id':'p1'}})


@pytest.mark.parametrize('policy',[None,'foundation_argmax','foundation_masked_sample'])
def test_existing_audited_train_wrapper_connects_optin_and_preserves_default(tmp_path,policy):
    parent=FakeFoundation();env=FakeEnv(parent)
    kwargs={} if policy is None else {'train_foundation_opponent':manifest(policy)}
    wrapped=AuditedPilotEnv(env,tmp_path,SimpleNamespace(),0,0,True,**kwargs)
    try:
        record=json.loads((tmp_path/'identity_0000.json').read_text())
        if policy is None:
            assert type(env.opponent) is FrozenPublicActor and env.opponent.mode=='argmax'
            assert 'TRAIN_foundation_opponent' not in record
        else:
            assert type(env.opponent) is TrainFoundationOpponent
            assert record['TRAIN_foundation_opponent']['policy']==policy
            assert record['opponent_mode']==env.opponent.mode
        action=env.opponent.act(view())
        assert action in (6,7,8) and (policy=='foundation_masked_sample' or action==7)
        if policy:assert env.opponent.last['TRAIN_opponent']['session']['team_sha256']==episode()['team_sha256']
    finally:wrapped.close()  # Mock fixture close only; no simulator exists.


def test_wrapper_copies_frozen_manifest_instead_of_reading_mutable_caller_spec(tmp_path):
    spec=manifest();env=FakeEnv(FakeFoundation())
    wrapped=AuditedPilotEnv(env,tmp_path,SimpleNamespace(),0,0,True,train_foundation_opponent=spec)
    try:
        spec['policy_slots'][0]='foundation_masked_sample'
        actor=env.opponent_factory('league_s0',91)
        assert actor.policy_name=='foundation_argmax'
    finally:wrapped.close()


@pytest.mark.parametrize('defect',['manifest','case_seed','unsupported_factory'])
def test_optin_rejected_before_native_constructor(defect,tmp_path,monkeypatch):
    import advisor.learned_gym as gym_module
    from advisor.learned_fixed_micro import training_vector, MATCHUP_VERSION
    plan={'schema_version':MATCHUP_VERSION,'opponents':['league_s0'],
          'micro_budget':{'transitions':16384,'Adam':512,'starts':4096,'targets':[4096,8192,12288,16384]},
          KEY:manifest()}
    if defect=='manifest':plan[KEY]['scope']='test'
    elif defect=='unsupported_factory':plan['schema_version']='unsupported'
    factory=lambda worker:SimpleNamespace(seed=78 if defect=='case_seed' else 77,worker=worker,segment=0)
    monkeypatch.setattr(gym_module,'ShowdownLearningEnv',lambda *a,**k:pytest.fail('native constructor forbidden'))
    with pytest.raises(ValueError):
        training_vector(plan,tmp_path,FakeFoundation(),case_factory=factory,start_budget=SimpleNamespace(maximum=4096))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('policy',[None,'foundation_argmax','foundation_masked_sample'])
def test_actual_training_vector_connects_four_mock_workers_without_native(tmp_path,monkeypatch,policy):
    import advisor.learned_gym as gym_module
    import advisor.learned_combat_foundation as foundation_module
    from advisor.learned_fixed_micro import training_vector, MATCHUP_VERSION
    plan={'schema_version':MATCHUP_VERSION,'opponents':['league_s0'],'checkout':'mock-only','catalog':'mock-only',
          'micro_budget':{'transitions':16384,'Adam':512,'starts':4096,'targets':[4096,8192,12288,16384]}}
    if policy is not None:plan[KEY]=manifest(policy)
    parent=FakeFoundation();starts=[]
    budget=SimpleNamespace(maximum=4096,reserve=lambda row:starts.append(row) or len(starts)-1)
    def make(**kwargs):
        env=FakeEnv(parent,kwargs['training_subset'])
        env.encoder=kwargs['encoder']
        env._episode_identity=episode(kwargs['index_offset'])
        env.opponent_factory=kwargs['opponent_factory']
        env.current=view(side='self',own_request={'side':{'id':'p1'}},
                         episode_id=f"mock-worker-{kwargs['index_offset']}")
        return env
    # Replace the native owner and feature encoder BEFORE constructing the vector.
    monkeypatch.setattr(gym_module,'ShowdownLearningEnv',lambda checkout,encoder,**kw:make(encoder=encoder,**kw))
    monkeypatch.setattr(foundation_module,'FoundationCombatEncoder',
                        lambda _:SimpleNamespace(encode=lambda v:np.zeros(1,dtype=np.float32)))
    monkeypatch.setattr(foundation_module,'install_environment_profile',lambda _:None)
    factory=lambda w:SimpleNamespace(seed=77,worker=w,segment=2)
    before=global_state()
    vector,returned=training_vector(plan,tmp_path,parent,case_factory=factory,start_budget=budget)
    try:
        assert returned is budget and len(starts)==4 and len(vector.envs)==4
        for w,wrapper in enumerate(vector.envs):
            actor=wrapper.env.opponent
            assert (type(actor) is FrozenPublicActor) if policy is None else (type(actor) is TrainFoundationOpponent)
            actual=actor.act(view(episode_id=f'mock-worker-{w*100000}'))
            assert actual in (6,7,8)
            if policy is not None:
                assert actor.policy_name==policy and actor.session['segment']==2 and actor.session['worker']==w
            if policy!='foundation_masked_sample':assert actual==7
        assert global_state()==before
    finally:vector.close()  # No reset/step/rollout/learn is ever called.
