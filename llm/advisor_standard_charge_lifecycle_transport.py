"""Strict detached transport for standard charge lifecycle state.

Truth originates only from an authenticated standard-charge action leaf already
embedded in one exact normalized immediate-pair terminal.  This module never
executes a move, consumes PP, resolves a future target occupant, or writes
runtime/reducer state.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_detached_standard_charge_start import (
    validate_pair_compatible_standard_charge_leaf,
)


TRANSPORT_SCHEMA_VERSION = "detached-standard-charge-lifecycle-transport-authority-v1"
POST_EOT_SCHEMA_VERSION = "detached-standard-charge-post-eot-lifecycle-authority-v1"
NEXT_TURN_SCHEMA_VERSION = "detached-standard-charge-next-turn-continuation-authority-v1"
_SIDES = ("self", "opponent")
_SUPPORTED_MOVES = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn"})
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def derive_standard_charge_lifecycle_transport_authorities(
    *,
    terminal_ledger: Mapping[str, Any],
    terminal_leaf_id: str,
) -> dict[str, Any] | str:
    """Derive two explicit rows from one exact normalized pair terminal."""
    source = _ledger_source(terminal_ledger, terminal_leaf_id)
    if isinstance(source, str):
        return source
    base, terminal = source
    charge_leaves = _charge_source_leaves(terminal)
    if isinstance(charge_leaves, str):
        return charge_leaves

    by_side: dict[str, Mapping[str, Any]] = {}
    for leaf in charge_leaves:
        provenance = leaf["provenance"]
        actor = provenance["attacker"]
        side = actor["side"]
        expected_owner = base["own_actor"] if side == "self" else base["opponent_actor"]
        if actor != expected_owner:
            return "standard_charge_transport_charger_identity_mismatch"
        if side in by_side:
            return "standard_charge_transport_duplicate_charger_side"
        by_side[side] = leaf

    rows: dict[str, dict[str, Any]] = {}
    final = terminal["final_consequences"]
    for side in _SIDES:
        owner = base["own_actor"] if side == "self" else base["opponent_actor"]
        leaf = by_side.get(side)
        if leaf is None:
            rows[side] = _transport_none(
                base=base,
                terminal_leaf_id=terminal_leaf_id,
                side=side,
                active_owner=owner,
                reason="no_executed_standard_charge_start",
            )
            continue
        hp_key = "own_final_hp" if side == "self" else "opponent_final_hp"
        if final[hp_key] == 0:
            rows[side] = _transport_none(
                base=base,
                terminal_leaf_id=terminal_leaf_id,
                side=side,
                active_owner=owner,
                reason="charger_fainted_before_eot",
                retired_leaf=leaf,
            )
            continue
        rows[side] = _transport_present(
            base=base,
            terminal_leaf_id=terminal_leaf_id,
            side=side,
            active_owner=owner,
            leaf=leaf,
        )
    return rows


def validate_standard_charge_lifecycle_transport_authorities(
    *,
    authorities: Any,
    terminal_ledger: Mapping[str, Any],
    terminal_leaf_id: str,
) -> str | None:
    expected = derive_standard_charge_lifecycle_transport_authorities(
        terminal_ledger=terminal_ledger,
        terminal_leaf_id=terminal_leaf_id,
    )
    if isinstance(expected, str):
        return expected
    if not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "standard_charge_transport_authorities_invalid"
    if deepcopy(dict(authorities)) != expected:
        return "standard_charge_transport_authorities_mismatch"
    return None


def project_post_eot_standard_charge_lifecycle_authorities(
    *,
    transport_authorities: Mapping[str, Any],
    post_end_of_turn_active_states: Mapping[str, Any],
    source_eot_fingerprint: str,
) -> dict[str, Any] | str:
    """Retire EOT-KO chargers; preserve survivors without changing target binding."""
    if (
        not isinstance(transport_authorities, Mapping)
        or set(transport_authorities) != set(_SIDES)
        or not isinstance(post_end_of_turn_active_states, Mapping)
        or set(post_end_of_turn_active_states) != set(_SIDES)
        or not isinstance(source_eot_fingerprint, str)
        or not source_eot_fingerprint
    ):
        return "post_eot_standard_charge_transport_invalid"
    rows: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        source = transport_authorities[side]
        final = post_end_of_turn_active_states[side]
        error = _transport_row_shape(source, side)
        if error is not None:
            return error
        if not isinstance(final, Mapping) or not _owner(final.get("owner"), side=side):
            return "post_eot_standard_charge_active_state_invalid"
        if (
            not isinstance(final.get("fainted"), bool)
            or not _integer(final.get("current_hp"))
            or final["current_hp"] < 0
            or final["fainted"] is not (final["current_hp"] == 0)
        ):
            return "post_eot_standard_charge_hp_faint_invalid"
        if source["status"] == "known_none":
            rows[side] = {
                "status": "known_none",
                "schema_version": POST_EOT_SCHEMA_VERSION,
                "side": side,
                "reason": source["reason"],
                "source_transport_authority": deepcopy(dict(source)),
                "source_eot_fingerprint": source_eot_fingerprint,
                "execution_grant": False,
                "provenance": "standard_charge_post_eot_explicit_none_v1",
            }
            continue
        charger = source["charger_owner"]
        if final["owner"] != charger:
            return "post_eot_standard_charge_charger_identity_mismatch"
        if final["fainted"]:
            rows[side] = {
                "status": "known_none",
                "schema_version": POST_EOT_SCHEMA_VERSION,
                "side": side,
                "reason": "charger_fainted_during_eot",
                "retired_charger_owner": deepcopy(charger),
                "historical_charge_authority": deepcopy(dict(source)),
                "source_transport_authority": deepcopy(dict(source)),
                "source_eot_fingerprint": source_eot_fingerprint,
                "execution_grant": False,
                "provenance": "standard_charge_retired_by_eot_faint_v1",
            }
            continue
        rows[side] = {
            "status": "known_present",
            "schema_version": POST_EOT_SCHEMA_VERSION,
            "side": side,
            "charger_owner": deepcopy(charger),
            "move_id": source["move_id"],
            "action_id": source["action_id"],
            "continuation_target_locator": deepcopy(source["continuation_target_locator"]),
            "source_charge_context": deepcopy(source["original_charge_start_context"]),
            "source_transport_authority": deepcopy(dict(source)),
            "source_eot_fingerprint": source_eot_fingerprint,
            "continuation_pending": True,
            "execution_grant": False,
            "pp_consumption_materialized": False,
            "provenance": "standard_charge_survived_eot_v1",
        }
    return rows


def validate_post_eot_standard_charge_lifecycle_authorities(
    *,
    authorities: Any,
    transport_authorities: Mapping[str, Any],
    post_end_of_turn_active_states: Mapping[str, Any],
    source_eot_fingerprint: str,
) -> str | None:
    expected = project_post_eot_standard_charge_lifecycle_authorities(
        transport_authorities=transport_authorities,
        post_end_of_turn_active_states=post_end_of_turn_active_states,
        source_eot_fingerprint=source_eot_fingerprint,
    )
    if isinstance(expected, str):
        return expected
    if not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "post_eot_standard_charge_authorities_invalid"
    if deepcopy(dict(authorities)) != expected:
        return "post_eot_standard_charge_authorities_mismatch"
    return None


def retire_standard_charge_lifecycle_for_replacement(
    *,
    authorities: Mapping[str, Any],
    active_states: Mapping[str, Any],
    replaced_side: str,
    incoming_owner: Mapping[str, Any],
    source_state_fingerprint: str,
) -> dict[str, Any] | str:
    """Never transfer a charger's lifecycle to a replacement identity."""
    error = validate_post_eot_standard_charge_authorities_against_active(
        authorities=authorities,
        active_states=active_states,
    )
    if error is not None:
        return error
    if replaced_side not in _SIDES or not _owner(incoming_owner, side=replaced_side):
        return "standard_charge_replacement_identity_invalid"
    if not isinstance(source_state_fingerprint, str) or not source_state_fingerprint:
        return "standard_charge_replacement_source_fingerprint_invalid"

    rows = deepcopy(dict(authorities))
    row = rows[replaced_side]
    outgoing = _active_owner(active_states[replaced_side])
    if row["status"] == "known_present":
        if row["charger_owner"] != outgoing:
            return "standard_charge_replacement_charger_binding_mismatch"
        rows[replaced_side] = {
            "status": "known_none",
            "schema_version": POST_EOT_SCHEMA_VERSION,
            "side": replaced_side,
            "reason": "charger_replaced_before_next_turn",
            "retired_charger_owner": deepcopy(outgoing),
            "replacement_owner": deepcopy(dict(incoming_owner)),
            "historical_charge_authority": deepcopy(dict(row)),
            "source_eot_fingerprint": row["source_eot_fingerprint"],
            "source_replacement_state_fingerprint": source_state_fingerprint,
            "execution_grant": False,
            "provenance": "standard_charge_retired_by_replacement_v1",
        }
    else:
        # Explicit none remains none; a replacement never creates charge state.
        rows[replaced_side] = {
            **deepcopy(dict(row)),
            "replacement_owner": deepcopy(dict(incoming_owner)),
            "source_replacement_state_fingerprint": source_state_fingerprint,
        }
    return rows


