"""Sludge Bomb-only trusted observed damage plus target-poison consequence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_hypothetical_condition_effects import apply_predicted_condition
from llm.advisor_observed_damage_application import apply_exact_observed_damage, exact_owner
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "observed-damage-plus-target-condition-result-v1"
_PROVENANCE = "trusted_observed_damage_plus_target_condition_result_v1"
_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user", "target_owner",
    "move_id", "damage_amount", "damaging_hit_result", "target_condition_result",
    "condition", "provenance",
})


def materialize_observed_sludge_bomb(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize exact Sludge Bomb damage, then an F1-bound poison overlay."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_sludge_bomb_branch")
    if not _valid(observed_result, source_branch_fingerprint):
        return _result("rejected", "invalid_observed_sludge_bomb_result")
    user, target = observed_result["user"], observed_result["target_owner"]
    damage = apply_exact_observed_damage(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        user=user, target_owner=target, damage_amount=observed_result["damage_amount"],
    )
    if damage.get("status") != "resolved":
        return damage
    f1, f1_fingerprint = damage["next_state"], damage["resulting_branch_fingerprint"]
    if observed_result["target_condition_result"] == "not_applied":
        return {
            **damage, "f1_branch_fingerprint": f1_fingerprint,
            "observed_damage_plus_target_condition_result": deepcopy(dict(observed_result)),
            "target_condition": "not_applied",
        }
    if damage["damage_application"].get("target_hit_substitute"):
        return _result("rejected", "condition_blocked_by_substitute")
    if damage["damage_application"]["target_fainted"]:
        return _result("rejected", "condition_after_terminal_damage")
    if _existing_condition(f1, target) != "none":
        return _result("rejected", "target_existing_condition_conflict")
    state = deepcopy(dict(f1))
    authority = {
        "schema_version": "observed-sludge-bomb-target-condition-authority-v1",
        "source_branch_fingerprint": f1_fingerprint, "owner": deepcopy(dict(target)),
        "condition": "poison", "provenance": _PROVENANCE,
    }
    apply_predicted_condition(
        state,
        {"status": "resolved", "applicable": True, "ailment": "poison", "owner": authority["owner"]},
        source_snapshot_fingerprint=f1_fingerprint, branch_state_fingerprint=f1_fingerprint,
    )
    state["predicted_condition_context"]["provenance"] = "turn_engine_observed_sludge_bomb_poison"
    f2_fingerprint = fingerprint_transition_preview_state(state)
    if f2_fingerprint is None:
        return _result("rejected", "unserializable_observed_target_condition_branch")
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "f1_branch_fingerprint": f1_fingerprint, "resulting_branch_fingerprint": f2_fingerprint,
        "next_state": state, "observed_damage_plus_target_condition_result": deepcopy(dict(observed_result)),
        "target_condition_authority": authority, "damage_application": damage["damage_application"],
        "target_condition_application": {"owner": deepcopy(dict(target)), "condition": "poison"},
        "materialization": "pure_idempotent",
    }


def _valid(value: Any, fingerprint: str) -> bool:
    if not isinstance(value, Mapping) or set(value) != _KEYS:
        return False
    user, target, damage, result = value.get("user"), value.get("target_owner"), value.get("damage_amount"), value.get("target_condition_result")
    condition_ok = (result == "applied" and value.get("condition") == "poison") or (result == "not_applied" and value.get("condition") is None)
    return (
        exact_owner(user) and exact_owner(target) and value.get("schema_version") == SCHEMA_VERSION
        and value.get("provenance") == _PROVENANCE and value.get("move_id") == "sludge-bomb"
        and value.get("damaging_hit_result") == "applied" and isinstance(damage, int)
        and not isinstance(damage, bool) and damage > 0 and condition_ok
        and value.get("source_branch_fingerprint") == fingerprint
        and value.get("session_id") == user["session_id"] == target["session_id"] and user["side"] != target["side"]
    )


def _existing_condition(state: Mapping[str, Any], owner: Mapping[str, Any]) -> str | None:
    predicted = state.get("predicted_condition_context") if isinstance(state, Mapping) else None
    if isinstance(predicted, Mapping) and predicted.get("owner") == dict(owner):
        return predicted.get("condition_type") if predicted.get("condition_type") in {"poison", "toxic"} else None
    return _current_condition(state, owner["side"])


def _current_condition(state: Mapping[str, Any], side: str) -> str | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("condition_context", {}).get("current_conditions") if isinstance(current, Mapping) else None
    row = next((entry for entry in rows if isinstance(entry, Mapping) and entry.get("side") == side), None) if isinstance(rows, list) else None
    if not isinstance(row, Mapping) or row.get("status") != "user_confirmed" or row.get("source") != "user_confirmed_current_condition":
        return None
    return row.get("condition_type") if row.get("condition_type") in {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"} else None


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
