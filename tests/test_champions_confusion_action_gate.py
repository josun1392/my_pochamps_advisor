from copy import deepcopy
from fractions import Fraction
import pytest
from tests.test_detached_opponent_response_profile import _state, _complete_state, _owner, _snapshot, _metadata, MOVES
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate as freeze, materialize_confusion_branch, validate_confusion_gate
from llm.advisor_champions_sleep_freeze_action_gate import fraction
from llm.advisor_champions_confusion_self_hit import materialize_confusion_self_hit

def inputs(*, prior=0, duration=None, ability="pressure", opposing="pressure"):
    state=_complete_state(_state()); raw=state["self_side"]["pokemon"][0]; raw.update(current_confusion="confused",current_ability=ability); raw["confusion_provenance"]={"event_kind":"current_confusion_observed","trust":"user_confirmed_observation","turn_number":1,"state":"confused"}; state["opponent_side"]["pokemon"][0]["current_ability"]=opposing
    owner=_owner(state,"self"); event={"observation_id":"confusion","observation_sequence":1,"planned_effect":"record_champions_confusion_progression","trust":"user_confirmed_observation",**owner,"state":"confused","origin_id":"confusion:1","established_turn":1,"prior_opportunities":prior,"duration":duration,"turn_number":1}
    result=project_atomic_transition(state,{"session_id":state["session_id"],"status":"planned","conflicts":[],"ordered_steps":[event]},state["session_id"]); assert result["status"]=="ready_with_projected_state",result
    snapshot=_snapshot(result["projected_state"]); return snapshot,freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=owner),owner

def gate(**kwargs):
    snapshot,d0,actor=inputs(**kwargs);return snapshot,d0,freeze(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,action_id="attack:tackle",move_id="tackle",action_order={"order":"own_first"},path=("root",))

def test_active_unknown_and_own_tempo_boundaries():
    _,_,result=gate();assert result["status"]=="resolved" and validate_confusion_gate(result)
    snapshot,d0,actor=inputs(); state=deepcopy(snapshot["state"]);state["self_side"]["pokemon"][0]["current_confusion"]="unknown"; snapshot=_snapshot(state);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=actor);assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,action_id="a",move_id="tackle",action_order={})["status"]=="incomplete"
    assert gate(ability="own-tempo")[2]["status"]=="rejected"
    assert gate(ability="own-tempo",opposing="neutralizing-gas")[2]["status"]=="resolved"

def test_duration_persists_and_snap_out_precedes_action():
    snapshot,d0,result=gate(duration=2)
    assert [fraction(x["probability"]) for x in result["branches"]]==[Fraction(1,3),Fraction(2,3)]
    proceed=result["branches"][1];view=materialize_confusion_branch(strategy_d0=d0,runtime_snapshot=snapshot,authority=result,branch=proceed)
    nxt=freeze(strategy_d0=view["strategy_d0"],runtime_snapshot=view["runtime_snapshot"],actor=result["actor"],action_id="next",move_id="tackle",action_order={},path=(proceed["branch_id"],))
    assert len(nxt["branches"])==1 and nxt["branches"][0]["kind"]=="confusion_snaps_out_and_executes"
    assert nxt["branches"][0]["duration_identity"]==proceed["duration_identity"]

def test_initial_duration_is_materialized_once_and_mass_is_exact():
    _,_,result=gate()
    assert sum((fraction(x["probability"]) for x in result["branches"]),Fraction())==1
    assert {x["duration"] for x in result["branches"]}=={2,3,4,5}
    assert set(fraction(x["probability"]) for x in result["branches"])=={Fraction(1,12),Fraction(1,6)}

def test_self_hit_is_typeless_physical_without_move_consequences_or_opponent_damage():
    snapshot,d0,result=gate(duration=3); branch=result["branches"][0]; view=materialize_confusion_branch(strategy_d0=d0,runtime_snapshot=snapshot,authority=result,branch=branch); hit=materialize_confusion_self_hit(runtime_snapshot=view["runtime_snapshot"],actor=result["actor"],gate=result,branch=branch)
    assert hit["status"]=="resolved";assert {hit[k] for k in ("base_power","type","category","critical","stab","contact")}=={40,"typeless","physical",False}
    assert hit["actor"]==hit["target"]==result["actor"] and hit["selected_move_does_not_execute"] is True and len(hit["damage_rolls"])==16
    assert all(row["hp_after"]<row["hp_before"] for row in hit["damage_rolls"])

def test_self_faint_and_narrow_disguise_bridge():
    snapshot,d0,result=gate(duration=3); branch=result["branches"][0]; view=materialize_confusion_branch(strategy_d0=d0,runtime_snapshot=snapshot,authority=result,branch=branch)
    state=deepcopy(view["runtime_snapshot"]["state"]); raw=state["self_side"]["pokemon"][0];raw["current_hp"]=1;raw["pokemon_id"]="mimikyu";raw["species_id"]="mimikyu";raw["disguise_state"]="intact";snapshot=_snapshot(state)
    hit=materialize_confusion_self_hit(runtime_snapshot=snapshot,actor=result["actor"],gate=result,branch=branch);assert all(row["disguise"]["status"]=="broken" and row["hp_after"]==1 for row in hit["damage_rolls"])
    raw["disguise_state"]="broken";snapshot=_snapshot(state);hit=materialize_confusion_self_hit(runtime_snapshot=snapshot,actor=result["actor"],gate=result,branch=branch);assert all(row["self_fainted"] for row in hit["damage_rolls"])

