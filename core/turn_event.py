from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


TURN_EVENT_STAGE_VALUES = frozenset(
    {
        "pre_turn",
        "pre_move",
        "damage",
        "on_damage_before_ko",
        "on_hit_or_damage_dealt",
        "post_damage",
        "post_turn",
    }
)
TURN_EVENT_STATUS_VALUES = frozenset({"candidate", "known_modifier", "not_simulated", "blocked", "unavailable"})
TURN_EVENT_CERTAINTY_VALUES = frozenset({"known", "likely", "possible", "unknown", "not_simulated"})
TURN_EVENT_SIDE_VALUES = frozenset({"player", "opponent", "field", "unknown"})
TURN_PIPELINE_SIMULATED_VALUES = frozenset({"none", "limited", "full"})


def _validate_member(value: str, *, field_name: str, allowed_values: frozenset[str]) -> str:
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return value


def _validate_optional_side(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _validate_member(value, field_name=field_name, allowed_values=TURN_EVENT_SIDE_VALUES)


def _normalize_string_tuple(value: list[str] | tuple[str, ...] | None, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_name} values must be non-empty strings")
        normalized.append(item)
    return tuple(normalized)


def _normalize_events(value: list["TurnEvent" | Mapping[str, Any]] | tuple["TurnEvent" | Mapping[str, Any], ...] | None) -> tuple["TurnEvent", ...]:
    if value is None:
        return ()
    normalized: list[TurnEvent] = []
    for item in value:
        if isinstance(item, TurnEvent):
            normalized.append(item)
        elif isinstance(item, Mapping):
            normalized.append(TurnEvent.from_dict(item))
        else:
            raise ValueError("events values must be TurnEvent or mapping instances")
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class TurnEvent:
    stage: str
    status: str
    certainty: str
    source: str | None = None
    subject_side: str | None = None
    target_side: str | None = None
    item_id: str | None = None
    trigger_type: str | None = None
    summary: str | None = None
    limitations: tuple[str, ...] = field(default_factory=tuple)
    payload_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stage",
            _validate_member(self.stage, field_name="stage", allowed_values=TURN_EVENT_STAGE_VALUES),
        )
        object.__setattr__(
            self,
            "status",
            _validate_member(self.status, field_name="status", allowed_values=TURN_EVENT_STATUS_VALUES),
        )
        object.__setattr__(
            self,
            "certainty",
            _validate_member(self.certainty, field_name="certainty", allowed_values=TURN_EVENT_CERTAINTY_VALUES),
        )
        object.__setattr__(self, "subject_side", _validate_optional_side(self.subject_side, field_name="subject_side"))
        object.__setattr__(self, "target_side", _validate_optional_side(self.target_side, field_name="target_side"))
        object.__setattr__(
            self,
            "limitations",
            _normalize_string_tuple(self.limitations, field_name="limitations"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "source": self.source,
            "subject_side": self.subject_side,
            "target_side": self.target_side,
            "item_id": self.item_id,
            "trigger_type": self.trigger_type,
            "status": self.status,
            "certainty": self.certainty,
            "summary": self.summary,
            "limitations": list(self.limitations),
            "payload_key": self.payload_key,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TurnEvent":
        return cls(
            stage=value["stage"],
            source=value.get("source"),
            subject_side=value.get("subject_side"),
            target_side=value.get("target_side"),
            item_id=value.get("item_id"),
            trigger_type=value.get("trigger_type"),
            status=value["status"],
            certainty=value["certainty"],
            summary=value.get("summary"),
            limitations=tuple(value.get("limitations") or ()),
            payload_key=value.get("payload_key"),
        )


@dataclass(frozen=True, slots=True)
class TurnPipelineResult:
    input_snapshot: Mapping[str, Any] | None = None
    selected_move_id: str | None = None
    damage_estimate_ref: str | None = None
    ko_context_ref: str | None = None
    events: tuple[TurnEvent, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)
    simulated: str = "none"

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", _normalize_events(self.events))
        object.__setattr__(self, "warnings", _normalize_string_tuple(self.warnings, field_name="warnings"))
        object.__setattr__(self, "limitations", _normalize_string_tuple(self.limitations, field_name="limitations"))
        object.__setattr__(
            self,
            "simulated",
            _validate_member(self.simulated, field_name="simulated", allowed_values=TURN_PIPELINE_SIMULATED_VALUES),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_snapshot": dict(self.input_snapshot) if self.input_snapshot is not None else None,
            "selected_move_id": self.selected_move_id,
            "damage_estimate_ref": self.damage_estimate_ref,
            "ko_context_ref": self.ko_context_ref,
            "events": [event.to_dict() for event in self.events],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "simulated": self.simulated,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TurnPipelineResult":
        return cls(
            input_snapshot=value.get("input_snapshot"),
            selected_move_id=value.get("selected_move_id"),
            damage_estimate_ref=value.get("damage_estimate_ref"),
            ko_context_ref=value.get("ko_context_ref"),
            events=tuple(value.get("events") or ()),
            warnings=tuple(value.get("warnings") or ()),
            limitations=tuple(value.get("limitations") or ()),
            simulated=value.get("simulated") or "none",
        )


def normalize_turn_event(value: TurnEvent | Mapping[str, Any]) -> TurnEvent:
    if isinstance(value, TurnEvent):
        return value
    if isinstance(value, Mapping):
        return TurnEvent.from_dict(value)
    raise ValueError("turn event must be a TurnEvent or mapping")


def normalize_turn_pipeline_result(value: TurnPipelineResult | Mapping[str, Any] | None = None) -> TurnPipelineResult:
    if value is None:
        return TurnPipelineResult()
    if isinstance(value, TurnPipelineResult):
        return value
    if isinstance(value, Mapping):
        return TurnPipelineResult.from_dict(value)
    raise ValueError("turn pipeline result must be a TurnPipelineResult, mapping, or None")
