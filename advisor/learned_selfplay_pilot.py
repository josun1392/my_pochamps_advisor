"""Bounded experiment adapters; native rules and PPO remain existing owners."""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import gzip
from hashlib import sha256
import json
from pathlib import Path

import gymnasium as gym
import numpy as np

from advisor.learned_execution_alignment import content_hash, digest, durable_json, masked_sample
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_response_predictor import public_input

VERSION = 'foundation-bounded-selfplay-exploration-ppo-pilot-v1'
OPPONENTS = ('league_s0', 'league_anchor', 'tactical_heuristic', 'champions_heuristic')
MODES = {'league_s0': 'argmax', 'league_anchor': 'T1_sample'}
RIVALS = ('foundation_argmax', 'v4_argmax', 'tactical_heuristic', 'champions_heuristic')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


class StartBudget:
    """Exclusive worker directory, durable intents before resets, no reuse."""
    def __init__(self, directory, maximum, stop, ordinal_offset=0):
        self.directory, self.maximum, self.stop = Path(directory), maximum, Path(stop)
        self.ordinal_offset = ordinal_offset
        self.directory.mkdir(parents=True, exist_ok=True)
        self.count = len(list(self.directory.glob('start_*.json')))

    def reserve(self, provenance):
        if self.stop.exists():
            raise RuntimeError('pilot_STOP_before_new_native_start')
        if self.count >= self.maximum:
            raise RuntimeError('pilot_native_start_budget_exhausted')
        ordinal = self.count + self.ordinal_offset
        durable_json(self.directory / f'start_{ordinal:04d}.json',
                     {'ordinal': ordinal, **provenance})
        self.count += 1
        return ordinal


class FrozenPublicActor:
    """A frozen existing model; only the supplied owner's public view enters it."""
    def __init__(self, actor, mode, seed):
        if mode not in ('argmax', 'T1_sample'):
            raise ValueError('unsupported_frozen_action_mode')
        self.actor, self.mode, self.model_id = actor, mode, actor.model_id
        self.rng = np.random.default_rng(seed)
        self.last = None

    def act(self, view):
        public_input(view)  # Validates owner/request, mask, privileged roots.
        proof = self.actor.infer(view)
        uniform = float(self.rng.random()) if self.mode == 'T1_sample' else None
        action = (masked_sample(proof['action_probabilities'], view['action_mask'], uniform)
                  if uniform is not None else int(proof['action_index']))
        if not view['action_mask'][action]:
            raise ValueError('frozen_opponent_illegal_action')
        self.last = {'action': action, 'argmax': proof['action_index'], 'mode': self.mode,
                     'model_SHA256': self.model_id, 'uniform': uniform,
                     'probabilities': proof['action_probabilities'],
                     'owner': view['side'], 'input_SHA256': content_hash(public_input(view))}
        return action


