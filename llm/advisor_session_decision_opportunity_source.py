"""Session-owned, opportunity-first certificates for offline decision provenance.

The owner records only opportunities explicitly admitted to it. A future
command-bearing or simulator source must ensure every real request is admitted.
Channel event references are opaque; they are not reducer observations or
submitted-choice evidence.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_decision_point_provenance import (
    BOUNDARY_SCHEMA, CHANNEL_SOURCE_SCHEMA, DECISION_KINDS,
    _context, _digest, _freeze, _legal, _sequence, _token,
    fingerprint_decision_channel_prefix, fingerprint_decision_contract_reference,
    materialize_offline_decision_point,
)


SOURCE_SCHEMA = "session-decision-opportunity-source-v1"
_CHANNELS = frozenset({"actor_first_person", "simulator_input"})


@dataclass(frozen=True, slots=True)
class SessionBoundDecisionOpportunityBoundarySource:
    """Own a source-local prefix and immutable certificates for one actor."""

    session_id: str
    battle_id: str
    source_id: str
    channel: str
    actor: Mapping[str, Any]
    _events: list[Mapping[str, Any]] = field(default_factory=list, init=False, repr=False, compare=False)
    _event_ids: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _opportunities: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (not all(_token(value) for value in (self.session_id, self.battle_id, self.source_id))
                or self.channel not in _CHANNELS or not _actor(self.actor, self.session_id)):
            raise ValueError("invalid_session_decision_opportunity_source")
        object.__setattr__(self, "actor", _freeze(self.actor))

    @classmethod
    def create(
        cls, *, session_id: str, battle_id: str, source_id: str,
        channel: str, actor: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if not all(_token(value) for value in (session_id, battle_id, source_id)):
            return _result("rejected", "source_identity_invalid")
        if channel not in _CHANNELS:
            return _result("rejected", "source_channel_invalid")
        if not _actor(actor, session_id):
            return _result("rejected", "source_actor_invalid")
        source = cls(session_id, battle_id, source_id, channel, _freeze(actor))
        return {"status": "source_ready", "schema_version": SOURCE_SCHEMA, "source": source}

    def admit_channel_event(
        self, *, captured_session_id: str, source_event_id: str, source_event_fingerprint: str,
    ) -> Mapping[str, Any]:
        """Append an opaque evidence marker under this source's own sequence."""
        if captured_session_id != self.session_id:
            return _result("rejected", "stale_or_foreign_session")
        if not _token(source_event_id) or not _digest(source_event_fingerprint):
            return _result("rejected", "source_event_reference_invalid")
        existing = self._event_ids.get(source_event_id)
        if existing is not None:
            if existing["payload"]["source_event_fingerprint"] != source_event_fingerprint:
                return _result("rejected", "conflicting_source_event")
            return _freeze({"status": "duplicate", "schema_version": SOURCE_SCHEMA, "event": existing})
        sequence = len(self._events) + 1
        event = _freeze({
            "sequence": sequence, "available_at_sequence": sequence,
            "session_id": self.session_id, "channel": self.channel,
            "event_kind": "channel_evidence_marker",
            "payload": {"source_event_id": source_event_id, "source_event_fingerprint": source_event_fingerprint},
        })
        self._events.append(event)
        self._event_ids[source_event_id] = event
        return _freeze({"status": "admitted", "schema_version": SOURCE_SCHEMA, "event": event})

    def capture_opportunity(
        self, *, captured_session_id: str, opportunity_id: str,
        actor: Mapping[str, Any], decision_kind: str, turn_number: int,
        simultaneity_group_id: str, context_reference: Mapping[str, Any],
        legal_action_set: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Pin the current prefix before any command or resolution is needed."""
        if captured_session_id != self.session_id:
            return _result("rejected", "stale_or_foreign_session")
        if not _token(opportunity_id):
            return _result("rejected", "opportunity_id_invalid")
        if not _actor(actor, self.session_id) or actor != self.actor:
            return _result("rejected", "foreign_actor")
        if decision_kind not in DECISION_KINDS or not _sequence(turn_number) or not _token(simultaneity_group_id):
            return _result("rejected", "opportunity_boundary_invalid")
        if not _context(context_reference):
            return _result("rejected", "context_reference_invalid")
        if not _legal(legal_action_set):
            return _result("rejected", "legal_action_set_invalid")
        # Freeze before hashing so caller mutation cannot change pinned evidence.
        context = _freeze(context_reference)
        legal = _freeze({
            "status": legal_action_set["status"],
            "action_ids": tuple(sorted(legal_action_set["action_ids"])),
        })
        prefix = tuple(self._events)
        cutoff = len(prefix)
        boundary_id = "decision-boundary:" + hashlib.sha256(
            f"{self.session_id}\x1f{self.battle_id}\x1f{self.source_id}\x1f{opportunity_id}".encode("utf-8")
        ).hexdigest()
        certificate = _freeze({
            "schema_version": BOUNDARY_SCHEMA,
            "source_id": self.source_id, "session_id": self.session_id,
            "battle_id": self.battle_id, "boundary_id": boundary_id,
            "simultaneity_group_id": simultaneity_group_id,
            "channel": self.channel, "actor": self.actor,
            "decision_kind": decision_kind, "turn_number": turn_number,
            "sequence_domain": "channel_event_sequence",
            "certified_runtime_fingerprint": None,
            "after_event_sequence": cutoff, "prefix_event_count": cutoff,
            "prefix_fingerprint": fingerprint_decision_channel_prefix(prefix),
            "context_fingerprint": fingerprint_decision_contract_reference(context),
            "legal_action_set_fingerprint": fingerprint_decision_contract_reference(legal),
        })
        source_snapshot = self._channel_snapshot(prefix)
        validated = materialize_offline_decision_point(
            boundary_certificate=certificate, channel_source=source_snapshot,
            context_reference=context, legal_action_set=legal,
            post_boundary_end_sequence=cutoff,
        )
        if validated["status"] != "contract_validated":
            return _result("rejected", "emitted_boundary_contract_invalid")
        record = _freeze({
            "certificate": certificate, "channel_source": source_snapshot,
            "context_reference": context, "legal_action_set": legal,
        })
        old = self._opportunities.get(opportunity_id)
        if old is not None:
            if old != record:
                return _result("rejected", "conflicting_opportunity")
            return _freeze({"status": "duplicate", "schema_version": SOURCE_SCHEMA, **old})
        self._opportunities[opportunity_id] = record
        return _freeze({"status": "captured", "schema_version": SOURCE_SCHEMA, **record})

    def read_snapshot(self, *, captured_session_id: str) -> Mapping[str, Any]:
        if captured_session_id != self.session_id:
            return _result("rejected", "stale_or_foreign_session")
        records = tuple(sorted(self._opportunities.values(), key=lambda item: item["certificate"]["boundary_id"]))
        return _freeze({
            "status": "ready", "schema_version": SOURCE_SCHEMA,
            "session_id": self.session_id, "battle_id": self.battle_id,
            "source_id": self.source_id, "channel": self.channel, "actor": self.actor,
            "sequence_domain": "channel_event_sequence",
            "opportunity_scope": "admitted_to_this_source_only",
            "channel_source": self._channel_snapshot(tuple(self._events)),
            "opportunities": records,
        })

    def _channel_snapshot(self, events: tuple[Mapping[str, Any], ...]) -> Mapping[str, Any]:
        return _freeze({
            "schema_version": CHANNEL_SOURCE_SCHEMA,
            "source_id": self.source_id, "session_id": self.session_id,
            "battle_id": self.battle_id, "channel": self.channel,
            "sequence_domain": "channel_event_sequence",
            "channel_actor": self.actor, "events": events,
        })


def _actor(value: Any, session_id: str) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"session_id", "side", "slot_index", "pokemon_id"}
        and value.get("session_id") == session_id
        and value.get("side") in {"self", "opponent"}
        and _sequence(value.get("slot_index"), zero=True)
        and _token(value.get("pokemon_id"))
    )


def _result(status: str, reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": status, "schema_version": SOURCE_SCHEMA, "reason": reason})
