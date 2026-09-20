import llm.advisor_detached_next_turn_held_item_effect_applicability as held
from llm.advisor_detached_next_turn_life_orb_immediate_authority import materialize_detached_next_turn_life_orb_immediate_authority
from tests.test_detached_next_turn_terminal_survival_authorities import _setup

def test_life_orb_recoil_and_suppressors(monkeypatch):
    state,fp,predictive,attacker,target,action,move=_setup(monkeypatch,item="life-orb",ability="static",hp=5); got=materialize_detached_next_turn_life_orb_immediate_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,attacker=attacker,target=target,action=action,move_metadata=move,qualifying_damage=True); assert got["effective_item_id"]=="life-orb" and got["recoil"]["post_hp"]==0
    predictive["sides"]["self"]["ability"]={"status":"known","value":"magic-guard"}; got=materialize_detached_next_turn_life_orb_immediate_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,attacker=attacker,target=target,action=action,move_metadata=move,qualifying_damage=True); assert got["recoil"]["suppressed_by"]=="magic-guard"
    predictive["sides"]["opponent"]["ability"]={"status":"known","value":"neutralizing-gas"}; got=materialize_detached_next_turn_life_orb_immediate_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,attacker=attacker,target=target,action=action,move_metadata=move,qualifying_damage=False); assert got["recoil"]["recoil_damage"]==0

def test_life_orb_magic_room_and_unknown_ability(monkeypatch):
    state,fp,predictive,attacker,target,action,move=_setup(monkeypatch,item="life-orb",ability="static"); state["field"]["magic_room_status"]="active"; fp=__import__("llm.advisor_transition_preview",fromlist=["fingerprint_transition_preview_state"]).fingerprint_transition_preview_state(state); got=materialize_detached_next_turn_life_orb_immediate_authority(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=predictive,attacker=attacker,target=target,action=action,move_metadata=move,qualifying_damage=True); assert got["effective_item_id"] is None