def validate_post_eot_standard_charge_authorities_against_active(
    *,
    authorities: Any,
    active_states: Mapping[str, Any],
) -> str | None:
    if (
        not isinstance(authorities, Mapping)
        or set(authorities) != set(_SIDES)
        or not isinstance(active_states, Mapping)
        or set(active_states) != set(_SIDES)
    ):
        return "post_eot_standard_charge_active_binding_invalid"
    for side in _SIDES:
        row = authorities[side]
        active = active_states[side]
        if not isinstance(row, Mapping) or row.get("schema_version") != POST_EOT_SCHEMA_VERSION:
            return "post_eot_standard_charge_row_invalid"
        if row.get("side") != side or row.get("status") not in {"known_present", "known_none"}:
            return "post_eot_standard_charge_row_invalid"
        if not isinstance(active, Mapping) or not _owner(_active_owner(active), side=side):
            return "post_eot_standard_charge_active_binding_invalid"
        if row["status"] == "known_present":
            if row.get("charger_owner") != _active_owner(active) or active.get("fainted") is not False:
                return "post_eot_standard_charge_charger_not_current_active"
            locator = row.get("continuation_target_locator")
            if not _locator(locator, opposite_of=side):
                return "post_eot_standard_charge_target_locator_invalid"
            if row.get("execution_grant") is not False or row.get("pp_consumption_materialized") is not False:
                return "post_eot_standard_charge_execution_semantics_invalid"
        elif row.get("execution_grant") is not False:
            return "post_eot_standard_charge_execution_semantics_invalid"
    return None


