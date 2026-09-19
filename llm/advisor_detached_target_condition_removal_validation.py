"""Exact admission for detached target-condition removal markers.

Only explicitly maintained provenance families are accepted here.  A generic
known-none state or schema-version match is never sufficient.
"""
from __future__ import annotations

from typing import Any, Mapping

from advisor.canonical_fling_major_status_cure_berry import (
    resolve_canonical_fling_major_status_cure_berry,
)
from advisor.canonical_fling_lum_major_status_confusion_cure_berry import (
    resolve_canonical_fling_lum_major_status_confusion_cure_berry,
)
from llm.advisor_champions_confusion_progression import valid_confusion_progression


SCHEMA_VERSION = "detached-hypothetical-target-condition-removal-v1"
_BERRY_AUTHORITY_SCHEMA = "runtime-d0-fling-major-status-cure-berry-target-effect-authority-v1"
_LUM_AUTHORITY_SCHEMA = "runtime-d0-fling-lum-major-status-confusion-cure-target-effect-authority-v1"
_EAT_AUTHORITY_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"


def validate_detached_target_condition_removal(
    value: Any,
    *,
    source_leaf_id: Any,
    source_leaf: Mapping[str, Any] | None = None,
    expected_target: Mapping[str, Any] | None = None,
) -> bool:
    """Admit exactly Sparkling Aria or authenticated Fling cure-Berry removal."""
    if _sparkling_aria(value, source_leaf_id):
        return True
    if _fling_cure_berry(
        value,
        source_leaf_id=source_leaf_id,
        source_leaf=source_leaf,
        expected_target=expected_target,
    ):
        return True
    return _fling_lum_cure(
        value,
        source_leaf_id=source_leaf_id,
        source_leaf=source_leaf,
        expected_target=expected_target,
    )


def _sparkling_aria(value: Any, source_leaf_id: Any) -> bool:
    return isinstance(value, Mapping) and value == {
        "schema_version": SCHEMA_VERSION,
        "condition_before": "burn",
        "condition_removed": "burn",
        "condition_after": "none",
        "removal_trigger": "successful_damaging_hit_target_survives",
        "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1",
        "source_leaf_id": source_leaf_id,
    }


