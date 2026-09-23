"""Session-bound raw battle-end declarations, separate from reward or replay.

Only an explicitly admitted final declaration establishes battle terminality.
Stream exhaustion is retained as incomplete evidence and never as a result.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_decision_point_provenance import _canonical, _freeze, _sequence, _token


SCHEMA_VERSION = "session-battle-terminal-outcome-evidence-v1"
DECLARED_RESULTS = frozenset({"self", "opponent", "tie", "none_observed"})
TERMINATION_CAUSES = frozenset({
    "all_fainted", "forfeit_self", "forfeit_opponent",
    "inactivity_self", "inactivity_opponent", "rules_based",
    "administrative", "server_error", "unrecognized", "unknown",
})
EVIDENCE_COMPLETENESS = frozenset({
    "final_declaration_observed", "stream_ended_without_declaration",
    "inconsistent", "unknown",
})
SOURCE_KINDS = frozenset({"first_person_battle_stream", "simulator_output"})


@dataclass(frozen=True, slots=True)
class SessionBoundBattleTerminalOutcomeEvidenceSource:
    """Retain one direct final declaration, or an explicit truncated stream."""

    session_id: str
    battle_id: str
    source_id: str
    source_kind: str
    _records: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (not all(_token(value) for value in (self.session_id, self.battle_id, self.source_id))
                or self.source_kind not in SOURCE_KINDS):
            raise ValueError("invalid_battle_terminal_source")

    @classmethod
    def create(
        cls, *, session_id: str, battle_id: str, source_id: str, source_kind: str,
    ) -> Mapping[str, Any]:
        if not all(_token(value) for value in (session_id, battle_id, source_id)):
            return _failure("source_identity_invalid")
        if source_kind not in SOURCE_KINDS:
            return _failure("source_kind_invalid")
        return {"status": "source_ready", "schema_version": SCHEMA_VERSION,
                "source": cls(session_id, battle_id, source_id, source_kind)}

    def admit_final_declaration(
        self, *, captured_session_id: str, captured_battle_id: str,
        declaring_source_id: str, source_terminal_event_id: str,
        source_event_sequence: int, declared_result: str,
        termination_cause: str, turn_number: int | None = None,
        raw_termination_cause: str | None = None,
        source_cause_event_id: str | None = None,
    ) -> Mapping[str, Any]:
        """Admit only a directly observed final result with explicit dimensions."""
        scope = self._scope(captured_session_id, captured_battle_id, declaring_source_id)
        if scope is not None:
            return _failure(scope)
        if "stream_end" in self._records:
            return _failure("declaration_after_stream_end")
        if declared_result not in {"self", "opponent", "tie"}:
            return _failure("declared_result_invalid")
        if termination_cause not in TERMINATION_CAUSES:
            return _failure("termination_cause_invalid")
        if termination_cause != "unknown" and not _token(source_cause_event_id):
            return _failure("direct_cause_provenance_missing")
        if (not _token(source_terminal_event_id) or not _sequence(source_event_sequence)
                or not _turn_or_none(turn_number) or not _raw_or_none(raw_termination_cause)
                or not _raw_or_none(source_cause_event_id)):
            return _failure("final_declaration_provenance_invalid")
        facts = {
            **self._identity(),
            "authority": "direct_final_declaration",
            "source_terminal_event_id": source_terminal_event_id,
            "source_event_sequence": source_event_sequence,
            "turn_number": turn_number,
            "declared_result": declared_result,
            "termination_cause": termination_cause,
            "raw_termination_cause": raw_termination_cause,
            "source_cause_event_id": source_cause_event_id,
            "evidence_completeness": "final_declaration_observed",
            "battle_terminal": True,
        }
        evidence_id = "battle-terminal:" + hashlib.sha256(_canonical(facts)).hexdigest()
        record = _freeze({"schema_version": SCHEMA_VERSION, "evidence_id": evidence_id, **facts})
        old = self._records.get("final")
        if old is not None:
            if old != record:
                return _failure("conflicting_final_declaration")
            return _freeze({"status": "duplicate", "schema_version": SCHEMA_VERSION, "evidence": old})
        self._records["final"] = record
        return _freeze({"status": "admitted", "schema_version": SCHEMA_VERSION, "evidence": record})

    def record_stream_end_without_declaration(
        self, *, captured_session_id: str, captured_battle_id: str,
        declaring_source_id: str, source_stream_end_event_id: str,
        source_event_sequence: int, turn_number: int | None = None,
    ) -> Mapping[str, Any]:
        """Preserve truncation without claiming a winner or battle terminality."""
        scope = self._scope(captured_session_id, captured_battle_id, declaring_source_id)
        if scope is not None:
            return _failure(scope)
        if "final" in self._records:
            return _failure("final_declaration_already_observed")
        if (not _token(source_stream_end_event_id) or not _sequence(source_event_sequence)
                or not _turn_or_none(turn_number)):
            return _failure("stream_end_provenance_invalid")
        facts = {
            **self._identity(),
            "authority": "direct_stream_end_marker",
            "source_stream_end_event_id": source_stream_end_event_id,
            "source_event_sequence": source_event_sequence,
            "turn_number": turn_number,
            "declared_result": "none_observed",
            "termination_cause": "unknown",
            "evidence_completeness": "stream_ended_without_declaration",
            "battle_terminal": False,
        }
        evidence_id = "stream-end:" + hashlib.sha256(_canonical(facts)).hexdigest()
        record = _freeze({"schema_version": SCHEMA_VERSION, "evidence_id": evidence_id, **facts})
        old = self._records.get("stream_end")
        if old is not None:
            if old != record:
                return _failure("conflicting_stream_end_evidence")
            return _freeze({"status": "duplicate", "schema_version": SCHEMA_VERSION, "evidence": old})
        self._records["stream_end"] = record
        return _freeze({"status": "admitted", "schema_version": SCHEMA_VERSION, "evidence": record})

    def read_snapshot(self, *, captured_session_id: str, captured_battle_id: str) -> Mapping[str, Any]:
        if captured_session_id != self.session_id:
            return _failure("stale_or_foreign_session")
        if captured_battle_id != self.battle_id:
            return _failure("foreign_battle")
        terminal = self._records.get("final")
        stream_end = self._records.get("stream_end")
        return _freeze({
            "status": "ready", "schema_version": SCHEMA_VERSION, **self._identity(),
            "terminal_evidence": terminal, "stream_end_evidence": stream_end,
            "outcome_evidence": terminal if terminal is not None else stream_end,
            "terminality_availability": "observed" if terminal is not None else "unavailable",
        })

    def authenticates(self, evidence: Any) -> bool:
        """Check that a detached evidence record is retained by this live source."""
        return isinstance(evidence, MappingProxyType) and any(
            retained is not None and evidence == retained
            for retained in (self._records.get("final"), self._records.get("stream_end"))
        )

    def _scope(self, session_id: str, battle_id: str, source_id: str) -> str | None:
        if session_id != self.session_id:
            return "stale_or_foreign_session"
        if battle_id != self.battle_id:
            return "foreign_battle"
        if source_id != self.source_id:
            return "foreign_declaring_source"
        return None

    def _identity(self) -> dict[str, str]:
        return {
            "session_id": self.session_id, "battle_id": self.battle_id,
            "source_id": self.source_id, "source_kind": self.source_kind,
        }


def _turn_or_none(value: Any) -> bool:
    return value is None or _sequence(value)


def _raw_or_none(value: Any) -> bool:
    return value is None or _token(value)


def _failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
