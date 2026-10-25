"""Opt-in observation-only audit around the maintained PPO, no new objective."""
from pathlib import Path
import numpy as np
import torch

from advisor.learned_signal_recorder import PublicSignalRecorder
from advisor.learned_execution_alignment import durable_json, digest
from advisor.learned_parent_anchor import optimizer_clock

VERSION = "foundation-T1-rollout-update-audit-v1"


class AuditedSignalRecorder(PublicSignalRecorder):
    def __init__(self, directory, encoder):
        super().__init__(directory, encoder)
        self.active = None

    def end(self, model, clock):
        super().end(model, clock)
        if self.active is not None:
            raise ValueError("unsettled_PPO_audit")
        buffer = model.rollout_buffer
        x = buffer.observations.reshape(-1, model.observation_space.shape[0])
        masks = buffer.action_masks.reshape(-1, 35).astype(bool)
        actions = buffer.actions.reshape(-1).astype(int)
        if not masks[np.arange(len(actions)), actions].all():
            raise ValueError("PPO_audit_illegal_action")
        raw, probabilities, lp, values = [], [], [], []
        hook = model.policy.action_net.register_forward_pre_hook(lambda m, a: raw.append(a[0].detach().cpu().numpy().copy()))
        try:
            with torch.no_grad():
                for start in range(0, len(x), 128):
                    _, value, _ = model.policy(torch.as_tensor(x[start:start+128], device=model.device),
                        action_masks=masks[start:start+128], deterministic=True)
                    distribution = model.policy.action_dist.distribution
                    probabilities.append(distribution.probs.cpu().numpy().copy())
                    lp.append(distribution.log_prob(torch.as_tensor(actions[start:start+128], device=model.device)).cpu().numpy())
                    values.append(value.flatten().cpu().numpy())
                last = model.policy.predict_values(torch.as_tensor(model._last_obs, device=model.device)).flatten().cpu().numpy()
        finally:
            hook.remove()
        raw, probabilities = np.concatenate(raw), np.concatenate(probabilities)
        lp, values = np.concatenate(lp), np.concatenate(values)
        logp_error = float(abs(lp-buffer.log_probs.reshape(-1)).max())
        value_error = float(abs(values-buffer.values.reshape(-1)).max())
        expected = np.where(masks, raw.astype(float), -np.inf)
        expected = np.exp(expected-expected.max(1, keepdims=True));expected /= expected.sum(1, keepdims=True)
        formula_error = float(abs(expected-probabilities).max())
        advantage = np.zeros_like(buffer.advantages);gae = np.zeros(model.n_envs, dtype=np.float32)
        for t in reversed(range(model.n_steps)):
            next_value = last if t == model.n_steps-1 else buffer.values[t+1]
            next_nonterminal = 1.-(model._last_episode_starts if t == model.n_steps-1 else buffer.episode_starts[t+1])
            delta = buffer.rewards[t]+model.gamma*next_value*next_nonterminal-buffer.values[t]
            gae = delta+model.gamma*model.gae_lambda*next_nonterminal*gae
            advantage[t] = gae
        gae_error = float(abs(advantage-buffer.advantages).max())
        return_error = float(abs(advantage+buffer.values-buffer.returns).max())
        if (not all(np.isfinite(v).all() for v in (raw, probabilities, lp, values, advantage))
                or logp_error > 2e-5 or value_error > 2e-5 or formula_error > 2e-6
                or gae_error > 2e-6 or return_error > 2e-6 or probabilities[~masks].any()):
            raise ValueError("PPO_audit_T1_logp_value_GAE_or_mask_mismatch")
        name = self.pending[0]
        path = self.directory/(name+".audit.npz")
        with path.open("xb") as stream:
            np.savez_compressed(stream, raw_logits=raw, probabilities=probabilities, native_masks=masks,
                actions=actions, old_logp=buffer.log_probs, values=buffer.values, rewards=buffer.rewards,
                returns=buffer.returns, advantages=buffer.advantages, episode_starts=buffer.episode_starts,
                last_values=last, last_dones=model._last_episode_starts)
        policy = model.policy
        residual = {n:p.detach().clone() for n,p in policy.named_parameters() if 'legal_set_residual' in n}
        audit = {"schema_version":VERSION,"model_timesteps_end":model.num_timesteps,"transitions":len(actions),
            "Adam_before":clock,"capture":str(path),"capture_SHA256":digest(path),"temperature":1,
            "preupdate_logp_error":logp_error,"preupdate_value_error":value_error,"T1_formula_error":formula_error,
            "GAE_error":gae_error,"return_error":return_error,"minibatches":[],"residual_clipped_gradient_max":0.}
        original_get, original_evaluate = buffer.get, policy.evaluate_actions
        if 'get' in buffer.__dict__ or 'evaluate_actions' in policy.__dict__:
            raise ValueError("PPO_audit_nested_override")
        current = []

        def get(*args, **kwargs):
            for batch in original_get(*args, **kwargs):
                current[:] = [batch]
                yield batch

        def evaluate(obs, selected, action_masks=None):
            result = original_evaluate(obs, selected, action_masks=action_masks)
            with torch.no_grad():
                if not current or not torch.equal(current[0].action_masks, torch.as_tensor(action_masks, device=model.device)):
                    raise ValueError("PPO_audit_minibatch_binding")
                ratio = (result[1]-current[0].old_log_prob).exp()
                if not torch.isfinite(ratio).all():
                    raise ValueError("PPO_audit_nonfinite_ratio")
                audit['minibatches'].append({"index":len(audit['minibatches']),"ratio_min":float(ratio.min()),
                    "ratio_max":float(ratio.max()),"ratio_mean":float(ratio.mean()),
                    "old_logp":current[0].old_log_prob.detach().cpu().tolist(),
                    "new_logp":result[1].detach().cpu().tolist(),"actions":selected.detach().cpu().tolist(),
                    "entropy":float(result[2].mean()),"approx_KL":float(((ratio-1)-(result[1]-current[0].old_log_prob)).mean()),
                    "clip_fraction":float(((ratio-1).abs()>.2).float().mean()),
                    "unit_ratio_max_error":float((ratio-1).abs().max()) if not audit['minibatches'] else None})
            return result  # Identical tensors/autograd graph, no loss modification.

        def before_step(optimizer, args, kwargs):
            g=sum(float(p.grad.detach().square().sum()) for n,p in policy.named_parameters()
                if n in residual and p.grad is not None)**.5
            audit['residual_clipped_gradient_max']=max(audit['residual_clipped_gradient_max'],g)

        buffer.get, policy.evaluate_actions = get, evaluate
        handle = policy.optimizer.register_step_pre_hook(before_step)
        self.active = (model, audit, residual, handle)

    def settled(self, clock, model=None):
        if self.active is not None:
            active_model, audit, residual, _ = self.active
            if model is not active_model or clock <= audit['Adam_before']:
                raise ValueError("PPO_audit_no_optimizer_progress")
            audit.update(Adam_after=clock, residual_parameter_delta_L2=sum(float((p.detach()-residual[n]).square().sum())
                for n,p in model.policy.named_parameters() if n in residual)**.5,
                residual_Adam_steps={n:int(model.policy.optimizer.state[p]['step'])
                    for n,p in model.policy.named_parameters() if n in residual})
            self.close()
            durable_json(self.directory/(self.pending[0]+'.audit.json'),audit)
        super().settled(clock, model)

    def close(self):
        if self.active is not None:
            model, _, _, handle = self.active
            del model.rollout_buffer.get
            del model.policy.evaluate_actions
            handle.remove()
            self.active = None