def _fling_cure_berry(
    value: Any,
    *,
    source_leaf_id: Any,
    source_leaf: Mapping[str, Any] | None,
    expected_target: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION:
        return False
    if value.get("provenance") != "fling_major_status_cure_berry_intrinsic_on_eat_v1":
        return False
    before = value.get("condition_before")
    if (
        not isinstance(before, str)
        or value.get("condition_removed") != before
        or value.get("condition_after") != "none"
        or value.get("removal_trigger") != "authenticated_fling_target_eat_then_eat_item"
        or value.get("source_leaf_id") != source_leaf_id
        or not isinstance(value.get("source_berry_item_id"), str)
        or not isinstance(value.get("source_fling_action_id"), str)
    ):
        return False
    authority = value.get("fling_major_status_cure_berry_target_effect_authority")
    if not isinstance(authority, Mapping):
        return False
    if (
        authority.get("schema_version") != _BERRY_AUTHORITY_SCHEMA
        or authority.get("status") != "resolved"
        or authority.get("outcome") != "applied_major_status_cure"
        or authority.get("condition_before") != before
        or authority.get("condition_after") != "none"
        or authority.get("source_leaf_id") != source_leaf_id
        or authority.get("item_id") != value.get("source_berry_item_id")
        or authority.get("action_id") != value.get("source_fling_action_id")
    ):
        return False
    target = authority.get("target")
    actor = authority.get("actor")
    if not isinstance(target, Mapping) or not isinstance(actor, Mapping) or actor.get("side") == target.get("side"):
        return False
    if expected_target is not None and target != dict(expected_target):
        return False

    canonical = resolve_canonical_fling_major_status_cure_berry(authority.get("item_id"))
    if canonical.get("status") != "resolved" or authority.get("berry_family_authority") != canonical:
        return False
    if before not in set(canonical.get("removable_conditions", ())):
        return False

    execution = authority.get("fling_execution_authority")
    if (
        not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("move_id") != "fling"
        or execution.get("action_id") != authority.get("action_id")
        or execution.get("actor") != actor
        or execution.get("target") != target
        or execution.get("user_item_before", {}).get("value") != authority.get("item_id")
    ):
        return False

    interaction = authority.get("berry_eat_item_interaction_authority")
    if (
        not isinstance(interaction, Mapping)
        or interaction.get("schema_version") != _EAT_AUTHORITY_SCHEMA
        or interaction.get("status") != "resolved"
        or interaction.get("phase") != "post_hit_target_berry_interaction"
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
        or interaction.get("actor") != actor
        or interaction.get("target") != target
        or interaction.get("item_id") != authority.get("item_id")
        or interaction.get("action_id") != authority.get("action_id")
        or interaction.get("fling_execution_authority") != execution
        or interaction.get("source_hit", {}).get("source_leaf_id") != source_leaf_id
    ):
        return False

    current = authority.get("current_condition_authority")
    if (
        not isinstance(current, Mapping)
        or current.get("status") != "resolved"
        or current.get("schema_version") != "runtime-current-condition-authority-v1"
        or current.get("owner") != target
        or current.get("condition", {}).get("status") != "known_present"
        or current.get("condition", {}).get("condition") != before
    ):
        return False

    leaf_binding = authority.get("source_leaf_binding")
    if not _leaf_binding_valid(
        leaf_binding,
        source_leaf_id=source_leaf_id,
        action_id=authority.get("action_id"),
        actor=actor,
        target=target,
        execution=execution,
        authority=authority,
    ):
        return False
    if source_leaf is not None and not _source_leaf_matches(source_leaf, leaf_binding):
        return False

    binding_keys = (
        "session_id",
        "source_runtime_fingerprint",
        "source_branch_fingerprint",
        "decision_owner",
    )
    return all(
        authority.get(key) == execution.get(key) == interaction.get(key)
        for key in binding_keys
    )


def _fling_lum_cure(
    value: Any,
    *,
    source_leaf_id: Any,
    source_leaf: Mapping[str, Any] | None,
    expected_target: Mapping[str, Any] | None,
) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("provenance") != "fling_lum_intrinsic_on_eat_major_status_removal_v1"
    ):
        return False
    before = value.get("condition_before")
    if (
        before not in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
        or value.get("condition_removed") != before
        or value.get("condition_after") != "none"
        or value.get("removal_trigger") != "authenticated_fling_target_eat_then_eat_item"
        or value.get("source_berry_item_id") != "lum-berry"
        or value.get("source_leaf_id") != source_leaf_id
        or not isinstance(value.get("source_fling_action_id"), str)
    ):
        return False
    authority = value.get("fling_lum_major_status_confusion_cure_target_effect_authority")
    if (
        not isinstance(authority, Mapping)
        or authority.get("schema_version") != _LUM_AUTHORITY_SCHEMA
        or authority.get("status") != "resolved"
        or authority.get("outcome") not in {
            "applied_major_status_cure",
            "applied_major_status_and_confusion_cure",
        }
        or authority.get("condition_before") != before
        or authority.get("condition_after") != "none"
        or authority.get("source_leaf_id") != source_leaf_id
        or authority.get("item_id") != "lum-berry"
        or authority.get("action_id") != value.get("source_fling_action_id")
        or authority.get("provenance")
        != "strict_runtime_d0_fling_lum_status_confusion_cure_target_effect_v1"
    ):
        return False
    target, actor = authority.get("target"), authority.get("actor")
    if not isinstance(target, Mapping) or not isinstance(actor, Mapping) or actor.get("side") == target.get("side"):
        return False
    if expected_target is not None and target != dict(expected_target):
        return False
    canonical = resolve_canonical_fling_lum_major_status_confusion_cure_berry("lum-berry")
    if (
        canonical.get("status") != "resolved"
        or authority.get("berry_family_authority") != canonical
        or before not in set(canonical.get("removable_conditions", ()))
    ):
        return False
    execution = authority.get("fling_execution_authority")
    if (
        not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("move_id") != "fling"
        or execution.get("action_id") != authority.get("action_id")
        or execution.get("actor") != actor
        or execution.get("target") != target
        or execution.get("user_item_before", {}).get("value") != "lum-berry"
        or execution.get("resolved_base_power") != 10
        or execution.get("fling_lum_major_status_confusion_cure_support")
        != "fling_lum_major_status_confusion_cure_target_effect_v1"
        or execution.get("fling_lum_major_status_confusion_cure_berry_authority") != canonical
        or any(
            execution.get(key) is not None
            for key in (
                "fling_major_status_cure_berry_support",
                "fling_type_resist_empty_intrinsic_berry_support",
                "fling_persim_confusion_cure_berry_support",
            )
        )
    ):
        return False
    interaction = authority.get("berry_eat_item_interaction_authority")
    if (
        not isinstance(interaction, Mapping)
        or interaction.get("schema_version") != _EAT_AUTHORITY_SCHEMA
        or interaction.get("status") != "resolved"
        or interaction.get("phase") != "post_hit_target_berry_interaction"
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
        or interaction.get("actor") != actor
        or interaction.get("target") != target
        or interaction.get("item_id") != "lum-berry"
        or interaction.get("action_id") != authority.get("action_id")
        or interaction.get("fling_execution_authority") != execution
        or interaction.get("source_hit", {}).get("source_leaf_id") != source_leaf_id
    ):
        return False
    current = authority.get("current_condition_authority")
    if (
        not isinstance(current, Mapping)
        or current.get("status") != "resolved"
        or current.get("schema_version") != "runtime-current-condition-authority-v1"
        or current.get("owner") != target
        or current.get("condition", {}).get("status") != "known_present"
        or current.get("condition", {}).get("condition") != before
    ):
        return False
    confusion = authority.get("current_confusion_authority")
    if not isinstance(confusion, Mapping) or confusion.get("status") != "resolved" or confusion.get("owner") != target:
        return False
    confusion_state = confusion.get("state")
    if confusion_state == "confused":
        if (
            authority.get("outcome") != "applied_major_status_and_confusion_cure"
            or authority.get("confusion_before") != "confused"
            or authority.get("confusion_after") != "none"
            or authority.get("confusion_progression_before") != confusion.get("progression")
            or authority.get("confusion_progression_after") is not None
            or not valid_confusion_progression(confusion.get("progression"), target)
        ):
            return False
    elif confusion_state == "none":
        if (
            authority.get("outcome") != "applied_major_status_cure"
            or authority.get("confusion_before") != "none"
            or authority.get("confusion_after") != "none"
            or confusion.get("progression") is not None
            or authority.get("confusion_progression_before") is not None
            or authority.get("confusion_progression_after") is not None
        ):
            return False
    else:
        return False
    leaf_binding = authority.get("source_leaf_binding")
    if not _leaf_binding_valid(
        leaf_binding,
        source_leaf_id=source_leaf_id,
        action_id=authority.get("action_id"),
        actor=actor,
        target=target,
        execution=execution,
        authority=authority,
    ):
        return False
    if source_leaf is not None and not _source_leaf_matches(source_leaf, leaf_binding):
        return False
    return all(
        authority.get(key) == execution.get(key) == interaction.get(key)
        for key in (
            "session_id", "source_runtime_fingerprint",
            "source_branch_fingerprint", "decision_owner",
        )
    )


