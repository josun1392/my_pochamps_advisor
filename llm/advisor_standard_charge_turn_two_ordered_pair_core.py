"""Bind one observed standard-charge turn to its real release-turn pair.

This is intentionally a narrow transport owner.  It does not model a charge
turn's damage, Power Herb consumption, or secondary effects; it merely proves
that an already observed Razor Wind charge belongs to the D0 from which the
release-turn immediate pair is materialized.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "standard-charge-turn-two-ordered-pair-core-v1"
_STANDARD_CHARGE_MOVE = "razor-wind"


def materialize_standard_charge_turn_two_ordered_pair_core(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], charge_observation: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any], action_order_authority: Mapping[str, Any], quick_claw_action_order_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Materialize a real release pair only after an identity-bound charge source.

    The source is an immutable runtime observation, not a caller-provided
    boolean.  This prevents a later action or a foreign active Pokemon from
    borrowing the charge state.
    """
    source = freeze_standard_charge_temporal_source(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        charge_observation=charge_observation, own_action=own_action,
    )
    if source.get("status") != "resolved":
        return _result(source.get("status", "rejected"), source.get("reason", "standard_charge_source_unavailable"), temporal_source=source)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        own_action=own_action, opponent_action=opponent_action,
        action_order_authority=action_order_authority,
        quick_claw_action_order_authority=quick_claw_action_order_authority,
    )
    if pair.get("status") != "evaluable":
        return _result(pair.get("status", "rejected"), pair.get("reason", "release_pair_unavailable"), temporal_source=source, immediate_pair=pair)
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    if ledger.get("status") != "evaluable":
        return _result(ledger.get("status", "rejected"), ledger.get("reason", "release_ledger_unavailable"), temporal_source=source, immediate_pair=pair, exact_ledger=ledger)
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION,
        "temporal_source": source, "immediate_pair": deepcopy(pair),
        "exact_ledger": deepcopy(ledger),
        "provenance": "observed_standard_charge_to_runtime_d0_ordered_pair_v1",
    }


def freeze_standard_charge_temporal_source(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], charge_observation: Mapping[str, Any], own_action: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the only permitted Razor Wind charge source for this D0."""
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"))
    owner = strategy_d0.get("active_owners", {}).get("self") if isinstance(strategy_d0.get("active_owners"), Mapping) else None
    if not isinstance(owner, Mapping) or strategy_d0.get("decision_owner") != owner:
        return _result("rejected", "standard_charge_decision_owner_invalid")
    if not isinstance(charge_observation, Mapping) or charge_observation.get("event_kind") != "used_move_observed" or charge_observation.get("move_id") != _STANDARD_CHARGE_MOVE or charge_observation.get("confirmed") is not True:
        return _result("rejected", "standard_charge_observation_invalid")
    if any(charge_observation.get(key) != owner.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")):
        return _result("rejected", "standard_charge_observation_owner_mismatch")
    if own_action.get("action_id") is None or own_action.get("identity") != _STANDARD_CHARGE_MOVE:
        return _result("rejected", "standard_charge_release_action_invalid")
    metadata = own_action.get("move_metadata_authority")
    if not isinstance(metadata, Mapping) or metadata.get("status") != "resolved" or metadata.get("move_id") != _STANDARD_CHARGE_MOVE or metadata.get("metadata", {}).get("move_id") != _STANDARD_CHARGE_MOVE:
        return _result("rejected", "standard_charge_release_metadata_invalid")
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    roster = state.get("self_side", {}).get("pokemon") if isinstance(state, Mapping) and isinstance(state.get("self_side"), Mapping) else None
    pokemon = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    provenance = pokemon.get("known_move_ids_provenance", {}).get(_STANDARD_CHARGE_MOVE) if isinstance(pokemon, Mapping) and isinstance(pokemon.get("known_move_ids_provenance"), Mapping) else None
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") != "used_move_observed" or provenance.get("source_observation_id") != charge_observation.get("observation_id"):
        return _result("rejected", "standard_charge_runtime_source_not_replayed")
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(owner)),
        "charge_move_id": _STANDARD_CHARGE_MOVE, "charge_observation_id": charge_observation["observation_id"],
        "release_action_id": own_action["action_id"], "provenance": "runtime_observation_reducer_temporal_source_freeze_v1",
    }


def _result(status: str, reason: str, **values: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason, **{key: deepcopy(value) for key, value in values.items()}}
