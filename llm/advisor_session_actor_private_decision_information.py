"""Direct pre-command own-side facts for a retained decision opportunity."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_offline_decision_point_provenance import _canonical, _freeze, _token
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource


SCHEMA_VERSION = "session-actor-private-decision-information-v1"
PRIVATE_SURFACE_VERSION = "actor-private-supported-singles-surface-v1"
FINAL_STATS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
_SCOPE_STATUSES = frozenset({"exact", "partial", "unknown"})


@dataclass(frozen=True, slots=True)
class SessionBoundActorPrivateDecisionInformationSource:
    """Retain at most one directly supplied private snapshot per opportunity."""

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
            raise ValueError("invalid_actor_private_information_source")

    @classmethod
    def create(
        cls, *, opportunity_source: SessionBoundDecisionOpportunityBoundarySource,
        command_source: SessionBoundSubmittedCommandEvidenceSource, source_id: str,
    ) -> Mapping[str, Any]:
        if not isinstance(opportunity_source, SessionBoundDecisionOpportunityBoundarySource):
            return _failure("opportunity_source_invalid")
        if (not isinstance(command_source, SessionBoundSubmittedCommandEvidenceSource)
                or command_source.opportunity_source is not opportunity_source):
            return _failure("command_source_mismatch")
        if opportunity_source.actor["side"] != "self":
            return _failure("foreign_actor_side")
        if not _token(source_id):
            return _failure("private_source_id_invalid")
        return {"status": "source_ready", "schema_version": SCHEMA_VERSION,
                "source": cls(opportunity_source, command_source, source_id)}

    @property
    def session_id(self) -> str:
        return self.opportunity_source.session_id

    @property
    def battle_id(self) -> str:
        return self.opportunity_source.battle_id

    def admit_private_snapshot(
        self, *, captured_session_id: str, captured_battle_id: str,
        opportunity_record: Mapping[str, Any], actor: Mapping[str, Any],
        source_private_event_id: str, private_snapshot: Mapping[str, Any],
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
        if not _token(source_private_event_id):
            return _failure("source_private_event_id_invalid")
        normalized = _normalize_snapshot(private_snapshot, boundary["actor"])
        if normalized is None:
            return _failure("private_snapshot_invalid")
        fingerprint = hashlib.sha256(_canonical(normalized)).hexdigest()
        identity = {
            "session_id": self.session_id, "battle_id": self.battle_id,
            "actor": boundary["actor"], "boundary_id": boundary["boundary_id"],
            "opportunity_source_id": self.opportunity_source.source_id,
            "private_source_id": self.source_id,
            "source_private_event_id": source_private_event_id,
            "private_snapshot_fingerprint": fingerprint,
            "private_surface_version": PRIVATE_SURFACE_VERSION,
        }
        record = _freeze({
            "status": "direct_pre_command", "schema_version": SCHEMA_VERSION,
            "private_information_id": "actor-private-information:" + hashlib.sha256(_canonical(identity)).hexdigest(),
            "private_surface_version": PRIVATE_SURFACE_VERSION,
            "source_provenance": "direct_pre_command_actor_private_admission",
            "source_private_event_id": source_private_event_id,
            "session_id": self.session_id, "battle_id": self.battle_id,
            "opportunity_source_id": self.opportunity_source.source_id,
            "bound_command_source_id": self.command_source.source_id,
            "private_source_id": self.source_id,
            "channel": boundary["channel"], "actor": boundary["actor"],
            "boundary_id": boundary["boundary_id"],
            "decision_kind": boundary["decision_kind"],
            "turn_number": boundary["turn_number"],
            "prefix_fingerprint": boundary["prefix_fingerprint"],
            "context_fingerprint": boundary["context_fingerprint"],
            "private_snapshot_fingerprint": fingerprint,
            "completeness": _completeness(normalized),
            "private_snapshot": normalized,
        })
        old = self._records.get(boundary["boundary_id"])
        if old is not None:
            if old != record:
                return _failure("conflicting_private_snapshot")
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
            "private_source_id": self.source_id,
            "channel": self.opportunity_source.channel,
            "actor": self.opportunity_source.actor,
            "private_surface_version": PRIVATE_SURFACE_VERSION,
            "completeness_scope": "v1_supported_own_side_surface_only",
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


def _normalize_snapshot(value: Any, actor: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != {"roster_scope", "own_roster"}:
        return None
    scope = _scope(value["roster_scope"], "slot_indices", 0, 5)
    rows = value["own_roster"]
    if scope is None or not isinstance(rows, (list, tuple)):
        return None
    if scope["status"] == "exact" and actor["slot_index"] not in scope["slot_indices"]:
        return None
    normalized = []
    seen = set()
    for row in rows:
        if (not isinstance(row, Mapping) or not {"slot_index", "pokemon_id"} <= set(row)
                or set(row) - {"slot_index", "pokemon_id", "move_scope", "moves", "known_item",
                               "current_ability", "current_level", "current_final_stats"}):
            return None
        slot = row["slot_index"]
        if not _slot(slot, 0, 5) or slot in seen or slot not in scope["slot_indices"] or not _token(row["pokemon_id"]):
            return None
        if slot == actor["slot_index"] and row["pokemon_id"] != actor["pokemon_id"]:
            return None
        seen.add(slot)
        moves = row.get("moves", [])
        if not isinstance(moves, (list, tuple)):
            return None
        raw_move_scope = row.get("move_scope", {
            "status": "partial", "move_slots": [
                move.get("move_slot") if isinstance(move, Mapping) else None for move in moves
            ],
        })
        move_scope = _scope(raw_move_scope, "move_slots", 1, 4)
        if move_scope is None:
            return None
        normalized_moves = []
        move_seen = set()
        for move in moves:
            if (not isinstance(move, Mapping) or "move_slot" not in move
                    or set(move) - {"move_slot", "move_id", "current_pp"}):
                return None
            move_slot = move["move_slot"]
            if not _slot(move_slot, 1, 4) or move_slot in move_seen or move_slot not in move_scope["move_slots"]:
                return None
            move_seen.add(move_slot)
            move_id = _simple(move.get("move_id"), "token")
            pp = _simple(move.get("current_pp"), "pp")
            if move_id is None or pp is None:
                return None
            normalized_moves.append({"move_slot": move_slot, "move_id": move_id, "current_pp": pp})
        item = _field(row.get("known_item"), "item")
        ability = _field(row.get("current_ability"), "token")
        level = _field(row.get("current_level"), "level")
        raw_stats = row.get("current_final_stats", {})
        if item is None or ability is None or level is None or not isinstance(raw_stats, Mapping) or set(raw_stats) - set(FINAL_STATS):
            return None
        stats = {}
        for stat in FINAL_STATS:
            entry = _field(raw_stats.get(stat), "stat")
            if entry is None:
                return None
            stats[stat] = entry
        normalized.append({
            "slot_index": slot, "pokemon_id": row["pokemon_id"],
            "move_scope": move_scope, "moves": tuple(sorted(normalized_moves, key=lambda move: move["move_slot"])),
            "known_item": item, "current_ability": ability, "current_level": level,
            "current_final_stats": stats,
        })
    return {"roster_scope": scope, "own_roster": tuple(sorted(normalized, key=lambda row: row["slot_index"]))}


def _completeness(snapshot: Mapping[str, Any]) -> str:
    scope = snapshot["roster_scope"]
    rows = snapshot["own_roster"]
    if scope["status"] != "exact" or set(scope["slot_indices"]) != {row["slot_index"] for row in rows}:
        return "incomplete"
    for row in rows:
        move_scope = row["move_scope"]
        if (move_scope["status"] != "exact"
                or set(move_scope["move_slots"]) != {move["move_slot"] for move in row["moves"]}
                or any(move["move_id"]["availability"] != "available"
                       or move["current_pp"]["availability"] != "available" for move in row["moves"])
                or any(row[field]["availability"] != "available"
                       for field in ("known_item", "current_ability", "current_level"))
                or any(entry["availability"] != "available" for entry in row["current_final_stats"].values())):
            return "incomplete"
    return "complete_for_v1_supported_private_surface"


def _scope(value: Any, slots_key: str, low: int, high: int) -> dict[str, Any] | None:
    if (not isinstance(value, Mapping) or set(value) != {"status", slots_key}
            or not isinstance(value["status"], str) or value["status"] not in _SCOPE_STATUSES
            or not isinstance(value[slots_key], (list, tuple))):
        return None
    slots = value[slots_key]
    if any(not _slot(slot, low, high) for slot in slots) or len(set(slots)) != len(slots):
        return None
    if value["status"] == "exact" and not slots:
        return None
    return {"status": value["status"], slots_key: tuple(sorted(slots))}


def _field(value: Any, kind: str) -> dict[str, Any] | None:
    if value is None:
        return {"availability": "unavailable"}
    if not isinstance(value, Mapping):
        return None
    if value == {"availability": "unavailable"}:
        return {"availability": "unavailable"}
    if set(value) != {"availability", "value"} or value.get("availability") != "available":
        return None
    raw = value["value"]
    if kind == "item":
        valid = raw is None or _token(raw)
    elif kind == "token":
        valid = _token(raw)
    elif kind == "level":
        valid = isinstance(raw, int) and not isinstance(raw, bool) and 1 <= raw <= 100
    else:
        valid = isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1
    return {"availability": "available", "value": raw} if valid else None


def _simple(value: Any, kind: str) -> dict[str, Any] | None:
    if value is None:
        return {"availability": "unavailable"}
    if kind == "token" and _token(value):
        return {"availability": "available", "value": value}
    if kind == "pp" and isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return {"availability": "available", "value": value}
    return None


def _slot(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
