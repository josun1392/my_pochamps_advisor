"""Opt-in minibatch statistics from decisions with multiple legal actions.

The pinned upstream train AST changes exactly one assignment. Its normalization
location, clipped loss, whole-batch reduction, value/entropy/auxiliary paths,
optimizer, and surrounding Foundation guards remain the maintained owners.

Runtime-derived upstream code: Copyright (c) 2020 Stable-Baselines Team.
MIT License: Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions: The above copyright notice and this
permission notice shall be included in all copies or substantial portions of the
Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import ast
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import importlib.metadata
import inspect
import json
import random
from pathlib import Path
import textwrap

import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.ppo_mask import ppo_mask

from advisor.experimental_context_training import (
    EXTRA, ResidualOnlyPolicy, ResidualOnlyExtractor, contract as actor_contract,
    initialize as actor_initialize, frozen_digest,
)
from advisor.experimental_critic_training import CriticSignalRecorder
from advisor.learned_combat_foundation import FoundationCombatPPO, FoundationCombatEncoder
from advisor.learned_execution_alignment import digest, durable_json
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_policy import LearnedPolicy

VERSION = 'experimental-actionable-decision-advantage-normalization-v1'
UPSTREAM_SHA = '8c1a18c11e10cd0b3f7990ff275e3d0e6032b573351a482e9ffa0a8fd1ffb9de'
ORIGINAL = '(advantages - advantages.mean()) / (advantages.std() + 1e-8)'


def contract():
    return {'version':VERSION,'upstream':'sb3-contrib-MaskablePPO-2.7.1',
        'upstream_train_SHA256':UPSTREAM_SHA,'statistics':'current_minibatch_legal_count_gt_1_only',
        'normalization':'same_mean_std_correction1_epsilon1e-8_at_upstream_assignment',
        'application':'all_minibatch_rows_same_clipped_policy_loss_mean_no_row_removal',
        'eligible_count_0_or_1':'all_normalized_advantages_zero_no_full_batch_fallback',
        'actor':'original_A_set_context_residual_only_4160_fresh_Adam',
        'other_parameters_GAE_rewards_masks_losses':'unchanged_frozen_Foundation',
        'temperature':1,'transitions':16384,'Adam_cap':512}


def normalized_advantages(advantages, action_masks):
    masks=torch.as_tensor(action_masks,device=advantages.device)
    if (advantages.ndim!=1 or masks.shape!=(len(advantages),35)
            or not torch.isfinite(advantages).all() or advantages.requires_grad
            or not torch.all((masks==0)|(masks==1)) or not masks.bool().any(1).all()):
        raise ValueError('actionable_advantage_input_contract')
    eligible=masks.sum(1)>1;n=int(eligible.sum())
    # No variance estimate is available with <2 actionable samples. This explicit
    # zero signal affects only the policy surrogate; rows/other losses stay put.
    result=((advantages-advantages[eligible].mean())/(advantages[eligible].std()+1e-8)
            if n>=2 else torch.zeros_like(advantages))
    if not torch.isfinite(result).all():
        raise ValueError('nonfinite_actionable_normalization')
    return result,eligible


def train_trees():
    source=textwrap.dedent(inspect.getsource(MaskablePPO.train))
    if importlib.metadata.version('sb3-contrib')!='2.7.1' or sha256(source.encode()).hexdigest()!=UPSTREAM_SHA:
        raise ValueError('actionable_normalization_unpinned_upstream')
    original=ast.parse(source);modified=deepcopy(original)
    expression=ast.dump(ast.parse(ORIGINAL,mode='eval').body,include_attributes=False)
    count=0
    for node in ast.walk(modified):
        if (isinstance(node,ast.Assign) and len(node.targets)==1
                and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='advantages'
                and ast.dump(node.value,include_attributes=False)==expression):
            node.value=ast.parse('self._normalize_actionable_advantage(advantages, rollout_data)',mode='eval').body
            count+=1
    if count!=1:raise ValueError('actionable_normalization_patch_not_unique')
    return original,ast.fix_missing_locations(modified)


def _patched_train():
    _,tree=train_trees();namespace=dict(ppo_mask.__dict__)
    exec(compile(tree,'<pinned-MaskablePPO-actionable-normalization>','exec'),namespace)
    return namespace['train']


class _ActionableMaskablePPO(MaskablePPO):
    train=_patched_train()


class ActionableFoundationPPO(FoundationCombatPPO,_ActionableMaskablePPO):
    def _excluded_save_params(self):
        return super()._excluded_save_params()+['_normalization_records']

    def _normalize_actionable_advantage(self, advantages, batch):
        result,eligible=normalized_advantages(advantages,batch.action_masks)
        old=(advantages-advantages.mean())/(advantages.std()+1e-8)
        n=int(eligible.sum())
        self._normalization_records.append({'index':len(self._normalization_records),'rows':len(advantages),
            'eligible':n,'forced':len(advantages)-n,'raw_advantages':advantages.detach().cpu().tolist(),
            'normalized_advantages':result.detach().cpu().tolist(),'eligible_flags':eligible.cpu().tolist(),
            'actions':batch.actions.flatten().cpu().tolist(),'old_logp':batch.old_log_prob.cpu().tolist(),
            'full_mean':float(advantages.mean()),'full_std':float(advantages.std()),
            'eligible_mean':float(advantages[eligible].mean()) if n else None,
            'eligible_std':float(advantages[eligible].std()) if n>=2 else None,
            'max_actionable_difference':float((result-old)[eligible].abs().max()) if n else 0.,
            'actionable_sign_changes':int((result[eligible].sign()!=old[eligible].sign()).sum())})
        return result

    def train(self):
        validate_model(self)
        self._normalization_records=[]
        super().train()  # Same Foundation/aux/KL stack, then patched one assignment.
        if not self._normalization_records:raise ValueError('actionable_normalization_not_executed')
        self.logger.record('train/actionable_normalization_batches',len(self._normalization_records))
        self.logger.record('train/actionable_rows_mean',float(np.mean([r['eligible'] for r in self._normalization_records])))


def allowed(name):
    return name in EXTRA


def validate_model(model, frozen=None):
    p=model.policy
    if (type(model) is not ActionableFoundationPPO or model.actionable_advantage_contract!=contract()
            or not model.normalize_advantage or type(p) is not ResidualOnlyPolicy or p.context_mode!='set'
            or type(p.mlp_extractor) is not ResidualOnlyExtractor or p.mlp_extractor.mode!='set'
            or model.experimental_context_contract!=actor_contract('set')
            or {n for n,v in p.named_parameters() if v.requires_grad}!=EXTRA
            or any(v.grad is not None for n,v in p.named_parameters() if n not in EXTRA)
            or len(p.optimizer.param_groups)!=1 or {id(v) for v in p.optimizer.param_groups[0]['params']}
                != {id(v) for n,v in p.named_parameters() if n in EXTRA}
            or (model.n_steps,model.batch_size,model.n_epochs)!=(128,128,4)
            or (model.gamma,model.gae_lambda,model.ent_coef,model.vf_coef,model.max_grad_norm)!=(1.,.95,.01,.5,.5)
            or model.target_kl!=.03 or model.zero_avoiding_beta!=.001 or model.device.type!='cpu'
            or p.optimizer.param_groups[0]['lr']!=5e-5 or model.action_space.n!=35
            or model.observation_space.shape!=(28822,) or getattr(model,'masked_temperature',None)
            or getattr(model,'parent_policy_anchor',None)):
        raise ValueError('actionable_normalization_model_contract')
    if frozen is not None and frozen_digest(p)!=frozen:raise ValueError('actionable_frozen_Foundation_mutated')
    if any(not torch.isfinite(v).all() for v in p.parameters()):raise ValueError('actionable_nonfinite_parameter')
    return True


def initialize(source):
    model=actor_initialize(source,'set')
    model.__class__=ActionableFoundationPPO
    model.actionable_advantage_contract=contract()
    validate_model(model)
    if model.policy.optimizer.state:raise ValueError('actionable_Adam_not_fresh')
    return model


def save(model,encoder,directory,provenance):
    validate_model(model);directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    path=directory/'actionable_model.zip';model.save(path)
    durable_json(directory/'actionable_metadata.json',{'version':VERSION,'contract':contract(),
        'model_SHA256':digest(path),'frozen_SHA256':frozen_digest(model.policy),
        'parameters_SHA256':tensor_digest(model.policy.state_dict()),'optimizer_SHA256':optimizer_digest(model.policy),
        'Adam_step':optimizer_clock(model.policy),'encoder_fingerprint':encoder.catalog_fingerprint,'provenance':provenance})
    return str(path)


@contextmanager
def isolated_loader_rng():
    """A verification load must not reseed the live learner's generators."""
    numpy_state,python_state=np.random.get_state(),random.getstate()
    with torch.random.fork_rng(devices=[]):
        try:
            yield
        finally:
            np.random.set_state(numpy_state);random.setstate(python_state)


