from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from core.turn_state import BattleState, PokemonBattleSlot, TurnInput, TurnSnapshot


RICH_CURRENT_STATE_KEYS = (
    "current_hp_context", "condition_context", "ability_context", "stat_stage_context",
    "field_state_context", "item_event_context", "final_stat_context",
    "battle_format_context", "observed_previous_damage_context", "battle_counter_context",
    "consecutive_use_context", "weight_context", "turn_event_context",
)
FIELD_SCOPED_CONTEXT_KEYS = frozenset({"field_state_context", "battle_format_context"})
PROVENANCE_REQUIRED_KEYS = frozenset({"side", "slot_index", "pokemon_id", "session_id", "source", "trust"})


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
        current_state=_extract_current_state(battle_input),
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


def snapshot_deterministic_context(turn_snapshot: TurnSnapshot) -> dict[str, Any]:
    """Return a detached deterministic-input mapping from one frozen snapshot."""
    if not isinstance(turn_snapshot, TurnSnapshot):
        raise ValueError("invalid_turn_snapshot")
    return turn_snapshot.to_dict().get("current_state", {})


def capture_ui_current_state_provenance(battle_input: Mapping[str, Any], *, session_id: str) -> dict[str, Any]:
    """Attach canonical provenance at the UI capture boundary, never in snapshot validation."""
    captured = dict(battle_input)
    provenance_added = False
    pokemon = _mapping_or_empty(captured.get("pokemon"))
    for key in RICH_CURRENT_STATE_KEYS:
        context = captured.get(key)
        if not isinstance(context, Mapping):
            continue
        copied = dict(context)
        for entries in copied.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("side") not in {"self", "opponent"}:
                    continue
                side = entry["side"]; active = _mapping_or_empty(pokemon.get("my_active" if side == "self" else "opponent_active"))
                if not _optional_str(active.get("name_en")) or _optional_int(active.get("slot_index")) is None:
                    continue
                entry["slot_index"] = _optional_int(active.get("slot_index"))
                entry["provenance"] = {"side": side, "slot_index": entry["slot_index"], "pokemon_id": active["name_en"], "session_id": session_id, "source": entry.get("source", "ui_current_state"), "trust": "user_confirmed_current"}
                provenance_added = True
        captured[key] = copied
    if provenance_added:
        captured["current_state_session_id"] = session_id
    return captured


def _extract_current_state(battle_input: Mapping[str, Any]) -> dict[str, Any]:
    current_state: dict[str, Any] = {}
    pokemon = _mapping_or_empty(battle_input.get("pokemon"))
    active_slots = {
        "self": _optional_int(_mapping_or_empty(pokemon.get("my_active")).get("slot_index")),
        "opponent": _optional_int(_mapping_or_empty(pokemon.get("opponent_active")).get("slot_index")),
    }
    session_id = _optional_str(battle_input.get("current_state_session_id"))
    for key in RICH_CURRENT_STATE_KEYS:
        value = battle_input.get(key)
        if isinstance(value, Mapping):
            normalized = _normalize_context_provenance(
                key, value, active_slots=active_slots, pokemon=pokemon, session_id=session_id
            )
            if normalized is not None:
                current_state[key] = normalized
    return current_state


def _validate_current_state_ownership(
    value: Mapping[str, Any], *, active_slots: Mapping[str, int | None], session_id: str | None
) -> None:
    """Reject explicit side, active-slot, or session labels that do not match capture."""
    side = value.get("side")
    if side is not None and side not in {"self", "opponent"}:
        raise ValueError("invalid_current_state_ownership")
    if side in active_slots and "slot_index" in value and value.get("slot_index") != active_slots[side]:
        raise ValueError("invalid_current_state_ownership")
    if "session_id" in value and (session_id is None or value.get("session_id") != session_id):
        raise ValueError("invalid_current_state_ownership")
    for key, item in value.items():
        if isinstance(item, Mapping):
            _validate_current_state_ownership(item, active_slots=active_slots, session_id=session_id)
        elif isinstance(item, list):
            for entry in item:
                if isinstance(entry, Mapping):
                    _validate_current_state_ownership(entry, active_slots=active_slots, session_id=session_id)


def _normalize_context_provenance(
    context_key: str, value: Mapping[str, Any], *, active_slots: Mapping[str, int | None],
    pokemon: Mapping[str, Any], session_id: str | None,
) -> dict[str, Any] | None:
    """Keep field state directly; never auto-attach unproven scoped legacy facts."""
    if context_key in FIELD_SCOPED_CONTEXT_KEYS:
        _validate_current_state_ownership(value, active_slots=active_slots, session_id=session_id)
        return dict(value)
    normalized = _filter_provenanced_entries(
        value, active_slots=active_slots, pokemon=pokemon, session_id=session_id
    )
    return normalized if _contains_provenanced_entry(normalized) else None


def _filter_provenanced_entries(
    value: Mapping[str, Any], *, active_slots: Mapping[str, int | None], pokemon: Mapping[str, Any], session_id: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, list):
            entries = []
            for entry in item:
                if isinstance(entry, Mapping) and _entry_has_valid_provenance(entry, active_slots=active_slots, pokemon=pokemon, session_id=session_id):
                    entries.append(dict(entry))
            result[key] = entries
        else:
            result[key] = item
    return result


def _contains_provenanced_entry(value: Mapping[str, Any]) -> bool:
    return any(isinstance(item, list) and bool(item) for item in value.values())


def _entry_has_valid_provenance(
    entry: Mapping[str, Any], *, active_slots: Mapping[str, int | None], pokemon: Mapping[str, Any], session_id: str | None,
) -> bool:
    provenance = entry.get("provenance")
    if not isinstance(provenance, Mapping) or not PROVENANCE_REQUIRED_KEYS <= set(provenance):
        return False
    side = provenance.get("side")
    if side not in {"self", "opponent"} or provenance.get("slot_index") != active_slots[side]:
        return False
    active_key = "my_active" if side == "self" else "opponent_active"
    if provenance.get("pokemon_id") != _optional_str(_mapping_or_empty(pokemon.get(active_key)).get("name_en")):
        return False
    if session_id is None or provenance.get("session_id") != session_id:
        return False
    if not isinstance(provenance.get("source"), str) or not isinstance(provenance.get("trust"), str):
        return False
    return True
