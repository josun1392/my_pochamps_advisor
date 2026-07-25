from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, USED_MOVE_SOURCE, HP_TRANSITION_SOURCE, USER_TRUST

def b(): return LifecycleConfirmationBoundary("s", {"self":{"slot_index":0,"pokemon_id":"pikachu"},"opponent":{"slot_index":1,"pokemon_id":"eevee"}})
def test_explicit_production_used_move_and_transition():
 x=b(); used=x.confirm(event_kind="used_move_observed",payload={"move_id":"tackle","move_slot":0},session_id="s",source=USED_MOVE_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu",observation_id="d")
 hp=x.confirm(event_kind="exact_hp_transition_observed",payload={"hp_before":70,"hp_after":40},session_id="s",source=HP_TRANSITION_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=1,pokemon_id="eevee",observation_id="d-hp",related_observation_id="d")
 assert used["status"]==hp["status"]=="confirmed" and used["observation"]["move_id"]=="tackle" and hp["observation"]["hp_unit"]=="exact"
def test_nonpromotion_validation_and_duplicate_rules():
 x=b(); assert x.confirm(event_kind="used_move_observed",payload={"move_id":"tackle"},session_id="s",source=USED_MOVE_SOURCE,trust=USER_TRUST,confirmed=False,side="self",slot_index=0,pokemon_id="pikachu")["status"]=="not_confirmed"
 assert x.confirm(event_kind="exact_hp_transition_observed",payload={"hp_before":40,"hp_after":70},session_id="s",source=HP_TRANSITION_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=1,pokemon_id="eevee")["status"]=="invalid_provenance"
 first=x.confirm(event_kind="used_move_observed",payload={"move_id":"tackle"},session_id="s",source=USED_MOVE_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu",observation_id="u"); assert x.confirm(event_kind="used_move_observed",payload={"move_id":"tackle"},session_id="s",source=USED_MOVE_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu",observation_id="u")["status"]=="duplicate" and first["observation"]["observation_sequence"]==1
