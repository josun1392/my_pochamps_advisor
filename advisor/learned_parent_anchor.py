"""Opt-in frozen-parent actor KL; rewards, GAE, features and PPO stay upstream."""
from hashlib import sha256
import math
import numpy as np
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatPolicy
from advisor.learned_combat_v5_strategic import VERSION as ENCODER

VERSION = "showdown-foundation-frozen-parent-kl-v1"


def anchor_contract(parent_sha256, catalog_fingerprint, optimizer_steps, coefficient=.01):
    for value in (parent_sha256, catalog_fingerprint):
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("invalid_parent_anchor_identity")
    if (type(coefficient) not in (int, float) or not math.isfinite(coefficient)
            or not 0 <= coefficient <= .05 or type(optimizer_steps) is not int or optimizer_steps < 0):
        raise ValueError("invalid_parent_anchor_coefficient_or_Adam")
    return {"schema_version": VERSION, "coefficient": float(coefficient),
        "parent_model_sha256": parent_sha256, "catalog_fingerprint": catalog_fingerprint,
        "parent_optimizer_steps": optimizer_steps, "encoder_version": ENCODER,
        "loss": "coefficient_KL_frozen_parent_legal_to_current_legal",
        "scope": "same_current_own_public_encoded_observation_and_native_mask_actor_only",
        "reference": "frozen_eval_no_grad_no_optimizer_steps_not_optimal_action_labels",
        "single_legal_action": "zero", "reward_and_value_targets": "unchanged"}


def validate_anchor_contract(value):
    if not isinstance(value, dict):
        raise ValueError("parent_anchor_contract_required")
    expected = anchor_contract(value.get("parent_model_sha256"), value.get("catalog_fingerprint"),
        value.get("parent_optimizer_steps"), value.get("coefficient"))
    if value != expected:
        raise ValueError("parent_anchor_contract_mismatch")
    return expected


def parent_policy_kl(reference_probabilities, reference_log_probabilities, current_log_probabilities, masks):
    """Stable KL(parent||current), encouraging only native-legal actions."""
    mask = torch.as_tensor(masks, dtype=torch.bool, device=current_log_probabilities.device)
    if (mask.shape != current_log_probabilities.shape or mask.shape != reference_probabilities.shape
            or mask.shape != reference_log_probabilities.shape or not mask.any(-1).all()):
        raise ValueError("invalid_parent_anchor_mask")
    p = reference_probabilities.detach()
    logp = reference_log_probabilities.detach()
    if (not torch.isfinite(p).all() or not torch.isfinite(logp).all()
            or not torch.isfinite(current_log_probabilities).all() or (p < 0).any()
            or (p.masked_select(~mask) != 0).any()
            or not torch.allclose(p.sum(-1), torch.ones_like(p[:, 0]), atol=1e-5)):
        raise ValueError("invalid_parent_anchor_distribution")
    terms = torch.where(mask, p * (logp - current_log_probabilities), 0)
    result = terms.sum(-1)
    result = torch.where(mask.sum(-1) == 1, torch.zeros_like(result), result)
    if not torch.isfinite(result).all():
        raise ValueError("nonfinite_parent_anchor_loss")
    return result


def optimizer_clock(policy):
    return max((int(v["step"]) for v in policy.optimizer.state.values() if "step" in v), default=0)


def tensor_digest(values):
    result = sha256()
    for name, value in sorted(values.items()):
        result.update(name.encode())
        result.update(str((value.dtype, tuple(value.shape))).encode())
        result.update(value.detach().cpu().contiguous().numpy().tobytes())
    return result.hexdigest()


def optimizer_digest(policy):
    from advisor.learned_encoder import fingerprint
    state = policy.optimizer.state_dict()
    tensors = {str(key) + ":" + name: value for key, row in state["state"].items()
               for name, value in row.items() if isinstance(value, torch.Tensor)}
    return fingerprint({"groups": state["param_groups"], "tensors": tensor_digest(tensors)})