class ActionableActor(LearnedPolicy):
    @isolated_loader_rng()
    def __init__(self,path,catalog):
        path=Path(path);meta=json.loads((path.parent/'actionable_metadata.json').read_text(encoding='utf-8'))
        if meta['version']!=VERSION or meta['contract']!=contract() or digest(path)!=meta['model_SHA256']:
            raise ValueError('actionable_checkpoint_identity')
        self.encoder=FoundationCombatEncoder(catalog)
        if self.encoder.catalog_fingerprint!=meta['encoder_fingerprint']:raise ValueError('actionable_encoder_identity')
        self.model=ActionableFoundationPPO.load(path,device='cpu');validate_model(self.model,meta['frozen_SHA256'])
        if (tensor_digest(self.model.policy.state_dict())!=meta['parameters_SHA256']
                or optimizer_digest(self.model.policy)!=meta['optimizer_SHA256'] or optimizer_clock(self.model.policy)!=meta['Adam_step']):
            raise ValueError('actionable_optimizer_reload')
        self.model.policy.set_training_mode(False);self.model_id=meta['model_SHA256']
        self.metadata={'combat_foundation':True,'actionable_advantage':meta}

    def infer(self,observation):
        from advisor.learned_response_predictor import public_input
        public_input(observation)
        return super().infer(observation)


class ActionableSignalRecorder(CriticSignalRecorder):
    def settled(self,clock,model=None):
        if self.active is not None:
            records=model._normalization_records
            audit=self.active[1]
            if len(records)!=len(audit['minibatches']):raise ValueError('actionable_minibatch_audit_count')
            for a,b in zip(records,audit['minibatches']):
                if a['old_logp']!=b['old_logp'] or a['actions']!=b['actions']:
                    raise ValueError('actionable_minibatch_order_binding')
            durable_json(self.directory/(self.pending[0]+'.normalization.json'),{
                'contract':contract(),'model_timesteps_end':model.num_timesteps,'Adam_after':clock,'minibatches':records})
        super().settled(clock,model)


# Explicit adapter for the existing bounded segment/checkpoint owner.
Actor=ActionableActor
Recorder=ActionableSignalRecorder
