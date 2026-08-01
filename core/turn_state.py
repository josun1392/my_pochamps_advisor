from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


SIDE_VALUES = frozenset({"player", "opponent"})
ITEM_STATUS_VALUES = frozenset({"unknown", "user_confirmed", "inferred", "consumed", "absent"})
STAT_STAGE_MIN = -6
STAT_STAGE_MAX = 6


def _validate_side(value: str | None, *, field_name: str, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if value not in SIDE_VALUES:
        allowed = ", ".join(sorted(SIDE_VALUES))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return value


def _validate_item_status(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in ITEM_STATUS_VALUES:
        allowed = ", ".join(sorted(ITEM_STATUS_VALUES))
        raise ValueError(f"item_status must be one of: {allowed}")
    return value


def _validate_hp_percent(value: int | float | None) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("current_hp_percent must be a number from 0 to 100 or None")
    if value < 0 or value > 100:
        raise ValueError("current_hp_percent must be between 0 and 100")
    return value


def _normalize_stat_stages(value: Mapping[str, int] | None) -> Mapping[str, int]:
    if value is None:
        return MappingProxyType({})
    normalized: dict[str, int] = {}
    for stage_name, stage_value in value.items():
        if not isinstance(stage_name, str) or not stage_name:
            raise ValueError("stat stage keys must be non-empty strings")
        if isinstance(stage_value, bool) or not isinstance(stage_value, int):
            raise ValueError("stat stage values must be integers")
        if stage_value < STAT_STAGE_MIN or stage_value > STAT_STAGE_MAX:
            raise ValueError("stat stage values must be between -6 and 6")
        normalized[stage_name] = stage_value
    return MappingProxyType(normalized)


def _normalize_mapping(value: Mapping[str, Any] | None, *, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return MappingProxyType(dict(value))


def _freeze_value(value: Any, *, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value, field_name=field_name)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item, field_name=field_name) for item in value)
    return value


def _freeze_mapping(value: Mapping[str, Any], *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return MappingProxyType({key: _freeze_value(item, field_name=field_name) for key, item in value.items()})


def _normalize_frozen_mapping(value: Mapping[str, Any] | None, *, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    return _freeze_mapping(value, field_name=field_name)


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _normalize_string_tuple(value: list[str] | tuple[str, ...] | None, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_name} values must be non-empty strings")
        normalized.append(item)
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class PokemonBattleSlot:
    side: str
    slot_index: int | None = None
    species_id: str | None = None
    species_name: str | None = None
    current_hp_percent: int | float | None = None
    known_item_id: str | None = None
    item_status: str | None = None
    item_source: str | None = None
    stat_stages: Mapping[str, int] = field(default_factory=dict)
    major_status: str | None = None
    volatile_conditions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "side", _validate_side(self.side, field_name="side"))
        object.__setattr__(self, "current_hp_percent", _validate_hp_percent(self.current_hp_percent))
        object.__setattr__(self, "item_status", _validate_item_status(self.item_status))
        if self.item_source is not None and (not isinstance(self.item_source, str) or not self.item_source):
            raise ValueError("item_source must be a non-empty string or None")
        object.__setattr__(self, "stat_stages", _normalize_stat_stages(self.stat_stages))
        object.__setattr__(
            self,
            "volatile_conditions",
            _normalize_string_tuple(self.volatile_conditions, field_name="volatile_conditions"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "side": self.side,
            "slot_index": self.slot_index,
            "species_id": self.species_id,
            "species_name": self.species_name,
            "current_hp_percent": self.current_hp_percent,
            "known_item_id": self.known_item_id,
            "item_status": self.item_status,
            "item_source": self.item_source,
            "stat_stages": dict(self.stat_stages),
            "major_status": self.major_status,
            "volatile_conditions": list(self.volatile_conditions),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PokemonBattleSlot":
        return cls(
            side=value["side"],
            slot_index=value.get("slot_index"),
            species_id=value.get("species_id"),
            species_name=value.get("species_name"),
            current_hp_percent=value.get("current_hp_percent"),
            known_item_id=value.get("known_item_id"),
            item_status=value.get("item_status"),
            item_source=value.get("item_source"),
            stat_stages=value.get("stat_stages") or {},
            major_status=value.get("major_status"),
            volatile_conditions=tuple(value.get("volatile_conditions") or ()),
        )


@dataclass(frozen=True, slots=True)
class BattleState:
    active_player: PokemonBattleSlot | None = None
    active_opponent: PokemonBattleSlot | None = None
    weather: str | None = None
    terrain: str | None = None
    field_conditions: Mapping[str, Any] = field(default_factory=dict)
    turn_number: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_conditions", _normalize_mapping(self.field_conditions, field_name="field_conditions"))
        if self.turn_number is not None:
            if isinstance(self.turn_number, bool) or not isinstance(self.turn_number, int) or self.turn_number < 0:
                raise ValueError("turn_number must be a non-negative integer or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_player": self.active_player.to_dict() if self.active_player else None,
            "active_opponent": self.active_opponent.to_dict() if self.active_opponent else None,
            "weather": self.weather,
            "terrain": self.terrain,
            "field_conditions": dict(self.field_conditions),
            "turn_number": self.turn_number,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BattleState":
        active_player = value.get("active_player")
        active_opponent = value.get("active_opponent")
        return cls(
            active_player=PokemonBattleSlot.from_dict(active_player) if active_player else None,
            active_opponent=PokemonBattleSlot.from_dict(active_opponent) if active_opponent else None,
            weather=value.get("weather"),
            terrain=value.get("terrain"),
            field_conditions=value.get("field_conditions") or {},
            turn_number=value.get("turn_number"),
        )


@dataclass(frozen=True, slots=True)
class TurnInput:
    selected_move_id: str | None = None
    acting_side: str | None = None
    target_side: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "acting_side", _validate_side(self.acting_side, field_name="acting_side", allow_none=True))
        object.__setattr__(self, "target_side", _validate_side(self.target_side, field_name="target_side", allow_none=True))

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_move_id": self.selected_move_id,
            "acting_side": self.acting_side,
            "target_side": self.target_side,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TurnInput":
        return cls(
            selected_move_id=value.get("selected_move_id"),
            acting_side=value.get("acting_side"),
            target_side=value.get("target_side"),
        )


@dataclass(frozen=True, slots=True)
class TurnSnapshot:
    battle_state: BattleState = field(default_factory=BattleState)
    turn_input: TurnInput = field(default_factory=TurnInput)
    notes: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)
    current_state: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", _normalize_string_tuple(self.notes, field_name="notes"))
        object.__setattr__(self, "limitations", _normalize_string_tuple(self.limitations, field_name="limitations"))
        object.__setattr__(self, "current_state", _normalize_frozen_mapping(self.current_state, field_name="current_state"))

    def to_dict(self) -> dict[str, Any]:
        value = {
            "battle_state": self.battle_state.to_dict(),
            "turn_input": self.turn_input.to_dict(),
            "notes": list(self.notes),
            "limitations": list(self.limitations),
        }
        if self.current_state:
            value["current_state"] = _thaw_value(self.current_state)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TurnSnapshot":
        return cls(
            battle_state=BattleState.from_dict(value.get("battle_state") or {}),
            turn_input=TurnInput.from_dict(value.get("turn_input") or {}),
            notes=tuple(value.get("notes") or ()),
            limitations=tuple(value.get("limitations") or ()),
            current_state=value.get("current_state") or {},
        )


def normalize_turn_snapshot(value: TurnSnapshot | Mapping[str, Any] | None = None) -> TurnSnapshot:
    if value is None:
        return TurnSnapshot()
    if isinstance(value, TurnSnapshot):
        return value
    if isinstance(value, Mapping):
        return TurnSnapshot.from_dict(value)
    raise ValueError("turn snapshot must be a TurnSnapshot, mapping, or None")
