"""Private calculator view for an exact switch-entry major condition.

The view is deliberately detached from reducer/current-D0 authority.  It is
only an input adapter for the immediate attack-after-opponent-switch path.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


SCHEMA_VERSION = "detached-switch-first-hypothetical-condition-predictive-consumer-v1"
_CONDITIONS = frozenset({"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"})
_BINDINGS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")


def materialize_detached_switch_first_hypothetical_condition_predictive_view(
    *, strategy_d0: Mapping[str, Any], synthetic_runtime_state: Mapping[str, Any],
    switch_in_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a private D0-shaped view without promoting an entry condition."""
    base = _base(strategy_d0)
    if base is None or not isinstance(synthetic_runtime_state, Mapping):
        return _result("rejected", "invalid_switch_first_condition_request", {})
    target, condition, toxic = _switch_in_condition(switch_in_authority, base)
    if isinstance(target, str):
        return _result("rejected", target, base)
    if isinstance(condition, str) and condition not in _CONDITIONS:
        return _result("incomplete", condition, base, target_owner=target)
    state = deepcopy(dict(synthetic_runtime_state))
    raw = _active_target(state, target)
    if raw is None:
        return _result("rejected", "switch_first_condition_target_identity_mismatch", base, target_owner=target)
    original = raw.get("condition") or "none"
    changed = False
    if toxic.get("outcome") == "status_applied":
        expected = toxic.get("post_condition")
        if expected not in {"poison", "toxic"} or condition != expected:
            return _result("rejected", "switch_first_toxic_spikes_condition_conflict", base, target_owner=target)
        changed = True
    elif condition != original:
        # A no-effect entry result cannot silently replace an exact current
        # target condition.  Treat the disagreement as incomplete rather than
        # choosing either value.
        return _result("incomplete", "switch_first_hypothetical_condition_conflicts_with_current_target", base, target_owner=target)
    # This marker exists only in our deep-copy calculator view.  It makes the
    # switch-in authority (rather than stale bench/reducer provenance) the
    # source for both an applied condition and a strictly confirmed no-effect.
    raw["condition"] = condition
    raw["condition_provenance"] = {
        "event_kind": "current_condition_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "condition": condition,
        "hypothetical_provenance": "exact_detached_switch_entry_toxic_spikes",
    }
    raw["detached_switch_first_hypothetical_condition_authority"] = True
    snapshot = {
        "status": "runtime_snapshot_ready", "session_id": base["session_id"],
        "state": state, "state_fingerprint": state_fingerprint(state),
    }
    private_d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=base["decision_owner"])
    if private_d0.get("status") != "resolved":
        return _result("incomplete", private_d0.get("reason", "switch_first_hypothetical_condition_d0_unavailable"), base, target_owner=target)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "hypothetical": True, **base, "target_owner": deepcopy(target),
        "condition": condition, "condition_changed": changed,
        "entry_effect": "toxic_spikes" if changed else "none",
        "strategy_d0": private_d0, "runtime_snapshot": snapshot,
        "provenance": "exact_detached_switch_in_condition_private_calculator_view_v1",
    }


def _switch_in_condition(value: Any, base: Mapping[str, Any]) -> tuple[dict[str, Any] | str, str | dict[str, Any], Mapping[str, Any]]:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or any(value.get(key) != base[key] for key in _BINDINGS):
        return "switch_in_condition_binding_mismatch", {}, {}
    target = value.get("target_owner")
    hypothetical = value.get("hypothetical_switch_in_state")
    if not _owner(target) or not isinstance(hypothetical, Mapping) or hypothetical.get("active_owner") != dict(target):
        return "switch_in_condition_target_identity_mismatch", {}, {}
    authority = hypothetical.get("condition_authority")
    entry = hypothetical.get("entry_consequence")
    toxic = entry.get("toxic_spikes_consequence") if isinstance(entry, Mapping) else None
    if not isinstance(authority, Mapping) or authority.get("status") != "known" or authority.get("value") not in _CONDITIONS:
        return dict(target), "switch_in_hypothetical_condition_unknown", {}
    if not isinstance(toxic, Mapping) or toxic.get("status") != "complete" or toxic.get("outcome") not in {"absent", "prevented_by_heavy_duty_boots", "ungrounded", "absorbed", "status_immune", "already_statused", "status_prevented", "status_applied"}:
        return dict(target), "switch_in_toxic_spikes_consequence_unknown", {}
    return dict(target), authority["value"], toxic


def _active_target(state: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | None:
    side = state.get("opponent_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    raw = roster.get(target["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(side, Mapping) or side.get("active_slot_index") != target["slot_index"]:
        return None
    return raw if isinstance(raw, dict) and raw.get("pokemon_id") == target["pokemon_id"] else None


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(d0.get("decision_owner"), Mapping):
        return None
    base = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
    }
    return deepcopy(base) if all(base.get(key) for key in _BINDINGS) else None


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") == "opponent" and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
