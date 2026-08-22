"""Bounded atomic Leech Seed residual coverage."""
from copy import deepcopy
from llm.advisor_leech_seed_end_of_turn import apply_owner_leech_seed_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import _apply_leech_seed_phase, project_per_owner_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority
from tests.test_leftovers_end_of_turn import _owner_id, _pre

def _seed(state, target="self", source="opponent", target_state="known_active"):
    owners={side:_owner_id(state,side) for side in ("self","opponent")}
    rows=[]
    for side in ("self","opponent"):
        rows.append({"owner":owners[side],"state":target_state if side==target else "known_inactive", **({"source_slot":{"session_id":owners[source]["session_id"],"side":source,"slot_index":owners[source]["slot_index"]}} if side==target and target_state=="known_active" else {})})
    state["leech_seed_persistent_effect_context"]={"schema_version":"detached-leech-seed-persistent-effect-v1","session_id":owners[target]["session_id"],"source_branch_fingerprint":"trusted-pre-materialized-branch","provenance":"trusted_leech_seed_persistent_effect_state","states":rows}
    states={side:{family:{"state":"known_inactive"} for family in ("aqua_ring","ingrain","leech_seed")} for side in ("self","opponent")}; states[target]["leech_seed"]={"state":target_state,"source_slot":rows[0 if target=="self" else 1].get("source_slot")}
    state["branch_persistent_effect_authority"]=materialize_persistent_effect_authority(owners=owners,source_branch_fingerprint="trusted-pre-materialized-branch",states=states)

def test_leech_seed_atomic_drain_heal_tier_eight_and_handoff():
    pre=_pre(self_hp=50,opponent_hp=40,self_item=None,opponent_item=None,self_condition="poison",opponent_condition="none"); _seed(pre["next_state"])
    result=project_per_owner_end_of_turn(pre_end_of_turn=pre,owner=_owner_id(pre["next_state"],"self"))
    assert result["status"]=="resolved",result
    rows=result["eot_consequence_trace"]
    assert [(r["tier"],r["effect"]) for r in rows]==[(8,"leech_seed"),(9,"poison_residual")]
    assert rows[0]["target_post_hp"]==38 and rows[0]["recipient_post_hp"]==52 and rows[1]["pre_hp"]==38
    handoff=handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"]=="resolved" and handoff["next_state"]["leech_seed_persistent_effect_context"]["source_branch_fingerprint"]==result["resulting_branch_fingerprint"]

def test_leech_seed_big_root_liquid_ooze_and_terminal_cases():
    big=_pre(self_hp=50,opponent_hp=40,self_item=None,opponent_item="big-root",self_condition="none",opponent_condition="none"); _seed(big["next_state"])
    result=project_per_owner_end_of_turn(pre_end_of_turn=big,owner=_owner_id(big["next_state"],"self")); row=result["eot_consequence_trace"][0]
    assert row["target_damage"]==12 and row["attempted_recovery"]==15 and row["recipient_post_hp"]==55
    ooze=_pre(self_hp=10,opponent_hp=10,self_item=None,opponent_item="big-root",self_condition="none",opponent_condition="none"); _seed(ooze["next_state"])
    abilities=ooze["next_state"]["current_state"]["ability_context"]["current_abilities"]; next(row for row in abilities if row["side"]=="self")["ability"]="liquid-ooze"
    result=project_per_owner_end_of_turn(pre_end_of_turn=ooze,owner=_owner_id(ooze["next_state"],"self")); row=result["eot_consequence_trace"][0]
    assert row["target_post_hp"]==0 and row["recipient_post_hp"]==0 and row["liquid_ooze"] is True

def test_leech_seed_unknown_skip_and_ordinary_switch_isolation():
    unknown=_pre(self_item=None,self_condition="none"); _seed(unknown["next_state"],target_state="unknown")
    assert project_per_owner_end_of_turn(pre_end_of_turn=unknown,owner=_owner_id(unknown["next_state"],"self"))=={"status":"incomplete","reason":"leech_seed_persistent_effect_unknown"}
    skipped=_pre(self_item=None,self_condition="none",opponent_hp=0); _seed(skipped["next_state"])
    result=project_per_owner_end_of_turn(pre_end_of_turn=skipped,owner=_owner_id(skipped["next_state"],"self"))
    assert result["status"]=="resolved" and result["eot_consequence_trace"][0]["reason"]=="source_slot_recipient_fainted"
    absent=_pre(self_item=None,self_condition="none"); _seed(absent["next_state"])
    absent["next_state"]["leech_seed_persistent_effect_context"]["states"][0]["source_slot"]["slot_index"] = 9
    result=project_per_owner_end_of_turn(pre_end_of_turn=absent,owner=_owner_id(absent["next_state"],"self"))
    assert result["status"]=="resolved" and result["eot_consequence_trace"][0]["reason"]=="source_slot_recipient_absent"
    source=unknown["next_state"]; incoming={"provenance":"identity_bound_incoming_current_state_v1","owner":{"session_id":"leftovers-eot","side":"self","slot_index":1,"pokemon_id":"incoming"},"hp_authority":{"status":"known","current_hp":50,"maximum_hp":100},"fainted_authority":{"status":"known","value":False},"current_state":deepcopy(source["current_state"])}
    switched=materialize_incoming_active_branch(source_branch=source,source_branch_fingerprint=fingerprint_transition_preview_state(source),incoming_authority=incoming)
    assert switched["status"]=="resolved" and "leech_seed_persistent_effect_context" not in switched["next_state"]

def test_source_slot_tracks_current_slot_occupant_and_cross_owner_plan_is_frozen():
    switched_source=_pre(self_hp=50,opponent_hp=40,self_item=None,opponent_item=None,self_condition="none",opponent_condition="none"); _seed(switched_source["next_state"])
    switched_source["next_state"]["active"]["opponent"]["pokemon_id"]="replacement-in-source-slot"
    result=project_per_owner_end_of_turn(pre_end_of_turn=switched_source,owner=_owner_id(switched_source["next_state"],"self"))
    assert result["status"]=="resolved" and result["eot_consequence_trace"][0]["recipient"]["pokemon_id"]=="replacement-in-source-slot"
    state=_pre(self_item=None,opponent_item=None,self_condition="none",opponent_condition="none")["next_state"]; _seed(state,target_state="known_active")
    state["leech_seed_persistent_effect_context"]["states"][1] = {"owner":_owner_id(state,"opponent"),"state":"known_active","source_slot":{"session_id":"leftovers-eot","side":"self","slot_index":0}}
    source=fingerprint_transition_preview_state(state)
    projection={"schema_version":"detached-leech-seed-target-order-v1","status":"known","session_id":"leftovers-eot","event_family":"ResidualLeechSeedTier8","source_branch_fingerprint":source,"ordered_active_owners":[_owner_id(state,"opponent"),_owner_id(state,"self")],"provenance":"trusted_canonical_showdown_leech_seed_residual_target_order"}
    phase=_apply_leech_seed_phase(state=state,projection=projection)
    assert phase["status"]=="resolved" and [row["owner"]["side"] for row in phase["trace"]]==["opponent","self"] and phase["trace"][0]["branch_fingerprint_consumed"]!=phase["trace"][1]["branch_fingerprint_consumed"]
