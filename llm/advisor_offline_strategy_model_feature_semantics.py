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
