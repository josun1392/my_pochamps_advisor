"""Versioned combat foundation using public V5-v3 and maintained masked PPO."""

from time import perf_counter
import numpy as np
import torch

from advisor.learned_combat_v5_strategic import VERSION as ENCODER_VERSION
from advisor.learned_combat_v5_strategic import StrategicCombatV5Encoder, prediction_public_rows, priors
from advisor.learned_combat_v5 import tactical_features
from advisor.learned_history_sequence import history_sequence
from advisor.learned_own_hp import own_hp_features
from advisor.learned_combat_v5_references import reference_features
from advisor.learned_combat_v5_strategic_aux import StrategicCombatV5PPO
from advisor.learned_combat_v5_strategic_policy import (
    StrategicCombatV5Policy,
    transfer_strategic_combat_v5_weights,
)

VERSION = "showdown-combat-foundation-v1"


def foundation_contract():
    return {
        "schema_version": VERSION,
        "encoder": ENCODER_VERSION,
        "policy": "FoundationCombatPolicy",
        "architecture": "V5_v3_shared_public_rows_actor_critic_single_forward",
        "encoder_implementation": "bit_identical_V5_v3_without_discarded_parent_prediction_transport",
        "learning": "maintained_MaskablePPO_2.7.1_GAE_with_V5_v3_auxiliary",
        "gradient_guard": "finite_before_clip_and_optimizer_step_max_norm_0.5",
        "resume": "same_contract_model_Adam_fresh_rollout_native_episodes",
        "predictions": "uncalibrated_bounded_residual_priors_no_exact_action_labels",
    }


class FoundationCombatPolicy(StrategicCombatV5Policy):
    """Explicit foundation identity, preserving the proven V5-v3 tensor contract."""


class FoundationCombatEncoder(StrategicCombatV5Encoder):
    def encode(self, view):
        if any(key in view for key in ("native_state", "teams", "scenario", "checkpoint", "seed", "future_seed",
                                      "input_log", "opponent_request", "coordinator_v5_supervision", "auxiliary_labels")):
            raise ValueError("privileged_input_in_v5_public_observation")
        old = self.base.encode(view)
        history, _ = history_sequence(view, self.base)
        transport, probabilities = prediction_public_rows(view, self.base)
        references, threat = reference_features(view, self.base, priors()[0]['native_moves'])
        return np.concatenate((old, own_hp_features(view).flatten(), history,
            tactical_features(view, self.base).flatten(), transport,
            np.concatenate((references, threat), axis=1).flatten(), probabilities)).astype(np.float32)


def transfer_foundation_weights(target, source, target_encoder, source_encoder):
    if type(target) is not FoundationCombatPolicy or target_encoder.version != ENCODER_VERSION:
        raise ValueError("foundation_transfer_target_contract")
    if type(source) is StrategicCombatV5Policy and source_encoder.catalog_fingerprint == target_encoder.catalog_fingerprint:
        target.load_state_dict(source.state_dict(), strict=True)
    else:
        bridge = StrategicCombatV5Policy(target.observation_space, target.action_space, lambda _: 5e-5)
        transfer_strategic_combat_v5_weights(bridge, source, target_encoder, source_encoder)
        target.load_state_dict(bridge.state_dict(), strict=True)
    target.optimizer = target.optimizer_class(
        target.parameters(), lr=target.optimizer.param_groups[0]["lr"], **target.optimizer_kwargs)


