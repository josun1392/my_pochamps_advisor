"""Matched public-potential reward adapter; reuse the maintained training/evaluation owner."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import numpy as np

from advisor import learned_anchor_study as paired
from advisor.learned_execution_alignment import digest
from advisor.learned_potential_ppo import RECORDER_VERSION
from advisor.learned_public_potential import potential_contract
from advisor.learned_move_slot_study import validate_detached_owner
from advisor.learned_ppo_contract_audit import VERSION as AUDIT_VERSION

VERSION = 'foundation-public-faint-potential-matched-PPO-v1'
SEEDS = (128021, 129037)
POLICIES = ('parent', *(f'{a}_{s}' for s in SEEDS for a in ('A', 'B')))
RIVALS = paired.RIVALS
TRAINING_SECONDS, EVALUATION_SECONDS, OVERALL_SECONDS = 5400, 5400, 10800


def matched_configs(configs, parent_sha):
    if set(configs) != set(POLICIES[1:]):
        raise ValueError('potential_four_matched_arms_required')
    common = None
    for key, value in configs.items():
        c = deepcopy(value)
        reference = c.pop('potential_first_rollout_reference', None)
        if (c.get('envs') != 4 or c.get('cpu_percent') != 50 or c.get('memory_mib') != 12288
                or c.get('device') != 'cpu' or c.get('vector_backend') != 'subproc'
                or c.get('transition_budget_scope') != 'trained_rollouts_v1'
                or c.get('checkpoint_evaluation_mode') != 'disabled_for_frozen_study_v1'
                or c.get('checkpoint_steps') != 16384 or c.get('final_test_cases', 0)
                or c.get('ppo_update_audit') != AUDIT_VERSION
                or c.get('potential_matched_rollout') != RECORDER_VERSION or len(c['experiments']) != 1):
            raise ValueError('potential_resource_or_audit_mismatch')
        e = c['experiments'][0]
        if (e.pop('name') != key or e.pop('seed') != int(key[2:]) or e.get('steps') != 65536
                or e.get('initial_model_id') != parent_sha or e.get('fresh_optimizer') is not False
                or e.get('gae_lambda') != .95
                or e.pop('objective') != ('native_terminal_public_faint_potential_v1' if key.startswith('B') else 'native_terminal_win_loss_draw_undiscounted_v1')
                or e.pop('public_potential_reward', None) != (potential_contract() if key.startswith('B') else None)
                or bool(reference) != key.startswith('B')
                or any(e.get(k) for k in ('move_slot_consistency', 'actor_set_context', 'parent_policy_anchor',
                    'masked_temperature', 'opponent_schedule', 'transfer_model', 'offline', 'warmstart_decisions', 'gae_lambda_experiment'))):
            raise ValueError('potential_initialization_or_objective_mismatch')
        if common is None:
            common = c
        elif c != common:
            raise ValueError('non_potential_matched_training_difference')
    return {'trained_transitions': 262144, 'per_arm': 65536, 'max_new_Adam': 8192,
        'seeds': list(SEEDS), 'only_variable': 'public_faint_progress_potential_reward_only_raw_initial_critic_unchanged',
        'initialization': 'identical_original_Foundation_weights_and_restored_Adam',
        'temperature': 1, 'replications': 'two_continuations_of_one_trained_parent'}


def verify_plan(path):
    p = json.loads(Path(path).read_text(encoding='utf8'))
    if (p.get('schema_version') != VERSION or p.get('automatic_restarts') != 0
            or p.get('evaluation_games') != 5760 or p.get('training_seconds_ceiling') != TRAINING_SECONDS
            or p.get('evaluation_seconds_ceiling') != EVALUATION_SECONDS
            or p.get('overall_seconds_ceiling') != OVERALL_SECONDS):
        raise ValueError('invalid_potential_study_plan')
    for name, expected in p['source_sha256'].items():
        if sha256((Path(p['source_root'])/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('potential_study_source_changed:'+name)
    for name, expected in p['immutable_files'].items():
        if digest(name) != expected:
            raise ValueError('potential_study_input_changed:'+name)
    configs = {a['key']: json.loads(Path(a['config']).read_text()) for a in p['arms']}
    if matched_configs(configs, p['parent_sha256']) != p['training_contract']:
        raise ValueError('potential_study_config_changed')
    arms = {a['key']: a for a in p['arms']}
    for seed in SEEDS:
        if configs[f'B_{seed}']['potential_first_rollout_reference'] != str(Path(arms[f'A_{seed}']['run'])/'public_signal_joins'):
            raise ValueError('potential_first_rollout_reference_identity_mismatch')
    cases = json.loads(Path(p['cases_path']).read_text())['cases']
    if (len(cases) != 192 or any(sum(c['scope']==s for c in cases) != 96 for s in ('train','heldout'))
            or len({c['native_identity'] for c in cases}) != 192
            or len({h for c in cases for h in c['team_sha256'].values()}) != 384):
        raise ValueError('potential_frozen_case_panel_mismatch')
    return p, configs


def game_slots(cases):
    if any(c.get('sampled') for c in cases):
        raise ValueError('potential_argmax_evaluation_only')
    return paired.game_slots(cases, policies=POLICIES, rivals=RIVALS)


def verify_initial_checkpoint(path, key, plan, config):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
    from advisor.learned_combat_foundation import FoundationCombatPPO
    from advisor.learned_potential_ppo import PotentialFoundationPPO
    a = LearnedPolicy(plan['parent_path'], config['catalog'], expected_model_id=plan['parent_sha256']).model
    b = LearnedPolicy(path, config['catalog']).model
    if (type(b) is not (PotentialFoundationPPO if key.startswith('B') else FoundationCombatPPO)
            or tensor_digest(a.policy.state_dict()) != tensor_digest(b.policy.state_dict())
            or optimizer_digest(a.policy) != optimizer_digest(b.policy) or optimizer_clock(b.policy) != 32768
            or a.num_timesteps != b.num_timesteps or b.gae_lambda != .95):
        raise ValueError('potential_initial_weights_Adam_or_algorithm_mismatch')
    hyper = ('n_steps','batch_size','n_epochs','gamma','learning_rate','ent_coef','vf_coef',
        'max_grad_norm','target_kl','zero_avoiding_beta','clip_range_vf','normalize_advantage')
    if any(getattr(a,k) != getattr(b,k) for k in hyper):
        raise ValueError('potential_non_lambda_initial_hyperparameter_difference')
    x = torch.as_tensor(np.load(plan['public_probe_features']));m = np.load(plan['public_probe_masks'])
    a.policy.set_training_mode(False);b.policy.set_training_mode(False)
    with torch.no_grad():
        for start in range(0,len(x),32):
            batch, mask = x[start:start+32], m[start:start+32]
            aa = a.policy(batch,action_masks=mask,deterministic=True)
            d = a.policy.action_dist.distribution
            old = [v.clone() for v in (*aa,d.logits,d.probs)]
            bb = b.policy(batch,action_masks=mask,deterministic=True)
            d = b.policy.action_dist.distribution
            if any(not torch.equal(v,w) for v,w in zip(old,(*bb,d.logits,d.probs))):
                raise ValueError('potential_initial_policy_value_not_bit_exact')
    return {'parameters_sha256':tensor_digest(b.policy.state_dict()),'Adam_sha256':optimizer_digest(b.policy),
        'Adam_clock':32768,'public_views':len(x),'initial_output_max_difference':0,
        'old_parameters_and_named_Adam_bit_exact':True,'checkpoint_SHA':digest(path),'lambda':b.gae_lambda}


def endpoint_clock(key, metadata):
    clock = metadata['optimizer_steps']
    if (metadata.get('total_steps') != 1114112 or not 32768 < clock <= 34816
            or metadata.get('gae_lambda') != .95
            or metadata.get('public_potential_reward') != (potential_contract() if key.startswith('B') else None)
            or key.startswith('B') and metadata.get('public_potential_trained') != 65536
            or any(metadata.get(k) for k in ('move_slot_consistency','actor_set_context','parent_policy_anchor','masked_temperature'))):
        raise ValueError('potential_endpoint_identity_mismatch')
    return clock


def verify_sampling_checkpoint(path, config, trained):
    from advisor.learned_two_group_study import verify_sampling_checkpoint as verify
    m = json.loads(Path(path).with_suffix('.json').read_text())
    e = config['experiments'][0]
    if (m.get('public_potential_reward') != e.get('public_potential_reward')
            or m['gae_lambda'] != e['gae_lambda']
            or e.get('public_potential_reward') and m.get('public_potential_trained') != trained):
        raise ValueError('potential_sampling_checkpoint_objective_mismatch')
    return verify(path, config, trained)


def evaluation_native_ids(cases):
    from advisor.learned_two_group_study import evaluation_native_ids as both
    return both(cases)


def evaluation_observer(output, slot):
    from advisor.learned_two_group_study import evaluation_observer as observe
    return observe(output, slot)


def analyze(rows, cases, *, resamples=20000):
    result = paired.analyze(rows,cases,resamples=resamples,policies=POLICIES,seeds=SEEDS,
        arm_names=('A','B'),rivals=RIVALS)
    primary = next(d for d in result['paired_differences'] if d['scope']=='heldout'
        and d['rival']=='all' and d['comparison']=='mean_seed(B-A)')
    seeds = [d for d in result['paired_differences'] if d['scope']=='heldout' and d['rival']=='all'
        and d['comparison'] in [f'B_{s}-A_{s}' for s in SEEDS]]
    heldout = [r for r in rows if r['slot']['scope']=='heldout']
    clusters = sorted({r['slot']['case'] for r in heldout})
    draw = np.random.default_rng(2026102301).integers(len(clusters),size=(resamples,len(clusters)))
    def values(policy, seat=None):
        return np.array([np.mean([r['record']['winner']=='self' and not r['record']['truncated']
            for r in heldout if r['slot']['case']==c and r['slot']['policy']==policy
            and (seat is None or r['slot']['seat']==seat)]) for c in clusters])
    extra = []
    for arm in ('A','B'):
        delta = np.mean([values(f'{arm}_{s}') for s in SEEDS],axis=0)-values('parent')
        extra.append({'comparison':f'mean_seed({arm})-parent','delta':float(delta.mean()),
            'case_clusters':len(clusters),'case_cluster_95':np.quantile(delta[draw].mean(1),[.025,.975]).tolist()})
    seats = []
    for seat in ('p1','p2'):
        delta = np.mean([values(f'B_{s}',seat)-values(f'A_{s}',seat) for s in SEEDS],axis=0)
        seats.append({'seat':seat,'delta':float(delta.mean()),
            'case_cluster_95':np.quantile(delta[draw].mean(1),[.025,.975]).tolist()})
    rivals = [d for d in result['paired_differences'] if d['scope']=='heldout'
        and d['rival'] in RIVALS and d['comparison']=='mean_seed(B-A)']
    broad = all(d['delta']>0 for d in seats) and sum(d['delta']>0 for d in rivals)>=2
    result.update(primary='heldout_argmax_mean_seed(B-A)',
        conclusion='PROMISING_REQUIRES_INDEPENDENT_CONFIRMATION' if primary['case_cluster_95'][0]>0
        and len(seeds)==2 and all(d['delta']>0 for d in seeds)
        else 'NO_EVIDENCE_OF_IMPROVEMENT',heldout_mean_parent_comparisons=extra,heldout_seat_differences=seats,
        breadth_diagnostic='both_seats_and_at_least_two_of_three_rivals_positive',breadth_positive=broad,no_promotion=True)
    return result
