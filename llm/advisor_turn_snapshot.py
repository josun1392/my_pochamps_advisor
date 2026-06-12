from __future__ import annotations

from typing import Any, Mapping

from core.turn_state import BattleState, PokemonBattleSlot, TurnInput, TurnSnapshot


def build_turn_snapshot_from_battle_input(battle_input: Mapping[str, Any]) -> TurnSnapshot:
    if not isinstance(battle_input, Mapping):
        raise ValueError("battle_input must be a mapping")

    pokemon = _mapping_or_empty(battle_input.get("pokemon"))
    item_profiles = _mapping_or_empty(battle_input.get("item_profiles"))
    moves = _mapping_or_empty(battle_input.get("moves"))

    active_player = _battle_slot_from_payload(
        side="player",
        pokemon_payload=_mapping_or_empty(pokemon.get("my_active")),
        item_profile=_mapping_or_empty(item_profiles.get("my_active")),
    )
    active_opponent = _battle_slot_from_payload(
        side="opponent",
        pokemon_payload=_mapping_or_empty(pokemon.get("opponent_active")),
        item_profile=_mapping_or_empty(item_profiles.get("opponent_active")),
    )
    selected_move = _mapping_or_empty(moves.get("my_selected_move"))

    return TurnSnapshot(
        battle_state=BattleState(
            active_player=active_player,
            active_opponent=active_opponent,
            weather=None,
            terrain=None,
            field_conditions={},
            turn_number=None,
        ),
        turn_input=TurnInput(
            selected_move_id=_optional_str(selected_move.get("move_id")),
            acting_side="player",
            target_side="opponent",
        ),
        notes=("Built from UI-selected battle_input.",),
        limitations=(
            "No full turn simulation.",
            "No item trigger evaluation.",
            "No item consumption.",
            "No post-damage HP update.",
            "No speed/order simulation.",
        ),
    )


def try_build_turn_snapshot_from_battle_input(battle_input: Mapping[str, Any]) -> TurnSnapshot | None:
    try:
        return build_turn_snapshot_from_battle_input(battle_input)
    except (KeyError, TypeError, ValueError):
        return None


def _battle_slot_from_payload(
    *,
    side: str,
    pokemon_payload: Mapping[str, Any],
    item_profile: Mapping[str, Any],
) -> PokemonBattleSlot:
    item_status, known_item_id = _snapshot_item_state(item_profile)
    return PokemonBattleSlot(
        side=side,
        slot_index=_optional_int(pokemon_payload.get("slot_index")),
        species_id=_optional_str(pokemon_payload.get("name_en")),
        species_name=_optional_str(pokemon_payload.get("name_ko")) or _optional_str(pokemon_payload.get("name_en")),
        current_hp_percent=pokemon_payload.get("hp_percent"),
        known_item_id=known_item_id,
        item_status=item_status,
        stat_stages={},
        major_status=None,
        volatile_conditions=(),
    )


def _snapshot_item_state(item_profile: Mapping[str, Any]) -> tuple[str, str | None]:
    status = _optional_str(item_profile.get("status"))
    item_id = _optional_str(item_profile.get("item_id"))
    if status == "user_confirmed":
        return "user_confirmed", item_id
    if status in {"none", "system_default_none", "absent"}:
        return "absent", None
    if status in {"inferred", "consumed"}:
        return status, item_id if status == "inferred" else None
    return "unknown", None


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("expected mapping value")
    return value


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None
