"""Strict detached authority for Flinged single-major-status cure Berries."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_major_status_cure_berry import (
    resolve_canonical_fling_major_status_cure_berry,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-fling-major-status-cure-berry-target-effect-authority-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_EAT_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    fling_execution_authority: Mapping[str, Any],
    source_leaf: Mapping[str, Any],
    berry_eat_item_interaction_authority: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one intrinsic cure after the already-authenticated Fling Eat boundary."""
    base = _base(strategy_d0, fling_execution_authority, actor, target)
    if isinstance(base, str):
        return _result("rejected", base, {})
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)

    family = resolve_canonical_fling_major_status_cure_berry(base["item_id"])
    if family.get("status") != "resolved":
        return _result(
            "rejected" if family.get("status") == "rejected" else "unsupported",
            family.get("reason", "fling_status_cure_berry_family_unavailable"),
            base,
        )
    if fling_execution_authority.get("fling_major_status_cure_berry_authority") != family:
        return _result("rejected", "fling_status_cure_berry_execution_family_binding_mismatch", base)

    leaf_binding = _source_leaf_binding(source_leaf, base)
    if isinstance(leaf_binding, str):
        return _result("rejected", leaf_binding, {**base, "berry_family_authority": family})

    interaction_error = _interaction_error(
        berry_eat_item_interaction_authority,
        base=base,
        source_leaf_id=source_leaf["leaf_id"],
    )
    common = {
        **base,
        "berry_family_authority": deepcopy(family),
        "source_leaf_id": source_leaf["leaf_id"],
        "source_leaf_binding": leaf_binding,
        "berry_eat_item_interaction_authority": deepcopy(dict(berry_eat_item_interaction_authority)),
    }
    if interaction_error is not None:
        return _result(
            _status(berry_eat_item_interaction_authority),
            interaction_error,
            common,
        )

    interaction_outcome = berry_eat_item_interaction_authority.get("outcome")
    if interaction_outcome == "post_hit_target_eat_not_reached":
        return _terminal(
            "not_applicable",
            berry_eat_item_interaction_authority.get("reason", "fling_berry_target_eat_not_reached"),
            common,
            condition_before="not_evaluated",
            condition_after="not_evaluated",
        )
    if (
        interaction_outcome != "post_hit_target_eat_item_dispatched"
        or berry_eat_item_interaction_authority.get("target_eat_occurred") is not True
        or berry_eat_item_interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return _result("rejected", "fling_status_cure_berry_eat_item_prerequisite_invalid", common)

    current = freeze_runtime_current_condition_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        owner=target,
    )
    if current.get("status") != "resolved":
        return _result(
            _status(current),
            current.get("reason", "fling_status_cure_berry_current_condition_unavailable"),
            common,
        )
    condition = current.get("condition")
    common = {**common, "current_condition_authority": deepcopy(current)}
    if not isinstance(condition, Mapping) or condition.get("status") == "unknown":
        return _result("incomplete", "fling_status_cure_berry_target_condition_unknown", common)
    if condition.get("status") == "known_none":
        return _terminal(
            "no_transition_healthy",
            "target_already_has_no_major_condition",
            common,
            condition_before="none",
            condition_after="none",
        )
    if condition.get("status") != "known_present" or not isinstance(condition.get("condition"), str):
        return _result("rejected", "fling_status_cure_berry_current_condition_authority_invalid", common)

    before = condition["condition"]
    if before in set(family["removable_conditions"]):
        return _terminal(
            "applied_major_status_cure",
            "pinned_berry_intrinsic_on_eat_cures_matching_major_condition",
            common,
            condition_before=before,
            condition_after="none",
        )
    return _terminal(
        "no_transition_nonmatching_condition",
        "berry_intrinsic_cure_does_not_match_current_condition",
        common,
        condition_before=before,
        condition_after=before,
    )


