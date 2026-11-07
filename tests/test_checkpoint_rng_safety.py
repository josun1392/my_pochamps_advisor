"""Synthetic checkpoint/RNG tests: no native, combat inference or Adam.step."""
import ast
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from advisor.learned_checkpoint_rng import (
    isolated_checkpoint_rng, rng_neutral_load, reject_unrestorable_resume,
)


def states():
    return random.getstate(), np.random.get_state(), torch.get_rng_state().clone()


def equal(a, b):
    return (a[0] == b[0] and a[1][0] == b[1][0]
            and np.array_equal(a[1][1], b[1][1]) and a[1][2:] == b[1][2:]
            and torch.equal(a[2], b[2]))


def seed(value):
    random.seed(value); np.random.seed(value); torch.manual_seed(value)


@pytest.fixture(autouse=True)
def preserve_test_rng():
    with isolated_checkpoint_rng():
        yield


@pytest.mark.parametrize('error', [False, True])
def test_load_preserves_all_global_streams_and_next_draws(error):
    seed(116051); before=states()
    def loader(path, **kwargs):
        seed(95017); torch.rand(13)  # SB3 constructor behavior, no network.
        if error: raise RuntimeError('synthetic load failure')
        return 'restored'
    if error:
        with pytest.raises(RuntimeError):rng_neutral_load(loader,'synthetic')
    else:
        assert rng_neutral_load(loader,'synthetic')=='restored'
    assert equal(before,states())
    actual=(random.random(),np.random.permutation(512),torch.rand(8))
    seed(116051)
    assert actual[0]==random.random()
    assert np.array_equal(actual[1],np.random.permutation(512))
    assert torch.equal(actual[2],torch.rand(8))


def test_live_environment_is_never_passed_to_SB3_load():
    called=[]
    with pytest.raises(ValueError,match='live_environment'):
        rng_neutral_load(lambda *a,**k:called.append(k),'synthetic',env=object())
    assert called==[]


def test_CUDA_without_preexisting_state_is_rejected_before_load(monkeypatch):
    monkeypatch.setattr(torch.cuda,'is_initialized',lambda:False)
    with pytest.raises(ValueError,match='initialized_CUDA_rng'):
        rng_neutral_load(lambda *a,**k:pytest.fail('must not load'),'synthetic',device='cuda')


@pytest.mark.parametrize('device',['auto','mps'])
def test_implicit_or_untracked_device_is_rejected_before_load(device):
    with pytest.raises(ValueError,match='explicit_supported_device'):
        rng_neutral_load(lambda *a,**k:pytest.fail('must not load'),'synthetic',device=device)


def test_worker_count_override_does_not_touch_live_environment_rng():
    vector=SimpleNamespace(num_envs=2,seed_calls=[],sampler_position=17)
    def loader(path, **kwargs):
        assert 'env' not in kwargs and kwargs['n_envs']==vector.num_envs
        seed(95017)
        return SimpleNamespace(n_envs=kwargs['n_envs'],optimizer_progress=384)
    before=deepcopy(vector.__dict__);seed(71);rng=states()
    model=rng_neutral_load(loader,'synthetic',n_envs=vector.num_envs)
    assert vector.__dict__==before and equal(rng,states())
    assert model.n_envs==2 and model.optimizer_progress==384