class FoundationCombatPPO(StrategicCombatV5PPO):
    def _excluded_save_params(self):
        return super()._excluded_save_params() + ["foundation_timings", "foundation_profile_rows"]

    def record_foundation_profile(self, row):
        if not hasattr(self, "foundation_profile_rows"):
            self.foundation_profile_rows = []
        self.foundation_profile_rows.append(row)

    def _supervised_loss(self, observations, labels):
        started = perf_counter()
        try:
            return super()._supervised_loss(observations, labels)
        finally:
            self.foundation_timings["auxiliary_forward_seconds"] += perf_counter() - started

    def collect_rollouts(self, *args, **kwargs):
        started = perf_counter()
        original = self.policy.forward
        inference_seconds = 0.

        def measured_forward(*inputs, **options):
            nonlocal inference_seconds
            begin = perf_counter()
            try:
                return original(*inputs, **options)
            finally:
                inference_seconds += perf_counter() - begin

        self.policy.forward = measured_forward
        try:
            return super().collect_rollouts(*args, **kwargs)
        finally:
            del self.policy.forward
            self.logger.record("foundation/rollout_seconds", perf_counter() - started)
            self.logger.record("foundation/rollout_actor_value_seconds", inference_seconds)
            self.record_foundation_profile({"phase": "rollout", "seconds": perf_counter() - started,
                                           "actor_value_seconds": inference_seconds})

    def train(self):
        if self.max_grad_norm != .5 or self.gamma != 1:
            raise ValueError("foundation_ppo_contract_mismatch")
        from advisor.learned_gae_lambda import validate_foundation_gae
        validate_foundation_gae(self)  # Default remains .95; typed opt-in only.
        from advisor.learned_potential_ppo import validate_model as validate_potential
        validate_potential(self)  # Reject a shaped ZIP silently loaded as base PPO.
        started = perf_counter()
        self.foundation_timings = {"auxiliary_forward_seconds": 0.}
        raw_norms, clipped_norms, hooks = [], [], []
        squared_norms = {}

        def capture(name):
            def hook(gradient):
                if not torch.isfinite(gradient).all():
                    raise ValueError("foundation_nonfinite_gradient:" + name)
                squared_norms[name] = float(gradient.detach().square().sum())
                return gradient
            return hook

        def before_step(optimizer, args, kwargs):
            raw_norm = sum(squared_norms.values()) ** .5
            if not np.isfinite(raw_norm):
                raise ValueError("foundation_nonfinite_gradient_norm")
            raw_norms.append(raw_norm)
            squared_norms.clear()
            squared = sum(float(parameter.grad.detach().square().sum())
                          for parameter in self.policy.parameters() if parameter.grad is not None)
            norm = squared ** .5
            if not np.isfinite(norm) or norm > self.max_grad_norm + 1e-5:
                raise ValueError("foundation_invalid_clipped_gradient")
            clipped_norms.append(norm)

        for name, parameter in self.policy.named_parameters():
            if parameter.requires_grad:
                hooks.append(parameter.register_hook(capture(name)))
        hooks.append(self.policy.optimizer.register_step_pre_hook(before_step))
        try:
            super().train()
            for parameter in self.policy.parameters():
                if not torch.isfinite(parameter).all():
                    raise ValueError("foundation_nonfinite_updated_parameter")
            for state in self.policy.optimizer.state.values():
                for value in state.values():
                    if isinstance(value, torch.Tensor) and not torch.isfinite(value).all():
                        raise ValueError("foundation_nonfinite_Adam_state")
        finally:
            for hook in hooks:
                hook.remove()
        self.logger.record("foundation/update_seconds", perf_counter() - started)
        for name, value in self.foundation_timings.items():
            self.logger.record("foundation/" + name, value)
        self.logger.record("foundation/optimizer_steps", len(raw_norms))
        self.logger.record("foundation/gradient_norm_max", max(raw_norms, default=0.))
        self.logger.record("foundation/clipped_gradient_norm_max", max(clipped_norms, default=0.))
        self.logger.record("foundation/gradient_clip_fraction", float(np.mean(np.asarray(raw_norms) > .5)) if raw_norms else 0.)
        self.record_foundation_profile({"phase": "update", "seconds": perf_counter() - started,
            **self.foundation_timings, "optimizer_steps": len(raw_norms), "gradient_norm_max": max(raw_norms, default=0.),
            "clipped_gradient_norm_max": max(clipped_norms, default=0.)})


def install_environment_profile(env):
    timings = {}

    def measure(owner, method, name):
        original = getattr(owner, method)

        def measured(*args, **kwargs):
            started = perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                timings[name] = timings.get(name, 0.) + perf_counter() - started
                timings[name + "_calls"] = timings.get(name + "_calls", 0) + 1
        setattr(owner, method, measured)

    measure(env, "_encode_public", "public_encoding_seconds")
    measure(env, "_native_step", "native_step_with_opponent_seconds")
    measure(env.native, "_request", "native_bridge_wait_seconds")
    measure(env.native, "observation", "public_observation_copy_seconds")

    def drain():
        result = dict(timings)
        timings.clear()
        return result

    env.drain_foundation_profile = drain
    return env
