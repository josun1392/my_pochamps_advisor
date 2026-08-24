from copy import deepcopy

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context, freeze_runtime_d0_hit_modifier_authority,
    freeze_runtime_strategy_d0,
)
from tests.test_runtime_d0_native_damage_context import _state as _native_state


def _state(session="runtime-hit-modifier"):
    state=_native_state(session)
    for side in ("self","opponent"):
        state[f"{side}_side"]["pokemon"][0]["stat_stages"]={"accuracy":0,"evasion":0}
    return state
def _owner(state,side="self"): return {"session_id":state["session_id"],"side":side,"slot_index":0,"pokemon_id":state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}
def _snapshot(state): return {"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":deepcopy(state),"state_fingerprint":state_fingerprint(state)}
def _d0(state):
    snapshot=_snapshot(state); return snapshot,freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state))
def _move(category="physical", move_id="tackle"): return {"move_id":move_id,"category":category}
def _hustle(state,status="applicable"):
    pokemon=state["self_side"]["pokemon"][0]
    pokemon["current_ability"]="hustle"; pokemon["current_ability_provenance"]={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1}
    state["ability_applicability_context"]={"schema_version":"ability-applicability-context-v1","session_id":state["session_id"],"source":{"side":"self","slot_index":0,"pokemon_id":pokemon["pokemon_id"]},"ability_id":"hustle","status":status}


def test_runtime_hustle_authority_projects_exact_applicable_resolver_and_stages():
    state=_state(); _hustle(state); snapshot,d0=_d0(state)
    result=freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata=_move())
    assert result["status"]=="resolved" and result["capability_resolution"]["ledger"][0]["state"]=="applicable"
    assert result["strict_stage_authority"]["status"]=="resolved"
    assert result["move"]==_move() and result["source_authority"]["attacker_ability"]["applicability"]=={"status":"applicable"}


def test_runtime_hustle_unknowns_and_known_non_hustle_remain_fail_closed():
    state=_state(); _hustle(state,"unknown"); snapshot,d0=_d0(state)
    incomplete=freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata=_move())
    assert incomplete["status"]=="incomplete" and incomplete["capability_resolution"]["reason"]=="hustle_applicability_unknown"
    state=_state(); snapshot,d0=_d0(state)
    unknown=freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata=_move())
    assert unknown["status"]=="incomplete" and unknown["source_authority"]["attacker_ability"]=={"status":"unknown"}
    state=_state(); state["self_side"]["pokemon"][0].update(current_ability="compound-eyes",current_ability_provenance={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1}); snapshot,d0=_d0(state)
    unsupported=freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata=_move())
    assert unsupported["status"]=="unsupported"


def test_neutral_category_stale_identity_move_and_detachment_contracts():
    state=_state(); _hustle(state); snapshot,d0=_d0(state)
    neutral=freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata=_move("special"))
    assert neutral["status"]=="resolved" and neutral["capability_resolution"]["ledger"][0]["state"]=="known_neutral"
    state["self_side"]["pokemon"][0]["current_ability"]="mutated"
    assert neutral["source_authority"]["attacker_ability"]["value"]=="hustle"
    stale=freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=_snapshot(state),attacker=_owner(state),target=_owner(state,"opponent"),move_metadata=_move())
    assert stale["status"]=="rejected"
    assert freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state,"opponent"),target=_owner(state),move_metadata=_move())["status"]=="rejected"
    assert freeze_runtime_d0_hit_modifier_authority(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata={"move_id":"tackle","category":"invalid"})["status"]=="rejected"


def test_native_damage_context_does_not_depend_on_hit_modifier_authority():
    state=_state(); snapshot,d0=_d0(state)
    native=build_runtime_d0_native_damage_context(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata={"move_id":"water-gun","category":"special","power":40,"type":"water"})
    assert "hit_modifier" not in native and native["schema_version"]=="runtime-d0-native-damage-context-v1"
