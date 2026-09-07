"""Narrow detached Champions confusion-application authority.

The module owns no generic status application.  It consumes a move-success
result and applies only the catalogued confusion effects to the existing
``current_confusion`` / progression representation.
"""
from copy import deepcopy
from typing import Mapping
from llm.advisor_observed_damage_application import apply_canonical_stage_delta
from llm.advisor_identity_groundedness import project_identity_groundedness
from llm.advisor_reducer_state_model import state_fingerprint

SCHEMA="champions-confusion-application-authority-v1"
CATALOG={
 "confuse-ray":{"kind":"pure_status","accuracy":100,"stage":None},
 "swagger":{"kind":"pure_status","accuracy":85,"stage":("attack",2)},
 "teeter-dance":{"kind":"pure_status","accuracy":100,"stage":None},
 "dynamic-punch":{"kind":"damaging_secondary","accuracy":50,"stage":None},
}

def _owner(raw,owner): return raw.get(f"{owner['side']}_side",{}).get("pokemon",{}).get(owner["slot_index"])
def _binding(d0,source,target,action):
    return isinstance(d0,Mapping) and d0.get("status")=="resolved" and d0.get("active_owners",{}).get(source.get("side"))==dict(source) and d0.get("active_owners",{}).get(target.get("side"))==dict(target) and source.get("side")!=target.get("side") and isinstance(action,Mapping) and isinstance(action.get("action_id"),str) and isinstance(action.get("identity"),str)

