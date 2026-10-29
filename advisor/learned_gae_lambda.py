"""Explicit, bounded lambda-one continuation; historical Foundation stays .95."""
from pathlib import Path
import gzip
import json
import numpy as np
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO
from advisor.learned_execution_alignment import digest, durable_json
from advisor.learned_ppo_contract_audit import AuditedSignalRecorder

VERSION = 'foundation-GAE-lambda-one-continuation-v1'
PARENT_SHA = '9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf'


def lambda_contract():
    return {'schema_version': VERSION, 'gamma': 1., 'gae_lambda': 1.,
        'parent_model_sha256': PARENT_SHA, 'parent_gae_lambda': .95,
        'initialization': 'same_Foundation_weights_and_restored_Adam',
        'scope': 'actor_GAE_and_critic_lambda_return_not_reward_change',
        'budget': 65536, 'rollout': 512}


def validate_contract(value):
    if value != lambda_contract():
        raise ValueError('invalid_GAE_lambda_one_opt_in')
    return dict(value)


def validate_foundation_gae(model):
    """No attribute can enable lambda one on the historical base algorithm."""
    marker = getattr(model, 'gae_lambda_experiment', None)
    if type(model) is GaeOneFoundationPPO:
        validate_contract(marker)
        if model.gae_lambda != 1. or model.gamma != 1.:
            raise ValueError('GAE_lambda_algorithm_objective_mismatch')
    elif marker is not None or model.gae_lambda != .95:
        raise ValueError('foundation_ppo_contract_mismatch')
    if (model.rollout_buffer.gae_lambda != model.gae_lambda
            or model.rollout_buffer.gamma != model.gamma):
        raise ValueError('GAE_lambda_buffer_contract_mismatch')


class GaeOneFoundationPPO(FoundationCombatPPO):
    def __init__(self, *args, gae_lambda_experiment=None, **kwargs):
        # SB3 constructs without data before restoring a ZIP's attributes.
        self.gae_lambda_experiment = (validate_contract(gae_lambda_experiment)
            if gae_lambda_experiment is not None else None)
        self.gae_lambda_trained = 0
        super().__init__(*args, **kwargs)

    def train(self):
        c = validate_contract(self.gae_lambda_experiment)
        validate_foundation_gae(self)
        size = self.n_steps * self.n_envs
        if size != c['rollout'] or not 0 <= self.gae_lambda_trained <= c['budget']-size:
            raise ValueError('GAE_lambda_training_budget')
        super().train()  # Original PPO, auxiliary, entropy, clipping and Adam.
        self.gae_lambda_trained += size
        self.logger.record('train/GAE_lambda', self.gae_lambda)


def validate_loaded(model, metadata):
    actual = getattr(model, 'gae_lambda_experiment', None)
    if actual != metadata.get('gae_lambda_experiment'):
        raise ValueError('GAE_lambda_checkpoint_metadata_mismatch')
    if isinstance(model, FoundationCombatPPO):
        validate_foundation_gae(model)
    if actual is not None or type(model) is GaeOneFoundationPPO:
        validate_foundation_gae(model)
        if (type(model) is not GaeOneFoundationPPO
                or model.gae_lambda_trained != metadata.get('gae_lambda_trained')
                or type(model.gae_lambda_trained) is not int
                or not 0 <= model.gae_lambda_trained <= 65536
                or model.gae_lambda_trained % 512):
            raise ValueError('GAE_lambda_checkpoint_algorithm_or_progress')


def initial_model(model, path, experiment, *, resume):
    """One declared .95 -> 1 boundary, never an implicit resume mutation."""
    requested = experiment.get('gae_lambda_experiment')
    actual = getattr(model, 'gae_lambda_experiment', None)
    if requested is None:
        if actual is not None:
            raise ValueError('resume_GAE_lambda_opt_in_removed')
        return model
    validate_contract(requested)
    if actual is not None:
        if actual != requested or type(model) is not GaeOneFoundationPPO:
            raise ValueError('resume_GAE_lambda_contract_mismatch')
        return model
    if (resume or type(model) is not FoundationCombatPPO or model.gae_lambda != .95
            or digest(path) != PARENT_SHA or experiment.get('fresh_optimizer') is not False):
        raise ValueError('GAE_lambda_requires_original_parent_and_Adam')
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
    converted = GaeOneFoundationPPO.load(path, device='cpu', gae_lambda=1.,
        gae_lambda_experiment=requested, gae_lambda_trained=0)
    if (tensor_digest(model.policy.state_dict()) != tensor_digest(converted.policy.state_dict())
            or optimizer_digest(model.policy) != optimizer_digest(converted.policy)):
        raise ValueError('GAE_lambda_initial_weights_or_Adam_changed')
    validate_foundation_gae(converted)
    return converted


