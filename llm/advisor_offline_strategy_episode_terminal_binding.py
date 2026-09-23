"""Detached, reward-free binding of an offline episode to direct battle-end evidence."""
from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_strategy_episode_dataset import (
    EPISODE_SCHEMA_VERSION,
    _canonical,
    _freeze,
    materialize_offline_strategy_episode,
)
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SCHEMA_VERSION as TERMINAL_SCHEMA_VERSION,
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)


SCHEMA_VERSION = "offline-strategy-episode-terminal-binding-v1"
BINDING_BASIS = "session_scoped_terminal_source"


def materialize_offline_strategy_episode_terminal_binding(
    *, episode: Mapping[str, Any],
    terminal_source: SessionBoundBattleTerminalOutcomeEvidenceSource,
    terminal_evidence: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Attach only evidence retained by the given source; never alter the episode."""
    if not isinstance(episode, MappingProxyType) or episode.get("schema_version") != EPISODE_SCHEMA_VERSION:
        return _failure("episode_invalid")
    try:
        rebuilt = materialize_offline_strategy_episode(episode.get("transitions"))
        if rebuilt.get("status") not in {"resolved", "incomplete"} or rebuilt != episode:
            return _failure("episode_revalidation_failed")
        final_turn = episode["final_next_state"]["turn_number"]
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failure("episode_revalidation_failed")
    if not isinstance(terminal_source, SessionBoundBattleTerminalOutcomeEvidenceSource):
        return _failure("terminal_source_invalid")
    if episode["session_id"] != terminal_source.session_id:
        return _failure("foreign_session")

    snapshot = terminal_source.read_snapshot(
        captured_session_id=episode["session_id"], captured_battle_id=terminal_source.battle_id,
    )
    retained = snapshot["outcome_evidence"]
    evidence = retained if terminal_evidence is None else terminal_evidence
    if evidence is not None and not terminal_source.authenticates(evidence):
        return _failure("terminal_evidence_not_authenticated")
    if evidence is not None and evidence.get("schema_version") != TERMINAL_SCHEMA_VERSION:
        return _failure("terminal_evidence_invalid")

    available = evidence is not None and evidence.get("authority") == "direct_final_declaration"
    if available:
        if (evidence.get("battle_terminal") is not True
                or evidence.get("evidence_completeness") != "final_declaration_observed"
                or evidence.get("declared_result") not in {"self", "opponent", "tie"}):
            return _failure("terminal_evidence_invalid")
        terminal_turn = evidence.get("turn_number")
        if terminal_turn is not None and terminal_turn < final_turn:
            return _failure("terminal_before_episode_final_turn")
        outcome = {
            "availability": "available", "evidence": evidence,
            "declared_result": evidence["declared_result"],
            "termination_cause": evidence["termination_cause"],
            "evidence_completeness": evidence["evidence_completeness"],
            "evidence_id": evidence["evidence_id"],
            "turn_number": terminal_turn,
        }
    elif evidence is None:
        outcome = {"availability": "unavailable", "reason": "terminal_declaration_not_observed", "evidence": None}
    elif (evidence.get("authority") == "direct_stream_end_marker"
          and evidence.get("battle_terminal") is False
          and evidence.get("evidence_completeness") == "stream_ended_without_declaration"):
        outcome = {"availability": "unavailable", "reason": "stream_ended_without_declaration", "evidence": evidence}
    else:
        return _failure("terminal_evidence_invalid")

    identity = {
        "episode_id": episode["episode_id"],
        "evidence_id": evidence["evidence_id"] if evidence is not None else None,
        "binding_basis": BINDING_BASIS,
        "session_id": episode["session_id"],
        "battle_id": terminal_source.battle_id,
        "source_id": terminal_source.source_id,
        "source_kind": terminal_source.source_kind,
    }
    return _freeze({
        "status": "resolved" if available and episode["status"] == "resolved" else "incomplete",
        "schema_version": SCHEMA_VERSION,
        "binding_id": "offline-episode-terminal-binding:" + hashlib.sha256(_canonical(identity)).hexdigest(),
        "episode_id": episode["episode_id"],
        "session_id": episode["session_id"],
        "battle_id": terminal_source.battle_id,
        "binding_basis": BINDING_BASIS,
        "terminal_source": {
            "source_id": terminal_source.source_id,
            "source_kind": terminal_source.source_kind,
        },
        "base_episode_status": episode["status"],
        "base_episode_completeness": episode["completeness"],
        "continuity_gaps": episode["continuity_gaps"],
        "terminal_outcome": outcome,
        "base_episode": episode,
    })


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
