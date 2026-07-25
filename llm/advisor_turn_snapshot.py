from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from typing import Any, Mapping

from core.turn_state import BattleState, PokemonBattleSlot, TurnInput, TurnSnapshot
from llm.advisor_battle_state_context import (
    normalize_user_confirmed_current_ability,
    normalize_user_confirmed_final_battle_stat,
)


RICH_CURRENT_STATE_KEYS = (
    "current_hp_context", "condition_context", "ability_context", "stat_stage_context",
    "field_state_context", "item_event_context", "final_stat_context",
    "battle_format_context", "observed_previous_damage_context", "battle_counter_context",
    "consecutive_use_context", "weight_context", "turn_event_context", "trusted_level_context",
    "observed_damage_context",
)
FIELD_SCOPED_CONTEXT_KEYS = frozenset({"field_state_context", "battle_format_context"})
PROVENANCE_REQUIRED_KEYS = frozenset({"side", "slot_index", "pokemon_id", "session_id", "source", "trust"})
BASE_STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


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


def build_snapshot_deterministic_input(turn_snapshot: TurnSnapshot) -> dict[str, Any]:
    """Detached deterministic input keyed only by the frozen request snapshot."""
    if not isinstance(turn_snapshot, TurnSnapshot):
        raise ValueError("invalid_turn_snapshot")
    serialized = turn_snapshot.to_dict()
    return {
        "pokemon": serialized["battle_state"],
        "selected_move_id": serialized["turn_input"]["selected_move_id"],
        "current_state": serialized.get("current_state", {}),
    }


def build_snapshot_damage_input(
    turn_snapshot: TurnSnapshot, *, candidate_slot_index: int,
    candidate_move_id: str, selectable_moves: Sequence[str | None],
    move_metadata: Mapping[str, Any], species_repository: Any = None,
) -> dict[str, Any]:
    """Build the detached input signature used at the candidate/damage boundary.

    This adapter deliberately does not calculate damage or invent final stats.
    It binds the candidate identity and metadata to the frozen request snapshot,
    then preserves supported current-state evidence for existing calculators.
    """
    if not isinstance(turn_snapshot, TurnSnapshot):
        raise ValueError("invalid_turn_snapshot")
    if isinstance(candidate_slot_index, bool) or not isinstance(candidate_slot_index, int):
        raise ValueError("invalid_candidate_slot")
    if not isinstance(candidate_move_id, str) or not candidate_move_id:
        raise ValueError("invalid_candidate_move")
    if candidate_slot_index < 0 or candidate_slot_index >= len(selectable_moves):
        raise ValueError("candidate_not_owned_by_snapshot")
    if selectable_moves[candidate_slot_index] != candidate_move_id:
        raise ValueError("candidate_not_owned_by_snapshot")
    if not isinstance(move_metadata, Mapping):
        raise ValueError("invalid_move_metadata")
    metadata_move_id = _optional_str(move_metadata.get("move_id"))
    if metadata_move_id not in {None, candidate_move_id}:
        raise ValueError("move_metadata_identity_mismatch")

    serialized = turn_snapshot.to_dict()
    battle_state = serialized["battle_state"]
    attacker = battle_state.get("active_player")
    defender = battle_state.get("active_opponent")
    if not isinstance(attacker, Mapping) or not isinstance(defender, Mapping):
        raise ValueError("missing_selected_pokemon")
    if not _optional_str(attacker.get("species_id")) or not _optional_str(defender.get("species_id")):
        raise ValueError("missing_selected_pokemon")
    current_state = deepcopy(serialized.get("current_state", {}))
    session_id = _current_state_session_id(current_state)
    move = deepcopy(dict(move_metadata))
    move["move_id"] = candidate_move_id
    move["slot_index"] = candidate_slot_index
    move["owner_species_id"] = attacker["species_id"]
    observed_events = _observed_event_evidence(current_state)
    limits = [
        "Exact final stats are unavailable unless explicitly user-confirmed.",
        "EV, IV, nature, and hidden ability/item values are not inferred.",
        "Observed events are evidence only and are not automatic damage modifiers.",
    ]
    if not current_state.get("final_stat_context"):
        limits.append("Exact damage guarantee unavailable without trusted final-stat context.")
    result = {
        "attacker": {**deepcopy(dict(attacker)), "session_id": session_id},
        "defender": {**deepcopy(dict(defender)), "session_id": session_id},
        "move": move,
        "battle_context": {
            "current_state": current_state,
            "observed_event_evidence": observed_events,
        },
        "calculation_limits": limits,
    }
    if species_repository is not None:
        result["battle_context"]["stat_provenance"] = build_snapshot_stat_provenance(
            turn_snapshot, species_repository=species_repository
        )
    return result


