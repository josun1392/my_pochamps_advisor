from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input
def battle(): return {"current_state_session_id":"s","pokemon":{"my_active":{"name_en":"pikachu","slot_index":0},"opponent_active":{"name_en":"eevee","slot_index":1}},"moves":{"my_selected_move":{"move_id":"tackle"}}}
def test_optional_collection_snapshot_is_detached_internal_evidence():
 c=ObservationCollection("s");c.add_confirmation_result({"status":"confirmed","observation":{"observation_id":"a","observation_sequence":1,"event_kind":"used_move_observed","session_id":"s","payload":{}}})
 frozen=build_turn_snapshot_from_battle_input(battle(),observation_snapshot=c.snapshot()).to_dict();c.add_confirmation_result({"status":"confirmed","observation":{"observation_id":"b","observation_sequence":2,"event_kind":"pokemon_faint_observed","session_id":"s","payload":{}}})
 assert [x["observation_id"] for x in frozen["current_state"]["canonical_observation_collection"]["ordered_observations"]]==["a"]