def gae_arrays(values, rewards, starts, last_values, last_dones, lam):
    """Independent read-only diagnostic; upstream remains the target authority."""
    result = np.zeros_like(values)
    tail = 0.
    for t in reversed(range(len(values))):
        non = 1.-last_dones.astype(np.float32) if t == len(values)-1 else 1.-starts[t+1]
        nxt = last_values if t == len(values)-1 else values[t+1]
        tail = rewards[t]+nxt*non-values[t]+lam*non*tail
        result[t] = tail
    return result


class GaeSignalRecorder(AuditedSignalRecorder):
    """Identical recorder plus pre-update matching and lambda diagnostics."""
    def __init__(self, directory, encoder, reference=None):
        super().__init__(directory, encoder)
        self.reference = Path(reference) if reference is not None else None

    def end(self, model, clock):
        super().end(model, clock)
        name = self.pending[0]
        path = self.directory/(name+'.audit.npz')
        with np.load(path) as z:
            a95 = gae_arrays(z['values'], z['rewards'], z['episode_starts'], z['last_values'], z['last_dones'], .95)
            a1 = gae_arrays(z['values'], z['rewards'], z['episode_starts'], z['last_values'], z['last_dones'], 1.)
            actual = a1 if model.gae_lambda == 1. else a95
            error = float(abs(actual-z['advantages']).max())
            if error > 2e-6 or not np.isfinite(actual).all():
                raise ValueError('GAE_lambda_independent_reproduction_failed')
            proof = {'capture_SHA256': digest(path), 'lambda': model.gae_lambda,
                'GAE_max_error': error, 'SD95': float(a95.std()), 'SD1': float(a1.std()),
                'raw_sign_flip': float(np.mean((a95>0)!=(a1>0))),
                'first_preupdate_comparison': None}
            if clock == 32768:
                proof['first_preupdate_comparison'] = self.compare_first(path, name, z)
        durable_json(self.directory/(name+'.gae.json'), proof)
        original = model.rollout_buffer.get
        normalization = self.active[1]['advantage_normalization'] = []
        def batches(*args, **kwargs):
            for batch in original(*args, **kwargs):
                a = batch.advantages
                n = (a-a.mean())/(a.std()+1e-8) if model.normalize_advantage else a
                normalization.append({'n': len(a), 'raw_mean': float(a.mean()),
                    'raw_std': float(a.std()), 'normalized_mean': float(n.mean()),
                    'normalized_std': float(n.std()), 'sign_flips': int(((a>0)!=(n>0)).sum())})
                yield batch
        model.rollout_buffer.get = batches

    def compare_first(self, path, name, z):
        if self.reference is None:
            return {'role': 'reference', 'capture': str(path), 'SHA256': digest(path)}
        refs = list(self.reference.glob('rollout_1049088_*.audit.npz'))
        if len(refs) != 1:
            raise ValueError('GAE_first_rollout_reference_missing_or_ambiguous')
        fields = ('raw_logits', 'probabilities', 'native_masks', 'actions', 'old_logp',
            'values', 'rewards', 'episode_starts', 'last_values', 'last_dones')
        with np.load(refs[0]) as ref:
            if any(not np.array_equal(z[k], ref[k]) for k in fields):
                raise ValueError('GAE_first_rollout_policy_or_execution_mismatch')
        def public_rows(p):
            with gzip.open(p, 'rt', encoding='utf8') as stream:
                return [json.loads(line) for line in stream]
        own = public_rows(self.directory/(name+'.jsonl.gz'))
        ref = public_rows(refs[0].with_name(refs[0].name.replace('.audit.npz', '.jsonl.gz')))
        keys = ('observation_sha256', 'legal_mask_bits', 'action', 'old_logp', 'value',
            'reward', 'episode_start', 'done', 'truncated')
        if len(own) != 512 or len(ref) != 512 or any(a[k] != b[k] for a,b in zip(own,ref) for k in keys):
            raise ValueError('GAE_first_rollout_public_observation_or_boundary_mismatch')
        return {'role': 'matched_before_any_B_update', 'reference': str(refs[0]),
            'reference_SHA256': digest(refs[0]), 'exact_fields': list(fields),
            'public_rows_exact': 512, 'advantages_returns': 'intentionally_different_estimators'}