def freeze_champions_confusion_application(*,strategy_d0,runtime_snapshot,source,target,action,move_success_authority,path=(),reflection_authority=None):
    """Freeze one selected catalogued application after its native success check."""
    if not _binding(strategy_d0,source,target,action): return {"status":"rejected","reason":"confusion_application_binding_invalid"}
    move=action["identity"]; rule=CATALOG.get(move)
    if rule is None:return {"status":"unsupported","reason":"move_not_in_champions_confusion_application_catalog"}
    if not isinstance(runtime_snapshot,Mapping) or runtime_snapshot.get("state_fingerprint")!=strategy_d0.get("source_runtime_fingerprint"):return {"status":"rejected","reason":"stale_confusion_application_runtime"}
    success=move_success_authority
    base={"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(strategy_d0["decision_owner"]),"source":deepcopy(source),"target":deepcopy(target),"action_id":action["action_id"],"move_id":move,"path":tuple(path)}
    if not isinstance(success,Mapping) or any(success.get(k)!=base.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","source","target","action_id","move_id")) or success.get("status")!="resolved":return {"status":"incomplete","reason":"move_success_authority_missing_or_foreign",**base}
    outcome=success.get("outcome")
    if outcome not in {"hit","missed","blocked_by_protection"}:return {"status":"rejected","reason":"move_success_outcome_invalid",**base}
    if rule["kind"] == "damaging_secondary" and outcome == "hit" and success.get("damage_resolved") is not True:
        return {"status":"rejected","reason":"damaging_confusion_secondary_requires_post_hit_authority",**base}
    if reflection_authority is not None:
        if not isinstance(reflection_authority,Mapping) or any(reflection_authority.get(k)!=base.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","source","target","action_id","move_id")):
            return {"status":"incomplete","reason":"reflection_authority_missing_or_foreign",**base}
        reflection_outcome=reflection_authority.get("outcome")
        if reflection_outcome=="reflected":
            return {"status":"incomplete","reason":"reflected_confusion_application_owner_unavailable",**base}
        if reflection_outcome!="not_reflected":
            return {"status":"incomplete","reason":"reflection_authority_incomplete",**base}
    state=runtime_snapshot["state"];raw=_owner(state,target); src=_owner(state,source)
    if not isinstance(raw,Mapping) or not isinstance(src,Mapping):return {"status":"rejected","reason":"confusion_application_active_identity_missing",**base}
    if move=="teeter-dance":
        battle_format=state.get("field",{}).get("battle_format") if isinstance(state.get("field"),Mapping) else None
        if battle_format is None:return {"status":"incomplete","reason":"teeter_dance_battle_format_unknown",**base}
        if battle_format!="singles":return {"status":"unsupported","reason":"teeter_dance_singles_only",**base}
    abilities={side:_owner(state,owner).get("current_ability") for side,owner in strategy_d0["active_owners"].items()}; exact=all(isinstance(v,str) and v for v in abilities.values())
    if not exact:return {"status":"incomplete","reason":"confusion_application_ability_unknown",**base}
    gas="neutralizing-gas" in abilities.values(); prevent=None
    if outcome=="missed":prevent="move_missed"
    elif outcome=="blocked_by_protection":prevent="blocked_by_protection"
    elif raw.get("current_confusion")=="unknown":return {"status":"incomplete","reason":"target_confusion_state_unknown",**base}
    elif raw.get("current_confusion")=="confused":prevent="already_confused_no_new_application"
    elif raw.get("current_ability")=="own-tempo" and not gas:prevent="blocked_by_own_tempo"
    else:
        field=state.get("field",{}); terrain=field.get("terrain") if isinstance(field,Mapping) else None
        if terrain=="misty":
            grounded=project_identity_groundedness(state,side=target["side"]).get("status")
            if grounded=="unknown":return {"status":"incomplete","reason":"misty_terrain_groundedness_unknown",**base}
            if grounded=="grounded":prevent="blocked_by_misty_terrain"
        side=state.get(f"{target['side']}_side",{}); conditions=side.get("side_conditions") if isinstance(side,Mapping) else None
        if prevent is None and conditions is None:return {"status":"incomplete","reason":"safeguard_authority_unknown",**base}
        if prevent is None and "safeguard" in conditions:prevent="blocked_by_safeguard"
        substitute=state.get("substitute_state_context")
        if prevent is None and isinstance(substitute,Mapping):
            rows=substitute.get("states",[]); match=[x for x in rows if isinstance(x,Mapping) and x.get("owner")==dict(target)]
            if len(match)!=1:return {"status":"incomplete","reason":"substitute_authority_unknown",**base}
            if match[0].get("state")=="known_active" and src.get("current_ability")!="infiltrator":prevent="blocked_by_substitute"
            elif match[0].get("state")=="unknown":return {"status":"incomplete","reason":"substitute_authority_unknown",**base}
    authority={"status":"resolved","schema_version":SCHEMA,**base,"application_kind":rule["kind"],"move_success_authority":deepcopy(success),"target_confusion_before":raw.get("current_confusion","none"),"target_ability_authority":{"abilities":abilities,"suppressed":gas},"prevention_outcome":prevent or "applies","swagger_stage":rule["stage"],"reflection_authority":deepcopy(reflection_authority),"provenance":"champions_catalogued_confusion_application_v1"}
    authority["validation_request"]={"strategy_d0":deepcopy(strategy_d0),"runtime_snapshot":deepcopy(runtime_snapshot),"source":deepcopy(source),"target":deepcopy(target),"action":deepcopy(action),"move_success_authority":deepcopy(move_success_authority),"path":tuple(path),"reflection_authority":deepcopy(reflection_authority)}
    return authority

def validate_champions_confusion_application(authority):
    """Accept only an authority reproduced from its immutable application inputs."""
    try:
        if not isinstance(authority,Mapping) or authority.get("status")!="resolved" or authority.get("schema_version")!=SCHEMA: raise ValueError()
        request=authority["validation_request"]
        if not isinstance(request,Mapping): raise ValueError()
        expected=freeze_champions_confusion_application(**request)
        if expected!=authority: raise ValueError()
        return {"status":"resolved","authority":deepcopy(authority)}
    except (KeyError,TypeError,ValueError):
        return {"status":"rejected","reason":"confusion_application_provenance_invalid"}

def materialize_champions_confusion_application(*,authority,runtime_snapshot):
    validation=validate_champions_confusion_application(authority)
    if validation.get("status")!="resolved": return validation
    if runtime_snapshot.get("state_fingerprint")!=authority.get("source_runtime_fingerprint"):return {"status":"rejected","reason":"foreign_confusion_application_runtime"}
    state=deepcopy(runtime_snapshot["state"]); target=authority["target"];raw=_owner(state,target); outcome=authority["prevention_outcome"]; stage=None
    if authority["swagger_stage"] is not None and outcome not in {"move_missed","blocked_by_protection"}:
        stat,delta=authority["swagger_stage"];before=raw.get("stat_stages",{}).get(stat)
        if not isinstance(before,int) or not -6<=before<=6:return {"status":"incomplete","reason":"swagger_target_attack_stage_unknown"}
        after=apply_canonical_stage_delta(before,delta);raw["stat_stages"][stat]=after;stage={"stat":stat,"pre_stage":before,"delta":delta,"post_stage":after}
    if outcome=="applies":
        raw["current_confusion"]="confused"; observation={"event_kind":"current_confusion_observed","trust":"user_confirmed_observation","turn_number":0,"state":"confused","hypothetical_provenance":"champions_confusion_application_v1"};raw["confusion_provenance"]=observation
        raw["champions_confusion_progression"]={"schema_version":"champions-confusion-progression-v1","owner":deepcopy(target),"state":"confused","origin_id":f"{authority['action_id']}:confusion","established_turn":1,"prior_opportunities":0,"duration":None,"confusion_observation":deepcopy(observation),"observed_turn":1,"provenance":"detached_champions_confusion_establishment_v1"}
    snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}
    return {"status":"resolved","runtime_snapshot":snapshot,"outcome":outcome,"confusion_applied":outcome=="applies","swagger_stage_transition":stage,"authority":deepcopy(authority),"provenance":"detached_champions_confusion_application_v1"}