class ParentAnchoredFoundationPPO(FoundationCombatPPO):
    """The entropy-loss seam adds actor KL without copying PPO train/GAE."""
    def __init__(self, *args, parent_policy_anchor=None, parent_reference_path=None,
                 parent_catalog_path=None, **kwargs):
        self.parent_policy_anchor = (validate_anchor_contract(parent_policy_anchor)
                                     if parent_policy_anchor is not None else None)
        self.parent_reference_path = str(parent_reference_path) if parent_reference_path is not None else None
        self.parent_catalog_path = str(parent_catalog_path) if parent_catalog_path is not None else None
        self._parent_reference = None
        super().__init__(*args, **kwargs)

    def _excluded_save_params(self):
        return super()._excluded_save_params() + ["_parent_reference", "_parent_reference_signature", "_parent_optimizer_signature"]

    @classmethod
    def load(cls, *args, **kwargs):
        # SB3 applies serialized data/kwargs after __init__, so constructor
        # validation alone does not validate an archive or load-time override.
        model = super().load(*args, **kwargs)
        validate_anchor_contract(model.parent_policy_anchor)
        return model

    def prepare_parent_reference(self):
        contract = validate_anchor_contract(self.parent_policy_anchor)
        if self._parent_reference is not None:
            return self._parent_reference
        if not self.parent_reference_path or not self.parent_catalog_path:
            raise ValueError("parent_anchor_reference_paths_required_for_training")
        from advisor.learned_policy import LearnedPolicy
        source = LearnedPolicy(self.parent_reference_path, self.parent_catalog_path,
                               expected_model_id=contract["parent_model_sha256"])
        if (type(source.model) is not FoundationCombatPPO
                or type(self.policy) is not FoundationCombatPolicy
                or source.encoder.catalog_fingerprint != contract["catalog_fingerprint"]
                or source.encoder.version != contract["encoder_version"]
                or source.model.observation_space.shape != self.observation_space.shape
                or self.action_space.n != source.model.action_space.n or self.action_space.n != 35
                or optimizer_clock(source.model.policy) != contract["parent_optimizer_steps"]):
            raise ValueError("incompatible_parent_anchor_reference")
        teacher = source.model.policy
        teacher.set_training_mode(False)
        teacher.requires_grad_(False)
        if {p.data_ptr() for p in teacher.parameters()} & {p.data_ptr() for p in self.policy.parameters()}:
            raise ValueError("parent_reference_shares_learner_storage")
        self._parent_reference = source
        self._parent_reference_signature = tensor_digest(teacher.state_dict())
        self._parent_optimizer_signature = optimizer_digest(teacher)
        return source

    def parent_reference_proof(self):
        source = self.prepare_parent_reference()
        unchanged = (tensor_digest(source.model.policy.state_dict()) == self._parent_reference_signature
            and optimizer_digest(source.model.policy) == self._parent_optimizer_signature
            and optimizer_clock(source.model.policy) == self.parent_policy_anchor["parent_optimizer_steps"]
            and not any(p.requires_grad or p.grad is not None for p in source.model.policy.parameters()))
        if not unchanged:
            raise ValueError("frozen_parent_reference_changed")
        return {"model_sha256": source.model_id, "parameter_digest": self._parent_reference_signature,
                "optimizer_digest": self._parent_optimizer_signature,
                "optimizer_steps": optimizer_clock(source.model.policy), "frozen_unchanged": True}

    def train(self):
        contract = validate_anchor_contract(self.parent_policy_anchor)
        coefficient = contract["coefficient"]
        if coefficient == 0:
            return super().train()  # exact historical loss/optimizer path
        if not self.ent_coef > 0:
            raise ValueError("parent_anchor_requires_entropy_seam")
        reference = self.prepare_parent_reference().model.policy
        original = self.policy.evaluate_actions
        had = "evaluate_actions" in self.policy.__dict__
        previous = self.policy.__dict__.get("evaluate_actions")
        kls, true_entropies = [], []

        def evaluate(observations, actions, action_masks=None):
            values, logp, entropy = original(observations, actions, action_masks=action_masks)
            if entropy is None or action_masks is None:
                raise ValueError("parent_anchor_requires_native_masked_categorical")
            current = self.policy.action_dist.distribution
            with torch.no_grad():
                teacher = reference.get_distribution(observations, action_masks=action_masks).distribution
            penalty = parent_policy_kl(teacher.probs, teacher.logits, current.logits, action_masks)
            kls.append(float(penalty.detach().mean()))
            true_entropies.append(float(entropy.detach().mean()))
            return values, logp, entropy - (coefficient / self.ent_coef) * penalty

        self.policy.evaluate_actions = evaluate
        try:
            super().train()
        finally:
            if had:
                self.policy.evaluate_actions = previous
            else:
                del self.policy.evaluate_actions
        self.logger.record("train/parent_anchor_coefficient", coefficient)
        self.logger.record("train/parent_anchor_kl", float(np.mean(kls)))
        self.logger.record("train/parent_anchor_weighted_loss", coefficient * float(np.mean(kls)))
        # Nested auxiliary/uniform-KL seams log composite entropy internally.
        self.logger.record("train/true_action_entropy", float(np.mean(true_entropies)))


def model_parent_anchor_contract(model):
    contract = getattr(model, "parent_policy_anchor", None)
    if contract is None:
        return None
    if not isinstance(model, ParentAnchoredFoundationPPO):
        raise ValueError("parent_anchor_loaded_as_base_algorithm")
    return validate_anchor_contract(contract)


def validate_loaded_parent_anchor(model, metadata):
    contract = model_parent_anchor_contract(model)
    if contract != metadata.get("parent_policy_anchor"):
        raise ValueError("parent_anchor_persistence_mismatch")
    if contract is not None and (metadata.get("catalog_fingerprint") != contract["catalog_fingerprint"]
                                or metadata.get("encoder_version") != contract["encoder_version"]):
        raise ValueError("parent_anchor_feature_binding_mismatch")
