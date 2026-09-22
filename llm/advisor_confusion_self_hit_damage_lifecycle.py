"""Deterministic Disguise lifecycle consequence of one exact observed confusion self-hit."""
from copy import deepcopy
from typing import Mapping

DISGUISE_BROKEN_DERIVED="confusion_self_hit_disguise_broken_derived"
DERIVED_KINDS=frozenset({DISGUISE_BROKEN_DERIVED})
SOURCE="runtime_confusion_self_hit_damage_lifecycle_v1"
TRUST="mechanics_derived_runtime"

def derive_disguise_break(*, source_damage_observation, observation_id, observation_sequence):
    source=source_damage_observation if isinstance(source_damage_observation,Mapping) else {}
    payload=source.get("payload") if isinstance(source.get("payload"),Mapping) else {}
    if (source.get("event_kind")!="confusion_self_hit_damage_observed"
            or payload.get("disguise_outcome")!="intact_to_broken"
            or not isinstance(observation_id,str) or not observation_id
            or not isinstance(observation_sequence,int) or isinstance(observation_sequence,bool)
            or observation_sequence<=source.get("observation_sequence",0)):
        return {"status":"rejected","reason":"invalid_confusion_self_hit_disguise_source"}
    out={key:deepcopy(payload[key]) for key in (
        "decision_point","action_id","move_id","confusion_origin_id","source_confusion_observation_id"
    )}
    out.update(source_damage_observation_id=source["observation_id"],disguise_before="intact",disguise_after="broken")
    return {"status":"confirmed","observation":{
        "event_kind":DISGUISE_BROKEN_DERIVED,"session_id":source["session_id"],
        "turn_number":source["turn_number"],"observation_id":observation_id,
        "observation_sequence":observation_sequence,"side":source["side"],
        "slot_index":source["slot_index"],"pokemon_id":source["pokemon_id"],
        "payload":out,"source":SOURCE,"trust":TRUST,
        "scope":"confusion_self_hit_damage_lifecycle","reducer_eligibility":"candidate",
    }}
