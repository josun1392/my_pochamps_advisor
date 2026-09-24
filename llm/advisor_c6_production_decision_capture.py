"""Battle-local C6 evidence capture; never an observation or recommendation authority."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_decision_point_provenance import _context, _freeze, _legal, _token
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
from llm.advisor_session_actor_private_decision_information import SessionBoundActorPrivateDecisionInformationSource
from llm.advisor_session_decision_public_battle_information import SessionBoundDecisionPublicBattleInformationSource


SCHEMA_VERSION = "c6-production-decision-capture-v1"


@dataclass(frozen=True, slots=True)
class ProductionDecisionCapture:
    """One session/battle's detached, in-memory decision evidence owners."""

    opportunity_source: SessionBoundDecisionOpportunityBoundarySource
    command_source: SessionBoundSubmittedCommandEvidenceSource
    private_source: SessionBoundActorPrivateDecisionInformationSource
    public_source: SessionBoundDecisionPublicBattleInformationSource

    @classmethod
    def create(cls, *, session_id: str, battle_id: str, actor: Mapping[str, Any],
               source_id: str) -> Mapping[str, Any]:
        if not _token(session_id) or not _token(battle_id) or not _token(source_id):
            return _rejected("source_identity_invalid")
        opportunity = SessionBoundDecisionOpportunityBoundarySource.create(
            session_id=session_id, battle_id=battle_id, source_id=source_id,
            channel="actor_first_person", actor=actor)
        if opportunity["status"] != "source_ready" or not isinstance(actor, Mapping) or actor.get("side") != "self":
            return _rejected("actor_invalid")
        owner = opportunity["source"]
        command = SessionBoundSubmittedCommandEvidenceSource.create(
            opportunity_source=owner, source_id=source_id + ":command")
        private = SessionBoundActorPrivateDecisionInformationSource.create(
            opportunity_source=owner, command_source=command["source"], source_id=source_id + ":private")
        public = SessionBoundDecisionPublicBattleInformationSource.create(
            opportunity_source=owner, command_source=command["source"], source_id=source_id + ":public")
        if private["status"] != "source_ready" or public["status"] != "source_ready":
            return _rejected("evidence_source_invalid")
        return MappingProxyType({"status": "source_ready", "schema_version": SCHEMA_VERSION,
                                 "source": cls(owner, command["source"], private["source"], public["source"])})

    @property
    def session_id(self) -> str:
        return self.opportunity_source.session_id

    @property
    def battle_id(self) -> str:
        return self.opportunity_source.battle_id

    def begin_decision_capture(
        self, *, captured_session_id: str, captured_battle_id: str, actor: Mapping[str, Any],
        opportunity_id: str, decision_kind: str, turn_number: int,
        simultaneity_group_id: str, context_reference: Mapping[str, Any],
        legal_action_set: Mapping[str, Any], public_snapshot: Mapping[str, Any],
        private_snapshot: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if captured_session_id != self.session_id or captured_battle_id != self.battle_id:
            return _rejected("stale_or_foreign_battle")
        if not _context(context_reference) or not _legal(legal_action_set):
            return _rejected("context_or_legal_set_invalid")
        opportunity = self.opportunity_source.capture_opportunity(
            captured_session_id=captured_session_id, opportunity_id=opportunity_id,
            actor=actor, decision_kind=decision_kind, turn_number=turn_number,
            simultaneity_group_id=simultaneity_group_id,
            context_reference=context_reference, legal_action_set=legal_action_set)
        if opportunity["status"] not in {"captured", "duplicate"}:
            return opportunity
        public = self.public_source.admit_public_snapshot(
            captured_session_id=captured_session_id, captured_battle_id=captured_battle_id,
            opportunity_record=opportunity, actor=actor,
            source_public_event_id=opportunity_id + ":public", public_snapshot=public_snapshot)
        if public["status"] not in {"admitted", "duplicate"}:
            return public
        private = self.private_source.admit_private_snapshot(
            captured_session_id=captured_session_id, captured_battle_id=captured_battle_id,
            opportunity_record=opportunity, actor=actor,
            source_private_event_id=opportunity_id + ":private", private_snapshot=private_snapshot)
        if private["status"] not in {"admitted", "duplicate"}:
            return private
        return _freeze({"status": "captured" if opportunity["status"] == "captured" else "duplicate",
                        "schema_version": SCHEMA_VERSION, "opportunity": opportunity,
                        "public_information": public["evidence"],
                        "private_information": private["evidence"]})

    def confirm_submitted_command(
        self, *, captured_session_id: str, captured_battle_id: str, boundary_id: str,
        actor: Mapping[str, Any], confirmation_event_id: str,
        command_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Only an explicit command-bearing confirmation calls this method."""
        if captured_session_id != self.session_id or captured_battle_id != self.battle_id:
            return _rejected("stale_or_foreign_battle")
        opportunities = self.opportunity_source.read_snapshot(captured_session_id=self.session_id)["opportunities"]
        matches = [row for row in opportunities if row["certificate"]["boundary_id"] == boundary_id]
        if len(matches) != 1:
            return _rejected("boundary_not_retained")
        opportunity = matches[0]
        if (not any(row["boundary_id"] == boundary_id for row in self.public_source.read_snapshot(
                captured_session_id=self.session_id)["evidence"])
                or not any(row["boundary_id"] == boundary_id for row in self.private_source.read_snapshot(
                    captured_session_id=self.session_id)["evidence"])):
            return _rejected("pre_command_information_missing")
        return self.command_source.admit_submitted_command(
            captured_session_id=captured_session_id, opportunity_record=opportunity,
            actor=actor, source_command_id=confirmation_event_id, command_payload=command_payload)

    def read_capture_snapshot(self, *, captured_session_id: str, captured_battle_id: str) -> Mapping[str, Any]:
        if captured_session_id != self.session_id or captured_battle_id != self.battle_id:
            return _rejected("stale_or_foreign_battle")
        return _freeze({"status": "ready", "schema_version": SCHEMA_VERSION,
                        "session_id": self.session_id, "battle_id": self.battle_id,
                        "opportunities": self.opportunity_source.read_snapshot(captured_session_id=self.session_id),
                        "public_information": self.public_source.read_snapshot(captured_session_id=self.session_id),
                        "private_information": self.private_source.read_snapshot(captured_session_id=self.session_id),
                        "submitted_commands": self.command_source.read_snapshot(captured_session_id=self.session_id),
                        "scope": "in_memory_admitted_decisions_only"})


def _rejected(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
