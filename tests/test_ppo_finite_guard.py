"""Safety checks only; no PPO algorithm, reward or input change."""
from types import SimpleNamespace
import numpy as np
import pytest
torch=pytest.importorskip("torch")
pytest.importorskip("sb3_contrib")
from stable_baselines3.common.logger import configure
from scripts.train_showdown_autonomous import require_finite_ppo


def model():
    policy=torch.nn.Linear(2,1)
    policy.optimizer=torch.optim.Adam(policy.parameters(),lr=1e-4)
    policy(torch.ones(1,2)).sum().backward();policy.optimizer.step()
    buffer=SimpleNamespace(**{key:np.array([0.,1.],dtype=np.float32)
                              for key in ("observations","rewards","values","returns","advantages")})
    return SimpleNamespace(policy=policy,logger=configure(folder=None,format_strings=[]),rollout_buffer=buffer)


def test_healthy_state_passes_without_changing_weights_or_optimizer():
    m=model(); before={k:v.clone() for k,v in m.policy.state_dict().items()}
    m.logger.record("train/value_loss",.2)
    require_finite_ppo(m,rollout=True)
    assert all(torch.equal(v,before[k]) for k,v in m.policy.state_dict().items())


@pytest.mark.parametrize("scope",["parameter","optimizer","metric","values","advantages"])
def test_nonfinite_learning_fails_closed(scope):
    m=model()
    if scope=="parameter":
        with torch.no_grad(): next(m.policy.parameters()).flatten()[0]=float('nan')
    elif scope=="optimizer":
        next(iter(m.policy.optimizer.state.values()))['exp_avg'].flatten()[0]=float('inf')
    elif scope=="metric": m.logger.record("train/value_loss",float('inf'))
    else: getattr(m.rollout_buffer,scope)[0]=float('nan')
    with pytest.raises(ValueError,match="nonfinite_ppo"):
        require_finite_ppo(m,rollout=True)


def test_undefined_explained_variance_only_allowed_for_constant_finite_targets():
    m=model();m.logger.record("train/explained_variance",float('nan'))
    with pytest.raises(ValueError,match="nonfinite_ppo_metric"):
        require_finite_ppo(m)
    m.rollout_buffer.returns[:]=0
    require_finite_ppo(m)
    assert m.logger.name_to_value['train/explained_variance_defined']==0
