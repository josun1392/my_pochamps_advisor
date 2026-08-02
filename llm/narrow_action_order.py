"""Priority-first action-order evidence without derived Speed modifiers."""
from __future__ import annotations

from typing import Any, Mapping
from llm.advisor_battle_state_context import calculate_stage_adjusted_stat
from advisor.damage.q12 import Q12_ONE, apply_damage_modifier
from advisor.damage.items import get_item
from advisor.damage.item_modifiers import speed_stat_item_mod
from advisor.damage.abilities import get_ability
from advisor.damage.ability_modifiers import speed_stat_ability_mod
from advisor.damage.status_effects import paralysis_spe_modifier


# These moves have a priority that depends on state outside this narrow slice.
# Do not silently treat their canonical base priority as the final priority.
_CONDITIONAL_PRIORITY_MOVES = frozenset({"grassy-glide"})
_STAGE_AUTHORITY_NOT_SUPPLIED = object()
_TRICK_ROOM_AUTHORITY_NOT_SUPPLIED = object()
_TAILWIND_AUTHORITY_NOT_SUPPLIED = object()
_PARALYSIS_AUTHORITY_NOT_SUPPLIED = object()
_SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED = object()
_SUPPORTED_SPEED_ABILITIES = frozenset({"swift-swim", "chlorophyll", "sand-rush", "slush-rush"})
_UNSUPPORTED_SPEED_ABILITIES = frozenset({"surge-surfer", "unburden", "speed-boost", "slow-start", "protosynthesis", "quark-drive"})
_UNSUPPORTED_SPEED_ITEMS = frozenset({"iron-ball", "macho-brace", "power-anklet", "power-band", "power-belt", "power-bracer", "power-lens", "power-weight", "lagging-tail", "full-incense", "quick-claw", "custap-berry"})


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
    trick_room: Any = _TRICK_ROOM_AUTHORITY_NOT_SUPPLIED,
    trick_room_provenance: str | None = None,
    self_tailwind: Any = _TAILWIND_AUTHORITY_NOT_SUPPLIED,
    opponent_tailwind: Any = _TAILWIND_AUTHORITY_NOT_SUPPLIED,
    self_tailwind_provenance: str | None = None,
    opponent_tailwind_provenance: str | None = None,
    self_paralysis: Any = _PARALYSIS_AUTHORITY_NOT_SUPPLIED,
    opponent_paralysis: Any = _PARALYSIS_AUTHORITY_NOT_SUPPLIED,
    self_paralysis_provenance: str | None = None,
    opponent_paralysis_provenance: str | None = None,
    self_paralysis_speed_ability_unsupported: bool = False,
    opponent_paralysis_speed_ability_unsupported: bool = False,
    self_speed_stage: Any = _STAGE_AUTHORITY_NOT_SUPPLIED,
    opponent_speed_stage: Any = _STAGE_AUTHORITY_NOT_SUPPLIED,
    self_speed_item: Any = _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED,
    opponent_speed_item: Any = _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED,
    self_speed_ability: Any = _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED,
    opponent_speed_ability: Any = _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED,
    weather: Any = _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED,
) -> dict[str, Any]:
    """Resolve a known action pair using only trusted final Speed and field state."""
    self_reference, self_error = _action(self_action, "self")
    opponent_reference, opponent_error = _action(opponent_action, "opponent")
    result: dict[str, Any] = {
        "self_action": self_reference,
        "opponent_action": opponent_reference,
        "trick_room": "inactive" if trick_room is _TRICK_ROOM_AUTHORITY_NOT_SUPPLIED else trick_room if trick_room in {"active", "inactive", "unknown"} else "unknown",
        "trick_room_authority": "omitted" if trick_room is _TRICK_ROOM_AUTHORITY_NOT_SUPPLIED else trick_room_provenance if trick_room_provenance in {"user_confirmed_current", "trusted_observed_current", "unknown"} else "unknown",
        "self_tailwind": "inactive" if self_tailwind is _TAILWIND_AUTHORITY_NOT_SUPPLIED else self_tailwind if self_tailwind in {"active", "inactive", "unknown", "invalid"} else "invalid",
        "opponent_tailwind": "inactive" if opponent_tailwind is _TAILWIND_AUTHORITY_NOT_SUPPLIED else opponent_tailwind if opponent_tailwind in {"active", "inactive", "unknown", "invalid"} else "invalid",
        "self_tailwind_authority": "omitted" if self_tailwind is _TAILWIND_AUTHORITY_NOT_SUPPLIED else self_tailwind_provenance if self_tailwind_provenance in {"user_confirmed_current", "trusted_observed_current", "unknown"} else "unknown",
        "opponent_tailwind_authority": "omitted" if opponent_tailwind is _TAILWIND_AUTHORITY_NOT_SUPPLIED else opponent_tailwind_provenance if opponent_tailwind_provenance in {"user_confirmed_current", "trusted_observed_current", "unknown"} else "unknown",
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
    self_paralysis_state = "not_paralyzed" if self_paralysis is _PARALYSIS_AUTHORITY_NOT_SUPPLIED else self_paralysis if self_paralysis in {"paralyzed", "not_paralyzed", "unknown", "invalid"} else "invalid"
    opponent_paralysis_state = "not_paralyzed" if opponent_paralysis is _PARALYSIS_AUTHORITY_NOT_SUPPLIED else opponent_paralysis if opponent_paralysis in {"paralyzed", "not_paralyzed", "unknown", "invalid"} else "invalid"
    result.update(
        self_paralysis=self_paralysis_state,
        opponent_paralysis=opponent_paralysis_state,
        self_paralysis_authority="omitted" if self_paralysis is _PARALYSIS_AUTHORITY_NOT_SUPPLIED else self_paralysis_provenance if self_paralysis_provenance in {"user_confirmed_current", "trusted_observed_current", "unknown"} else "unknown",
        opponent_paralysis_authority="omitted" if opponent_paralysis is _PARALYSIS_AUTHORITY_NOT_SUPPLIED else opponent_paralysis_provenance if opponent_paralysis_provenance in {"user_confirmed_current", "trusted_observed_current", "unknown"} else "unknown",
    )
    if "invalid" in {self_paralysis_state, opponent_paralysis_state}:
        result.update(status="unsupported_mechanic", unsupported_reason="paralysis_context")
        return result
    missing_paralysis = [name for name, value in (("self_paralysis", self_paralysis_state), ("opponent_paralysis", opponent_paralysis_state)) if value == "unknown"]
    if missing_paralysis:
        result["missing_inputs"] = missing_paralysis
        return result
    if (self_paralysis_state == "paralyzed" and self_paralysis_speed_ability_unsupported) or (opponent_paralysis_state == "paralyzed" and opponent_paralysis_speed_ability_unsupported):
        result.update(status="unsupported_mechanic", unsupported_reason="paralysis_speed_ability")
        return result
    if self_paralysis_state == "paralyzed":
        self_final_speed = (self_final_speed * paralysis_spe_modifier("paralysis", "static")) // Q12_ONE
    if opponent_paralysis_state == "paralyzed":
        opponent_final_speed = (opponent_final_speed * paralysis_spe_modifier("paralysis", "static")) // Q12_ONE
    if "paralyzed" in {self_paralysis_state, opponent_paralysis_state}:
        result["paralysis_speed_adjustment_applied"] = True
    item_states = {"self": "omitted" if self_speed_item is _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED else self_speed_item, "opponent": "omitted" if opponent_speed_item is _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED else opponent_speed_item}
    for side, value in item_states.items():
        if value in {"unknown", None}:
            result["missing_inputs"] = [f"{side}_speed_item"]
            return result
        if not isinstance(value, str) or value == "invalid":
            result.update(status="unsupported_mechanic", unsupported_reason="speed_item_context")
            return result
        if value in _UNSUPPORTED_SPEED_ITEMS:
            result.update(status="unsupported_mechanic", unsupported_reason="speed_item_modifier")
            return result
    ability_states = {"self": "omitted" if self_speed_ability is _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED else self_speed_ability, "opponent": "omitted" if opponent_speed_ability is _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED else opponent_speed_ability}
    weather_state = "omitted" if weather is _SPEED_MODIFIER_AUTHORITY_NOT_SUPPLIED else weather
    if weather_state not in {"omitted", "none", "rain", "sun", "sand", "snow", "unknown"}:
        result.update(status="unsupported_mechanic", unsupported_reason="weather_speed_context")
        return result
    for side, value in ability_states.items():
        if value in _UNSUPPORTED_SPEED_ABILITIES:
            result.update(status="unsupported_mechanic", unsupported_reason="speed_ability_modifier")
            return result
        if value == "invalid":
            result.update(status="unsupported_mechanic", unsupported_reason="speed_ability_context")
            return result
        if value in {"unknown", None} and weather_state not in {"omitted", "none"}:
            result["missing_inputs"] = [f"{side}_speed_ability"]
            return result
    if weather_state == "unknown" and any(value in _SUPPORTED_SPEED_ABILITIES for value in ability_states.values()):
        result["missing_inputs"] = ["weather"]
        return result
    for side, item_id in item_states.items():
        if item_id == "choice-scarf":
            modifier = speed_stat_item_mod(get_item(item_id), "")
            if side == "self": self_final_speed = apply_damage_modifier(self_final_speed, modifier)
            else: opponent_final_speed = apply_damage_modifier(opponent_final_speed, modifier)
            result[f"{side}_speed_item_applied"] = "choice-scarf"
    for side, ability_id in ability_states.items():
        if ability_id in _SUPPORTED_SPEED_ABILITIES and weather_state not in {"omitted", "unknown", "none"}:
            modifier = speed_stat_ability_mod(get_ability(ability_id), weather_state, False, "none")
            if modifier != Q12_ONE:
                if side == "self": self_final_speed = apply_damage_modifier(self_final_speed, modifier)
                else: opponent_final_speed = apply_damage_modifier(opponent_final_speed, modifier)
                result[f"{side}_speed_ability_applied"] = ability_id
    if weather_state not in {"omitted", "unknown"}:
        result["weather_basis"] = weather_state
    if "invalid" in {result["self_tailwind"], result["opponent_tailwind"]}:
        result.update(status="unsupported_mechanic", unsupported_reason="tailwind_context")
        return result
    missing_tailwind = [name for name, value in (("self_tailwind", result["self_tailwind"]), ("opponent_tailwind", result["opponent_tailwind"])) if value == "unknown"]
    if missing_tailwind:
        result["missing_inputs"] = missing_tailwind
        return result
    if result["self_tailwind"] == "active":
        self_final_speed *= 2
    if result["opponent_tailwind"] == "active":
        opponent_final_speed *= 2
    if "active" in {result["self_tailwind"], result["opponent_tailwind"]}:
        result["tailwind_adjustment_applied"] = True
    if result["trick_room"] == "unknown":
        result["missing_inputs"] = ["trick_room"]
        return result
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
