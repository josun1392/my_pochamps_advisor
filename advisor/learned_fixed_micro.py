"""Frozen small cases and existing native/PPO adapters, no teacher or mechanics."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import numpy as np

from advisor.learned_encoder import fingerprint
from advisor.learned_selfplay_pilot import OPPONENTS, MODES, FrozenPublicActor, StartBudget, AuditedPilotEnv

VERSION = 'foundation-teacher-free-fixed-scenario-micro-v1'
CURVE_VERSION = 'foundation-frozen-micro-ppo-learning-curve-16k-v1'
DIVERSE_VERSION = 'foundation-diverse-scenario-micro-ppo-generalization-v1'


def micro_budget(plan):
    """An exact opt-in study cap, not PPO hyperparameter configuration."""
    default={'transitions':4096,'Adam':128,'starts':512,'targets':[1024,2048,3072,4096]}
    if 'micro_budget'not in plan:return default
    if plan.get('schema_version')==DIVERSE_VERSION:
        expected={'transitions':16384,'Adam':512,'starts':2048,'targets':[4096,8192,12288,16384]}
        if (plan.get('micro_prior_transitions')!=0 or plan['micro_budget']!=expected
                or plan.get('opponents')!=['league_s0']):
            raise ValueError('unsupported_diverse_micro_budget_or_opponent')
        return deepcopy(expected)
    expected={'transitions':12288,'Adam':384,'starts':1024,'targets':[4096,8192,12288]}
    if (plan.get('schema_version')!=CURVE_VERSION or plan.get('micro_prior_transitions')!=4096
            or plan['micro_budget']!=expected):
        raise ValueError('unsupported_micro_continuation_budget')
    return deepcopy(expected)


def seed4(namespace):
    raw=sha256(namespace.encode()).digest()
    return [int.from_bytes(raw[i:i+2],'big')for i in range(0,8,2)]


class FixedMicroCases:
    def __init__(self, plan):
        self.plan=plan
        self.identity={'sha256':fingerprint(plan['templates'])}
        self.contract={'selection_mode':'fixed_ordered_three_micro_v1'}

    def __call__(self, split, index):
        if split!='train' or type(index)is not int or index<0:
            raise ValueError('micro_TRAIN_only')
        # Opponent is index%4 in the existing Gym. Avoid coupling one family
        # exclusively to a subset of rivals.
        members=self.plan.get('training_template_indices',[0,1])
        divisor=1 if self.plan.get('schema_version')==DIVERSE_VERSION else len(OPPONENTS)
        which=members[(index//divisor)%len(members)]
        case=deepcopy(self.plan['templates'][which]['scenario'])
        version=self.plan.get('schema_version',VERSION)
        case.update(scenario_id=f'{version}:TRAIN:{index}',seed=seed4(f'{version}:TRAIN:{self.plan["seed"]}:{index}'))
        return case


class EpisodeRival:
    """Per-case addressed policy RNG, separate from native RNG and features."""
    def __init__(self, kind, parent):
        self.kind,self.parent=kind,parent
        self.model_id=(parent.model_id+':'+MODES[kind]if kind in MODES else kind)
        self.actor=None

    def reset(self, seed):
        from advisor.learned_baselines import VisibleBaseline
        self.actor=(FrozenPublicActor(self.parent,MODES[self.kind],seed)if self.kind in MODES else VisibleBaseline(self.kind,seed))

    def act(self, view):
        if self.actor is None:raise ValueError('micro_rival_not_case_initialized')
        return self.actor.act(view)


def training_vector(plan, root, parent):
    """Four sequential native workers using existing Gym/trace/retry owners."""
    from stable_baselines3.common.vec_env import DummyVecEnv
    from advisor.learned_gym import ShowdownLearningEnv, OPAQUE_TERMINAL
    from advisor.learned_baselines import VisibleBaseline
    from advisor.learned_combat_foundation import FoundationCombatEncoder,install_environment_profile
    root=Path(root)
    budget=StartBudget(root/'TRAIN_starts',micro_budget(plan)['starts'],root/'STOP')
    opponents=('league_s0',)if plan.get('schema_version')==DIVERSE_VERSION else OPPONENTS
    def make(worker):
        initial=budget.reserve({'phase':'training','worker':worker,'reason':'Gym_constructor_reset'})
        def opponent(kind,seed):
            return parent if kind in MODES else VisibleBaseline(kind,seed)
        env=ShowdownLearningEnv(plan['checkout'],FoundationCombatEncoder(plan['catalog']),
            index_offset=worker*100000,curriculum_version='showdown-learning-curriculum-v8',
            opponents=opponents,opponent_factory=opponent,collect_tactical_metrics=True,
            collect_v5_supervision=True,max_decisions=256,terminal_transport_version=OPAQUE_TERMINAL,
            training_subset=FixedMicroCases(plan))
        install_environment_profile(env)
        directory=root/'native_training'/f'worker_{worker}'
        directory.mkdir(parents=True,exist_ok=False)
        return AuditedPilotEnv(env,directory,budget,initial,worker,True)
    vector=DummyVecEnv([lambda w=w:make(w)for w in range(4)])
    return vector,budget


def paired_summary(records, cases, *, seed=2026102708, draws=20000):
    """Seed-cluster/seat paired CI conditional on the fixed small team motifs."""
    by={(r['model'],r['record']['case'],r['record']['candidate_seat']):r['record']for r in records}
    expected={(m,c['index'],s)for m in ('Foundation','Micro')for c in cases for s in ('p1','p2')}
    if len(records)!=256 or set(by)!=expected:raise ValueError('micro_evaluation_missing_or_duplicate')
    result={}
    rng=np.random.default_rng(seed)
    for scope in ('seen','heldout','all'):
        subset=[c for c in cases if scope=='all'or c['scope']==scope]
        rows={m:[by[m,c['index'],s]for c in subset for s in ('p1','p2')]for m in ('Foundation','Micro')}
        outcomes={m:{'wins':sum(r['winner']=='self'and not r['truncated']for r in rs),
            'losses':sum(r['winner']=='opponent'and not r['truncated']for r in rs),
            'draws':sum(r['winner']is None and not r['truncated']for r in rs),
            'truncations':sum(r['truncated']for r in rs),'games':len(rs)}for m,rs in rows.items()}
        deltas=np.array([np.mean([int(by['Micro',c['index'],s]['winner']=='self'and not by['Micro',c['index'],s]['truncated'])-
            int(by['Foundation',c['index'],s]['winner']=='self'and not by['Foundation',c['index'],s]['truncated'])for s in ('p1','p2')])for c in subset])
        # Keep the predeclared family/rival weights; resample native case seeds
        # within each stratum and keep both actual seats in each cluster.
        strata={}
        for i,c in enumerate(subset):strata.setdefault((c['scope'],c['family'],c['rival']),[]).append(i)
        samples=np.zeros(draws)
        for ids in strata.values():
            x=deltas[ids];samples+=x[rng.integers(0,len(x),size=(draws,len(x)))].sum(1)/len(deltas)
        result[scope]={'outcomes':outcomes,'Micro_minus_Foundation_winrate':float(deltas.mean()),
            'case_seed_cluster_95CI':np.quantile(samples,[.025,.975]).tolist(),'clusters':len(subset),
            'scope':'conditional_fixed_team_pairs_not_team_population_or_training_seed_uncertainty'}
    train=result['seen'];held=result['heldout']
    result['verdict']=('MICRO_LEARNING_DEMONSTRATED'if held['case_seed_cluster_95CI'][0]>0 and train['Micro_minus_Foundation_winrate']>0
        else 'MICRO_NO_GAIN'if held['case_seed_cluster_95CI'][1]<0 else'MICRO_INCONCLUSIVE')
    return result