def materialize_detached_fling_major_status_cure_berry_target_effect(
    *,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize only the condition transition authorized above."""
    if not _authority_shape(authority):
        return {
            "status": "rejected",
            "schema_version": "detached-fling-major-status-cure-berry-target-effect-v1",
            "reason": "fling_status_cure_berry_target_effect_authority_invalid",
        }
    result = {
        "status": "resolved",
        "schema_version": "detached-fling-major-status-cure-berry-target-effect-v1",
        "outcome": authority["outcome"],
        "item_id": authority["item_id"],
        "actor": deepcopy(authority["actor"]),
        "target": deepcopy(authority["target"]),
        "condition_before": authority.get("condition_before"),
        "condition_after": authority.get("condition_after"),
        "authority": deepcopy(dict(authority)),
        "provenance": "detached_authenticated_fling_major_status_cure_berry_v1",
    }
    if authority["outcome"] == "applied_major_status_cure":
        result["hypothetical_target_condition_removal"] = {
            "schema_version": "detached-hypothetical-target-condition-removal-v1",
            "condition_before": authority["condition_before"],
            "condition_removed": authority["condition_before"],
            "condition_after": "none",
            "removal_trigger": "authenticated_fling_target_eat_then_eat_item",
            "source_berry_item_id": authority["item_id"],
            "source_fling_action_id": authority["action_id"],
            "source_leaf_id": authority["source_leaf_id"],
            "fling_major_status_cure_berry_target_effect_authority": deepcopy(dict(authority)),
            "provenance": "fling_major_status_cure_berry_intrinsic_on_eat_v1",
        }
    return result


def validate_detached_fling_major_status_cure_berry_no_transition(
    *,
    consequence: Any,
    expected_target: Mapping[str, Any],
    source_leaf: Mapping[str, Any] | None = None,
    source_leaf_id: Any = None,
) -> bool:
    """Authenticate one exact nonmatching-condition Berry no-transition.

    This does not create a cure.  It only proves that the target's already
    known major condition survived an authenticated Fling Berry Eat unchanged.
    """
    if (
        not isinstance(consequence, Mapping)
        or consequence.get("status") != "resolved"
        or consequence.get("schema_version") != "detached-fling-major-status-cure-berry-target-effect-v1"
        or consequence.get("outcome") != "no_transition_nonmatching_condition"
        or consequence.get("provenance") != "detached_authenticated_fling_major_status_cure_berry_v1"
        or not isinstance(expected_target, Mapping)
    ):
        return False
    leaf_id = source_leaf.get("leaf_id") if isinstance(source_leaf, Mapping) else source_leaf_id
    if not isinstance(leaf_id, str) or not leaf_id:
        return False
    authority = consequence.get("authority")
    if (
        not isinstance(authority, Mapping)
        or not _authority_shape(authority)
        or authority.get("outcome") != "no_transition_nonmatching_condition"
        or consequence.get("item_id") != authority.get("item_id")
        or consequence.get("actor") != authority.get("actor")
        or consequence.get("target") != authority.get("target")
        or authority.get("target") != dict(expected_target)
        or consequence.get("condition_before") != authority.get("condition_before")
        or consequence.get("condition_after") != authority.get("condition_after")
    ):
        return False
    before = authority.get("condition_before")
    if (
        before not in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
        or authority.get("condition_after") != before
        or consequence.get("hypothetical_target_condition_removal") is not None
    ):
        return False

    family = resolve_canonical_fling_major_status_cure_berry(authority.get("item_id"))
    if (
        family.get("status") != "resolved"
        or authority.get("berry_family_authority") != family
        or before in set(family.get("removable_conditions", ()))
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
        or execution.get("actor") != authority.get("actor")
        or execution.get("target") != authority.get("target")
        or execution.get("user_item_before", {}).get("value") != authority.get("item_id")
        or execution.get("fling_major_status_cure_berry_authority") != family
        or execution.get("fling_major_status_cure_berry_support") != "fling_major_status_cure_berry_target_effect_v1"
    ):
        return False

    base = {
        "schema_version": SCHEMA_VERSION,
        "session_id": authority.get("session_id"),
        "source_runtime_fingerprint": authority.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": authority.get("source_branch_fingerprint"),
        "decision_owner": authority.get("decision_owner"),
        "actor": authority.get("actor"),
        "target": authority.get("target"),
        "action_id": authority.get("action_id"),
        "move_id": "fling",
        "item_id": authority.get("item_id"),
        "fling_execution_authority": execution,
    }
    if any(
        execution.get(key) != authority.get(key)
        for key in (
            "session_id",
            "source_runtime_fingerprint",
            "source_branch_fingerprint",
            "decision_owner",
        )
    ):
        return False
    binding = authority.get("source_leaf_binding")
    binding_provenance = binding.get("provenance") if isinstance(binding, Mapping) else None
    if (
        not isinstance(binding, Mapping)
        or binding.get("leaf_id") != leaf_id
        or binding.get("candidate_id") != authority.get("action_id")
        or not isinstance(binding_provenance, Mapping)
        or binding_provenance.get("attacker") != authority.get("actor")
        or binding_provenance.get("target") != authority.get("target")
        or binding_provenance.get("move_id") != "fling"
        or binding_provenance.get("fling_execution_authority") != execution
        or any(
            binding_provenance.get(key) != authority.get(key)
            for key in (
                "session_id",
                "source_runtime_fingerprint",
                "source_branch_fingerprint",
                "decision_owner",
            )
        )
        or authority.get("source_leaf_id") != leaf_id
    ):
        return False
    if isinstance(source_leaf, Mapping):
        exact_binding = _source_leaf_binding(source_leaf, base)
        if isinstance(exact_binding, str) or exact_binding != binding:
            return False

    interaction = authority.get("berry_eat_item_interaction_authority")
    if (
        _interaction_error(
            interaction,
            base=base,
            source_leaf_id=leaf_id,
        )
        is not None
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
    ):
        return False

    current = authority.get("current_condition_authority")
    return (
        isinstance(current, Mapping)
        and current.get("status") == "resolved"
        and current.get("owner") == dict(expected_target)
        and current.get("condition", {}).get("status") == "known_present"
        and current.get("condition", {}).get("condition") == before
    )


def _base(
    d0: Any,
    execution: Any,
    actor: Any,
    target: Any,
) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    if not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return "fling_status_cure_berry_owner_identity_invalid"
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or d0.get("decision_owner") != dict(actor)
        or active.get(actor["side"]) != dict(actor)
        or active.get(target["side"]) != dict(target)
    ):
        return "fling_status_cure_berry_owner_binding_invalid"
    if not isinstance(execution, Mapping) or execution.get("schema_version") != _EXECUTION_SCHEMA:
        return "fling_status_cure_berry_execution_authority_invalid"
    if (
        execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("move_id") != "fling"
        or execution.get("actor") != dict(actor)
        or execution.get("target") != dict(target)
        or not isinstance(execution.get("action_id"), str)
    ):
        return "fling_status_cure_berry_execution_identity_mismatch"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_status_cure_berry_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if (
        not isinstance(item, Mapping)
        or item.get("status") != "known"
        or not isinstance(item.get("value"), str)
        or not item["value"]
    ):
        return "fling_status_cure_berry_item_identity_unknown"
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


def _source_leaf_binding(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if (
        not isinstance(value, Mapping)
        or value.get("candidate_id") != base["action_id"]
        or not isinstance(value.get("leaf_id"), str)
    ):
        return "fling_status_cure_berry_source_leaf_invalid"
    provenance = value.get("provenance")
    consequences = value.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping):
        return "fling_status_cure_berry_source_leaf_invalid"
    expected = (
        "session_id",
        "source_runtime_fingerprint",
        "source_branch_fingerprint",
        "decision_owner",
    )
    if any(provenance.get(key) != base.get(key) for key in expected):
        return "fling_status_cure_berry_source_leaf_binding_mismatch"
    if (
        provenance.get("attacker") != base["actor"]
        or provenance.get("target") != base["target"]
        or provenance.get("move_id") != "fling"
        or provenance.get("fling_execution_authority") != base["fling_execution_authority"]
    ):
        return "fling_status_cure_berry_source_leaf_identity_mismatch"
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
                "session_id",
                "source_runtime_fingerprint",
                "source_branch_fingerprint",
                "decision_owner",
                "attacker",
                "target",
                "move_id",
                "fling_execution_authority",
            )
        },
    }


def _interaction_error(
    value: Any,
    *,
    base: Mapping[str, Any],
    source_leaf_id: str,
) -> str | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != _EAT_SCHEMA:
        return "fling_status_cure_berry_eat_item_authority_invalid"
    if value.get("status") != "resolved":
        return value.get("reason", "fling_status_cure_berry_eat_item_authority_unresolved")
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
                "session_id",
                "source_runtime_fingerprint",
                "source_branch_fingerprint",
                "decision_owner",
            )
        )
    ):
        return "fling_status_cure_berry_eat_item_authority_binding_mismatch"
    if value.get("source_hit", {}).get("source_leaf_id") != source_leaf_id:
        return "fling_status_cure_berry_eat_item_source_leaf_mismatch"
    return None


def _authority_shape(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("status") != "resolved"
        or value.get("outcome")
        not in {
            "applied_major_status_cure",
            "no_transition_nonmatching_condition",
            "no_transition_healthy",
            "not_applicable",
        }
    ):
        return False
    if value.get("outcome") == "applied_major_status_cure":
        family = value.get("berry_family_authority")
        return (
            isinstance(family, Mapping)
            and family.get("status") == "resolved"
            and value.get("condition_before") in set(family.get("removable_conditions", ()))
            and value.get("condition_after") == "none"
        )
    return True


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value.get("slot_index"), bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _status(value: Any) -> str:
    if isinstance(value, Mapping) and value.get("status") in {"incomplete", "unsupported", "rejected"}:
        return value["status"]
    return "rejected"


def _terminal(
    outcome: str,
    reason: str,
    base: Mapping[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    return {
        "status": "resolved",
        **deepcopy(dict(base)),
        "outcome": outcome,
        "reason": reason,
        **deepcopy(extra),
        "provenance": "strict_runtime_d0_fling_major_status_cure_berry_target_effect_v1",
    }


def _result(
    status: str,
    reason: str,
    base: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
    }
