"""Offline fixtures only. No checkpoint, native battle, optimizer or training."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
import torch

from advisor.learned_execution_alignment import content_hash, masked_sample
from advisor.learned_opponent_quality import QualityActor, QualityTrace, analyze, global_rng_digest
from advisor.learned_train_opponents import POLICIES, addressed_policy_seed

MODEL='a'*64


def view(side='self', revision=0):
    return {'side':side,'episode_id':'fixture','revision':revision,'turn':revision+1,
        'request_state':'move','own_request':{'side':{'id':'p1' if side=='self' else 'p2'},
            'active':[{'moves':[{'id':'tackle'},{'id':'protect'},{'id':'recover'}]}]},
        'action_schema_version':'showdown-policy-actions-v1','state':{},'public_history':[],
        'action_mask':[int(i in (6,7,8)) for i in range(35)],'choices':[f'move {i}' for i in range(35)]}


class FakeFoundation:
    def __init__(self):
        self.model_id=MODEL;self.metadata={'combat_foundation':True};self.inputs=[];self.override={}
        self.model=SimpleNamespace(policy=SimpleNamespace(action_net=torch.nn.Identity()))
    def infer(self, v):
        self.inputs.append(deepcopy(v));logits=self.model.policy.action_net(torch.arange(35,dtype=torch.float32)[None]/10)
        mask=torch.tensor(v['action_mask'],dtype=torch.bool)[None]
        p=torch.softmax(torch.where(mask,logits,-torch.inf),dim=-1)[0].tolist()
        return {'model_id':self.model_id,'action_schema_version':'showdown-policy-actions-v1',
            **{k:v[k] for k in ('episode_id','revision','side')},'action_probabilities':p,
            'action_index':int(np.argmax(p)),'discounted_return_estimate':.25,**self.override}


def actor(policy='foundation_masked_sample',seat='p1',role='candidate',parent=None,record=None):
    return QualityActor(parent or FakeFoundation(),policy,case=0,seat=seat,role=role,record=record or (lambda *args:None))


@pytest.mark.parametrize('seat',['p1','p2'])
@pytest.mark.parametrize('role',['candidate','rival'])
@pytest.mark.parametrize('policy',list(POLICIES))
def test_exact_seats_same_logits_local_rng_and_original_forward(seat,role,policy):
    records=[];a=actor(policy,seat,role,record=lambda r,v:records.append(r));expected=np.random.default_rng(a.seed)
    initial=global_rng_digest()
    for i in range(32):
        v=view(a.side,i);action=a.act(v);r=records[-1]
        u=float(expected.random()) if policy=='foundation_masked_sample' else None
        assert r['uniform']==u and r['argmax']==8
        assert action==(masked_sample(r['probabilities'],v['action_mask'],u) if u is not None else 8)
        assert r['legal_count']==3 and r['global_RNG_unchanged'] and r['selected_family'] in ('attack','defense','recovery')
        assert len(r['legal_logits'])==35 and r['legal_logits'][0] is None
    assert global_rng_digest()==initial and a.parent.inputs==[view(a.side,i) for i in range(32)]
    assert a.core.rng.bit_generator.state==expected.bit_generator.state


@pytest.mark.parametrize('private',['native_state','seed','teams','opponent_request','future','labels'])
def test_private_roots_fail_before_inference_and_draw(private):
    a=actor();v=view();v[private]='secret';before=content_hash(a.core.rng.bit_generator.state)
    with pytest.raises(ValueError,match='private_predictor_input'):a.act(v)
    assert not a.parent.inputs and content_hash(a.core.rng.bit_generator.state)==before


def test_wrong_owner_episode_and_duplicate_decisions_fail_closed():
    a=actor()
    with pytest.raises(ValueError):a.act(view('opponent'))
    a.act(view());before=content_hash(a.core.rng.bit_generator.state)
    for v in [view(),{**view(revision=1),'episode_id':'other'}]:
        with pytest.raises(ValueError):a.act(v)
    assert content_hash(a.core.rng.bit_generator.state)==before


def test_invalid_proof_does_not_draw_or_leave_capture_hook():
    f=FakeFoundation();f.override={'model_id':'b'*64};a=actor(parent=f)
    before=content_hash(a.core.rng.bit_generator.state)
    with pytest.raises(ValueError):a.act(view())
    assert not f.model.policy.action_net._forward_pre_hooks and content_hash(a.core.rng.bit_generator.state)==before


def test_public_inputs_and_sampling_address_have_no_hidden_coordinator_fields():
    a,b=actor(),actor();assert a.address==b.address and a.seed==b.seed
    assert not {'native_seed','scenario','team_hashes','checkpoint','hidden'} & set(a.address)
    for i in range(10):assert a.act(view(revision=i))==b.act(view(revision=i))
    assert a.parent.inputs==b.parent.inputs


def trace(tmp_path,policy='foundation_argmax'):
    for n in ['decisions','initial_public','initial_native','trace_receipts']:(tmp_path/n).mkdir(exist_ok=True)
    return QualityTrace(tmp_path,policy,'p1',0)


def test_trace_requires_initial_native_pair_equality_and_no_truth_in_callback(tmp_path):
    a=trace(tmp_path);b=trace(tmp_path,'foundation_masked_sample')
    row={'policy':'foundation_argmax','candidate_seat':'p1','case':0,'native_checkpoint_digest':'c'*64,
         'native_state_SHA256':'d'*64,'canonical_scenario_sha256':'e'*64,'native_scenario_sha256':'f'*64}
    a.initial(row)
    with pytest.raises(ValueError,match='initial_native_states_not_matched'):
        b.initial({**row,'policy':'foundation_masked_sample','native_state_SHA256':'x'*64})
    a.stream.close();b.stream.close()


def test_trace_checks_actual_joint_execution_and_native_rejection(tmp_path):
    tr=trace(tmp_path);a=actor('foundation_argmax',record=tr.selection);b=actor('foundation_argmax',role='rival',record=tr.selection)
    va,vb=view(),view('opponent');aa,bb=a.act(va),b.act(vb)
    e={'before':{'self':va,'opponent':vb},'actions':{'self':aa,'opponent':bb},
       'result':{'action_rejected':False,'truncated':False,'terminated':True,'winner':'self','rewards':{'self':1,'opponent':-1},'private_request':'never_record'}}
    tr.observe(e);tr.finish({'decisions':1})
    assert 'private_request' not in tr.path.read_text()
    assert len(list((tmp_path/'initial_public').iterdir()))==2


def synthetic_results():
    cases=[{'index':i,'pair':i//4} for i in range(320)]
    rows=[{'policy':p,'case':c['index'],'seat':s,'record':{'return':1,'winner':'self',
        'truncated':False,'native_choice_rejections':0}} for p in POLICIES for c in cases for s in ('p1','p2')]
    return rows,cases


@pytest.mark.parametrize('rate,loss,verdict',[(.1,False,'OPPONENT_QUALITY_PILOT_COMPLETE'),(.01,False,'DIVERSITY_INSUFFICIENT'),(.1,True,'QUALITY_DEGRADED')])
def test_exact1280_cluster_accounting_and_predeclared_point_gates(rate,loss,verdict):
    rows,cases=synthetic_results()
    if loss:
        for r in rows:
            if r['policy']=='foundation_masked_sample':r['record'].update(winner='opponent');r['record']['return']=-1
    decisions=[{'legal_count':2,'action':int(i<100*rate),'argmax':0} for i in range(100)]
    r=analyze(rows,cases,decisions,draws=100)
    assert r['verdict']==verdict and r['clusters']==80 and sum(o['games'] for o in r['outcomes'].values())==1280
    assert analyze(list(reversed(rows)),cases,decisions,draws=100)==r
    with pytest.raises(ValueError):analyze(rows[:-1],cases,decisions,draws=100)
    with pytest.raises(ValueError):analyze(rows[:-1]+rows[:1],cases,decisions,draws=100)


@pytest.mark.parametrize('enabled',[False,True])
def test_evaluator_initial_hook_is_opt_in_and_before_first_actions(monkeypatch,enabled):
    import scripts.evaluate_showdown_policy as mod
    import advisor.learned_tactical_curriculum as curriculum
    events=[]
    class Env:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def observation(self,side,include_history):
            v=view(side);v['action_mask']=[int(i==26) for i in range(35)];return v
        def save(self):events.append('save');return {'digest':'a'*64,'native_state':{'only_coordinator':True}}
        def step(self,actions,revision):
            events.append('step');return {'terminated':True,'truncated':False,'action_rejected':False,'winner':'self','rewards':{'self':1,'opponent':-1}}
    class Policy:
        model_id=MODEL
        def act(self,v):events.append('act');return 26
    monkeypatch.setattr(mod,'ShowdownEnvironment',Env);monkeypatch.setattr(curriculum,'reset_learning_episode',lambda *a:None)
    def hook(row):
        assert 'native_state' not in row and 'native_state_SHA256' in row;events.append('hash')
    def provider(*a):return {'scenario_id':'fixture','teams':{'self':[],'opponent':[]},'seed':[1,2,3,4]}
    provider.identity={'fixture':True}
    result=mod.evaluate('mock','mock',{'mock':Policy()},cases=1,rivals={'rival':Policy()},
        case_provider=provider,
        initial_state_observer=hook if enabled else None)
    assert len(result['records'])==1 if isinstance(result,dict) else len(result)==1
    assert events==(['save','hash','act','act','step'] if enabled else ['act','act','step'])
