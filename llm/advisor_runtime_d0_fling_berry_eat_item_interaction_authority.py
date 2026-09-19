"""Strict detached authority for Fling Berry Eat/EatItem interaction timing.

This module authenticates event boundaries and ability hooks only.  It never
materializes an intrinsic Berry consequence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_berry_eat_item_interactions import (
    resolve_canonical_fling_berry_ability_interaction,
    resolve_canonical_fling_berry_item_identity,
    resolve_canonical_fling_berry_timing,
)
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_PHASES = frozenset({"pre_hit_source_berry_interaction", "post_hit_target_berry_interaction"})


def freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    fling_execution_authority: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    phase: str,
    source_leaf: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze one exact Fling Berry event boundary without applying the Berry."""
    base = _base(strategy_d0, fling_execution_authority, actor, target)
    if isinstance(base, str):
        return _result("rejected", base, {})
    if phase not in _PHASES:
        return _result("rejected", "fling_berry_interaction_phase_invalid", base)
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)

    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    actor_raw = _pokemon(state, actor)
    target_raw = _pokemon(state, target)
    if actor_raw is None or target_raw is None:
        return _result("rejected", "fling_berry_runtime_identity_mismatch", base)

    source_ability = _trusted_ability(actor_raw, actor)
    target_ability = _trusted_ability(target_raw, target)
    timing = resolve_canonical_fling_berry_timing()
    if timing.get("status") != "resolved":
        return _result("rejected", timing.get("reason", "fling_berry_timing_unavailable"), base)

    common = {
        **base,
        "phase": phase,
        "source_ability_authority": deepcopy(source_ability),
        "target_ability_authority": deepcopy(target_ability),
        "timing_authority": deepcopy(timing),
        "intrinsic_berry_effect": "deferred",
    }

    if phase == "pre_hit_source_berry_interaction":
        return _source_phase(fling_execution_authority, source_ability, target_ability, common)

    return _target_phase(
        fling_execution_authority=fling_execution_authority,
        source_leaf=source_leaf,
        source_ability=source_ability,
        target_ability=target_ability,
        common=common,
    )


def _source_phase(
    execution: Mapping[str, Any],
    source_ability: Mapping[str, Any],
    target_ability: Mapping[str, Any],
    common: Mapping[str, Any],
) -> dict[str, Any]:
    outcome = execution.get("outcome")
    if outcome in {"failed_item_suppressed", "failed_no_item"}:
        return _terminal(
            "pre_hit_source_berry_branch_not_reached",
            execution.get("reason", "fling_pre_hit_failed"),
            common,
            source_cud_chew_dispatch=False,
            target_hit_required=False,
        )

    if source_ability.get("status") != "resolved":
        return _result("incomplete", "fling_berry_source_ability_unknown", common)

    ability_id = source_ability["ability_id"]
    classification = resolve_canonical_fling_berry_ability_interaction(ability_id)
    if classification.get("status") != "resolved":
        return _result("incomplete", classification.get("reason", "fling_berry_source_ability_unclassified"), common, source_ability_classification=classification)

    if _showdown_id(ability_id) != "cudchew":
        return _terminal(
            "pre_hit_source_no_cud_chew_dispatch",
            "source_ability_not_cud_chew",
            common,
            source_ability_classification=classification,
            source_cud_chew_dispatch=False,
            target_hit_required=False,
        )

    if target_ability.get("status") != "resolved":
        return _result(
            "incomplete",
            "fling_berry_source_cud_chew_suppression_context_unknown",
            common,
            source_ability_classification=classification,
        )
    gas = _neutralizing_gas_state(source_ability, target_ability)
    if gas:
        return _result(
            "incomplete",
            "fling_berry_source_cud_chew_neutralizing_gas_composition_unresolved",
            common,
            source_ability_classification=classification,
            neutralizing_gas_active=True,
        )

    return _terminal(
        "pre_hit_source_cud_chew_eat_item_dispatched",
        "pinned_fling_source_cud_chew_branch",
        common,
        source_ability_classification=classification,
        source_cud_chew_dispatch=True,
        target_hit_required=False,
        neutralizing_gas_active=False,
        future_cud_chew_lifecycle="deferred",
    )