def test_actual_SB3_load_order_preserves_synthetic_weights_Adam_and_worker_override(monkeypatch):
    from stable_baselines3.common import base_class
    from stable_baselines3.common.base_class import BaseAlgorithm
    import gymnasium as gym
    data={'seed':95017,'n_envs':4,'observation_space':gym.spaces.Box(-1.,1.,shape=(1,)),
          'action_space':gym.spaces.Discrete(35),'policy_class':'no network','policy_kwargs':{}}
    parameters={'policy':{'synthetic_weight':[.25,-.5]},
                'policy.optimizer':{'step':384,'exp_avg':[.125,-.25],'exp_avg_sq':[.01,.02]}}
    monkeypatch.setattr(base_class,'load_from_zip_file',lambda *a,**k:(deepcopy(data),deepcopy(parameters),None))
    class SyntheticAlgorithm:
        # Only the real SB3 load state machine is exercised; no network/Adam.
        load=classmethod(BaseAlgorithm.load.__func__)
        def __init__(self,*,policy,env,device,_init_setup_model):
            assert env is None and not _init_setup_model
            self.device=torch.device(device);self.env=None;self.use_sde=False
        def _setup_model(self):
            BaseAlgorithm.set_random_seed(self,self.seed)
            torch.rand(13)
        def set_parameters(self,payload,**kwargs):self.payload=deepcopy(payload)
    seed(116051);before=states()
    result=rng_neutral_load(SyntheticAlgorithm.load,'synthetic',n_envs=2)
    assert result.payload==parameters and result.n_envs==2 and result.env is None
    assert equal(before,states())


@pytest.mark.parametrize('training_seed',[116051,116053])
def test_4K_8K_12K_reloads_match_uninterrupted_sampler_and_progress(training_seed):
    """In-process checkpoint reconstruction; cold native resume is refused below.

    The optimizer ledger is synthetic data, NOT a real optimizer/update. Local
    Gym/native generators are represented separately and cannot reach the loader.
    """
    def execution(reload=False,unsafe=False):
        seed(training_seed)
        local=np.random.default_rng(training_seed+1)
        native=random.Random(training_seed+2)
        sampler={'position':0};optimizer={'step':0,'moments':[.25,-.5]}
        traces=[];boundaries=[]
        for block in range(16):
            for rollout in range(2):
                draws=(tuple(torch.rand(512).tolist()),random.random(),float(local.random()),native.random())
                sampler['position']+=512
                for epoch in range(4):
                    order=tuple(np.random.permutation(512))
                    auxiliary=tuple(np.random.randint(0,512,size=128).tolist())
                    traces.append((order,auxiliary,draws))
                    optimizer['step']+=4  # Four synthetic minibatch ledger entries, no Adam operation.
            if (block+1)*1024 in (4096,8192,12288):
                checkpoint=deepcopy({'optimizer':optimizer,'sampler':sampler})
                before=states();local_before=deepcopy(local.bit_generator.state);native_before=native.getstate()
                def load(*args,**kwargs):
                    seed(95017);torch.rand(13)
                    return deepcopy(checkpoint)
                if reload:
                    restored=load() if unsafe else rng_neutral_load(load,'synthetic')
                    optimizer,sampler=restored['optimizer'],restored['sampler']
                if not unsafe:
                    assert equal(before,states())
                    assert local.bit_generator.state==local_before and native.getstate()==native_before
                assert optimizer==checkpoint['optimizer'] and sampler==checkpoint['sampler']
                boundaries.append((optimizer['step'],sampler['position']))
        return traces,optimizer,sampler,boundaries,states()
    uninterrupted=execution()
    resumed=execution(reload=True)
    assert uninterrupted[:4]==resumed[:4] and equal(uninterrupted[4],resumed[4])
    assert resumed[3]==[(128,4096),(256,8192),(384,12288)]
    assert resumed[1]['step']==512 and resumed[2]['position']==16384
    unsafe=execution(reload=True,unsafe=True)
    assert unsafe[0]!=uninterrupted[0]  # Regression must detect the old seed95017 bug.


