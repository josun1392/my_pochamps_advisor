"""Prepare, smoke-test or consume one frozen combat-foundation readiness panel."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from time import perf_counter
import gymnasium as gym
import numpy as np
import torch

from advisor.learned_combat_foundation import (
    FoundationCombatEncoder, FoundationCombatPPO, FoundationCombatPolicy,
    foundation_contract, transfer_foundation_weights,
)
from advisor.learned_objective import categorical_learning_source_identity
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.learned_encoder import fingerprint
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json
from scripts.train_showdown_autonomous import run, save_checkpoint, validate_config, optimizer_steps
from scripts.evaluate_showdown_policy import evaluate


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def prepare(reference, output, initialization, pretrained_model=None, pretrained_id=None):
    config = json.loads(reference.read_text(encoding='utf-8-sig'))
    output.mkdir(parents=True, exist_ok=False)
    encoder = FoundationCombatEncoder(config['catalog'])

    class Spaces(gym.Env):
        action_space = gym.spaces.Discrete(35)
        observation_space = gym.spaces.Box(-2, 4, (encoder.dimension,), dtype=np.float32)

    torch.set_num_threads(1)
    learner = FoundationCombatPPO(FoundationCombatPolicy, Spaces(), n_steps=128, batch_size=128,
        n_epochs=4, gamma=1., gae_lambda=.95, learning_rate=5e-5, ent_coef=.01,
        zero_avoiding_beta=.001, target_kl=.03, seed=95017, device='cpu')
    source = (LearnedPolicy(pretrained_model, config['catalog'], expected_model_id=pretrained_id)
              if initialization == 'v4' else None)
    if initialization == 'v4':
        transfer_foundation_weights(learner.policy, source.model.policy, encoder, source.encoder)
    initial = save_checkpoint(learner, encoder, output / 'initialization', {
        'initialization': initialization, 'weight_transfer_source_sha256': source.model_id if initialization == 'v4' else None,
        'optimizer_initialization': 'fresh_Adam', 'competitive_strength_claim': False})
    experiment = deepcopy(config['experiments'][0])
    for key in ('initial_model', 'initial_model_id', 'transfer_model', 'transfer_model_id'):
        experiment.pop(key, None)
    experiment.update(name='foundation_v1', seed=95017, steps=4096,
        initial_model=initial, initial_model_id=digest(initial), fresh_optimizer=False,
        combat_foundation=foundation_contract(), gamma=1., gae_lambda=.95, ent_coef=.01,
        zero_avoiding_beta=.001, learning_rate=5e-5, warmstart_decisions=0)
    config.update(experiments=[experiment], max_runtime_seconds=600, checkpoint_steps=2048,
        validation_cases=1, evaluation_opponents=['tactical_heuristic'], final_test_cases=0,
        collect_rollout_diagnostics=True, collect_tactical_metrics=True,
        cpu_threads=1, cpu_percent=50, memory_mib=12288, device='cpu',
        transition_budget_scope='trained_rollouts_v1', validation_selection_mode='diagnostic_fixed_budget_v1')
    validate_config(config)
    atomic_json(output / 'smoke_config.json', config)
    long_config = deepcopy(config)
    long_config.update(envs=4, max_runtime_seconds=21600, checkpoint_steps=32768, validation_cases=16,
        evaluation_opponents=['max_power', 'champions_heuristic', 'tactical_heuristic', 'previous'])
    long_config['experiments'][0]['steps'] = 1048576
    validate_config(long_config)
    atomic_json(output / 'long_training_stage1_NOT_STARTED.json', long_config)
    cases = [scenario(split, 96171000 + index, version=config['curriculum_version'])
             for split in ('test', 'unseen') for index in range(8)]
    atomic_json(output / 'final_readiness_cases.json', {'cases': cases})
    identity_paths = [config['previous_model'], initial, config['training_subset'],
                      experiment['historical_model'], *experiment['frozen_opponents'].values()]
    if pretrained_model:
        identity_paths.append(str(pretrained_model))
    atomic_json(output / 'freeze.json', {
        'contract': foundation_contract(), 'source_sha256': categorical_learning_source_identity(),
        'initialization': initialization, 'initial_model_sha256': digest(initial),
        'artifacts': {str(path): digest(path) for path in identity_paths},
        'config_sha256': digest(output / 'smoke_config.json'),
        'long_config_sha256': digest(output / 'long_training_stage1_NOT_STARTED.json'),
        'final_panel_sha256': digest(output / 'final_readiness_cases.json'),
        'final_panel': {'cases': 16, 'seats': ['p1', 'p2'],
                       'rivals': ['max_power', 'tactical_heuristic', 'V4', 'league_anchor'],
                       'consumption': 'once_after_source_freeze_no_architecture_selection',
                       'scope': 'fresh_seeded_case_identities_existing_heldout_team_pools_not_species_unseen'},
        'long_training_started': False,
    })
    print(json.dumps({'initial': initial, 'sha256': digest(initial), 'parameters': sum(p.numel() for p in learner.policy.parameters())}))


def require_freeze(output):
    frozen = json.loads((output / 'freeze.json').read_text())
    if frozen['contract'] != foundation_contract() or frozen['source_sha256'] != categorical_learning_source_identity():
        raise ValueError('foundation_frozen_source_changed')
    for name, identity in frozen['artifacts'].items():
        if digest(name) != identity:
            raise ValueError('foundation_external_artifact_changed:' + name)
    for name, key in [('smoke_config.json', 'config_sha256'),
                      ('long_training_stage1_NOT_STARTED.json', 'long_config_sha256'),
                      ('final_readiness_cases.json', 'final_panel_sha256')]:
        if digest(output / name) != frozen[key]:
            raise ValueError('foundation_frozen_file_changed:' + name)
    return frozen, json.loads((output / 'smoke_config.json').read_text())


def smoke(output):
    _, config = require_freeze(output)
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=40)
    directory = output / 'native_smoke'
    started = perf_counter()

    def stop_at_checkpoint(event):
        if event['phase'] == 'evaluating' and event.get('transitions', 0) >= 2048:
            (directory / 'STOP').write_text('intentional foundation recovery test', encoding='utf-8')

    run(config, directory, event_callback=stop_at_checkpoint, resource_job=job)
    stopped = json.loads((directory / 'state.json').read_text())
    if stopped['status'] != 'stopped' or stopped['trained_rollout_transitions'] != 2048:
        raise AssertionError('foundation_checkpoint_STOP_failed')
    first = LearnedPolicy(stopped['latest'], config['catalog'])
    initial_steps = optimizer_steps(first.model)
    state = run(config, directory, resume=True, resource_job=job)
    endpoints = sorted((directory / 'experiment_00').glob('checkpoint_*_ppo_*/model.zip'))
    endpoint = max(endpoints, key=lambda path: json.loads(path.with_suffix('.json').read_text())['total_steps'])
    restored = LearnedPolicy(endpoint, config['catalog'])
    if state['status'] != 'complete' or state['trained_rollout_transitions'] != 4096 or optimizer_steps(restored.model) <= initial_steps:
        raise AssertionError('foundation_checkpoint_resume_failed')
    atomic_json(output / 'smoke_result.json', {
        'stopped': stopped, 'resumed': state, 'wall_seconds': perf_counter() - started,
        'resources': job.usage(), 'endpoint': str(endpoint), 'endpoint_sha256': restored.model_id,
        'first_optimizer_steps': initial_steps, 'final_optimizer_steps': optimizer_steps(restored.model),
        'resume_scope': 'exact_model_Adam_state_fresh_native_episodes_and_partial_rollout_discard',
        'strength_claim': False, 'long_training_started': False})
    print(json.dumps({'status': state['status'], 'trained_transitions': state['trained_rollout_transitions'],
                      'ended_episodes': state['completed_battles'], 'resources': job.usage()}), flush=True)


class FrozenReadinessCases:
    def __init__(self, path, identity):
        if digest(path) != identity:
            raise ValueError('foundation_final_panel_changed')
        self.cases = json.loads(path.read_text())['cases']
        self.identity = {'sha256': identity, 'scope': 'one_time_engineering_readiness'}

    def __call__(self, split, index):
        if split != 'test' or not 0 <= index < len(self.cases):
            raise ValueError('foundation_final_panel_bounds')
        return deepcopy(self.cases[index])


def assess(output):
    frozen, config = require_freeze(output)
    consumed = output / 'FINAL_PANEL_CONSUMED.json'
    if consumed.exists():
        raise ValueError('foundation_final_assessment_already_consumed')
    smoke_result = json.loads((output / 'smoke_result.json').read_text())
    player = LearnedPolicy(smoke_result['endpoint'], config['catalog'], expected_model_id=smoke_result['endpoint_sha256'])
    rivals = {'max_power': 'max_power', 'tactical_heuristic': 'tactical_heuristic',
        'V4': LearnedPolicy(config['experiments'][0]['frozen_opponents']['league_s0'], config['catalog'],
            expected_model_id=config['experiments'][0]['frozen_opponent_ids']['league_s0']),
        'league_anchor': LearnedPolicy(config['experiments'][0]['frozen_opponents']['league_anchor'], config['catalog'],
            expected_model_id=config['experiments'][0]['frozen_opponent_ids']['league_anchor'])}
    cases = FrozenReadinessCases(output / 'final_readiness_cases.json', frozen['final_panel_sha256'])
    atomic_json(consumed, {'model_sha256': player.model_id, 'panel_sha256': frozen['final_panel_sha256'],
                          'source_sha256': frozen['source_sha256'], 'status': 'started_do_not_reuse_for_tuning'})
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=12)
    budget = RuntimeLimit(output, 600)
    results = {}
    try:
        for seat in ('p1', 'p2'):
            results[seat] = evaluate(config['checkout'], config['catalog'], {'foundation': player}, split='test',
                cases=16, offset=0, curriculum_version=config['curriculum_version'], rivals=rivals,
                case_provider=cases, candidate_seat=seat, integrated_diagnostics=True, tactical_diagnostics=True,
                stopping=budget.stopping)
            atomic_json(output / ('final_readiness_' + seat + '.json'), results[seat])
    finally:
        budget.finished.set()
    records = [row for result in results.values() for row in result['records']]
    atomic_json(consumed, {'model_sha256': player.model_id, 'panel_sha256': frozen['final_panel_sha256'],
        'status': 'complete', 'battles': len(records), 'resources': job.usage(), 'strength_claim': False,
        'truncations': sum(row['truncated'] for row in records),
        'native_rejections': sum(row['native_choice_rejections'] for row in records)})
    print(json.dumps(json.loads(consumed.read_text())), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'smoke', 'assess'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference-config', type=Path)
    parser.add_argument('--initialization', choices=['v4', 'scratch'], default='v4')
    parser.add_argument('--pretrained-model', type=Path)
    parser.add_argument('--pretrained-id')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error('foundation model/evidence output must remain outside the repository')
    if args.phase == 'prepare':
        if args.reference_config is None:
            parser.error('prepare requires --reference-config with verified local resource/artifact paths')
        if args.initialization == 'v4' and (args.pretrained_model is None or args.pretrained_id is None):
            parser.error('V4 initialization requires an explicit categorical V4 path and SHA256')
        prepare(args.reference_config, output, args.initialization, args.pretrained_model, args.pretrained_id)
    elif args.phase == 'smoke':
        smoke(output)
    else:
        assess(output)


if __name__ == '__main__':
    main()
