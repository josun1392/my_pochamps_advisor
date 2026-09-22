"""Strict current-D0 facts for Locked On target binding and Gravity field state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_lifecycle_confirmation import GRAVITY_SOURCE, LOCKED_ON_SOURCE
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


LOCKED_ON_SCHEMA_VERSION = "runtime-d0-locked-on-target-binding-authority-v1"
GRAVITY_SCHEMA_VERSION = "runtime-d0-gravity-field-authority-v1"
_OWNER_KEYS = frozenset({"session_id", "side", "slot_index", "pokemon_id"})


def freeze_runtime_d0_locked_on_target_binding_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    source_owner: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze only the exact current Locked On fact for one active source owner."""
    base = _base(strategy_d0, source_owner, LOCKED_ON_SCHEMA_VERSION)
    if base is None:
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_d0_or_source_owner_invalid")
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, fresh.get("reason", "stale_runtime_d0"))

    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    pokemon = _pokemon(state, source_owner)
    if pokemon is None:
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_source_owner_identity_mismatch")
    value = pokemon.get("locked_on_state")
    provenance = pokemon.get("locked_on_state_provenance")
    if is_unknown_battle_fact(value):
        if provenance is not None:
            return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_unknown_provenance_mismatch")
        return {
            **base,
            "status": "incomplete",
            "reason": "current_locked_on_state_unknown",
            "locked_on_state": {"status": "unknown"},
        }
    if not _trusted_provenance(provenance, "current_locked_on_state_observed", LOCKED_ON_SOURCE):
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_observation_provenance_invalid")
    if value == {"status": "known_inactive"}:
        return {
            **base,
            "status": "resolved",
            "locked_on_state": {"status": "known_inactive"},
            "observation_provenance": deepcopy(dict(provenance)),
            "targetability_outcome": None,
            "provenance": "strict_runtime_d0_current_locked_on_target_binding_v1",
        }
    if not isinstance(value, Mapping) or set(value) != {"status", "bound_target"} or value.get("status") != "known_active":
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_current_state_malformed")
    target = value.get("bound_target")
    if not _owner(target) or target.get("session_id") != strategy_d0.get("session_id") or target.get("side") == source_owner.get("side"):
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_bound_target_binding_invalid")
    if _pokemon(state, target) is None:
        return _result("rejected", LOCKED_ON_SCHEMA_VERSION, "locked_on_bound_target_identity_mismatch")
    return {
        **base,
        "status": "resolved",
        "locked_on_state": {
            "status": "known_active",
            "bound_target": deepcopy(dict(target)),
        },
        "observation_provenance": deepcopy(dict(provenance)),
        "targetability_outcome": None,
        "provenance": "strict_runtime_d0_current_locked_on_target_binding_v1",
    }


def freeze_runtime_d0_gravity_field_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the exact current Gravity field fact without predicting duration."""
    owner = strategy_d0.get("decision_owner") if isinstance(strategy_d0, Mapping) else None
    base = _base(strategy_d0, owner, GRAVITY_SCHEMA_VERSION)
    if base is None:
        return _result("rejected", GRAVITY_SCHEMA_VERSION, "gravity_d0_invalid")
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", GRAVITY_SCHEMA_VERSION, fresh.get("reason", "stale_runtime_d0"))
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    field = state.get("field") if isinstance(state, Mapping) else None
    if not isinstance(field, Mapping):
        return _result("rejected", GRAVITY_SCHEMA_VERSION, "gravity_field_state_invalid")
    value = field.get("gravity_status")
    provenance = field.get("gravity_status_provenance")
    if is_unknown_battle_fact(value):
        if provenance is not None:
            return _result("rejected", GRAVITY_SCHEMA_VERSION, "gravity_unknown_provenance_mismatch")
        return {
            **base,
            "status": "incomplete",
            "reason": "current_gravity_state_unknown",
            "gravity": {"status": "unknown"},
        }
    if value not in {"active", "inactive"}:
        return _result("rejected", GRAVITY_SCHEMA_VERSION, "gravity_current_state_malformed")
    if not _trusted_provenance(provenance, "gravity_field_observed", GRAVITY_SOURCE):
        return _result("rejected", GRAVITY_SCHEMA_VERSION, "gravity_observation_provenance_invalid")
    return {
        **base,
        "status": "resolved",
        "scope": "battle_field",
        "gravity": {"status": value},
        "observation_provenance": deepcopy(dict(provenance)),
        "remaining_duration": None,
        "targetability_outcome": None,
        "provenance": "strict_runtime_d0_current_gravity_field_v1",
    }


def _base(
    strategy_d0: Any, owner: Any, schema_version: str,
) -> dict[str, Any] | None:
    if (
        not isinstance(strategy_d0, Mapping)
        or strategy_d0.get("status") != "resolved"
        or not _owner(owner)
        or owner.get("session_id") != strategy_d0.get("session_id")
        or strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner)
        or not isinstance(strategy_d0.get("source_runtime_fingerprint"), str)
        or not strategy_d0["source_runtime_fingerprint"]
        or not isinstance(strategy_d0.get("strategy_preview_fingerprint"), str)
        or not strategy_d0["strategy_preview_fingerprint"]
    ):
        return None
    return {
        "schema_version": schema_version,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "source_owner": deepcopy(dict(owner)),
    }


def _pokemon(state: Any, owner: Any) -> Mapping[str, Any] | None:
    if not isinstance(state, Mapping) or not _owner(owner) or owner.get("session_id") != state.get("session_id"):
        return None
    side = state.get(f"{owner['side']}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(owner["slot_index"], roster.get(str(owner["slot_index"]))) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id", pokemon.get("name_en")) != owner["pokemon_id"]:
        return None
    return pokemon


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _OWNER_KEYS
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value.get("slot_index"), bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _trusted_provenance(value: Any, event_kind: str, source: str) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("event_kind") == event_kind
        and value.get("trust") == "user_confirmed_observation"
        and value.get("source") == source
        and isinstance(value.get("turn_number"), int)
        and not isinstance(value.get("turn_number"), bool)
        and value["turn_number"] >= 1
        and isinstance(value.get("source_observation_id"), str)
        and bool(value["source_observation_id"])
        and isinstance(value.get("source_sequence"), int)
        and not isinstance(value.get("source_sequence"), bool)
        and value["source_sequence"] >= 1
    )


def _result(status: str, schema_version: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": schema_version, "reason": reason}
