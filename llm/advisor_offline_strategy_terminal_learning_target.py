"""Episode-level terminal targets under the explicitly approved v1 policy."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import (
    _freeze,
    fingerprint_decision_contract_reference,
)
from llm.advisor_offline_strategy_episode_population_context import (
    SCHEMA_VERSION as POPULATION_SCHEMA,
    materialize_offline_strategy_episode_population_context,
    validates_materialized_population_context,
)
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)


SCHEMA_VERSION = "offline-strategy-terminal-learning-target-v1"
TARGET_POLICY_VERSION = "terminal-only-self-perspective-v1"
TARGET_SEMANTICS = "terminal_outcome_self_perspective"
ADMITTED_TERMINATION_CAUSES = frozenset({"all_fainted", "rules_based"})
_RESULT_VALUES = {"self": 1, "tie": 0, "opponent": -1}


def materialize_offline_strategy_terminal_learning_target(
    *, population_context: Mapping[str, Any],
    terminal_source: SessionBoundBattleTerminalOutcomeEvidenceSource,
) -> Mapping[str, Any]:
    """Attach one numeric terminal target to a reauthenticated episode record."""
    if (not isinstance(population_context, MappingProxyType)
            or population_context.get("schema_version") != POPULATION_SCHEMA
            or not validates_materialized_population_context(population_context)):
        return _failure("population_context_invalid")
    if not isinstance(terminal_source, SessionBoundBattleTerminalOutcomeEvidenceSource):
        return _failure("terminal_source_invalid")
    if population_context["session_id"] != terminal_source.session_id:
        return _failure("foreign_session")
    if population_context["battle_id"] != terminal_source.battle_id:
        return _failure("foreign_battle")

    sampling = population_context["sampling_context"]
    raw_sampling = {
        "collection_mode": sampling["collection_mode"],
        "competition_context": sampling["competition_context"],
        **{
            key: wrapper["value"] for key, wrapper in sampling.items()
            if isinstance(wrapper, Mapping) and wrapper["availability"] == "available"
        },
    }
    rebuilt = materialize_offline_strategy_episode_population_context(
        terminal_binding=population_context["base_terminal_binding"],
        terminal_source=terminal_source,
        session_id=population_context["session_id"],
        battle_id=population_context["battle_id"],
        rules_context=population_context["rules_context"],
        sampling_context=raw_sampling,
    )
    if rebuilt.get("status") not in {"resolved", "incomplete"} or rebuilt != population_context:
        return _failure("population_context_reauthentication_failed")

    binding = population_context["base_terminal_binding"]
    outcome = binding["terminal_outcome"]
    evidence = outcome["evidence"]
    if (binding["base_episode_status"] != "resolved" or binding["continuity_gaps"]
            or binding["status"] == "incomplete" and outcome["availability"] == "available"):
        target = {"availability": "unavailable", "reason": "episode_incomplete"}
    elif outcome["availability"] != "available":
        target = {"availability": "unavailable", "reason": outcome["reason"]}
    elif (binding["status"] != "resolved" or evidence is None
          or evidence["authority"] != "direct_final_declaration"
          or evidence["evidence_completeness"] != "final_declaration_observed"):
        target = {"availability": "unavailable", "reason": "terminal_declaration_not_authenticated"}
    elif evidence["termination_cause"] not in ADMITTED_TERMINATION_CAUSES:
        target = {"availability": "unavailable", "reason": "termination_cause_not_admitted_v1"}
    else:
        target = {
            "availability": "available",
            "value": _RESULT_VALUES[evidence["declared_result"]],
            "semantics": TARGET_SEMANTICS,
        }

    identity = {
        "context_binding_id": population_context["context_binding_id"],
        "episode_terminal_binding_id": binding["binding_id"],
        "terminal_evidence_id": evidence["evidence_id"] if evidence is not None else None,
        "target_policy_version": TARGET_POLICY_VERSION,
    }
    return _freeze({
        "status": "materialized", "schema_version": SCHEMA_VERSION,
        "target_record_id": "offline-terminal-learning-target:" + fingerprint_decision_contract_reference(identity),
        "session_id": population_context["session_id"],
        "battle_id": population_context["battle_id"],
        "context_binding_id": population_context["context_binding_id"],
        "episode_terminal_binding_id": binding["binding_id"],
        "target_policy_version": TARGET_POLICY_VERSION,
        "target_semantics": TARGET_SEMANTICS,
        "target": target,
        "raw_terminal_outcome": outcome,
        "base_population_context": population_context,
    })


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
