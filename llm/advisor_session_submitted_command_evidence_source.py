"""Direct, session-bound submitted-command evidence for captured opportunities.

Admission represents a command supplied by a command-bearing input source. It
never derives a choice from execution, recommendation, or battle consequences.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_decision_point_provenance import (
    BOUNDARY_SCHEMA, _canonical, _freeze, _sequence, _token,
)
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource


SCHEMA_VERSION = "session-submitted-command-evidence-v1"


@dataclass(frozen=True, slots=True)
class SessionBoundSubmittedCommandEvidenceSource:
    """Accept at most one direct command for each retained opportunity."""

    opportunity_source: SessionBoundDecisionOpportunityBoundarySource
    source_id: str
    _commands: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.opportunity_source, SessionBoundDecisionOpportunityBoundarySource) or not _token(self.source_id):
            raise ValueError("invalid_submitted_command_source")

    @classmethod
    def create(
        cls, *, opportunity_source: SessionBoundDecisionOpportunityBoundarySource,
        source_id: str,
    ) -> Mapping[str, Any]:
        if not isinstance(opportunity_source, SessionBoundDecisionOpportunityBoundarySource):
            return _result("rejected", "opportunity_source_invalid")
        if not _token(source_id):
            return _result("rejected", "command_source_id_invalid")
        return {"status": "source_ready", "schema_version": SCHEMA_VERSION,
                "source": cls(opportunity_source, source_id)}

    @property
    def session_id(self) -> str:
        return self.opportunity_source.session_id

    @property
    def battle_id(self) -> str:
        return self.opportunity_source.battle_id

    @property
    def channel(self) -> str:
        return self.opportunity_source.channel

    def admit_submitted_command(
        self, *, captured_session_id: str, opportunity_record: Mapping[str, Any],
        actor: Mapping[str, Any], source_command_id: str, command_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Record direct input without requiring any subsequent execution."""
        if captured_session_id != self.session_id:
            return _result("rejected", "stale_or_foreign_session")
        opportunity = self._retained_opportunity(opportunity_record)
        if opportunity is None:
            return _result("rejected", "opportunity_not_retained_by_source")
        boundary = opportunity["certificate"]
        if actor != self.opportunity_source.actor or actor != boundary["actor"]:
            return _result("rejected", "foreign_actor")
        if not _token(source_command_id):
            return _result("rejected", "source_command_id_invalid")
        if not _command(command_payload, boundary["decision_kind"]):
            return _result("rejected", "submitted_command_payload_invalid")
        payload = _freeze(command_payload)
        identity = {
            "session_id": self.session_id, "battle_id": self.battle_id,
            "opportunity_source_id": self.opportunity_source.source_id,
            "command_source_id": self.source_id, "channel": self.channel,
            "actor": boundary["actor"], "boundary_id": boundary["boundary_id"],
            "source_command_id": source_command_id, "command_payload": payload,
        }
        command_id = "submitted-command:" + hashlib.sha256(_canonical(identity)).hexdigest()
        record = _freeze({
            "status": "direct", "schema_version": SCHEMA_VERSION,
            "command_id": command_id, "source_command_id": source_command_id,
            "source_provenance": "direct_command_input_admission",
            "session_id": self.session_id, "battle_id": self.battle_id,
            "opportunity_source_id": self.opportunity_source.source_id,
            "command_source_id": self.source_id, "channel": self.channel,
            "actor": boundary["actor"], "boundary_id": boundary["boundary_id"],
            "decision_kind": boundary["decision_kind"], "turn_number": boundary["turn_number"],
            "prefix_fingerprint": boundary["prefix_fingerprint"],
            "context_fingerprint": boundary["context_fingerprint"],
            "legal_action_set_fingerprint": boundary["legal_action_set_fingerprint"],
            "command_payload": payload,
        })
        old = self._commands.get(boundary["boundary_id"])
        if old is not None:
            if old != record:
                return _result("rejected", "conflicting_submitted_command")
            return _freeze({"status": "duplicate", "schema_version": SCHEMA_VERSION, "evidence": old})
        self._commands[boundary["boundary_id"]] = record
        return _freeze({"status": "admitted", "schema_version": SCHEMA_VERSION, "evidence": record})

    def authenticates(self, evidence: Any, boundary: Mapping[str, Any]) -> bool:
        """Check exact retained evidence and opportunity, not a caller's claim."""
        if not isinstance(evidence, MappingProxyType) or not isinstance(boundary, Mapping):
            return False
        if evidence.get("schema_version") != SCHEMA_VERSION or evidence.get("status") != "direct":
            return False
        retained = self._commands.get(boundary.get("boundary_id"))
        if retained is None or retained != evidence:
            return False
        opportunity = self._retained_opportunity_by_boundary_id(boundary.get("boundary_id"))
        return opportunity is not None and opportunity["certificate"] == boundary

    def read_snapshot(self, *, captured_session_id: str) -> Mapping[str, Any]:
        if captured_session_id != self.session_id:
            return _result("rejected", "stale_or_foreign_session")
        commands = tuple(self._commands[key] for key in sorted(self._commands))
        opportunities = self.opportunity_source.read_snapshot(captured_session_id=self.session_id)["opportunities"]
        return _freeze({
            "status": "ready", "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id, "battle_id": self.battle_id,
            "opportunity_source_id": self.opportunity_source.source_id,
            "command_source_id": self.source_id, "channel": self.channel,
            "actor": self.opportunity_source.actor,
            "command_evidence": commands,
            "command_unknown_boundary_ids": tuple(sorted(
                item["certificate"]["boundary_id"] for item in opportunities
                if item["certificate"]["boundary_id"] not in self._commands
            )),
        })

    def _retained_opportunity(self, value: Any) -> Mapping[str, Any] | None:
        if not isinstance(value, MappingProxyType):
            return None
        certificate = value.get("certificate")
        if not isinstance(certificate, Mapping) or certificate.get("schema_version") != BOUNDARY_SCHEMA:
            return None
        retained = self._retained_opportunity_by_boundary_id(certificate.get("boundary_id"))
        if retained is None:
            return None
        return retained if all(value.get(key) == retained[key] for key in (
            "certificate", "channel_source", "context_reference", "legal_action_set",
        )) else None

    def _retained_opportunity_by_boundary_id(self, boundary_id: Any) -> Mapping[str, Any] | None:
        if not _token(boundary_id):
            return None
        snapshot = self.opportunity_source.read_snapshot(captured_session_id=self.session_id)
        matches = [item for item in snapshot["opportunities"] if item["certificate"]["boundary_id"] == boundary_id]
        return matches[0] if len(matches) == 1 else None


def _command(value: Any, decision_kind: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    kind = value.get("kind")
    if kind == "attack":
        if decision_kind != "turn_start" or not set(value) <= {"kind", "move_slot", "move_id"}:
            return False
        slot, move_id = value.get("move_slot"), value.get("move_id")
        return (slot is not None or move_id is not None) and (
            slot is None or (_sequence(slot) and slot <= 4)
        ) and (move_id is None or _token(move_id))
    if kind == "switch":
        if decision_kind not in {"turn_start", "forced_replacement", "mid_turn_replacement"} or not set(value) <= {"kind", "incoming_slot_index", "incoming_pokemon_id"}:
            return False
        slot, pokemon_id = value.get("incoming_slot_index"), value.get("incoming_pokemon_id")
        return (slot is not None or pokemon_id is not None) and (
            slot is None or _sequence(slot, zero=True)
        ) and (pokemon_id is None or _token(pokemon_id))
    return False


def _result(status: str, reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": status, "schema_version": SCHEMA_VERSION, "reason": reason})
