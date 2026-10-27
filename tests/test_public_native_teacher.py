"""Pure admission tests. Synthetic examples are not actual TRAIN coverage."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from advisor.learned_public_native_teacher import support_conditions, PublicNativeTeacher
from advisor.learned_public_native_teacher import confirmed_item_absence
from advisor.learned_action_search_teacher import public_teacher_binding, validate_public_teacher_target
from tests.test_integrated_micro_contract import view


def test_unknown_response_availability_abstains_before_native(monkeypatch):
    import advisor.learned_public_native_teacher as module
    projection={'unsupported':[],'active':[{'effects':{'recharge':False}},{'effects':{'recharge':None}}]}
    monkeypatch.setattr(module,'project_strategic_public',lambda *a:projection)
    reason,conditions=support_conditions(view(),{})
    assert reason=='opponent_response_availability_not_publicly_forced'and conditions is None
    teacher=object.__new__(PublicNativeTeacher);teacher.catalog={}
    result=teacher.assess(view(),policy_id='fixture',learning_step=0)
    assert result['status']=='abstain' and result['native_starts']==0
    assert validate_public_teacher_target(result,view(),policy_id='fixture',learning_step=0)is None


def test_nontrivial_and_unsupported_projection_are_not_targets(monkeypatch):
    import advisor.learned_public_native_teacher as module
    v=view();v['action_mask']=[int(a==6)for a in range(35)]
    assert support_conditions(v,{})[0]=='no_nontrivial_move_decision'
    monkeypatch.setattr(module,'project_strategic_public',lambda *a:{'unsupported':['uncertain_type']})
    assert support_conditions(view(),{})[0]=='unsupported_public_projection'


@pytest.mark.parametrize('key',['native_state','checkpoint','opponent_request','seed','rng'])
def test_private_truth_cannot_be_hypothesis_input(key):
    v=view();v['state']={'opponent_side':{key:{}}}
    with pytest.raises(ValueError):public_teacher_binding(v,policy_id='p',learning_step=0)


def test_public_equivalence_is_whole_view_not_feature_similarity():
    from advisor.learned_action_signals import require_public_equivalence
    v=view();c=deepcopy(v);c['own_request']['side']['id']='p2'
    with pytest.raises(ValueError,match='contradicts'):require_public_equivalence(v,c)
    c=deepcopy(v);c['action_mask'][6]=0
    with pytest.raises(ValueError,match='contradicts'):require_public_equivalence(v,c)


def test_consumed_item_heal_is_not_item_regain_and_real_gain_cancels_absence():
    v={'public_history':['|-enditem|p2a: slot-2|Sitrus Berry|[eat]',
        '|-heal|p2a: slot-2|50/100|[from] item: Sitrus Berry']}
    assert confirmed_item_absence(v,'p2a: slot-2',{'known_item':'sitrusberry'})
    v['public_history'].append('|-item|p2a: slot-2|Focus Sash')
    assert not confirmed_item_absence(v,'p2a: slot-2',{'known_item':'sitrusberry'})


def test_bound_native_teacher_uses_existing_consumer_without_optimizer(monkeypatch):
    from scripts.train_showdown_autonomous import apply_public_teacher_decision
    model=SimpleNamespace(num_timesteps=0,rollout_buffer=SimpleNamespace(pos=0))
    def forbidden(*a,**k):raise AssertionError('encoder or Adam must not execute')
    provider=SimpleNamespace(assess=lambda v,**kw:{'schema_version':'foundation-public-search-teacher-admission-v1',
        'binding':public_teacher_binding(v,**kw)[1],'status':'abstain','target':None,
        'reason':'unknown_availability','evidence_scope':'public_only_admission'})
    result=apply_public_teacher_decision(model,SimpleNamespace(encode=forbidden),view(),provider,
        policy_id='p',learning_step=0,enabled=True,ledger=SimpleNamespace(reserve=forbidden))
    assert result['optimizer_updates']==0