@pytest.mark.parametrize('module_name,class_name,metadata_name',[
    ('advisor.experimental_context_training','ResidualActor','residual_metadata.json'),
    ('advisor.experimental_critic_training','CriticTrainableActor','critic_metadata.json'),
])
def test_actual_experimental_constructors_use_rng_neutral_boundary(
        module_name,class_name,metadata_name,tmp_path,monkeypatch):
    import importlib
    module=importlib.import_module(module_name)
    payload=tmp_path/'synthetic.payload';payload.write_bytes(b'not a model; never unpickled')
    digest=sha256(payload.read_bytes()).hexdigest()
    class Policy:
        def set_training_mode(self,mode):assert mode is False
        def state_dict(self):return {}
        def named_parameters(self):return iter([])
    fake=SimpleNamespace(policy=Policy(),optimizer_progress=512)
    meta={'schema_version':module.VERSION,'version':module.VERSION,'mode':'set',
          'contract':module.contract('set') if class_name=='ResidualActor' else module.contract(),
          'model_SHA256':digest,'frozen_SHA256':'frozen','parameters_SHA256':'parameters',
          'optimizer_SHA256':'Adam','Adam_step':512,'trainable_names':[],
          'encoder_fingerprint':'catalog'}
    (tmp_path/metadata_name).write_text(json.dumps(meta))
    monkeypatch.setattr(module,'FoundationCombatEncoder',lambda _:SimpleNamespace(catalog_fingerprint='catalog'))
    monkeypatch.setattr(module,'validate_model',lambda *a,**k:None)
    monkeypatch.setattr(module,'tensor_digest',lambda _: 'parameters')
    monkeypatch.setattr(module,'optimizer_digest',lambda _: 'Adam')
    monkeypatch.setattr(module,'optimizer_clock',lambda _:512)
    def loader(path,**kwargs):seed(95017);torch.rand(13);return fake
    monkeypatch.setattr(module.FoundationCombatPPO,'load',loader)
    seed(116053);before=states()
    actor=getattr(module,class_name)(payload,'catalog')
    assert actor.model is fake and equal(before,states()) and fake.optimizer_progress==512


def test_incomplete_native_resume_rejected_before_any_mutation(tmp_path,monkeypatch):
    import scripts.train_showdown_autonomous as trainer
    original={'state.json':b'{"optimizer_steps":384,"latest":"historical.zip"}',
              'STOP':b'preserve','run.lock':b'{"pid":0}', 'sampler.json':b'{"position":42}'}
    for name,value in original.items():(tmp_path/name).write_bytes(value)
    monkeypatch.setattr(trainer,'validate_config',lambda _:pytest.fail('resume gate must run first'))
    monkeypatch.setattr(trainer,'WindowsJob',lambda **k:pytest.fail('no resource/native launch'))
    seed(116051);before=states()
    with pytest.raises(ValueError,match='checkpoint_resume_unavailable_rng_native_sampler_state'):
        trainer.run({},tmp_path,resume=True)
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()}==original
    assert equal(before,states())


