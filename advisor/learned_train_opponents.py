"""Opt-in TRAIN-only Foundation action selection, no new policy network."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256

import numpy as np

from advisor.learned_execution_alignment import content_hash, masked_sample
from advisor.learned_response_predictor import public_input
from advisor.learned_selfplay_pilot import FrozenPublicActor

VERSION = 'foundation-TRAIN-opponent-policy-diversity-v1'
KEY = 'train_foundation_opponent'
POLICIES = {'foundation_argmax': 'argmax', 'foundation_masked_sample': 'T1_sample'}


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_manifest(manifest, model_id):
    required = {'schema_version', 'scope', 'model_SHA256', 'training_seed', 'rng_namespace', 'policy_slots'}
    if (not isinstance(manifest, dict) or set(manifest) != required
            or manifest['schema_version'] != VERSION or manifest['scope'] != 'train'
            or not _sha(model_id) or manifest['model_SHA256'] != model_id
            or type(manifest['training_seed']) is not int or not 0 <= manifest['training_seed'] < 2**32
            or not isinstance(manifest['rng_namespace'], str) or not manifest['rng_namespace']
            or not isinstance(manifest['policy_slots'], list) or not 1 <= len(manifest['policy_slots']) <= 12
            or any(type(p) is not str or p not in POLICIES for p in manifest['policy_slots'])):
        raise ValueError('invalid_TRAIN_Foundation_opponent_manifest')
    return deepcopy(manifest)


def mixture_identity(manifest):
    manifest = validate_manifest(manifest, manifest.get('model_SHA256') if isinstance(manifest, dict) else None)
    slots = manifest['policy_slots']
    return {'manifest_SHA256': content_hash(manifest),
            'selection': 'case_index_modulo_policy_slots_not_iid_or_decision_weighting',
            'nominal_episode_probabilities': {p: n / len(slots) for p, n in Counter(slots).items()}}


def addressed_policy_seed(policy, legacy_seed, address):
    """Shared PCG64 addressing; callers keep TRAIN/evaluation authority separate."""
    if policy not in POLICIES or type(legacy_seed) is not int or legacy_seed < 0:
        raise ValueError('invalid_Foundation_policy_rng_address')
    return (legacy_seed if policy == 'foundation_argmax'
            else int.from_bytes(sha256(content_hash(address).encode()).digest()[:16], 'big'))


class _ValidatedProof:
    def __init__(self, owner):
        self.owner, self.model_id = owner, owner.model_id

    def infer(self, view):
        owner = self.owner
        if owner.parent.model_id != self.model_id:
            raise ValueError('TRAIN_opponent_model_changed')
        proof = owner.parent.infer(view)  # The exact original owner-visible view only.
        if (proof.get('model_id') != self.model_id
                or proof.get('action_schema_version') != 'showdown-policy-actions-v1'
                or any(proof.get(k) != view[k] for k in ('episode_id', 'revision', 'side'))):
            raise ValueError('TRAIN_opponent_proof_identity')
        # Validate before the existing sampler draws. Never repair illegal mass.
        masked_sample(proof['action_probabilities'], view['action_mask'], 0.)
        action = proof.get('action_index')
        if type(action) is not int or action != int(np.argmax(proof['action_probabilities'])):
            raise ValueError('TRAIN_opponent_argmax_identity')
        return proof


class TrainFoundationOpponent:
    """Per-case frozen actor with a coordinator-only, independently addressed RNG.

    State export/import restores this adapter only. It is not native/rollout
    cold-resume support and does not enable the fail-closed trainer --resume.
    """
    def __init__(self, parent, manifest, episode, *, worker, segment, legacy_seed):
        self.manifest = validate_manifest(manifest, parent.model_id)
        if 'combat_foundation' not in getattr(parent, 'metadata', {}):
            raise ValueError('TRAIN_opponent_requires_frozen_Foundation')
        if (episode.get('split') != 'train' or type(worker) is not int or not 0 <= worker < 4
                or type(segment) is not int or segment < 0
                or type(episode.get('case_index')) is not int or episode['case_index'] < 0
                or type(legacy_seed) is not int or legacy_seed != episode['case_index'] + 91
                or not isinstance(episode.get('scenario_id'), str) or not episode['scenario_id']
                or not _sha(episode.get('scenario_sha256'))
                or set(episode.get('team_sha256', {})) != {'self', 'opponent'}
                or any(not _sha(x) for x in episode['team_sha256'].values())
                or not isinstance(episode.get('native_seed'), list) or len(episode['native_seed']) != 4
                or any(type(x) is not int or not 0 <= x <= 65535 for x in episode['native_seed'])):
            raise ValueError('TRAIN_opponent_session_identity')
        self.parent, self.model_id = parent, parent.model_id
        self.policy_name = self.manifest['policy_slots'][episode['case_index'] % len(self.manifest['policy_slots'])]
        self.mode = POLICIES[self.policy_name]
        self.session = {'worker': worker, 'segment': segment,
            **{k: deepcopy(episode[k]) for k in ('split', 'case_index', 'scenario_id', 'scenario_sha256', 'team_sha256', 'native_seed')}}
        self.address = {'version': VERSION, 'namespace': self.manifest['rng_namespace'],
            'training_seed': self.manifest['training_seed'], 'worker': worker, 'segment': segment,
            'case_index': episode['case_index'], 'policy': self.policy_name, 'model_SHA256': self.model_id}
        # No hidden team/preview/native RNG value participates in the draw address.
        self.seed = addressed_policy_seed(self.policy_name, legacy_seed, self.address)
        self.core = FrozenPublicActor(_ValidatedProof(self), self.mode, self.seed)
        if type(self.core.rng.bit_generator) is not np.random.PCG64:
            raise ValueError('TRAIN_opponent_requires_versioned_PCG64')
        self.selections, self.draws, self.bound_episode, self.revision = 0, 0, None, None
        self.last, self._restored = None, False

    def identity(self):
        return {'schema_version': VERSION, 'scope': 'train', 'policy': self.policy_name,
                'model_SHA256': self.model_id, 'manifest': deepcopy(self.manifest),
                **mixture_identity(self.manifest), 'session': deepcopy(self.session),
                'session_SHA256': content_hash(self.session), 'rng_address': deepcopy(self.address),
                'rng_seed': self.seed, 'rng_algorithm': 'PCG64',
                'rng_source': ('none_argmax_legacy_seed_unused' if self.mode == 'argmax'
                               else 'independent_per_case_numpy_Generator_one_float64_per_selection')}

    def act(self, view):
        public_input(view)
        if (view.get('side') != 'opponent' or not isinstance(view.get('episode_id'), str)
                or not view['episode_id'] or type(view.get('revision')) is not int or view['revision'] < 0
                or self.bound_episode is not None and view['episode_id'] != self.bound_episode
                or self.revision is not None and view['revision'] < self.revision):
            raise ValueError('TRAIN_opponent_public_session_mismatch')
        before = content_hash(self.core.rng.bit_generator.state)
        action = self.core.act(view)  # Maintained public-input/mask/CDF authority.
        self.selections += 1
        self.draws += self.mode == 'T1_sample'
        self.bound_episode, self.revision = view['episode_id'], view['revision']
        self.last = {**deepcopy(self.core.last), 'TRAIN_opponent': self.identity(),
                     'selection_index': self.selections - 1, 'rng_draws': self.draws,
                     'episode_id': self.bound_episode, 'revision': self.revision,
                     'rng_before_SHA256': before,
                     'rng_after_SHA256': content_hash(self.core.rng.bit_generator.state)}
        return action

    def state_dict(self):
        body = {'schema_version': VERSION, 'identity': self.identity(),
                'selections': self.selections, 'draws': self.draws,
                'bound_episode': self.bound_episode, 'revision': self.revision,
                'rng_state': deepcopy(self.core.rng.bit_generator.state)}
        return {**body, 'SHA256': content_hash(body)}

    def load_state_dict(self, state):
        if self._restored or self.selections:
            raise ValueError('TRAIN_opponent_restore_requires_fresh_adapter')
        if not isinstance(state, dict) or set(state) != {
                'schema_version', 'identity', 'selections', 'draws', 'bound_episode', 'revision', 'rng_state', 'SHA256'}:
            raise ValueError('TRAIN_opponent_missing_rng_checkpoint')
        body = {k: v for k, v in state.items() if k != 'SHA256'}
        if (state['SHA256'] != content_hash(body) or state['schema_version'] != VERSION
                or state['identity'] != self.identity() or self.parent.model_id != self.model_id):
            raise ValueError('TRAIN_opponent_checkpoint_identity')
        n, draws = state['selections'], state['draws']
        if (type(n) is not int or n < 0 or type(draws) is not int
                or draws != (n if self.mode == 'T1_sample' else 0)
                or n == 0 and (state['bound_episode'] is not None or state['revision'] is not None)
                or n > 0 and (not isinstance(state['bound_episode'], str) or not state['bound_episode']
                             or type(state['revision']) is not int or state['revision'] < 0)):
            raise ValueError('TRAIN_opponent_checkpoint_cursor')
        expected = np.random.PCG64(self.seed)
        expected.advance(draws)  # One float64 draw/selection, also for singleton masks.
        if content_hash(expected.state) != content_hash(state['rng_state']):
            raise ValueError('TRAIN_opponent_rng_cursor_mismatch')
        self.core.rng.bit_generator.state = deepcopy(expected.state)
        self.selections, self.draws = n, draws
        self.bound_episode, self.revision = state['bound_episode'], state['revision']
        self._restored = True
