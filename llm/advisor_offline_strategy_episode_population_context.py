"""Detached episode-level rules and population metadata, without admission policy."""
from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import (
    _context as _decision_context_valid,
    _freeze,
    _token,
    fingerprint_decision_contract_reference,
)
from llm.advisor_offline_strategy_episode_terminal_binding import (
    SCHEMA_VERSION as TERMINAL_BINDING_SCHEMA,
    materialize_offline_strategy_episode_terminal_binding,
)
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)


SCHEMA_VERSION = "offline-strategy-episode-population-context-v1"
COLLECTION_MODES = frozenset({
    "first_person_capture", "simulator_self_generated", "spectator_auxiliary", "unknown",
})
COMPETITION_CONTEXTS = frozenset({
    "ladder", "tournament", "direct_challenge", "self_play", "fixture", "unknown",
})
OPTIONAL_FIELDS = frozenset({
    "collection_time", "self_rating", "opponent_rating", "self_player_cluster_id",
    "opponent_player_cluster_id", "team_cluster_id", "set_id", "source_dataset_id",
})
_RATING_FIELDS = frozenset({"self_rating", "opponent_rating"})


def materialize_offline_strategy_episode_population_context(
    *, terminal_binding: Mapping[str, Any],
    terminal_source: SessionBoundBattleTerminalOutcomeEvidenceSource,
    session_id: str, battle_id: str,
    rules_context: Mapping[str, Any], sampling_context: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Revalidate the terminal binding, then attach explicit battle-level metadata."""
    if not isinstance(terminal_source, SessionBoundBattleTerminalOutcomeEvidenceSource):
        return _failure("terminal_source_invalid")
    if not isinstance(terminal_binding, MappingProxyType) or terminal_binding.get("schema_version") != TERMINAL_BINDING_SCHEMA:
        return _failure("terminal_binding_invalid")
    if session_id != terminal_source.session_id or session_id != terminal_binding.get("session_id"):
        return _failure("foreign_session")
    if battle_id != terminal_source.battle_id or battle_id != terminal_binding.get("battle_id"):
        return _failure("foreign_battle")
    try:
        rebuilt = materialize_offline_strategy_episode_terminal_binding(
            episode=terminal_binding["base_episode"], terminal_source=terminal_source,
            terminal_evidence=terminal_binding["terminal_outcome"]["evidence"],
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failure("terminal_binding_revalidation_failed")
    if rebuilt.get("status") not in {"resolved", "incomplete"} or rebuilt != terminal_binding:
        return _failure("terminal_binding_revalidation_failed")
    if not _decision_context_valid(rules_context):
        return _failure("rules_context_invalid")
    normalized_sampling = _sampling(sampling_context)
    if normalized_sampling is None:
        return _failure("sampling_context_invalid")

    rules_fingerprint = fingerprint_decision_contract_reference(rules_context)
    sampling_fingerprint = fingerprint_decision_contract_reference(normalized_sampling)
    identity = {
        "session_id": session_id, "battle_id": battle_id,
        "episode_terminal_binding_id": terminal_binding["binding_id"],
        "rules_context_fingerprint": rules_fingerprint,
        "sampling_context_fingerprint": sampling_fingerprint,
    }
    return _freeze({
        "status": terminal_binding["status"],
        "schema_version": SCHEMA_VERSION,
        "context_binding_id": "offline-episode-population-context:" + fingerprint_decision_contract_reference(identity),
        "session_id": session_id, "battle_id": battle_id,
        "episode_terminal_binding_id": terminal_binding["binding_id"],
        "rules_context": rules_context,
        "rules_context_fingerprint": rules_fingerprint,
        "sampling_context": normalized_sampling,
        "sampling_context_fingerprint": sampling_fingerprint,
        "provenance": {
            "binding_basis": terminal_binding["binding_basis"],
            "metadata_authority": "explicit_caller_supplied_unverified",
            "decision_context_alignment": "not_proven_by_episode_transition_records",
        },
        "base_terminal_binding": terminal_binding,
    })


def _sampling(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or not {"collection_mode", "competition_context"} <= set(value):
        return None
    if set(value) - ({"collection_mode", "competition_context"} | OPTIONAL_FIELDS):
        return None
    if (not isinstance(value["collection_mode"], str) or value["collection_mode"] not in COLLECTION_MODES
            or not isinstance(value["competition_context"], str)
            or value["competition_context"] not in COMPETITION_CONTEXTS):
        return None
    normalized: dict[str, Any] = {
        "collection_mode": value["collection_mode"],
        "competition_context": value["competition_context"],
    }
    for field in sorted(OPTIONAL_FIELDS):
        if field not in value:
            normalized[field] = {"availability": "unavailable"}
            continue
        raw = value[field]
        if field in _RATING_FIELDS:
            if (not isinstance(raw, (int, float)) or isinstance(raw, bool)
                    or not math.isfinite(raw) or raw < 0):
                return None
        elif not _token(raw):
            return None
        normalized[field] = {"availability": "available", "value": raw}
    return normalized


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
