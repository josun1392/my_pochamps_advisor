"""Detached forced-action materialization for standard charge continuations.

This owner consumes only authenticated next-turn standard-charge continuation
authority.  It resolves the current occupant of the stored positional target
locator and materializes a forced continuation action request.  It deliberately
does not grant execution or invoke hit, critical-hit, damage-roll, secondary,
pair, PP, or reducer mechanics.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import (
    resolve_canonical_charge_move_lifecycle,
)
from llm.advisor_standard_charge_lifecycle_transport import (
    NEXT_TURN_SCHEMA_VERSION,
    validate_next_turn_standard_charge_continuation_authorities,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "detached-standard-charge-forced-continuation-set-v1"
ACTION_SCHEMA_VERSION = "detached-standard-charge-forced-continuation-action-v1"
METADATA_SCHEMA_VERSION = "detached-standard-charge-continuation-move-metadata-authority-v1"
_SIDES = ("self", "opponent")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SUPPORTED_MOVES = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn"})
_EXPECTED_CATEGORY = {
    "sky-attack": "physical",
    "razor-wind": "special",
    "freeze-shock": "physical",
    "ice-burn": "special",
}


def materialize_detached_standard_charge_forced_continuation(
    *,
    next_decision_state: Mapping[str, Any],
    next_decision_fingerprint: str,
) -> dict[str, Any]:
    """Materialize side-neutral forced continuation requests without execution."""
    if not isinstance(next_decision_state, Mapping):
        return _result("rejected", "standard_charge_next_decision_state_invalid")
    if not isinstance(next_decision_fingerprint, str) or not next_decision_fingerprint:
        return _result("rejected", "standard_charge_next_decision_fingerprint_invalid")
    if fingerprint_transition_preview_state(next_decision_state) != next_decision_fingerprint:
        return _result("rejected", "stale_or_forged_standard_charge_next_decision_state")

    active = next_decision_state.get("active")
    owners = _active_owners(active)
    if isinstance(owners, str):
        return _result("rejected", owners)

    source = next_decision_state.get("next_turn_standard_charge_continuation_authorities")
    if source is None:
        rows = {
            side: _known_none(
                side=side,
                reason="next_turn_standard_charge_continuation_absent",
                next_decision_fingerprint=next_decision_fingerprint,
            )
            for side in _SIDES
        }
        return _resolved(rows, next_decision_fingerprint)

    source_error = _validate_source_authorities(
        state=next_decision_state,
        authorities=source,
        active=active,
    )
    if source_error is not None:
        return _result("rejected", source_error)

    rows: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        continuation = source[side]
        if continuation["status"] == "known_none":
            rows[side] = _known_none(
                side=side,
                reason=continuation["reason"],
                next_decision_fingerprint=next_decision_fingerprint,
                source_continuation=continuation,
            )
            continue
        row = _forced_row(
            continuation=continuation,
            current_actor=owners[side],
            active=active,
            next_decision_fingerprint=next_decision_fingerprint,
        )
        if isinstance(row, str):
            return _result("rejected", row)
        rows[side] = row
    return _resolved(rows, next_decision_fingerprint)


def validate_detached_standard_charge_forced_continuation(
    *,
    result: Any,
    next_decision_state: Mapping[str, Any],
    next_decision_fingerprint: str,
) -> bool:
    expected = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=next_decision_state,
        next_decision_fingerprint=next_decision_fingerprint,
    )
    return isinstance(result, Mapping) and deepcopy(dict(result)) == expected


def _validate_source_authorities(
    *,
    state: Mapping[str, Any],
    authorities: Any,
    active: Mapping[str, Any],
) -> str | None:
    if not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "standard_charge_next_turn_authorities_invalid"
    source_post_eot: dict[str, Any] = {}
    fingerprints: set[str] = set()
    for side in _SIDES:
        row = authorities[side]
        if (
            not isinstance(row, Mapping)
            or row.get("schema_version") != NEXT_TURN_SCHEMA_VERSION
            or row.get("side") != side
            or row.get("status") not in {"known_present", "known_none"}
        ):
            return "standard_charge_next_turn_row_invalid"
        post = row.get("source_post_eot_authority")
        source_fp = row.get("source_post_eot_fingerprint")
        if not isinstance(post, Mapping) or not isinstance(source_fp, str) or not source_fp:
            return "standard_charge_next_turn_source_post_eot_invalid"
        source_post_eot[side] = post
        fingerprints.add(source_fp)
    if len(fingerprints) != 1:
        return "standard_charge_next_turn_source_post_eot_fingerprint_mismatch"
    source_post_eot_fingerprint = next(iter(fingerprints))

    lifecycle_error = _lifecycle_binding_error(
        state=state,
        source_post_eot_fingerprint=source_post_eot_fingerprint,
    )
    if lifecycle_error is not None:
        return lifecycle_error

    error = validate_next_turn_standard_charge_continuation_authorities(
        authorities=authorities,
        post_eot_authorities=source_post_eot,
        active_states=active,
        source_post_eot_fingerprint=source_post_eot_fingerprint,
    )
    if error is not None:
        return error

    for side in _SIDES:
        row = authorities[side]
        if row["status"] == "known_present":
            error = _present_source_error(
                row=row,
                side=side,
                current_actor=_owner_from_active(active[side]),
            )
            if error is not None:
                return error
        else:
            if (
                row.get("execution_grant") is not False
                or row.get("forced_action_synthesized") is not False
                or row.get("damage_execution_synthesized") is not False
                or row.get("pp_consumption_materialized") is not False
            ):
                return "standard_charge_known_none_execution_semantics_invalid"
    return None


def _lifecycle_binding_error(
    *,
    state: Mapping[str, Any],
    source_post_eot_fingerprint: str,
) -> str | None:
    lifecycle = state.get("turn_engine_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return "standard_charge_next_turn_lifecycle_provenance_missing"
    schema = lifecycle.get("schema_version")
    if schema == "detached-post-eot-next-decision-v1":
        if lifecycle.get("source_post_eot_state_fingerprint") != source_post_eot_fingerprint:
            return "standard_charge_next_turn_post_eot_fingerprint_mismatch"
    elif schema == "deterministic-next-turn-start-v1":
        if lifecycle.get("source_end_of_turn_fingerprint") != source_post_eot_fingerprint:
            return "standard_charge_next_turn_post_eot_fingerprint_mismatch"
    else:
        return "standard_charge_next_turn_lifecycle_provenance_invalid"
    return None


def _present_source_error(
    *,
    row: Mapping[str, Any],
    side: str,
    current_actor: Mapping[str, Any],
) -> str | None:
    if (
        row.get("lifecycle_state") != "continuation_pending"
        or row.get("continuation_pending") is not True
        or row.get("execution_grant") is not False
        or row.get("target_occupant_resolved") is not False
        or row.get("forced_action_synthesized") is not False
        or row.get("damage_execution_synthesized") is not False
        or row.get("pp_consumption_materialized") is not False
    ):
        return "standard_charge_next_turn_pending_semantics_invalid"
    charger = row.get("charger_owner")
    if not _owner(charger, side=side) or charger != current_actor:
        return "standard_charge_next_turn_charger_identity_mismatch"
    move_id = row.get("move_id")
    action_id = row.get("action_id")
    if move_id not in _SUPPORTED_MOVES or not isinstance(action_id, str) or not action_id:
        return "standard_charge_next_turn_move_or_action_invalid"

    context = row.get("source_charge_context")
    post = row.get("source_post_eot_authority")
    if not isinstance(context, Mapping) or not isinstance(post, Mapping):
        return "standard_charge_next_turn_source_charge_context_invalid"
    transport = post.get("source_transport_authority")
    if not isinstance(transport, Mapping):
        return "standard_charge_next_turn_source_transport_missing"
    if (
        post.get("status") != "known_present"
        or post.get("side") != side
        or post.get("charger_owner") != charger
        or post.get("move_id") != move_id
        or post.get("action_id") != action_id
        or post.get("source_charge_context") != context
        or transport.get("status") != "known_present"
        or transport.get("charger_owner") != charger
        or transport.get("move_id") != move_id
        or transport.get("action_id") != action_id
        or transport.get("original_charge_start_context") != context
    ):
        return "standard_charge_next_turn_source_chain_mismatch"

    readiness = context.get("readiness_authority")
    if (
        not isinstance(readiness, Mapping)
        or transport.get("original_readiness_authority") != readiness
        or context.get("status") != "resolved"
        or context.get("schema_version") != "detached-standard-charge-lifecycle-context-v1"
        or context.get("state") != "charging"
        or context.get("phase") != "turn_one_charge_started"
        or context.get("actor") != charger
        or context.get("move_id") != move_id
        or context.get("action_id") != action_id
        or context.get("canonical_lifecycle_family") != "ordinary_charge_then_damage"
        or context.get("execution_model") != "charge_then_execute"
        or context.get("turn_two_continuation_required") is not True
        or context.get("immediate_damage_executed") is not False
        or context.get("charge_turn_damage") != 0
        or context.get("pp_consumption_materialized") is not False
        or context.get("power_herb_applicability_state", {}).get("status") == "active"
        or readiness.get("status") != "resolved"
        or readiness.get("outcome") != "charge_start_ready"
        or readiness.get("move_id") != move_id
        or readiness.get("action_id") != action_id
        or readiness.get("actor") != charger
        or readiness.get("pp_consumed") is not False
        or readiness.get("immediate_damage_execution_grant") is not False
    ):
        return "standard_charge_next_turn_source_charge_context_invalid"

    locator = row.get("continuation_target_locator")
    if (
        context.get("continuation_target_locator") != locator
        or post.get("continuation_target_locator") != locator
        or transport.get("continuation_target_locator") != locator
        or readiness.get("continuation_target_locator") != locator
    ):
        return "standard_charge_next_turn_target_locator_chain_mismatch"

    canonical = readiness.get("canonical_charge_lifecycle_authority")
    expected_canonical = resolve_canonical_charge_move_lifecycle(move_id)
    if (
        not isinstance(canonical, Mapping)
        or canonical != expected_canonical
        or canonical.get("status") != "resolved"
        or canonical.get("move_id") != move_id
        or canonical.get("lifecycle_family") != "ordinary_charge_then_damage"
        or canonical.get("execution_model") != "charge_then_execute"
    ):
        return "standard_charge_next_turn_canonical_lifecycle_invalid"

    metadata_error = _metadata_error(
        metadata_authority=readiness.get("move_metadata_authority"),
        move_id=move_id,
        action_id=action_id,
        charger=charger,
    )
    if metadata_error is not None:
        return metadata_error
    return None


def _forced_row(
    *,
    continuation: Mapping[str, Any],
    current_actor: Mapping[str, Any],
    active: Mapping[str, Any],
    next_decision_fingerprint: str,
) -> dict[str, Any] | str:
    side = continuation["side"]
    if continuation.get("charger_owner") != current_actor:
        return "standard_charge_forced_continuation_actor_identity_mismatch"
    context = continuation["source_charge_context"]
    locator = continuation.get("continuation_target_locator")
    locator_error = _locator_error(
        locator=locator,
        session_id=current_actor["session_id"],
        charger_side=side,
        active=active,
        historical_target=context.get("source_target_owner"),
    )
    if locator_error is not None:
        return locator_error
    target_active = active[locator["side"]]
    resolved_target = _owner_from_active(target_active)
    if target_active.get("fainted") is not False:
        return "standard_charge_forced_continuation_target_not_actionable"

    readiness = context["readiness_authority"]
    source_metadata = readiness["move_metadata_authority"]
    raw_metadata = source_metadata["metadata"]
    continuation_action_id = (
        f"{continuation['action_id']}:standard-charge-continuation"
    )
    detached_metadata = {
        "status": "resolved",
        "schema_version": METADATA_SCHEMA_VERSION,
        "source_next_decision_fingerprint": next_decision_fingerprint,
        "source_original_action_id": continuation["action_id"],
        "action_id": continuation_action_id,
        "move_id": continuation["move_id"],
        "active_attacker": deepcopy(current_actor),
        "resolved_target_owner": deepcopy(resolved_target),
        "metadata": deepcopy(dict(raw_metadata)),
        "source_move_metadata_authority": deepcopy(dict(source_metadata)),
        "provenance": "detached_standard_charge_continuation_metadata_rebind_v1",
    }
    return {
        "status": "resolved",
        "schema_version": ACTION_SCHEMA_VERSION,
        "source_next_decision_fingerprint": next_decision_fingerprint,
        "side": side,
        "actor": deepcopy(current_actor),
        "resolved_target_owner": deepcopy(resolved_target),
        "continuation_target_locator": deepcopy(dict(locator)),
        "move_id": continuation["move_id"],
        "original_charge_action_id": continuation["action_id"],
        "continuation_action_id": continuation_action_id,
        "move_metadata_authority": detached_metadata,
        "execution_priority": raw_metadata["priority"],
        "lifecycle_state": "turn_two_continuation_forced",
        "continuation_forced": True,
        "user_selection_required": False,
        "forced_action_materialized": True,
        "target_occupant_resolved": True,
        "execution_grant": False,
        "damage_execution_synthesized": False,
        "pp_consumption_materialized": False,
        "source_continuation_authority": deepcopy(dict(continuation)),
        "original_charge_provenance": deepcopy(dict(context)),
        "historical_source_target_owner": deepcopy(context["source_target_owner"]),
        "provenance": "authenticated_standard_charge_turn_two_forced_request_v1",
    }


def _metadata_error(
    *,
    metadata_authority: Any,
    move_id: str,
    action_id: str,
    charger: Mapping[str, Any],
) -> str | None:
    if not isinstance(metadata_authority, Mapping):
        return "standard_charge_continuation_metadata_authority_missing"
    metadata = metadata_authority.get("metadata")
    if (
        metadata_authority.get("status") != "resolved"
        or metadata_authority.get("move_id") != move_id
        or not isinstance(metadata, Mapping)
        or metadata.get("move_id") != move_id
    ):
        return "standard_charge_continuation_metadata_identity_invalid"
    if (
        "candidate_id" in metadata_authority
        and metadata_authority.get("candidate_id") != action_id
    ):
        return "standard_charge_continuation_metadata_action_binding_invalid"
    if (
        "active_attacker" in metadata_authority
        and metadata_authority.get("active_attacker") != charger
    ):
        return "standard_charge_continuation_metadata_actor_binding_invalid"
    category = metadata.get("category")
    power = metadata.get("power")
    accuracy = metadata.get("accuracy")
    priority = metadata.get("priority")
    move_type = metadata.get("type")
    if (
        category != _EXPECTED_CATEGORY[move_id]
        or not _positive_int(power)
        or not _integer(accuracy)
        or not 1 <= accuracy <= 100
        or not _integer(priority)
        or not isinstance(move_type, str)
        or not move_type
    ):
        return "standard_charge_continuation_move_metadata_invalid"
    return None


def _locator_error(
    *,
    locator: Any,
    session_id: str,
    charger_side: str,
    active: Mapping[str, Any],
    historical_target: Any,
) -> str | None:
    target_side = "opponent" if charger_side == "self" else "self"
    if (
        not isinstance(locator, Mapping)
        or set(locator) != {"session_id", "side", "slot_index"}
        or "pokemon_id" in locator
        or locator.get("session_id") != session_id
        or locator.get("side") != target_side
        or not _integer(locator.get("slot_index"))
        or locator["slot_index"] < 0
    ):
        return "standard_charge_forced_continuation_target_locator_invalid"
    target = active.get(target_side)
    if not isinstance(target, Mapping):
        return "standard_charge_forced_continuation_target_side_missing"
    owner = _owner_from_active(target)
    if not _owner(owner, side=target_side) or owner["session_id"] != session_id:
        return "standard_charge_forced_continuation_target_identity_invalid"
    if not _owner(historical_target, side=target_side) or historical_target["session_id"] != session_id:
        return "standard_charge_forced_continuation_historical_target_invalid"
    if owner["pokemon_id"] == historical_target["pokemon_id"]:
        if owner != historical_target or owner["slot_index"] != locator["slot_index"]:
            return "standard_charge_forced_continuation_target_slot_mismatch"
    # The detached replacement owner uses roster slot_index for the new
    # Pokemon, while the authenticated continuation locator deliberately
    # retains the prior battlefield position.  A changed identity is therefore
    # resolved as the current occupant of the already-authenticated side
    # position instead of rewriting the locator to the incoming roster slot.
    return None


def _known_none(
    *,
    side: str,
    reason: str,
    next_decision_fingerprint: str,
    source_continuation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "known_none",
        "schema_version": ACTION_SCHEMA_VERSION,
        "source_next_decision_fingerprint": next_decision_fingerprint,
        "side": side,
        "reason": reason,
        "forced_action_materialized": False,
        "execution_grant": False,
        "damage_execution_synthesized": False,
        "pp_consumption_materialized": False,
        **(
            {"source_continuation_authority": deepcopy(dict(source_continuation))}
            if source_continuation is not None
            else {}
        ),
        "provenance": "standard_charge_forced_continuation_explicit_none_v1",
    }


def _active_owners(active: Any) -> dict[str, dict[str, Any]] | str:
    if not isinstance(active, Mapping) or set(active) != set(_SIDES):
        return "standard_charge_next_decision_active_state_invalid"
    owners: dict[str, dict[str, Any]] = {}
    session_id: str | None = None
    for side in _SIDES:
        row = active[side]
        if not isinstance(row, Mapping):
            return "standard_charge_next_decision_active_state_invalid"
        owner = _owner_from_active(row)
        if not _owner(owner, side=side):
            return "standard_charge_next_decision_active_owner_invalid"
        if not _positive_int(row.get("max_hp")) or not _nonnegative_int(row.get("current_hp")):
            return "standard_charge_next_decision_active_hp_invalid"
        if row["current_hp"] > row["max_hp"] or row.get("fainted") is not (row["current_hp"] == 0):
            return "standard_charge_next_decision_active_hp_invalid"
        if session_id is None:
            session_id = owner["session_id"]
        elif owner["session_id"] != session_id:
            return "standard_charge_next_decision_session_mismatch"
        owners[side] = owner
    return owners


def _owner_from_active(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in _OWNER_KEYS}


def _owner(value: Any, *, side: str) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and value.get("side") == side
        and _integer(value.get("slot_index"))
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _resolved(rows: Mapping[str, Any], fingerprint: str) -> dict[str, Any]:
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "source_next_decision_fingerprint": fingerprint,
        "forced_continuation_actions": deepcopy(dict(rows)),
        "action_order_materialized": False,
        "execution_grant": False,
        "damage_execution_synthesized": False,
        "pp_consumption_materialized": False,
        "provenance": "detached_standard_charge_forced_continuation_set_v1",
    }


def _result(status: str, reason: str) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        "reason": reason,
    }


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_int(value: Any) -> bool:
    return _integer(value) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return _integer(value) and value >= 0
