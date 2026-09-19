"""Atomic target-side Lum Berry major-status + confusion cure after Fling Eat."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_lum_major_status_confusion_cure_berry import (
    resolve_canonical_fling_lum_major_status_confusion_cure_berry,
)
from llm.advisor_champions_confusion_progression import valid_confusion_progression
from llm.advisor_detached_target_condition_removal_validation import (
    validate_detached_target_condition_removal,
)
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-fling-lum-major-status-confusion-cure-target-effect-authority-v1"
DETACHED_SCHEMA_VERSION = "detached-fling-lum-major-status-confusion-cure-target-effect-v1"
CONFUSION_REMOVAL_SCHEMA_VERSION = "detached-hypothetical-target-confusion-removal-v1"
CONDITION_REMOVAL_SCHEMA_VERSION = "detached-hypothetical-target-condition-removal-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_EAT_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_SUPPORT = "fling_lum_major_status_confusion_cure_target_effect_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_MAJOR_CONDITIONS = {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
_OUTCOMES = {
    "applied_major_status_and_confusion_cure",
    "applied_major_status_cure",
    "applied_confusion_cure",
    "no_transition_no_curable_state",
}


def freeze_runtime_d0_fling_lum_major_status_confusion_cure_target_effect_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    fling_execution_authority: Mapping[str, Any],
    source_leaf: Mapping[str, Any],
    berry_eat_item_interaction_authority: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one atomic Lum intrinsic consequence after authenticated target Eat."""
    base = _base(strategy_d0, fling_execution_authority, actor, target)
    if isinstance(base, str):
        return _result("rejected", base, {})
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)

    family = resolve_canonical_fling_lum_major_status_confusion_cure_berry(base["item_id"])
    if family.get("status") != "resolved":
        return _result(
            "rejected" if family.get("status") == "rejected" else "unsupported",
            family.get("reason", "fling_lum_family_unavailable"),
            base,
        )
    if (
        fling_execution_authority.get("fling_lum_major_status_confusion_cure_support")
        != _SUPPORT
        or fling_execution_authority.get(
            "fling_lum_major_status_confusion_cure_berry_authority"
        ) != family
        or any(
            fling_execution_authority.get(key) is not None
            for key in (
                "fling_major_status_cure_berry_support",
                "fling_type_resist_empty_intrinsic_berry_support",
                "fling_persim_confusion_cure_berry_support",
            )
        )
    ):
        return _result(
            "rejected", "fling_lum_execution_family_binding_mismatch",
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

    interaction_outcome = berry_eat_item_interaction_authority.get("outcome")
    if interaction_outcome == "post_hit_target_eat_not_reached":
        return _terminal(
            "not_applicable",
            berry_eat_item_interaction_authority.get(
                "reason", "fling_berry_target_eat_not_reached"
            ),
            common,
            condition_before="not_evaluated",
            condition_after="not_evaluated",
            confusion_before="not_evaluated",
            confusion_after="not_evaluated",
            confusion_progression_before=None,
            confusion_progression_after=None,
        )
    if (
        interaction_outcome != "post_hit_target_eat_item_dispatched"
        or berry_eat_item_interaction_authority.get("target_eat_occurred") is not True
        or berry_eat_item_interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return _result("rejected", "fling_lum_eat_item_prerequisite_invalid", common)

    readiness = assess_fling_berry_target_eat_item_consequence_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {**common, "target_eat_item_consequence_readiness": deepcopy(readiness)}
    if readiness.get("status") != "resolved" or readiness.get("readiness") != "ready":
        status = readiness.get("status")
        if status not in {"incomplete", "rejected"}:
            status = "rejected"
        return _result(
            status,
            readiness.get("reason", "fling_lum_target_eat_item_consequence_not_ready"),
            common,
        )

    current_condition = freeze_runtime_current_condition_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        owner=target,
    )
    common = {**common, "current_condition_authority": deepcopy(current_condition)}
    if current_condition.get("status") != "resolved":
        return _result(
            _status(current_condition),
            current_condition.get("reason", "fling_lum_current_condition_unavailable"),
            common,
        )
    condition_value = current_condition.get("condition")
    condition_before = _condition_before(condition_value)
    if condition_before == "unknown":
        return _result("incomplete", "fling_lum_target_condition_unknown", common)
    if condition_before == "invalid":
        return _result("rejected", "fling_lum_current_condition_authority_invalid", common)

    current_confusion = _current_confusion(
        runtime_snapshot=runtime_snapshot, target=target,
    )
    common = {**common, "current_confusion_authority": deepcopy(current_confusion)}
    if current_confusion.get("status") != "resolved":
        return _result(
            current_confusion.get("status", "rejected"),
            current_confusion.get("reason", "fling_lum_current_confusion_unavailable"),
            common,
        )

    confusion_before = current_confusion["state"]
    has_condition = condition_before in _MAJOR_CONDITIONS
    has_confusion = confusion_before == "confused"
    if has_condition and has_confusion:
        outcome = "applied_major_status_and_confusion_cure"
    elif has_condition:
        outcome = "applied_major_status_cure"
    elif has_confusion:
        outcome = "applied_confusion_cure"
    else:
        outcome = "no_transition_no_curable_state"
    return _terminal(
        outcome,
        "pinned_lum_intrinsic_on_eat_atomically_cures_major_status_and_confusion",
        common,
        condition_before=condition_before,
        condition_after="none",
        confusion_before=confusion_before,
        confusion_after="none",
        confusion_progression_before=deepcopy(current_confusion.get("progression")),
        confusion_progression_after=None,
    )


def materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
    *, authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize both Lum state dimensions as one authenticated consequence."""
    if not _authority_shape(authority):
        return {
            "status": "rejected",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "reason": "fling_lum_target_effect_authority_invalid",
        }
    result = {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": authority["outcome"],
        "item_id": "lum-berry",
        "actor": deepcopy(authority["actor"]),
        "target": deepcopy(authority["target"]),
        "condition_before": authority["condition_before"],
        "condition_after": authority["condition_after"],
        "confusion_before": authority["confusion_before"],
        "confusion_after": authority["confusion_after"],
        "confusion_progression_before": deepcopy(
            authority.get("confusion_progression_before")
        ),
        "confusion_progression_after": None,
        "authority": deepcopy(dict(authority)),
        "provenance": "detached_authenticated_fling_lum_status_confusion_cure_v1",
    }
    if authority["condition_before"] in _MAJOR_CONDITIONS:
        result["hypothetical_target_condition_removal"] = {
            "schema_version": CONDITION_REMOVAL_SCHEMA_VERSION,
            "condition_before": authority["condition_before"],
            "condition_removed": authority["condition_before"],
            "condition_after": "none",
            "removal_trigger": "authenticated_fling_target_eat_then_eat_item",
            "source_berry_item_id": "lum-berry",
            "source_fling_action_id": authority["action_id"],
            "source_leaf_id": authority["source_leaf_id"],
            "fling_lum_major_status_confusion_cure_target_effect_authority": deepcopy(
                dict(authority)
            ),
            "provenance": "fling_lum_intrinsic_on_eat_major_status_removal_v1",
        }
    if authority["confusion_before"] == "confused":
        result["hypothetical_target_confusion_removal"] = {
            "schema_version": CONFUSION_REMOVAL_SCHEMA_VERSION,
            "target": deepcopy(authority["target"]),
            "confusion_before": "confused",
            "confusion_after": "none",
            "confusion_progression_before": deepcopy(
                authority["confusion_progression_before"]
            ),
            "confusion_progression_after": None,
            "source_berry_item_id": "lum-berry",
            "source_fling_action_id": authority["action_id"],
            "source_leaf_id": authority["source_leaf_id"],
            "berry_eat_item_interaction_authority": deepcopy(
                authority["berry_eat_item_interaction_authority"]
            ),
            "fling_lum_major_status_confusion_cure_target_effect_authority": deepcopy(
                dict(authority)
            ),
            "provenance": "fling_lum_intrinsic_on_eat_confusion_removal_v1",
        }
    return result


def validate_detached_fling_lum_major_status_confusion_cure_target_effect(
    *,
    consequence: Any,
    source_leaf: Mapping[str, Any],
    expected_target: Mapping[str, Any],
) -> bool:
    if (
        not isinstance(consequence, Mapping)
        or consequence.get("status") != "resolved"
        or consequence.get("schema_version") != DETACHED_SCHEMA_VERSION
        or consequence.get("provenance")
        != "detached_authenticated_fling_lum_status_confusion_cure_v1"
        or not _authority_shape(consequence.get("authority"))
    ):
        return False
    authority = consequence["authority"]
    if (
        consequence.get("item_id") != "lum-berry"
        or consequence.get("actor") != authority.get("actor")
        or consequence.get("target") != dict(expected_target)
        or authority.get("target") != dict(expected_target)
        or authority.get("source_leaf_id") != source_leaf.get("leaf_id")
        or authority.get("action_id") != source_leaf.get("candidate_id")
        or consequence.get("outcome") != authority.get("outcome")
        or any(
            consequence.get(key) != authority.get(key)
            for key in (
                "condition_before", "condition_after",
                "confusion_before", "confusion_after",
                "confusion_progression_before", "confusion_progression_after",
            )
        )
    ):
        return False
    exact_binding = _source_leaf_binding(source_leaf, _base_from_authority(authority))
    if isinstance(exact_binding, str) or exact_binding != authority.get("source_leaf_binding"):
        return False

    condition_marker = consequence.get("hypothetical_target_condition_removal")
    confusion_marker = consequence.get("hypothetical_target_confusion_removal")
    needs_condition = authority["condition_before"] in _MAJOR_CONDITIONS
    needs_confusion = authority["confusion_before"] == "confused"
    if needs_condition:
        if not validate_detached_target_condition_removal(
            condition_marker,
            source_leaf_id=source_leaf.get("leaf_id"),
            source_leaf=source_leaf,
            expected_target=expected_target,
        ):
            return False
    elif condition_marker is not None:
        return False
    if needs_confusion:
        if not validate_detached_lum_confusion_removal(
            confusion_marker,
            source_leaf=source_leaf,
            expected_target=expected_target,
        ):
            return False
    elif confusion_marker is not None:
        return False

    expected_outcome = (
        "applied_major_status_and_confusion_cure"
        if needs_condition and needs_confusion else
        "applied_major_status_cure" if needs_condition else
        "applied_confusion_cure" if needs_confusion else
        "no_transition_no_curable_state"
    )
    return authority.get("outcome") == expected_outcome


def validate_detached_lum_confusion_removal(
    value: Any,
    *,
    expected_target: Mapping[str, Any],
    source_leaf: Mapping[str, Any] | None = None,
    source_leaf_id: Any = None,
) -> bool:
    leaf_id = source_leaf.get("leaf_id") if isinstance(source_leaf, Mapping) else source_leaf_id
    action_id = (
        source_leaf.get("candidate_id") if isinstance(source_leaf, Mapping)
        else value.get("source_fling_action_id") if isinstance(value, Mapping) else None
    )
    if (
        not isinstance(leaf_id, str) or not leaf_id
        or not isinstance(action_id, str) or not action_id
        or not isinstance(value, Mapping)
        or value.get("schema_version") != CONFUSION_REMOVAL_SCHEMA_VERSION
        or value.get("target") != dict(expected_target)
        or value.get("confusion_before") != "confused"
        or value.get("confusion_after") != "none"
        or value.get("confusion_progression_after") is not None
        or value.get("source_berry_item_id") != "lum-berry"
        or value.get("source_fling_action_id") != action_id
        or value.get("source_leaf_id") != leaf_id
        or value.get("provenance") != "fling_lum_intrinsic_on_eat_confusion_removal_v1"
    ):
        return False
    authority = value.get("fling_lum_major_status_confusion_cure_target_effect_authority")
    if (
        not _authority_shape(authority)
        or authority.get("outcome") not in {
            "applied_major_status_and_confusion_cure", "applied_confusion_cure",
        }
        or authority.get("target") != dict(expected_target)
        or authority.get("source_leaf_id") != leaf_id
        or authority.get("action_id") != action_id
        or value.get("confusion_progression_before")
        != authority.get("confusion_progression_before")
        or value.get("berry_eat_item_interaction_authority")
        != authority.get("berry_eat_item_interaction_authority")
    ):
        return False
    return valid_confusion_progression(
        value.get("confusion_progression_before"), dict(expected_target),
    )


def _condition_before(value: Any) -> str:
    if not isinstance(value, Mapping) or value.get("status") == "unknown":
        return "unknown"
    if value.get("status") == "known_none":
        return "none"
    if (
        value.get("status") == "known_present"
        and value.get("condition") in _MAJOR_CONDITIONS
    ):
        return value["condition"]
    return "invalid"


def _current_confusion(
    *, runtime_snapshot: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    state = runtime_snapshot.get("state")
    raw = _pokemon(state, target) if isinstance(state, Mapping) else None
    if raw is None:
        return {"status": "rejected", "reason": "fling_lum_runtime_target_identity_mismatch"}
    value = raw.get("current_confusion")
    provenance = raw.get("confusion_provenance")
    progression = raw.get("champions_confusion_progression")
    if value in {None, "unknown"}:
        return {
            "status": "incomplete", "owner": deepcopy(dict(target)),
            "reason": "fling_lum_target_confusion_unknown",
        }
    if value not in {"confused", "none"}:
        return {
            "status": "rejected", "owner": deepcopy(dict(target)),
            "reason": "fling_lum_target_confusion_state_invalid",
        }
    if (
        not isinstance(provenance, Mapping)
        or provenance.get("state") != value
        or provenance.get("trust") != "user_confirmed_observation"
        or provenance.get("event_kind")
        not in {"current_confusion_observed", "confusion_cleared_on_switch"}
    ):
        return {
            "status": "incomplete", "owner": deepcopy(dict(target)), "state": value,
            "reason": "fling_lum_target_confusion_provenance_unknown",
        }
    if value == "none":
        if progression is not None:
            return {
                "status": "rejected", "owner": deepcopy(dict(target)), "state": value,
                "reason": "fling_lum_none_confusion_has_stale_progression",
            }
        return {
            "status": "resolved", "owner": deepcopy(dict(target)), "state": "none",
            "confusion_provenance": deepcopy(dict(provenance)), "progression": None,
            "provenance": "exact_runtime_current_confusion_v1",
        }
    if progression is None:
        return {
            "status": "incomplete", "owner": deepcopy(dict(target)), "state": "confused",
            "confusion_provenance": deepcopy(dict(provenance)),
            "reason": "fling_lum_confusion_progression_missing",
        }
    if not valid_confusion_progression(progression, dict(target)):
        return {
            "status": "rejected", "owner": deepcopy(dict(target)), "state": "confused",
            "reason": "fling_lum_confusion_progression_invalid",
        }
    if progression.get("confusion_observation") != dict(provenance):
        return {
            "status": "rejected", "owner": deepcopy(dict(target)), "state": "confused",
            "reason": "fling_lum_confusion_progression_stale",
        }
    return {
        "status": "resolved", "owner": deepcopy(dict(target)), "state": "confused",
        "confusion_provenance": deepcopy(dict(provenance)),
        "progression": deepcopy(dict(progression)),
        "provenance": "exact_runtime_current_confusion_v1",
    }


def _base(d0: Any, execution: Any, actor: Any, target: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    if not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return "fling_lum_owner_identity_invalid"
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or d0.get("decision_owner") != dict(actor)
        or active.get(actor["side"]) != dict(actor)
        or active.get(target["side"]) != dict(target)
    ):
        return "fling_lum_owner_binding_invalid"
    if (
        not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("move_id") != "fling"
        or execution.get("actor") != dict(actor)
        or execution.get("target") != dict(target)
        or not isinstance(execution.get("action_id"), str)
    ):
        return "fling_lum_execution_authority_invalid"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_lum_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if not isinstance(item, Mapping) or item.get("status") != "known" or item.get("value") != "lum-berry":
        return "fling_lum_item_identity_invalid"
    return {
        "schema_version": SCHEMA_VERSION,
        **deepcopy(expected),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": execution["action_id"],
        "move_id": "fling",
        "item_id": "lum-berry",
        "fling_execution_authority": deepcopy(dict(execution)),
    }


def _base_from_authority(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": authority.get("session_id"),
        "source_runtime_fingerprint": authority.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": authority.get("source_branch_fingerprint"),
        "decision_owner": authority.get("decision_owner"),
        "actor": authority.get("actor"),
        "target": authority.get("target"),
        "action_id": authority.get("action_id"),
        "move_id": "fling",
        "item_id": "lum-berry",
        "fling_execution_authority": authority.get("fling_execution_authority"),
    }


def _source_leaf_binding(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if (
        not isinstance(value, Mapping)
        or value.get("candidate_id") != base["action_id"]
        or not isinstance(value.get("leaf_id"), str)
    ):
        return "fling_lum_source_leaf_invalid"
    provenance = value.get("provenance")
    consequences = value.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping):
        return "fling_lum_source_leaf_invalid"
    if any(
        provenance.get(key) != base.get(key)
        for key in (
            "session_id", "source_runtime_fingerprint",
            "source_branch_fingerprint", "decision_owner",
        )
    ):
        return "fling_lum_source_leaf_binding_mismatch"
    if (
        provenance.get("attacker") != base["actor"]
        or provenance.get("target") != base["target"]
        or provenance.get("move_id") != "fling"
        or provenance.get("fling_execution_authority") != base["fling_execution_authority"]
    ):
        return "fling_lum_source_leaf_identity_mismatch"
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
        return "fling_lum_eat_item_authority_invalid"
    if value.get("status") != "resolved":
        return value.get("reason", "fling_lum_eat_item_authority_unresolved")
    if (
        value.get("phase") != "post_hit_target_berry_interaction"
        or value.get("actor") != base["actor"]
        or value.get("target") != base["target"]
        or value.get("action_id") != base["action_id"]
        or value.get("item_id") != "lum-berry"
        or value.get("fling_execution_authority") != base["fling_execution_authority"]
        or any(
            value.get(key) != base.get(key)
            for key in (
                "session_id", "source_runtime_fingerprint",
                "source_branch_fingerprint", "decision_owner",
            )
        )
    ):
        return "fling_lum_eat_item_authority_binding_mismatch"
    source_hit = value.get("source_hit")
    if not isinstance(source_hit, Mapping) or source_hit.get("source_leaf_id") != source_leaf_id:
        return "fling_lum_eat_item_source_leaf_mismatch"
    return None


def _authority_shape(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("status") != "resolved"
        or value.get("outcome") not in _OUTCOMES
        or value.get("item_id") != "lum-berry"
        or value.get("provenance")
        != "strict_runtime_d0_fling_lum_status_confusion_cure_target_effect_v1"
    ):
        return False
    family = resolve_canonical_fling_lum_major_status_confusion_cure_berry("lum-berry")
    execution = value.get("fling_execution_authority")
    interaction = value.get("berry_eat_item_interaction_authority")
    readiness = assess_fling_berry_target_eat_item_consequence_readiness(interaction)
    condition = value.get("current_condition_authority")
    confusion = value.get("current_confusion_authority")
    if (
        family.get("status") != "resolved"
        or value.get("berry_family_authority") != family
        or not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("fling_lum_major_status_confusion_cure_support") != _SUPPORT
        or execution.get("fling_lum_major_status_confusion_cure_berry_authority") != family
        or any(
            execution.get(key) is not None
            for key in (
                "fling_major_status_cure_berry_support",
                "fling_type_resist_empty_intrinsic_berry_support",
                "fling_persim_confusion_cure_berry_support",
            )
        )
        or execution.get("resolved_base_power") != 10
        or execution.get("actor") != value.get("actor")
        or execution.get("target") != value.get("target")
        or execution.get("action_id") != value.get("action_id")
        or not isinstance(interaction, Mapping)
        or _interaction_error(
            interaction, base=_base_from_authority(value),
            source_leaf_id=value.get("source_leaf_id"),
        ) is not None
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
        or readiness.get("status") != "resolved"
        or readiness.get("readiness") != "ready"
        or value.get("target_eat_item_consequence_readiness") != readiness
        or not isinstance(condition, Mapping)
        or condition.get("status") != "resolved"
        or condition.get("owner") != value.get("target")
        or not isinstance(confusion, Mapping)
        or confusion.get("status") != "resolved"
        or confusion.get("owner") != value.get("target")
    ):
        return False
    before = _condition_before(condition.get("condition"))
    if before not in _MAJOR_CONDITIONS | {"none"}:
        return False
    if value.get("condition_before") != before or value.get("condition_after") != "none":
        return False
    conf_before = confusion.get("state")
    if conf_before not in {"none", "confused"}:
        return False
    if (
        value.get("confusion_before") != conf_before
        or value.get("confusion_after") != "none"
        or value.get("confusion_progression_before") != confusion.get("progression")
        or value.get("confusion_progression_after") is not None
    ):
        return False
    if conf_before == "confused":
        if not valid_confusion_progression(confusion.get("progression"), value.get("target")):
            return False
    elif confusion.get("progression") is not None:
        return False
    expected_outcome = (
        "applied_major_status_and_confusion_cure"
        if before in _MAJOR_CONDITIONS and conf_before == "confused" else
        "applied_major_status_cure"
        if before in _MAJOR_CONDITIONS else
        "applied_confusion_cure"
        if conf_before == "confused" else
        "no_transition_no_curable_state"
    )
    return value.get("outcome") == expected_outcome


def _pokemon(state: Mapping[str, Any], owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return value if (
        isinstance(value, Mapping)
        and value.get("pokemon_id", value.get("name_en")) == owner["pokemon_id"]
    ) else None


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
        "provenance": "strict_runtime_d0_fling_lum_status_confusion_cure_target_effect_v1",
    }


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
    }
