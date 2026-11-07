"""Opt-in critic-trainability experiment; historical residual contracts unchanged."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import torch

from advisor.experimental_context_training import (
    EXTRA, ResidualOnlyPolicy, ResidualOnlyExtractor, initialize as residual_initialize,
)
from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatEncoder
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_execution_alignment import digest, durable_json
from advisor.learned_policy import LearnedPolicy
from advisor.learned_ppo_contract_audit import AuditedSignalRecorder

VERSION = 'experimental-set-context-trainable-critic-PPO-v1'


def allowed(name):
    return name in EXTRA or name.startswith('mlp_extractor.critic.') or name.startswith('value_net.')


def frozen_digest(policy):
    return tensor_digest({n: p for n, p in policy.state_dict().items() if not allowed(n)})


def contract():
    return {'version': VERSION, 'actor': 'unchanged_set_context_residual_4160',
            'trainable': ['mlp_extractor.legal_set_residual.*', 'mlp_extractor.critic.*', 'value_net.*'],
            'all_other_parameters': 'frozen', 'optimizer': 'fresh_Adam_parent_defaults',
            'PPO_reward_GAE_auxiliary_uniform_KL': 'unchanged_original_A', 'temperature': 1,
            'transitions': 16384, 'Adam_cap': 512,
            'global_gradient_clipping': 'same_0.5_includes_actor_and_newly_trainable_critic',
            'scope': 'experimental_only_no_production_loader_or_promotion'}


class CriticTrainablePolicy(ResidualOnlyPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        for name, parameter in self.named_parameters():
            parameter.requires_grad_(allowed(name))
        self.optimizer = self.optimizer_class(
            [p for p in self.parameters() if p.requires_grad],
            lr=lr_schedule(1.), **self.optimizer_kwargs)


def validate_model(model, frozen=None):
    p = model.policy
    names = {n for n, v in p.named_parameters() if v.requires_grad}
    expected = {n for n, v in p.named_parameters() if allowed(n)}
    if (type(model) is not FoundationCombatPPO or type(p) is not CriticTrainablePolicy
            or type(p.mlp_extractor) is not ResidualOnlyExtractor or p.context_mode != 'set'
            or p.mlp_extractor.mode != 'set' or names != expected or not EXTRA < names
            or model.critic_trainability_contract != contract()
            or any(v.grad is not None for n, v in p.named_parameters() if not allowed(n))
            or len(p.optimizer.param_groups) != 1
            or {id(v) for v in p.optimizer.param_groups[0]['params']}
                != {id(v) for n, v in p.named_parameters() if allowed(n)}
            or (model.n_steps, model.batch_size, model.n_epochs) != (128, 128, 4)
            or model.gamma != 1 or model.gae_lambda != .95
            or model.ent_coef != .01 or model.vf_coef != .5 or model.max_grad_norm != .5
            or model.target_kl != .03 or model.zero_avoiding_beta != .001
            or p.optimizer.param_groups[0]['lr'] != 5e-5
            or model.device.type != 'cpu' or model.observation_space.shape != (28822,)
            or model.action_space.n != 35 or getattr(model, 'masked_temperature', None)
            or getattr(model, 'parent_policy_anchor', None)):
        raise ValueError('experimental_critic_trainability_contract')
    if frozen is not None and frozen_digest(p) != frozen:
        raise ValueError('experimental_critic_frozen_block_mutated')
    if any(not torch.isfinite(v).all() for v in p.parameters()):
        raise ValueError('experimental_critic_nonfinite_parameter')
    return True


def initialize(source):
    before = tensor_digest(source.policy.state_dict()), optimizer_digest(source.policy)
    model = residual_initialize(source, 'set')
    with torch.random.fork_rng(devices=[]):
        p = CriticTrainablePolicy(source.observation_space, source.action_space,
                                 source.lr_schedule, **deepcopy(model.policy_kwargs))
    p.load_state_dict(model.policy.state_dict(), strict=True)
    p.set_training_mode(False)
    model.policy, model.policy_class = p, CriticTrainablePolicy
    del model.experimental_context_contract
    model.critic_trainability_contract = contract()
    validate_model(model)
    if p.optimizer.state or before != (tensor_digest(source.policy.state_dict()), optimizer_digest(source.policy)):
        raise ValueError('experimental_critic_parent_or_fresh_Adam')
    return model


def save(model, encoder, directory, provenance):
    validate_model(model)
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    path = directory / 'critic_model.zip'; model.save(path)
    durable_json(directory / 'critic_metadata.json', {
        'version': VERSION, 'contract': contract(), 'model_SHA256': digest(path),
        'frozen_SHA256': frozen_digest(model.policy),
        'parameters_SHA256': tensor_digest(model.policy.state_dict()),
        'optimizer_SHA256': optimizer_digest(model.policy), 'Adam_step': optimizer_clock(model.policy),
        'trainable_names': [n for n, v in model.policy.named_parameters() if v.requires_grad],
        'encoder_fingerprint': encoder.catalog_fingerprint, 'provenance': provenance})
    return str(path)


class CriticTrainableActor(LearnedPolicy):
    def __init__(self, path, catalog):
        path = Path(path)
        meta = json.loads((path.parent / 'critic_metadata.json').read_text(encoding='utf-8'))
        if meta['version'] != VERSION or meta['contract'] != contract() or digest(path) != meta['model_SHA256']:
            raise ValueError('experimental_critic_checkpoint_identity')
        self.encoder = FoundationCombatEncoder(catalog)
        if self.encoder.catalog_fingerprint != meta['encoder_fingerprint']:
            raise ValueError('experimental_critic_encoder_identity')
        self.model = FoundationCombatPPO.load(path, device='cpu')
        validate_model(self.model, meta['frozen_SHA256'])
        if (tensor_digest(self.model.policy.state_dict()) != meta['parameters_SHA256']
                or optimizer_digest(self.model.policy) != meta['optimizer_SHA256']
                or optimizer_clock(self.model.policy) != meta['Adam_step']
                or [n for n, v in self.model.policy.named_parameters() if v.requires_grad] != meta['trainable_names']):
            raise ValueError('experimental_critic_optimizer_reload')
        self.model.policy.set_training_mode(False)
        self.model_id = meta['model_SHA256']
        self.metadata = {'combat_foundation': True, 'experimental_critic': meta}

    def infer(self, observation):
        from advisor.learned_response_predictor import public_input
        public_input(observation)
        return super().infer(observation)


class CriticSignalRecorder(AuditedSignalRecorder):
    """Read-only comparisons before first update and after each whole rollout."""
    def __init__(self, directory, encoder, reference_first):
        super().__init__(directory, encoder)
        self.reference_first = Path(reference_first)
        self.same_input = None

    def end(self, model, clock):
        super().end(model, clock)
        name = self.pending[0]
        if clock == 0:
            with np.load(self.reference_first, allow_pickle=False) as old, np.load(
                    self.directory / (name + '.audit.npz'), allow_pickle=False) as new:
                if old.files != new.files or any(not np.array_equal(old[k], new[k]) for k in old.files):
                    raise ValueError('critic_first_rollout_not_bit_identical_before_update')
            import gzip
            scalar_fields = ('t','env','observation_sha256','legal_mask_bits','action','old_logp','value',
                             'reward','return','advantage','episode_start','done','truncated')
            old_path = Path(str(self.reference_first).removesuffix('.audit.npz')+'.jsonl.gz')
            def scalar_rows(path):
                with gzip.open(path,'rt',encoding='utf-8') as stream:
                    return [{k:r[k] for k in scalar_fields} for r in map(json.loads,stream)]
            if scalar_rows(old_path) != scalar_rows(self.directory/(name+'.jsonl.gz')):
                raise ValueError('critic_first_rollout_public_observation_or_boundaries_changed')
            durable_json(self.directory / 'first_rollout_equivalence.json', {
                'status': 'BIT_IDENTICAL', 'transitions': 512, 'before_Adam': clock,
                'reference': str(self.reference_first), 'reference_SHA256': digest(self.reference_first),
                'actual_capture_SHA256': digest(self.directory / (name + '.audit.npz'))})
        b = model.rollout_buffer
        self.same_input = (name, b.observations.reshape(-1, model.observation_space.shape[0]).copy(),
                           b.action_masks.reshape(-1, 35).copy(), b.returns.reshape(-1).copy())

    def settled(self, clock, model=None):
        if self.same_input is not None:
            name, x, masks, targets = self.same_input
            probabilities, values = [], []
            with torch.no_grad():
                for i in range(0, len(x), 128):
                    _, v, _ = model.policy(torch.as_tensor(x[i:i+128], device=model.device),
                        action_masks=masks[i:i+128], deterministic=True)
                    probabilities.append(model.policy.action_dist.distribution.probs.cpu().numpy().copy())
                    values.append(v.flatten().cpu().numpy())
            with (self.directory / (name + '.post.npz')).open('xb') as f:
                np.savez_compressed(f, probabilities=np.concatenate(probabilities), values=np.concatenate(values),
                                    returns=targets)
            self.same_input = None
        super().settled(clock, model)
