"""Explicit TRAIN-only residual pilot. Historical models/loaders stay unchanged."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatEncoder
from advisor.learned_legal_set_context import (
    LegalSetContextExtractor, LegalSetContextFoundationPolicy,
    extend_foundation_legal_set_context,
)
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_execution_alignment import digest, durable_json
from advisor.learned_policy import LearnedPolicy
from advisor.learned_fixed_micro import seed4

VERSION = "experimental-candidate-context-residual-only-PPO-v1"
SEEDS = (116051, 116053)
STEPS = 16384
ADAM_CAP = 512
EXTRA = {"mlp_extractor.legal_set_residual.weight", "mlp_extractor.legal_set_residual.bias"}


def contract(mode):
    if mode not in ("set", "local"):
        raise ValueError("experimental_context_mode")
    return {"version": VERSION, "mode": mode, "trainable_parameters": 4160,
            "parent": "frozen_Foundation_including_critic_and_prediction_heads",
            "optimizer": "fresh_Adam_residual_only_parent_Adam_never_updated",
            "PPO_reward_GAE_auxiliary_uniform_KL": "unchanged_parent",
            "temperature": 1, "transitions": STEPS, "Adam_cap": ADAM_CAP,
            "scope": "TRAIN_development_only_no_production_loader_or_promotion"}


class ResidualOnlyExtractor(LegalSetContextExtractor):
    def __init__(self, mode):
        contract(mode)
        self.mode = mode
        super().__init__()

    def _set_actor(self, context, actions, mask):
        if self.mode == "set":
            return super()._set_actor(context, actions, mask)
        # Same joint features/scorer/64x64 residual; only its input differs.
        shared = self.context(context)[:, None, :].expand(-1, 35, -1)
        hidden = torch.cat((shared, actions), dim=-1)
        for layer in tuple(self.scorer)[:-1]:
            hidden = layer(hidden)
        shifted = shared + self.legal_set_residual(hidden)
        return self.scorer(torch.cat((shifted, actions), dim=-1)).squeeze(-1)


class ResidualOnlyPolicy(LegalSetContextFoundationPolicy):
    def __init__(self, *args, context_mode, **kwargs):
        self.context_mode = context_mode
        contract(context_mode)
        super().__init__(*args, **kwargs)

    def _build_mlp_extractor(self):
        self.mlp_extractor = ResidualOnlyExtractor(self.context_mode)

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        for name, parameter in self.named_parameters():
            parameter.requires_grad_(name in EXTRA)
        # Executed again on SB3 reload; requires_grad flags are not serialized.
        self.optimizer = self.optimizer_class(
            self.mlp_extractor.legal_set_residual.parameters(),
            lr=lr_schedule(1.), **self.optimizer_kwargs)


def frozen_digest(policy):
    return tensor_digest({k: v for k, v in policy.state_dict().items() if k not in EXTRA})


def validate_model(model, mode, frozen=None):
    policy = model.policy
    if (type(model) is not FoundationCombatPPO or type(policy) is not ResidualOnlyPolicy
            or type(policy.mlp_extractor) is not ResidualOnlyExtractor
            or policy.context_mode != mode or policy.mlp_extractor.mode != mode
            or model.experimental_context_contract != contract(mode)
            or {n for n, p in policy.named_parameters() if p.requires_grad} != EXTRA
            or any(p.grad is not None for n, p in policy.named_parameters() if n not in EXTRA)
            or len(policy.optimizer.param_groups) != 1
            or {id(p) for p in policy.optimizer.param_groups[0]['params']}
                != {id(p) for n, p in policy.named_parameters() if n in EXTRA}
            or (model.n_steps, model.batch_size, model.n_epochs) != (128, 128, 4)
            or model.gamma != 1 or model.gae_lambda != .95
            or model.device.type != 'cpu' or model.observation_space.shape != (28822,)
            or model.action_space.n != 35 or getattr(model, 'masked_temperature', None)
            or getattr(model, 'parent_policy_anchor', None)):
        raise ValueError('experimental_residual_training_contract')
    if frozen is not None and frozen_digest(policy) != frozen:
        raise ValueError('experimental_frozen_Foundation_mutated')
    if any(not torch.isfinite(p).all() for p in policy.parameters()):
        raise ValueError('experimental_nonfinite_parameter')
    return True


def initialize(source, mode):
    """Use the maintained strict copy, then freeze its parent tensors forever."""
    if type(source) is not FoundationCombatPPO:
        raise ValueError('experimental_original_Foundation_required')
    before = tensor_digest(source.policy.state_dict()), optimizer_digest(source.policy)
    target = extend_foundation_legal_set_context(source)
    options = {**deepcopy(source.policy_kwargs), 'context_mode': mode}
    with torch.random.fork_rng(devices=[]):
        policy = ResidualOnlyPolicy(source.observation_space, source.action_space,
                                    source.lr_schedule, **options)
    policy.load_state_dict(target.policy.state_dict(), strict=True)
    policy.set_training_mode(False)
    target.policy, target.policy_class, target.policy_kwargs = policy, ResidualOnlyPolicy, options
    target.experimental_context_contract = contract(mode)
    assert before == (tensor_digest(source.policy.state_dict()), optimizer_digest(source.policy))
    validate_model(target, mode, before[0])
    if policy.optimizer.state:
        raise ValueError('experimental_residual_Adam_not_fresh')
    return target


def save(model, encoder, directory, provenance):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    mode = model.policy.context_mode
    validate_model(model, mode)
    path = directory / 'residual_model.zip'
    model.save(path)
    metadata = {'schema_version': VERSION, 'mode': mode, 'contract': contract(mode),
                'model_SHA256': digest(path), 'frozen_SHA256': frozen_digest(model.policy),
                'parameters_SHA256': tensor_digest(model.policy.state_dict()),
                'optimizer_SHA256': optimizer_digest(model.policy),
                'Adam_step': optimizer_clock(model.policy),
                'encoder_fingerprint': encoder.catalog_fingerprint, 'provenance': provenance}
    durable_json(directory / 'residual_metadata.json', metadata)
    return str(path)


class ResidualActor(LearnedPolicy):
    """Separate experimental loader; the historical LearnedPolicy rejects it."""
    def __init__(self, path, catalog):
        path = Path(path)
        metadata = json.loads((path.parent / 'residual_metadata.json').read_text(encoding='utf-8'))
        if metadata['schema_version'] != VERSION or digest(path) != metadata['model_SHA256']:
            raise ValueError('experimental_residual_checkpoint_identity')
        self.encoder = FoundationCombatEncoder(catalog)
        if self.encoder.catalog_fingerprint != metadata['encoder_fingerprint']:
            raise ValueError('experimental_residual_encoder_identity')
        self.model = FoundationCombatPPO.load(path, device='cpu')
        validate_model(self.model, metadata['mode'], metadata['frozen_SHA256'])
        if (metadata['contract'] != contract(metadata['mode'])
                or tensor_digest(self.model.policy.state_dict()) != metadata['parameters_SHA256']
                or optimizer_digest(self.model.policy) != metadata['optimizer_SHA256']
                or optimizer_clock(self.model.policy) != metadata['Adam_step']):
            raise ValueError('experimental_residual_optimizer_reload')
        self.model.policy.set_training_mode(False)
        self.model_id = metadata['model_SHA256']
        self.metadata = {'combat_foundation': True, 'experimental_context': metadata}

    def infer(self, observation):
        from advisor.learned_response_predictor import public_input
        public_input(observation)
        return super().infer(observation)


class TrainCases:
    def __init__(self, plan, seed, segment, worker):
        self.plan, self.seed, self.segment, self.worker = plan, seed, segment, worker
        self.template = (4 * segment + worker) % len(plan['training_templates'])
        self.identity = {'sha256': plan['case_identity'], 'segment': segment, 'worker': worker}
        self.contract = {'selection_mode': 'fixed_ordered_three_micro_v1'}

    def __call__(self, split, index):
        if split != 'train' or type(index) is not int or index < 0:
            raise ValueError('experimental_context_TRAIN_only')
        s = deepcopy(self.plan['training_templates'][self.template]['scenario'])
        name = f'{VERSION}:TRAIN:{self.seed}:{self.segment}:{self.worker}:{index}'
        s.update(scenario_id=name, seed=seed4(name))
        if tuple(s['seed']) in {tuple(x) for x in self.plan['excluded_native_seeds']}:
            raise ValueError('experimental_context_sealed_seed_collision')
        return s


def paired_development(records, cases, *, draws=20000, seed=116055):
    """Keep both owners/seats/RNG and both training repetitions in each pair."""
    models = ('A_s1', 'B_s1', 'A_s2', 'B_s2')
    by = {(r['policy'], r['case'], r['seat']): r['record'] for r in records}
    expected = {(m, c['index'], s) for m in models for c in cases for s in ('p1', 'p2')}
    if len(records) != len(expected) or set(by) != expected:
        raise ValueError('experimental_context_development_missing_or_duplicate')
    if any(r['truncated'] for r in by.values()):
        raise ValueError('experimental_context_nonterminal_development')
    pairs = sorted({c['pair'] for c in cases})
    means, outcomes = {}, {}
    for m in models:
        rows = [by[m, c['index'], s] for c in cases for s in ('p1', 'p2')]
        outcomes[m] = {'games': len(rows), 'wins': sum(r['winner']=='self' for r in rows),
                       'losses': sum(r['winner']=='opponent' for r in rows),
                       'draws': sum(r['winner'] is None for r in rows)}
        means[m] = np.array([np.mean([int(by[m,c['index'],s]['winner']=='self')
            -int(by[m,c['index'],s]['winner']=='opponent') for c in cases if c['pair']==p
            for s in ('p1','p2')]) for p in pairs])
    indices = np.random.default_rng(seed).integers(0,len(pairs),(draws,len(pairs)))
    contrasts = {}
    for key,d in [('s1',means['A_s1']-means['B_s1']),('s2',means['A_s2']-means['B_s2']),
                  ('two_seed_mean',(means['A_s1']+means['A_s2']-means['B_s1']-means['B_s2'])/2)]:
        contrasts[key] = {'A_minus_B_terminal_return':float(d.mean()),
                         'team_pair_cluster_95CI':np.quantile(d[indices].mean(1),[.025,.975]).tolist()}
    # Draws are possible: win differences are computed separately from returns.
    win_differences=[]
    for rep in (1,2):
        d=np.array([np.mean([int(by[f'A_s{rep}',c['index'],s]['winner']=='self')
            -int(by[f'B_s{rep}',c['index'],s]['winner']=='self') for c in cases if c['pair']==p
            for s in ('p1','p2')]) for p in pairs])
        contrasts[f's{rep}']['A_minus_B_win_fraction']=float(d.mean())
        contrasts[f's{rep}']['win_fraction_cluster_95CI']=np.quantile(d[indices].mean(1),[.025,.975]).tolist()
        win_differences.append(d)
    combined=np.mean(win_differences,axis=0)
    contrasts['two_seed_mean']['A_minus_B_win_fraction']=float(combined.mean())
    contrasts['two_seed_mean']['win_fraction_cluster_95CI']=np.quantile(combined[indices].mean(1),[.025,.975]).tolist()
    return {'outcomes':outcomes,'comparisons':contrasts,'TRAIN_domain_team_pair_clusters':len(pairs),
            'scope':'development_only_not_sealed_generalization_or_training_seed_population'}
