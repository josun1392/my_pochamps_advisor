"""Bounded observed damage-plus-phazing composition for Dragon Tail/Circle Throw."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observed_damage_application import OWNER_KEYS, apply_exact_observed_damage, exact_owner
from llm.advisor_observed_forced_switch_request import materialize_observed_forced_switch_request
from llm.advisor_transition_preview import fingerprint_transition_preview_state


OBSERVED_DAMAGE_PHAZING_SCHEMA_VERSION = "observed-damage-plus-phazing-result-v1"
_PROVENANCE = "trusted_observed_damage_plus_phazing_result_v1"
_REQUEST_PROVENANCE = "trusted_observed_forced_switch_request_v1"
_REQUIRED = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user", "target_owner",
    "move_id", "damage_amount", "damaging_hit_result", "drag_out_result", "provenance",
})
_SUPPORTED = frozenset({"dragon-tail", "circle-throw"})
_CANONICAL_AUTHORITY = {
    "source": "pokemon_showdown_data_moves_and_battle_actions_force_switch",
    "moves": {"dragon-tail": "forceSwitch", "circle-throw": "forceSwitch"},
    "sequence": "damage_before_drag_out",
    "drag_out_gate": "target_alive_source_alive_switch_available_then_DragOut",
    "target_ko": "suppresses_drag_out",
}


def materialize_observed_damage_plus_phazing_result(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply one already-observed exact hit and optionally emit an F1 request.

    Accuracy, immunity, protection, contact, and every other hit-resolution
    question are deliberately outside this adapter.  The supplied observation
    already answers them for this exact F0 action.
    """
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_damage_plus_phazing_branch")
    if not _valid_observation(observed_result, source_branch_fingerprint, active):
        return _result("rejected", "invalid_observed_damage_plus_phazing_result")

    user, target = observed_result["user"], observed_result["target_owner"]
    applied = apply_exact_observed_damage(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        user=user, target_owner=target, damage_amount=observed_result["damage_amount"],
    )
    if applied.get("status") != "resolved":
        return applied
    terminal = applied["damage_application"]["target_fainted"]
    if terminal and observed_result["drag_out_result"] != "not_applied":
        return _result("rejected", "drag_out_after_terminal_damage")
    state, resulting_fingerprint = applied["next_state"], applied["resulting_branch_fingerprint"]

    result = {
        **applied,
        "observed_damage_plus_phazing_result": deepcopy(dict(observed_result)),
        "damage_application": {
            "user": deepcopy(dict(user)), "target_owner": deepcopy(dict(target)),
            **applied["damage_application"], "provenance": _PROVENANCE,
        },
        "canonical_authority": deepcopy(_CANONICAL_AUTHORITY),
        "materialization": "pure_idempotent",
    }
    if observed_result["drag_out_result"] == "not_applied":
        return {**result, "drag_out": "not_applied"}

    observed_request = {
        "schema_version": "observed-forced-switch-request-v1",
        "session_id": target["session_id"],
        "source_branch_fingerprint": resulting_fingerprint,
        "target_owner": deepcopy(dict(target)),
        "request_kind": "drag_out", "result": "drag_out_requested",
        "provenance": _REQUEST_PROVENANCE,
    }
    materialized = materialize_observed_forced_switch_request(
        branch_state=state, source_branch_fingerprint=resulting_fingerprint, observed_request=observed_request,
    )
    if materialized.get("status") != "resolved":
        return materialized
    return {
        **result,
        "observed_forced_switch_request": materialized["observed_forced_switch_request"],
        "forced_switch_request": materialized["forced_switch_request"],
        "drag_out": "requested",
    }


def _valid_observation(value: Any, fingerprint: str, active: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or set(value) != _REQUIRED:
        return False
    user, target = value.get("user"), value.get("target_owner")
    damage = value.get("damage_amount")
    return (
        _exact_owner(user) and _exact_owner(target)
        and value.get("schema_version") == OBSERVED_DAMAGE_PHAZING_SCHEMA_VERSION
        and value.get("provenance") == _PROVENANCE
        and value.get("move_id") in _SUPPORTED
        and value.get("damaging_hit_result") == "applied"
        and value.get("drag_out_result") in {"drag_out_requested", "not_applied"}
        and isinstance(damage, int) and not isinstance(damage, bool) and damage > 0
        and value.get("source_branch_fingerprint") == fingerprint
        and value.get("session_id") == user["session_id"] == target["session_id"]
        and user["side"] != target["side"]
        and _current_owner(active, user) and _current_owner(active, target)
        and _active_hp_is_exact(active[target["side"]])
        and active[user["side"]].get("fainted") is False and active[target["side"]].get("fainted") is False
    )


def _exact_owner(value: Any) -> bool:
    return exact_owner(value)


def _current_owner(active: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    current = active.get(owner["side"])
    return isinstance(current, Mapping) and dict(owner) == {key: current.get(key) for key in OWNER_KEYS}


def _active_hp_is_exact(active: Mapping[str, Any]) -> bool:
    hp, maximum = active.get("current_hp"), active.get("max_hp")
    return (
        isinstance(hp, int) and not isinstance(hp, bool)
        and isinstance(maximum, int) and not isinstance(maximum, bool)
        and maximum > 0 and 0 < hp <= maximum
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
