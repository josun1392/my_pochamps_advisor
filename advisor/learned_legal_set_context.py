"""Opt-in legal-set context using the existing Foundation scorer twice.

No observation changes, extra scorer, critic, or PPO loss. The residual is a
separately identified policy extension; original Foundation tensors stay intact.
"""
from copy import deepcopy

import torch
from torch import nn

from advisor.learned_combat_foundation import FoundationCombatPolicy, FoundationCombatPPO
from advisor.learned_combat_v5_strategic import DIMENSION
from advisor.learned_combat_v5_strategic_policy import StrategicCombatV5Extractor
from advisor.learned_combat_v5 import OLD_DIM
from advisor.learned_strategic_public import CONTEXT
from advisor.learned_public_categories import ACTION

VERSION = "showdown-foundation-legal-action-set-context-v1"


def legal_set_context_contract():
    return {
        "schema_version": VERSION,
        "policy": "LegalSetContextFoundationPolicy",
        "encoder": "unchanged_showdown-public-categorical-observation-v5-integrated-v3",
        "pool": "own_native_legal_mean_existing_joint_scorer_penultimate_64",
        "residual": "zero_initialized_linear64_to64_before_reused_candidate_scorer",
        "additional_parameters": 4160,
        "critic": "unchanged_original_context_and_candidate_rows",
        "mask": "transported_own_native_mask_must_match_explicit_mask",
        "optimizer_transfer": "old_Adam_states_by_parameter_name_new_residual_states_empty",
        "scope": "offline_contract_only_no_automatic_training_opt_in",
    }


def transported_legal_mask(features):
    if (not isinstance(features, torch.Tensor) or features.ndim != 2
            or features.shape[1] != DIMENSION or not torch.isfinite(features).all()):
        raise ValueError("legal_set_context_observation_contract")
    mask = features[:, CONTEXT:OLD_DIM].reshape(-1, 35, ACTION)[:, :, -1]
    if not torch.all((mask == 0) | (mask == 1)) or not mask.bool().any(1).all():
        raise ValueError("legal_set_context_native_mask_required")
    return mask.bool()


class LegalSetContextExtractor(StrategicCombatV5Extractor):
    def __init__(self):
        super().__init__()
        self.legal_set_residual = nn.Linear(64, 64)
        self.zero_residual()

    def zero_residual(self):
        nn.init.zeros_(self.legal_set_residual.weight)
        nn.init.zeros_(self.legal_set_residual.bias)

    def _public_rows(self, features):
        expected = transported_legal_mask(features)
        context, actions, mask = super()._public_rows(features)
        if not torch.equal(mask.squeeze(-1).bool(), expected):
            raise ValueError("legal_set_context_internal_mask_mismatch")
        return context, actions, mask

    def _set_actor(self, context, actions, mask):
        shared = self.context(context)
        joined = torch.cat((shared[:, None, :].expand(-1, 35, -1), actions), dim=-1)
        hidden = joined
        # Reuse the original joint identity/state/candidate nonlinear features.
        for layer in tuple(self.scorer)[:-1]:
            hidden = layer(hidden)
        legal = mask.bool()
        pooled = torch.where(legal, hidden, torch.zeros_like(hidden)).sum(1)
        pooled = pooled / mask.sum(1).clamp(min=1)
        shifted = shared + self.legal_set_residual(pooled)
        return self.scorer(torch.cat((shifted[:, None, :].expand(-1, 35, -1), actions), dim=-1)).squeeze(-1)

    def forward(self, features):
        context, actions, mask = self._public_rows(features)
        return self._set_actor(context, actions, mask), self._critic(context, actions, mask)

    def forward_actor(self, features):
        context, actions, mask = self._public_rows(features)
        return self._set_actor(context, actions, mask)


