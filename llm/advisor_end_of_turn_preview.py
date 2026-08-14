"""Small, pure end-of-turn continuation for detached Turn Engine branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.probability.residual import ResidualSpec, residual_damage_amount
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def project_poison_end_of_turn(*, pre_end_of_turn: Mapping[str, Any]) -> dict[str, Any]:
    """Apply only exact poison residuals to a pre-EOT detached transition result."""
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn":
        return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state")
    source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None:
        return _result("rejected", "invalid_pre_end_of_turn_branch")
    state = deepcopy(dict(source))
    trace: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        active = _active(state, side)
        if active is None:
            return _result("rejected", "invalid_active_owner")
        if active["fainted"]:
            continue
        condition = _condition(state, side, pre_end_of_turn.get("source_snapshot_fingerprint"), source_fp)
        if isinstance(condition, dict):
            return _result(condition["status"], condition["reason"])
        if condition == "none":
            continue
        if condition == "toxic":
            toxic = _toxic_lifecycle(state, side, pre_end_of_turn.get("source_snapshot_fingerprint"))
            if isinstance(toxic, dict) and toxic.get("status"):
                return toxic
            stage = toxic
        elif condition == "poison":
            stage = None
        else:
            continue
        ability = _ability(state, side)
        if ability is None:
            return _result("incomplete", f"{side}.ability")
        if ability == "poison-heal":
            return _result("unsupported", "poison_heal_end_of_turn_not_in_slice")
        hp, maximum = active["current_hp"], active["max_hp"]
        damage = 0 if ability == "magic-guard" else residual_damage_amount(ResidualSpec(condition, maximum), stage or 1)
        post = max(0, hp - damage)
        active["current_hp"], active["fainted"] = post, post == 0
        _sync_hp(state, side, post, maximum)
        row = {"sequence": len(trace) + 1, "effect": f"{condition}_residual", "side": side, "owner": _owner(active), "condition": condition, "pre_hp": hp, "damage": damage, "post_hp": post, "execution_status": "prevented" if ability == "magic-guard" else "executed", "reason": "magic_guard" if ability == "magic-guard" else f"canonical_{condition}_residual"}
        if stage is not None:
            lifecycle = state["predicted_toxic_lifecycle"]
            lifecycle["current_stage"] = min(stage + 1, 15)
            row.update(toxic_stage=stage, resulting_toxic_stage=lifecycle["current_stage"], lifecycle_provenance=lifecycle["provenance"])
        trace.append(row)
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "limitations": ["poison_and_predicted_toxic_residual_only", "no_reducer_or_runtime_writeback"]}


def _condition(state: Mapping[str, Any], side: str, source_snapshot_fp: Any, source_fp: str) -> str | dict[str, str]:
    predicted = state.get("predicted_condition_context")
    if isinstance(predicted, Mapping) and predicted.get("owner", {}).get("side") == side:
        lifecycle = state.get("predicted_toxic_lifecycle")
        valid_source = predicted.get("source_snapshot_fingerprint") == source_snapshot_fp or (isinstance(lifecycle, Mapping) and predicted.get("source_snapshot_fingerprint") == lifecycle.get("source_snapshot_fingerprint"))
        if not valid_source or predicted.get("branch_state_fingerprint") is None:
            return _result("rejected", "stale_predicted_condition_overlay")
        # The overlay's original branch can legitimately precede later direct HP
        # consequences; ownership and source snapshot remain the safe bindings.
        if predicted.get("condition_type") not in {"poison", "toxic"}:
            return _result("rejected", "invalid_predicted_condition_overlay")
        return predicted["condition_type"]
    current = state.get("current_state")
    entries = current.get("condition_context", {}).get("current_conditions") if isinstance(current, Mapping) else None
    match = next((row for row in entries if isinstance(row, Mapping) and row.get("side") == side), None) if isinstance(entries, list) else None
    if not isinstance(match, Mapping) or match.get("status") != "user_confirmed" or match.get("source") != "user_confirmed_current_condition" or match.get("condition_type") not in {"none", "poison", "toxic", "burn", "paralysis", "sleep", "freeze"}:
        return _result("incomplete", f"{side}.condition")
    return match["condition_type"]


def _ability(state: Mapping[str, Any], side: str) -> str | None:
    current = state.get("current_state")
    entries = current.get("ability_context", {}).get("current_abilities") if isinstance(current, Mapping) else None
    match = next((row for row in entries if isinstance(row, Mapping) and row.get("side") == side), None) if isinstance(entries, list) else None
    return match.get("ability") if isinstance(match, Mapping) and match.get("status") == "user_confirmed" and match.get("source") == "user_confirmed_current_ability" and isinstance(match.get("ability"), str) else None


def _toxic_lifecycle(state: Mapping[str, Any], side: str, source_snapshot_fingerprint: Any) -> int | dict[str, str]:
    lifecycle = state.get("predicted_toxic_lifecycle")
    condition = state.get("predicted_condition_context")
    if not isinstance(lifecycle, Mapping) or not isinstance(condition, Mapping):
        return _result("incomplete", f"{side}.toxic_progression")
    if lifecycle.get("schema_version") != "hypothetical-predictive-toxic-lifecycle-v1" or lifecycle.get("provenance") != "turn_engine_predicted_toxic_application" or lifecycle.get("source_snapshot_fingerprint") != condition.get("source_snapshot_fingerprint") or lifecycle.get("owner") != condition.get("owner") or condition.get("condition_type") != "toxic":
        return _result("rejected", "stale_or_mismatched_predicted_toxic_lifecycle")
    stage = lifecycle.get("current_stage")
    if lifecycle.get("owner", {}).get("side") != side or isinstance(stage, bool) or not isinstance(stage, int) or not 1 <= stage <= 15:
        return _result("rejected", "invalid_predicted_toxic_lifecycle")
    return stage


def _active(state: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    value = state.get("active", {}).get(side) if isinstance(state.get("active"), Mapping) else None
    if not isinstance(value, dict) or any(not isinstance(value.get(key), int) or isinstance(value.get(key), bool) for key in ("current_hp", "max_hp")) or not 0 <= value["current_hp"] <= value["max_hp"] or value.get("fainted") is not (value["current_hp"] == 0):
        return None
    return value


def _sync_hp(state: Mapping[str, Any], side: str, hp: int, maximum: int) -> None:
    current = state.get("current_state")
    rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current, Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == side:
                row["current_hp"], row["maximum_hp"] = hp, maximum


def _owner(active: Mapping[str, Any]) -> dict[str, Any]:
    return {key: active[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
