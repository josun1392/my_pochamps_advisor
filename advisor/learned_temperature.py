"""Opt-in masked sampling temperature; the maintained PPO owns every update.

No network/feature/reward changes. A rollout's distribution is frozen at one
temperature for sampling, stored old logp, ratios, entropy and legal-uniform KL.
Inference outside collection/update always uses the historical temperature one.
"""
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import numpy as np
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatPolicy
from advisor.learned_execution_alignment import durable_json, digest

VERSION = "showdown-foundation-masked-temperature-schedule-v1"


def temperature_contract(treatment=False):
    if type(treatment) is not bool:
        raise ValueError("temperature_treatment_boolean_required")
    return {"schema_version": VERSION, "treatment": treatment,
        "segments": ([[0, 49152, 1.5], [49152, 65536, 1.0]] if treatment else [[0, 65536, 1.0]]),
        "progress": "completed_trained_rollout_transitions_since_Foundation_parent",
        "rollout_size": 512, "budget": 65536, "inference_temperature": 1.0,
        "distribution": "native_masked_softmax_raw_actor_logits_div_temperature",
        "update": "same_rollout_temperature_for_oldlogp_ratio_entropy_and_uniform_KL",
        "network_reward_value_auxiliary_Adam": "unchanged", "parent_KL": False}


def validate_temperature(value):
    if not isinstance(value, dict) or value != temperature_contract(value.get("treatment")):
        raise ValueError("invalid_temperature_contract")
    return value


def at_progress(contract, trained):
    validate_temperature(contract)
    if type(trained) is not int or trained < 0 or trained > 65536 or trained % 512:
        raise ValueError("invalid_temperature_trained_progress")
    if trained == 65536:
        return 1.0
    return next(t for start, end, t in contract["segments"] if start <= trained < end)


@contextmanager
def distribution_temperature(policy, temperature, observer=None):
    if (type(policy) is not FoundationCombatPolicy or not isinstance(policy.action_net, torch.nn.Identity)
            or type(temperature) not in (float, int) or temperature not in (1., 1.5)):
        raise ValueError("unsupported_temperature_policy_or_scale")
    name = "_get_action_dist_from_latent"
    if name in policy.__dict__:
        raise ValueError("nested_temperature_distribution_override")
    original = getattr(policy, name)

    def distribution(latent):
        if latent.ndim != 2 or latent.shape[1] != 35 or not torch.isfinite(latent).all():
            raise ValueError("invalid_temperature_actor_logits")
        if observer is not None:
            observer(latent.detach())
        # No extra arithmetic at T=1: old checkpoint/update behavior is exact.
        return original(latent if temperature == 1 else latent / temperature)

    setattr(policy, name, distribution)
    try:
        yield
    finally:
        delattr(policy, name)


