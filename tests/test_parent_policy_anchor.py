"""Frozen reference KL, exact zero path and real save/load optimizer behavior.

Optimizer tests use a synthetic fixed-public-view Gym fixture, never native PPO
transitions or research checkpoints. Native fixtures only reset both seats.
"""
from copy import deepcopy
import json
from pathlib import Path
import gymnasium as gym
import numpy as np
import pytest
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatPolicy, FoundationCombatEncoder
from advisor.learned_parent_anchor import (ParentAnchoredFoundationPPO, anchor_contract,
    parent_policy_kl, optimizer_clock, tensor_digest)
from advisor.learned_combat_v5_strategic_aux import supervision_targets
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_environment import ShowdownEnvironment
from scripts.train_showdown_autonomous import save_checkpoint, BudgetCallback, validate_config
from scripts.verify_showdown_integration import fixture_scenarios
from tests.test_combat_v5_strategic import checkout, CAT


class Budget:
    def stopping(self):return False


@pytest.fixture(scope='module')
def public_pair(checkout):
    torch.set_num_threads(1)
    with ShowdownEnvironment(checkout) as env:
        env.reset(fixture_scenarios()[0])
        return [env.observation(s,include_history=True) for s in ('self','opponent')]


class ToyPublicEnv(gym.Env):
    def __init__(self, pair):
        self.current=deepcopy(pair[0])
        self.encoder=FoundationCombatEncoder(CAT)
        self.features=self.encoder.encode(pair[0]);self.mask=np.array(pair[0]['action_mask'],bool)
        self.labels=supervision_targets(pair[0],pair[1],[],self.encoder)
        self.observation_space=gym.spaces.Box(-2,4,(len(self.features),),dtype=np.float32)
        self.action_space=gym.spaces.Discrete(35);self.i=0;self.episodes=0
    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);self.i=0
        return self.features.copy(),{}
    def action_masks(self):return self.mask.copy()
    def step(self,action):
        assert self.mask[action];self.i+=1;done=self.i==4
        reward=(1. if self.episodes%2==0 else -1.) if done else 0.
        self.episodes+=int(done)
        return self.features.copy(),reward,done,False,{'coordinator_v5_supervision':deepcopy(self.labels)}


def new_model(pair):
    return FoundationCombatPPO(FoundationCombatPolicy,ToyPublicEnv(pair),n_steps=8,batch_size=8,
        n_epochs=2,gamma=1.,gae_lambda=.95,learning_rate=5e-5,ent_coef=.01,zero_avoiding_beta=.001,
        seed=9871,device='cpu')


@pytest.fixture
def source(public_pair,tmp_path):
    model=new_model(public_pair);model.learn(8,callback=BudgetCallback(Budget()))
    encoder=FoundationCombatEncoder(CAT)
    path=save_checkpoint(model,encoder,tmp_path/'parent',{})
    loaded=LearnedPolicy(path,CAT)
    contract=anchor_contract(loaded.model_id,encoder.catalog_fingerprint,optimizer_clock(model.policy),.01)
    return path,contract,model


def load_anchor(path,contract,pair,coefficient=None):
    c=deepcopy(contract)
    if coefficient is not None:c['coefficient']=coefficient
    return ParentAnchoredFoundationPPO.load(path,env=ToyPublicEnv(pair),device='cpu',
        parent_policy_anchor=c,parent_reference_path=path,parent_catalog_path=str(CAT))


def assert_optimizer_equal(a,b):
    sa,sb=a.policy.optimizer.state_dict(),b.policy.optimizer.state_dict()
    assert sa['param_groups']==sb['param_groups'] and sa['state'].keys()==sb['state'].keys()
    for key,values in sa['state'].items():
        for name,value in values.items():
            if isinstance(value,torch.Tensor):torch.testing.assert_close(value,sb['state'][key][name],rtol=0,atol=0)
            else:assert value==sb['state'][key][name]


