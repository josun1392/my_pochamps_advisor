"""Priority-first action-order evidence without derived Speed modifiers."""
from __future__ import annotations

from typing import Any, Mapping
from llm.advisor_battle_state_context import calculate_stage_adjusted_stat


# These moves have a priority that depends on state outside this narrow slice.
# Do not silently treat their canonical base priority as the final priority.
_CONDITIONAL_PRIORITY_MOVES = frozenset({"grassy-glide"})
_STAGE_AUTHORITY_NOT_SUPPLIED = object()


def _action(value: Mapping[str, Any] | None, side: str) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, Mapping):
        return None, f"{side}_action"
    move_id, priority = value.get("move_id"), value.get("priority")
    if not isinstance(move_id, str) or not move_id:
        return None, f"{side}_action"
    if move_id in _CONDITIONAL_PRIORITY_MOVES:
        return {"move_id": move_id}, "conditional_priority_mechanic"
    if isinstance(priority, bool) or not isinstance(priority, int) or not -7 <= priority <= 7:
        return {"move_id": move_id}, f"{side}_move_priority"
    return {"move_id": move_id, "priority": priority}, None


def evaluate_action_order(
    *,
    self_action: Mapping[str, Any] | None,
    opponent_action: Mapping[str, Any] | None,
    self_final_speed: Any,
    opponent_final_speed: Any,
    trick_room: str,
    self_speed_stage: Any = _STAGE_AUTHORITY_NOT_SUPPLIED,
    opponent_speed_stage: Any = _STAGE_AUTHORITY_NOT_SUPPLIED,
) -> dict[str, Any]:
    """Resolve a known action pair using only trusted final Speed and field state."""
    self_reference, self_error = _action(self_action, "self")
    opponent_reference, opponent_error = _action(opponent_action, "opponent")
    result: dict[str, Any] = {
        "self_action": self_reference,
        "opponent_action": opponent_reference,
        "trick_room": trick_room if trick_room in {"active", "inactive", "unknown"} else "unknown",
        "authority": "canonical_move_metadata_and_trusted_runtime",
        "status": "insufficient_context",
        "missing_inputs": [],
        "unsupported_reason": None,
    }
    if "conditional_priority_mechanic" in {self_error, opponent_error}:
        result.update(status="unsupported_mechanic", unsupported_reason="conditional_priority_mechanic")
        return result
    missing = [item for item in (self_error, opponent_error) if item]
    if missing:
        result["missing_inputs"] = missing
        return result
    assert self_reference is not None and opponent_reference is not None
    self_priority, opponent_priority = self_reference["priority"], opponent_reference["priority"]
    result.update(
        self_priority=self_priority,
        opponent_priority=opponent_priority,
        priority_comparison="equal" if self_priority == opponent_priority else "self_higher" if self_priority > opponent_priority else "opponent_higher",
    )
    if self_priority != opponent_priority:
        result.update(
            status="acts_first" if self_priority > opponent_priority else "acts_second",
            reason="priority_advantage",
            speed_comparison="not_needed",
        )
        return result
    if result["trick_room"] == "unknown":
        result["missing_inputs"] = ["trick_room"]
        return result
    missing_speeds = [
        name
        for name, value in (("self_final_speed", self_final_speed), ("opponent_final_speed", opponent_final_speed))
        if isinstance(value, bool) or not isinstance(value, int) or value < 1
    ]
    if missing_speeds:
        result["missing_inputs"] = missing_speeds
        return result
    if self_speed_stage is not _STAGE_AUTHORITY_NOT_SUPPLIED or opponent_speed_stage is not _STAGE_AUTHORITY_NOT_SUPPLIED:
        invalid = [value for value in (self_speed_stage, opponent_speed_stage) if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not -6 <= value <= 6)]
        if invalid:
            result.update(status="unsupported_mechanic", unsupported_reason="speed_stage_context")
            return result
        missing_stages = [name for name, value in (("self_speed_stage", self_speed_stage), ("opponent_speed_stage", opponent_speed_stage)) if value is None]
        if missing_stages:
            result["missing_inputs"] = missing_stages
            return result
        self_final_speed = calculate_stage_adjusted_stat(self_final_speed, self_speed_stage)
        opponent_final_speed = calculate_stage_adjusted_stat(opponent_final_speed, opponent_speed_stage)
        result.update(self_speed_stage=self_speed_stage, opponent_speed_stage=opponent_speed_stage, speed_stage_adjustment_applied=True)
    result.update(self_final_speed=self_final_speed, opponent_final_speed=opponent_final_speed)
    if self_final_speed == opponent_final_speed:
        result.update(status="speed_tie", reason="equal_priority_equal_speed", speed_comparison="equal")
        return result
    self_first = self_final_speed < opponent_final_speed if result["trick_room"] == "active" else self_final_speed > opponent_final_speed
    result.update(
        status="acts_first" if self_first else "acts_second",
        reason="speed_advantage",
        speed_comparison="self_higher" if self_final_speed > opponent_final_speed else "opponent_higher",
    )
    return result
