"""Bounded observed damage-plus-phazing composition for Dragon Tail/Circle Throw."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observed_forced_switch_request import materialize_observed_forced_switch_request
from llm.advisor_transition_preview import fingerprint_transition_preview_state


OBSERVED_DAMAGE_PHAZING_SCHEMA_VERSION = "observed-damage-plus-phazing-result-v1"
_PROVENANCE = "trusted_observed_damage_plus_phazing_result_v1"
_REQUEST_PROVENANCE = "trusted_observed_forced_switch_request_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
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
    state = deepcopy(dict(branch_state))
    current_target = state["active"][target["side"]]
    post_hp = max(0, current_target["current_hp"] - observed_result["damage_amount"])
    terminal = post_hp == 0
    if terminal and observed_result["drag_out_result"] != "not_applied":
        return _result("rejected", "drag_out_after_terminal_damage")
    current_target["current_hp"] = post_hp
    current_target["fainted"] = terminal
    _sync_hp(state, target["side"], post_hp, current_target["max_hp"])
    resulting_fingerprint = fingerprint_transition_preview_state(state)
    if resulting_fingerprint is None:
        return _result("rejected", "unserializable_damage_plus_phazing_branch")

    result = {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": resulting_fingerprint,
        "next_state": state,
        "observed_damage_plus_phazing_result": deepcopy(dict(observed_result)),
        "damage_application": {
            "user": deepcopy(dict(user)), "target_owner": deepcopy(dict(target)),
            "damage": observed_result["damage_amount"], "post_hp": post_hp,
            "target_fainted": terminal, "provenance": _PROVENANCE,
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
        and active[user["side"]].get("fainted") is False and active[target["side"]].get("fainted") is False
    )


def _exact_owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _current_owner(active: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    current = active.get(owner["side"])
    return isinstance(current, Mapping) and dict(owner) == {key: current.get(key) for key in _OWNER_KEYS}


def _sync_hp(state: Mapping[str, Any], side: str, hp: int, maximum: int) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    if not isinstance(current, dict):
        return
    rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current.get("current_hp_context"), Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == side:
                row["current_hp"], row["maximum_hp"] = hp, maximum
    direct = current.get("direct_mechanics_context")
    role = "attacker" if side == "self" else "defender"
    combatant = direct.get(role) if isinstance(direct, Mapping) else None
    if isinstance(combatant, dict):
        combatant["current_hp"], combatant["max_hp"] = hp, maximum


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