def build_snapshot_stat_provenance(
    turn_snapshot: TurnSnapshot, *, species_repository: Any,
) -> dict[str, Any]:
    """Detach repository species facts without promoting them to final stats."""
    if not isinstance(turn_snapshot, TurnSnapshot):
        raise ValueError("invalid_turn_snapshot")
    serialized = turn_snapshot.to_dict()
    current_state = serialized.get("current_state", {})
    session_id = _current_state_session_id(current_state)
    result = {
        "attacker": _snapshot_side_stat_provenance(
            serialized["battle_state"].get("active_player"), "self", current_state,
            session_id, species_repository,
        ),
        "defender": _snapshot_side_stat_provenance(
            serialized["battle_state"].get("active_opponent"), "opponent", current_state,
            session_id, species_repository,
        ),
        "limits": [
            "Repository base stats are not exact final stats.",
            "EV, IV, nature, level, and hidden modifiers are not inferred.",
            "Stat stages are separate from final-stat availability.",
        ],
    }
    return result


def build_q12_input_adapter(
    damage_input: Mapping[str, Any], *, stat_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a detached Q12-ready signature without invoking its formula."""
    if not isinstance(damage_input, Mapping) or not isinstance(stat_provenance, Mapping):
        raise ValueError("invalid_damage_input")
    attacker = stat_provenance.get("attacker")
    defender = stat_provenance.get("defender")
    if not isinstance(attacker, Mapping) or not isinstance(defender, Mapping):
        raise ValueError("invalid_stat_provenance")
    required = (attacker, defender)
    if any(not _available_block(side.get("types")) for side in required):
        return {"status": "unavailable", "reason": "missing_type_metadata"}
    if any(not _available_block(side.get("base_stats")) for side in required):
        return {"status": "unavailable", "reason": "missing_base_stat_metadata"}
    if any(not _available_block(side.get("final_stats")) for side in required):
        return {"status": "unavailable", "reason": "final_stats_unavailable"}
    return {
        "status": "ready_for_existing_q12_boundary",
        "attacker": deepcopy(dict(attacker)),
        "defender": deepcopy(dict(defender)),
        "move": deepcopy(dict(damage_input.get("move", {}))),
        "limits": deepcopy(list(stat_provenance.get("limits", []))),
    }


def build_snapshot_trusted_level_provenance(turn_snapshot: TurnSnapshot) -> dict[str, Any]:
    """Return only an already-captured, active-self trusted level.

    Level has no UI producer in v15.13.  This boundary therefore never derives
    one from stat profiles, species metadata, or a conventional default.
    """
    if not isinstance(turn_snapshot, TurnSnapshot):
        raise ValueError("invalid_turn_snapshot")
    serialized = turn_snapshot.to_dict()
    current_state = serialized.get("current_state", {})
    context = current_state.get("trusted_level_context") if isinstance(current_state, Mapping) else None
    entries = context.get("current_levels") if isinstance(context, Mapping) else None
    attacker = serialized["battle_state"].get("active_player")
    if not isinstance(attacker, Mapping):
        return _unavailable_level("missing_selected_pokemon")
    if not isinstance(entries, list):
        return _unavailable_level("trusted_level_unavailable")
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("side") != "self":
            continue
        provenance = entry.get("provenance")
        if not isinstance(provenance, Mapping):
            continue
        source, trust = provenance.get("source"), provenance.get("trust")
        if (source, trust) not in {
            ("user_confirmed_current_level", "user_confirmed_current"),
            ("deterministic_rules_metadata", "deterministic_rules_metadata"),
        }:
            continue
        value = entry.get("value")
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
            continue
        if (
            provenance.get("slot_index") != attacker.get("slot_index")
            or provenance.get("pokemon_id") != attacker.get("species_id")
            or provenance.get("side") != "self"
        ):
            continue
        return {
            "available": True, "value": value, "side": "self",
            "slot_index": attacker.get("slot_index"), "pokemon_id": attacker.get("species_id"),
            "session_id": provenance.get("session_id"), "source": source, "trust": trust,
            "reason": None,
        }
    return _unavailable_level("trusted_level_unavailable")


def _unavailable_level(reason: str) -> dict[str, Any]:
    return {
        "available": False, "value": None, "side": "self", "slot_index": None,
        "pokemon_id": None, "session_id": None, "source": "unknown", "trust": "unknown",
        "reason": reason,
    }


def _snapshot_side_stat_provenance(
    slot: Any, side: str, current_state: Mapping[str, Any], session_id: str | None,
    species_repository: Any,
) -> dict[str, Any]:
    if not isinstance(slot, Mapping) or not _optional_str(slot.get("species_id")):
        raise ValueError("missing_selected_pokemon")
    species_id = slot["species_id"]
    metadata = _lookup_species_metadata(species_repository, species_id)
    types = _metadata_sequence(metadata, "types_en", "types")
    base_stats = _metadata_base_stats(metadata)
    if _metadata_identity(metadata) not in {None, species_id}:
        raise ValueError("species_metadata_identity_mismatch")
    final_values = _provenanced_stats(current_state.get("final_stat_context"), "current_final_stats", side)
    stage_values = _provenanced_stats(current_state.get("stat_stage_context"), "current_stages", side, value_key="stage")
    item_id = _optional_str(slot.get("known_item_id")) if slot.get("item_status") == "user_confirmed" else None
    ability_id = _provenanced_ability(current_state.get("ability_context"), side)
    return {
        "pokemon_identity": species_id,
        "side": side,
        "slot_index": slot.get("slot_index"),
        "session_id": session_id,
        "types": _provenance_block(types, source="repository_metadata", trust="deterministic_metadata", reason="missing_type_metadata"),
        "base_stats": _provenance_block(base_stats, source="repository_metadata", trust="deterministic_metadata", reason="missing_base_stat_metadata"),
        "final_stats": _provenance_block(final_values if len(final_values) == len(BASE_STAT_KEYS) else None, source="user_confirmed_final_stat", trust="user_confirmed_current", reason="final_stats_unavailable"),
        "stat_stages": _provenance_block(stage_values or None, source="user_confirmed_current_stat_stage", trust="user_confirmed_current", reason="stat_stages_unavailable"),
        "known_ability": _provenance_block(ability_id, source="user_confirmed_current_ability" if ability_id else "unknown", trust="user_confirmed_current" if ability_id else "unknown", reason="ability_unknown"),
        "known_item": _provenance_block(item_id, source="user_confirmed_current" if item_id else "unknown", trust="user_confirmed_current" if item_id else "unknown", reason="item_unknown"),
    }


def _lookup_species_metadata(repository: Any, species_id: str) -> Any:
    try:
        return repository.get(species_id) if hasattr(repository, "get") else repository[species_id]
    except Exception:
        return None


def _metadata_value(metadata: Any, *names: str) -> Any:
    for name in names:
        value = metadata.get(name) if isinstance(metadata, Mapping) else getattr(metadata, name, None)
        if value is not None:
            return value
    return None


def _metadata_identity(metadata: Any) -> str | None:
    return _optional_str(_metadata_value(metadata, "en", "name_en", "species_id"))


def _metadata_sequence(metadata: Any, *names: str) -> list[str] | None:
    value = _metadata_value(metadata, *names)
    if not isinstance(value, (list, tuple)):
        return None
    values = [item for item in value if isinstance(item, str) and item]
    return values or None


def _metadata_base_stats(metadata: Any) -> dict[str, int] | None:
    value = _metadata_value(metadata, "base_stats")
    if not isinstance(value, Mapping):
        return None
    result = {key: value.get(key) for key in BASE_STAT_KEYS}
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in result.values()):
        return None
    return deepcopy(result)


def _provenanced_stats(context: Any, entry_key: str, side: str, *, value_key: str = "value") -> dict[str, int]:
    entries = context.get(entry_key) if isinstance(context, Mapping) else None
    result: dict[str, int] = {}
    if not isinstance(entries, list):
        return result
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("side") != side:
            continue
        provenance = entry.get("provenance")
        if not isinstance(provenance, Mapping) or provenance.get("side") != side:
            continue
        stat = _optional_str(entry.get("stat"))
        value = entry.get(value_key)
        if stat in BASE_STAT_KEYS and isinstance(value, int) and not isinstance(value, bool):
            result[stat] = value
    return result


def _provenanced_ability(context: Any, side: str) -> str | None:
    entries = context.get("current_abilities") if isinstance(context, Mapping) else None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("side") != side:
            continue
        try:
            normalized = normalize_user_confirmed_current_ability(
                {key: value for key, value in entry.items() if key not in {"confidence", "provenance"}}
            )
        except ValueError:
            continue
        if normalized["ability"] == "unknown":
            continue
        return normalized["ability"]
    return None


def _provenance_block(value: Any, *, source: str, trust: str, reason: str) -> dict[str, Any]:
    return {
        "available": value is not None,
        "value": deepcopy(value) if value is not None else None,
        "source": source,
        "trust": trust,
        "reason": None if value is not None else reason,
    }


def _available_block(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("available") is True


def _current_state_session_id(current_state: Mapping[str, Any]) -> str | None:
    for context in current_state.values():
        if not isinstance(context, Mapping):
            continue
        for entries in context.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, Mapping):
                    continue
                provenance = entry.get("provenance")
                if isinstance(provenance, Mapping):
                    session_id = _optional_str(provenance.get("session_id"))
                    if session_id is not None:
                        return session_id
    return None


def _observed_event_evidence(current_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    context = current_state.get("item_event_context")
    events = context.get("observed_events") if isinstance(context, Mapping) else None
    return deepcopy([dict(event) for event in events if isinstance(event, Mapping)]) if isinstance(events, list) else []


def capture_ui_current_state_provenance(
    battle_input: Mapping[str, Any], *, session_id: str,
    observed_events: Sequence[Mapping[str, Any]] | None = None,
    final_stat_confirmations: Sequence[Mapping[str, Any]] | None = None,
    ability_confirmations: Sequence[Mapping[str, Any]] | None = None,
    observed_damage_confirmations: Sequence[Mapping[str, Any]] | None = None,
    used_move_confirmations: Sequence[Mapping[str, Any]] | None = None,
    hp_transition_confirmations: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Capture structured-only provenance and explicitly observed UI events.

    The caller may pass a legacy-compatible base input, but this function always
    returns a detached copy.  It is intentionally invoked only after the
    structured request boundary, so neither legacy prompts nor the UI session
    dictionaries acquire internal provenance or event metadata.
    """
    captured = deepcopy(dict(battle_input))
    provenance_added = False
    pokemon = _mapping_or_empty(captured.get("pokemon"))
    for key in RICH_CURRENT_STATE_KEYS:
        if key == "trusted_level_context":
            continue
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
    canonical_events = normalize_observed_events(
        observed_events, pokemon=pokemon, session_id=session_id
    )
    if canonical_events:
        event_context = captured.get("item_event_context")
        event_context = dict(event_context) if isinstance(event_context, Mapping) else {}
        event_context["observed_events"] = canonical_events
        captured["item_event_context"] = event_context
        provenance_added = True
    final_stats = normalize_structured_final_stat_confirmations(
        final_stat_confirmations, pokemon=pokemon, session_id=session_id
    )
    if final_stats:
        captured["final_stat_context"] = {"current_final_stats": final_stats}
        provenance_added = True
    abilities = normalize_structured_ability_confirmations(
        ability_confirmations, pokemon=pokemon, session_id=session_id,
    )
    if abilities:
        captured["ability_context"] = {"current_abilities": abilities}
        provenance_added = True
    observed_damage = normalize_structured_observed_damage_confirmations(
        observed_damage_confirmations, pokemon=pokemon, session_id=session_id,
        moves=_mapping_or_empty(captured.get("moves")),
        used_move_confirmations=used_move_confirmations,
        hp_transition_confirmations=hp_transition_confirmations,
    )
    if observed_damage:
        captured["observed_damage_context"] = {"observed_damage_events": observed_damage}
        provenance_added = True
    trusted_levels = normalize_structured_trusted_levels(
        _mapping_or_empty(battle_input.get("trusted_level_context")).get("current_levels"),
        pokemon=pokemon, session_id=session_id,
    )
    if trusted_levels:
        captured["trusted_level_context"] = {"current_levels": trusted_levels}
        provenance_added = True
    if provenance_added:
        captured["current_state_session_id"] = session_id
    return captured


def normalize_structured_observed_damage_confirmations(
    confirmations: Sequence[Mapping[str, Any]] | None, *, pokemon: Mapping[str, Any], session_id: str,
    moves: Mapping[str, Any] | None = None,
    used_move_confirmations: Sequence[Mapping[str, Any]] | None = None,
    hp_transition_confirmations: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Copy direct exact-HP observations without associating an unconfirmed move."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, (str, bytes)):
        return []
    active = {"self": _mapping_or_empty(pokemon.get("my_active")), "opponent": _mapping_or_empty(pokemon.get("opponent_active"))}
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in confirmations:
        if not isinstance(item, Mapping):
            continue
        attacker, defender, amount = item.get("attacker"), item.get("defender"), item.get("damage_amount")
        if (item.get("event_kind"), item.get("hp_unit"), item.get("source"), item.get("trust"), item.get("observed"), item.get("confirmed")) != ("direct_move_damage_observed", "exact", "ui_observed_damage_confirmation", "user_confirmed_observation", True, True):
            continue
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0 or item.get("move_id") is not None or item.get("move_slot") is not None or "hp_before" in item or "hp_after" in item:
            continue
        if not _observed_damage_owner_matches(attacker, active, session_id) or not _observed_damage_owner_matches(defender, active, session_id) or attacker.get("side") == defender.get("side"):
            continue
        observation_id = _optional_str(item.get("observation_id"))
        key = (attacker["side"], attacker["slot_index"], attacker["pokemon_id"], defender["side"], defender["slot_index"], defender["pokemon_id"], amount, observation_id)
        if key in seen:  # no sequence producer: only exact duplicate captures collapse
            continue
        seen.add(key)
        sequence = _optional_int(item.get("observation_sequence"))
        turn_number = _optional_int(item.get("turn_number"))
        if sequence is not None and sequence < 1:
            continue
        if turn_number is not None and (turn_number < 1 or item.get("turn_source") != "ui_turn_number_confirmation" or item.get("turn_trust") != "user_confirmed_observation"):
            continue
        event = {
            "event_kind": "direct_move_damage_observed", "attacker_side": attacker["side"], "attacker_slot_index": attacker["slot_index"], "attacker_pokemon_id": attacker["pokemon_id"],
            "defender_side": defender["side"], "defender_slot_index": defender["slot_index"], "defender_pokemon_id": defender["pokemon_id"],
            "move_id": None, "move_slot": None, "session_id": session_id, "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation",
            "observed": True, "confirmed": True, "damage_amount": amount, "hp_unit": "exact", "payload": {"damage_amount": amount, "hp_unit": "exact", "mode": "amount_only"},
            "attacker": deepcopy(attacker), "defender": deepcopy(defender),
            "attacker_provenance": deepcopy(attacker), "defender_provenance": deepcopy(defender),
        }
        if observation_id is not None:
            event["observation_id"] = observation_id
        event["observation_sequence"] = sequence
        event["turn_number"] = turn_number
        result.append(event)
    enriched = _enrich_observed_damage_events(
        result, active=active, session_id=session_id, moves=moves or {},
        used_move_confirmations=used_move_confirmations,
        hp_transition_confirmations=hp_transition_confirmations,
    )
    return sorted(enriched, key=lambda event: (event["observation_sequence"] is None, event["observation_sequence"] or 0, event.get("observation_id") or ""))


def _enrich_observed_damage_events(
    events: list[dict[str, Any]], *, active: Mapping[str, Mapping[str, Any]], session_id: str,
    moves: Mapping[str, Any], used_move_confirmations: Sequence[Mapping[str, Any]] | None,
    hp_transition_confirmations: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Link only confirmations bearing the same explicit observation id."""
    used_by_id = _normalize_used_move_confirmations(used_move_confirmations, active, session_id, moves)
    hp_by_id = _normalize_hp_transition_confirmations(hp_transition_confirmations, active, session_id)
    for event in events:
        observation_id = event.get("observation_id")
        if not isinstance(observation_id, str):
            continue
        used, transition = used_by_id.get(observation_id), hp_by_id.get(observation_id)
        if used is not None and _same_owner(used["attacker"], event["attacker"]):
            event.update(move_id=used["move_id"], move_slot=used["move_slot"], used_move_provenance=deepcopy(used))
            event["payload"]["mode"] = "amount_with_used_move"
        if transition is not None and _same_owner(transition["defender"], event["defender"]):
            derived = transition["hp_before"] - transition["hp_after"]
            if derived == event["damage_amount"]:
                event["hp_transition_provenance"] = deepcopy(transition)
                event["payload"].update(hp_before=transition["hp_before"], hp_after=transition["hp_after"], derived_damage=derived)
                event["payload"]["mode"] = "complete" if event["move_id"] is not None else "amount_with_hp_transition"
            else:
                event["enrichment_status"] = "conflicting_damage_amount"
    return events


def _normalize_used_move_confirmations(values: Sequence[Mapping[str, Any]] | None, active: Mapping[str, Mapping[str, Any]], session_id: str, moves: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return result
    available = moves.get("my_available_moves")
    for value in values:
        if not isinstance(value, Mapping):
            continue
        observation_id, attacker, move_id, slot = _optional_str(value.get("observation_id")), value.get("attacker"), _optional_str(value.get("move_id")), _optional_int(value.get("move_slot"))
        if observation_id is None or move_id is None or slot is None or value.get("source") != "ui_used_move_confirmation" or value.get("trust") != "user_confirmed_observation" or value.get("confirmed") is not True:
            continue
        if not _observed_damage_owner_matches(attacker, active, session_id) or attacker.get("side") != "self":
            continue
        if not isinstance(available, list) or not any(isinstance(entry, Mapping) and entry.get("slot_index") == slot and entry.get("move_id") == move_id for entry in available):
            continue
        result.setdefault(observation_id, {"move_id": move_id, "move_slot": slot, "attacker": deepcopy(attacker), "source": "ui_used_move_confirmation", "trust": "user_confirmed_observation", "confirmed": True})
    return result


def _normalize_hp_transition_confirmations(values: Sequence[Mapping[str, Any]] | None, active: Mapping[str, Mapping[str, Any]], session_id: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return result
    for value in values:
        if not isinstance(value, Mapping):
            continue
        observation_id, defender, before, after = _optional_str(value.get("observation_id")), value.get("defender"), value.get("hp_before"), value.get("hp_after")
        if observation_id is None or value.get("hp_unit") != "exact" or value.get("source") != "ui_exact_hp_transition_confirmation" or value.get("trust") != "user_confirmed_observation" or value.get("confirmed") is not True:
            continue
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (before, after)) or after > before or not _observed_damage_owner_matches(defender, active, session_id):
            continue
        result.setdefault(observation_id, {"defender": deepcopy(defender), "hp_before": before, "hp_after": after, "hp_unit": "exact", "source": "ui_exact_hp_transition_confirmation", "trust": "user_confirmed_observation", "confirmed": True})
    return result


def _same_owner(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in ("side", "slot_index", "pokemon_id", "session_id"))


def _observed_damage_owner_matches(owner: Any, active: Mapping[str, Mapping[str, Any]], session_id: str) -> bool:
    if not isinstance(owner, Mapping) or owner.get("side") not in {"self", "opponent"} or owner.get("session_id") != session_id:
        return False
    expected = active[owner["side"]]
    return owner.get("slot_index") == _optional_int(expected.get("slot_index")) and owner.get("pokemon_id") == _optional_str(expected.get("name_en")) and isinstance(owner.get("source"), str) and isinstance(owner.get("trust"), str)


def normalize_structured_final_stat_confirmations(
    confirmations: Sequence[Mapping[str, Any]] | None, *, pokemon: Mapping[str, Any],
    session_id: str,
) -> list[dict[str, Any]]:
    """Keep only pre-captured final stats that still match this structured request.

    Provenance is captured at the confirmation boundary by MainWindow. This
    helper deliberately does not attach missing slot, Pokemon, or session facts
    at request time, preventing a stat set from following a side after a switch.
    """
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, (str, bytes)):
        return []
    active_slots = {
        "self": _optional_int(_mapping_or_empty(pokemon.get("my_active")).get("slot_index")),
        "opponent": _optional_int(_mapping_or_empty(pokemon.get("opponent_active")).get("slot_index")),
    }
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for confirmation in confirmations:
        if not isinstance(confirmation, Mapping):
            continue
        raw = {key: value for key, value in confirmation.items() if key != "provenance"}
        try:
            normalized = normalize_user_confirmed_final_battle_stat(raw)
        except ValueError:
            continue
        provenance = confirmation.get("provenance")
        entry = {**normalized, "provenance": deepcopy(provenance)}
        if not _entry_has_valid_provenance(entry, active_slots=active_slots, pokemon=pokemon, session_id=session_id):
            continue
        key = (normalized["side"], normalized["stat"])
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def normalize_structured_ability_confirmations(
    confirmations: Sequence[Mapping[str, Any]] | None, *, pokemon: Mapping[str, Any], session_id: str,
) -> list[dict[str, Any]]:
    """Accept only explicit, pre-bound current abilities for this request."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, (str, bytes)):
        return []
    active_slots = {
        "self": _optional_int(_mapping_or_empty(pokemon.get("my_active")).get("slot_index")),
        "opponent": _optional_int(_mapping_or_empty(pokemon.get("opponent_active")).get("slot_index")),
    }
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for confirmation in confirmations:
        if not isinstance(confirmation, Mapping):
            continue
        raw = {key: value for key, value in confirmation.items() if key != "provenance"}
        try:
            normalized = normalize_user_confirmed_current_ability(raw)
        except ValueError:
            continue
        if normalized["ability"] == "unknown":
            continue
        entry = {**normalized, "provenance": deepcopy(confirmation.get("provenance"))}
        if normalized["side"] in seen:
            continue
        if not _entry_has_valid_provenance(entry, active_slots=active_slots, pokemon=pokemon, session_id=session_id):
            continue
        provenance = entry["provenance"]
        if provenance.get("source") != "user_confirmed_current_ability" or provenance.get("trust") != "user_confirmed_current":
            continue
        seen.add(normalized["side"])
        result.append(entry)
    return result


def normalize_structured_trusted_levels(
    confirmations: Sequence[Mapping[str, Any]] | None, *, pokemon: Mapping[str, Any], session_id: str,
) -> list[dict[str, Any]]:
    """Copy only pre-provenanced trusted levels; do not manufacture ownership."""
    if not isinstance(confirmations, Sequence) or isinstance(confirmations, (str, bytes)):
        return []
    active_slots = {
        "self": _optional_int(_mapping_or_empty(pokemon.get("my_active")).get("slot_index")),
        "opponent": _optional_int(_mapping_or_empty(pokemon.get("opponent_active")).get("slot_index")),
    }
    result: list[dict[str, Any]] = []
    for entry in confirmations:
        if not isinstance(entry, Mapping) or entry.get("side") not in {"self", "opponent"}:
            continue
        value = entry.get("value")
        provenance = entry.get("provenance")
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
            continue
        copied = {"side": entry["side"], "value": value, "provenance": deepcopy(provenance)}
        if not _entry_has_valid_provenance(copied, active_slots=active_slots, pokemon=pokemon, session_id=session_id):
            continue
        source, trust = provenance.get("source"), provenance.get("trust")
        if (source, trust) not in {
            ("user_confirmed_current_level", "user_confirmed_current"),
            ("deterministic_rules_metadata", "deterministic_rules_metadata"),
        }:
            continue
        result.append(copied)
    return result


def normalize_observed_events(
    events: Sequence[Mapping[str, Any]] | None, *, pokemon: Mapping[str, Any],
    session_id: str,
) -> list[dict[str, Any]]:
    """Return detached, canonical events that explicitly belong to this request.

    This is a capture boundary, not an inference engine. Missing or mismatched
    ownership/session metadata is excluded, and an observed event never creates
    a known item, ability, or current-condition fact.
    """
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return []
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for event in events:
        if not isinstance(event, Mapping):
            continue
        event_kind = _optional_str(event.get("event_kind")) or _optional_str(event.get("event_type"))
        side = _optional_str(event.get("side"))
        if event_kind is None or side not in {"self", "opponent"}:
            continue
        active_key = "my_active" if side == "self" else "opponent_active"
        active = _mapping_or_empty(pokemon.get(active_key))
        slot_index = _optional_int(active.get("slot_index"))
        pokemon_id = _optional_str(active.get("name_en"))
        if slot_index is None or pokemon_id is None:
            continue
        if event.get("slot_index") not in {None, slot_index}:
            continue
        if event.get("pokemon_id") not in {None, pokemon_id}:
            continue
        if event.get("session_id") not in {None, session_id}:
            continue
        if event.get("observed") is False or not (
            event.get("status") == "user_confirmed" or event.get("confirmed") is True
        ):
            continue
        source = _optional_str(event.get("source")) or "explicit_user_event_confirmation"
        payload = {
            key: deepcopy(value)
            for key, value in event.items()
            if key not in {
                "event_kind", "event_type", "side", "slot_index", "pokemon_id", "session_id",
                "source", "trust", "observed", "confirmed", "status", "provenance",
            }
        }
        dedup_key = (event_kind, side, slot_index, pokemon_id, session_id, _freeze_event_payload(payload))
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        provenance = {
            "side": side,
            "slot_index": slot_index,
            "pokemon_id": pokemon_id,
            "session_id": session_id,
            "source": source,
            "trust": "observed_event",
        }
        normalized.append({
            "event_kind": event_kind,
            "side": side,
            "slot_index": slot_index,
            "pokemon_id": pokemon_id,
            "session_id": session_id,
            "source": source,
            "trust": "observed_event",
            "observed": True,
            "confirmed": True,
            "payload": payload,
            "provenance": provenance,
        })
    return normalized


def _freeze_event_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze_event_payload(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze_event_payload(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_event_payload(item) for item in value)
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


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
    if context_key == "observed_damage_context":
        events = value.get("observed_damage_events")
        active = {"self": _mapping_or_empty(pokemon.get("my_active")), "opponent": _mapping_or_empty(pokemon.get("opponent_active"))}
        normalized = [deepcopy(event) for event in events if isinstance(event, Mapping) and event.get("event_kind") == "direct_move_damage_observed" and event.get("session_id") == session_id and _observed_damage_owner_matches(event.get("attacker"), active, session_id or "") and _observed_damage_owner_matches(event.get("defender"), active, session_id or "")] if isinstance(events, list) else []
        return {"observed_damage_events": normalized} if normalized else None
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
