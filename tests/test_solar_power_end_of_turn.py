from copy import deepcopy
from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_solar_power_end_of_turn import project_solar_power_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import _project_bounded_eot


def _pre(*, hp=80, ability="solar-power", condition="none"):
    active=lambda side,pid,value: {"session_id":"solar-eot","side":side,"slot_index":0,"pokemon_id":pid,"current_hp":value,"max_hp":100,"fainted":value==0}
    state={"schema_version":"deterministic-transition-preview-v1","active":{"self":active("self","solar-user",hp),"opponent":active("opponent","target",80)},"current_state":{"current_state_session_id":"solar-eot","field_state_context":{"current_field":{"weather":"none","side_effects":[]}},"current_hp_context":{"current_hp":[{"side":"self","current_hp":hp,"maximum_hp":100},{"side":"opponent","current_hp":80,"maximum_hp":100}]},"ability_context":{"current_abilities":[{"side":"self","ability":ability,"status":"user_confirmed","source":"user_confirmed_current_ability"},{"side":"opponent","ability":"pressure","status":"user_confirmed","source":"user_confirmed_current_ability"}]},"condition_context":{"current_conditions":[{"side":"self","condition_type":condition,"status":"user_confirmed","source":"user_confirmed_current_condition"},{"side":"opponent","condition_type":"none","status":"user_confirmed","source":"user_confirmed_current_condition"}]},"direct_mechanics_context":{"attacker":{"current_hp":hp,"max_hp":100},"defender":{"current_hp":80,"max_hp":100}}}}
    fp=fingerprint_transition_preview_state(state); projected=project_field_weather(branch_state=state,source_fingerprint=fp,frozen_field_state={"current_field":{"weather":"rain","side_effects":[]}}); sun=apply_supported_switch_entry_weather(branch_state=projected["next_state"],source_fingerprint=projected["resulting_branch_fingerprint"],weather_result={"status":"complete","outcome":"weather_set","weather_before":"rain","weather_after":"sun"})
    return state,{"status":"resolved","next_state":sun["next_state"],"boundary":{"phase":"pre_end_of_turn"}}


def _row(result): return next(x for x in result["eot_consequence_trace"] if x["owner"]["side"]=="self")


def test_solar_power_sun_damage_lethal_handoff_and_dispatch():
    source,pre=_pre(); frozen=deepcopy(pre["next_state"]); result=project_solar_power_end_of_turn(pre_end_of_turn=pre)
    assert result["status"]=="resolved" and source["active"]["self"]["current_hp"]==80 and pre["next_state"]==frozen
    assert _row(result)["damage"]==12 and _row(result)["post_hp"]==68 and result["resulting_branch_fingerprint"]!=fingerprint_transition_preview_state(pre["next_state"])
    handoff=handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result); assert handoff["status"]=="resolved" and handoff["next_state"]["active"]["self"]["current_hp"]==68 and handoff["next_state"]["branch_field_weather_context"]["weather"]=="sun"
    _,lethal=_pre(hp=10); lethal_result=project_solar_power_end_of_turn(pre_end_of_turn=lethal); assert _row(lethal_result)["guaranteed_ko"] is True and lethal_result["next_state"]["active"]["self"]["fainted"] is True
    assert _row(_project_bounded_eot(pre_end_of_turn=pre))["effect"]=="solar_power_residual"


def test_solar_power_wrong_authority_ordering_and_faint_fail_closed():
    _,pre=_pre(); foreign=deepcopy(pre); foreign["next_state"]["branch_field_weather_context"]["session_id"]="foreign"; assert project_solar_power_end_of_turn(pre_end_of_turn=foreign)=={"status":"rejected","reason":"stale_or_invalid_branch_sun_authority"}
    wrong=deepcopy(pre); wrong["next_state"]["current_state"]["field_state_context"]["current_field"]["weather"]="rain"; assert project_solar_power_end_of_turn(pre_end_of_turn=wrong)=={"status":"rejected","reason":"stale_or_invalid_branch_sun_authority"}
    _,poison=_pre(condition="poison"); assert project_solar_power_end_of_turn(pre_end_of_turn=poison)=={"status":"incomplete","reason":"solar_power_residual_ordering_unresolved"}
    _,fainted=_pre(hp=0); result=project_solar_power_end_of_turn(pre_end_of_turn=fainted); assert _row(result)["outcome"]=="fainted_before_eot" and result["next_state"]["active"]["self"]["current_hp"]==0
