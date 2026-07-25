from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, SWITCH_SOURCE, FAINT_SOURCE, USER_TRUST
def b(): return LifecycleConfirmationBoundary("s", {"self":{"slot_index":0,"pokemon_id":"pikachu"},"opponent":{"slot_index":1,"pokemon_id":"eevee"}})
def test_explicit_switch_and_faint():
 x=b(); sw=x.confirm(event_kind="pokemon_switch_observed",payload={"switch_out_slot_index":0,"switch_out_pokemon_id":"pikachu","switch_in_slot_index":2,"switch_in_pokemon_id":"charizard"},session_id="s",source=SWITCH_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu")
 faint=x.confirm(event_kind="pokemon_faint_observed",payload={"cause_known":False},session_id="s",source=FAINT_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=1,pokemon_id="eevee",related_observation_id=sw["observation"]["observation_id"])
 assert sw["status"]==faint["status"]=="confirmed" and sw["observation"]["switch_kind"]=="unknown"
def test_nonpromotion_invalid_and_duplicate():
 x=b(); assert x.confirm(event_kind="pokemon_faint_observed",payload={"hp_zero":True},session_id="s",source=FAINT_SOURCE,trust=USER_TRUST,confirmed=False,side="self",slot_index=0,pokemon_id="pikachu")["status"]=="not_confirmed"
 args=dict(event_kind="pokemon_switch_observed",payload={"switch_out_slot_index":0,"switch_out_pokemon_id":"pikachu","switch_in_slot_index":0,"switch_in_pokemon_id":"pikachu"},session_id="s",source=SWITCH_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu")
 assert x.confirm(**args)["status"]=="invalid_provenance"