def materialize_next_turn_standard_charge_continuation_authorities(
    *,
    post_eot_authorities: Mapping[str, Any],
    active_states: Mapping[str, Any],
    source_post_eot_fingerprint: str,
) -> dict[str, Any] | str:
    error = validate_post_eot_standard_charge_authorities_against_active(
        authorities=post_eot_authorities,
        active_states=active_states,
    )
    if error is not None:
        return error
    if not isinstance(source_post_eot_fingerprint, str) or not source_post_eot_fingerprint:
        return "next_turn_standard_charge_source_fingerprint_invalid"
    rows: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        source = post_eot_authorities[side]
        if source["status"] == "known_none":
            rows[side] = {
                "status": "known_none",
                "schema_version": NEXT_TURN_SCHEMA_VERSION,
                "side": side,
                "reason": source["reason"],
                "source_post_eot_authority": deepcopy(dict(source)),
                "source_post_eot_fingerprint": source_post_eot_fingerprint,
                "execution_grant": False,
                "selected_action_synthesized": False,
                "forced_action_synthesized": False,
                "damage_execution_synthesized": False,
                "pp_consumption_materialized": False,
                "provenance": "standard_charge_next_turn_explicit_none_v1",
            }
            continue
        rows[side] = {
            "status": "known_present",
            "schema_version": NEXT_TURN_SCHEMA_VERSION,
            "side": side,
            "lifecycle_state": "continuation_pending",
            "continuation_pending": True,
            "charger_owner": deepcopy(source["charger_owner"]),
            "move_id": source["move_id"],
            "action_id": source["action_id"],
            "continuation_target_locator": deepcopy(source["continuation_target_locator"]),
            "source_charge_context": deepcopy(source["source_charge_context"]),
            "source_post_eot_authority": deepcopy(dict(source)),
            "source_eot_fingerprint": source["source_eot_fingerprint"],
            "source_post_eot_fingerprint": source_post_eot_fingerprint,
            "execution_grant": False,
            "target_occupant_resolved": False,
            "selected_action_synthesized": False,
            "forced_action_synthesized": False,
            "damage_execution_synthesized": False,
            "pp_consumption_materialized": False,
            "provenance": "standard_charge_next_turn_continuation_pending_v1",
        }
    return rows


