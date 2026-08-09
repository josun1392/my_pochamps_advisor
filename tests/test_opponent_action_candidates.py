from llm.advisor_opponent_action_candidates import build_opponent_action_candidates

class S:
 def __init__(self,d):self.d=d
 def to_dict(self):return self.d
def snap(moves,state="partially_known"):
 return S({"battle_state":{"active_player":{"species_id":"pikachu","slot_index":0},"active_opponent":{"species_id":"garchomp","slot_index":1}},"current_state":{"known_move_context":{"opponent":{"pokemon_id":"garchomp","slot_index":1,"known_move_ids":moves,"state":state}},"final_stat_context":{},"current_type_context":{}}})
def test_enumerates_only_frozen_active_known_moves_with_namespaced_ids():
 r=build_opponent_action_candidates(turn_snapshot=snap(["earthquake","protect"]),move_repository={"earthquake":{"move_id":"earthquake","category":"physical"},"protect":{"move_id":"protect","category":"status"}})
 assert r["known_candidate_count"]==2 and not r["candidate_set_complete"]
 assert [x["candidate_id"] for x in r["opponent_action_candidates"]]==["opponent-action:garchomp:earthquake:0","opponent-action:garchomp:protect:1"]
 assert all(x["acting_side"]=="opponent" and x["target_side"]=="self" for x in r["opponent_action_candidates"])
def test_unknown_and_metadata_failure_do_not_synthesize_or_drop_known_identity():
 assert build_opponent_action_candidates(turn_snapshot=snap([] ,"unknown"),move_repository={})["opponent_action_candidates"]==[]
 r=build_opponent_action_candidates(turn_snapshot=snap(["earthquake"]),move_repository={})
 assert r["known_candidate_count"]==1 and r["opponent_action_candidates"][0]["metadata_supportability"]=="unsupported_mechanic"
