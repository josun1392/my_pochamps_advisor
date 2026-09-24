"""Per-decision semantic model inputs, separate from outcomes and evaluation."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_choice_outcome_example import (
    SCHEMA_VERSION as EXAMPLE_SCHEMA,
    materialize_offline_strategy_choice_outcome_example,
)
from llm.advisor_session_decision_public_battle_information import (
    PUBLIC_SURFACE_VERSION,
    SCHEMA_VERSION as PUBLIC_SCHEMA,
    SessionBoundDecisionPublicBattleInformationSource,
)


SCHEMA_VERSION = "offline-strategy-model-feature-semantics-v1"
LIMITATIONS = (
    "v1_supported_public_surface_only",
    "external_actor_visibility_not_independently_verified",
    "predictive_strategy_feature_join_not_proven",
    "observational_terminal_outcome_not_causal_action_value",
)


def validates_detached_semantic_feature_record(value: Any) -> bool:
    """Check detached structure and identity; live source retention is not reproven."""
    if not isinstance(value, MappingProxyType) or set(value) != {
        "status", "schema_version", "feature_record_id", "feature_availability",
        "model_features", "semantic_feature_fingerprint", "label", "evaluation_partition", "audit",
    } or value["status"] != "materialized" or value["schema_version"] != SCHEMA_VERSION:
        return False
    if not _deeply_frozen(value) or value["evaluation_partition"] not in {"train", "validation", "test"}:
        return False
    availability = value["feature_availability"]
    label = value["label"]
    audit = value["audit"]
    if (not isinstance(availability, Mapping) or availability.get("availability") not in {"available", "unavailable"}
            or not isinstance(label, Mapping) or label.get("availability") not in {"available", "unavailable"}
            or not isinstance(audit, Mapping) or set(audit) != {
                "choice_example_id", "public_information_id", "evaluation_split_id",
                "choice_example_schema", "public_information_schema", "public_surface_version", "limitations",
            }):
        return False
    if (not all(isinstance(audit[key], str) and audit[key] for key in (
        "choice_example_id", "public_information_id", "evaluation_split_id",
    )) or audit["choice_example_schema"] != EXAMPLE_SCHEMA
            or audit["public_information_schema"] != PUBLIC_SCHEMA
            or audit["public_surface_version"] != PUBLIC_SURFACE_VERSION
            or audit["limitations"] != LIMITATIONS):
        return False
    if label["availability"] == "available":
        if (set(label) != {"availability", "value", "semantics"}
                or type(label["value"]) is not int or label["value"] not in {-1, 0, 1}
                or label["semantics"] != "terminal_outcome_self_perspective"):
            return False
    elif (set(label) != {"availability", "reason"}
          or not isinstance(label["reason"], str) or not label["reason"]):
        return False
    features = value["model_features"]
    fingerprint = value["semantic_feature_fingerprint"]
    if availability["availability"] == "available":
        if (set(availability) != {"availability"} or label["availability"] != "available"
                or not isinstance(features, MappingProxyType) or set(features) != {
                    "rules_and_decision", "public_battle", "actor_private", "exact_legal_actions", "selected_action",
                } or not isinstance(fingerprint, str)
                or fingerprint != fingerprint_decision_contract_reference(features)
                or _contains_leakage_key(features)):
            return False
    elif (set(availability) != {"availability", "reason"}
          or not isinstance(availability["reason"], str) or not availability["reason"]
          or features is not None or fingerprint is not None):
        return False
    expected = "offline-semantic-feature:" + fingerprint_decision_contract_reference({
        "schema_version": SCHEMA_VERSION, "example_id": audit["choice_example_id"],
        "public_information_id": audit["public_information_id"],
        "semantic_feature_fingerprint": fingerprint,
    })
    return value["feature_record_id"] == expected


def _deeply_frozen(value: Any) -> bool:
    if isinstance(value, MappingProxyType):
        return all(isinstance(key, str) and _deeply_frozen(item) for key, item in value.items())
    if isinstance(value, tuple):
        return all(_deeply_frozen(item) for item in value)
    return value is None or type(value) in {str, int, float, bool}


def _contains_leakage_key(value: Any) -> bool:
    forbidden = {
        "label", "target", "terminal_target", "declared_result", "termination_cause",
        "evaluation_partition", "evaluation_split_id", "session_id", "battle_id",
        "boundary_id", "decision_id", "example_id", "command_id", "evidence_id",
        "source_id", "private_information_id", "public_information_id", "collection_mode",
        "competition_context", "source_dataset_id", "set_id", "team_cluster_id",
        "self_player_cluster_id", "opponent_player_cluster_id", "fingerprint",
    }
    if isinstance(value, Mapping):
        return any(key in forbidden or "fingerprint" in key or _contains_leakage_key(item)
                   for key, item in value.items())
    if isinstance(value, tuple):
        return any(_contains_leakage_key(item) for item in value)
    return False


def materialize_offline_strategy_model_feature_semantics(
    *, choice_example: Mapping[str, Any], public_information: Mapping[str, Any],
    public_source: SessionBoundDecisionPublicBattleInformationSource,
    private_source: Any, terminal_source: Any, evaluation_split: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Reauthenticate a choice and its pre-command public facts before projection."""
    if (not isinstance(public_source, SessionBoundDecisionPublicBattleInformationSource)
            or not isinstance(choice_example, MappingProxyType)
            or choice_example.get("schema_version") != EXAMPLE_SCHEMA
            or choice_example.get("status") != "materialized"):
        return _failure("choice_example_invalid")
    if not isinstance(choice_example.get("evidence"), Mapping):
        return _failure("choice_example_invalid")
    evidence = choice_example["evidence"]
    if not all(key in evidence for key in ("opportunity", "private_information", "submitted_command", "terminal_target")):
        return _failure("choice_example_invalid")
    opportunity = evidence["opportunity"]
    if not isinstance(opportunity, Mapping):
        return _failure("choice_example_invalid")
    rebuilt = materialize_offline_strategy_choice_outcome_example(
        opportunity_record=opportunity,
        opportunity_source=public_source.opportunity_source,
        private_information=evidence["private_information"], private_source=private_source,
        submitted_command=evidence["submitted_command"], command_source=public_source.command_source,
        terminal_target=evidence["terminal_target"], terminal_source=terminal_source,
        evaluation_split=evaluation_split,
    )
    if rebuilt.get("status") != "materialized" or rebuilt != choice_example:
        return _failure("choice_example_reauthentication_failed")
    if not public_source.authenticates(public_information, opportunity):
        return _failure("public_information_not_authenticated")
    boundary = opportunity["certificate"]
    if (public_information.get("schema_version") != PUBLIC_SCHEMA
            or public_information.get("public_surface_version") != PUBLIC_SURFACE_VERSION
            or any(public_information.get(key) != boundary[key] for key in (
                "session_id", "battle_id", "actor", "boundary_id", "decision_kind",
                "turn_number", "prefix_fingerprint", "context_fingerprint", "channel",
            ))):
        return _failure("public_information_binding_invalid")
    if any(public_information.get(key) != choice_example[key] for key in (
        "session_id", "battle_id", "actor", "boundary_id", "decision_kind", "turn_number", "channel",
    )):
        return _failure("public_information_choice_mismatch")
    return _project_authenticated_semantics(choice_example=choice_example,
                                            public_information=public_information)


