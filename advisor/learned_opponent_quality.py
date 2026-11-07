"""Research-only frozen opponent quality audit; no TRAIN authority or learning.

The maintained frozen sampler and addressed PCG64 are reused. Actual native
seats remain intact. Only an owner's validated public view reaches inference.
"""
from copy import deepcopy
from hashlib import sha256
import json
import random

import numpy as np
import torch

from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learned_response_predictor import public_input
from advisor.learned_selfplay_pilot import FrozenPublicActor, read
from advisor.learned_train_opponents import POLICIES, _ValidatedProof, addressed_policy_seed
from advisor.learned_tactical_diagnostics import action_class

VERSION = 'opponent-diversity-quality-pilot-v1'


def global_rng_digest():
    state = np.random.get_state()
    return content_hash({'python': random.getstate(),
        'numpy': [state[0], state[1].tolist(), *state[2:]],
        'torch_CPU': sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()})


class _CapturedProof(_ValidatedProof):
    def infer(self, view):
        result = super().infer(view)
        self.owner.proof = result
        return result


class QualityActor:
    def __init__(self, parent, policy, *, case, seat, role, record):
        if (policy not in POLICIES or seat not in ('p1', 'p2')
                or role not in ('candidate', 'rival') or type(case) is not int or case < 0
                or 'combat_foundation' not in parent.metadata):
            raise ValueError('quality_public_actor_identity')
        self.parent, self.model_id = parent, parent.model_id
        self.policy, self.role, self.seat = policy, role, seat
        self.side = ('self' if seat == 'p1' else 'opponent')
        if role == 'rival': self.side = 'opponent' if self.side == 'self' else 'self'
        self.address = {'version': VERSION, 'seed_namespace': 116081,
            'policy': policy, 'role': role, 'seat': seat, 'case': case,
            'model_SHA256': self.model_id}
        self.seed = addressed_policy_seed(policy, case + 91, self.address)
        self.core = FrozenPublicActor(_CapturedProof(self), POLICIES[policy], self.seed)
        if type(self.core.rng.bit_generator) is not np.random.PCG64:
            raise ValueError('quality_requires_PCG64')
        self.record, self.ordinal, self.episode, self.revision = record, 0, None, None

    def act(self, view):
        public_input(view)
        if (view['side'] != self.side or not isinstance(view.get('episode_id'), str) or not view['episode_id']
                or type(view.get('revision')) is not int or view['revision'] < 0
                or self.episode is not None and self.episode != view['episode_id']
                or self.revision is not None and view['revision'] <= self.revision):
            raise ValueError('quality_owner_or_episode_changed')
        global_before = global_rng_digest()
        local_before = content_hash(self.core.rng.bit_generator.state)
        logits = []
        def capture(module, args):
            logits.append(args[0].detach().cpu().numpy().copy())
        hook = self.parent.model.policy.action_net.register_forward_pre_hook(capture)
        try:
            action = self.core.act(view)
        finally:
            hook.remove()
        if global_rng_digest() != global_before:
            raise ValueError('quality_inference_changed_global_RNG')
        mask = np.asarray(view['action_mask'], dtype=bool)
        if len(logits) != 1 or logits[0].shape != (1, 35):
            raise ValueError('quality_original_logit_capture_missing')
        raw = logits[0][0]; legal = raw[mask].astype(np.float64)
        probs = np.asarray(self.core.last['probabilities'])
        expected = np.exp(legal - legal.max()); expected /= expected.sum()
        if (not np.isfinite(legal).all() or not np.allclose(expected, probs[mask], rtol=2e-5, atol=2e-6)
                or int(np.argmax(np.where(mask, raw, -np.inf))) != self.core.last['argmax']):
            raise ValueError('quality_same_logits_T1_probability_mismatch')
        self.episode, self.revision = view['episode_id'], view['revision']
        entropy = float(-(probs[mask] * np.log(np.maximum(probs[mask], 1e-300))).sum())
        row = {'phase': 'selected_before_native_step', **deepcopy(self.core.last),
            'policy': self.policy, 'role': self.role, 'episode_id': self.episode,
            'revision': self.revision, 'ordinal': self.ordinal, 'case': self.address['case'],
            'candidate_seat': self.seat, 'mask': mask.astype(int).tolist(),
            'legal_count': int(mask.sum()), 'native_choice': view['choices'][action],
            'legal_logits': [float(x) if m else None for x, m in zip(raw, mask)],
            'entropy': entropy, 'selected_family': action_class(view, action),
            'argmax_family': action_class(view, self.core.last['argmax']),
            'value': self.proof['discounted_return_estimate'],
            'rng_address': self.address, 'rng_seed': self.seed, 'rng_algorithm': 'PCG64',
            'rng_before_SHA256': local_before,
            'rng_after_SHA256': content_hash(self.core.rng.bit_generator.state),
            'global_RNG_unchanged': True}
        self.ordinal += 1
        self.record(row, view)
        return action


