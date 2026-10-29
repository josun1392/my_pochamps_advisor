"""Opt-in legal-uniform reverse KL added to maintained MaskablePPO updates.

The upstream entropy-loss seam supplies + beta * KL(U_legal || pi) without
copying PPO/GAE/optimizer code. No additional forward pass or policy inputs.
The composite entropy diagnostic is explicitly distinguished from true entropy.
"""
import importlib.metadata
import math

import numpy as np
import torch
from sb3_contrib import MaskablePPO

VERSION = "showdown-legal-uniform-kl-ppo-v1"


def regularizer_contract(beta):
    if type(beta) not in (int, float) or not math.isfinite(beta) or not 0 <= beta <= .01:
        raise ValueError("invalid_legal_uniform_kl_beta")
    return {"schema_version": VERSION, "beta": float(beta),
            "loss": "beta_KL_uniform_legal_to_masked_policy",
            "scope": "own_public_rollout_native_legal_mask_only",
            "upstream": "sb3-contrib-MaskablePPO-2.7.1",
            "single_legal_action": "zero"}


def legal_uniform_kl(log_probabilities, masks):
    masks = torch.as_tensor(masks, dtype=torch.bool, device=log_probabilities.device)
    if masks.shape != log_probabilities.shape or not masks.any(-1).all():
        raise ValueError("invalid_regularizer_action_mask")
    count = masks.sum(-1).to(log_probabilities.dtype)
    # torch Categorical.logits are normalized log probabilities, not raw scores.
    selected = torch.where(masks, log_probabilities, 0)
    result = -count.log() - selected.sum(-1) / count
    result = torch.where(count == 1, torch.zeros_like(result), result)
    if not torch.isfinite(result).all():
        raise ValueError("nonfinite_legal_uniform_kl")
    return result


class RegularizedMaskablePPO(MaskablePPO):
    def __init__(self, *args, zero_avoiding_beta=0., **kwargs):
        self.zero_avoiding_beta = regularizer_contract(zero_avoiding_beta)["beta"]
        super().__init__(*args, **kwargs)

    def train(self):
        beta = regularizer_contract(self.zero_avoiding_beta)["beta"]
        if beta == 0:
            return super().train()  # Exactly the original loss/update path.
        if importlib.metadata.version("sb3-contrib") != "2.7.1" or not self.ent_coef > 0:
            raise ValueError("unsupported_regularized_ppo_entropy_seam")
        original = self.policy.evaluate_actions
        had_override = "evaluate_actions" in self.policy.__dict__
        old_override = self.policy.__dict__.get("evaluate_actions")
        kls, entropies = [], []

        def evaluate_actions(obs, actions, action_masks=None):
            values, log_probability, entropy = original(obs, actions, action_masks=action_masks)
            if entropy is None or action_masks is None:
                raise ValueError("masked_categorical_entropy_required")
            # Upstream evaluate_actions just installed this same masked distribution.
            distribution = self.policy.action_dist.distribution
            kl = legal_uniform_kl(distribution.logits, action_masks)
            kls.append(float(kl.detach().mean()))
            entropies.append(float(entropy.detach().mean()))
            return values, log_probability, entropy - (beta / self.ent_coef) * kl

        self.policy.evaluate_actions = evaluate_actions
        try:
            super().train()
        finally:
            if had_override:
                self.policy.evaluate_actions = old_override
            else:
                del self.policy.evaluate_actions
        self.logger.record("train/zero_avoiding_beta", beta)
        self.logger.record("train/legal_uniform_kl", float(np.mean(kls)))
        self.logger.record("train/regularization_loss", beta * float(np.mean(kls)))
        self.logger.record("train/true_action_entropy", float(np.mean(entropies)))


def model_regularizer_contract(model):
    if isinstance(model, RegularizedMaskablePPO):
        return regularizer_contract(model.zero_avoiding_beta)
    if getattr(model, "zero_avoiding_beta", 0) != 0:
        raise ValueError("regularized_checkpoint_loaded_with_base_algorithm")
    return None