def validate_next_turn_standard_charge_continuation_authorities(
    *,
    authorities: Any,
    post_eot_authorities: Mapping[str, Any],
    active_states: Mapping[str, Any],
    source_post_eot_fingerprint: str,
) -> str | None:
    expected = materialize_next_turn_standard_charge_continuation_authorities(
        post_eot_authorities=post_eot_authorities,
        active_states=active_states,
        source_post_eot_fingerprint=source_post_eot_fingerprint,
    )
    if isinstance(expected, str):
        return expected
    if not isinstance(authorities, Mapping) or set(authorities) != set(_SIDES):
        return "next_turn_standard_charge_authorities_invalid"
    if deepcopy(dict(authorities)) != expected:
        return "next_turn_standard_charge_authorities_mismatch"
    return None


def _transport_present(
    *,
    base: Mapping[str, Any],
    terminal_leaf_id: str,
    side: str,
    active_owner: Mapping[str, Any],
    leaf: Mapping[str, Any],
) -> dict[str, Any]:
    context = leaf["consequences"]["detached_standard_charge_lifecycle_context"]
    readiness = context["readiness_authority"]
    return {
        "status": "known_present",
        "schema_version": TRANSPORT_SCHEMA_VERSION,
        **_transport_binding(base, terminal_leaf_id, side),
        "charger_owner": deepcopy(dict(active_owner)),
        "action_id": context["action_id"],
        "move_id": context["move_id"],
        "canonical_lifecycle_family": context["canonical_lifecycle_family"],
        "execution_model": context["execution_model"],
        "original_charge_start_context": deepcopy(dict(context)),
        "original_readiness_authority": deepcopy(dict(readiness)),
        "source_charge_start_leaf_id": leaf["leaf_id"],
        "continuation_target_locator": deepcopy(context["continuation_target_locator"]),
        "pp_consumption_materialized": False,
        "power_herb_skip_active": False,
        "immediate_damage_executed": False,
        "turn_two_continuation_required": True,
        "execution_grant": False,
        "provenance": "exact_pair_terminal_standard_charge_transport_v1",
    }


def _transport_none(
    *,
    base: Mapping[str, Any],
    terminal_leaf_id: str,
    side: str,
    active_owner: Mapping[str, Any],
    reason: str,
    retired_leaf: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "status": "known_none",
        "schema_version": TRANSPORT_SCHEMA_VERSION,
        **_transport_binding(base, terminal_leaf_id, side),
        "active_owner": deepcopy(dict(active_owner)),
        "reason": reason,
        "execution_grant": False,
        "provenance": "exact_pair_terminal_standard_charge_explicit_none_v1",
    }
    if retired_leaf is not None:
        row["retired_charge_start_leaf"] = deepcopy(dict(retired_leaf))
        row["retired_charger_owner"] = deepcopy(dict(retired_leaf["provenance"]["attacker"]))
    return row


