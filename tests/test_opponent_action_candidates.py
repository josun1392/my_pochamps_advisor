from llm.advisor_opponent_action_candidates import build_opponent_action_candidates
from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle, build_provider_recommendation_payload

class S:
 def __init__(self,d):self.d=d
 def to_dict(self):return self.d
def snap(moves,state="partially_known"):
 return S({"battle_state":{"active_player":{"species_id":"pikachu","slot_index":0},"active_opponent":{"species_id":"garchomp","slot_index":1}},"current_state":{"known_move_context":{"session_id":"s","opponent":{"pokemon_id":"garchomp","slot_index":1,"known_move_ids":moves,"state":state}},"final_stat_context":{},"current_type_context":{}}})
def test_enumerates_only_frozen_active_known_moves_with_namespaced_ids():
 r=build_opponent_action_candidates(turn_snapshot=snap(["earthquake","protect"]),move_repository={"earthquake":{"move_id":"earthquake","category":"physical"},"protect":{"move_id":"protect","category":"status"}})
 assert r["known_candidate_count"]==2 and not r["candidate_set_complete"]
 assert [x["candidate_id"] for x in r["opponent_action_candidates"]]==["opponent-action:s:garchomp:earthquake:0","opponent-action:s:garchomp:protect:1"]
 assert all(x["acting_side"]=="opponent" and x["target_side"]=="self" for x in r["opponent_action_candidates"])
def test_unknown_and_metadata_failure_do_not_synthesize_or_drop_known_identity():
 assert build_opponent_action_candidates(turn_snapshot=snap([] ,"unknown"),move_repository={})["opponent_action_candidates"]==[]
 r=build_opponent_action_candidates(turn_snapshot=snap(["earthquake"]),move_repository={})
 assert r["known_candidate_count"]==1 and r["opponent_action_candidates"][0]["metadata_supportability"]=="unsupported_mechanic"
def test_prepared_cycle_keeps_opponent_candidates_internal_and_provider_request_unchanged():
 context={"schema_version":"known-move-context-v1","session_id":"s","self":{"slot_index":0,"pokemon_id":"pikachu","state":"unknown","known_move_ids":[],"unknown_slot_count":4},"opponent":{"slot_index":1,"pokemon_id":"garchomp","state":"partially_known","known_move_ids":["earthquake"],"unknown_slot_count":3}}
 battle={"current_state_session_id":"s","known_move_context":context,"moves":{"my_available_moves":[{"slot_index":0,"move_id":"tackle"}]},"pokemon":{"my_active":{"name_en":"pikachu","slot_index":0},"opponent_active":{"name_en":"garchomp","slot_index":1}}}
 repo={"tackle":{"move_id":"tackle","category":"physical","priority":0,"power":40,"type":"normal","target":"selected-pokemon"},"earthquake":{"move_id":"earthquake","category":"physical","priority":0,"power":100,"type":"ground","target":"selected-pokemon"}}
 prepared=prepare_ui_recommendation_cycle(selected_moves=[{"move_id":"tackle"}],battle_input=battle,move_repository=repo)
 assert prepared["evidence_bundle"]["opponent_action_candidates"]["known_candidate_count"]==1
 assert "opponent_action_candidates" not in repr(build_provider_recommendation_payload(prepared_cycle=prepared))