def test_hand_calculated_kl_gradients_and_illegal_actions():
    logits=torch.tensor([[.4,-.2,9.],[.2,.1,0.]],requires_grad=True)
    mask=torch.tensor([[True,True,False],[True,False,False]])
    current=logits.masked_fill(~mask,-1e8).log_softmax(-1)
    p=torch.tensor([[.25,.75,0.],[1.,0.,0.]])
    logp=p.clamp(min=1e-30).log()
    kl=parent_policy_kl(p,logp,current,mask)
    expected=.25*(np.log(.25)-float(current[0,0]))+.75*(np.log(.75)-float(current[0,1]))
    assert float(kl[0])==pytest.approx(expected,abs=1e-6) and float(kl[1])==0
    kl.mean().backward()
    assert torch.isfinite(logits.grad).all() and logits.grad[0,2]==0 and not logits.grad[1].any()
    assert logits.grad[0,:2].abs().sum()>0
    with pytest.raises(ValueError,match='mask'):parent_policy_kl(p,logp,current,torch.zeros_like(mask))
    with pytest.raises(ValueError,match='distribution'):parent_policy_kl(torch.ones_like(p),logp,current,mask)


def test_restored_parameters_Adam_initial_outputs_and_zero_equivalence(source,public_pair):
    path,contract,_=source
    base=FoundationCombatPPO.load(path,env=ToyPublicEnv(public_pair),device='cpu')
    zero=load_anchor(path,contract,public_pair,0.)
    assert tensor_digest(base.policy.state_dict())==tensor_digest(zero.policy.state_dict())
    assert_optimizer_equal(base,zero)
    x=torch.as_tensor(base.get_env().reset())
    mask=np.asarray(public_pair[0]['action_mask'],bool)[None]
    with torch.no_grad():
        bv=base.policy(x,action_masks=mask,deterministic=True)[1]
        zv=zero.policy(x,action_masks=mask,deterministic=True)[1]
    torch.testing.assert_close(bv,zv,rtol=0,atol=0)
    torch.testing.assert_close(base.policy.action_dist.distribution.probs,zero.policy.action_dist.distribution.probs,rtol=0,atol=0)
    base.set_random_seed(123);base.learn(8,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
    zero.set_random_seed(123);zero.learn(8,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
    assert tensor_digest(base.policy.state_dict())==tensor_digest(zero.policy.state_dict())
    assert_optimizer_equal(base,zero)
    assert zero._parent_reference is None


def test_nonzero_parent_frozen_save_load_continue_and_metadata_fail_closed(source,public_pair,tmp_path):
    path,contract,parent=source
    anchored=load_anchor(path,contract,public_pair)
    assert_optimizer_equal(anchored,parent)
    for view in public_pair:
        x=torch.as_tensor(FoundationCombatEncoder(CAT).encode(view))[None]
        masks=np.asarray(view['action_mask'])[None]
        with torch.no_grad():
            a=anchored.policy(x,action_masks=masks,deterministic=True)[1]
            p=parent.policy(x,action_masks=masks,deterministic=True)[1]
        torch.testing.assert_close(a,p,rtol=0,atol=0)
        torch.testing.assert_close(anchored.policy.action_dist.distribution.logits,parent.policy.action_dist.distribution.logits,rtol=0,atol=0)
    teacher=anchored.prepare_parent_reference().model
    teacher_parameters=tensor_digest(teacher.policy.state_dict())
    teacher_optimizer=deepcopy(teacher.policy.optimizer.state_dict())
    anchored.learn(16,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
    assert anchored.logger.name_to_value['train/parent_anchor_coefficient']==.01
    assert anchored.logger.name_to_value['train/parent_anchor_kl']>0
    assert anchored.logger.name_to_value['train/parent_anchor_weighted_loss']>0
    assert all(not p.requires_grad and p.grad is None for p in teacher.policy.parameters())
    assert tensor_digest(teacher.policy.state_dict())==teacher_parameters
    assert_optimizer_equal(teacher,parent)
    for k,row in teacher_optimizer['state'].items():
        for name,value in row.items():torch.testing.assert_close(value,teacher.policy.optimizer.state_dict()['state'][k][name],rtol=0,atol=0)
    saved=save_checkpoint(anchored,FoundationCombatEncoder(CAT),tmp_path/'anchored',{})
    restored=LearnedPolicy(saved,CAT)
    assert type(restored.model) is ParentAnchoredFoundationPPO
    assert restored.model.parent_policy_anchor==contract
    assert tensor_digest(restored.model.policy.state_dict())==tensor_digest(anchored.policy.state_dict())
    assert_optimizer_equal(restored.model,anchored)
    before=optimizer_clock(restored.model.policy)
    restored.model.set_env(ToyPublicEnv(public_pair))
    restored.model.learn(8,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
    assert optimizer_clock(restored.model.policy)==before+2
    assert restored.model.logger.name_to_value['train/parent_anchor_coefficient']==.01
    assert restored.model.logger.name_to_value['train/parent_anchor_kl']>0
    assert restored.model.parent_reference_proof()['frozen_unchanged']
    metadata_path=Path(saved).with_suffix('.json');metadata=json.loads(metadata_path.read_text())
    tampered=deepcopy(metadata);tampered['parent_policy_anchor']['coefficient']=.02
    metadata_path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError,match='anchor_persistence'):LearnedPolicy(saved,CAT)
    tampered=deepcopy(metadata);tampered.pop('parent_policy_anchor')
    metadata_path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError,match='anchor_loaded_as_base'):LearnedPolicy(saved,CAT)


def test_reference_only_receives_identical_public_features_and_mask(source,public_pair):
    path,contract,_=source;learner=load_anchor(path,contract,public_pair)
    reference=learner.prepare_parent_reference().model.policy
    captured=[];original=reference.get_distribution
    def observe(features,action_masks=None):
        captured.append((features.detach().clone(),np.asarray(action_masks).copy()))
        return original(features,action_masks=action_masks)
    reference.get_distribution=observe
    learner.learn(8,reset_num_timesteps=False,callback=BudgetCallback(Budget()))
    expected=FoundationCombatEncoder(CAT).encode(public_pair[0]);mask=np.asarray(public_pair[0]['action_mask'])
    assert captured
    for features,masks in captured:
        np.testing.assert_array_equal(features.numpy(),np.repeat(expected[None],len(features),axis=0))
        np.testing.assert_array_equal(masks,np.repeat(mask[None],len(features),axis=0))
    for field in ('opponent_request','future_seed','checkpoint','coordinator_v5_supervision'):
        with pytest.raises(ValueError,match='privileged_input'):
            FoundationCombatEncoder(CAT).encode({**public_pair[0],field:{}})


def test_invalid_contract_and_reference_identity_rejected(source,public_pair):
    path,contract,_=source
    for key,value in [('coefficient',float('nan')),('parent_model_sha256','bad'),('loss','unversioned')]:
        bad=deepcopy(contract);bad[key]=value
        with pytest.raises(ValueError):load_anchor(path,bad,public_pair)
    bad=deepcopy(contract);bad['parent_model_sha256']='0'*64
    learner=load_anchor(path,bad,public_pair)
    with pytest.raises(ValueError):learner.prepare_parent_reference()


def test_optional_scalar_joins_public_snapshots_and_update_boundary(public_pair,tmp_path):
    import gzip
    from advisor.learned_signal_recorder import PublicSignalRecorder
    model=new_model(public_pair)
    recorder=PublicSignalRecorder(tmp_path,FoundationCombatEncoder(CAT))
    model.learn(16,callback=BudgetCallback(Budget(),signal_recorder=recorder))
    files=list(tmp_path.glob('*.jsonl.gz'))
    assert len(files)==2
    rows=[json.loads(line) for path in files for line in gzip.open(path,'rt')]
    assert len(rows)==16
    assert all(r['legal_mask_bits'] & (1<<r['action']) for r in rows)
    assert not any('supervision' in json.dumps(r) for r in rows)
    assert all(r['Adam_after']>r['Adam_before'] for r in
               [json.loads(path.read_text()) for path in tmp_path.glob('*.settled.json')])
    snapshots=[json.loads(path.read_text()) for path in tmp_path.glob('public_*.json')]
    assert snapshots and snapshots[0]['observation']==public_pair[0]
