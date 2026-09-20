from copy import deepcopy
from llm.advisor_transition_preview import fingerprint_transition_preview_state
import llm.advisor_detached_next_turn_held_item_effect_applicability as held

def _case(*, item="choice-band", ability="static", other="static", magic="inactive"):
    self_={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}; opp={"session_id":"s","side":"opponent","slot_index":0,"pokemon_id":"b"}
    state={"active":{"self":deepcopy(self_),"opponent":deepcopy(opp)},"field":{"magic_room_status":magic,"magic_room_status_provenance":{"event_kind":"magic_room_field_observed","trust":"user_confirmed_observation","source_observation_id":"m","source_sequence":1}}}
    fp=fingerprint_transition_preview_state(state)
    fact=lambda v: {"status":"known","value":v} if v is not None else {"status":"known_absent"}
    predictive={"active_owners":{"self":self_,"opponent":opp},"sides":{"self":{"owner":self_,"item":fact(item),"ability":fact(ability)},"opponent":{"owner":opp,"item":fact(None),"ability":fact(other)}}}
    return state,fp,predictive,self_,opp

def _allow(monkeypatch): monkeypatch.setattr(held,"validate_next_turn_predictive_mechanics_authority",lambda **_:None)

def test_held_item_active_and_suppressors(monkeypatch):
    _allow(monkeypatch)
    for kwargs, active, effective in [({},True,"choice-band"),({"magic":"active"},False,None),({"ability":"klutz"},False,None),({"ability":"klutz","other":"neutralizing-gas"},True,"choice-band"),({"item":None},False,None)]:
        state,fp,predictive,owner,_=_case(**kwargs); got=held.materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,holder=owner)
        assert got["status"]=="resolved" and got["item_effects_active"] is active and got["effective_item_id"]==effective

def test_held_item_unknowns_and_fingerprint(monkeypatch):
    _allow(monkeypatch); state,fp,predictive,owner,_=_case(); state["field"]={}; assert held.materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state,next_decision_fingerprint=fingerprint_transition_preview_state(state),predictive_mechanics=predictive,holder=owner)["status"]=="incomplete"
    state,fp,predictive,owner,_=_case(ability="klutz",other=None); assert held.materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,holder=owner)["status"]=="incomplete"
    state,fp,predictive,owner,_=_case(ability=None); assert held.materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,holder=owner)["status"]=="incomplete"
    assert held.materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state,next_decision_fingerprint="forged",predictive_mechanics=predictive,holder=owner)["status"]=="rejected"

def test_resist_berry_is_explicitly_unrepresented(monkeypatch):
    _allow(monkeypatch); state,fp,predictive,owner,_=_case(item="occa-berry"); got=held.materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,holder=owner); assert got["terminal_consumption"]=="required_unrepresented"
