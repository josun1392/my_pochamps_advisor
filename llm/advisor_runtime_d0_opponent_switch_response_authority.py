"""Strict D0-bound authority for explicit opponent switch responses."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-opponent-switch-response-authority-v1"


def freeze_runtime_d0_opponent_switch_response_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved": return _result("rejected", "invalid_runtime_d0", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"), _base(strategy_d0))
    base = _base(strategy_d0)
    if not base: return _result("rejected", "invalid_runtime_d0_owners", {})
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    side = state.get("opponent_side") if isinstance(state, Mapping) else None
    if not isinstance(side, Mapping) or side.get("active_slot_index") != base["opponent_actor"]["slot_index"] or not isinstance(side.get("pokemon"), Mapping): return _result("rejected", "runtime_active_opponent_identity_mismatch", base)
    active = side["pokemon"].get(base["opponent_actor"]["slot_index"])
    if not isinstance(active, Mapping) or active.get("pokemon_id") != base["opponent_actor"]["pokemon_id"]: return _result("rejected", "runtime_active_opponent_identity_mismatch", base)
    record = side.get("current_opponent_switch_response_set")
    if not isinstance(record, Mapping): return _result("incomplete", "opponent_switch_response_set_unknown", base)
    if not _record_valid(record, state, base["opponent_actor"]): return _result("rejected", "opponent_switch_response_set_record_invalid", base)
    provenance = record["provenance"]
    if provenance.get("source_sequence") != state.get("last_applied_observation_sequence"):
        return _result("incomplete", "opponent_switch_response_observation_not_current", base)
    permission = record["permission"]
    if permission == "unknown": return _result("incomplete", "opponent_switch_permission_unknown", base)
    targets = tuple(deepcopy(record["targets"]))
    if any(row["availability"] == "unknown" for row in targets): return _result("incomplete", "opponent_switch_target_availability_unknown", base, switch_permission=permission, targets=targets)
    actions = tuple({"action_id": f"opponent_switch:{base['session_id']}:{row['slot_index']}:{row['pokemon_id']}", "action_type": "manual_switch", "acting_side": "opponent", "target_side": "self", "selectability": "selectable" if permission == "permitted" and row["availability"] == "alive" else "not_selectable", "target_owner": {"session_id": base["session_id"], "side": "opponent", "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"]}, "availability": row["availability"]} for row in targets)
    selectable = tuple(row["action_id"] for row in actions if row["selectability"] == "selectable")
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "switch_permission": permission, "target_set_completeness": "complete", "targets": targets, "actions": actions, "selectable_response_action_ids": selectable, "response_probability": "not_modeled", "provenance": "runtime_d0_explicit_opponent_switch_response_authority_v1", "response_set_provenance": deepcopy(provenance)}


def _base(d0: Mapping[str, Any]) -> dict:
    owners = d0.get("active_owners") if isinstance(d0, Mapping) else None
    own, opponent = owners.get("self") if isinstance(owners, Mapping) else None, owners.get("opponent") if isinstance(owners, Mapping) else None
    if not isinstance(own, Mapping) or not isinstance(opponent, Mapping): return {}
    return {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")), "own_actor": deepcopy(own), "opponent_actor": deepcopy(opponent)}


def _record_valid(record: Mapping[str, Any], state: Mapping[str, Any], opponent: Mapping[str, Any]) -> bool:
    if set(record) != {"schema_version", "permission", "target_set_completeness", "targets", "active_owner", "provenance"} or record.get("schema_version") != "current-opponent-switch-response-set-v1" or record.get("permission") not in {"permitted", "blocked", "unknown"} or record.get("target_set_completeness") != "complete" or record.get("active_owner") != opponent or not isinstance(record.get("targets"), list): return False
    seen = set(); roster = state.get("opponent_side", {}).get("pokemon", {}) if isinstance(state.get("opponent_side"), Mapping) else {}
    for row in record["targets"]:
        owner = (row.get("slot_index"), row.get("pokemon_id")) if isinstance(row, Mapping) else None; pokemon = roster.get(owner[0]) if owner else None
        if not isinstance(row, Mapping) or set(row) != {"slot_index", "pokemon_id", "availability"} or owner in seen or owner[0] == opponent["slot_index"] or not isinstance(owner[0], int) or isinstance(owner[0], bool) or owner[0] < 0 or not isinstance(owner[1], str) or not owner[1] or row.get("availability") not in {"alive", "fainted", "unknown"} or not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != owner[1]: return False
        seen.add(owner)
    provenance = record.get("provenance")
    return isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_opponent_switch_response_set_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] >= 1


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