def _transport_binding(
    base: Mapping[str, Any],
    terminal_leaf_id: str,
    side: str,
) -> dict[str, Any]:
    return {
        "session_id": base["session_id"],
        "pair_id": base["pair_id"],
        "terminal_leaf_id": terminal_leaf_id,
        "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"],
        "decision_owner": deepcopy(base["decision_owner"]),
        "charger_side": side,
    }


def _ledger_source(
    ledger: Any,
    terminal_leaf_id: Any,
) -> tuple[dict[str, Any], Mapping[str, Any]] | str:
    if (
        not isinstance(ledger, Mapping)
        or ledger.get("status") != "evaluable"
        or ledger.get("schema_version") != "exact-immediate-action-pair-outcome-ledger-v1"
        or ledger.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1}
        or not isinstance(terminal_leaf_id, str)
        or not terminal_leaf_id
    ):
        return "standard_charge_transport_terminal_ledger_invalid"
    required = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint")
    if any(not isinstance(ledger.get(key), str) or not ledger[key] for key in required):
        return "standard_charge_transport_terminal_binding_invalid"
    if not isinstance(ledger.get("decision_owner"), Mapping):
        return "standard_charge_transport_terminal_binding_invalid"
    if not _owner(ledger.get("own_actor"), side="self") or not _owner(ledger.get("opponent_actor"), side="opponent"):
        return "standard_charge_transport_terminal_owner_invalid"
    if ledger["own_actor"]["session_id"] != ledger["session_id"] or ledger["opponent_actor"]["session_id"] != ledger["session_id"]:
        return "standard_charge_transport_terminal_owner_invalid"
    leaves = ledger.get("terminal_leaves")
    matches = [
        leaf for leaf in leaves
        if isinstance(leaf, Mapping) and leaf.get("pair_leaf_id") == terminal_leaf_id
    ] if isinstance(leaves, (tuple, list)) else []
    if len(matches) != 1:
        return "standard_charge_transport_terminal_leaf_invalid"
    terminal = matches[0]
    source_pair_branch = terminal.get("source_pair_branch")
    if source_pair_branch is not None:
        if not isinstance(source_pair_branch, Mapping):
            return "standard_charge_transport_source_pair_branch_invalid"
        source_provenance = source_pair_branch.get("provenance")
        if not isinstance(source_provenance, Mapping):
            return "standard_charge_transport_source_pair_provenance_invalid"
        expected_source = {
            "pair_id": ledger["pair_id"],
            "session_id": ledger["session_id"],
            "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
            "source_branch_fingerprint": ledger["source_branch_fingerprint"],
            "decision_owner": ledger["decision_owner"],
            "own_actor": ledger["own_actor"],
            "opponent_actor": ledger["opponent_actor"],
        }
        if any(
            source_provenance.get(key) != value
            for key, value in expected_source.items()
        ):
            return "standard_charge_transport_source_pair_binding_mismatch"
        if source_pair_branch.get("pair_leaf_id") != terminal_leaf_id:
            return "standard_charge_transport_source_terminal_leaf_mismatch"
    final = terminal.get("final_consequences")
    if (
        not isinstance(final, Mapping)
        or not _nonnegative_int(final.get("own_final_hp"))
        or not _nonnegative_int(final.get("opponent_final_hp"))
    ):
        return "standard_charge_transport_terminal_final_hp_invalid"
    base = {
        "pair_id": ledger["pair_id"],
        "session_id": ledger["session_id"],
        "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
        "source_branch_fingerprint": ledger["source_branch_fingerprint"],
        "decision_owner": deepcopy(ledger["decision_owner"]),
        "own_actor": deepcopy(ledger["own_actor"]),
        "opponent_actor": deepcopy(ledger["opponent_actor"]),
    }
    return base, terminal


