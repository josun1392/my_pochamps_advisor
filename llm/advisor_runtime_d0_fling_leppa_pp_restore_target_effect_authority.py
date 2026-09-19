"""Exact thrown Leppa Berry target PP restoration authority and detached consequence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_leppa_pp_restore_berry import (
    resolve_canonical_fling_leppa_pp_restore_berry,
)
from llm.advisor_runtime_d0_current_opponent_move_pp_state_authority import (
    freeze_runtime_d0_current_opponent_move_pp_state_authority,
    validate_runtime_d0_current_opponent_move_pp_state_authority,
)
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
    assess_fling_berry_target_intrinsic_on_eat_readiness,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-fling-leppa-pp-restore-target-effect-authority-v1"
DETACHED_SCHEMA_VERSION = "detached-fling-leppa-pp-restore-target-effect-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_EAT_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_PP_SCHEMA = "runtime-d0-current-opponent-move-pp-state-authority-v1"
_SUPPORT = "fling_leppa_pp_restore_target_effect_v1"
_BINDING_KEYS = (
    "session_id", "source_runtime_fingerprint",
    "source_branch_fingerprint", "decision_owner",
)


def freeze_runtime_d0_fling_leppa_pp_restore_target_effect_authority(
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
    family = resolve_canonical_fling_leppa_pp_restore_berry(base["item_id"])
    if family.get("status") != "resolved":
        return _result(
            "rejected" if family.get("status") == "rejected" else "unsupported",
            family.get("reason", "fling_leppa_family_unavailable"), base,
        )
    common = {**base, "berry_family_authority": deepcopy(family)}
    if (
        fling_execution_authority.get("fling_leppa_pp_restore_support") != _SUPPORT
        or fling_execution_authority.get("fling_leppa_pp_restore_berry_authority") != family
        or fling_execution_authority.get("resolved_base_power") != 10
    ):
        return _result("rejected", "fling_leppa_execution_family_binding_mismatch", common)
    leaf = _source_leaf_binding(source_leaf, base)
    if isinstance(leaf, str):
        return _result("rejected", leaf, common)
    common = {
        **common,
        "source_leaf_id": source_leaf["leaf_id"],
        "source_leaf_binding": deepcopy(leaf),
        "berry_eat_item_interaction_authority": deepcopy(dict(berry_eat_item_interaction_authority)),
    }
    error = _interaction_error(
        berry_eat_item_interaction_authority,
        base=base,
        source_leaf_id=source_leaf["leaf_id"],
    )
    if error is not None:
        return _result(_status(berry_eat_item_interaction_authority), error, common)
    if berry_eat_item_interaction_authority.get("outcome") == "post_hit_target_eat_not_reached":
        return _terminal(
            "not_applicable",
            berry_eat_item_interaction_authority.get("reason", "fling_leppa_target_eat_not_reached"),
            common,
            external_staleness=None,
        )
    if (
        berry_eat_item_interaction_authority.get("outcome") != "post_hit_target_eat_item_dispatched"
        or berry_eat_item_interaction_authority.get("target_eat_occurred") is not True
        or berry_eat_item_interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return _result("rejected", "fling_leppa_eat_prerequisite_invalid", common)

    direct = assess_fling_berry_target_eat_item_consequence_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {**common, "target_eat_item_consequence_readiness": deepcopy(direct)}
    if direct.get("status") != "resolved" or direct.get("readiness") != "ready":
        return _result(
            direct.get("status") if direct.get("status") in {"incomplete", "rejected"} else "rejected",
            direct.get("reason", "fling_leppa_direct_eat_item_not_ready"),
            common,
        )
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {**common, "target_intrinsic_on_eat_readiness": deepcopy(intrinsic)}
    if intrinsic.get("status") != "resolved":
        return _result(
            intrinsic.get("status") if intrinsic.get("status") in {"incomplete", "rejected"} else "rejected",
            intrinsic.get("reason", "fling_leppa_intrinsic_on_eat_unavailable"),
            common,
        )
    staleness = deepcopy(family["external_staleness"])
    if intrinsic.get("readiness") == "suppressed_by_target_klutz":
        return _terminal(
            "intrinsic_suppressed_by_target_klutz",
            "fling_leppa_intrinsic_on_eat_suppressed",
            common,
            selected_slot_index=None,
            selected_move_id=None,
            selection_reason=None,
            pp_before=None,
            max_pp=None,
            nominal_restore=0,
            actual_restore=0,
            pp_after=None,
            current_pp_authority=None,
            external_staleness=staleness,
            timing="post_eat_pre_pending_action",
        )
    if intrinsic.get("readiness") != "executes":
        return _result("rejected", "fling_leppa_intrinsic_state_invalid", common)

    pp_authority = freeze_runtime_d0_current_opponent_move_pp_state_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    common = {**common, "current_pp_authority": deepcopy(pp_authority)}
    if pp_authority.get("status") != "resolved":
        return _result(
            pp_authority.get("status") if pp_authority.get("status") in {"incomplete", "rejected"} else "rejected",
            pp_authority.get("reason", "fling_leppa_current_pp_unavailable"),
            common,
        )
    if pp_authority.get("opponent_actor") != dict(target):
        return _result("rejected", "fling_leppa_pp_target_identity_mismatch", common)
    slots = pp_authority["ordered_pp_slots"]
    selected = next((row for row in slots if row["current_pp"] == 0), None)
    reason = "first_zero_pp" if selected is not None else None
    if selected is None:
        selected = next((row for row in slots if row["current_pp"] < row["max_pp"]), None)
        reason = "first_missing_pp" if selected is not None else None
    if selected is None:
        return _terminal(
            "no_effect_all_pp_full",
            "fling_leppa_all_pp_full",
            common,
            selected_slot_index=None,
            selected_move_id=None,
            selection_reason=None,
            pp_before=None,
            max_pp=None,
            nominal_restore=10,
            actual_restore=0,
            pp_after=None,
            external_staleness=staleness,
            timing="post_eat_pre_pending_action",
        )
    before, maximum = selected["current_pp"], selected["max_pp"]
    nominal = family["ordinary_restore_amount"]
    actual = min(nominal, maximum - before)
    return _terminal(
        "pp_restored",
        "fling_leppa_pp_restored",
        common,
        selected_slot_index=selected["slot_index"],
        selected_move_id=selected["move_id"],
        selection_reason=reason,
        pp_before=before,
        max_pp=maximum,
        nominal_restore=nominal,
        actual_restore=actual,
        pp_after=before + actual,
        external_staleness=staleness,
        timing="post_eat_pre_pending_action",
    )


def materialize_detached_fling_leppa_pp_restore_target_effect(
    *, authority: Mapping[str, Any], source_leaf: Mapping[str, Any],
) -> dict[str, Any]:
    if authority.get("status") != "resolved" or authority.get("schema_version") != SCHEMA_VERSION:
        return {"status": "rejected", "schema_version": DETACHED_SCHEMA_VERSION, "reason": "fling_leppa_authority_invalid"}
    if authority.get("outcome") == "not_applicable":
        return {
            "status": "not_applicable",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "outcome": "not_applicable",
            "authority": deepcopy(dict(authority)),
        }
    if not validate_fling_leppa_pp_restore_target_effect_authority(authority):
        return {"status": "rejected", "schema_version": DETACHED_SCHEMA_VERSION, "reason": "fling_leppa_authority_validation_failed"}
    if source_leaf.get("leaf_id") != authority.get("source_leaf_id"):
        return {"status": "rejected", "schema_version": DETACHED_SCHEMA_VERSION, "reason": "fling_leppa_source_leaf_mismatch"}
    payload = {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": authority["outcome"],
        "item_id": authority["item_id"],
        "target": deepcopy(authority["target"]),
        "selected_slot_index": authority["selected_slot_index"],
        "selected_move_id": authority["selected_move_id"],
        "selection_reason": authority["selection_reason"],
        "pp_before": authority["pp_before"],
        "max_pp": authority["max_pp"],
        "nominal_restore": authority["nominal_restore"],
        "actual_restore": authority["actual_restore"],
        "pp_after": authority["pp_after"],
        "external_staleness": deepcopy(authority["external_staleness"]),
        "timing": authority["timing"],
        "authority": deepcopy(dict(authority)),
        "provenance": "detached_authenticated_fling_leppa_pp_restore_v1",
    }
    updated = deepcopy(dict(source_leaf))
    consequences = deepcopy(dict(updated.get("consequences", {})))
    consequences["fling_leppa_pp_restore_target_effect"] = deepcopy(payload)
    updated["consequences"] = consequences
    return {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": authority["outcome"],
        "leaf": updated,
        "consequence": payload,
        "provenance": payload["provenance"],
    }


def validate_fling_leppa_pp_restore_target_effect_authority(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("status") != "resolved"
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("outcome") not in {
            "pp_restored", "no_effect_all_pp_full", "intrinsic_suppressed_by_target_klutz",
        }
    ):
        return False
    family = resolve_canonical_fling_leppa_pp_restore_berry(value.get("item_id"))
    execution = value.get("fling_execution_authority")
    interaction = value.get("berry_eat_item_interaction_authority")
    direct = assess_fling_berry_target_eat_item_consequence_readiness(interaction)
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(interaction)
    if (
        family.get("status") != "resolved"
        or value.get("berry_family_authority") != family
        or not isinstance(execution, Mapping)
        or execution.get("schema_version") != _EXECUTION_SCHEMA
        or execution.get("status") != "resolved"
        or execution.get("outcome") != "ready_throw"
        or execution.get("fling_leppa_pp_restore_support") != _SUPPORT
        or execution.get("fling_leppa_pp_restore_berry_authority") != family
        or execution.get("resolved_base_power") != 10
        or execution.get("actor") != value.get("actor")
        or execution.get("target") != value.get("target")
        or execution.get("action_id") != value.get("action_id")
        or execution.get("user_item_before", {}).get("value") != "leppa-berry"
        or not isinstance(interaction, Mapping)
        or interaction.get("schema_version") != _EAT_SCHEMA
        or interaction.get("status") != "resolved"
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
        or interaction.get("fling_execution_authority") != execution
        or interaction.get("source_hit", {}).get("source_leaf_id") != value.get("source_leaf_id")
        or direct.get("status") != "resolved" or direct.get("readiness") != "ready"
        or value.get("target_eat_item_consequence_readiness") != direct
        or intrinsic.get("status") != "resolved"
        or value.get("target_intrinsic_on_eat_readiness") != intrinsic
        or value.get("external_staleness") != family["external_staleness"]
        or value.get("timing") != "post_eat_pre_pending_action"
    ):
        return False
    outcome = value["outcome"]
    if intrinsic.get("readiness") == "suppressed_by_target_klutz":
        return (
            outcome == "intrinsic_suppressed_by_target_klutz"
            and value.get("current_pp_authority") is None
            and all(value.get(key) is None for key in (
                "selected_slot_index", "selected_move_id", "selection_reason",
                "pp_before", "max_pp", "pp_after",
            ))
            and value.get("nominal_restore") == 0
            and value.get("actual_restore") == 0
        )
    if intrinsic.get("readiness") != "executes":
        return False
    pp = value.get("current_pp_authority")
    if (
        not validate_runtime_d0_current_opponent_move_pp_state_authority(pp)
        or pp.get("schema_version") != _PP_SCHEMA
        or pp.get("opponent_actor") != value.get("target")
        or any(pp.get(key) != value.get(key) for key in _BINDING_KEYS)
    ):
        return False
    slots = pp.get("ordered_pp_slots")
    if not isinstance(slots, tuple) or len(slots) != 4:
        return False
    selected = next((row for row in slots if row.get("current_pp") == 0), None)
    expected_reason = "first_zero_pp" if selected is not None else None
    if selected is None:
        selected = next((row for row in slots if row.get("current_pp") < row.get("max_pp")), None)
        expected_reason = "first_missing_pp" if selected is not None else None
    if selected is None:
        return (
            outcome == "no_effect_all_pp_full"
            and all(value.get(key) is None for key in (
                "selected_slot_index", "selected_move_id", "selection_reason",
                "pp_before", "max_pp", "pp_after",
            ))
            and value.get("nominal_restore") == 10
            and value.get("actual_restore") == 0
        )
    before, maximum = selected["current_pp"], selected["max_pp"]
    actual = min(10, maximum - before)
    return (
        outcome == "pp_restored"
        and value.get("selected_slot_index") == selected["slot_index"]
        and value.get("selected_move_id") == selected["move_id"]
        and value.get("selection_reason") == expected_reason
        and value.get("pp_before") == before
        and value.get("max_pp") == maximum
        and value.get("nominal_restore") == 10
        and value.get("actual_restore") == actual
        and value.get("pp_after") == before + actual
    )


def validate_detached_fling_leppa_pp_restore_target_effect(
    *, consequence: Any, source_leaf: Mapping[str, Any], expected_target: Mapping[str, Any],
) -> bool:
    if (
        not isinstance(consequence, Mapping)
        or consequence.get("status") != "resolved"
        or consequence.get("schema_version") != DETACHED_SCHEMA_VERSION
        or consequence.get("target") != dict(expected_target)
        or consequence.get("provenance") != "detached_authenticated_fling_leppa_pp_restore_v1"
        or not validate_fling_leppa_pp_restore_target_effect_authority(consequence.get("authority"))
    ):
        return False
    authority = consequence["authority"]
    if authority.get("source_leaf_id") != source_leaf.get("leaf_id"):
        return False
    for key in (
        "outcome", "item_id", "selected_slot_index", "selected_move_id",
        "selection_reason", "pp_before", "max_pp", "nominal_restore",
        "actual_restore", "pp_after", "external_staleness", "timing",
    ):
        if consequence.get(key) != authority.get(key):
            return False
    forbidden = {
        "target_item_after", "item_after", "consumed_target_item",
        "held_item_consumption", "replacement_item",
    }
    return forbidden.isdisjoint(consequence)


def _base(d0: Any, execution: Any, actor: Any, target: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or active.get("self") != dict(actor)
        or active.get("opponent") != dict(target)
        or d0.get("decision_owner") != dict(actor)
    ):
        return "fling_leppa_owner_binding_invalid"
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
        return "fling_leppa_execution_authority_invalid"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_leppa_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if not isinstance(item, Mapping) or item.get("status") != "known" or item.get("value") != "leppa-berry":
        return "fling_leppa_item_identity_invalid"
    return {
        "schema_version": SCHEMA_VERSION,
        **deepcopy(expected),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": execution["action_id"],
        "move_id": "fling",
        "item_id": "leppa-berry",
        "fling_execution_authority": deepcopy(dict(execution)),
    }


def _source_leaf_binding(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if (
        not isinstance(value, Mapping)
        or value.get("candidate_id") != base["action_id"]
        or not isinstance(value.get("leaf_id"), str)
        or not isinstance(value.get("consequences"), Mapping)
        or not isinstance(value.get("provenance"), Mapping)
    ):
        return "fling_leppa_source_leaf_invalid"
    p, c = value["provenance"], value["consequences"]
    if any(p.get(key) != base.get(key) for key in _BINDING_KEYS):
        return "fling_leppa_source_leaf_binding_mismatch"
    if (
        p.get("attacker") != base["actor"]
        or p.get("target") != base["target"]
        or p.get("move_id") != "fling"
        or p.get("fling_execution_authority") != base["fling_execution_authority"]
    ):
        return "fling_leppa_source_leaf_identity_mismatch"
    return {
        "leaf_id": value["leaf_id"],
        "candidate_id": value["candidate_id"],
        "hit_state": value.get("hit_state"),
        "source_hit_context": deepcopy(c.get("source_hit_context")),
        "target_final_hp": c.get("target_final_hp"),
        "target_ko": c.get("target_ko"),
    }


def _interaction_error(value: Any, *, base: Mapping[str, Any], source_leaf_id: str) -> str | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != _EAT_SCHEMA:
        return "fling_leppa_eat_item_authority_invalid"
    if value.get("status") != "resolved":
        return value.get("reason", "fling_leppa_eat_item_authority_unresolved")
    if (
        value.get("phase") != "post_hit_target_berry_interaction"
        or value.get("actor") != base["actor"]
        or value.get("target") != base["target"]
        or value.get("action_id") != base["action_id"]
        or value.get("item_id") != "leppa-berry"
        or value.get("fling_execution_authority") != base["fling_execution_authority"]
        or any(value.get(key) != base.get(key) for key in _BINDING_KEYS)
    ):
        return "fling_leppa_eat_item_binding_mismatch"
    source_hit = value.get("source_hit")
    if not isinstance(source_hit, Mapping) or source_hit.get("source_leaf_id") != source_leaf_id:
        return "fling_leppa_eat_item_source_leaf_mismatch"
    return None


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"


def _terminal(outcome: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": "resolved",
        **deepcopy(dict(base)),
        "outcome": outcome,
        "reason": reason,
        **deepcopy(extra),
        "provenance": "strict_runtime_d0_fling_leppa_pp_restore_target_effect_v1",
    }


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
        **deepcopy(extra),
    }
