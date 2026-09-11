"""Strict live nonconsecutive ordinary Protect/Detect success authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_hypothetical_protection_effects import canonical_protection_success_chain_metadata
from llm.advisor_runtime_d0_last_executed_move_authority import (
    SCHEMA_VERSION as LAST_MOVE_SCHEMA,
    freeze_runtime_d0_last_executed_move_authority,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-nonconsecutive-protection-success-authority-v1"


def freeze_runtime_d0_nonconsecutive_protection_success_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    protection_owner: Mapping[str, Any], protection_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove only the zero-count ordinary protection case from current history."""
    base = _base(strategy_d0, protection_owner, protection_action)
    if base is None:
        return _result("rejected", "invalid_nonconsecutive_protection_request", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    history = freeze_runtime_d0_last_executed_move_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=protection_owner,
    )
    if history.get("status") != "resolved":
        return _result(_status(history), history.get("reason", "last_executed_move_unavailable"), base,
                       last_executed_move_authority=history)
    if history.get("schema_version") != LAST_MOVE_SCHEMA or any(history.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) or history.get("owner") != base["protection_owner"]:
        return _result("rejected", "last_executed_move_authority_binding_mismatch", base,
                       last_executed_move_authority=history)
    previous_move_id = history.get("move_id")
    if not isinstance(previous_move_id, str) or not previous_move_id:
        return _result("rejected", "last_executed_move_identity_invalid", base,
                       last_executed_move_authority=history)
    # This maintained protection-success catalog is the shared chain-family owner.
    # A member proves that the current chain cannot be reset to zero here.
    if canonical_protection_success_chain_metadata(previous_move_id) is not None:
        return _result("incomplete", "previous_protection_success_chain_state_unproven", base,
                       last_executed_move_authority=history)
    success = {
        "schema_version": "branch-protection-success-v1",
        "owner": deepcopy(dict(protection_owner)),
        "previous_successful_protection_count": 0,
        "provenance": "explicit_branch_nonconsecutive_protection",
    }
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "last_executed_move_authority": deepcopy(dict(history)),
        "protection_success_authority": success,
        "provenance": "runtime_d0_current_nonconsecutive_ordinary_protection_success_v1",
    }


def _base(d0: Any, owner: Any, action: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(owner, Mapping) or d0.get("active_owners", {}).get("opponent") != dict(owner) or not isinstance(action, Mapping):
        return None
    metadata = action.get("metadata_authority", {}).get("metadata") if isinstance(action.get("metadata_authority"), Mapping) else None
    move_id = metadata.get("move_id") if isinstance(metadata, Mapping) else None
    if action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str) or action.get("move_id", action.get("identity")) != move_id or canonical_protection_success_chain_metadata(move_id) is None:
        return None
    if any(not isinstance(d0.get(key), str) or not d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "protection_owner": deepcopy(dict(owner)), "protection_action_id": action["action_id"],
        "protection_move_id": move_id,
    }


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "rejected", "unsupported"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