def _charge_source_leaves(terminal: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...] | str:
    source = terminal.get("source_pair_branch")
    normalized_rows: list[tuple[Any, Any]] = []
    if source is None:
        # Legacy normalized fixtures without source_pair_branch can only prove
        # explicit absence when no charge context is present in normalized rows.
        for action in (terminal.get("first_action"), terminal.get("second_action", {}).get("leaf") if isinstance(terminal.get("second_action"), Mapping) else None):
            if _nested_charge_context(action):
                return "standard_charge_transport_source_pair_branch_missing"
        return ()
    if not isinstance(source, Mapping):
        return "standard_charge_transport_source_pair_branch_invalid"

    normalized_rows.append((terminal.get("first_action"), source.get("first_action_leaf")))
    second = terminal.get("second_action")
    source_second = source.get("second_action")
    if not isinstance(second, Mapping) or not isinstance(source_second, Mapping):
        return "standard_charge_transport_second_action_shape_invalid"
    if second.get("state") == "executed":
        normalized_rows.append((second.get("leaf"), source_second.get("leaf")))
    elif second.get("leaf") is not None or source_second.get("leaf") is not None:
        return "standard_charge_transport_cancelled_action_has_leaf"

    result: list[Mapping[str, Any]] = []
    for normalized, full in normalized_rows:
        if not isinstance(full, Mapping):
            if _nested_charge_context(normalized):
                return "standard_charge_transport_source_leaf_missing"
            continue
        provenance = full.get("provenance")
        move_id = provenance.get("move_id") if isinstance(provenance, Mapping) else None
        has_context = _nested_charge_context(full)
        if move_id in _SUPPORTED_MOVES or has_context:
            error = validate_pair_compatible_standard_charge_leaf(full)
            if error is not None:
                return error
            if not isinstance(normalized, Mapping) or not _normalized_matches_source(normalized, full):
                return "standard_charge_transport_normalized_leaf_mismatch"
            result.append(full)
        elif _nested_charge_context(normalized):
            return "unexpected_standard_charge_transport_context"
    return tuple(result)


def _normalized_matches_source(normalized: Mapping[str, Any], full: Mapping[str, Any]) -> bool:
    for key in ("leaf_id", "branch_path", "probability", "hit_state", "critical_state", "damage_roll", "consequences", "provenance"):
        if normalized.get(key) != full.get(key):
            return False
    return True


def _nested_charge_context(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("consequences"), Mapping)
        and "detached_standard_charge_lifecycle_context" in value["consequences"]
    )


def _transport_row_shape(row: Any, side: str) -> str | None:
    if (
        not isinstance(row, Mapping)
        or row.get("schema_version") != TRANSPORT_SCHEMA_VERSION
        or row.get("charger_side") != side
        or row.get("status") not in {"known_present", "known_none"}
        or row.get("execution_grant") is not False
    ):
        return "standard_charge_transport_row_invalid"
    if row["status"] == "known_none":
        return None if isinstance(row.get("reason"), str) and row["reason"] else "standard_charge_transport_none_reason_invalid"
    if (
        not _owner(row.get("charger_owner"), side=side)
        or row.get("move_id") not in _SUPPORTED_MOVES
        or not isinstance(row.get("action_id"), str)
        or not row["action_id"]
        or row.get("canonical_lifecycle_family") != "ordinary_charge_then_damage"
        or row.get("execution_model") != "charge_then_execute"
        or not _locator(row.get("continuation_target_locator"), opposite_of=side)
        or row.get("pp_consumption_materialized") is not False
        or row.get("power_herb_skip_active") is not False
        or row.get("immediate_damage_executed") is not False
        or row.get("turn_two_continuation_required") is not True
    ):
        return "standard_charge_transport_present_semantics_invalid"
    return None


def _active_owner(active: Mapping[str, Any]) -> dict[str, Any]:
    return {key: active[key] for key in _OWNER_KEYS}


def _owner(value: Any, *, side: str) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) >= set(_OWNER_KEYS)
        and value.get("side") == side
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and _integer(value.get("slot_index"))
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _locator(value: Any, *, opposite_of: str) -> bool:
    expected_side = "opponent" if opposite_of == "self" else "self"
    return (
        isinstance(value, Mapping)
        and set(value) == {"session_id", "side", "slot_index"}
        and value.get("side") == expected_side
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and _integer(value.get("slot_index"))
        and value["slot_index"] >= 0
    )


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonnegative_int(value: Any) -> bool:
    return _integer(value) and value >= 0
