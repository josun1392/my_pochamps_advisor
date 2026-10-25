"""Matched legal-set residual study; native runner/statistics remain shared owners."""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import json
from advisor import learned_anchor_study as paired
from advisor.learned_execution_alignment import digest
from advisor.learned_legal_set_context import legal_set_context_contract, legal_set_training_contract
from advisor.learned_ppo_contract_audit import VERSION as AUDIT_VERSION

VERSION='foundation-legal-action-set-residual-matched-PPO-v1'
SEEDS=(113021,114037)
POLICIES=('parent',*(f'{a}_{s}' for s in SEEDS for a in ('A','B')))
RIVALS=paired.RIVALS
EVALUATION_SECONDS=5400
OVERALL_SECONDS=10800


def matched_configs(configs,parent_sha):
    if set(configs)!=set(POLICIES[1:]):raise ValueError('legal_set_four_paired_arms_required')
    common=None
    for key,config in configs.items():
        c=deepcopy(config)
        if (c.get('envs')!=4 or c.get('cpu_percent')!=50 or c.get('memory_mib')!=12288 or c.get('device')!='cpu'
            or c.get('vector_backend')!='subproc' or c.get('transition_budget_scope')!='trained_rollouts_v1'
            or c.get('checkpoint_evaluation_mode')!='disabled_for_frozen_study_v1'
            or c.get('validation_selection_mode')!='diagnostic_fixed_budget_v1' or c.get('final_test_cases',0)
            or c.get('checkpoint_steps')!=16384 or c.get('ppo_update_audit')!=AUDIT_VERSION or len(c['experiments'])!=1):
            raise ValueError('legal_set_resources_or_budget_mismatch')
        e=c['experiments'][0]
        if (e.pop('name')!=key or e.pop('seed')!=int(key[2:]) or e.get('steps')!=65536
            or e.get('initial_model_id')!=parent_sha or e.get('fresh_optimizer') is not False
            or any(e.get(k) for k in ('parent_policy_anchor','masked_temperature','opponent_schedule','transfer_model','offline','warmstart_decisions'))):
            raise ValueError('legal_set_initialization_or_objective_mismatch')
        expected=legal_set_context_contract() if key.startswith('B') else None
        train=legal_set_training_contract() if key.startswith('B') else None
        if e.pop('actor_set_context',None)!=expected or e.pop('legal_set_training',None)!=train:
            raise ValueError('legal_set_architecture_opt_in_mismatch')
        if common is None:common=c
        elif common!=c:raise ValueError('non_legal_set_matched_difference')
    return {'trained_transitions':262144,'per_arm':65536,'seeds':list(SEEDS),'only_variable':'legal_candidate_set_zero_residual_actor_path',
        'initialization':'same_parent_old_weights_named_Adam_new_B_states_empty','temperature':1,
        'replications':'two_stochastic_continuations_of_one_trained_parent_not_fresh_initializations'}


def game_slots(cases):
    if any(c.get('sampled') for c in cases):raise ValueError('legal_set_argmax_only')
    return paired.game_slots(cases,policies=POLICIES,rivals=RIVALS)


