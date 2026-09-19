"""Exact target-side Fling consequence for empty-intrinsic resist Berries."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_type_resist_empty_intrinsic_berry import (
    resolve_canonical_fling_type_resist_empty_intrinsic_berry,
)
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
    assess_fling_berry_target_intrinsic_on_eat_readiness,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-fling-type-resist-empty-intrinsic-berry-target-effect-authority-v1"
DETACHED_SCHEMA_VERSION = "detached-fling-type-resist-empty-intrinsic-berry-target-effect-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_EAT_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_SUPPORT = "fling_type_resist_empty_intrinsic_berry_target_effect_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    fling_execution_authority: Mapping[str, Any],
    source_leaf: Mapping[str, Any],
    berry_eat_item_interaction_authority: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    base = _base(strategy_d0, fling_execution_authority, actor, target)
    if isinstance(base, str):
        return _result("rejected", base, {})
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)

    family = resolve_canonical_fling_type_resist_empty_intrinsic_berry(base["item_id"])
    if family.get("status") != "resolved":
        return _result(
            "rejected" if family.get("status") == "rejected" else "unsupported",
            family.get("reason", "fling_type_resist_berry_family_unavailable"),
            base,
        )
    if (
        fling_execution_authority.get("fling_type_resist_empty_intrinsic_berry_support")
        != _SUPPORT
        or fling_execution_authority.get(
            "fling_type_resist_empty_intrinsic_berry_authority"
        ) != family
    ):
        return _result(
            "rejected",
            "fling_type_resist_berry_execution_family_binding_mismatch",
            {**base, "berry_family_authority": deepcopy(family)},
        )

    leaf_binding = _source_leaf_binding(source_leaf, base)
    if isinstance(leaf_binding, str):
        return _result(
            "rejected", leaf_binding,
            {**base, "berry_family_authority": deepcopy(family)},
        )

    interaction_error = _interaction_error(
        berry_eat_item_interaction_authority,
        base=base,
        source_leaf_id=source_leaf["leaf_id"],
    )
    common = {
        **base,
        "berry_family_authority": deepcopy(family),
        "source_leaf_id": source_leaf["leaf_id"],
        "source_leaf_binding": deepcopy(leaf_binding),
        "berry_eat_item_interaction_authority": deepcopy(
            dict(berry_eat_item_interaction_authority)
        ),
    }
    if interaction_error is not None:
        return _result(
            _status(berry_eat_item_interaction_authority),
            interaction_error,
            common,
        )

    outcome = berry_eat_item_interaction_authority.get("outcome")
    if outcome == "post_hit_target_eat_not_reached":
        return _terminal(
            "not_applicable",
            berry_eat_item_interaction_authority.get(
                "reason", "fling_berry_target_eat_not_reached"
            ),
            common,
        )
    if (
        outcome != "post_hit_target_eat_item_dispatched"
        or berry_eat_item_interaction_authority.get("target_eat_occurred") is not True
        or berry_eat_item_interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return _result(
            "rejected",
            "fling_type_resist_berry_eat_item_prerequisite_invalid",
            common,
        )

    readiness = assess_fling_berry_target_eat_item_consequence_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {
        **common,
        "target_eat_item_consequence_readiness": deepcopy(readiness),
    }
    if readiness.get("status") != "resolved" or readiness.get("readiness") != "ready":
        status = readiness.get("status")
        if status not in {"incomplete", "rejected"}:
            status = "rejected"
        return _result(
            status,
            readiness.get(
                "reason", "fling_type_resist_berry_target_eat_item_consequence_not_ready"
            ),
            common,
        )
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {
        **common,
        "target_intrinsic_on_eat_readiness": deepcopy(intrinsic),
    }
    if intrinsic.get("status") != "resolved":
        status = intrinsic.get("status")
        if status not in {"incomplete", "rejected"}:
            status = "rejected"
        return _result(
            status,
            intrinsic.get(
                "reason",
                "fling_type_resist_berry_target_intrinsic_on_eat_unavailable",
            ),
            common,
        )
    if intrinsic.get("readiness") not in {
        "executes", "suppressed_by_target_klutz",
    }:
        return _result(
            "rejected",
            "fling_type_resist_berry_target_intrinsic_on_eat_state_invalid",
            common,
        )

    return _terminal(
        "no_intrinsic_target_effect",
        "pinned_empty_intrinsic_berry_on_eat",
        common,
        intrinsic_hp_change=0,
        intrinsic_major_condition_change="none",
        intrinsic_stage_change="none",
        intrinsic_item_change="none",
        intrinsic_type_change="none",
        intrinsic_field_change="none",
        intrinsic_action_order_change="none",
    )


def materialize_detached_fling_type_resist_empty_intrinsic_berry_target_effect(
    *, authority: Mapping[str, Any],
) -> dict[str, Any]:
    if not _authority_shape(authority):
        return {
            "status": "rejected",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "reason": "fling_type_resist_empty_intrinsic_berry_target_effect_authority_invalid",
        }
    return {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": "no_intrinsic_target_effect",
        "item_id": authority["item_id"],
        "actor": deepcopy(authority["actor"]),
        "target": deepcopy(authority["target"]),
        "intrinsic_hp_change": 0,
        "intrinsic_major_condition_change": "none",
        "intrinsic_stage_change": "none",
        "intrinsic_item_change": "none",
        "intrinsic_type_change": "none",
        "intrinsic_field_change": "none",
        "intrinsic_action_order_change": "none",
        "authority": deepcopy(dict(authority)),
        "provenance": "detached_authenticated_fling_type_resist_empty_intrinsic_berry_v1",
    }


def validate_detached_fling_type_resist_empty_intrinsic_berry_target_effect(
    *,
    consequence: Any,
    source_leaf: Mapping[str, Any],
    expected_target: Mapping[str, Any],
) -> bool:
    if (
        not isinstance(consequence, Mapping)
        or consequence.get("status") != "resolved"
        or consequence.get("schema_version") != DETACHED_SCHEMA_VERSION
        or consequence.get("outcome") != "no_intrinsic_target_effect"
        or consequence.get("target") != dict(expected_target)
        or consequence.get("provenance")
        != "detached_authenticated_fling_type_resist_empty_intrinsic_berry_v1"
    ):
        return False
    authority = consequence.get("authority")
    if (
        not _authority_shape(authority)
        or authority.get("target") != dict(expected_target)
        or authority.get("source_leaf_id") != source_leaf.get("leaf_id")
        or authority.get("action_id") != source_leaf.get("candidate_id")
        or consequence.get("item_id") != authority.get("item_id")
        or consequence.get("actor") != authority.get("actor")
    ):
        return False
    leaf_binding = authority.get("source_leaf_binding")
    consequences = source_leaf.get("consequences")
    provenance = source_leaf.get("provenance")
    if (
        not isinstance(leaf_binding, Mapping)
        or not isinstance(consequences, Mapping)
        or not isinstance(provenance, Mapping)
        or leaf_binding.get("leaf_id") != source_leaf.get("leaf_id")
        or leaf_binding.get("candidate_id") != source_leaf.get("candidate_id")
        or leaf_binding.get("hit_state") != source_leaf.get("hit_state")
        or leaf_binding.get("source_hit_context") != consequences.get("source_hit_context")
        or leaf_binding.get("target_final_hp") != consequences.get("target_final_hp")
        or leaf_binding.get("target_ko") != consequences.get("target_ko")
    ):
        return False
    expected_provenance = leaf_binding.get("provenance")
    if not isinstance(expected_provenance, Mapping) or any(
        provenance.get(key) != expected_provenance.get(key)
        for key in expected_provenance
    ):
        return False
    if any(
        consequence.get(key) != expected
        for key, expected in (
            ("intrinsic_hp_change", 0),
            ("intrinsic_major_condition_change", "none"),
            ("intrinsic_stage_change", "none"),
            ("intrinsic_item_change", "none"),
            ("intrinsic_type_change", "none"),
            ("intrinsic_field_change", "none"),
            ("intrinsic_action_order_change", "none"),
        )
    ):
        return False
    forbidden = {
        "heal_amount", "hypothetical_target_condition",
        "hypothetical_target_condition_removal", "hypothetical_target_stage",
        "target_item_after", "target_type_after", "field_after",
    }
    return forbidden.isdisjoint(consequence)


def _base(
    d0: Any, execution: Any, actor: Any, target: Any,
) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    if not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return "fling_type_resist_berry_owner_identity_invalid"
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or active.get(actor["side"]) != dict(actor)
        or active.get(target["side"]) != dict(target)
        or d0.get("decision_owner") != dict(actor)
    ):
        return "fling_type_resist_berry_owner_binding_invalid"
    if (
        not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("actor") != dict(actor)
        or execution.get("target") != dict(target)
        or execution.get("move_id") != "fling"
        or not isinstance(execution.get("action_id"), str)
    ):
        return "fling_type_resist_berry_execution_authority_invalid"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_type_resist_berry_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if (
        not isinstance(item, Mapping)
        or item.get("status") != "known"
        or not isinstance(item.get("value"), str)
        or not item["value"]
    ):
        return "fling_type_resist_berry_item_identity_unknown"
    return {
        "schema_version": SCHEMA_VERSION,
        **deepcopy(expected),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": execution["action_id"],
        "move_id": "fling",
        "item_id": item["value"],
        "fling_execution_authority": deepcopy(dict(execution)),
    }


def _source_leaf_binding(
    value: Any, base: Mapping[str, Any],
) -> dict[str, Any] | str:
    if (
        not isinstance(value, Mapping)
        or value.get("candidate_id") != base["action_id"]
        or not isinstance(value.get("leaf_id"), str)
    ):
        return "fling_type_resist_berry_source_leaf_invalid"
    provenance = value.get("provenance")
    consequences = value.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping):
        return "fling_type_resist_berry_source_leaf_invalid"
    expected = (
        "session_id", "source_runtime_fingerprint",
        "source_branch_fingerprint", "decision_owner",
    )
    if any(provenance.get(key) != base.get(key) for key in expected):
        return "fling_type_resist_berry_source_leaf_binding_mismatch"
    if (
        provenance.get("attacker") != base["actor"]
        or provenance.get("target") != base["target"]
        or provenance.get("move_id") != "fling"
        or provenance.get("fling_execution_authority")
        != base["fling_execution_authority"]
    ):
        return "fling_type_resist_berry_source_leaf_identity_mismatch"
    return {
        "leaf_id": value["leaf_id"],
        "candidate_id": value["candidate_id"],
        "hit_state": value.get("hit_state"),
        "source_hit_context": deepcopy(consequences.get("source_hit_context")),
        "target_final_hp": consequences.get("target_final_hp"),
        "target_ko": consequences.get("target_ko"),
        "provenance": {
            key: deepcopy(provenance.get(key))
            for key in (
                "session_id", "source_runtime_fingerprint",
                "source_branch_fingerprint", "decision_owner",
                "attacker", "target", "move_id", "fling_execution_authority",
            )
        },
    }


def _interaction_error(
    value: Any, *, base: Mapping[str, Any], source_leaf_id: str,
) -> str | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != _EAT_SCHEMA:
        return "fling_type_resist_berry_eat_item_authority_invalid"
    if value.get("status") != "resolved":
        return value.get(
            "reason", "fling_type_resist_berry_eat_item_authority_unresolved"
        )
    if (
        value.get("phase") != "post_hit_target_berry_interaction"
        or value.get("actor") != base["actor"]
        or value.get("target") != base["target"]
        or value.get("action_id") != base["action_id"]
        or value.get("item_id") != base["item_id"]
        or value.get("fling_execution_authority") != base["fling_execution_authority"]
        or any(
            value.get(key) != base.get(key)
            for key in (
                "session_id", "source_runtime_fingerprint",
                "source_branch_fingerprint", "decision_owner",
            )
        )
    ):
        return "fling_type_resist_berry_eat_item_authority_binding_mismatch"
    source_hit = value.get("source_hit")
    if (
        not isinstance(source_hit, Mapping)
        or source_hit.get("source_leaf_id") != source_leaf_id
    ):
        return "fling_type_resist_berry_eat_item_source_leaf_mismatch"
    return None


def _authority_shape(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("status") != "resolved"
        or value.get("outcome") != "no_intrinsic_target_effect"
        or value.get("provenance")
        != "strict_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_v1"
    ):
        return False
    family = resolve_canonical_fling_type_resist_empty_intrinsic_berry(
        value.get("item_id")
    )
    interaction = value.get("berry_eat_item_interaction_authority")
    readiness = assess_fling_berry_target_eat_item_consequence_readiness(
        interaction
    )
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(
        interaction
    )
    execution = value.get("fling_execution_authority")
    leaf_binding = value.get("source_leaf_binding")
    expected = {
        "session_id": value.get("session_id"),
        "source_runtime_fingerprint": value.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": value.get("source_branch_fingerprint"),
        "decision_owner": value.get("decision_owner"),
    }
    return (
        family.get("status") == "resolved"
        and value.get("berry_family_authority") == family
        and isinstance(execution, Mapping)
        and execution.get("schema_version") == _EXECUTION_SCHEMA
        and execution.get("status") == "resolved"
        and execution.get("outcome") == "ready_throw"
        and execution.get("fling_type_resist_empty_intrinsic_berry_support") == _SUPPORT
        and execution.get("fling_type_resist_empty_intrinsic_berry_authority") == family
        and execution.get("actor") == value.get("actor")
        and execution.get("target") == value.get("target")
        and execution.get("action_id") == value.get("action_id")
        and execution.get("user_item_before", {}).get("value") == value.get("item_id")
        and execution.get("resolved_base_power") == 10
        and all(execution.get(key) == expected[key] for key in expected)
        and isinstance(interaction, Mapping)
        and interaction.get("schema_version") == _EAT_SCHEMA
        and interaction.get("status") == "resolved"
        and interaction.get("outcome") == "post_hit_target_eat_item_dispatched"
        and interaction.get("actor") == value.get("actor")
        and interaction.get("target") == value.get("target")
        and interaction.get("action_id") == value.get("action_id")
        and interaction.get("item_id") == value.get("item_id")
        and interaction.get("fling_execution_authority") == execution
        and interaction.get("source_hit", {}).get("source_leaf_id") == value.get("source_leaf_id")
        and all(interaction.get(key) == expected[key] for key in expected)
        and isinstance(leaf_binding, Mapping)
        and leaf_binding.get("leaf_id") == value.get("source_leaf_id")
        and leaf_binding.get("candidate_id") == value.get("action_id")
        and readiness.get("status") == "resolved"
        and readiness.get("readiness") == "ready"
        and value.get("target_eat_item_consequence_readiness") == readiness
        and intrinsic.get("status") == "resolved"
        and intrinsic.get("readiness") in {"executes", "suppressed_by_target_klutz"}
        and value.get("target_intrinsic_on_eat_readiness") == intrinsic
        and value.get("intrinsic_hp_change") == 0
        and value.get("intrinsic_major_condition_change") == "none"
        and value.get("intrinsic_stage_change") == "none"
        and value.get("intrinsic_item_change") == "none"
        and value.get("intrinsic_type_change") == "none"
        and value.get("intrinsic_field_change") == "none"
        and value.get("intrinsic_action_order_change") == "none"
    )


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value.get("slot_index"), bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _status(value: Any) -> str:
    if isinstance(value, Mapping) and value.get("status") in {
        "incomplete", "unsupported", "rejected",
    }:
        return value["status"]
    return "rejected"


def _terminal(
    outcome: str, reason: str, base: Mapping[str, Any], **extra: Any,
) -> dict[str, Any]:
    return {
        "status": "resolved",
        **deepcopy(dict(base)),
        "outcome": outcome,
        "reason": reason,
        **deepcopy(extra),
        "provenance": "strict_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_v1",
    }


def _result(
    status: str, reason: str, base: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
    }