def _target_phase(
    *,
    fling_execution_authority: Mapping[str, Any],
    source_leaf: Mapping[str, Any] | None,
    source_ability: Mapping[str, Any],
    target_ability: Mapping[str, Any],
    common: Mapping[str, Any],
) -> dict[str, Any]:
    execution_outcome = fling_execution_authority.get("outcome")
    if execution_outcome in {"failed_item_suppressed", "failed_no_item", "failed_klutz"}:
        return _terminal(
            "post_hit_target_eat_not_reached",
            fling_execution_authority.get("reason", "fling_pre_hit_failed"),
            common,
            target_eat_occurred=False,
            target_eat_item_dispatched=False,
        )
    if execution_outcome not in {"unsupported_mandatory_item_effect", "ready_throw"}:
        return _result("incomplete", "fling_berry_execution_not_ready_for_target_phase", common)

    hit = _source_leaf(source_leaf, common)
    if isinstance(hit, str):
        return _result("rejected", hit, common)
    if hit["outcome"] != "successful_target_hit":
        return _terminal(
            "post_hit_target_eat_not_reached",
            hit["reason"],
            common,
            source_hit=hit,
            target_eat_occurred=False,
            target_eat_item_dispatched=False,
        )

    event_common = {
        **common,
        "source_hit": deepcopy(hit),
        "target_eat_occurred": True,
        "target_eat_item_dispatched": True,
        "ordinary_held_berry_trigger_used": False,
    }
    if source_ability.get("status") != "resolved" or target_ability.get("status") != "resolved":
        return _result("incomplete", "fling_berry_target_ability_context_unknown", event_common)

    source_class = resolve_canonical_fling_berry_ability_interaction(source_ability["ability_id"])
    target_class = resolve_canonical_fling_berry_ability_interaction(target_ability["ability_id"])
    if source_class.get("status") != "resolved" or target_class.get("status") != "resolved":
        return _result(
            "incomplete",
            "fling_berry_target_ability_interaction_unclassified",
            event_common,
            source_ability_classification=source_class,
            target_ability_classification=target_class,
        )

    direct_hook = target_class["classification"]["direct_target_eat_item_hook"] is True
    gas = _neutralizing_gas_state(source_ability, target_ability)
    if gas and direct_hook:
        return _result(
            "incomplete",
            "fling_berry_target_eat_item_neutralizing_gas_composition_unresolved",
            event_common,
            source_ability_classification=source_class,
            target_ability_classification=target_class,
            neutralizing_gas_active=True,
        )

    source_roles = set(source_class["classification"].get("roles", []))
    opposing_try_eat_bypassed = "opposing_try_eat_blocker" in source_roles
    return _terminal(
        "post_hit_target_eat_item_dispatched",
        "pinned_fling_direct_eat_then_eat_item",
        event_common,
        source_ability_classification=source_class,
        target_ability_classification=target_class,
        target_ability_interaction="applies" if direct_hook else "not_applicable",
        opposing_try_eat_blocker_bypassed=opposing_try_eat_bypassed,
        neutralizing_gas_active=gas,
        ability_consequence_materialization="deferred" if direct_hook else "not_applicable",
    )


