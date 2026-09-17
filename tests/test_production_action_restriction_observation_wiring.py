"""End-to-end regressions for explicit production restriction observations."""
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_action_restriction_observation import admit_action_restriction_observation
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
from llm.advisor_switch_hazard_authority import build_switch_hazard_context

def _manager():
    state=create_unknown_bootstrap_battle_state("s","pikachu","eevee",self_roster={0:"pikachu",1:"raichu"},opponent_roster={0:"eevee",1:"vaporeon"})["state"]
    for side in ("self_side", "opponent_side"):
        for pokemon in state[side]["pokemon"].values():
            pokemon.update(current_hp=90,max_hp=100,fainted=False,current_ability="static")
            pokemon["current_ability_provenance"]={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1}
            pokemon["stat_stages"]={key:0 for key in ("attack","defense","special-attack","special-defense","speed","accuracy","evasion")}
    state["switch_hazard_context"]=build_switch_hazard_context(session_id="s",affected_side="self",stealth_rock="absent",spikes_layers=0,toxic_spikes_layers=0,sticky_web="absent")
    state["field"]["weather"]="none"; state["field"]["weather_provenance"]={"event_kind":"current_weather_observed","trust":"user_confirmed_observation","turn_number":1}
    return BattleObservationRuntimeSessionManager.create("s",state)["manager"]
def _admit(m, restriction, operation, turn, side="self", action="action:restriction"):
    return admit_action_restriction_observation(runtime_session_manager=m,captured_session_id="s",side=side,restriction=restriction,operation=operation,source_action_id=action if operation=="applied" else None,turn_number=turn)
def _history(m, side="self", move="tackle", action="action:move"):
    return admit_previous_action_history_observation(runtime_session_manager=m,captured_session_id="s",side=side,execution_move_id=move,selected_move_id=move,source_action_id=action,result_class="success",turn_number=1)
def _row(m, name, side="self"): return m.read_state()["state"][f"current_{name}_restrictions"][side]

def test_taunt_production_lifecycle_is_three_affected_turns():
    m=_manager(); result=_admit(m,"taunt","applied",1)
    assert result["status"]=="resolved" and result["observation"]["source_move_id"]=="taunt" and _row(m,"taunt")["remaining_target_turns"]==3
    assert _admit(m,"taunt","completed",2)["status"]=="resolved" and _row(m,"taunt")["remaining_target_turns"]==2
    assert _admit(m,"taunt","completed",3)["status"]=="resolved" and _row(m,"taunt")["remaining_target_turns"]==1
    assert _admit(m,"taunt","completed",4)["status"]=="resolved" and _row(m,"taunt")["state"]=="not_active" and _row(m,"taunt")["retired_reason"]=="expired"

def test_encore_and_disable_derive_exact_production_last_move_and_expire():
    for restriction, turns, field in (("encore",3,"locked_move_id"),("disable",4,"disabled_move_id")):
        m=_manager(); assert _history(m,move="tackle")["status"]=="resolved"; applied=_admit(m,restriction,"applied",1)
        row=_row(m,restriction); history=m.read_state()["state"]["self_side"]["pokemon"][0]["last_executed_move"]
        assert applied["status"]=="resolved" and row[field]=="tackle" and row["last_used_execution_id"]==history["execution_id"] and row["remaining_target_turns"]==turns
        for turn in range(2,turns+2): assert _admit(m,restriction,"completed",turn)["status"]=="resolved"
        assert _row(m,restriction)["retired_reason"]=="expired"

def test_missing_history_and_malformed_or_stale_requests_fail_closed_without_append():
    m=_manager(); before=m.read_collection_snapshot()["ordered_observations"]
    assert _admit(m,"encore","applied",1)["status"]=="incomplete"; assert _admit(m,"disable","applied",1)["status"]=="incomplete"
    assert admit_action_restriction_observation(runtime_session_manager=m,captured_session_id="old",side="self",restriction="taunt",operation="applied",source_action_id="x",turn_number=1)["status"]=="rejected"
    assert _admit(m,"taunt","completed",1)["status"]=="rejected" and m.read_collection_snapshot()["ordered_observations"]==before

def test_production_switch_retires_each_active_restriction_without_inheritance():
    for restriction in ("taunt","encore","disable"):
        m=_manager();
        if restriction!="taunt": _history(m)
        assert _admit(m,restriction,"applied",1)["status"]=="resolved"
        assert admit_pokemon_switch_observation(runtime_session_manager=m,captured_session_id="s",side="self",switch_in_slot_index=1,switch_in_pokemon_id="raichu",turn_number=2)["status"]=="resolved"
        row=_row(m,restriction); assert row["state"]=="not_active" and row["retired_reason"]=="switch_out" and row["owner"]["pokemon_id"]=="pikachu"
