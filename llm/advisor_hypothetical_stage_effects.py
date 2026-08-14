"""Detached, self-target stage-effect projection for the Turn Engine."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_STATS = frozenset({"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"})


def project_self_stage_change(*, branch_state: Mapping[str, Any], action: Mapping[str, Any], expected_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Return one exact self-stage transition without mutating observations."""
    if not isinstance(branch_state, Mapping) or branch_state.get("schema_version") != "deterministic-transition-preview-v1":
        return _result("rejected", "invalid_branch_state")
    if not _same_owner(action.get("owner"), expected_owner) or expected_owner.get("side") != "self":
        return _result("rejected", "stale_or_mismatched_stage_owner")
    move = action.get("move")
    if not isinstance(move, Mapping) or move.get("category") != "status":
        return _result("unsupported", "self_stage_action_not_status")
    if move.get("target") != "user":
        return _result("unsupported", "self_stage_target_unsupported")
    # ``None`` is canonical PokeAPI metadata for a self action without an
    # accuracy roll.  Anything else would require a success/RNG contract.
    if move.get("accuracy") is not None:
        return _result("incomplete", "self_stage_move_success_uncertain")
    changes = _one_exact_stat_change(move.get("stat_changes"))
    if changes is None:
        return _result("unsupported", "self_stage_effect_metadata")
    stat, delta = changes
    current = branch_state.get("current_state")
    context = current.get("stat_stage_context") if isinstance(current, Mapping) else None
    entries = context.get("current_stages") if isinstance(context, Mapping) else None
    base = next((entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == "self" and entry.get("stat") == stat), None) if isinstance(entries, list) else None
    if not _trusted_stage(base):
        return _result("incomplete", f"self.{stat}_stage")
    stage = base["stage"]
    projected = max(-6, min(6, stage + delta))
    return {
        "status": "resolved",
        "stat": stat,
        "previous_stage": stage,
        "delta": delta,
        "projected_stage": projected,
        "owner": deepcopy(dict(expected_owner)),
    }


def apply_predicted_stage_change(branch_state: Mapping[str, Any], effect: Mapping[str, Any]) -> None:
    """Attach a detached predictive overlay; never alter observation records."""
    if not isinstance(branch_state, dict) or effect.get("status") != "resolved":
        raise ValueError("invalid_stage_effect")
    branch_state["predicted_stage_context"] = {
        "schema_version": "hypothetical-self-stage-v1",
        "owner": deepcopy(dict(effect["owner"])),
        "stat": effect["stat"],
        "previous_stage": effect["previous_stage"],
        "delta": effect["delta"],
        "projected_stage": effect["projected_stage"],
    }


def overlay_predicted_stage_for_direct_mechanics(current_state: Mapping[str, Any], predicted: Any) -> dict[str, Any] | None:
    """Build the private calculator view of a valid detached stage overlay."""
    if predicted is None:
        return deepcopy(dict(current_state))
    if not isinstance(predicted, Mapping) or predicted.get("schema_version") != "hypothetical-self-stage-v1" or predicted.get("owner", {}).get("side") != "self":
        return None
    stat, projected = predicted.get("stat"), predicted.get("projected_stage")
    if stat not in _STATS or isinstance(projected, bool) or not isinstance(projected, int) or not -6 <= projected <= 6:
        return None
    current = deepcopy(dict(current_state))
    context = current.get("stat_stage_context")
    entries = context.get("current_stages") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return None
    match = next((entry for entry in entries if isinstance(entry, dict) and entry.get("side") == "self" and entry.get("stat") == stat), None)
    if match is None:
        return None
    match["stage"] = projected
    return current


def _one_exact_stat_change(value: Any) -> tuple[str, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 1:
        return None
    item = value[0]
    if isinstance(item, Mapping):
        raw_stat, delta = item.get("stat"), item.get("change")
        stat = raw_stat.get("name") if isinstance(raw_stat, Mapping) else raw_stat
    elif isinstance(item, tuple) and len(item) == 2:
        stat, delta = item
    else:
        return None
    if not isinstance(stat, str) or stat not in _STATS or isinstance(delta, bool) or not isinstance(delta, int) or delta == 0 or not -6 <= delta <= 6:
        return None
    return stat, delta


def _trusted_stage(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "user_confirmed" and value.get("source") == "user_confirmed_current_stat_stage" and value.get("confidence") == "known" and isinstance(value.get("stage"), int) and not isinstance(value.get("stage"), bool) and -6 <= value["stage"] <= 6


def _same_owner(value: Any, expected: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and all(value.get(key) == expected.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id"))


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
