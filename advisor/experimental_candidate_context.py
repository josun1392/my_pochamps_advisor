"""Offline-only facade over the existing legal-set residual, never a live policy.

No new scorer or policy architecture is registered. Construction requires an
explicit opt-in and copies the trusted Foundation in memory; nothing is saved.
"""
from copy import deepcopy
from dataclasses import dataclass

import numpy as np
import torch

from advisor.learned_legal_set_context import (
    extend_foundation_legal_set_context, legal_set_context_contract,
)
from advisor.learned_policy import LearnedPolicy
from advisor.learned_response_predictor import public_input

VERSION = "experimental-legal-candidate-context-prototype-v1"


def prototype_contract():
    return {"schema_version": VERSION, "reuses": legal_set_context_contract(),
            "scope": "offline_public_scores_only_no_training_native_save_or_production_route",
            "permutation": "aligned_encoded_candidate_rows_with_fixed_global_context",
            "missing": "existing_encoder_unknown_semantics_or_fail_closed_no_imputation",
            "probe": "fixed_0.05_identity_residual_not_fitted",
            "strength_evidence": False}


@dataclass(frozen=True)
class CandidateScores:
    logits: torch.Tensor
    probabilities: torch.Tensor
    values: torch.Tensor
    legal_mask: torch.Tensor
    context_enabled: bool


def _no_update(*args, **kwargs):
    raise RuntimeError("experimental_context_optimizer_updates_forbidden")


class CandidateContextPrototype:
    """Read-only score inspection; not accepted by LearnedPolicy or a trainer."""
    def __init__(self, source, *, opt_in=False):
        if opt_in is not True:
            raise ValueError("experimental_candidate_context_explicit_opt_in_required")
        if not isinstance(source, LearnedPolicy):
            raise ValueError("experimental_context_trusted_learned_policy_required")
        # The maintained owner validates original CPU Foundation, shapes,
        # parameter/Adam bindings and creates a zero-output-projection copy.
        extended = extend_foundation_legal_set_context(source.model)
        self._policy = extended.policy
        self._base = deepcopy(source.model.policy)
        self._encoder = deepcopy(source.encoder)
        self.source_model_id = source.model_id
        self.contract = prototype_contract()
        for policy in (self._base, self._policy):
            policy.set_training_mode(False)
            policy.optimizer.step = _no_update
        # No PPO instance/environment is retained or exposed by this facade.

    def zero_context(self):
        """Reset only the independent prototype's residual output projection."""
        self._policy.mlp_extractor.zero_residual()

    def use_fixed_diagnostic_context(self):
        """One deterministic capacity probe; never fit or select it by outcomes."""
        residual = self._policy.mlp_extractor.legal_set_residual
        with torch.no_grad():
            residual.weight.copy_(.05 * torch.eye(64, dtype=residual.weight.dtype, device=residual.weight.device))
            residual.bias.zero_()

    def score_public(self, observation, *, use_context=True):
        if not isinstance(observation, dict):
            raise ValueError("experimental_context_public_observation_required")
        public = public_input(observation)  # own request/mask and predictor boundary
        try:
            # Validate the original view too: projecting public fields first
            # would discard roots (e.g. future_seed) that Foundation rejects.
            features = self._encoder.encode(observation)
        except (KeyError, TypeError, IndexError, AttributeError) as error:
            raise ValueError("experimental_context_missing_or_invalid_public_observation") from error
        tensor = torch.as_tensor(np.asarray(features), dtype=torch.float32)[None, :]
        return self._score_encoded(tensor, action_masks=public["action_mask"], use_context=use_context)

    def _score_encoded(self, features, *, action_masks=None, use_context=True):
        """Test seam for aligned public-encoder rows, not an observation authority."""
        if (type(use_context) is not bool or not isinstance(features, torch.Tensor)
                or features.dtype != torch.float32 or features.device.type != "cpu"):
            raise ValueError("experimental_context_score_contract")
        native = self._policy._checked_mask(features, action_masks)
        policy = self._policy if use_context else self._base
        raw = []
        # Observe the maintained policy's raw actor output without duplicating
        # its scorer, probability normalization, value head or masking logic.
        hook = policy.action_net.register_forward_hook(lambda module, args, output: raw.append(output.detach().clone()))
        try:
            with torch.no_grad():
                _, values, _ = policy(features, deterministic=True, action_masks=native)
                probabilities = policy.action_dist.distribution.probs.detach().clone()
        finally:
            hook.remove()
        if len(raw) != 1 or raw[0].shape != native.shape:
            raise ValueError("experimental_context_actor_output_binding")
        return CandidateScores(raw[0], probabilities, values.detach().clone(), native.detach().clone(), use_context)
