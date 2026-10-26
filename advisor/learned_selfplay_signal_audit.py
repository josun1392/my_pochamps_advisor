"""Observe the maintained T=1 PPO audit, with a hard optimizer-step guard."""
from hashlib import sha256
from pathlib import Path
import json
import numpy as np

from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
from advisor.learned_parent_anchor import optimizer_clock, tensor_digest, optimizer_digest
from advisor.learned_execution_alignment import durable_json, digest
from advisor.learned_selfplay_pilot import read, exploration_gate


class PilotSignalRecorder(AuditedSignalRecorder):
    def __init__(self, directory, encoder, *, pilot_root):
        super().__init__(directory, encoder)
        self.root = Path(pilot_root)
        self.plan = read(self.root / 'plan.json')
        self.links = []
        self.guard = None

    def start(self, model, clock):
        super().start(model, clock)
        self.links = []
        self.policy_sha = tensor_digest(model.policy.state_dict())
        if self.guard is None:
            def guard(optimizer, args, kwargs):
                if optimizer_clock(model.policy) - self.plan['parent']['optimizer_steps'] >= 2048:
                    raise ValueError('pilot_optimizer_step_cap')
                if (self.root / 'DATA_GAP.json').exists():
                    raise ValueError('pilot_exploration_gate_failed_no_update')
            self.guard = model.policy.optimizer.register_step_pre_hook(guard)
        if not (self.root / 'initial_learner_identity.json').exists():
            initial = {'parameters': self.policy_sha, 'Adam': optimizer_digest(model.policy)}
            if initial != self.plan['parent']['semantic_identity']:
                raise ValueError('pilot_initial_weights_or_Adam_changed')
            durable_json(self.root / 'initial_learner_identity.json', {
                **initial, 'Adam_steps': clock, 'model_timesteps': model.num_timesteps,
                'policy_class': type(model.policy).__name__, 'temperature': 1,
                'gamma': model.gamma, 'GAE_lambda': model.gae_lambda,
                'n_steps': model.n_steps, 'n_envs': model.n_envs, 'batch_size': model.batch_size,
                'epochs': model.n_epochs, 'learning_rate': model.learning_rate,
                'entropy_coefficient': model.ent_coef, 'fresh_Adam': False})

    def step(self, infos, dones):
        super().step(infos, dones)
        self.links.append([info['pilot_public_link'] for info in infos])

    def end(self, model, clock):
        super().end(model, clock)  # Original audit, returns original graph/tensors.
        name = self.pending[0]
        buffer = model.rollout_buffer
        links = []
        for t, row in enumerate(self.links):
            for env, link in enumerate(row):
                if (link['feature_SHA256'] != sha256(buffer.observations[t, env].tobytes()).hexdigest()
                        or link['action'] != int(buffer.actions[t, env, 0])
                        or link['mask'] != buffer.action_masks[t, env].astype(bool).tolist()):
                    raise ValueError('pilot_rollout_native_link_mismatch')
                links.append({'t': t, 'env': env, **link})
        if len(links) != 512 or len({x['decision_id'] for x in links}) != 512:
            raise ValueError('pilot_missing_or_duplicate_decision_join')
        with np.load(self.directory / (name + '.audit.npz'), allow_pickle=False) as data:
            gate = exploration_gate(data['probabilities'], data['native_masks'], data['actions'],
                                    [x['family'] for x in links])
        durable_json(self.directory / (name + '.native_links.json'), {
            'rollout': name, 'policy_parameter_SHA256': self.policy_sha, 'Adam_before': clock,
            'links': links, 'exploration': gate,
            'scope': 'selected_native_action_and_GAE_join_not_teacher_or_optimal_action_labels'})
        if not (self.root / 'preupdate_gate.json').exists():
            durable_json(self.root / 'preupdate_gate.json', gate)
            if not gate['passed']:
                durable_json(self.root / 'DATA_GAP.json', {'reason': 'preupdate_exploration_or_coverage_gate', **gate})
                self.close()
                raise ValueError('DATA_GAP: first_rollout_insufficient_exploration')

    def close(self):
        if self.guard is not None:
            self.guard.remove()
            self.guard = None
        super().close()
