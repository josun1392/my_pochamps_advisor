"""Strict D0-bound contact classification for one selected direct attack."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-canonical-contact-classification-authority-v1"
_PATH = Path(__file__).parents[1] / "data" / "static" / "move_flags.json"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_canonical_contact_classification_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze only canonical contact/non-contact for one current direct attack."""
    base = _base(strategy_d0)
    if base is None or not _owner(attacker) or not _owner(target):
        return _result("rejected", "invalid_runtime_d0_or_contact_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    active = strategy_d0.get("active_owners", {})
    expected_attacker = strategy_d0.get("decision_owner")
    expected_target = active.get("opponent" if isinstance(expected_attacker, Mapping) and expected_attacker.get("side") == "self" else "self")
    if attacker != expected_attacker or target != expected_target:
        return _result("rejected", "contact_actor_or_target_not_current_d0_action_pair", base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {
        **base, "action_id": action.get("action_id") if isinstance(action, Mapping) else None,
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)),
        "move_metadata_authority": deepcopy(metadata_authority),
        "provenance": "runtime_d0_canonical_move_contact_classification_v1",
    }
    if metadata_authority.get("status") != "resolved":
        status = metadata_authority.get("status")
        return _result(
            "rejected" if status == "rejected" else "incomplete",
            metadata_authority.get("reason", "contact_move_metadata_unavailable"), common,
        )
    metadata = metadata_authority.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != action.get("identity"):
        return _result("rejected", "contact_metadata_action_identity_mismatch", common)
    if metadata.get("category") not in {"physical", "special"}:
        return _result("incomplete", "contact_action_not_direct_damaging_move", common)
    action_target = action.get("target_owner") if isinstance(action, Mapping) else None
    if action_target is not None and action_target != target:
        return _result("rejected", "contact_action_target_binding_mismatch", common)
    classification = canonical_move_contact_metadata(metadata.get("move_id"))
    if classification.get("status") != "resolved":
        return _result(classification["status"], classification["reason"], {**common, "canonical_contact_metadata": classification})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "move_id": metadata["move_id"], "contact_state": classification["contact_state"],
        "canonical_contact_metadata": classification,
    }


def canonical_move_contact_metadata(move_id: Any) -> dict[str, Any]:
    """Read only the maintained move-flags catalog; absence is never neutral."""
    if not isinstance(move_id, str) or not move_id:
        return {"status": "rejected", "reason": "canonical_contact_move_identity_invalid"}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "rejected", "reason": "canonical_contact_catalog_unreadable"}
    flags_by_move = data.get("flags_by_move") if isinstance(data, Mapping) and data.get("version") == "gen9" else None
    if not isinstance(flags_by_move, Mapping):
        return {"status": "rejected", "reason": "canonical_contact_catalog_invalid"}
    flags = flags_by_move.get(move_id)
    if flags is None:
        return {"status": "incomplete", "reason": "canonical_move_contact_metadata_missing", "move_id": move_id}
    if not isinstance(flags, list) or any(not isinstance(flag, str) or not flag for flag in flags) or len(flags) != len(set(flags)):
        return {"status": "rejected", "reason": "canonical_move_contact_metadata_malformed", "move_id": move_id}
    return {
        "status": "resolved", "move_id": move_id,
        "contact_state": "contact" if "contact" in flags else "non_contact",
        "flags": tuple(flags), "provenance": "data/static/move_flags.json:gen9",
    }


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(value.get("decision_owner")):
        return None
    return {
        "session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"],
        "source_branch_fingerprint": value["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(value["decision_owner"])),
    }


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