class LegalSetContextFoundationPolicy(FoundationCombatPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = LegalSetContextExtractor()

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        # Upstream orthogonal initialization runs AFTER extractor construction.
        self.mlp_extractor.zero_residual()
        self.legal_set_context = legal_set_context_contract()

    def _checked_mask(self, obs, action_masks):
        native = transported_legal_mask(obs)
        if action_masks is not None:
            explicit = torch.as_tensor(action_masks, device=obs.device)
            if (explicit.numel() != native.numel()
                    or not torch.all((explicit == 0) | (explicit == 1))
                    or not torch.equal(explicit.reshape(native.shape).bool(), native)):
                raise ValueError("legal_set_context_explicit_mask_mismatch")
        # None never means unmasked inference; use the native transport itself.
        return native

    def forward(self, obs, deterministic=False, action_masks=None):
        return super().forward(obs, deterministic=deterministic,
                               action_masks=self._checked_mask(obs, action_masks))

    def get_distribution(self, obs, action_masks=None):
        return super().get_distribution(obs, action_masks=self._checked_mask(obs, action_masks))

    def evaluate_actions(self, obs, actions, action_masks=None):
        return super().evaluate_actions(obs, actions, action_masks=self._checked_mask(obs, action_masks))


def model_legal_set_context_contract(model):
    policy = model.policy
    if type(policy) is LegalSetContextFoundationPolicy:
        if (type(policy.mlp_extractor) is not LegalSetContextExtractor
                or policy.legal_set_context != legal_set_context_contract()):
            raise ValueError("legal_set_context_policy_contract")
        return legal_set_context_contract()
    if hasattr(policy, "legal_set_context") or hasattr(getattr(policy, "mlp_extractor", None), "legal_set_residual"):
        raise ValueError("unversioned_legal_set_context_policy")
    return None


def validate_loaded_legal_set_context(model, metadata):
    actual = model_legal_set_context_contract(model)
    if actual != metadata.get("actor_set_context"):
        raise ValueError("legal_set_context_checkpoint_contract_mismatch")
    if actual is not None and metadata.get("policy_class") != actual["policy"]:
        raise ValueError("legal_set_context_checkpoint_policy_class")


def extend_foundation_legal_set_context(source):
    """Independent CPU copy: preserve old tensors/Adam by NAME, add zero path.

    No optimizer steps or environment interaction. This is a policy extension
    with a fresh rollout boundary, never an uninterrupted native/RNG resume.
    """
    if (type(source) is not FoundationCombatPPO or type(source.policy) is not FoundationCombatPolicy
            or source.observation_space.shape != (DIMENSION,) or source.action_space.n != 35
            or source.device.type != "cpu"):
        raise ValueError("legal_set_context_requires_original_CPU_foundation")
    old = source.policy
    names = dict(old.named_parameters())
    if (type(old.optimizer) is not torch.optim.Adam or len(old.optimizer.param_groups) != 1
            or [id(p) for p in old.optimizer.param_groups[0]["params"]] != [id(p) for p in names.values()]):
        raise ValueError("legal_set_context_unsupported_Adam_parameter_layout")
    with torch.random.fork_rng(devices=[]):
        policy = LegalSetContextFoundationPolicy(source.observation_space, source.action_space,
            source.lr_schedule, **deepcopy(source.policy_kwargs))
    state = policy.state_dict()
    extra = {"mlp_extractor.legal_set_residual.weight", "mlp_extractor.legal_set_residual.bias"}
    if set(state) - set(old.state_dict()) != extra:
        raise ValueError("legal_set_context_transfer_tensor_layout")
    for name, value in old.state_dict().items():
        if state[name].shape != value.shape:
            raise ValueError("legal_set_context_transfer_shape")
        state[name] = value.detach().clone()
    policy.load_state_dict(state, strict=True)
    new_names = dict(policy.named_parameters())
    group = {k: deepcopy(v) for k, v in old.optimizer.param_groups[0].items() if k != "params"}
    # Natural NEW registration order is essential to correct subsequent SB3 load.
    group["params"] = list(new_names.values())
    policy.optimizer = old.optimizer_class([group], **deepcopy(old.optimizer.defaults))
    for name, parameter in names.items():
        if parameter in old.optimizer.state:
            policy.optimizer.state[new_names[name]] = deepcopy(old.optimizer.state[parameter])
    policy.set_training_mode(False)
    target = deepcopy(source)
    target.policy = policy
    target.policy_class = LegalSetContextFoundationPolicy
    target._last_obs = None
    target._last_original_obs = None
    target._last_episode_starts = None
    target.rollout_buffer.reset()
    return target
