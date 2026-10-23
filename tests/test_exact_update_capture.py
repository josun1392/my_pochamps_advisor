"""Synthetic-buffer optimizer tests: ZERO native or Gym environment steps.

The small fixture tests recorder transparency, original sampler replay and loss
arithmetic without spending any of the authorized native 512-transition cap.
"""
from copy import deepcopy
from types import SimpleNamespace
import gymnasium as gym
import numpy as np
import pytest
import torch
from torch import nn
from stable_baselines3.common.logger import configure
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from advisor.learned_parent_anchor import ParentAnchoredFoundationPPO, anchor_contract
from advisor.learned_exact_update import (ExactUpdateCapture, load_capture, restore_training,
    restore_policy, compare_trees, policy_state, loss_terms, atomic_torch)


class NoStepEnv(gym.Env):
    observation_space=gym.spaces.Box(-2,4,(4,),dtype=np.float32)
    action_space=gym.spaces.Discrete(3)
    def step(self,*args):raise AssertionError('tests_must_not_collect_environment_steps')
    def reset(self,*args,**kwargs):raise AssertionError('tests_must_not_reset_environment')


class Policy(MaskableActorCriticPolicy):
    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        self.prediction_test=nn.Linear(4,1)
        self.optimizer=self.optimizer_class(self.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)


class ToyFoundation(ParentAnchoredFoundationPPO):
    def prepare_parent_reference(self):return self.reference
    def _supervised_loss(self,observations,labels):
        prediction=self.policy.prediction_test(observations.detach()).flatten()
        target=torch.tensor([r['test_target'] for r in labels])
        weights=torch.tensor(self._aux_weights)
        return ((prediction-target).square()*weights).sum()/weights.sum(),{}


def model():
    torch.set_num_threads(1)
    m=ToyFoundation(Policy,NoStepEnv(),n_steps=8,batch_size=4,n_epochs=2,
        gamma=1,gae_lambda=.95,learning_rate=5e-5,ent_coef=.01,zero_avoiding_beta=.001,
        parent_policy_anchor=anchor_contract('a'*64,'b'*64,0),seed=77,target_kl=.03,device='cpu')
    reference=deepcopy(m.policy);reference.requires_grad_(False);reference.set_training_mode(False)
    m.reference=SimpleNamespace(model=SimpleNamespace(policy=reference))
    # Make the frozen teacher different, so parent KL gradients are nonzero.
    with torch.no_grad():reference.action_net.bias[0]+=.25
    b=m.rollout_buffer
    x=np.arange(32,dtype=np.float32).reshape(8,4)/32
    mask=np.array([[1,1,0]],dtype=bool)
    with torch.no_grad():
        for i in range(8):
            a=torch.tensor([i%2]);v,lp,_=m.policy.evaluate_actions(torch.tensor(x[i:i+1]),a,action_masks=mask)
            b.add(x[i:i+1],a.numpy().reshape(1,1),np.array([0.],np.float32),np.array([i==0]),v,lp,action_masks=mask)
    b.advantages[:,0]=np.linspace(-1,1,8,dtype=np.float32)
    b.returns[:,0]=np.linspace(1,-1,8,dtype=np.float32)
    m._auxiliary_rows=[{'action_family':i%2,'test_target':float(i%3)} for i in range(8)]
    m._auxiliary_observations=x.copy();m._aux_groups=None;m._aux_weights=None
    m.num_timesteps=8;m._current_progress_remaining=.5;m.set_logger(configure(format_strings=[]))
    return m


def recorded(tmp_path):
    m=model()
    with ExactUpdateCapture(m,tmp_path/'actual',expected_transitions=8) as recorder:m.train()
    assert recorder.steps==4
    return m,load_capture(tmp_path/'actual/training.pt')


def test_recorder_transparent_and_exact_original_sampler_Adam_replay(tmp_path):
    m,saved=recorded(tmp_path)
    actual=policy_state(m.policy)
    restore_training(m,saved)
    # Uninstrumented maintained train must produce identical weights and Adam.
    m.train()
    assert compare_trees(actual,policy_state(m.policy))['exact']
    restore_training(m,saved)
    with ExactUpdateCapture(m,tmp_path/'replay',expected_transitions=8):m.train()
    for p in (tmp_path/'actual').glob('*.pt'):
        assert compare_trees(load_capture(p),load_capture(tmp_path/'replay'/p.name))['exact']


def test_exact_loss_gradient_clipping_and_single_Adam_step(tmp_path):
    m,saved=recorded(tmp_path);s=load_capture(tmp_path/'actual/step_00.pt')
    restore_policy(m.policy,s['before']);terms,combine,_=loss_terms(m,saved,s)
    assert torch.equal(combine().detach(),s['upstream']['loss'])
    params=dict(m.policy.named_parameters())
    aux=torch.autograd.grad(terms['auxiliary'],tuple(params.values()),retain_graph=True,allow_unused=True)
    assert all(g is None or not g.any() for n,g in zip(params,aux) if 'prediction_' not in n)
    assert any(g is not None and g.any() for n,g in zip(params,aux) if 'prediction_' in n)
    policy=torch.autograd.grad(terms['policy'],tuple(params.values()),retain_graph=True,allow_unused=True)
    assert all(g is None for n,g in zip(params,policy) if 'prediction_' in n)
    combine().backward()
    assert compare_trees({n:p.grad for n,p in params.items() if p.grad is not None},s['gradient_before_clip'])['exact']
    torch.nn.utils.clip_grad_norm_(m.policy.parameters(),m.max_grad_norm)
    assert compare_trees({n:p.grad for n,p in params.items() if p.grad is not None},s['gradient_after_clip'])['exact']
    m.policy.optimizer.step()
    assert compare_trees(policy_state(m.policy),s['after'])['exact']
    restore_policy(m.policy,s['before']);_,omit,_=loss_terms(m,saved,s);omit('auxiliary').backward()
    assert all(p.grad is None for n,p in m.policy.named_parameters() if 'prediction_' in n)


def test_capture_bounds_and_artifact_overwrite_fail_closed(tmp_path):
    m=model()
    with pytest.raises(ValueError,match='cap'):ExactUpdateCapture(m,tmp_path/'bad',expected_transitions=513)
    atomic_torch(tmp_path/'receipt.pt',{'n':1})
    with pytest.raises(FileExistsError):atomic_torch(tmp_path/'receipt.pt',{'n':2})


def test_exact_comparison_rejects_dtype_and_shape_changes():
    assert not compare_trees(torch.ones(2),torch.ones(2,dtype=torch.float64))['exact']
    assert not compare_trees(np.ones(2),np.ones(3))['exact']


def test_existing_native_start_marker_blocks_before_any_environment_import(tmp_path,monkeypatch):
    import scripts.diagnose_foundation_exact_update as runner
    monkeypatch.setattr(runner,'verify',lambda out:{'transitions':512})
    (tmp_path/'native_started.json').write_text('{}')
    with pytest.raises(ValueError,match='already_started'):
        runner.capture(tmp_path)


def test_second_train_call_fails_before_advancing_Adam(tmp_path):
    m=model()
    with ExactUpdateCapture(m,tmp_path/'once',expected_transitions=8):
        m.train();state=policy_state(m.policy)
        with pytest.raises(ValueError,match='second_rollout_update'):m.train()
        assert compare_trees(state,policy_state(m.policy))['exact']
