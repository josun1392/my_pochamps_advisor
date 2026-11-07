"""Opt-in 3:1 frozen-opponent treatment; original A learning is unchanged."""
from copy import deepcopy
import numpy as np

from advisor import experimental_context_training as original
from advisor.experimental_critic_training import CriticSignalRecorder
from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learned_train_opponents import VERSION as SAMPLER_VERSION, KEY, POLICIES, validate_manifest

VERSION = 'minority-stochastic-opponent-mix-controlled-ppo-v1'
SLOTS = ['foundation_argmax'] * 3 + ['foundation_masked_sample']
EXTRA = original.EXTRA
Actor = original.ResidualActor
frozen_digest = original.frozen_digest


def manifest(seed, model_id):
    if seed not in (116051, 116053): raise ValueError('mixed_training_seed_not_predeclared')
    return validate_manifest({'schema_version':SAMPLER_VERSION,'scope':'train',
        'model_SHA256':model_id,'training_seed':seed,'rng_namespace':VERSION,
        'policy_slots':list(SLOTS)},model_id)


def training_adapter(adapter, seed, model_id):
    if KEY in adapter: raise ValueError('mixed_requires_original_A_adapter')
    result=deepcopy(adapter); result[KEY]=manifest(seed,model_id)
    return result


def verify_training_identity(identity, seed, model_id):
    record=identity.get('TRAIN_foundation_opponent',{});ep=identity['episode_identity']
    expected=manifest(seed,model_id);policy=SLOTS[ep['case_index'] % 4]
    if (record.get('manifest')!=expected or record.get('policy')!=policy
            or record.get('model_SHA256')!=model_id
            or identity['opponent_mode']!=POLICIES[policy]
            or record.get('session',{}).get('worker')!=identity['worker']
            or record.get('session',{}).get('case_index')!=ep['case_index']
            or record.get('session',{}).get('team_sha256')!=ep['team_sha256']):
        raise ValueError('mixed_actual_opponent_identity_or_assignment')
    return policy


def allowed(name): return name in EXTRA


def initialize(source): return original.initialize(source,'set')


def validate_model(model, frozen=None):
    original.validate_model(model,'set',frozen)
    if ((model.ent_coef,model.vf_coef,model.max_grad_norm,model.target_kl,model.zero_avoiding_beta)
            !=(.01,.5,.5,.03,.001) or not model.normalize_advantage
            or getattr(model,'actionable_advantage_contract',None) is not None
            or model.policy.optimizer.param_groups[0]['lr']!=5e-5):
        raise ValueError('mixed_original_PPO_coefficients_changed')
    return True


def save(model, encoder, directory, provenance):
    validate_model(model)
    return original.save(model,encoder,directory,{'experiment':VERSION,
        'opponent_slots':SLOTS,'only_treatment':'TRAIN episode opponent action selection',**provenance})


class Recorder(CriticSignalRecorder):
    """The same audits, without asserting equality after the opponent changes.

    Join each PPO row to its pre-decision native episode, not VecEnv's automatic
    post-terminal reset. This is coordinator provenance, never a policy feature.
    """
    def start(self, model, clock):
        super().start(model,clock);self.links=[]

    def step(self, infos, dones):
        super().step(infos,dones)
        links=[]
        for info in infos:
            link=info.get('pilot_public_link')
            if not isinstance(link,dict) or not {'episode_id','action','feature_SHA256','decision_id','native_trace','native_ordinal'}<=set(link):
                raise ValueError('mixed_missing_predecision_training_join')
            links.append(deepcopy(link))
        self.links.append(links)

    def end(self, model, clock):
        AuditedSignalRecorder.end(self,model,clock)
        name=self.pending[0];b=model.rollout_buffer
        if len(self.links)!=model.n_steps or any(len(x)!=model.n_envs for x in self.links):
            raise ValueError('mixed_rollout_native_join_shape')
        rows=[]
        from hashlib import sha256
        for t in range(model.n_steps):
            for env in range(model.n_envs):
                link=self.links[t][env]
                if (link['action']!=int(b.actions[t,env,0])
                        or link['feature_SHA256']!=sha256(b.observations[t,env].tobytes()).hexdigest()):
                    raise ValueError('mixed_rollout_native_join_identity')
                rows.append({'t':t,'env':env,**link})
        durable_json(self.directory/(name+'.native_join.json'),{'rows':rows,'transitions':len(rows),
            'scope':'coordinator provenance only; actual first native decision of each PPO transition'})
        if clock==0:
            durable_json(self.directory/'first_rollout_provenance.json',{'status':'OPPONENT_MIXTURE_CHANGED_NO_BIT_EQUALITY_CLAIM',
                'transitions':len(rows),'before_Adam':0,'original_A_first_SHA256':digest(self.reference_first),
                'initial_output_equivalence':'verified separately before native collection',
                'GAE_logp_value_masks':'same maintained AuditedSignalRecorder checks'})
        self.same_input=(name,b.observations.reshape(-1,model.observation_space.shape[0]).copy(),
                         b.action_masks.reshape(-1,35).copy(),b.returns.reshape(-1).copy())
