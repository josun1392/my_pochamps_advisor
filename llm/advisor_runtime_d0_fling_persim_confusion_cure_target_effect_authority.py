"""Exact target-side Persim Berry confusion cure after Fling Eat."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_persim_confusion_cure_berry import (
    resolve_canonical_fling_persim_confusion_cure_berry,
)
from llm.advisor_champions_confusion_progression import valid_confusion_progression
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
    assess_fling_berry_target_intrinsic_on_eat_readiness,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-fling-persim-confusion-cure-target-effect-authority-v1"
DETACHED_SCHEMA_VERSION = "detached-fling-persim-confusion-cure-target-effect-v1"
REMOVAL_SCHEMA_VERSION = "detached-hypothetical-target-confusion-removal-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_EAT_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_SUPPORT = "fling_persim_confusion_cure_target_effect_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_fling_persim_confusion_cure_target_effect_authority(
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

    family = resolve_canonical_fling_persim_confusion_cure_berry(base["item_id"])
    if family.get("status") != "resolved":
        return _result(
            "rejected" if family.get("status") == "rejected" else "unsupported",
            family.get("reason", "fling_persim_family_unavailable"),
            base,
        )
    if (
        fling_execution_authority.get("fling_persim_confusion_cure_berry_support")
        != _SUPPORT
        or fling_execution_authority.get(
            "fling_persim_confusion_cure_berry_authority"
        ) != family
    ):
        return _result(
            "rejected",
            "fling_persim_execution_family_binding_mismatch",
            {**base, "berry_family_authority": deepcopy(family)},
        )

    leaf_binding = _source_leaf_binding(source_leaf, base)
    if isinstance(leaf_binding, str):
        return _result(
            "rejected",
            leaf_binding,
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
            confusion_before="not_evaluated",
            confusion_after="not_evaluated",
            confusion_progression_before=None,
            confusion_progression_after=None,
        )
    if (
        outcome != "post_hit_target_eat_item_dispatched"
        or berry_eat_item_interaction_authority.get("target_eat_occurred") is not True
        or berry_eat_item_interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return _result(
            "rejected",
            "fling_persim_eat_item_prerequisite_invalid",
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
                "reason", "fling_persim_target_eat_item_consequence_not_ready"
            ),
            common,
        )
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {**common, "target_intrinsic_on_eat_readiness": deepcopy(intrinsic)}
    if intrinsic.get("status") != "resolved":
        status = intrinsic.get("status")
        if status not in {"incomplete", "rejected"}:
            status = "rejected"
        return _result(
            status,
            intrinsic.get("reason", "fling_persim_target_intrinsic_on_eat_unavailable"),
            common,
        )
    if intrinsic.get("readiness") == "suppressed_by_target_klutz":
        return _terminal(
            "not_applicable",
            "fling_berry_intrinsic_on_eat_suppressed_by_target_klutz",
            common,
            confusion_before="not_evaluated",
            confusion_after="not_evaluated",
            confusion_progression_before=None,
            confusion_progression_after=None,
        )
    if intrinsic.get("readiness") != "executes":
        return _result("rejected", "fling_persim_target_intrinsic_on_eat_state_invalid", common)

    current = _current_confusion(
        runtime_snapshot=runtime_snapshot,
        target=target,
    )
    if current.get("status") != "resolved":
        return _result(
            current.get("status", "rejected"),
            current.get("reason", "fling_persim_current_confusion_unavailable"),
            {**common, "current_confusion_authority": deepcopy(current)},
        )
    common = {**common, "current_confusion_authority": deepcopy(current)}
    state = current["state"]
    if state == "none":
        return _terminal(
            "no_transition_not_confused",
            "target_already_not_confused",
            common,
            confusion_before="none",
            confusion_after="none",
            confusion_progression_before=None,
            confusion_progression_after=None,
        )
    if state != "confused":
        return _result("rejected", "fling_persim_current_confusion_state_invalid", common)
    return _terminal(
        "applied_confusion_cure",
        "pinned_persim_intrinsic_on_eat_removes_confusion",
        common,
        confusion_before="confused",
        confusion_after="none",
        confusion_progression_before=deepcopy(current["progression"]),
        confusion_progression_after=None,
    )


def materialize_detached_fling_persim_confusion_cure_target_effect(
    *, authority: Mapping[str, Any],
) -> dict[str, Any]:
    if not _authority_shape(authority):
        return {
            "status": "rejected",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "reason": "fling_persim_target_effect_authority_invalid",
        }
    result = {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": authority["outcome"],
        "item_id": authority["item_id"],
        "actor": deepcopy(authority["actor"]),
        "target": deepcopy(authority["target"]),
        "confusion_before": authority.get("confusion_before"),
        "confusion_after": authority.get("confusion_after"),
        "confusion_progression_before": deepcopy(
            authority.get("confusion_progression_before")
        ),
        "confusion_progression_after": deepcopy(
            authority.get("confusion_progression_after")
        ),
        "authority": deepcopy(dict(authority)),
        "provenance": "detached_authenticated_fling_persim_confusion_cure_v1",
    }
    if authority["outcome"] == "applied_confusion_cure":
        result["hypothetical_target_confusion_removal"] = {
            "schema_version": REMOVAL_SCHEMA_VERSION,
            "target": deepcopy(authority["target"]),
            "confusion_before": "confused",
            "confusion_after": "none",
            "confusion_progression_before": deepcopy(
                authority["confusion_progression_before"]
            ),
            "confusion_progression_after": None,
            "source_berry_item_id": "persim-berry",
            "source_fling_action_id": authority["action_id"],
            "source_leaf_id": authority["source_leaf_id"],
            "berry_eat_item_interaction_authority": deepcopy(
                authority["berry_eat_item_interaction_authority"]
            ),
            "fling_persim_confusion_cure_target_effect_authority": deepcopy(
                dict(authority)
            ),
            "provenance": "fling_persim_intrinsic_on_eat_confusion_removal_v1",
        }
    return result


def validate_detached_fling_persim_confusion_cure_target_effect(
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
        != "detached_authenticated_fling_persim_confusion_cure_v1"
        or not _authority_shape(consequence.get("authority"))
    ):
        return False
    authority = consequence["authority"]
    if (
        consequence.get("item_id") != "persim-berry"
        or consequence.get("actor") != authority.get("actor")
        or consequence.get("target") != dict(expected_target)
        or authority.get("target") != dict(expected_target)
        or authority.get("source_leaf_id") != source_leaf.get("leaf_id")
        or authority.get("action_id") != source_leaf.get("candidate_id")
        or consequence.get("outcome") != authority.get("outcome")
        or consequence.get("confusion_before") != authority.get("confusion_before")
        or consequence.get("confusion_after") != authority.get("confusion_after")
        or consequence.get("confusion_progression_before")
        != authority.get("confusion_progression_before")
        or consequence.get("confusion_progression_after")
        != authority.get("confusion_progression_after")
    ):
        return False
    exact_binding = _source_leaf_binding(source_leaf, _base_from_authority(authority))
    if isinstance(exact_binding, str) or exact_binding != authority.get("source_leaf_binding"):
        return False
    removal = consequence.get("hypothetical_target_confusion_removal")
    if authority["outcome"] == "applied_confusion_cure":
        return validate_detached_persim_confusion_removal(
            removal,
            source_leaf=source_leaf,
            expected_target=expected_target,
        )
    if authority["outcome"] == "no_transition_not_confused":
        return removal is None
    return False


def validate_detached_persim_confusion_removal(
    value: Any,
    *,
    expected_target: Mapping[str, Any],
    source_leaf: Mapping[str, Any] | None = None,
    source_leaf_id: Any = None,
) -> bool:
    leaf_id = (
        source_leaf.get("leaf_id")
        if isinstance(source_leaf, Mapping)
        else source_leaf_id
    )
    action_id = (
        source_leaf.get("candidate_id")
        if isinstance(source_leaf, Mapping)
        else value.get("source_fling_action_id") if isinstance(value, Mapping) else None
    )
    if (
        not isinstance(leaf_id, str)
        or not leaf_id
        or not isinstance(action_id, str)
        or not action_id
        or not isinstance(value, Mapping)
        or value.get("schema_version") != REMOVAL_SCHEMA_VERSION
        or value.get("target") != dict(expected_target)
        or value.get("confusion_before") != "confused"
        or value.get("confusion_after") != "none"
        or value.get("confusion_progression_after") is not None
        or value.get("source_berry_item_id") != "persim-berry"
        or value.get("source_fling_action_id") != action_id
        or value.get("source_leaf_id") != leaf_id
        or value.get("provenance")
        != "fling_persim_intrinsic_on_eat_confusion_removal_v1"
    ):
        return False
    authority = value.get("fling_persim_confusion_cure_target_effect_authority")
    if (
        not _authority_shape(authority)
        or authority.get("outcome") != "applied_confusion_cure"
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
        value.get("confusion_progression_before"),
        dict(expected_target),
    )


def _current_confusion(
    *, runtime_snapshot: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    state = runtime_snapshot.get("state")
    raw = _pokemon(state, target) if isinstance(state, Mapping) else None
    if raw is None:
        return {"status": "rejected", "reason": "fling_persim_runtime_target_identity_mismatch"}
    value = raw.get("current_confusion")
    provenance = raw.get("confusion_provenance")
    progression = raw.get("champions_confusion_progression")
    if value in {None, "unknown"}:
        return {
            "status": "incomplete",
            "owner": deepcopy(dict(target)),
            "reason": "fling_persim_target_confusion_unknown",
        }
    if value not in {"confused", "none"}:
        return {
            "status": "rejected",
            "owner": deepcopy(dict(target)),
            "reason": "fling_persim_target_confusion_state_invalid",
        }
    if (
        not isinstance(provenance, Mapping)
        or provenance.get("state") != value
        or provenance.get("trust") != "user_confirmed_observation"
        or provenance.get("event_kind")
        not in {"current_confusion_observed", "confusion_cleared_on_switch"}
    ):
        return {
            "status": "incomplete",
            "owner": deepcopy(dict(target)),
            "state": value,
            "reason": "fling_persim_target_confusion_provenance_unknown",
        }
    if value == "none":
        if progression is not None:
            return {
                "status": "rejected",
                "owner": deepcopy(dict(target)),
                "state": value,
                "reason": "fling_persim_none_confusion_has_stale_progression",
            }
        return {
            "status": "resolved",
            "owner": deepcopy(dict(target)),
            "state": "none",
            "confusion_provenance": deepcopy(dict(provenance)),
            "progression": None,
            "provenance": "exact_runtime_current_confusion_v1",
        }
    if progression is None:
        return {
            "status": "incomplete",
            "owner": deepcopy(dict(target)),
            "state": "confused",
            "confusion_provenance": deepcopy(dict(provenance)),
            "reason": "fling_persim_confusion_progression_missing",
        }
    if not valid_confusion_progression(progression, dict(target)):
        return {
            "status": "rejected",
            "owner": deepcopy(dict(target)),
            "state": "confused",
            "reason": "fling_persim_confusion_progression_invalid",
        }
    if progression.get("confusion_observation") != dict(provenance):
        return {
            "status": "rejected",
            "owner": deepcopy(dict(target)),
            "state": "confused",
            "reason": "fling_persim_confusion_progression_stale",
        }
    return {
        "status": "resolved",
        "owner": deepcopy(dict(target)),
        "state": "confused",
        "confusion_provenance": deepcopy(dict(provenance)),
        "progression": deepcopy(dict(progression)),
        "provenance": "exact_runtime_current_confusion_v1",
    }


def _base(d0: Any, execution: Any, actor: Any, target: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    if not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return "fling_persim_owner_identity_invalid"
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or d0.get("decision_owner") != dict(actor)
        or active.get(actor["side"]) != dict(actor)
        or active.get(target["side"]) != dict(target)
    ):
        return "fling_persim_owner_binding_invalid"
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
        return "fling_persim_execution_authority_invalid"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_persim_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if (
        not isinstance(item, Mapping)
        or item.get("status") != "known"
        or item.get("value") != "persim-berry"
    ):
        return "fling_persim_item_identity_invalid"
    return {
        "schema_version": SCHEMA_VERSION,
        **deepcopy(expected),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": execution["action_id"],
        "move_id": "fling",
        "item_id": "persim-berry",
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
        "item_id": "persim-berry",
        "fling_execution_authority": authority.get("fling_execution_authority"),
    }


def _source_leaf_binding(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if (
        not isinstance(value, Mapping)
        or value.get("candidate_id") != base["action_id"]
        or not isinstance(value.get("leaf_id"), str)
    ):
        return "fling_persim_source_leaf_invalid"
    provenance = value.get("provenance")
    consequences = value.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping):
        return "fling_persim_source_leaf_invalid"
    for key in (
        "session_id", "source_runtime_fingerprint",
        "source_branch_fingerprint", "decision_owner",
    ):
        if provenance.get(key) != base.get(key):
            return "fling_persim_source_leaf_binding_mismatch"
    if (
        provenance.get("attacker") != base["actor"]
        or provenance.get("target") != base["target"]
        or provenance.get("move_id") != "fling"
        or provenance.get("fling_execution_authority")
        != base["fling_execution_authority"]
    ):
        return "fling_persim_source_leaf_identity_mismatch"
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
        return "fling_persim_eat_item_authority_invalid"
    if value.get("status") != "resolved":
        return value.get("reason", "fling_persim_eat_item_authority_unresolved")
    if (
        value.get("phase") != "post_hit_target_berry_interaction"
        or value.get("actor") != base["actor"]
        or value.get("target") != base["target"]
        or value.get("action_id") != base["action_id"]
        or value.get("item_id") != "persim-berry"
        or value.get("fling_execution_authority") != base["fling_execution_authority"]
        or any(
            value.get(key) != base.get(key)
            for key in (
                "session_id", "source_runtime_fingerprint",
                "source_branch_fingerprint", "decision_owner",
            )
        )
    ):
        return "fling_persim_eat_item_authority_binding_mismatch"
    source_hit = value.get("source_hit")
    if (
        not isinstance(source_hit, Mapping)
        or source_hit.get("source_leaf_id") != source_leaf_id
    ):
        return "fling_persim_eat_item_source_leaf_mismatch"
    return None


def _authority_shape(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("status") != "resolved"
        or value.get("outcome")
        not in {"applied_confusion_cure", "no_transition_not_confused"}
        or value.get("item_id") != "persim-berry"
        or value.get("provenance")
        != "strict_runtime_d0_fling_persim_confusion_cure_target_effect_v1"
    ):
        return False
    family = resolve_canonical_fling_persim_confusion_cure_berry("persim-berry")
    execution = value.get("fling_execution_authority")
    interaction = value.get("berry_eat_item_interaction_authority")
    readiness = assess_fling_berry_target_eat_item_consequence_readiness(interaction)
    current = value.get("current_confusion_authority")
    if (
        family.get("status") != "resolved"
        or value.get("berry_family_authority") != family
        or not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("fling_persim_confusion_cure_berry_support") != _SUPPORT
        or execution.get("fling_persim_confusion_cure_berry_authority") != family
        or execution.get("resolved_base_power") != 10
        or execution.get("actor") != value.get("actor")
        or execution.get("target") != value.get("target")
        or execution.get("action_id") != value.get("action_id")
        or not isinstance(interaction, Mapping)
        or _interaction_error(
            interaction,
            base=_base_from_authority(value),
            source_leaf_id=value.get("source_leaf_id"),
        ) is not None
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
        or readiness.get("status") != "resolved"
        or readiness.get("readiness") != "ready"
        or value.get("target_eat_item_consequence_readiness") != readiness
        or not isinstance(current, Mapping)
        or current.get("status") != "resolved"
        or current.get("owner") != value.get("target")
    ):
        return False
    if value["outcome"] == "applied_confusion_cure":
        return (
            value.get("confusion_before") == "confused"
            and value.get("confusion_after") == "none"
            and valid_confusion_progression(
                value.get("confusion_progression_before"), value.get("target")
            )
            and value.get("confusion_progression_after") is None
            and current.get("state") == "confused"
            and current.get("progression") == value.get("confusion_progression_before")
        )
    return (
        value.get("confusion_before") == "none"
        and value.get("confusion_after") == "none"
        and value.get("confusion_progression_before") is None
        and value.get("confusion_progression_after") is None
        and current.get("state") == "none"
        and current.get("progression") is None
    )


def _pokemon(state: Mapping[str, Any], owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    if (
        not isinstance(value, Mapping)
        or value.get("pokemon_id", value.get("name_en")) != owner["pokemon_id"]
    ):
        return None
    return value


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
        "provenance": "strict_runtime_d0_fling_persim_confusion_cure_target_effect_v1",
    }


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
    }