class QualityTrace:
    """Coordinator-only receipts; native truth is never supplied to actors."""
    def __init__(self, directory, policy, seat, case):
        self.directory, self.policy, self.seat, self.case = directory, policy, seat, case
        self.key = f'{policy}_foundation_argmax_{seat}_{case}'
        self.path = directory / 'decisions' / (self.key + '.jsonl')
        self.stream = self.path.open('x', encoding='utf-8')
        self.pending, self.first, self.steps = {}, {}, 0

    def write(self, row):
        self.stream.write(json.dumps(row, allow_nan=False) + '\n'); self.stream.flush()

    def selection(self, row, view):
        role = row['role']
        if role in self.pending: raise ValueError('quality_unexecuted_selection')
        self.pending[role] = row
        if role not in self.first:
            self.first[role] = row
            durable_json(self.directory / 'initial_public' / (self.key + '_' + role + '.json'),
                         {'view': public_input(view), 'proof': row})
        self.write(row)

    def initial(self, row):
        if self.pending or self.steps: raise ValueError('quality_snapshot_not_before_decisions')
        path = self.directory / 'initial_native' / (self.key + '.json')
        durable_json(path, row)
        other = ('foundation_masked_sample' if self.policy == 'foundation_argmax' else 'foundation_argmax')
        counterpart = self.directory / 'initial_native' / (self.key.replace(self.policy, other, 1) + '.json')
        if counterpart.exists():
            previous = read(counterpart)
            if any(previous[k] != row[k] for k in ('native_checkpoint_digest', 'native_state_SHA256',
                    'canonical_scenario_sha256', 'native_scenario_sha256', 'case', 'candidate_seat')):
                raise ValueError('quality_initial_native_states_not_matched')

    def observe(self, event):
        if set(self.pending) != {'candidate', 'rival'}: raise ValueError('quality_joint_selection_missing')
        for row in self.pending.values():
            side = row['owner']; before = event['before'][side]
            if (content_hash(public_input(before)) != row['input_SHA256']
                    or before['revision'] != row['revision']
                    or event['actions'][side] != row['action']):
                raise ValueError('quality_selection_execution_identity')
        self.write({'phase': 'native_result', 'ordinal': self.steps,
            'actions': event['actions'], 'result': {k: event['result'][k] for k in
                ('action_rejected', 'truncated', 'terminated', 'winner', 'rewards', 'revision', 'decisions')
                if k in event['result']}})
        self.pending = {}; self.steps += 1
        if event['result']['action_rejected'] or event['result']['truncated']:
            raise ValueError('quality_native_rejection_or_truncation_no_retry')

    def finish(self, record):
        self.stream.close()
        if self.pending or record['decisions'] != self.steps:
            raise ValueError('quality_unfinished_execution')
        durable_json(self.directory / 'trace_receipts' / (self.key + '.json'),
            {'trace_path': str(self.path), 'trace_SHA256': digest(self.path),
             'first': self.first, 'decisions': self.steps, 'record_SHA256': content_hash(record)})


def analyze(rows, cases, sampled_decisions, *, draws=20000, seed=116085):
    """Pair clusters retain ownership, native RNG, actual seats, and policies."""
    expected = {(p, c['index'], s) for p in POLICIES for c in cases for s in ('p1', 'p2')}
    by = {(r['policy'], r['case'], r['seat']): r['record'] for r in rows}
    if len(rows) != 1280 or len(by) != 1280 or set(by) != expected:
        raise ValueError('quality_missing_or_duplicate_results')
    if any(r['truncated'] or r['native_choice_rejections'] for r in by.values()):
        raise ValueError('quality_invalid_native_results')
    pairs = sorted({c['pair'] for c in cases})
    if len(pairs) != 80: raise ValueError('quality_requires80clusters')
    indices = np.random.default_rng(seed).integers(0, 80, (draws, 80))
    returns, wins, outcomes = {}, {}, {}
    def interval(x): return np.quantile(x[indices].mean(1), [.025, .975]).tolist()
    for policy in POLICIES:
        records = [r for (p, _, _), r in by.items() if p == policy]
        returns[policy] = np.array([np.mean([by[policy, c['index'], s]['return']
            for c in cases if c['pair'] == pair for s in ('p1', 'p2')]) for pair in pairs])
        wins[policy] = np.array([np.mean([by[policy, c['index'], s]['winner'] == 'self'
            for c in cases if c['pair'] == pair for s in ('p1', 'p2')]) for pair in pairs])
        outcomes[policy] = {'games': len(records), 'wins': sum(r['winner'] == 'self' for r in records),
            'losses': sum(r['winner'] == 'opponent' for r in records),
            'draws': sum(r['winner'] is None for r in records),
            'win_rate': float(wins[policy].mean()), 'win_cluster95CI': interval(wins[policy]),
            'terminal_return': float(returns[policy].mean()), 'return_cluster95CI': interval(returns[policy])}
    delta = returns['foundation_masked_sample'] - returns['foundation_argmax']
    wd = wins['foundation_masked_sample'] - wins['foundation_argmax']
    multi = [r for r in sampled_decisions if r['legal_count'] > 1]
    if not multi: raise ValueError('quality_no_multilegal_decisions')
    diversity = sum(r['action'] != r['argmax'] for r in multi) / len(multi)
    verdict = ('QUALITY_DEGRADED' if float(wd.mean()) < -.1 else
               'DIVERSITY_INSUFFICIENT' if diversity < .05 else 'OPPONENT_QUALITY_PILOT_COMPLETE')
    return {'outcomes': outcomes, 'sample_minus_argmax_return': float(delta.mean()),
        'return_cluster95CI': interval(delta), 'win_difference': float(wd.mean()),
        'win_difference_cluster95CI': interval(wd), 'pair_return_differences': delta.tolist(),
        'multilegal_decisions': len(multi), 'nonargmax_multilegal_rate': diversity,
        'clusters': 80, 'draws': draws, 'bootstrap_seed': seed, 'verdict': verdict,
        'interpretation': 'exploratory screening, not noninferiority, PPO benefit, or model promotion'}
