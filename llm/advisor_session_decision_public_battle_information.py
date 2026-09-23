"""Direct actor-visible battle facts retained at a decision boundary.

This is historical channel evidence, not reducer, mechanics, or predictive truth.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_decision_point_provenance import _canonical, _freeze, _token
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource


SCHEMA_VERSION = "session-decision-public-battle-information-v1"
PUBLIC_SURFACE_VERSION = "decision-public-supported-singles-surface-v1"
STAT_STAGES = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")
CONDITIONS = frozenset({"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"})
WEATHER = frozenset({"none", "sun", "rain", "sandstorm", "snow"})
TERRAIN = frozenset({"none", "electric", "grassy", "psychic", "misty"})
_SIDES = frozenset({"self", "opponent"})


@dataclass(frozen=True, slots=True)
class SessionBoundDecisionPublicBattleInformationSource:
    """Retain one directly supplied, pre-command public snapshot per opportunity."""

    opportunity_source: SessionBoundDecisionOpportunityBoundarySource
    command_source: SessionBoundSubmittedCommandEvidenceSource
    source_id: str
    _records: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (not isinstance(self.opportunity_source, SessionBoundDecisionOpportunityBoundarySource)
                or not isinstance(self.command_source, SessionBoundSubmittedCommandEvidenceSource)
                or self.command_source.opportunity_source is not self.opportunity_source
                or self.opportunity_source.actor["side"] != "self"
                or not _token(self.source_id)):
            raise ValueError("invalid_decision_public_information_source")

    @classmethod
    def create(cls, *, opportunity_source: SessionBoundDecisionOpportunityBoundarySource,
               command_source: SessionBoundSubmittedCommandEvidenceSource, source_id: str) -> Mapping[str, Any]:
        if not isinstance(opportunity_source, SessionBoundDecisionOpportunityBoundarySource):
            return _failure("opportunity_source_invalid")
        if (not isinstance(command_source, SessionBoundSubmittedCommandEvidenceSource)
                or command_source.opportunity_source is not opportunity_source):
            return _failure("command_source_mismatch")
        if opportunity_source.actor["side"] != "self":
            return _failure("foreign_actor_side")
        if not _token(source_id):
            return _failure("public_source_id_invalid")
        return _freeze({"status": "source_ready", "schema_version": SCHEMA_VERSION,
                        "source": cls(opportunity_source, command_source, source_id)})

    @property
    def session_id(self) -> str:
        return self.opportunity_source.session_id

    @property
    def battle_id(self) -> str:
        return self.opportunity_source.battle_id

    def admit_public_snapshot(
        self, *, captured_session_id: str, captured_battle_id: str,
        opportunity_record: Mapping[str, Any], actor: Mapping[str, Any],
        source_public_event_id: str, public_snapshot: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if captured_session_id != self.session_id:
            return _failure("stale_or_foreign_session")
        if captured_battle_id != self.battle_id:
            return _failure("foreign_battle")
        opportunity = self._retained_opportunity(opportunity_record)
        if opportunity is None:
            return _failure("opportunity_not_retained_by_source")
        boundary = opportunity["certificate"]
        if actor != self.opportunity_source.actor or actor != boundary["actor"]:
            return _failure("foreign_actor")
        if not _token(source_public_event_id):
            return _failure("source_public_event_id_invalid")
        normalized = _normalize_snapshot(public_snapshot, boundary["actor"])
        if normalized is None:
            return _failure("public_snapshot_invalid")
        fingerprint = hashlib.sha256(_canonical(normalized)).hexdigest()
        identity = {
            "session_id": self.session_id, "battle_id": self.battle_id,
            "boundary_id": boundary["boundary_id"], "actor": boundary["actor"],
            "source_id": self.source_id, "source_public_event_id": source_public_event_id,
            "public_surface_version": PUBLIC_SURFACE_VERSION, "public_snapshot_fingerprint": fingerprint,
        }
        record = _freeze({
            "status": "direct_pre_command", "schema_version": SCHEMA_VERSION,
            "public_information_id": "decision-public-information:" + hashlib.sha256(_canonical(identity)).hexdigest(),
            "public_surface_version": PUBLIC_SURFACE_VERSION,
            "public_snapshot_fingerprint": fingerprint,
            "source_provenance": "direct_pre_command_public_admission",
            "source_public_event_id": source_public_event_id,
            "session_id": self.session_id, "battle_id": self.battle_id,
            "opportunity_source_id": self.opportunity_source.source_id,
            "bound_command_source_id": self.command_source.source_id,
            "public_source_id": self.source_id,
            "channel": boundary["channel"], "actor": boundary["actor"],
            "boundary_id": boundary["boundary_id"], "decision_kind": boundary["decision_kind"],
            "turn_number": boundary["turn_number"],
            "prefix_fingerprint": boundary["prefix_fingerprint"],
            "context_fingerprint": boundary["context_fingerprint"],
            "scope_limitation": "v1_supported_public_surface_only",
            "directness_limitation": "external_actor_visibility_not_independently_verified",
            "public_snapshot": normalized,
        })
        old = self._records.get(boundary["boundary_id"])
        if old is not None:
            if old != record:
                return _failure("conflicting_public_snapshot")
            return _freeze({"status": "duplicate", "schema_version": SCHEMA_VERSION, "evidence": old})
        current = self.opportunity_source.read_snapshot(captured_session_id=self.session_id)
        if len(current["channel_source"]["events"]) != boundary["prefix_event_count"]:
            return _failure("opportunity_prefix_advanced")
        commands = self.command_source.read_snapshot(captured_session_id=self.session_id)["command_evidence"]
        if any(command["boundary_id"] == boundary["boundary_id"] for command in commands):
            return _failure("command_already_admitted")
        self._records[boundary["boundary_id"]] = record
        return _freeze({"status": "admitted", "schema_version": SCHEMA_VERSION, "evidence": record})

    def authenticates(self, evidence: Any, opportunity_record: Mapping[str, Any]) -> bool:
        opportunity = self._retained_opportunity(opportunity_record)
        if opportunity is None or not isinstance(evidence, MappingProxyType):
            return False
        return self._records.get(opportunity["certificate"]["boundary_id"]) == evidence

    def read_snapshot(self, *, captured_session_id: str) -> Mapping[str, Any]:
        if captured_session_id != self.session_id:
            return _failure("stale_or_foreign_session")
        return _freeze({
            "status": "ready", "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id, "battle_id": self.battle_id,
            "opportunity_source_id": self.opportunity_source.source_id,
            "bound_command_source_id": self.command_source.source_id,
            "public_source_id": self.source_id, "channel": self.opportunity_source.channel,
            "actor": self.opportunity_source.actor,
            "public_surface_version": PUBLIC_SURFACE_VERSION,
            "scope_limitation": "v1_supported_public_surface_only",
            "directness_limitation": "external_actor_visibility_not_independently_verified",
            "evidence": tuple(self._records[key] for key in sorted(self._records)),
        })

    def _retained_opportunity(self, value: Any) -> Mapping[str, Any] | None:
        if not isinstance(value, MappingProxyType):
            return None
        certificate = value.get("certificate")
        if not isinstance(certificate, Mapping):
            return None
        snapshot = self.opportunity_source.read_snapshot(captured_session_id=self.session_id)
        matches = [item for item in snapshot["opportunities"]
                   if item["certificate"]["boundary_id"] == certificate.get("boundary_id")]
        if len(matches) != 1:
            return None
        retained = matches[0]
        return retained if all(value.get(key) == retained[key] for key in (
            "certificate", "channel_source", "context_reference", "legal_action_set",
        )) else None


def _normalize_snapshot(value: Any, actor: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != {"active", "field", "sides", "opponent_revealed_moves"}:
        return None
    active = value["active"]
    sides = value["sides"]
    field = value["field"]
    if not isinstance(active, Mapping) or set(active) != _SIDES or not isinstance(sides, Mapping) or set(sides) != _SIDES:
        return None
    if not isinstance(field, Mapping) or set(field) - {"weather", "terrain", "trick_room"}:
        return None
    normalized_active = {side: _active(active[side], actor, side) for side in sorted(_SIDES)}
    if any(row is None for row in normalized_active.values()):
        return None
    normalized_field = {key: _available(field.get(key), key) for key in ("weather", "terrain", "trick_room")}
    if any(entry is None for entry in normalized_field.values()):
        return None
    normalized_sides = {}
    for side in sorted(_SIDES):
        row = sides[side]
        if not isinstance(row, Mapping) or set(row) - {"tailwind"}:
            return None
        normalized_sides[side] = {"tailwind": _available(row.get("tailwind"), "tailwind")}
        if normalized_sides[side]["tailwind"] is None:
            return None
    revealed = value["opponent_revealed_moves"]
    if (not isinstance(revealed, Mapping) or set(revealed) != {"status", "move_ids"}
            or revealed["status"] not in ("exact", "partial", "unknown")
            or not isinstance(revealed["move_ids"], (list, tuple))):
        return None
    moves = revealed["move_ids"]
    if (any(not _token(move) for move in moves) or len(moves) != len(set(moves))
            or (revealed["status"] == "unknown" and moves)):
        return None
    return {"active": normalized_active, "field": normalized_field, "sides": normalized_sides,
            "opponent_revealed_moves": {"status": revealed["status"], "move_ids": tuple(sorted(moves))}}


def _active(value: Any, actor: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    allowed = {"session_id", "slot_index", "pokemon_id", "current_hp", "max_hp", "fainted", "condition", "stat_stages"}
    if (not isinstance(value, Mapping) or not {"session_id", "slot_index", "pokemon_id"} <= set(value)
            or set(value) - allowed or value["session_id"] != actor["session_id"]
            or not isinstance(value["slot_index"], int) or isinstance(value["slot_index"], bool)
            or not 0 <= value["slot_index"] <= 5 or not _token(value["pokemon_id"])):
        return None
    if side == "self" and (value["slot_index"] != actor["slot_index"] or value["pokemon_id"] != actor["pokemon_id"]):
        return None
    row = {key: _available(value.get(key), key) for key in ("current_hp", "max_hp", "fainted", "condition")}
    if any(entry is None for entry in row.values()):
        return None
    if (row["current_hp"]["availability"] == "available" and row["max_hp"]["availability"] == "available"
            and row["current_hp"]["value"] > row["max_hp"]["value"]):
        return None
    stages = value.get("stat_stages", {})
    if not isinstance(stages, Mapping) or set(stages) - set(STAT_STAGES):
        return None
    normalized_stages = {stat: _available(stages.get(stat), "stage") for stat in STAT_STAGES}
    if any(entry is None for entry in normalized_stages.values()):
        return None
    return {"session_id": value["session_id"], "slot_index": value["slot_index"],
            "pokemon_id": value["pokemon_id"], **row, "stat_stages": normalized_stages}


def _available(value: Any, kind: str) -> dict[str, Any] | None:
    if value is None or value == {"availability": "unavailable"}:
        return {"availability": "unavailable"}
    if not isinstance(value, Mapping) or set(value) != {"availability", "value"} or value.get("availability") != "available":
        return None
    raw = value["value"]
    if kind == "current_hp":
        valid = isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0
    elif kind == "max_hp":
        valid = isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1
    elif kind == "stage":
        valid = isinstance(raw, int) and not isinstance(raw, bool) and -6 <= raw <= 6
    elif kind == "condition":
        valid = isinstance(raw, str) and raw in CONDITIONS
    elif kind == "weather":
        valid = isinstance(raw, str) and raw in WEATHER
    elif kind == "terrain":
        valid = isinstance(raw, str) and raw in TERRAIN
    else:
        valid = isinstance(raw, bool)
    return {"availability": "available", "value": raw} if valid else None


def _failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
