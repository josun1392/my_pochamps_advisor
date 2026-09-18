"""Atomic admission of explicitly observed contact-reactive damage results."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_exact_hp_zero_faint_runtime_lifecycle import (
    SOURCE as HP_ZERO_FAINT_SOURCE,
    build_exact_hp_zero_faint_confirmation_pair,
    validate_exact_hp_zero_faint_confirmation_pair,
)
from llm.advisor_lifecycle_confirmation import (
    CONTACT_REACTIVE_DAMAGE_RESULT_SOURCE,
    EXECUTED_MOVE_SOURCE,
    HP_TRANSITION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    canonical_move_contact_metadata,
)
from llm.advisor_runtime_d0_contact_reactive_damage_authority import (
    freeze_runtime_d0_contact_reactive_damage_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def admit_observed_contact_reactive_damage_result(
    *,
    runtime_session_manager,
    captured_session_id,
    attacker_side,
    move_id,
    source_action_id,
    attacker_hp_after,
    source_hit_actual_damage,
    source_hit_target_routing="target",
    turn_number,
):
    """Commit one exact observed contact-reactive attacker HP result."""
    if (
        not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager)
        or attacker_side not in {"self", "opponent"}
        or not _token(move_id)
        or not _token(source_action_id)
        or not _nonnegative(attacker_hp_after)
        or not _nonnegative(source_hit_actual_damage)
        or source_hit_target_routing not in {"target", "substitute"}
        or not _positive(turn_number)
    ):
        return _result("rejected", "invalid_observed_contact_reactive_damage_request")

    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        status = "rejected" if snapshot.get("status") == "stale_session" else "incomplete"
        return _result(status, "runtime_snapshot_unavailable")

    state = snapshot.get("state")
    attacker = _active_identity(state, attacker_side)
    defender = _active_identity(state, _other(attacker_side))
    if attacker is None or defender is None:
        return _result("rejected", "observed_contact_reactive_damage_owner_unavailable")

    collection = runtime_session_manager.read_collection_snapshot()
    ids = _observation_ids(captured_session_id, source_action_id)
    receipt = _by_id(collection, ids["receipt"])
    hp = _by_id(collection, ids["hp"])
    faint = _by_id(collection, ids["faint"])

    if receipt is not None:
        return _reuse_receipt(
            receipt=receipt,
            hp=hp,
            faint=faint,
            attacker=attacker,
            defender=defender,
            move_id=move_id,
            source_action_id=source_action_id,
            attacker_hp_after=attacker_hp_after,
            source_hit_actual_damage=source_hit_actual_damage,
            source_hit_target_routing=source_hit_target_routing,
            turn_number=turn_number,
            manager=runtime_session_manager,
            snapshot=snapshot,
        )
    if hp is not None or faint is not None:
        return _result("rejected", "incomplete_or_conflicting_observed_contact_reactive_damage_history")

    execution = _execution(collection, captured_session_id, source_action_id)
    if execution is not None and not _execution_matches(execution, attacker, move_id, turn_number):
        return _result("rejected", "conflicting_observed_contact_reactive_damage_source_action")

    current = _pokemon(state, attacker)
    current_hp = current.get("current_hp") if isinstance(current, Mapping) else None
    authority_result = _freeze_authority(
        snapshot=snapshot,
        attacker=attacker,
        defender=defender,
        move_id=move_id,
        source_action_id=source_action_id,
        source_hit_actual_damage=source_hit_actual_damage,
        source_hit_target_routing=source_hit_target_routing,
    )
    authority = authority_result.get("authority")
    d0 = authority_result.get("strategy_d0")
    if authority_result.get("status") != "resolved" or not isinstance(authority, Mapping):
        return _result(
            authority_result.get("status", "rejected"),
            authority_result.get("reason", "contact_reactive_damage_authority_unavailable"),
        )

    if authority.get("outcome") != "applies":
        if not _nonnegative(current_hp):
            return _result("incomplete", "contact_reactive_attacker_hp_unknown")
        if attacker_hp_after != current_hp:
            return _result("rejected", "observed_contact_reactive_damage_post_hp_mismatch")
        return {
            "status": "resolved",
            "reason": authority.get("reason", authority.get("outcome", "no_contact_reactive_damage")),
            "owner": deepcopy(attacker),
            "observations": [],
            "runtime_snapshot": snapshot,
            "strategy_d0": d0,
            "authority": deepcopy(dict(authority)),
            "idempotent": False,
        }

    if authority.get("pre_hp") != current_hp:
        return _result("rejected", "contact_reactive_damage_pre_hp_runtime_mismatch")
    if attacker_hp_after != authority.get("post_hp"):
        return _result("rejected", "observed_contact_reactive_damage_post_hp_mismatch")

    payload = _payload(
        attacker=attacker,
        defender=defender,
        move_id=move_id,
        source_action_id=source_action_id,
        source_hit_actual_damage=source_hit_actual_damage,
        source_hit_target_routing=source_hit_target_routing,
        authority=authority,
    )
    confirmations = _confirmations(
        session=captured_session_id,
        attacker=attacker,
        defender=defender,
        payload=payload,
        turn=turn_number,
        create_execution=execution is None,
        ids=ids,
    )
    if confirmations is None:
        return _result("rejected", "observed_contact_reactive_damage_confirmation_rejected")

    for row in confirmations:
        allocated = runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
            return _result("rejected", "observation_sequence_unavailable")
        row["observation"]["observation_sequence"] = allocated["observation_sequence"]

    preview = _preview(collection, confirmations)
    if preview is None or runtime_session_manager.preview(captured_session_id, preview).get("status") != "preview_ready":
        return _result("rejected", "observed_contact_reactive_damage_preview_rejected")
    if runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations).get("status") not in {"added", "duplicate"}:
        return _result("rejected", "observed_contact_reactive_damage_admission_rejected")
    if runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot()).get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "observed_contact_reactive_damage_application_rejected")

    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if not _committed_ok(committed, attacker, attacker_hp_after, confirmations):
        return _result("rejected", "observed_contact_reactive_damage_committed_runtime_verification_failed")

    fresh = None
    if attacker_hp_after > 0:
        fresh = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=attacker)
        if (
            fresh.get("status") != "resolved"
            or fresh.get("source_runtime_fingerprint") != committed.get("state_fingerprint")
            or fresh.get("source_runtime_fingerprint") == d0.get("source_runtime_fingerprint")
        ):
            return _result("rejected", "observed_contact_reactive_damage_fresh_d0_verification_failed")

    result = {
        "status": "resolved",
        "reason": None,
        "owner": deepcopy(attacker),
        "observations": [deepcopy(row["observation"]) for row in confirmations],
        "runtime_snapshot": committed,
        "strategy_d0": fresh,
        "authority": deepcopy(dict(authority)),
        "idempotent": False,
    }
    if attacker_hp_after == 0:
        result.update(_faint_boundary(attacker, confirmations))
    return result


def _freeze_authority(
    *,
    snapshot,
    attacker,
    defender,
    move_id,
    source_action_id,
    source_hit_actual_damage,
    source_hit_target_routing,
    attacker_hp_authority=None,
):
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=attacker)
    if d0.get("status") != "resolved":
        return {"status": "incomplete", "reason": "fresh_runtime_d0_unavailable", "strategy_d0": d0, "authority": None}
    metadata = canonical_move_contact_metadata(move_id)
    if not isinstance(metadata, Mapping) or metadata.get("status") != "resolved":
        return {
            "status": metadata.get("status", "rejected") if isinstance(metadata, Mapping) else "rejected",
            "reason": metadata.get("reason", "contact_metadata_unavailable") if isinstance(metadata, Mapping) else "contact_metadata_unavailable",
            "strategy_d0": d0,
            "authority": None,
        }
    action = {"action_id": source_action_id, "action_type": "attack", "identity": move_id}
    contact = {
        "status": "resolved",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
        "action_id": source_action_id,
        "attacker": deepcopy(attacker),
        "target": deepcopy(defender),
        "move_id": move_id,
        "contact_state": metadata["contact_state"],
        "canonical_contact_metadata": deepcopy(dict(metadata)),
        "provenance": "observed_runtime_canonical_contact_evidence_v1",
    }
    source_hit = {
        "source_action_id": source_action_id,
        "source_move_id": move_id,
        "hit_index": 1,
        "actual_damage": source_hit_actual_damage,
        "target_routing": source_hit_target_routing,
    }
    kwargs = {}
    if attacker_hp_authority is not None:
        kwargs["attacker_hp_authority"] = attacker_hp_authority
    authority = freeze_runtime_d0_contact_reactive_damage_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        attacker=attacker,
        defender=defender,
        source_action=action,
        contact_authority=contact,
        source_hit=source_hit,
        **kwargs,
    )
    return {
        "status": authority.get("status", "rejected"),
        "reason": authority.get("reason"),
        "strategy_d0": d0,
        "authority": authority,
    }


def _confirmations(*, session, attacker, defender, payload, turn, create_execution, ids):
    boundary = LifecycleConfirmationBoundary(
        session,
        {attacker["side"]: attacker, defender["side"]: defender},
    )
    rows = []
    if create_execution:
        rows.append(
            boundary.confirm(
                event_kind="executed_move_observed",
                payload={"move_id": payload["move_id"], "source_action_id": payload["source_action_id"]},
                session_id=session,
                source=EXECUTED_MOVE_SOURCE,
                trust=USER_TRUST,
                confirmed=True,
                side=attacker["side"],
                slot_index=attacker["slot_index"],
                pokemon_id=attacker["pokemon_id"],
                observation_id=ids["execution"],
                turn_number=turn,
            )
        )
    rows.append(
        boundary.confirm(
            event_kind="contact_reactive_damage_result_observed",
            payload=payload,
            session_id=session,
            source=CONTACT_REACTIVE_DAMAGE_RESULT_SOURCE,
            trust=USER_TRUST,
            confirmed=True,
            side=attacker["side"],
            slot_index=attacker["slot_index"],
            pokemon_id=attacker["pokemon_id"],
            observation_id=ids["receipt"],
            turn_number=turn,
        )
    )
    if payload["hp_after"] == 0:
        pair = build_exact_hp_zero_faint_confirmation_pair(
            session_id=session,
            owner=attacker,
            hp_before=payload["hp_before"],
            turn_number=turn,
            source_event_id=payload["source_action_id"],
            hp_observation_id=ids["hp"],
            faint_observation_id=ids["faint"],
        )
        if pair is None:
            return None
        rows.extend(pair)
    else:
        rows.append(
            boundary.confirm(
                event_kind="exact_hp_transition_observed",
                payload={"hp_before": payload["hp_before"], "hp_after": payload["hp_after"]},
                session_id=session,
                source=HP_TRANSITION_SOURCE,
                trust=USER_TRUST,
                confirmed=True,
                side=attacker["side"],
                slot_index=attacker["slot_index"],
                pokemon_id=attacker["pokemon_id"],
                observation_id=ids["hp"],
                turn_number=turn,
            )
        )
    return rows if all(row.get("status") == "confirmed" for row in rows) else None


def _reuse_receipt(
    *,
    receipt,
    hp,
    faint,
    attacker,
    defender,
    move_id,
    source_action_id,
    attacker_hp_after,
    source_hit_actual_damage,
    source_hit_target_routing,
    turn_number,
    manager,
    snapshot,
):
    payload = receipt.get("payload") if isinstance(receipt, Mapping) else None
    if (
        receipt.get("event_kind") != "contact_reactive_damage_result_observed"
        or receipt.get("source") != CONTACT_REACTIVE_DAMAGE_RESULT_SOURCE
        or receipt.get("trust") != USER_TRUST
        or receipt.get("reducer_eligibility") != "evidence_only"
        or receipt.get("turn_number") != turn_number
        or (receipt.get("side"), receipt.get("slot_index"), receipt.get("pokemon_id"))
        != (attacker["side"], attacker["slot_index"], attacker["pokemon_id"])
        or not isinstance(payload, Mapping)
        or payload.get("move_id") != move_id
        or payload.get("source_action_id") != source_action_id
        or payload.get("attacker_side") != attacker["side"]
        or payload.get("attacker_slot_index") != attacker["slot_index"]
        or payload.get("attacker_pokemon_id") != attacker["pokemon_id"]
        or payload.get("defender_side") != defender["side"]
        or payload.get("defender_slot_index") != defender["slot_index"]
        or payload.get("defender_pokemon_id") != defender["pokemon_id"]
        or payload.get("hp_after") != attacker_hp_after
        or payload.get("source_hit_actual_damage") != source_hit_actual_damage
        or payload.get("source_hit_target_routing") != source_hit_target_routing
    ):
        return _result("rejected", "conflicting_observed_contact_reactive_damage_receipt")

    maximum = _pokemon(snapshot.get("state"), attacker)
    maximum = maximum.get("max_hp") if isinstance(maximum, Mapping) else None
    before = payload.get("hp_before")
    if not _positive(maximum) or not _positive(before):
        return _result("rejected", "observed_contact_reactive_damage_receipt_hp_authority_invalid")
    authority_result = _freeze_authority(
        snapshot=snapshot,
        attacker=attacker,
        defender=defender,
        move_id=move_id,
        source_action_id=source_action_id,
        source_hit_actual_damage=source_hit_actual_damage,
        source_hit_target_routing=source_hit_target_routing,
        attacker_hp_authority={
            "status": "resolved",
            "current_hp": before,
            "maximum_hp": maximum,
            "fainted": False,
            "provenance": "observed_contact_reactive_damage_receipt_retry_v1",
        },
    )
    authority = authority_result.get("authority")
    if (
        authority_result.get("status") != "resolved"
        or not isinstance(authority, Mapping)
        or authority.get("outcome") != "applies"
        or _payload(
            attacker=attacker,
            defender=defender,
            move_id=move_id,
            source_action_id=source_action_id,
            source_hit_actual_damage=source_hit_actual_damage,
            source_hit_target_routing=source_hit_target_routing,
            authority=authority,
        )
        != payload
    ):
        return _result("rejected", "conflicting_observed_contact_reactive_damage_receipt")

    collection = manager.read_collection_snapshot()
    execution = _execution(collection, receipt.get("session_id"), source_action_id)
    ids = _observation_ids(receipt.get("session_id"), source_action_id)
    hp_ok = _hp_matches(
        hp,
        attacker=attacker,
        session_id=receipt.get("session_id"),
        turn_number=turn_number,
        observation_id=ids["hp"],
        hp_before=before,
        hp_after=attacker_hp_after,
    )
    pair_state = (
        validate_exact_hp_zero_faint_confirmation_pair(
            hp=hp,
            faint=faint,
            owner=attacker,
            turn_number=turn_number,
            hp_observation_id=ids["hp"],
            faint_observation_id=ids["faint"],
            session_id=receipt.get("session_id"),
        )
        if attacker_hp_after == 0
        else "not_required"
    )
    if (
        not _execution_matches(execution, attacker, move_id, turn_number)
        or not hp_ok
        or pair_state not in {"exact", "not_required"}
        or (attacker_hp_after > 0 and faint is not None)
    ):
        return _result("rejected", "incomplete_or_conflicting_observed_contact_reactive_damage_receipt")

    rows = [execution, receipt, hp] + ([faint] if attacker_hp_after == 0 else [])
    if not _committed_ok(snapshot, attacker, attacker_hp_after, [{"observation": row} for row in rows]):
        return _result("rejected", "inconsistent_committed_observed_contact_reactive_damage_receipt")

    fresh = None
    if attacker_hp_after > 0:
        fresh = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=attacker)
        if fresh.get("status") != "resolved" or fresh.get("source_runtime_fingerprint") != snapshot.get("state_fingerprint"):
            return _result("rejected", "observed_contact_reactive_damage_fresh_d0_verification_failed")
    result = {
        "status": "resolved",
        "reason": "idempotent_reuse",
        "owner": deepcopy(attacker),
        "observations": [deepcopy(row) for row in rows],
        "runtime_snapshot": snapshot,
        "strategy_d0": fresh,
        "authority": deepcopy(dict(authority)),
        "idempotent": True,
    }
    if attacker_hp_after == 0:
        result.update(_faint_boundary(attacker, [{"observation": row} for row in rows]))
    return result


def _payload(
    *,
    attacker,
    defender,
    move_id,
    source_action_id,
    source_hit_actual_damage,
    source_hit_target_routing,
    authority,
):
    return {
        "source_action_id": source_action_id,
        "move_id": move_id,
        "attacker_side": attacker["side"],
        "attacker_slot_index": attacker["slot_index"],
        "attacker_pokemon_id": attacker["pokemon_id"],
        "defender_side": defender["side"],
        "defender_slot_index": defender["slot_index"],
        "defender_pokemon_id": defender["pokemon_id"],
        "hp_before": authority["pre_hp"],
        "hp_after": authority["post_hp"],
        "source_hit_actual_damage": source_hit_actual_damage,
        "source_hit_target_routing": source_hit_target_routing,
        "ordered_sources": [deepcopy(dict(row)) for row in authority.get("ordered_sources", ())],
    }


def _hp_matches(row, *, attacker, session_id, turn_number, observation_id, hp_before, hp_after):
    return (
        isinstance(row, Mapping)
        and row.get("event_kind") == "exact_hp_transition_observed"
        and row.get("source") == HP_TRANSITION_SOURCE
        and row.get("trust") == USER_TRUST
        and row.get("session_id") == session_id
        and row.get("turn_number") == turn_number
        and row.get("observation_id") == observation_id
        and (row.get("side"), row.get("slot_index"), row.get("pokemon_id"))
        == (attacker["side"], attacker["slot_index"], attacker["pokemon_id"])
        and row.get("payload") == {"hp_before": hp_before, "hp_after": hp_after}
    )


def _committed_ok(snapshot, attacker, after, confirmations):
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    actor = _pokemon(state, attacker)
    if not isinstance(actor, Mapping) or actor.get("pokemon_id") != attacker["pokemon_id"] or actor.get("current_hp") != after:
        return False
    rows = [
        row.get("observation")
        for row in confirmations
        if isinstance(row, Mapping) and isinstance(row.get("observation"), Mapping)
    ]
    hp = next((row for row in rows if row.get("event_kind") == "exact_hp_transition_observed"), None)
    faint = next((row for row in rows if row.get("event_kind") == "pokemon_faint_observed"), None)
    hp_provenance = actor.get("current_hp_provenance")
    if (
        not isinstance(hp, Mapping)
        or not isinstance(hp_provenance, Mapping)
        or (hp_provenance.get("source_observation_id"), hp_provenance.get("source_sequence"))
        != (hp.get("observation_id"), hp.get("observation_sequence"))
    ):
        return False
    if after == 0:
        faint_provenance = actor.get("fainted_provenance")
        return (
            actor.get("fainted") is True
            and isinstance(faint, Mapping)
            and isinstance(faint_provenance, Mapping)
            and (faint_provenance.get("source_observation_id"), faint_provenance.get("source_sequence"))
            == (faint.get("observation_id"), faint.get("observation_sequence"))
        )
    return actor.get("fainted") is False and faint is None and _active_identity(state, attacker["side"]) == attacker


def _preview(snapshot, confirmations):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready":
        return None
    return {
        **deepcopy(dict(snapshot)),
        "ordered_observations": sorted(
            [
                *deepcopy(snapshot.get("ordered_observations", [])),
                *[deepcopy(row["observation"]) for row in confirmations],
            ],
            key=lambda row: (row["observation_sequence"], row["observation_id"]),
        ),
    }


def _execution(snapshot, session, action):
    rows = [
        row
        for row in snapshot.get("ordered_observations", [])
        if isinstance(row, Mapping)
        and row.get("session_id") == session
        and row.get("event_kind") == "executed_move_observed"
        and row.get("payload", {}).get("source_action_id") == action
    ]
    return rows[0] if len(rows) == 1 else ({} if rows else None)


def _execution_matches(row, owner, move, turn):
    return (
        bool(row)
        and row.get("side") == owner["side"]
        and row.get("slot_index") == owner["slot_index"]
        and row.get("pokemon_id") == owner["pokemon_id"]
        and row.get("turn_number") == turn
        and row.get("payload", {}).get("move_id") == move
        and row.get("source") == EXECUTED_MOVE_SOURCE
        and row.get("trust") == USER_TRUST
    )


def _by_id(snapshot, observation_id):
    return next(
        (
            row
            for row in snapshot.get("ordered_observations", [])
            if isinstance(row, Mapping) and row.get("observation_id") == observation_id
        ),
        None,
    )


def _observation_ids(session, action):
    base = f"{session}:contact-reactive-damage:{action}"
    return {
        "execution": f"{base}:execution",
        "receipt": f"{base}:result",
        "hp": f"{base}:hp",
        "faint": f"{base}:faint",
    }


def _faint_boundary(attacker, confirmations):
    rows = [
        row.get("observation")
        for row in confirmations
        if isinstance(row, Mapping) and isinstance(row.get("observation"), Mapping)
    ]
    hp = next(row for row in rows if row.get("event_kind") == "exact_hp_transition_observed")
    faint = next(row for row in rows if row.get("event_kind") == "pokemon_faint_observed")
    return {
        "replacement_boundary": {
            "status": "replacement_required_after_faint",
            "fainted_owner": deepcopy(attacker),
            "hp_transition_observation_id": hp["observation_id"],
            "faint_observation_id": faint["observation_id"],
            "terminal_sequence": faint["observation_sequence"],
            "provenance": HP_ZERO_FAINT_SOURCE,
        }
    }


def _active_identity(state, side):
    row = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = row.get("pokemon") if isinstance(row, Mapping) else None
    slot = row.get("active_slot_index") if isinstance(row, Mapping) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) and not isinstance(slot, bool) and slot >= 0 else None
    session = state.get("session_id") if isinstance(state, Mapping) else None
    return (
        {"session_id": session, "side": side, "slot_index": slot, "pokemon_id": pokemon.get("pokemon_id")}
        if isinstance(session, str)
        and session
        and isinstance(pokemon, Mapping)
        and isinstance(pokemon.get("pokemon_id"), str)
        and pokemon.get("pokemon_id")
        else None
    )


def _pokemon(state, owner):
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    return roster.get(owner["slot_index"], roster.get(str(owner["slot_index"]))) if isinstance(roster, Mapping) else None


def _other(side):
    return "opponent" if side == "self" else "self"


def _token(value):
    return isinstance(value, str) and bool(value) and value == value.lower() and " " not in value and "_" not in value


def _positive(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _result(status, reason):
    return {
        "status": status,
        "reason": reason,
        "owner": None,
        "observations": [],
        "runtime_snapshot": None,
        "strategy_d0": None,
        "authority": None,
        "idempotent": False,
    }