def verify_plan(path):
    p=json.loads(Path(path).read_text(encoding='utf8'))
    if (p.get('schema_version')!=VERSION or p.get('automatic_restarts')!=0 or p.get('evaluation_games')!=5760
        or p.get('training_seconds_ceiling')!=3600 or p.get('evaluation_seconds_ceiling')!=EVALUATION_SECONDS
        or p.get('overall_seconds_ceiling')!=OVERALL_SECONDS):raise ValueError('invalid_legal_set_study')
    for name,s in p['source_sha256'].items():
        if sha256((Path(p['source_root'])/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=s:raise ValueError('legal_set_source_changed:'+name)
    for name,s in p['immutable_files'].items():
        if digest(name)!=s:raise ValueError('legal_set_input_changed:'+name)
    configs={a['key']:json.loads(Path(a['config']).read_text()) for a in p['arms']}
    if matched_configs(configs,p['parent_sha256'])!=p['training_contract']:raise ValueError('legal_set_config_changed')
    cases=json.loads(Path(p['cases_path']).read_text())['cases']
    if (len(cases)!=192 or any(sum(c['scope']==s for c in cases)!=96 for s in ('train','heldout'))
        or len(game_slots(cases))!=5760 or len({c['native_identity'] for c in cases})!=192
        or len({h for c in cases for h in c['team_sha256'].values()})!=384):raise ValueError('legal_set_frozen_panel_mismatch')
    return p,configs


def verify_initial_checkpoint(path,key,plan,config):
    import torch,numpy as np
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest,optimizer_clock
    from advisor.learned_combat_foundation import FoundationCombatPolicy
    from advisor.learned_legal_set_context import LegalSetContextFoundationPolicy
    a=LearnedPolicy(plan['parent_path'],config['catalog'],expected_model_id=plan['parent_sha256']).model
    b=LearnedPolicy(path,config['catalog']).model
    if type(b.policy) is not (LegalSetContextFoundationPolicy if key.startswith('B') else FoundationCombatPolicy):raise ValueError('legal_set_initial_policy_class')
    old,new=dict(a.policy.named_parameters()),dict(b.policy.named_parameters())
    for name,param in old.items():
        if param.detach().numpy().tobytes()!=new[name].detach().numpy().tobytes():raise ValueError('legal_set_initial_weight_mismatch:'+name)
        left,right=a.policy.optimizer.state.get(param,{}),b.policy.optimizer.state.get(new[name],{})
        if left.keys()!=right.keys():raise ValueError('legal_set_initial_Adam_keys')
        for k,value in left.items():
            if (value.detach().numpy().tobytes()!=right[k].detach().numpy().tobytes() if torch.is_tensor(value) else value!=right[k]):raise ValueError('legal_set_initial_Adam_mismatch:'+name)
    for name in set(new)-set(old):
        if new[name].detach().count_nonzero() or b.policy.optimizer.state.get(new[name]):raise ValueError('legal_set_new_path_not_zero_empty')
    for k,v in a.policy.optimizer.param_groups[0].items():
        if k!='params' and v!=b.policy.optimizer.param_groups[0][k]:raise ValueError('legal_set_Adam_options')
    hyper={'n_steps':128,'batch_size':128,'n_epochs':4,'n_envs':4,'gamma':1.,'gae_lambda':.95,'learning_rate':5e-5,
           'ent_coef':.01,'vf_coef':.5,'max_grad_norm':.5,'target_kl':.03,'zero_avoiding_beta':.001}
    if any(getattr(a,k)!=v or getattr(b,k)!=v for k,v in hyper.items()) or optimizer_clock(b.policy)!=32768 or a.num_timesteps!=b.num_timesteps:raise ValueError('legal_set_initial_PPO_or_clock_mismatch')
    x=torch.as_tensor(np.load(plan['public_probe_features']));m=np.load(plan['public_probe_masks'])
    a.policy.set_training_mode(False);b.policy.set_training_mode(False)
    with torch.no_grad():
        for start in range(0,len(x),32):
            args=x[start:start+32];mask=m[start:start+32]
            aa=a.policy(args,action_masks=mask,deterministic=True);da=a.policy.action_dist.distribution
            saved=[v.clone() for v in (*aa,da.logits,da.probs)]
            bb=b.policy(args,action_masks=mask,deterministic=True);db=b.policy.action_dist.distribution
            for left,right in zip(saved,(*bb,db.logits,db.probs)):
                if left.numpy().tobytes()!=right.numpy().tobytes():raise ValueError('legal_set_initial_output_not_bit_exact')
    return {'parameters_sha256':tensor_digest(b.policy.state_dict()),'Adam_sha256':optimizer_digest(b.policy),
            'old_parameters_and_named_Adam_bit_exact':True,'new_residual_zero_empty':key.startswith('B'),
            'Adam_clock':32768,'public_views':len(x),'initial_output_max_difference':0,'checkpoint_SHA':digest(path),'hyper':hyper}


def checkpoint_integrity(path,expected_sha,expected_clock):
    import torch,zipfile
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import optimizer_clock
    from scripts.run_foundation_parent_anchor_study import checkpoint_integrity as original
    meta=json.loads(Path(path).with_suffix('.json').read_text())
    if 'actor_set_context' not in meta:return original(path,expected_sha,expected_clock)
    if digest(path)!=expected_sha:raise ValueError('legal_set_checkpoint_SHA')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('legal_set_checkpoint_CRC')
    root=Path(__file__).resolve().parents[1]
    b=LearnedPolicy(path,root/'models/showdown_mc_domain_v1/catalog.json').model.policy
    clocks={}
    for name,param in b.named_parameters():
        if not torch.isfinite(param).all():raise ValueError('legal_set_nonfinite_parameter')
        state=b.optimizer.state.get(param,{})
        if any(torch.is_tensor(v) and not torch.isfinite(v).all() for v in state.values()):raise ValueError('legal_set_nonfinite_Adam')
        if 'step' in state:
            clock=int(state['step']);expected=expected_clock-32768 if 'legal_set_residual' in name else expected_clock
            if clock!=expected:raise ValueError('legal_set_named_Adam_step_mismatch:'+name)
            clocks[name]=clock
    if optimizer_clock(b)!=expected_clock:raise ValueError('legal_set_Adam_max_clock')
    return {'sha256':expected_sha,'CRC':'pass','policy_Adam_finite':True,'Adam':expected_clock,'residual_Adam':expected_clock-32768,'named_steps_verified':len(clocks)}


def endpoint_clock(key,metadata):
    clock=metadata['optimizer_steps']
    if (metadata.get('total_steps')!=1114112 or not 32768<clock<=34816 or metadata.get('masked_temperature') is not None
        or metadata.get('parent_policy_anchor') is not None or ('actor_set_context' in metadata)!=key.startswith('B')):raise ValueError('legal_set_endpoint_mismatch')
    return clock


def verify_sampling_checkpoint(path,config,trained):
    from advisor.learned_two_group_study import verify_sampling_checkpoint as verify
    return verify(path,config,trained)


def evaluation_native_ids(cases):
    from advisor.learned_two_group_study import evaluation_native_ids as both
    return both(cases)


def evaluation_observer(output,slot):
    from advisor.learned_two_group_study import evaluation_observer as observe
    return observe(output,slot)


def analyze(rows,cases,*,resamples=20000):
    result=paired.analyze(rows,cases,resamples=resamples,policies=POLICIES,seeds=SEEDS,arm_names=('A','B'),rivals=RIVALS)
    primary=next(d for d in result['paired_differences'] if d['scope']=='heldout' and d['rival']=='all' and d['comparison']=='mean_seed(B-A)')
    seeds=[next(d for d in result['paired_differences'] if d['scope']=='heldout' and d['rival']=='all' and d['comparison']==f'B_{s}-A_{s}') for s in SEEDS]
    result.update(primary='heldout-team T1 argmax mean_seed(B-A)',sampling='none_all_argmax_T1',
        uncertainty='unique_complete_teams_per_case_cluster_both_seats_rivals_and_two_continuations_retained_not_seed_population_CI',
        conclusion='CANDIDATE_FOR_LARGER_INDEPENDENT_VALIDATION' if primary['case_cluster_95'][0]>0 and all(d['delta']>0 for d in seeds) else 'NO_EVIDENCE_OF_IMPROVEMENT')
    return result