def checkpoint_algorithm(metadata):
    if "gae_lambda_experiment" in metadata:
        from advisor.learned_gae_lambda import GaeOneFoundationPPO, validate_contract
        from advisor.learned_objective import objective_contract
        validate_contract(metadata['gae_lambda_experiment'])
        if ('combat_foundation' not in metadata or metadata.get('gamma') != 1
                or metadata.get('gae_lambda') != 1
                or metadata.get('training_objective') != objective_contract(1., 1.)
                or any(k in metadata for k in ('move_slot_consistency', 'actor_set_context',
                    'parent_policy_anchor', 'masked_temperature'))):
            raise ValueError('GAE_lambda_checkpoint_objective_mismatch')
        ordinary = dict(metadata)
        ordinary.pop('gae_lambda_experiment')
        if checkpoint_algorithm(ordinary).__name__ != 'FoundationCombatPPO':
            raise ValueError('GAE_lambda_requires_original_Foundation')
        return GaeOneFoundationPPO
    if "move_slot_consistency" in metadata:
        from advisor.learned_move_slot_consistency import MoveSlotFoundationPPO, validate_contract
        validate_contract(metadata["move_slot_consistency"])
        if "combat_foundation" not in metadata or any(k in metadata for k in (
                "actor_set_context", "parent_policy_anchor", "masked_temperature")):
            raise ValueError("move_slot_requires_original_foundation_objective")
        # Validate the historical Foundation identity before selecting the opt-in.
        ordinary = dict(metadata)
        ordinary.pop("move_slot_consistency")
        if checkpoint_algorithm(ordinary).__name__ != "FoundationCombatPPO":
            raise ValueError("move_slot_foundation_algorithm_required")
        return MoveSlotFoundationPPO
    if "actor_set_context" in metadata:
        from advisor.learned_legal_set_context import legal_set_context_contract
        if (metadata["actor_set_context"] != legal_set_context_contract()
                or "combat_foundation" not in metadata
                or any(k in metadata for k in ("masked_temperature", "parent_policy_anchor"))):
            raise ValueError("legal_set_context_checkpoint_contract_mismatch")
    if "masked_temperature" in metadata and "combat_foundation" not in metadata:
        raise ValueError("temperature_requires_foundation_checkpoint")
    if "combat_foundation" in metadata:
        from advisor.learned_combat_foundation import FoundationCombatPPO, foundation_contract
        if metadata["combat_foundation"] != foundation_contract() or metadata.get("encoder_version") != foundation_contract()["encoder"]:
            raise ValueError("combat_foundation_checkpoint_contract_mismatch")
        from advisor.learned_combat_v5_strategic_aux import auxiliary_contract
        if metadata.get("integrated_auxiliary") != auxiliary_contract():
            raise ValueError("combat_foundation_auxiliary_contract_mismatch")
        if "masked_temperature" in metadata:
            from advisor.learned_temperature import TemperatureFoundationPPO, validate_temperature
            validate_temperature(metadata["masked_temperature"])
            if "parent_policy_anchor" in metadata:
                raise ValueError("temperature_parent_anchor_combination_not_supported")
            return TemperatureFoundationPPO
        if "parent_policy_anchor" in metadata:
            from advisor.learned_parent_anchor import ParentAnchoredFoundationPPO, validate_anchor_contract
            validate_anchor_contract(metadata["parent_policy_anchor"])
            return ParentAnchoredFoundationPPO
        return FoundationCombatPPO
    if "parent_policy_anchor" in metadata:
        raise ValueError("parent_anchor_requires_foundation_contract")
    if metadata.get("encoder_version") == "showdown-public-categorical-observation-v5-integrated-v3":
        from advisor.learned_combat_v5_strategic_aux import StrategicCombatV5PPO, auxiliary_contract
        if metadata.get("integrated_auxiliary") != auxiliary_contract():
            raise ValueError("strategic_v5_auxiliary_checkpoint_contract_required")
        return StrategicCombatV5PPO
    if metadata.get("encoder_version") in ("showdown-public-categorical-observation-v5-integrated-v1", "showdown-public-categorical-observation-v5-integrated-v2"):
        from advisor.learned_combat_v5_aux import IntegratedCombatV5PPO, auxiliary_contract
        if metadata.get("integrated_auxiliary") != auxiliary_contract():
            raise ValueError("v5_auxiliary_checkpoint_contract_required")
        return IntegratedCombatV5PPO
    contract = metadata.get("training_regularizer")
    if contract is None:
        return MaskablePPO
    if not isinstance(contract, dict) or contract != regularizer_contract(contract.get("beta")):
        raise ValueError("checkpoint_regularizer_contract_mismatch")
    return RegularizedMaskablePPO


def validate_loaded_regularizer(model, metadata):
    if model_regularizer_contract(model) != metadata.get("training_regularizer"):
        raise ValueError("checkpoint_regularizer_persistence_mismatch")
    if hasattr(model, "auxiliary_metadata") and model.auxiliary_metadata() != metadata.get("integrated_auxiliary"):
        raise ValueError("v5_auxiliary_persistence_mismatch")
    from advisor.learned_parent_anchor import validate_loaded_parent_anchor
    validate_loaded_parent_anchor(model, metadata)
    from advisor.learned_temperature import validate_loaded_temperature
    validate_loaded_temperature(model, metadata)
    from advisor.learned_legal_set_context import validate_loaded_legal_set_context
    validate_loaded_legal_set_context(model, metadata)
    from advisor.learned_move_slot_consistency import validate_loaded
    validate_loaded(model, metadata)
    from advisor.learned_gae_lambda import validate_loaded as validate_gae
    validate_gae(model, metadata)
