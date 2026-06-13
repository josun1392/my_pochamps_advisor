from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.turn_event import TurnEvent, TurnPipelineResult


_TURN_PIPELINE_LIMITATIONS = (
    "This result is a limited planning summary, not a full turn simulation.",
    "Item consumption is not simulated.",
    "HP updates and exact post-turn state are not simulated.",
)


_MOVE_CONTEXT_KEYS = (
    "species_stat_item_context",
    "speed_order_context",
    "survival_context",
    "chilan_berry_context",
)


def build_turn_events_from_advice_payload(payload: Mapping[str, Any]) -> tuple[TurnEvent, ...]:
    """Build planning-only TurnEvent candidates from existing advisor context dicts."""
    events: list[TurnEvent] = []

    events.extend(_events_from_move_payload(payload, payload_prefix=""))

    moves = payload.get("moves")
    if isinstance(moves, Mapping):
        selected_move = moves.get("my_selected_move")
        if isinstance(selected_move, Mapping):
            events.extend(_events_from_move_payload(selected_move, payload_prefix="moves.my_selected_move."))

        available_moves = moves.get("my_available_moves")
        if isinstance(available_moves, list):
            for index, move in enumerate(available_moves):
                if isinstance(move, Mapping):
                    events.extend(
                        _events_from_move_payload(move, payload_prefix=f"moves.my_available_moves[{index}].")
                    )

    return tuple(events)


def build_turn_pipeline_result_from_advice_payload(
    payload: Mapping[str, Any],
    *,
    selected_move_id: str | None = None,
    input_snapshot: Mapping[str, Any] | None = None,
    damage_estimate_ref: str | None = None,
    ko_context_ref: str | None = None,
    simulated: str = "limited",
) -> TurnPipelineResult:
    """Bundle mapper events into a fixture/debug TurnPipelineResult."""
    return TurnPipelineResult(
        input_snapshot=input_snapshot,
        selected_move_id=selected_move_id,
        damage_estimate_ref=damage_estimate_ref,
        ko_context_ref=ko_context_ref,
        events=build_turn_events_from_advice_payload(payload),
        warnings=("Unavailable, blocked, deferred, unknown, or malformed contexts do not create events.",),
        limitations=_TURN_PIPELINE_LIMITATIONS,
        simulated=simulated,
    )


def build_optional_turn_pipeline_for_advice_payload(
    payload: Mapping[str, Any],
    *,
    enable_turn_pipeline: bool = False,
    selected_move_id: str | None = None,
    input_snapshot: Mapping[str, Any] | None = None,
    damage_estimate_ref: str | None = None,
    ko_context_ref: str | None = None,
) -> TurnPipelineResult | None:
    """Build a limited TurnPipelineResult only when explicitly enabled."""
    if not enable_turn_pipeline:
        return None
    return build_turn_pipeline_result_from_advice_payload(
        payload,
        selected_move_id=selected_move_id,
        input_snapshot=input_snapshot,
        damage_estimate_ref=damage_estimate_ref,
        ko_context_ref=ko_context_ref,
        simulated="limited",
    )


def _events_from_move_payload(move_payload: Mapping[str, Any], *, payload_prefix: str) -> tuple[TurnEvent, ...]:
    events: list[TurnEvent] = []
    for context_key in _MOVE_CONTEXT_KEYS:
        context = move_payload.get(context_key)
        if not isinstance(context, Mapping) or context.get("available") is not True:
            continue
        event = _event_from_context(context_key, context, payload_prefix=f"{payload_prefix}{context_key}")
        if event is not None:
            events.append(event)
    return tuple(events)


def _event_from_context(context_key: str, context: Mapping[str, Any], *, payload_prefix: str) -> TurnEvent | None:
    if _context_has_blocked_item_status(context):
        return None
    if context_key == "species_stat_item_context":
        return _light_ball_event(context, payload_key=payload_prefix)
    if context_key == "speed_order_context":
        return _quick_claw_event(context, payload_key=payload_prefix)
    if context_key == "survival_context":
        return _survival_event(context, payload_key=payload_prefix)
    if context_key == "chilan_berry_context":
        return _chilan_berry_event(context, payload_key=payload_prefix)
    return None


