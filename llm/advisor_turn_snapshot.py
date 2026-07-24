from __future__ import annotations

from collections.abc import Sequence
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


def build_request_start_recommendation_snapshot(
    battle_input: Mapping[str, Any], *, selectable_moves: Sequence[str | None]
) -> TurnSnapshot:
    """Freeze and validate the trusted UI state used by one structured request.

    The result deliberately contains no request token, widget, repository, or
    provider object.  If the UI exposes its active selectable slots, every
    non-empty candidate must still belong to that active player at capture time.
    """
    snapshot = build_turn_snapshot_from_battle_input(battle_input)
    player = snapshot.battle_state.active_player
    opponent = snapshot.battle_state.active_opponent
    if player is None or not player.species_id or opponent is None or not opponent.species_id:
        raise ValueError("missing_selected_pokemon")
    _validate_selectable_move_ownership(battle_input, selectable_moves)
    return snapshot


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


def _validate_selectable_move_ownership(
    battle_input: Mapping[str, Any], selectable_moves: Sequence[str | None]
) -> None:
    moves = _mapping_or_empty(battle_input.get("moves"))
    available = moves.get("my_available_moves")
    if available is None:
        return
    if not isinstance(available, list):
        raise ValueError("invalid_active_selectable_moves")
    active_slots: dict[int, str] = {}
    for entry in available:
        if not isinstance(entry, Mapping):
            raise ValueError("invalid_active_selectable_moves")
        index, move_id = entry.get("slot_index"), _optional_str(entry.get("move_id"))
        if isinstance(index, bool) or not isinstance(index, int) or move_id is None or index in active_slots:
            raise ValueError("invalid_active_selectable_moves")
        active_slots[index] = move_id
    for index, move_id in enumerate(selectable_moves):
        if move_id is not None and active_slots.get(index) != move_id:
            raise ValueError("selected_move_not_owned_by_active_pokemon")