class NativePublicTrace:
    """Existing native recorder hooks; never reads checkpoint, truth or RNG."""
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.pending = None
        self.ordinal = 0
        self.first_link = None

    def native_before(self, native, views, actions):
        from scripts.run_foundation_difficulty_calibration import compact_view
        w = self.wrapper
        for side, view in views.items():
            public_input(view)
            if not view['action_mask'][int(actions[side])]:
                raise ValueError('pilot_illegal_native_submission')
        view = views['self']
        key = (view['episode_id'], view['revision'], view['side'])
        feature = w.last_encoded[1] if w.last_encoded and w.last_encoded[0] == key else None
        decision_id = f'{w.worker}:{w.episode}:{self.ordinal}:self'
        self.pending = {'decision_id': decision_id, 'ordinal': self.ordinal,
            'before': {s: compact_view(v) for s, v in views.items()},
            'actions': {s: int(a) for s, a in actions.items()},
            'self_public_input_SHA256': content_hash(public_input(view)),
            'self_feature_SHA256': feature,
            'opponent_proof': deepcopy(getattr(w.env.opponent, 'last', None))}
        if self.ordinal == 0:
            self.pending['initial_public_views'] = views
        if self.first_link is None:
            if feature is None:
                raise ValueError('pilot_policy_observation_feature_link_missing')
            from advisor.learned_tactical_diagnostics import action_class
            self.first_link = {'decision_id': decision_id, 'episode_id': view['episode_id'],
                'revision': view['revision'], 'feature_SHA256': feature,
                'action': int(actions['self']), 'mask': list(view['action_mask']),
                'public_input_SHA256': self.pending['self_public_input_SHA256'],
                'family': action_class(view, int(actions['self'])),
                'native_trace': str(w.trace_path), 'native_ordinal': self.ordinal}
        self._before = views

    def native_after(self, native, result):
        from scripts.run_foundation_difficulty_calibration import compact_view
        from advisor.learned_selfplay_retry import ResolvedRequestRateGuard
        w = self.wrapper
        after = {s: native.observation(s, include_history=True) for s in self._before}
        row = {**self.pending, 'result': result, 'after': {s: compact_view(v) for s, v in after.items()},
               'outcome_receipt': f'episode_{w.episode:04d}.json'}
        w.stream.write((json.dumps(row, allow_nan=False) + '\n').encode())
        self.ordinal += 1
        self.pending = None
        w.last_result = deepcopy(result)
        # Native execution has already happened. Record it before either guard
        # can raise; keep guard order, thresholds and recovery behavior intact.
        try:
            w.retry.observe({'before': self._before, 'actions': row['actions'], 'result': result})
            w.rate.observe(row if isinstance(w.rate, ResolvedRequestRateGuard) else result['action_rejected'])
        except Exception as error:
            import os
            w.stream.flush(); w.raw.flush(); os.fsync(w.raw.fileno())
            durable_json(w.directory / f'guard_failure_{w.episode:04d}_{row["ordinal"]:04d}.json', {
                'scope': 'coordinator_only_player_owned_views_no_native_truth',
                'guard_type': type(error).__name__, 'guard_message': str(error),
                'rate_attempts': getattr(w.rate, 'attempts', None),
                'rate_rejections': getattr(w.rate, 'rejections', None),
                'trace': str(w.trace_path), 'row': row,
                'native_error_text': 'not_exposed_by_existing_native_response',
                'guard_behavior_changed': isinstance(w.rate, ResolvedRequestRateGuard),
                'classified_rate': w.rate.statistics() if isinstance(w.rate, ResolvedRequestRateGuard) else None})
            raise


class AuditedPilotEnv(gym.Wrapper):
    def __init__(self, env, directory, budget, initial_episode, worker, classified_retries=False):
        super().__init__(env)
        from advisor.learned_difficulty_calibration import AttemptRateGuard
        self.directory, self.budget, self.worker = Path(directory), budget, worker
        self.last_encoded, self.last_result = None, None
        self.stream = self.raw = None
        if classified_retries:
            from advisor.learned_selfplay_retry import ResolvedRequestRateGuard
            self.rate = ResolvedRequestRateGuard()
        else:
            self.rate = AttemptRateGuard()
        encode = env.encoder.encode
        def encoded(view):
            value = encode(view)
            self.last_encoded = ((view['episode_id'], view['revision'], view['side']),
                                 sha256(value.tobytes()).hexdigest())
            return value
        env.encoder.encode = encoded
        factory = env.opponent_factory
        def opponent(kind, seed):
            # Both aliases share ONE immutable Foundation instance per worker.
            if kind in MODES:
                return FrozenPublicActor(factory('league_s0', seed), MODES[kind], seed)
            return factory(kind, seed)
        env.opponent_factory = opponent
        env.opponent = opponent(env.opponent_kind, env._episode_identity['case_index'] + 91)
        self._open_episode(initial_episode)

    def _open_episode(self, ordinal):
        from advisor.learned_difficulty_calibration import PublicRetryAudit
        self.episode, self.last_result = ordinal, None
        self.trace_path = self.directory / f'trace_{ordinal:04d}.jsonl.gz'
        self.raw = self.trace_path.open('xb')
        self.stream = gzip.GzipFile(fileobj=self.raw, mode='wb', mtime=0)
        self.retry = PublicRetryAudit(self.env._episode_identity['case_index'])
        self.recorder = NativePublicTrace(self)
        self.env.decision_snapshot_recorder = self.recorder
        durable_json(self.directory / f'identity_{ordinal:04d}.json', {
            'episode_id': self.env.current['episode_id'], 'worker': self.worker,
            'episode_identity': deepcopy(self.env._episode_identity),
            'opponent_mode': MODES.get(self.env.opponent_kind, 'existing_heuristic'),
            'information_scope': 'coordinator_only_not_actor_critic_features'})

    def _finish_episode(self, status):
        if self.stream is None:
            return
        import os
        self.stream.close(); self.raw.flush(); os.fsync(self.raw.fileno()); self.raw.close()
        self.stream = self.raw = None
        from advisor.learned_selfplay_retry import ResolvedRequestRateGuard
        durable_json(self.directory / f'episode_{self.episode:04d}.json', {
            'episode': self.episode, 'worker': self.worker, 'status': status,
            'native_steps': self.recorder.ordinal, 'trace': str(self.trace_path),
            'trace_SHA256': digest(self.trace_path), 'last_native_result': self.last_result,
            'native_rejections': self.retry.rejections,
            'classified_rate': self.rate.statistics() if isinstance(self.rate, ResolvedRequestRateGuard) else None,
            'identity_SHA256': digest(self.directory / f'identity_{self.episode:04d}.json')})

    def reset(self, **kwargs):
        self._finish_episode('reset_before_terminal')
        ordinal = self.budget.reserve({'phase': 'training', 'reason': 'Gym_reset', 'worker': self.worker})
        result = self.env.reset(**kwargs)
        self._open_episode(ordinal)
        return result

    def step(self, action):
        self.recorder.first_link = None
        value, reward, terminated, truncated, info = self.env.step(action)
        link = self.recorder.first_link
        if link is None or link['action'] != int(action):
            raise ValueError('pilot_PPO_native_action_link')
        if terminated or truncated:
            self._finish_episode('terminal' if terminated else 'native_time_limit')
        return value, reward, terminated, truncated, {**info, 'pilot_public_link': link}

    def close(self):
        self._finish_episode('open_at_training_stop')
        return self.env.close()


