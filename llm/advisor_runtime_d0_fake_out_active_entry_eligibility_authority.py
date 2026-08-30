"""Strict D0 reader for an explicit Fake Out current-active-entry observation."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-fake-out-active-entry-eligibility-authority-v1"


def freeze_runtime_d0_fake_out_active_entry_eligibility_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], fake_out_user: Mapping[str, Any], fake_out_action: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, fake_out_user, fake_out_action, target)
    if base is None: return _result("rejected", "invalid_runtime_d0_or_fake_out_action", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping) or state.get("session_id") != strategy_d0.get("session_id"): return _result("rejected", "runtime_snapshot_session_mismatch", base)
    context = state.get("fake_out_active_entry_eligibility_context")
    if context is None: return _result("incomplete", "fake_out_active_entry_eligibility_observation_missing", base)
    if not isinstance(context, Mapping) or not _matches(context, strategy_d0, fake_out_user, fake_out_action): return _result("rejected", "fake_out_active_entry_eligibility_binding_mismatch", base)
    sequence = context.get("provenance", {}).get("source_sequence") if isinstance(context.get("provenance"), Mapping) else None
    if not isinstance(sequence, int) or isinstance(sequence, bool) or state.get("last_applied_observation_sequence") != sequence: return _result("rejected", "stale_fake_out_active_entry_eligibility_observation", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "active_entry_token": context["active_entry_token"], "eligibility": context["eligibility"], "observation_sequence": sequence, "trusted_provenance": deepcopy(dict(context["provenance"])), "provenance": "runtime_d0_explicit_fake_out_active_entry_eligibility_observation_v1"}


def _base(d0: Mapping[str, Any], user: Mapping[str, Any], action: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(user, Mapping) or not isinstance(action, Mapping) or not isinstance(target, Mapping): return None
    owner_keys = {"session_id", "side", "slot_index", "pokemon_id"}
    if set(user) != owner_keys or set(target) != owner_keys or user.get("side") not in {"self", "opponent"} or target.get("side") not in {"self", "opponent"} or user.get("side") == target.get("side") or not isinstance(user.get("slot_index"), int) or not isinstance(target.get("slot_index"), int) or not isinstance(user.get("pokemon_id"), str) or not isinstance(target.get("pokemon_id"), str): return None
    if not all(isinstance(action.get(key), str) and action[key] for key in ("decision_point", "action_id")) or action.get("move_id") != "fake-out": return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(user.get("side")) != dict(user) or active.get(target.get("side")) != dict(target): return None
    if not all(isinstance(d0.get(key), str) and d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0.get("decision_owner")), "fake_out_user": deepcopy(dict(user)), "target": deepcopy(dict(target)), "decision_point": action["decision_point"], "fake_out_action_id": action["action_id"], "fake_out_move_id": "fake-out"}


def _matches(context: Mapping[str, Any], d0: Mapping[str, Any], user: Mapping[str, Any], action: Mapping[str, Any]) -> bool:
    provenance = context.get("provenance")
    return context.get("schema_version") == "fake-out-active-entry-eligibility-context-v1" and context.get("session_id") == d0.get("session_id") and context.get("actor") == dict(user) and context.get("decision_point") == action.get("decision_point") and context.get("action_id") == action.get("action_id") and context.get("move_id") == "fake-out" and context.get("eligibility") in {"eligible", "ineligible"} and isinstance(context.get("active_entry_token"), str) and bool(context["active_entry_token"]) and isinstance(provenance, Mapping) and provenance.get("event_kind") == "fake_out_active_entry_eligibility_observed" and provenance.get("trust") == "user_confirmed_observation"


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