def _light_ball_event(context: Mapping[str, Any], *, payload_key: str) -> TurnEvent | None:
    if _context_item_id(context) != "light-ball":
        return None
    return TurnEvent(
        stage="damage",
        source="item_context",
        subject_side=_side_from_context(context, "attacker_side"),
        target_side=None,
        item_id="light-ball",
        trigger_type="species_stat_modifier",
        status="known_modifier",
        certainty="known",
        summary="Light Ball is represented as a known Pikachu damage modifier in the advisor estimate.",
        limitations=("This event does not simulate item consumption or a full turn.",),
        payload_key=payload_key,
    )


def _quick_claw_event(context: Mapping[str, Any], *, payload_key: str) -> TurnEvent | None:
    if _context_item_id(context) != "quick-claw":
        return None
    return TurnEvent(
        stage="pre_move",
        source="item_context",
        subject_side=_side_from_context(context, "attacker_side"),
        target_side=None,
        item_id="quick-claw",
        trigger_type="priority_or_move_order_chance",
        status="candidate",
        certainty="possible",
        summary="Quick Claw may affect move order, but activation is not resolved by the Turn Engine yet.",
        limitations=("Activation probability and final move order are not resolved.",),
        payload_key=payload_key,
    )


def _survival_event(context: Mapping[str, Any], *, payload_key: str) -> TurnEvent | None:
    item_id = _context_item_id(context)
    if item_id not in {"focus-band", "focus-sash"}:
        return None
    return TurnEvent(
        stage="on_damage_before_ko",
        source="item_context",
        subject_side=_side_from_context(context, "defender_side"),
        target_side=None,
        item_id=item_id,
        trigger_type="survival_before_ko",
        status="candidate",
        certainty="possible",
        summary=f"{_item_label(item_id)} may affect survival before KO, but the trigger result is not simulated.",
        limitations=("Item consumption, multi-hit handling, chip damage, and exact turn sequencing are not simulated.",),
        payload_key=payload_key,
    )


def _chilan_berry_event(context: Mapping[str, Any], *, payload_key: str) -> TurnEvent | None:
    if _context_item_id(context) != "chilan-berry":
        return None
    return TurnEvent(
        stage="on_damage_before_ko",
        source="item_context",
        subject_side=_side_from_context(context, "defender_side"),
        target_side=None,
        item_id="chilan-berry",
        trigger_type="normal_type_damage_reduction",
        status="candidate",
        certainty="possible",
        summary="Chilan Berry can reduce Normal-type damage, but consumption and the precise trigger outcome are not simulated.",
        limitations=("Raw damage rolls and ko_context remain separate from this planning event.",),
        payload_key=payload_key,
    )


def _context_item_id(context: Mapping[str, Any]) -> str | None:
    item = context.get("item")
    if isinstance(item, Mapping):
        item_id = _normalized_item_id(item.get("item_id"))
        if item_id is not None:
            return item_id
        item_name = item.get("item_name") or item.get("name")
        return _normalized_item_id(item_name)
    item_id = _normalized_item_id(context.get("item_id"))
    if item_id is not None:
        return item_id
    return _normalized_item_id(context.get("item_name"))


def _context_has_blocked_item_status(context: Mapping[str, Any]) -> bool:
    status_values: list[Any] = [context.get("status"), context.get("item_status")]
    item = context.get("item")
    if isinstance(item, Mapping):
        status_values.extend((item.get("status"), item.get("item_status")))
    return any(_normalized_item_id(value) in {"unavailable", "blocked", "deferred"} for value in status_values)


def _normalized_item_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _side_from_context(context: Mapping[str, Any], key: str) -> str:
    value = context.get(key)
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower()
    if normalized in {"player", "my_active", "attacker"}:
        return "player"
    if normalized in {"opponent", "opponent_active", "defender"}:
        return "opponent"
    return "unknown"


def _item_label(item_id: str) -> str:
    return " ".join(part.capitalize() for part in item_id.split("-"))