def test_detached_resume_rejected_before_spawning_or_creating_directory(tmp_path,monkeypatch):
    import scripts.train_showdown_autonomous as trainer
    monkeypatch.setattr(trainer.subprocess,'Popen',lambda *a,**k:pytest.fail('must not spawn'))
    with pytest.raises(ValueError,match='checkpoint_resume_unavailable'):
        trainer.launch_detached(tmp_path/'absent.json',tmp_path/'absent',True)
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize('existing_state',[{'status':'stopped','optimizer_steps':128},{},None,[]])
def test_league_incomplete_generation_rejected_before_event_or_config_write(tmp_path,monkeypatch,existing_state):
    import scripts.train_showdown_snapshot_league as league
    plan={'B0':{'path':'original','sha256':'parent'},'generations':1,'base_config':{}}
    raw=json.dumps(plan).encode();plan_path=tmp_path/'plan.json';plan_path.write_bytes(raw)
    output=tmp_path/'chain';output.mkdir()
    (output/'chain_state.json').write_text(json.dumps({'plan_sha256':sha256(raw).hexdigest(),'chain':'F-s1','completed':[]}))
    generation=output/'generation_00';generation.mkdir()
    (generation/'state.json').write_text(json.dumps(existing_state))
    monkeypatch.setattr(league,'validate_chain_plan',lambda *a:None)
    monkeypatch.setattr(league,'checkpoint_identity',lambda *a:plan['B0'])
    monkeypatch.setattr(league,'generation_config',lambda *a:{})
    monkeypatch.setattr(league,'WindowsJob',lambda **k:object())
    monkeypatch.setattr(league,'run',lambda *a,**k:pytest.fail('must not resume'))
    snapshot={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='checkpoint_resume_unavailable'):
        league.run_chain(plan_path,output,'F-s1',resume=True)
    assert snapshot=={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_league_resume_without_chain_state_never_starts_a_fresh_generation(tmp_path,monkeypatch):
    import scripts.train_showdown_snapshot_league as league
    plan={'B0':{'path':'original','sha256':'parent'},'generations':1,'base_config':{}}
    plan_path=tmp_path/'plan.json';plan_path.write_text(json.dumps(plan))
    monkeypatch.setattr(league,'validate_chain_plan',lambda *a:None)
    monkeypatch.setattr(league,'checkpoint_identity',lambda *a:plan['B0'])
    monkeypatch.setattr(league,'WindowsJob',lambda **k:pytest.fail('must not launch'))
    with pytest.raises(ValueError,match='checkpoint_resume_unavailable'):
        league.run_chain(plan_path,tmp_path/'absent','F-s1',resume=True)
    assert not (tmp_path/'absent').exists()


def test_completed_league_generation_still_skips_without_training(tmp_path,monkeypatch):
    import scripts.train_showdown_snapshot_league as league
    parent={'path':'original','sha256':'parent'}
    plan={'B0':parent,'generations':1,'base_config':{}}
    raw=json.dumps(plan).encode();plan_path=tmp_path/'plan.json';plan_path.write_bytes(raw)
    output=tmp_path/'chain';output.mkdir()
    (output/'chain_state.json').write_text(json.dumps({'plan_sha256':sha256(raw).hexdigest(),'chain':'F-s1','completed':[parent]}))
    monkeypatch.setattr(league,'validate_chain_plan',lambda *a:None)
    monkeypatch.setattr(league,'checkpoint_identity',lambda *a:parent)
    monkeypatch.setattr(league,'WindowsJob',lambda **k:object())
    monkeypatch.setattr(league,'run',lambda *a,**k:pytest.fail('must not train'))
    assert league.run_chain(plan_path,output,'F-s1',resume=True)['status']=='complete'


def test_existing_actionable_guard_matches_shared_guard_without_model_calls():
    source=Path(__file__).resolve().parents[1]/'advisor/experimental_actionable_advantage.py'
    node=next(n for n in ast.parse(source.read_text(encoding='utf-8')).body
              if isinstance(n,ast.FunctionDef) and n.name=='isolated_loader_rng')
    ns=dict(contextmanager=contextmanager,np=np,torch=torch,random=random)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<existing CPU guard>','exec'),ns)
    for guard in (ns['isolated_loader_rng'],isolated_checkpoint_rng):
        seed(116051);before=states()
        with guard():seed(95017);torch.rand(13)
        assert equal(before,states())


def test_trainer_fallback_never_attaches_live_vector_inside_SB3_load():
    source=Path(__file__).resolve().parents[1]/'scripts/train_showdown_autonomous.py'
    tree=ast.parse(source.read_text(encoding='utf-8'))
    run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    load=next(n for n in ast.walk(run) if isinstance(n,ast.Call)
              and isinstance(n.func,ast.Name) and n.func.id=='rng_neutral_load')
    assert ast.unparse(load.args[0])=='algorithm.load'
    assert 'env' not in {k.arg for k in load.keywords}
    assert any(k.arg=='n_envs' and ast.unparse(k.value)=='vector.num_envs' for k in load.keywords)
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                   and ast.unparse(n.func)=='algorithm.load' for n in ast.walk(run))
