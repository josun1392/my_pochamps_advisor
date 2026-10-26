from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
import torch

from advisor.learned_policy_matched_signals import (
    HistoricalSampler, return_signals, policy_matched_branch, paired_summary,
)
from tests.test_update_credit import ProbePolicy


def row(reward, value, nxt, terminated=False, truncated=False):
    return dict(reward=reward,value=value,next_value=nxt,terminated=terminated,truncated=truncated)


def test_finite_lambda_return_matches_hand_GAE_and_rollout_cut():
    rows=[row(0,.2,.3),row(0,.3,.4),row(1,.4,0,terminated=True)]
    result=return_signals(rows,gamma=1.,gae_lambda=.95,horizon=128)
    assert result["full_return"]==1
    assert result["finite_critic_advantage"]==pytest.approx(.7365)
    assert result["finite_lambda_return"]==pytest.approx(.9365)
    cut=return_signals(rows,gamma=1.,gae_lambda=.95,horizon=1)
    assert cut["finite_lambda_return"]==pytest.approx(.3)


def test_timeout_bootstrap_is_not_draw_and_no_episode_boundary_crossing():
    result=return_signals([row(0,.2,.7,truncated=True)],gamma=1.,gae_lambda=.95,horizon=32)
    assert result["full_return"]==.7
    assert result["finite_critic_advantage"]==pytest.approx(.5)
    assert result["bootstrap_kind"]=="public_critic_time_limit"
    with pytest.raises(ValueError,match="crossed"):
        return_signals([row(1,.1,0,terminated=True),row(1,0,0,terminated=True)],
                       gamma=1.,gae_lambda=.95,horizon=128)
    with pytest.raises(ValueError,match="unfinished"):
        return_signals([row(0,.2,.3)],gamma=1.,gae_lambda=.95,horizon=128)


def test_local_sampler_preserves_global_RNG_weights_and_public_information():
    policy=ProbePolicy()
    encoder=SimpleNamespace(encode=lambda public:np.array([1.],np.float32))
    public={"action_mask":[int(i in (6,7)) for i in range(35)]}
    before=deepcopy(policy.state_dict());global_rng=torch.get_rng_state().clone()
    first=HistoricalSampler(encoder,policy,811)
    second=HistoricalSampler(encoder,policy,811)
    hidden_changed={**public,"unused_private_truth":{"opponent_set":"not an encoder input"}}
    assert [first.decision(public)[0] for _ in range(20)]==[second.decision(hidden_changed)[0] for _ in range(20)]
    assert torch.equal(global_rng,torch.get_rng_state())
    assert all(torch.equal(v,before[k]) for k,v in policy.state_dict().items())
    assert all(p.grad is None for p in policy.parameters())


class Native:
    """No real native start: wait aggregation and perspective contract fixture."""
    def restart(self, checkpoint, future_seed): self.n=0
    def observation(self, side, **_):
        allowed=(26,) if self.n==1 and side=="self" else (6,7)
        return {"side":side,"action_mask":[int(i in allowed) for i in range(35)],
                "choices":[str(i) if i in allowed else None for i in range(35)],
                "episode_id":"x","revision":self.n,"public_history":[]}
    def step(self, actions, revision):
        assert revision==self.n
        if self.n==1:assert actions["self"]==26
        self.n+=1
        return dict(action_rejected=False,rewards={"self":int(self.n==2)},
                    terminated=self.n==2,truncated=False,winner="self" if self.n==2 else None)
    def save(self):return {"digest":str(self.n)}


def test_branch_keeps_opponent_view_and_Gym_automatic_wait_without_actor_draw():
    native=Native();native.n=0;public=native.observation("self")
    calls=[]
    actor=SimpleNamespace(decision=lambda p:(calls.append(p["side"]) or (6,{"value":.2})))
    opponent_calls=[]
    opponent=SimpleNamespace(act=lambda p:(opponent_calls.append(p["side"]) or 7))
    result=policy_matched_branch(native,{},public,actor=actor,opponent=opponent,
        forced_action=7,future_seed=[1,2,3,4],horizon=128)
    assert calls==["self"] and opponent_calls==["opponent","opponent"]
    assert result["first_policy_action"]==6 and result["first_executed_action"]==7
    assert result["gym_decisions"]==1 and result["native_decisions"]==2
    assert result["full_return"]==result["finite_lambda_return"]==1


def test_paired_summary_clusters_repeats_and_keeps_degenerate_CI_unreported():
    pairs=[]
    for root,gae,d in (("a",1.,1.),("b",-1.,-1.),("c",0.,0.)):
        for rep in range(2):
            pairs.append({"root":root,"GAE":gae,"critic_value":0.,
                "forced":{"full_return":d,"finite_lambda_return":d,"first_executed_action":6},
                "baseline":{"full_return":0.,"finite_lambda_return":0.,"first_executed_action":7}})
    result=paired_summary(pairs,root_order=["a","b","c"],resamples=1000)
    assert result["paired_samples"]==6 and result["root_clusters"]==3
    assert result["GAE_advantage_correlation"]==pytest.approx(1.)
    assert result["correlation_95CI"] is None
    assert result["undefined_correlation_bootstrap_draws"]>0


def test_plan_and_training_guards_fail_closed():
    from scripts.diagnose_foundation_policy_matched_signals import validate_plan,training_forbidden
    with pytest.raises(ValueError,match="bounded_policy_matched"):
        validate_plan({"PPO":1})
    with pytest.raises(RuntimeError,match="no_PPO"):
        training_forbidden()
