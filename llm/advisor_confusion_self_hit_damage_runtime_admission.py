"""Atomic production admission for exact observed confusion self-hit HP consequences."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_confusion_self_hit_damage_lifecycle import derive_disguise_break
from llm.advisor_detached_observed_rng_reconciliation import (
    reconcile_observed_confusion_self_hit_damage_rng,
    validate_historical_confusion_self_hit,
)
from llm.advisor_exact_hp_zero_faint_runtime_lifecycle import (
    build_exact_hp_zero_faint_confirmation_pair,
)
from llm.advisor_lifecycle_confirmation import (
    CONFUSION_SELF_HIT_DAMAGE_SOURCE,
    HP_TRANSITION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def admit_observed_confusion_self_hit_damage_result(
    *, runtime_session_manager, captured_session_id, retained_prediction,
    turn_number, hp_after, disguise_outcome,
):
    if (not isinstance(runtime_session_manager,BattleObservationRuntimeSessionManager)
            or not isinstance(turn_number,int) or isinstance(turn_number,bool) or turn_number<1
            or not isinstance(hp_after,int) or isinstance(hp_after,bool) or hp_after<0
            or disguise_outcome not in {"not_applicable","already_broken","intact_to_broken"}):
        return _result("rejected","invalid_confusion_self_hit_damage_request")
    retained=validate_historical_confusion_self_hit(retained_prediction)
    if retained.get("status")!="resolved":
        return _result(retained.get("status","rejected"),retained.get("reason","historical_confusion_self_hit_invalid"))
    if retained.get("session_id")!=captured_session_id:
        return _result("rejected","confusion_self_hit_damage_stale_session")
    if retained.get("turn_number")!=turn_number:
        return _result("rejected","confusion_self_hit_damage_stale_turn")

    collection=runtime_session_manager.read_collection_snapshot()
    primary_rows=[
        row for row in collection.get("ordered_observations",[])
        if _primary_matches(row,retained)
    ]
    if len(primary_rows)!=1:
        return _result("rejected" if primary_rows else "incomplete",
                       "ambiguous_confusion_self_hit_primary_observation" if primary_rows else "confusion_self_hit_primary_observation_missing")
    primary=primary_rows[0]
    snapshot=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status")!="runtime_snapshot_ready":
        return _result("rejected","confusion_self_hit_damage_runtime_snapshot_unavailable")
    actor=retained["actor"]
    state=snapshot.get("state")
    side_state=state.get(f"{actor['side']}_side") if isinstance(state,Mapping) else None
    if not isinstance(side_state,Mapping) or side_state.get("active_slot_index")!=actor["slot_index"]:
        return _result("rejected","confusion_self_hit_damage_actor_not_active")
    receipt_id=f"{captured_session_id}:confusion-self-hit-damage:{retained['action_id']}:result"
    pokemon=_pokemon(snapshot.get("state"),actor)
    if not isinstance(pokemon,Mapping) or pokemon.get("pokemon_id")!=actor.get("pokemon_id"):
        return _result("rejected","confusion_self_hit_damage_actor_unavailable")
    progression=pokemon.get("champions_confusion_progression")
    if (pokemon.get("current_confusion")!="confused" or not isinstance(progression,Mapping)
            or progression.get("origin_id")!=retained["confusion_origin_id"]):
        return _result("rejected","confusion_self_hit_damage_confusion_episode_stale")
    pending=state.get("pending_confusion_action_execution_context") if isinstance(state,Mapping) else None
    if (not isinstance(pending,Mapping) or pending.get("actor")!=actor
            or pending.get("decision_point")!=retained["decision_point"]
            or pending.get("action_id")!=retained["action_id"]
            or pending.get("move_id")!=retained["move_id"]
            or pending.get("confusion_origin_id")!=retained["confusion_origin_id"]
            or pending.get("outcome_class")!="confusion_self_hit"):
        return _result("rejected","confusion_self_hit_damage_action_context_stale")
    existing=next((row for row in collection.get("ordered_observations",[]) if row.get("observation_id")==receipt_id),None)
    if existing is not None:
        existing_payload=existing.get("payload") if isinstance(existing,Mapping) else None
        if not isinstance(existing_payload,Mapping):
            return _result("rejected","conflicting_confusion_self_hit_damage_evidence")
        expected_payload={**dict(existing_payload),"hp_after":hp_after,"self_fainted":hp_after==0,"disguise_outcome":disguise_outcome}
        if existing_payload!=expected_payload or not _receipt_matches(existing,retained,primary,existing_payload):
            return _result("rejected","conflicting_confusion_self_hit_damage_evidence")
        rec=reconcile_observed_confusion_self_hit_damage_rng(
            retained_prediction=retained,primary_confusion_observation=primary,damage_observation=existing)
        return {"status":"resolved","reason":"idempotent_reuse","idempotent":True,
                "observation":deepcopy(existing),"observations":[deepcopy(existing)],
                "runtime_snapshot":snapshot,"reconciliation":rec,"replacement_boundary":None}
    current_hp=pokemon.get("current_hp")
    rows=retained["canonical_damage_rolls"]
    hp_before=rows[0]["hp_before"]
    if any(row.get("hp_before")!=hp_before for row in rows):
        return _result("rejected","historical_confusion_self_hit_hp_before_diverged")
    if current_hp!=hp_before:
        return _result("rejected","confusion_self_hit_damage_pre_hp_runtime_mismatch")

    predicted_disguise={_observed_disguise(row.get("disguise",{}).get("status")) for row in rows}
    if len(predicted_disguise)!=1:
        return _result("rejected","historical_confusion_self_hit_disguise_diverged")
    if disguise_outcome not in predicted_disguise:
        return _result("rejected","confusion_self_hit_damage_disguise_mismatch")
    if disguise_outcome=="intact_to_broken" and pokemon.get("disguise_state")!="intact":
        return _result("incomplete","confusion_self_hit_disguise_runtime_not_intact")
    if disguise_outcome=="already_broken" and pokemon.get("disguise_state")!="broken":
        return _result("incomplete","confusion_self_hit_disguise_runtime_not_broken")

    payload={
        "decision_point":retained["decision_point"],"action_id":retained["action_id"],
        "move_id":retained["move_id"],"confusion_origin_id":retained["confusion_origin_id"],
        "source_confusion_observation_id":primary["observation_id"],
        "hp_before":hp_before,"hp_after":hp_after,"self_fainted":hp_after==0,
        "disguise_outcome":disguise_outcome,
    }
    boundary=LifecycleConfirmationBoundary(captured_session_id,{actor["side"]:actor})
    receipt=boundary.confirm(
        event_kind="confusion_self_hit_damage_observed",payload=payload,
        session_id=captured_session_id,source=CONFUSION_SELF_HIT_DAMAGE_SOURCE,trust=USER_TRUST,
        confirmed=True,side=actor["side"],slot_index=actor["slot_index"],pokemon_id=actor["pokemon_id"],
        observation_id=receipt_id,turn_number=retained["turn_number"])
    if receipt.get("status")!="confirmed":
        return _result("rejected","confusion_self_hit_damage_confirmation_rejected")
    seq=runtime_session_manager.allocate_observation_sequence()
    if seq.get("status")!="allocated":
        return _result("rejected","confusion_self_hit_damage_sequence_unavailable")
    receipt["observation"]["observation_sequence"]=seq["observation_sequence"]
    if receipt["observation"]["observation_sequence"]<=primary.get("observation_sequence",0):
        return _result("rejected","confusion_self_hit_damage_observation_order_invalid")

    reconciliation=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=primary,
        damage_observation=receipt["observation"])
    if reconciliation.get("status")!="resolved" or reconciliation.get("match_outcome")=="incompatible_observation":
        return {"status":"rejected","reason":"incompatible_confusion_self_hit_damage_observation",
                "idempotent":False,"observation":deepcopy(receipt["observation"]),"observations":[],
                "runtime_snapshot":snapshot,"reconciliation":reconciliation,"replacement_boundary":None}

    confirmations=[receipt]
    hp_id=f"{captured_session_id}:confusion-self-hit-damage:{retained['action_id']}:hp"
    faint_id=f"{captured_session_id}:confusion-self-hit-damage:{retained['action_id']}:faint"
    if hp_after<hp_before:
        if hp_after==0:
            pair=build_exact_hp_zero_faint_confirmation_pair(
                session_id=captured_session_id,owner=actor,hp_before=hp_before,
                turn_number=retained["turn_number"],source_event_id=retained["action_id"],
                hp_observation_id=hp_id,faint_observation_id=faint_id)
            if pair is None:
                return _result("rejected","confusion_self_hit_hp_faint_confirmation_rejected")
            pair[0]["observation"]["related_observation_id"]=receipt_id
            confirmations.extend(pair)
        else:
            hp=boundary.confirm(
                event_kind="exact_hp_transition_observed",
                payload={"hp_before":hp_before,"hp_after":hp_after},
                session_id=captured_session_id,source=HP_TRANSITION_SOURCE,trust=USER_TRUST,
                confirmed=True,side=actor["side"],slot_index=actor["slot_index"],pokemon_id=actor["pokemon_id"],
                observation_id=hp_id,related_observation_id=receipt_id,turn_number=retained["turn_number"])
            if hp.get("status")!="confirmed":
                return _result("rejected","confusion_self_hit_hp_confirmation_rejected")
            confirmations.append(hp)

    for row in confirmations[1:]:
        allocated=runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status")!="allocated":
            return _result("rejected","confusion_self_hit_consequence_sequence_unavailable")
        row["observation"]["observation_sequence"]=allocated["observation_sequence"]

    if disguise_outcome=="intact_to_broken":
        allocated=runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status")!="allocated":
            return _result("rejected","confusion_self_hit_disguise_sequence_unavailable")
        derived=derive_disguise_break(
            source_damage_observation=receipt["observation"],
            observation_id=f"{captured_session_id}:confusion-self-hit-damage:{retained['action_id']}:disguise",
            observation_sequence=allocated["observation_sequence"])
        if derived.get("status")!="confirmed":
            return _result("rejected","confusion_self_hit_disguise_derivation_rejected")
        confirmations.append(derived)

    preview_rows=deepcopy(collection.get("ordered_observations",[]))
    preview_rows.extend(deepcopy(row["observation"]) for row in confirmations)
    preview={**collection,"ordered_observations":sorted(preview_rows,key=lambda row:(row["observation_sequence"],row["observation_id"]))}
    preview_result=runtime_session_manager.preview(captured_session_id,preview)
    if preview_result.get("status")!="preview_ready":
        return _result("rejected","confusion_self_hit_damage_preview_rejected")
    admitted=runtime_session_manager.admit_confirmations_atomically(captured_session_id,confirmations)
    if admitted.get("status") not in {"added","duplicate"}:
        return _result("rejected","confusion_self_hit_damage_admission_rejected")
    if runtime_session_manager.apply(captured_session_id,runtime_session_manager.read_collection_snapshot()).get("status") not in {"applied","already_applied"}:
        return _result("rejected","confusion_self_hit_damage_application_rejected")
    committed=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    target=_pokemon(committed.get("state"),actor)
    if not isinstance(target,Mapping) or target.get("current_hp")!=hp_after or target.get("fainted") is not (hp_after==0):
        return _result("rejected","confusion_self_hit_damage_committed_runtime_mismatch")
    if disguise_outcome=="intact_to_broken" and target.get("disguise_state")!="broken":
        return _result("rejected","confusion_self_hit_disguise_committed_runtime_mismatch")
    replacement=None
    if hp_after==0:
        faint=next(row["observation"] for row in confirmations if row["observation"].get("event_kind")=="pokemon_faint_observed")
        replacement={"status":"replacement_required_after_faint","fainted_owner":deepcopy(actor),
                     "hp_transition_observation_id":hp_id,"faint_observation_id":faint_id,
                     "terminal_sequence":faint["observation_sequence"],
                     "provenance":"runtime_exact_hp_zero_faint_lifecycle_v1"}
    return {"status":"resolved","reason":None,"idempotent":False,
            "observation":deepcopy(receipt["observation"]),
            "observations":[deepcopy(row["observation"]) for row in confirmations],
            "runtime_snapshot":committed,"reconciliation":reconciliation,
            "replacement_boundary":replacement}


def _primary_matches(row,retained):
    payload=row.get("payload") if isinstance(row,Mapping) else None
    actor=retained["actor"]
    return (
        isinstance(payload,Mapping)
        and row.get("event_kind")=="pending_confusion_action_execution_observed"
        and row.get("source")=="ui_pending_confusion_action_execution_confirmation"
        and row.get("trust")=="user_confirmed_observation"
        and row.get("session_id")==retained["session_id"]
        and row.get("turn_number")==retained["turn_number"]
        and (row.get("side"),row.get("slot_index"),row.get("pokemon_id"))
        ==(actor["side"],actor["slot_index"],actor["pokemon_id"])
        and payload.get("decision_point")==retained["decision_point"]
        and payload.get("action_id")==retained["action_id"]
        and payload.get("move_id")==retained["move_id"]
        and payload.get("confusion_origin_id")==retained["confusion_origin_id"]
        and payload.get("outcome_class")=="confusion_self_hit"
    )


def _receipt_matches(row,retained,primary,payload):
    actor=retained["actor"]
    return (
        row.get("event_kind")=="confusion_self_hit_damage_observed"
        and row.get("source")==CONFUSION_SELF_HIT_DAMAGE_SOURCE and row.get("trust")==USER_TRUST
        and row.get("session_id")==retained["session_id"] and row.get("turn_number")==retained["turn_number"]
        and (row.get("side"),row.get("slot_index"),row.get("pokemon_id"))
        ==(actor["side"],actor["slot_index"],actor["pokemon_id"])
        and row.get("payload")==payload
        and payload.get("source_confusion_observation_id")==primary.get("observation_id")
    )


def _observed_disguise(status):
    return "intact_to_broken" if status=="broken" else status


def _pokemon(state,actor):
    side=state.get(f"{actor['side']}_side") if isinstance(state,Mapping) else None
    roster=side.get("pokemon") if isinstance(side,Mapping) else None
    if not isinstance(roster,Mapping):
        return None
    return roster.get(actor["slot_index"],roster.get(str(actor["slot_index"])))


def _result(status,reason):
    return {"status":status,"reason":reason,"idempotent":False,"observation":None,
            "observations":[],"runtime_snapshot":None,"reconciliation":None,
            "replacement_boundary":None}
