"""Canonical metadata authority for already observed, active opponent moves."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_candidate_contract import _selected_move_from_metadata
from llm.advisor_runtime_d0_opponent_action_authority import METADATA_SCHEMA_VERSION
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


def freeze_runtime_d0_observed_opponent_move_metadata_authorities(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], move_repository: Any) -> dict[str, Mapping[str, Any]]:
    """Normalize repository metadata only for trusted, identity-bound moves."""
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    opponent = strategy_d0.get("active_owners", {}).get("opponent") if isinstance(strategy_d0, Mapping) else None
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if fresh.get("status") != "current" or not isinstance(opponent, Mapping) or not isinstance(state, Mapping): return {}
    side = state.get("opponent_side"); roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(opponent.get("slot_index")) if isinstance(roster, Mapping) else None
    moves, provenance = (pokemon.get("known_move_ids"), pokemon.get("known_move_ids_provenance")) if isinstance(pokemon, Mapping) and side.get("active_slot_index") == opponent.get("slot_index") and pokemon.get("pokemon_id") == opponent.get("pokemon_id") else (None, None)
    if not isinstance(moves, list) or not isinstance(provenance, Mapping): return {}
    result = {}
    for move_id in moves:
        observation = provenance.get(move_id)
        base = {"schema_version": METADATA_SCHEMA_VERSION, "move_id": move_id, "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "opponent_actor": deepcopy(dict(opponent)), "observation_provenance": deepcopy(observation) if isinstance(observation, Mapping) else None}
        if not isinstance(move_id, str) or not move_id or not isinstance(observation, Mapping) or observation.get("event_kind") not in {"used_move_observed", "current_opponent_response_set_observed"} or observation.get("trust") != "user_confirmed_observation":
            result[move_id] = {"status": "incomplete", **base, "reason": "trusted_observed_opponent_move_provenance_missing"}; continue
        try: metadata = _selected_move_from_metadata(move_id, move_repository.get(move_id))
        except Exception: result[move_id] = {"status": "incomplete", **base, "reason": "canonical_opponent_move_metadata_missing"}; continue
        if metadata.get("move_id") != move_id:
            result[move_id] = {"status": "rejected", **base, "reason": "canonical_opponent_move_metadata_binding_conflict"}; continue
        result[move_id] = {"status": "resolved", **base, "metadata": metadata, "provenance": "repository_normalized_observed_opponent_move_metadata_bound_to_runtime_d0_v1"}
    return result
