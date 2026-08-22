from copy import deepcopy
from llm.advisor_predictive_water_gun_interval import build_predictive_water_gun_interval, project_guaranteed_water_gun_facts
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot, build_snapshot_damage_input, build_snapshot_stat_provenance
from tests.test_v15_direct_mechanics_slice_contract import _battle, _Species

def _fixture(hp=100, sub="known_inactive", sub_hp=None):
 b=_battle(self_pokemon="pikachu",opponent_pokemon="eevee");b["moves"]["my_available_moves"][0]["move_id"]="water-gun";s=build_request_start_recommendation_snapshot(b,selectable_moves=("water-gun",));d=build_snapshot_damage_input(s,candidate_slot_index=0,candidate_move_id="water-gun",selectable_moves=("water-gun",),move_metadata={"category":"special","power":40,"type":"water"});d["battle_context"]["current_state"]["field_state_context"]={"current_field":{"weather":"none","terrain":"none","side_effects":[]}};p=build_snapshot_stat_provenance(s,species_repository=_Species());o={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"pikachu"};t={"session_id":"s","side":"opponent","slot_index":1,"pokemon_id":"eevee"};state={"active":{"self":{**o,"current_hp":100,"max_hp":100,"fainted":False},"opponent":{**t,"current_hp":hp,"max_hp":100,"fainted":False}},"current_state":deepcopy(d["battle_context"]["current_state"]),"substitute_state_context":{"schema_version":"detached-substitute-state-v1","states":[{"owner":o,"state":"known_inactive","substitute_hp":None},{"owner":t,"state":sub,"substitute_hp":sub_hp}]}};return state,o,t,d,p
def _run(hp=100,sub="known_inactive",sub_hp=None):
 s,o,t,d,p=_fixture(hp,sub,sub_hp);return build_predictive_water_gun_interval(branch_state=s,decision_owner=o,target_owner=t,snapshot_damage_input=d,stat_provenance=p,trusted_level=50)
def test_native_water_gun_rolls_bounds_facts_and_projection_are_pure():
 r=_run();assert r["completeness"]=="exact_complete" and len(r["exact_damage_rolls"])==16 and (r["min_damage"],r["max_damage"])==(min(r["exact_damage_rolls"]),max(r["exact_damage_rolls"])) and r["guaranteed_facts"]["guaranteed_target_survival"] and project_guaranteed_water_gun_facts(r)["facts"]==r["guaranteed_facts"] and _run()==r
def test_ko_possible_and_substitute_interval_facts():
 assert _run(10)["guaranteed_facts"]["guaranteed_target_KO"]
 assert _run(17)["guaranteed_facts"]["possible_target_KO"]
 assert _run(sub="known_active",sub_hp=30)["guaranteed_facts"]["guaranteed_substitute_survival"]
 assert _run(sub="known_active",sub_hp=10)["guaranteed_facts"]["guaranteed_substitute_break"]
 assert _run(sub="known_active",sub_hp=17)["guaranteed_facts"]["possible_substitute_break"]
def test_unknown_substitute_and_foreign_input_fail_closed():
 s,o,t,d,p=_fixture();s.pop("substitute_state_context");assert build_predictive_water_gun_interval(branch_state=s,decision_owner=o,target_owner=t,snapshot_damage_input=d,stat_provenance=p,trusted_level=50)["completeness"]=="exact_incomplete"
 d["move"]["move_id"]="tackle";assert build_predictive_water_gun_interval(branch_state=s,decision_owner=o,target_owner=t,snapshot_damage_input=d,stat_provenance=p,trusted_level=50)["status"]=="rejected"