def _leaf_binding_valid(
    value: Any,
    *,
    source_leaf_id: Any,
    action_id: Any,
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    execution: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> bool:
    if not isinstance(value, Mapping):
        return False
    provenance = value.get("provenance")
    return (
        value.get("leaf_id") == source_leaf_id
        and value.get("candidate_id") == action_id
        and isinstance(provenance, Mapping)
        and provenance.get("attacker") == actor
        and provenance.get("target") == target
        and provenance.get("move_id") == "fling"
        and provenance.get("fling_execution_authority") == execution
        and all(
            provenance.get(key) == authority.get(key)
            for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
        )
    )


def _source_leaf_matches(leaf: Mapping[str, Any], binding: Mapping[str, Any]) -> bool:
    provenance = leaf.get("provenance")
    expected = binding.get("provenance")
    if not isinstance(provenance, Mapping) or not isinstance(expected, Mapping):
        return False
    return (
        leaf.get("leaf_id") == binding.get("leaf_id")
        and leaf.get("candidate_id") == binding.get("candidate_id")
        and leaf.get("hit_state") == binding.get("hit_state")
        and leaf.get("consequences", {}).get("source_hit_context") == binding.get("source_hit_context")
        and leaf.get("consequences", {}).get("target_final_hp") == binding.get("target_final_hp")
        and leaf.get("consequences", {}).get("target_ko") == binding.get("target_ko")
        and all(provenance.get(key) == expected.get(key) for key in expected)
    )
