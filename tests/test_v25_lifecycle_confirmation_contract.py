from copy import deepcopy
from llm.advisor_lifecycle_confirmation import CONDITION_APPLICATION_SOURCE, HAZARD_STATE_SOURCE, HP_RECOVERY_SOURCE, STAT_STAGE_SOURCE, LifecycleConfirmationBoundary, FIXTURE_SOURCE, FIXTURE_TRUST, PRODUCTION_SOURCE, USER_TRUST

def boundary(session="s"): return LifecycleConfirmationBoundary(session, {"self":{"slot_index":0,"pokemon_id":"pikachu"}, "opponent":{"slot_index":1,"pokemon_id":"eevee"}})
def damage(**x): return {"damage_amount":10,"hp_unit":"exact",**x}

def test_production_damage_explicit_sequence_and_immutability():
 b=boundary(); payload=damage(); before=deepcopy(payload); r=b.confirm(event_kind="direct_move_damage_observed",payload=payload,session_id="s",source=PRODUCTION_SOURCE,trust=USER_TRUST,confirmed=True)
 assert r["status"]=="confirmed" and r["observation"]["observation_sequence"]==1 and payload==before
 assert b.confirm(event_kind="direct_move_damage_observed",payload=damage(),session_id="s",source=PRODUCTION_SOURCE,trust=USER_TRUST,confirmed=False)["status"]=="not_confirmed"

def test_fixture_nonpromotion_owner_session_and_payload_rejections():
 b=boundary()
 assert b.confirm(event_kind="used_move_observed",payload={"move_id":"tackle"},session_id="s",source=FIXTURE_SOURCE,trust=FIXTURE_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu")["status"]=="fixture_only_source"
 assert b.confirm(event_kind="used_move_observed",payload={"move_id":"tackle"},session_id="s",source=FIXTURE_SOURCE,trust=FIXTURE_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu",production=False)["status"]=="confirmed"
 assert b.confirm(event_kind="pokemon_faint_observed",payload={"q12":True},session_id="old",source=FIXTURE_SOURCE,trust=FIXTURE_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu",production=False)["status"]=="stale_session"
 assert b.confirm(event_kind="pokemon_switch_observed",payload={"selected":True},session_id="s",source=FIXTURE_SOURCE,trust=FIXTURE_TRUST,confirmed=True,side="self",slot_index=1,pokemon_id="pikachu",production=False)["status"]=="invalid_provenance"

def test_duplicate_conflict_and_repeated_occurrence_do_not_misallocate():
 b=boundary(); args=dict(event_kind="direct_move_damage_observed",payload=damage(),session_id="s",source=PRODUCTION_SOURCE,trust=USER_TRUST,confirmed=True,observation_id="x")
 assert b.confirm(**args)["status"]=="confirmed"
 assert b.confirm(**args)["status"]=="duplicate"
 changed={**args,"payload":damage(damage_amount=11)}; assert b.confirm(**changed)["status"]=="conflicting_confirmation"
 assert b.confirm(**{**args,"observation_id":"y"})["observation"]["observation_sequence"]==2

def test_production_condition_application_requires_exact_major_condition_and_owner():
 b=boundary(); args=dict(event_kind="condition_applied_observed",payload={"condition":"burn"},session_id="s",source=CONDITION_APPLICATION_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=1,pokemon_id="eevee",related_observation_id="used-move")
 result=b.confirm(**args); assert result["status"]=="confirmed" and result["observation"]["reducer_eligibility"]=="candidate"
 assert b.confirm(**{**args,"payload":{"condition":"unknown"}})["status"]=="invalid_provenance"
 assert b.confirm(**{**args,"side":"self"})["status"]=="invalid_provenance"

def test_production_absolute_stat_stage_requires_exact_supported_stage_and_owner():
 b=boundary(); args=dict(event_kind="stat_stage_observed",payload={"stat":"attack","stage":-2},session_id="s",source=STAT_STAGE_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=1,pokemon_id="eevee")
 assert b.confirm(**args)["status"]=="confirmed"
 assert b.confirm(**{**args,"payload":{"stat":"attack","stage":7}})["status"]=="invalid_provenance"
 assert b.confirm(**{**args,"payload":{"stat":"unknown","stage":0}})["status"]=="invalid_provenance"

def test_production_hazard_state_requires_complete_side_owned_replacement():
 b=boundary(); payload={"stealth_rock":"absent","spikes_layers":0,"toxic_spikes_layers":0,"sticky_web":"absent"}; args=dict(event_kind="switch_hazards_observed",payload=payload,session_id="s",source=HAZARD_STATE_SOURCE,trust=USER_TRUST,confirmed=True,side="self")
 assert b.confirm(**args)["status"]=="confirmed"
 assert b.confirm(**{**args,"payload":{**payload,"spikes_layers":4}})["status"]=="invalid_provenance"
 assert b.confirm(**{**args,"payload":{"stealth_rock":"absent"}})["status"]=="invalid_provenance"

def test_production_exact_hp_recovery_requires_observed_increase_and_owner():
 b=boundary(); args=dict(event_kind="exact_hp_recovery_observed",payload={"hp_before":40,"hp_after":70},session_id="s",source=HP_RECOVERY_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="pikachu")
 assert b.confirm(**args)["status"]=="confirmed"
 assert b.confirm(**{**args,"payload":{"hp_before":70,"hp_after":40}})["status"]=="invalid_provenance"
 assert b.confirm(**{**args,"payload":{"hp_before":0,"hp_after":40}})["status"]=="invalid_provenance"