def materialize_offline_strategy_model_feature_semantics_from_archive(
    *, ingestion: Mapping[str, Any], boundary_id: str,
    choice_example: Mapping[str, Any], evaluation_split: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Project the archived pre-command public facts after detached revalidation."""
    from llm.advisor_c6_durable_archive_offline_ingestion import validates_c6_ingested_archive
    from llm.advisor_offline_strategy_choice_outcome_example import (
        materialize_offline_strategy_choice_outcome_example_from_archive,
    )
    if not validates_c6_ingested_archive(ingestion):
        return _failure("archive_ingestion_invalid")
    rebuilt = materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingestion, boundary_id=boundary_id, evaluation_split=evaluation_split)
    if rebuilt.get("status") != "materialized" or rebuilt != choice_example:
        return _failure("choice_example_revalidation_failed")
    rows = [row for row in ingestion["boundaries"] if row["boundary_id"] == boundary_id]
    if len(rows) != 1:
        return _failure("boundary_not_ingested")
    return _project_authenticated_semantics(
        choice_example=choice_example, public_information=rows[0]["public_information"])


def _project_authenticated_semantics(
    *, choice_example: Mapping[str, Any], public_information: Mapping[str, Any],
) -> Mapping[str, Any]:
    if any(public_information.get(key) != choice_example[key] for key in (
        "session_id", "battle_id", "actor", "boundary_id", "decision_kind", "turn_number", "channel",
    )):
        return _failure("public_information_choice_mismatch")
    public = public_information["public_snapshot"]
    private = choice_example["decision_information"]["actor_private_snapshot"]
    actor = choice_example["actor"]
    own_public = public["active"]["self"]
    own_private = [row for row in private["own_roster"]
                   if row["slot_index"] == actor["slot_index"] and row["pokemon_id"] == actor["pokemon_id"]]
    if (own_public["slot_index"] != actor["slot_index"]
            or own_public["pokemon_id"] != actor["pokemon_id"] or len(own_private) != 1):
        return _failure("public_private_active_identity_mismatch")

    availability = choice_example["example_availability"]
    target = choice_example["outcome"]["terminal_target"]
    model_features = None
    feature_fingerprint = None
    if availability["availability"] == "available":
        action = choice_example["selected_choice"]["canonical_action"]
        if action is None or target["availability"] != "available":
            return _failure("available_example_inconsistent")
        if action["kind"] == "attack":
            semantic_action = {"kind": "attack", "move_id": action["move_id"]}
        elif action["kind"] == "switch":
            semantic_action = {"kind": "switch", "incoming_pokemon_id": action["incoming_pokemon_id"]}
        else:
            return _failure("selected_action_kind_invalid")
        # Session and party-slot identifiers certify the source and command
        # resolution; the semantic identities are the active Pokémon IDs.
        public_features = {
            "active": {
                side: {key: value for key, value in public["active"][side].items()
                       if key not in {"session_id", "slot_index"}}
                for side in ("self", "opponent")
            },
            "field": public["field"], "sides": public["sides"],
            "opponent_revealed_moves": public["opponent_revealed_moves"],
        }
        private_rows = []
        for row in private["own_roster"]:
            moves = tuple(sorted(({
                "move_id": move["move_id"], "current_pp": move["current_pp"],
            } for move in row["moves"]), key=fingerprint_decision_contract_reference))
            private_rows.append({
                "pokemon_id": row["pokemon_id"],
                "move_scope": {"status": row["move_scope"]["status"]},
                "moves": moves,
                "known_item": row["known_item"], "current_ability": row["current_ability"],
                "current_level": row["current_level"], "current_final_stats": row["current_final_stats"],
            })
        private_features = {
            "roster_scope": {"status": private["roster_scope"]["status"]},
            "own_roster": tuple(sorted(private_rows, key=fingerprint_decision_contract_reference)),
        }
        pre = choice_example["decision_information"]["public_pre_boundary"]
        model_features = _freeze({
            "rules_and_decision": {
                **pre["context_reference"], "decision_kind": choice_example["decision_kind"],
                "turn_number": choice_example["turn_number"],
            },
            "public_battle": public_features,
            "actor_private": private_features,
            "exact_legal_actions": choice_example["decision_information"]["exact_legal_action_set"],
            "selected_action": semantic_action,
        })
        feature_fingerprint = fingerprint_decision_contract_reference(model_features)
    elif availability["availability"] != "unavailable":
        return _failure("example_availability_invalid")

    record_id = fingerprint_decision_contract_reference({
        "schema_version": SCHEMA_VERSION, "example_id": choice_example["example_id"],
        "public_information_id": public_information["public_information_id"],
        "semantic_feature_fingerprint": feature_fingerprint,
    })
    return _freeze({
        "status": "materialized", "schema_version": SCHEMA_VERSION,
        "feature_record_id": "offline-semantic-feature:" + record_id,
        "feature_availability": availability,
        "model_features": model_features,
        "semantic_feature_fingerprint": feature_fingerprint,
        "label": target,
        "evaluation_partition": choice_example["evaluation"]["partition"],
        "audit": {
            "choice_example_id": choice_example["example_id"],
            "public_information_id": public_information["public_information_id"],
            "evaluation_split_id": choice_example["evaluation"]["evaluation_split_id"],
            "choice_example_schema": EXAMPLE_SCHEMA, "public_information_schema": PUBLIC_SCHEMA,
            "public_surface_version": PUBLIC_SURFACE_VERSION, "limitations": LIMITATIONS,
        },
    })


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