def assess_fling_berry_target_eat_item_consequence_readiness(
    interaction_authority: Any,
) -> dict[str, Any]:
    """Validate whether exact downstream target-side Berry mechanics may continue.

    The Eat/EatItem interaction owner remains descriptive.  This helper only
    answers whether a known direct target EatItem hook has an exact materialized
    consequence available to a downstream consumer.
    """
    base = {
        "schema_version": "fling-berry-target-eat-item-consequence-readiness-v1",
    }
    if (
        not isinstance(interaction_authority, Mapping)
        or interaction_authority.get("schema_version") != SCHEMA_VERSION
        or interaction_authority.get("status") != "resolved"
        or interaction_authority.get("phase") != "post_hit_target_berry_interaction"
        or interaction_authority.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction_authority.get("target_eat_occurred") is not True
        or interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return {
            "status": "rejected", **base,
            "reason": "fling_berry_target_eat_item_readiness_authority_invalid",
        }

    target_ability = interaction_authority.get("target_ability_authority")
    target_class = interaction_authority.get("target_ability_classification")
    if (
        not isinstance(target_ability, Mapping)
        or target_ability.get("status") != "resolved"
        or not isinstance(target_ability.get("ability_id"), str)
        or not isinstance(target_class, Mapping)
        or target_class.get("status") != "resolved"
    ):
        return {
            "status": "rejected", **base,
            "reason": "fling_berry_target_eat_item_readiness_ability_binding_invalid",
        }

    canonical = resolve_canonical_fling_berry_ability_interaction(
        target_ability["ability_id"],
    )
    if canonical.get("status") != "resolved" or target_class != canonical:
        return {
            "status": "rejected", **base,
            "reason": "fling_berry_target_eat_item_readiness_classification_mismatch",
        }

    classification = canonical.get("classification")
    if not isinstance(classification, Mapping):
        return {
            "status": "rejected", **base,
            "reason": "fling_berry_target_eat_item_readiness_classification_invalid",
        }
    direct_hook = classification.get("direct_target_eat_item_hook") is True
    expected_interaction = "applies" if direct_hook else "not_applicable"
    expected_materialization = "deferred" if direct_hook else "not_applicable"
    if (
        interaction_authority.get("target_ability_interaction") != expected_interaction
        or interaction_authority.get("ability_consequence_materialization")
        != expected_materialization
    ):
        return {
            "status": "rejected", **base,
            "reason": "fling_berry_target_eat_item_readiness_state_inconsistent",
            "target_ability_id": target_ability["ability_id"],
            "direct_target_eat_item_hook": direct_hook,
        }

    if direct_hook:
        return {
            "status": "incomplete", **base,
            "readiness": "incomplete_due_to_deferred_direct_target_hook",
            "reason": "fling_berry_direct_target_eat_item_consequence_deferred",
            "target_ability_id": target_ability["ability_id"],
            "target_ability_classification": deepcopy(canonical),
            "ability_consequence_materialization": "deferred",
        }
    return {
        "status": "resolved", **base,
        "readiness": "ready",
        "reason": "no_direct_target_eat_item_hook",
        "target_ability_id": target_ability["ability_id"],
        "target_ability_classification": deepcopy(canonical),
        "ability_consequence_materialization": "not_applicable",
    }


def _base(d0: Any, execution: Any, actor: Any, target: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    if not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return "fling_berry_owner_identity_invalid"
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(actor["side"]) != dict(actor) or active.get(target["side"]) != dict(target) or d0.get("decision_owner") != dict(actor):
        return "fling_berry_owner_binding_invalid"
    if not isinstance(execution, Mapping) or execution.get("schema_version") != _EXECUTION_SCHEMA:
        return "fling_berry_execution_authority_invalid"
    if execution.get("actor") != dict(actor) or execution.get("target") != dict(target) or execution.get("move_id") != "fling" or not isinstance(execution.get("action_id"), str):
        return "fling_berry_execution_identity_mismatch"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_berry_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if not isinstance(item, Mapping) or item.get("status") != "known" or not isinstance(item.get("value"), str) or not item["value"]:
        return "fling_berry_item_identity_unknown"
    item_id = item["value"]
    berry = resolve_canonical_fling_berry_item_identity(item_id)
    if berry.get("status") == "not_applicable":
        return "fling_item_not_berry_effect"
    if berry.get("status") != "resolved":
        return berry.get("reason", "fling_berry_item_identity_unavailable")
    metadata = resolve_canonical_fling_item_metadata(item_id)
    if metadata.get("status") != "resolved" or metadata.get("effect", {}).get("kind") != "berry_effect":
        return "fling_berry_manifest_binding_invalid"
    embedded = execution.get("fling_item_metadata")
    if embedded is not None and embedded != metadata:
        return "fling_berry_execution_manifest_binding_mismatch"
    return {
        "schema_version": SCHEMA_VERSION,
        **deepcopy(expected),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": execution["action_id"],
        "move_id": "fling",
        "item_id": item_id,
        "fling_item_metadata": deepcopy(metadata),
        "fling_execution_authority": deepcopy(dict(execution)),
        "berry_identity_authority": deepcopy(berry),
    }


def _source_leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("candidate_id") != base["action_id"] or not isinstance(value.get("leaf_id"), str):
        return "fling_berry_source_leaf_invalid"
    provenance = value.get("provenance")
    consequences = value.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping):
        return "fling_berry_source_leaf_invalid"
    if any(provenance.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")):
        return "fling_berry_source_leaf_binding_mismatch"
    if provenance.get("attacker") != base["actor"] or provenance.get("target") != base["target"] or provenance.get("move_id") != "fling":
        return "fling_berry_source_leaf_identity_mismatch"
    embedded = provenance.get("fling_execution_authority")
    if embedded is not None and embedded != base["fling_execution_authority"]:
        return "fling_berry_source_leaf_execution_binding_mismatch"
    if value.get("hit_state") != "hit":
        return {"outcome": "inapplicable", "reason": "fling_miss_or_pre_execution_cancellation", "source_leaf_id": value["leaf_id"]}
    hit = consequences.get("source_hit_context")
    if not isinstance(hit, Mapping) or hit.get("source_action_id") != base["action_id"] or hit.get("source_move_id") != "fling":
        return "fling_berry_source_hit_missing"
    if hit.get("target_routing") != "target":
        return {"outcome": "inapplicable", "reason": "fling_target_effect_substitute_or_non_target_route", "source_leaf_id": value["leaf_id"]}
    damage = hit.get("actual_damage")
    if not isinstance(damage, int) or isinstance(damage, bool) or damage <= 0:
        return {"outcome": "inapplicable", "reason": "fling_protect_or_immunity_or_no_damage", "source_leaf_id": value["leaf_id"]}
    hp = consequences.get("target_final_hp")
    if consequences.get("target_ko") is True or not isinstance(hp, int) or isinstance(hp, bool) or hp <= 0:
        return {"outcome": "inapplicable", "reason": "fling_target_fainted_before_effect", "source_leaf_id": value["leaf_id"]}
    return {
        "outcome": "successful_target_hit",
        "reason": None,
        "source_leaf_id": value["leaf_id"],
        "actual_damage": damage,
        "target_post_hp": hp,
        "target_routing": "target",
    }


def _trusted_ability(raw: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    value = raw.get("current_ability")
    provenance = raw.get("current_ability_provenance")
    if (
        isinstance(value, str) and value
        and isinstance(provenance, Mapping)
        and provenance.get("event_kind") == "current_ability_observed"
        and provenance.get("trust") == "user_confirmed_observation"
    ):
        return {
            "status": "resolved",
            "owner": deepcopy(dict(owner)),
            "ability_id": value,
            "runtime_ability_provenance": deepcopy(dict(provenance)),
        }
    return {"status": "incomplete", "owner": deepcopy(dict(owner)), "reason": "current_ability_unknown"}


def _neutralizing_gas_state(source: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    return source.get("ability_id") == "neutralizing-gas" or target.get("ability_id") == "neutralizing-gas"


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    raw = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return raw if isinstance(raw, Mapping) and raw.get("pokemon_id") == owner["pokemon_id"] else None


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _showdown_id(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _terminal(outcome: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": "resolved",
        **deepcopy(dict(base)),
        "outcome": outcome,
        "reason": reason,
        **deepcopy(extra),
        "provenance": "strict_runtime_d0_fling_berry_eat_item_interaction_v1",
    }


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        **deepcopy(dict(base)),
        "reason": reason,
        **deepcopy(extra),
    }
