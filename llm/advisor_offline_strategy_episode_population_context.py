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
from llm.advisor_offline_strategy_episode_dataset import materialize_offline_strategy_episode
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SCHEMA_VERSION as OUTCOME_SCHEMA,
    TERMINATION_CAUSES,
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


def validates_materialized_population_context(record: Any) -> bool:
    """Check detached identity and structure; live source retention is not encoded here."""
    if not _deep_read_only(record):
        return False
    try:
        expected_keys = {
            "status", "schema_version", "context_binding_id", "session_id", "battle_id",
            "episode_terminal_binding_id", "rules_context", "rules_context_fingerprint",
            "sampling_context", "sampling_context_fingerprint", "provenance", "base_terminal_binding",
        }
        if set(record) != expected_keys or record["schema_version"] != SCHEMA_VERSION:
            return False
        binding = record["base_terminal_binding"]
        if (not isinstance(binding, MappingProxyType) or binding.get("schema_version") != TERMINAL_BINDING_SCHEMA
                or binding.get("status") not in {"resolved", "incomplete"}
                or record["status"] != binding["status"]
                or record["session_id"] != binding.get("session_id")
                or record["battle_id"] != binding.get("battle_id")
                or record["episode_terminal_binding_id"] != binding.get("binding_id")):
            return False
        if not _valid_detached_terminal_binding(binding):
            return False
        rules = record["rules_context"]
        sampling = record["sampling_context"]
        if not _decision_context_valid(rules) or not _valid_normalized_sampling(sampling):
            return False
        rules_fp = fingerprint_decision_contract_reference(rules)
        sampling_fp = fingerprint_decision_contract_reference(sampling)
        if rules_fp != record["rules_context_fingerprint"] or sampling_fp != record["sampling_context_fingerprint"]:
            return False
        if record["provenance"] != {
            "binding_basis": binding["binding_basis"],
            "metadata_authority": "explicit_caller_supplied_unverified",
            "decision_context_alignment": "not_proven_by_episode_transition_records",
        }:
            return False
        identity = {
            "session_id": record["session_id"], "battle_id": record["battle_id"],
            "episode_terminal_binding_id": binding["binding_id"],
            "rules_context_fingerprint": rules_fp, "sampling_context_fingerprint": sampling_fp,
        }
        return record["context_binding_id"] == (
            "offline-episode-population-context:" + fingerprint_decision_contract_reference(identity)
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _valid_normalized_sampling(value: Any) -> bool:
    if not isinstance(value, MappingProxyType) or set(value) != {
        "collection_mode", "competition_context", *OPTIONAL_FIELDS,
    }:
        return False
    raw = {"collection_mode": value["collection_mode"], "competition_context": value["competition_context"]}
    for field in OPTIONAL_FIELDS:
        wrapper = value[field]
        if not isinstance(wrapper, MappingProxyType):
            return False
        if wrapper == {"availability": "unavailable"}:
            continue
        if set(wrapper) != {"availability", "value"} or wrapper["availability"] != "available":
            return False
        raw[field] = wrapper["value"]
    return _sampling(raw) == value


def _valid_detached_terminal_binding(binding: Mapping[str, Any]) -> bool:
    if set(binding) != {
        "status", "schema_version", "binding_id", "episode_id", "session_id", "battle_id",
        "binding_basis", "terminal_source", "base_episode_status", "base_episode_completeness",
        "continuity_gaps", "terminal_outcome", "base_episode",
    }:
        return False
    episode = binding.get("base_episode")
    if not isinstance(episode, MappingProxyType):
        return False
    rebuilt_episode = materialize_offline_strategy_episode(episode.get("transitions"))
    if rebuilt_episode.get("status") not in {"resolved", "incomplete"} or rebuilt_episode != episode:
        return False
    outcome, source = binding.get("terminal_outcome"), binding.get("terminal_source")
    if (not isinstance(outcome, MappingProxyType) or not isinstance(source, MappingProxyType)
            or set(source) != {"source_id", "source_kind"}
            or not _token(source["source_id"])
            or source["source_kind"] not in {"first_person_battle_stream", "simulator_output"}
            or binding.get("session_id") != episode["session_id"]
            or not _token(binding.get("battle_id"))
            or binding.get("episode_id") != episode["episode_id"]
            or binding.get("base_episode_status") != episode["status"]
            or binding.get("base_episode_completeness") != episode["completeness"]
            or binding.get("continuity_gaps") != episode["continuity_gaps"]
            or binding.get("binding_basis") != "session_scoped_terminal_source"):
        return False
    evidence = outcome.get("evidence")
    if evidence is not None:
        if not _valid_detached_outcome_evidence(evidence, binding, source):
            return False
    available = evidence is not None and evidence["authority"] == "direct_final_declaration"
    if available:
        if outcome != {
            "availability": "available", "evidence": evidence,
            "declared_result": evidence["declared_result"],
            "termination_cause": evidence["termination_cause"],
            "evidence_completeness": evidence["evidence_completeness"],
            "evidence_id": evidence["evidence_id"], "turn_number": evidence["turn_number"],
        }:
            return False
        if evidence["turn_number"] is not None and evidence["turn_number"] < episode["final_next_state"]["turn_number"]:
            return False
    elif evidence is None:
        if outcome != {"availability": "unavailable", "reason": "terminal_declaration_not_observed", "evidence": None}:
            return False
    elif outcome != {"availability": "unavailable", "reason": "stream_ended_without_declaration", "evidence": evidence}:
        return False
    expected_status = "resolved" if available and episode["status"] == "resolved" else "incomplete"
    identity = {
        "episode_id": episode["episode_id"],
        "evidence_id": evidence["evidence_id"] if evidence is not None else None,
        "binding_basis": binding["binding_basis"],
        "session_id": episode["session_id"], "battle_id": binding["battle_id"],
        "source_id": source["source_id"], "source_kind": source["source_kind"],
    }
    return (binding.get("status") == expected_status
            and binding.get("binding_id") == "offline-episode-terminal-binding:" + fingerprint_decision_contract_reference(identity))


def _valid_detached_outcome_evidence(
    evidence: Any, binding: Mapping[str, Any], source: Mapping[str, Any],
) -> bool:
    if (not isinstance(evidence, MappingProxyType) or evidence.get("schema_version") != OUTCOME_SCHEMA
            or evidence.get("session_id") != binding["session_id"]
            or evidence.get("battle_id") != binding["battle_id"]
            or evidence.get("source_id") != source["source_id"]
            or evidence.get("source_kind") != source["source_kind"]):
        return False
    authority = evidence.get("authority")
    if authority == "direct_final_declaration":
        if set(evidence) != {
            "schema_version", "evidence_id", "session_id", "battle_id", "source_id",
            "source_kind", "authority", "source_terminal_event_id", "source_event_sequence",
            "turn_number", "declared_result", "termination_cause", "raw_termination_cause",
            "source_cause_event_id", "evidence_completeness", "battle_terminal",
        }:
            return False
        if (evidence.get("battle_terminal") is not True
                or evidence.get("evidence_completeness") != "final_declaration_observed"
                or evidence.get("declared_result") not in {"self", "opponent", "tie"}
                or evidence.get("termination_cause") not in TERMINATION_CAUSES
                or not _token(evidence.get("source_terminal_event_id"))
                or (evidence["termination_cause"] != "unknown"
                    and not _token(evidence.get("source_cause_event_id")))):
            return False
        prefix = "battle-terminal:"
    elif authority == "direct_stream_end_marker":
        if set(evidence) != {
            "schema_version", "evidence_id", "session_id", "battle_id", "source_id",
            "source_kind", "authority", "source_stream_end_event_id", "source_event_sequence",
            "turn_number", "declared_result", "termination_cause", "evidence_completeness",
            "battle_terminal",
        }:
            return False
        if (evidence.get("battle_terminal") is not False
                or evidence.get("evidence_completeness") != "stream_ended_without_declaration"
                or evidence.get("declared_result") != "none_observed"
                or evidence.get("termination_cause") != "unknown"
                or not _token(evidence.get("source_stream_end_event_id"))):
            return False
        prefix = "stream-end:"
    else:
        return False
    if (not isinstance(evidence.get("source_event_sequence"), int)
            or isinstance(evidence["source_event_sequence"], bool)
            or evidence["source_event_sequence"] < 1):
        return False
    turn = evidence.get("turn_number")
    if turn is not None and (not isinstance(turn, int) or isinstance(turn, bool) or turn < 1):
        return False
    facts = {key: value for key, value in evidence.items() if key not in {"schema_version", "evidence_id"}}
    return evidence.get("evidence_id") == prefix + fingerprint_decision_contract_reference(facts)


def _deep_read_only(value: Any) -> bool:
    if isinstance(value, MappingProxyType):
        return all(_deep_read_only(item) for item in value.values())
    if isinstance(value, tuple):
        return all(_deep_read_only(item) for item in value)
    return value is None or type(value) in {str, int, float, bool}


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
