"""Candidate-bound completeness classification for live secondary manifests."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "live-secondary-manifest-authority-v1"
_LIVE_WIRED = {
    "metal-claw": "probabilistic_self_stage_effect_authorities",
    "shadow-ball": "probabilistic_target_stage_effect_authorities",
    "thunderbolt": "thunderbolt_paralysis_authorities",
}
_KNOWN_UNWIRED = frozenset({"iron-head", "sparkling-aria"})


def freeze_live_secondary_manifest_authority(
    *, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], metadata_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one selected move without turning missing metadata into neutral.

    This authority decides only component completeness.  Secondary execution
    stays with the existing family-specific runtime authorities.
    """
    base = _base(strategy_d0, action)
    if base is None:
        return _result("rejected", "invalid_live_secondary_manifest_request", {})
    metadata = _metadata(metadata_authority, base)
    if isinstance(metadata, str):
        return _result("rejected", metadata, base)
    if metadata is None:
        return _result("incomplete", "canonical_secondary_metadata_unknown", base)
    move_id = metadata["move_id"]
    if move_id in _LIVE_WIRED:
        return _result("secondary_authority_required", None, base, required_authority_map=_LIVE_WIRED[move_id])
    if move_id in _KNOWN_UNWIRED:
        return _result("incomplete", "canonical_secondary_live_authority_unwired", base)
    neutral = _proven_no_secondary(metadata)
    if neutral is None:
        return _result("incomplete", "canonical_secondary_metadata_unknown", base)
    if neutral is False:
        return _result("incomplete", "canonical_secondary_live_authority_unwired", base)
    return _result("not_applicable", None, base, provenance="canonical_d0_bound_no_relevant_secondary_v1")


def _base(d0: Any, action: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping):
        return None
    action_id, move_id = action.get("action_id"), action.get("identity", action.get("move_id"))
    if action.get("action_type") != "attack" or not isinstance(action_id, str) or not isinstance(move_id, str) or not move_id:
        return None
    owner = d0.get("decision_owner")
    active = d0.get("active_owners")
    if not isinstance(owner, Mapping) or not isinstance(active, Mapping) or active.get(owner.get("side")) != dict(owner):
        return None
    return {
        "schema_version": SCHEMA_VERSION, "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(dict(owner)), "action_id": action_id, "move_id": move_id,
        "provenance": "runtime_d0_canonical_secondary_manifest_binding_v1",
    }


def _metadata(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("schema_version") != "runtime-d0-selectable-move-metadata-authority-v1":
        return "canonical_secondary_metadata_schema_invalid"
    expected = {
        "candidate_id": base["action_id"], "move_id": base["move_id"], "session_id": base["session_id"],
        "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"],
        "active_attacker": base["decision_owner"],
    }
    if any(value.get(key) != item for key, item in expected.items()):
        return "canonical_secondary_metadata_binding_mismatch"
    if value.get("status") != "resolved":
        return None
    metadata = value.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != base["move_id"]:
        return "canonical_secondary_metadata_move_mismatch"
    return deepcopy(dict(metadata))


def _proven_no_secondary(metadata: Mapping[str, Any]) -> bool | None:
    """Accept only explicit canonical neutral fields for the bounded families."""
    chance, ailment, changes = metadata.get("effect_chance"), metadata.get("ailment"), metadata.get("stat_changes")
    chance_known = chance is None or (isinstance(chance, int) and not isinstance(chance, bool) and chance == 0)
    if not chance_known or ailment != "none" or not isinstance(changes, list) or changes:
        return False if chance is not None and ailment is not None and isinstance(changes, list) else None
    return True


def _result(status: str, reason: str | None, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
