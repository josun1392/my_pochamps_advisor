"""Frozen move-slot consistency study using the established native owner."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from advisor import learned_anchor_study as paired
from advisor.learned_execution_alignment import digest
from advisor.learned_move_slot_consistency import consistency_contract
from advisor.learned_ppo_contract_audit import VERSION as AUDIT_VERSION

VERSION = 'foundation-move-slot-equivariance-matched-PPO-v1'
SEEDS = (116021, 117037)
POLICIES = ('parent', *(f'{a}_{s}' for s in SEEDS for a in ('A', 'B')))
RIVALS = paired.RIVALS
EVALUATION_SECONDS, OVERALL_SECONDS = 5400, 10800
TRAINING_SECONDS = 5400  # Four bounded arms combined; each trainer retains its own ceiling.


def validate_detached_owner(plan, job):
    """Retain the default fail-closed guard; opt in only with fresh OS evidence.

    As in the accepted diverse/recombination pilots, a persistent outer app Job
    can survive the short-lived tool Job. Our own nested Job remains mandatory.
    This does not launch through the desktop or weaken CPU/RAM containment.
    """
    import sys
    proof_path = plan.get('detached_survival_proof')
    launcher_path = plan.get('detached_probe_launcher_receipt')
    if (not proof_path or not launcher_path or digest(proof_path) != plan.get('detached_survival_proof_sha256')
            or digest(launcher_path) != plan.get('detached_probe_launcher_receipt_sha256')):
        raise RuntimeError('move_slot_detached_proof_missing_or_changed')
    proof = json.loads(Path(proof_path).read_text())
    launch = json.loads(Path(launcher_path).read_text())
    if (proof.get('phase') != 'survived_launcher_exit' or proof.get('PID') != launch.get('probe_PID')
            or proof.get('inherited_job') != job.inherited_job
            or proof.get('completed_unix', 0) - launch.get('launcher_exit_unix', 0) < 7.5
            or Path(proof.get('executable', '')).resolve() != Path(sys.executable).resolve()
            or launch.get('training') != 0 or launch.get('native') != 0):
        raise RuntimeError('move_slot_detached_lifetime_or_runtime_not_proven')
    return {'path': proof_path, 'sha256': plan['detached_survival_proof_sha256'],
        'persistent_outer_job': job.inherited_job, 'own_nested_CPU_RAM_job_required': True}


def matched_configs(configs, parent_sha):
    if set(configs) != set(POLICIES[1:]):
        raise ValueError('move_slot_four_matched_arms_required')
    common = None
    for key, original in configs.items():
        c = deepcopy(original)
        if (c.get('envs') != 4 or c.get('cpu_percent') != 50 or c.get('memory_mib') != 12288
                or c.get('device') != 'cpu' or c.get('vector_backend') != 'subproc'
                or c.get('transition_budget_scope') != 'trained_rollouts_v1'
                or c.get('checkpoint_evaluation_mode') != 'disabled_for_frozen_study_v1'
                or c.get('validation_selection_mode') != 'diagnostic_fixed_budget_v1'
                or c.get('final_test_cases', 0) or c.get('checkpoint_steps') != 16384
                or c.get('ppo_update_audit') != AUDIT_VERSION or len(c['experiments']) != 1):
            raise ValueError('move_slot_resource_or_evaluation_mismatch')
        e = c['experiments'][0]
        if (e.pop('name') != key or e.pop('seed') != int(key[2:]) or e.get('steps') != 65536
                or e.get('initial_model_id') != parent_sha or e.get('fresh_optimizer') is not False
                or e.pop('move_slot_consistency', None) != (consistency_contract() if key.startswith('B') else None)
                or any(e.get(k) for k in ('actor_set_context', 'parent_policy_anchor', 'masked_temperature',
                    'opponent_schedule', 'transfer_model', 'offline', 'warmstart_decisions'))):
            raise ValueError('move_slot_initialization_or_objective_mismatch')
        if common is None:
            common = c
        elif c != common:
            raise ValueError('non_move_slot_matched_difference')
    return {'trained_transitions': 262144, 'per_arm': 65536, 'seeds': list(SEEDS),
        'only_variable': 'training_only_own_move_presentation_Jensen_Shannon_coefficient_0.01',
        'initialization': 'identical_original_Foundation_weights_and_restored_Adam', 'temperature': 1,
        'replications': 'two_continuations_of_one_trained_parent_not_fresh_initializations'}


def verify_plan(path):
    p = json.loads(Path(path).read_text(encoding='utf8'))
    if (p.get('schema_version') != VERSION or p.get('automatic_restarts') != 0
            or p.get('evaluation_games') != 5760 or p.get('training_seconds_ceiling') != TRAINING_SECONDS
            or p.get('evaluation_seconds_ceiling') != EVALUATION_SECONDS
            or p.get('overall_seconds_ceiling') != OVERALL_SECONDS):
        raise ValueError('invalid_move_slot_plan')
    for name, value in p['source_sha256'].items():
        if sha256((Path(p['source_root'])/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != value:
            raise ValueError('move_slot_source_changed:' + name)
    for name, value in p['immutable_files'].items():
        if digest(name) != value:
            raise ValueError('move_slot_input_changed:' + name)
    configs = {a['key']: json.loads(Path(a['config']).read_text()) for a in p['arms']}
    if matched_configs(configs, p['parent_sha256']) != p['training_contract']:
        raise ValueError('move_slot_config_changed')
    cases = json.loads(Path(p['cases_path']).read_text())['cases']
    if (len(cases) != 192 or any(sum(c['scope'] == s for c in cases) != 96 for s in ('train', 'heldout'))
            or len({c['native_identity'] for c in cases}) != 192
            or len({h for c in cases for h in c['team_sha256'].values()}) != 384):
        raise ValueError('move_slot_case_panel_changed')
    return p, configs


def game_slots(cases):
    if any(c.get('sampled') for c in cases):
        raise ValueError('move_slot_evaluation_argmax_only')
    return paired.game_slots(cases, policies=POLICIES, rivals=RIVALS)


def verify_initial_checkpoint(path, key, plan, config):
    import numpy as np
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
    from advisor.learned_combat_foundation import FoundationCombatPPO
    from advisor.learned_move_slot_consistency import MoveSlotFoundationPPO
    a = LearnedPolicy(plan['parent_path'], config['catalog'], expected_model_id=plan['parent_sha256']).model
    b = LearnedPolicy(path, config['catalog']).model
    if (type(b) is not (MoveSlotFoundationPPO if key.startswith('B') else FoundationCombatPPO)
            or tensor_digest(a.policy.state_dict()) != tensor_digest(b.policy.state_dict())
            or optimizer_digest(a.policy) != optimizer_digest(b.policy) or optimizer_clock(b.policy) != 32768
            or a.num_timesteps != b.num_timesteps):
        raise ValueError('move_slot_initial_weights_or_Adam_mismatch')
    hyper = ('n_steps', 'batch_size', 'n_epochs', 'gamma', 'gae_lambda', 'learning_rate',
        'ent_coef', 'vf_coef', 'max_grad_norm', 'target_kl', 'zero_avoiding_beta')
    if any(getattr(a, k) != getattr(b, k) for k in hyper):
        raise ValueError('move_slot_initial_hyperparameters_mismatch')
    x = torch.as_tensor(np.load(plan['public_probe_features']));m = np.load(plan['public_probe_masks'])
    a.policy.set_training_mode(False);b.policy.set_training_mode(False)
    with torch.no_grad():
        for start in range(0, len(x), 32):
            batch, mask = x[start:start+32], m[start:start+32]
            aa = a.policy(batch, action_masks=mask, deterministic=True)
            da = a.policy.action_dist.distribution
            saved = [v.clone() for v in (*aa, da.logits, da.probs)]
            bb = b.policy(batch, action_masks=mask, deterministic=True)
            db = b.policy.action_dist.distribution
            if any(not torch.equal(v, w) for v, w in zip(saved, (*bb, db.logits, db.probs))):
                raise ValueError('move_slot_initial_outputs_not_bit_exact')
    return {'parameters_sha256': tensor_digest(b.policy.state_dict()), 'Adam_sha256': optimizer_digest(b.policy),
        'Adam_clock': 32768, 'public_views': len(x), 'initial_output_max_difference': 0,
        'old_parameters_and_named_Adam_bit_exact': True, 'checkpoint_SHA': digest(path)}


def endpoint_clock(key, metadata):
    clock = metadata['optimizer_steps']
    if (metadata.get('total_steps') != 1114112 or not 32768 < clock <= 34816
            or metadata.get('move_slot_consistency') != (consistency_contract() if key.startswith('B') else None)
            or (key.startswith('B') and metadata.get('move_slot_trained') != 65536)
            or any(metadata.get(k) for k in ('actor_set_context', 'parent_policy_anchor', 'masked_temperature'))):
        raise ValueError('move_slot_endpoint_mismatch')
    return clock


def verify_sampling_checkpoint(path, config, trained):
    from advisor.learned_two_group_study import verify_sampling_checkpoint as verify
    m = json.loads(Path(path).with_suffix('.json').read_text())
    expected = config['experiments'][0].get('move_slot_consistency')
    if m.get('move_slot_consistency') != expected or (expected is not None and m.get('move_slot_trained') != trained):
        raise ValueError('move_slot_sampling_objective_or_progress')
    return verify(path, config, trained)


def evaluation_native_ids(cases):
    from advisor.learned_two_group_study import evaluation_native_ids as both
    return both(cases)


def evaluation_observer(output, slot):
    from advisor.learned_two_group_study import evaluation_observer as observe
    from advisor.learned_combat_foundation import FoundationCombatEncoder
    from advisor.learned_move_slot_consistency import transform, PERMUTATION
    from advisor.learned_execution_alignment import durable_json
    import numpy as np
    import torch
    guard = observe(output, slot)
    captured = False
    def record(event):
        nonlocal captured
        guard(event)
        # Predeclared deterministic sample, one eligible predecision per game.
        if captured or slot['case'] % 6:
            return
        view = event['before']['self' if slot['seat']=='p1' else 'opponent']
        encoder = FoundationCombatEncoder(Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json')
        x = torch.tensor(encoder.encode(view))[None]
        y, _, eligible = transform(x, torch.tensor(view['action_mask'])[None])
        if not eligible[0]:
            return
        changed = deepcopy(view)
        moves = changed['own_request']['active'][0]['moves']
        own = next(p for p in changed['own_request']['side']['pokemon'] if p.get('active'))
        if len(moves)!=4 or own['moves']!=[m['id'] for m in moves]:
            raise ValueError('move_slot_native_public_reconstruction_binding')
        changed['own_request']['active'][0]['moves'] = list(reversed(moves))
        own['moves'] = list(reversed(own['moves']))
        changed['action_mask'] = [view['action_mask'][i] for i in PERMUTATION]
        delta = float(np.max(abs(encoder.encode(changed)-y[0].numpy())))
        if delta > 2e-6 or changed['state'] != view['state'] or changed['public_history'] != view['public_history']:
            raise ValueError('move_slot_actual_native_seat_transform_mismatch')
        directory = Path(output)/'public_slot_evaluation_probes';directory.mkdir(exist_ok=True)
        durable_json(directory/(str(slot['policy'])+'_'+str(slot['case'])+'_'+slot['seat']+'_'+slot['rival']+'.json'),
            {'slot':slot,'public_observation':view,'public_reencoding_max_error':delta,
             'scope':'actual_own_player_predecision_view_no_other_player_request_no_training_use'})
        captured = True
    return record


def analyze(rows, cases, *, resamples=20000):
    result = paired.analyze(rows, cases, resamples=resamples, policies=POLICIES, seeds=SEEDS,
        arm_names=('A', 'B'), rivals=RIVALS)
    primary = next(d for d in result['paired_differences'] if d['scope']=='heldout'
        and d['rival']=='all' and d['comparison']=='mean_seed(B-A)')
    per_seed = [d for d in result['paired_differences'] if d['scope']=='heldout'
        and d['rival']=='all' and d['comparison'] in [f'B_{s}-A_{s}' for s in SEEDS]]
    result.update(primary='heldout_argmax_mean_seed(B-A)',
        conclusion='PROMISING_REQUIRES_INDEPENDENT_CONFIRMATION' if primary['case_cluster_95'][0]>0
        and all(d['delta']>0 for d in per_seed) else 'INCONCLUSIVE', no_promotion=True)
    return result