class TemperatureFoundationPPO(FoundationCombatPPO):
    def __init__(self, *args, masked_temperature=None, **kwargs):
        self.masked_temperature = validate_temperature(masked_temperature) if masked_temperature is not None else None
        self.temperature_trained = 0
        self._temperature_pending = None
        self._temperature_audit_directory = None
        super().__init__(*args, **kwargs)

    def _excluded_save_params(self):
        return super()._excluded_save_params() + ["_temperature_pending", "_temperature_audit_directory"]

    @classmethod
    def load(cls, *args, **kwargs):
        model = super().load(*args, **kwargs)
        validate_temperature(model.masked_temperature)
        at_progress(model.masked_temperature, model.temperature_trained)
        return model

    def temperature_state(self):
        return {"trained_transitions": self.temperature_trained,
                "next_rollout_temperature": at_progress(self.masked_temperature, self.temperature_trained),
                "inference_temperature": 1.0, "pending_untrained_rollout": self._temperature_pending is not None}

    def set_temperature_audit_directory(self, directory):
        self._temperature_audit_directory = str(directory)
        Path(directory).mkdir(parents=True, exist_ok=True)

    def collect_rollouts(self, *args, **kwargs):
        if self.n_steps * self.n_envs != 512:
            raise ValueError("temperature_requires_fixed_512_rollout")
        if self._temperature_pending is not None:
            raise ValueError("temperature_untrained_rollout_not_consumed")
        progress = self.temperature_trained
        if progress >= self.masked_temperature["budget"]:
            raise ValueError("temperature_transition_budget_exhausted")
        temperature = at_progress(self.masked_temperature, progress)
        records, raw = [], []
        buffer = self.rollout_buffer
        original_add = buffer.add

        def observe_logits(z):
            raw[:] = [z.cpu().numpy().copy()]

        def add(obs, actions, rewards, starts, values, logp, *extra, **options):
            mask = np.asarray(options["action_masks"], bool)
            dist = self.policy.action_dist.distribution
            p = dist.probs.detach().cpu().numpy().copy()
            lp = logp.detach().cpu().numpy().copy()
            acts = np.asarray(actions).reshape(-1).astype(int)
            if (p.shape != mask.shape or not mask.any(1).all() or np.any(p[~mask] != 0)
                    or not np.isfinite(p).all() or not np.allclose(p.sum(1), 1, atol=2e-6)
                    or not mask[np.arange(len(acts)), acts].all() or not raw):
                raise ValueError("temperature_native_mask_or_distribution_mismatch")
            masked_logp = dist.logits.detach().cpu().numpy()
            if np.max(abs(masked_logp[np.arange(len(acts)), acts]-lp)) > 2e-6:
                raise ValueError("temperature_sampled_action_oldlogp_mismatch")
            # Independent formula from the actual raw scores and native mask.
            z = raw[0].astype(np.float64)/temperature
            z[~mask] = -np.inf
            z -= z.max(1, keepdims=True)
            expected = np.exp(z); expected /= expected.sum(1, keepdims=True)
            if np.max(abs(expected-p)) > 2e-6:
                raise ValueError("temperature_behavior_formula_mismatch")
            records.append((raw[0].copy(), p, lp, acts, mask, dist.entropy().detach().cpu().numpy().copy()))
            return original_add(obs, actions, rewards, starts, values, logp, *extra, **options)

        buffer.add = add
        try:
            with distribution_temperature(self.policy, temperature, observe_logits):
                collected = super().collect_rollouts(*args, **kwargs)
        finally:
            del buffer.add
        if not collected:
            return False  # STOP: no trained progress; pending partial buffer is discarded.
        if len(records) != self.n_steps:
            raise ValueError("temperature_rollout_record_count")
        fields = {key: np.stack([row[i] for row in records]) for i, key in enumerate(
            ("raw_logits", "probabilities", "old_logp", "actions", "native_masks", "entropy"))}
        if (not np.array_equal(fields["old_logp"], buffer.log_probs)
                or not np.array_equal(fields["actions"], buffer.actions[..., 0])
                or not np.array_equal(fields["native_masks"], buffer.action_masks.astype(bool))):
            raise ValueError("temperature_stored_rollout_distribution_mismatch")
        identity = f"rollout_{progress:06d}_{uuid4().hex}"
        saved = None
        if self._temperature_audit_directory:
            directory = Path(self._temperature_audit_directory)
            saved = directory/(identity+".npz")
            # Exclusive write: never overwrite a recovered rollout receipt.
            with saved.open("xb") as f:
                np.savez_compressed(f, **fields, temperature=np.asarray(temperature),
                    trained_start=np.asarray(progress), values=buffer.values, rewards=buffer.rewards,
                    returns=buffer.returns, advantages=buffer.advantages, episode_starts=buffer.episode_starts)
        self._temperature_pending = {"temperature": temperature, "trained_start": progress,
            "identity": identity, "capture": str(saved) if saved else None,
            "capture_SHA256": digest(saved) if saved else None,
            "entropy_mean": float(fields["entropy"].mean()), "max_probability_mean": float(fields["probabilities"].max(-1).mean()),
            "nontrivial_count": int((fields["native_masks"].sum(-1)>1).sum())}
        return True

    def train(self):
        pending = self._temperature_pending
        if (pending is None or pending["trained_start"] != self.temperature_trained
                or self.temperature_trained >= self.masked_temperature['budget']):
            raise ValueError("temperature_update_requires_bound_rollout")
        temperature = pending["temperature"]
        if temperature != at_progress(self.masked_temperature, self.temperature_trained):
            raise ValueError("temperature_update_schedule_mismatch")
        maximum_logp_error, maximum_value_error = 0., 0.
        # Check the actual whole collected rollout BEFORE the first optimizer
        # step. Float32 GEMM uses batch4 in collection and batch128 here.
        observations = self.rollout_buffer.observations.reshape(-1, self.observation_space.shape[0])
        masks = self.rollout_buffer.action_masks.reshape(-1, 35)
        actions = self.rollout_buffer.actions.reshape(-1).astype(int)
        old_logp = self.rollout_buffer.log_probs.reshape(-1)
        old_values = self.rollout_buffer.values.reshape(-1)
        if not np.isfinite(old_logp).all() or not np.isfinite(old_values).all():
            raise ValueError("temperature_nonfinite_stored_logp_value")
        with torch.no_grad(), distribution_temperature(self.policy, temperature):
            for start in range(0, len(actions), 128):
                _, values, _ = self.policy(torch.as_tensor(observations[start:start+128], device=self.device),
                    action_masks=masks[start:start+128], deterministic=True)
                distribution = self.policy.action_dist.distribution
                logp = distribution.log_prob(torch.as_tensor(actions[start:start+128], device=self.device))
                if not torch.isfinite(logp).all() or not torch.isfinite(values).all():
                    raise ValueError("temperature_nonfinite_preupdate_logp_value")
                maximum_logp_error = max(maximum_logp_error, float(np.max(abs(logp.cpu().numpy()-old_logp[start:start+128]))))
                maximum_value_error = max(maximum_value_error, float(np.max(abs(values.flatten().cpu().numpy()-old_values[start:start+128]))))
        if maximum_logp_error > 2e-5 or maximum_value_error > 2e-5:
            raise ValueError("temperature_preupdate_oldlogp_value_ratio_mismatch")
        original = self.policy.evaluate_actions
        original_get = self.rollout_buffer.get
        had_override = "evaluate_actions" in self.policy.__dict__
        old_override = self.policy.__dict__.get("evaluate_actions")
        uniform_kls, entropies, minibatches = [], [], []
        raw_update, current_batch = [], []

        def observe_update_logits(z):
            raw_update[:] = [z.detach()]

        def get(*args, **kwargs):
            for batch in original_get(*args, **kwargs):
                current_batch[:] = [batch]
                yield batch

        def evaluate(obs, actions, action_masks=None):
            values, logp, entropy = original(obs, actions, action_masks=action_masks)
            dist = self.policy.action_dist.distribution
            from advisor.learned_regularized_ppo import legal_uniform_kl
            if entropy is None or action_masks is None or not torch.isfinite(logp).all():
                raise ValueError("temperature_update_distribution_invalid")
            masks = torch.as_tensor(action_masks, device=dist.probs.device, dtype=torch.bool)
            if (dist.probs[~masks] != 0).any():
                raise ValueError("temperature_update_illegal_probability")
            if not current_batch or not raw_update or not torch.equal(masks, current_batch[0].action_masks.bool()):
                raise ValueError("temperature_update_minibatch_binding_mismatch")
            with torch.no_grad():
                expected = (raw_update[0].double()/temperature).masked_fill(~masks, -torch.inf).log_softmax(1)
                error = float((expected[masks]-dist.logits.detach().double()[masks]).abs().max())
                ratio = (logp.detach()-current_batch[0].old_log_prob).exp()
                if error > 2e-5 or not torch.isfinite(ratio).all():
                    raise ValueError("temperature_update_formula_or_ratio_mismatch")
                minibatches.append({'index':len(minibatches),'temperature':temperature,'legal_logp_formula_max_error':error,
                    'ratio_min':float(ratio.min()),'ratio_max':float(ratio.max()),'ratio_mean':float(ratio.mean()),
                    'first_minibatch_unit_ratio_max_error':float((ratio-1).abs().max()) if not minibatches else None})
            entropies.append(float(entropy.detach().mean()))
            uniform_kls.append(float(legal_uniform_kl(dist.logits, action_masks).detach().mean()))
            return values, logp, entropy

        self.policy.evaluate_actions = evaluate
        self.rollout_buffer.get = get
        try:
            with distribution_temperature(self.policy, temperature, observe_update_logits):
                super().train()
        finally:
            del self.rollout_buffer.get
            if had_override:
                self.policy.evaluate_actions = old_override
            else:
                del self.policy.evaluate_actions
        self.temperature_trained += self.n_steps*self.n_envs
        self._temperature_pending = None
        self.logger.record("train/masked_temperature", temperature)
        self.logger.record("train/temperature_trained_transitions", self.temperature_trained)
        self.logger.record("train/temperature_actual_entropy", float(np.mean(entropies)))
        self.logger.record("train/temperature_actual_uniform_kl", float(np.mean(uniform_kls)))
        self.logger.record("train/temperature_preupdate_logp_error", maximum_logp_error)
        self.logger.record("train/temperature_preupdate_value_error", maximum_value_error)
        if self._temperature_audit_directory:
            durable_json(Path(self._temperature_audit_directory)/(pending["identity"]+".trained.json"), {
                **pending, "trained_end": self.temperature_trained,
                "actual_update_temperature": temperature, "update_entropy": float(np.mean(entropies)),
                "preupdate_max_logp_error": maximum_logp_error, "preupdate_max_value_error": maximum_value_error,
                "minibatches": minibatches,
                "update_uniform_KL": float(np.mean(uniform_kls)),
                "Adam_clock": max((int(v["step"]) for v in self.policy.optimizer.state.values() if "step" in v),default=0),
                "score_gradient_multiplier_at_same_logits": 1./temperature,
                "gradient_scope": "also changes probabilities_and_visitation_not_equivalent_entropy_coefficient"})


def model_temperature_contract(model):
    contract = getattr(model, "masked_temperature", None)
    if contract is None:
        return None
    if not isinstance(model, TemperatureFoundationPPO):
        raise ValueError("temperature_checkpoint_loaded_as_base_algorithm")
    return validate_temperature(contract)


def validate_loaded_temperature(model, metadata):
    if model_temperature_contract(model) != metadata.get("masked_temperature"):
        raise ValueError("temperature_checkpoint_contract_mismatch")
    if model_temperature_contract(model) is not None:
        if model.temperature_state() != metadata.get("temperature_state"):
            raise ValueError("temperature_checkpoint_progress_mismatch")
