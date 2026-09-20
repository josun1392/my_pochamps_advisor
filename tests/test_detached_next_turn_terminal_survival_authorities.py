from copy import deepcopy
from llm.advisor_transition_preview import fingerprint_transition_preview_state
import llm.advisor_detached_next_turn_held_item_effect_applicability as held
from llm.advisor_detached_next_turn_sturdy_survival_authority import materialize_detached_next_turn_sturdy_survival_authority
from llm.advisor_detached_next_turn_focus_sash_survival_authority import materialize_detached_next_turn_focus_sash_survival_authority,apply_detached_focus_sash_single_hit
from tests.test_detached_next_turn_held_item_effect_applicability import _case

def _setup(monkeypatch,item="focus-sash",ability="sturdy",hp=100):
    monkeypatch.setattr(held,"validate_next_turn_predictive_mechanics_authority",lambda **_:None); state,fp,predictive,self_,opp=_case(item=item,ability=ability); predictive["sides"]["self"]["current_hp"]={"current_hp":hp,"maximum_hp":100}; action={"action_type":"attack","action_id":"x","identity":"tackle"}; move={"move_id":"tackle"}; return state,fp,predictive,self_,opp,action,move

def test_sturdy_readiness(monkeypatch):
    state,fp,predictive,defender,attacker,action,move=_setup(monkeypatch); state["ability_applicability_context"]={"schema_version":"ability-applicability-context-v1","session_id":"s","source":{key:defender[key] for key in ("side","slot_index","pokemon_id")},"ability_id":"sturdy","status":"applicable"}; fp=fingerprint_transition_preview_state(state); got=materialize_detached_next_turn_sturdy_survival_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,defender=defender,attacker=attacker,action=action,move_metadata=move); assert got["status"]=="ready"
    state["ability_applicability_context"]["status"]="not_applicable"; fp=fingerprint_transition_preview_state(state); assert materialize_detached_next_turn_sturdy_survival_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,defender=defender,attacker=attacker,action=action,move_metadata=move)["outcome"]=="known_no_effect"

def test_focus_sash_and_path_local_application(monkeypatch):
    state,fp,predictive,holder,attacker,action,move=_setup(monkeypatch,item="focus-sash",ability="static"); got=materialize_detached_next_turn_focus_sash_survival_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,holder=holder,attacker=attacker,action=action,move_metadata=move); assert got["status"]=="ready"
    lethal=apply_detached_focus_sash_single_hit(authority=got,damage=120,source_hit_id="h"); assert lethal["final_hp"]==1 and lethal["item_after"]["status"]=="known_absent"
    non=apply_detached_focus_sash_single_hit(authority=got,damage=20); assert non["item_consumed"] is False
