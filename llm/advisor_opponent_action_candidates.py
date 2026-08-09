"""Frozen trusted-opponent action candidates; no ranking or provider integration."""
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_turn_snapshot import _current_state_session_id, _snapshot_side_stat_provenance


def build_opponent_action_candidates(*, turn_snapshot: Any, move_repository: Any, species_repository: Any = None) -> dict[str, Any]:
    serialized = turn_snapshot.to_dict()
    current = serialized.get("current_state", {})
    context = current.get("known_move_context") if isinstance(current, Mapping) else None
    opponent = serialized.get("battle_state", {}).get("active_opponent")
    self_slot = serialized.get("battle_state", {}).get("active_player")
    if not isinstance(context, Mapping) or not isinstance(opponent, Mapping) or not isinstance(self_slot, Mapping):
        return _empty()
    entry = context.get("opponent")
    if not isinstance(entry, Mapping) or entry.get("pokemon_id") != opponent.get("species_id") or entry.get("slot_index") != opponent.get("slot_index"):
        return _empty()
    moves = entry.get("known_move_ids", [])
    if not isinstance(moves, list) or any(not isinstance(move, str) or not move for move in moves):
        return _empty()
    state = entry.get("state")
    complete = state == "complete" and len(moves) == 4
    session = context.get("session_id") if isinstance(context.get("session_id"), str) else _current_state_session_id(current)
    candidates = []
    for index, move_id in enumerate(moves):
        metadata = _resolve(move_repository, move_id)
        candidate = {"candidate_id": f"opponent-action:{session or 'unknown'}:{opponent['species_id']}:{move_id}:{index}", "role": "opponent_action", "acting_side": "opponent", "target_side": "self", "session_id": session, "pokemon_identity": opponent["species_id"], "move_id": move_id, "move_identity_authority": "frozen_known_move_context", "moveset_state": state, "candidate_set_complete": complete, "metadata_supportability": "complete" if metadata is not None else "unsupported_mechanic"}
        if metadata is not None:
            candidate["move_metadata"] = deepcopy(metadata)
            candidate["mechanics_snapshot"] = _reverse_snapshot(opponent, self_slot, current, session, move_id, index, metadata, species_repository)
        candidates.append(candidate)
    return {"known_move_state": state, "known_candidate_count": len(candidates), "unknown_slots_remaining": 4 - len(moves), "candidate_set_complete": complete, "opponent_action_candidates": candidates}


def _reverse_snapshot(attacker, defender, current, session, move_id, index, metadata, species_repository):
    return {"attacker": {**deepcopy(dict(attacker)), "session_id": session}, "defender": {**deepcopy(dict(defender)), "session_id": session}, "move": {**deepcopy(metadata), "move_id": move_id, "slot_index": index, "owner_species_id": attacker["species_id"]}, "battle_context": {"current_state": deepcopy(current), "stat_provenance": {"attacker": _snapshot_side_stat_provenance(attacker, "opponent", current, session, species_repository), "defender": _snapshot_side_stat_provenance(defender, "self", current, session, species_repository)}}}


def _resolve(repository, move_id):
    try:
        value = repository.get(move_id) if hasattr(repository, "get") else repository[move_id]
    except Exception:
        return None
    if value is None: return None
    if isinstance(value, Mapping): return dict(value) if value.get("move_id", move_id) == move_id else None
    return {key: getattr(value, key) for key in ("move_id", "category", "power", "type", "priority", "target", "drain", "healing") if getattr(value, key, None) is not None} if getattr(value, "move_id", move_id) == move_id else None


def _empty(): return {"known_move_state": "unknown", "known_candidate_count": 0, "unknown_slots_remaining": 4, "candidate_set_complete": False, "opponent_action_candidates": []}