@dataclass(frozen=True)
class PilotEnvFactory(LearningEnvFactory):
    pilot_root: str = ''

    def __call__(self):
        root = Path(self.pilot_root)
        worker = self.index_offset // 100000
        if tuple(self.opponents) != OPPONENTS or not 0 <= worker < 4:
            raise ValueError('pilot_factory_contract')
        plan = read(root / 'plan.json')
        if any(self.references[k][1] != plan['parent']['sha256'] for k in MODES):
            raise ValueError('pilot_frozen_Foundation_identity')
        directory = root / 'native_training' / f'worker_{worker}'
        recovery = plan.get('recovery')
        budget = StartBudget(directory, 512 if recovery else 2048, root / 'STOP',
                             recovery['prior_worker_starts'][worker] if recovery else 0)
        initial = budget.reserve({'phase': 'training', 'reason': 'existing_Gym_constructor_reset', 'worker': worker})
        return AuditedPilotEnv(super().__call__(), directory, budget, initial, worker, bool(recovery))


def exploration_gate(probabilities, masks, actions, families):
    p, m, a = np.asarray(probabilities), np.asarray(masks, bool), np.asarray(actions, int)
    if p.shape != m.shape or p.shape[1] != 35 or len(a) != len(p) or not m[np.arange(len(a)), a].all():
        raise ValueError('pilot_gate_shape_or_mask')
    if not np.isfinite(p).all() or (p[~m] != 0).any() or not np.allclose(p.sum(1), 1):
        raise ValueError('pilot_gate_invalid_distribution')
    selected = m.sum(1) > 1
    maxima = p.argmax(1)
    n = int(selected.sum())
    rate = float(np.mean(a[selected] != maxima[selected])) if n else 0.
    entropy = -(p * np.log(np.clip(p, 1e-30, 1))).sum(1)
    normalized = float(np.mean(entropy[selected] / np.log(m.sum(1)[selected]))) if n else 0.
    counts = Counter(families)
    meaningful = Counter(f for f, use in zip(families, selected) if use and f not in ('wait', 'replacement'))
    distinct = len(set(a[selected].tolist()))
    result = {'multi_legal_decisions': n, 'nonargmax_rate': rate,
              'normalized_entropy': normalized, 'distinct_action_slots': distinct,
              'families': dict(counts), 'multi_legal_meaningful_families': dict(meaningful)}
    result['passed'] = n >= 128 and rate >= .10 and normalized >= .10 and distinct >= 8 and len(meaningful) >= 2
    return result