def test_switch_retires_confusion_and_progression():
    snapshot,_,owner=inputs();state=deepcopy(snapshot["state"]);state["self_side"]["pokemon"][1]=deepcopy(state["self_side"]["pokemon"][0]);state["self_side"]["pokemon"][1]["pokemon_id"]="bench";state["self_side"]["pokemon"][1].update(current_confusion="none",champions_confusion_progression=None)
    event={"observation_id":"switch","observation_sequence":2,"planned_effect":"switch_active","trust":"user_confirmed_observation","turn_number":2,"side":"self","switch_out_slot_index":0,"switch_out_pokemon_id":owner["pokemon_id"],"switch_in_slot_index":1,"switch_in_pokemon_id":"bench"};result=project_atomic_transition(state,{"session_id":state["session_id"],"status":"planned","conflicts":[],"ordered_steps":[event]},state["session_id"]);assert result["status"]=="ready_with_projected_state";assert result["projected_state"]["self_side"]["pokemon"][0]["current_confusion"]=="none" and result["projected_state"]["self_side"]["pokemon"][0]["champions_confusion_progression"] is None

def pair(*,duration=3,own_hp=100,order="own_first"):
    from tests.test_fixed_two_hit_immediate_move_pair_integration import _fixed_two_action,_order
    from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
    from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
    from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
    snapshot,d0,owner=inputs(duration=duration);state=deepcopy(snapshot["state"]);state["self_side"]["pokemon"][0]["current_hp"]=own_hp;snapshot=_snapshot(state);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=owner);own=_fixed_two_action(d0,move_id="tackle");own["move_metadata_authority"]["metadata"].pop("min_hits");own["move_metadata_authority"]["metadata"].pop("max_hits")
    known=freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0,runtime_snapshot=snapshot,canonical_move_metadata_authorities={m:_metadata(m) for m in MOVES});responses=freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0,runtime_snapshot=snapshot,opponent_known_move_authority=known);opponent=next(x for x in responses["actions"] if x["action_id"]=="opponent_attack:tackle")
    return materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=_order(d0,own,opponent,order))

def test_pair_self_hit_has_no_selected_attack_and_execute_path_does():
    result=pair();assert result["status"]=="evaluable",result;assert result["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    self_hit=[path for path in result["terminal_paths"] if path["actions"][0]["state"]=="confusion_self_hit"];executed=[path for path in result["terminal_paths"] if path["actions"][0]["state"]=="confusion_selected_action_executes"]
    assert self_hit and executed and all("attack_leaf" not in path["actions"][0] and "self_hit" in path["actions"][0] for path in self_hit)
    assert all("attack_leaf" in path["actions"][0] for path in executed)

def test_self_faint_cancels_selected_action_and_pending_opponent_action():
    result=pair(own_hp=1);assert result["status"]=="evaluable",result
    rows=[path for path in result["terminal_paths"] if path["actions"][0]["state"]=="confusion_self_hit"]
    assert rows and all(path["actions"][1]["state"]=="cancelled_due_to_faint" for path in rows)

def test_pair_ledger_replays_and_rejects_self_hit_forgery():
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    result=pair();assert normalize_exact_immediate_action_pair_outcome_ledger(pair=result)["status"]=="evaluable"
    forged=deepcopy(result); event=next(path["actions"][0] for path in forged["terminal_paths"] if path["actions"][0]["state"]=="confusion_self_hit");event["self_hit"]["critical"]=True
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"]=="rejected"

def test_sleep_cancel_skips_confusion_and_wake_then_checks_it():
    from tests.test_champions_sleep_freeze_action_gate import inputs as status_inputs
    from tests.test_fixed_two_hit_immediate_move_pair_integration import _fixed_two_action,_order
    from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
    from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
    from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
    from llm.advisor_reducer_state_model import state_fingerprint
    snapshot,_,owner=status_inputs("sleep",prior=0,duration=2);state=deepcopy(snapshot["state"]);raw=state["self_side"]["pokemon"][0];raw["current_confusion"]="confused";raw["confusion_provenance"]={"event_kind":"current_confusion_observed","trust":"user_confirmed_observation","turn_number":1,"state":"confused"};raw["champions_confusion_progression"]={"schema_version":"champions-confusion-progression-v1","owner":owner,"state":"confused","origin_id":"c1","established_turn":1,"prior_opportunities":0,"duration":3,"confusion_observation":deepcopy(raw["confusion_provenance"]),"observed_turn":1,"provenance":"test"};snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)};d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=owner);own=_fixed_two_action(d0,move_id="tackle");own["move_metadata_authority"]["metadata"].pop("min_hits");own["move_metadata_authority"]["metadata"].pop("max_hits")
    known=freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0,runtime_snapshot=snapshot,canonical_move_metadata_authorities={m:_metadata(m) for m in MOVES});responses=freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0,runtime_snapshot=snapshot,opponent_known_move_authority=known);opponent=next(x for x in responses["actions"] if x["action_id"]=="opponent_attack:tackle");result=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=_order(d0,own,opponent,"own_first"))
    assert result["status"]=="evaluable",result
    blocked=[p for p in result["terminal_paths"] if p["actions"][0]["state"]=="cancelled_sleep"]
    assert blocked and all(not any(e.get("state")=="confusion_self_hit" for e in p["actions"]) for p in blocked)
