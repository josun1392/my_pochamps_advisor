"""Exact thrown Oran/Sitrus Fling target healing authority and detached consequence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_hp_restore_berry import (
    nominal_fling_hp_restore_amount,
    resolve_canonical_fling_hp_restore_berry,
)
from llm.advisor_detached_current_healing_prevented_at_item_check_authority import (
    materialize_detached_current_healing_prevented_at_item_check_authority,
)
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
    assess_fling_berry_target_intrinsic_on_eat_readiness,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_current_healing_prevented_authority,
    runtime_strategy_d0_freshness,
)

SCHEMA_VERSION = "runtime-d0-fling-hp-restore-berry-target-effect-authority-v1"
DETACHED_SCHEMA_VERSION = "detached-fling-hp-restore-berry-target-effect-v1"
_EXECUTION_SCHEMA = "runtime-d0-fling-item-execution-authority-v1"
_EAT_SCHEMA = "runtime-d0-fling-berry-eat-item-interaction-authority-v1"
_SUPPORT = "fling_hp_restore_berry_target_effect_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_BINDING_KEYS = (
    "session_id", "source_runtime_fingerprint",
    "source_branch_fingerprint", "decision_owner",
)


def freeze_runtime_d0_fling_hp_restore_berry_target_effect_authority(
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

    family = resolve_canonical_fling_hp_restore_berry(base["item_id"])
    if family.get("status") != "resolved":
        return _result(
            "rejected" if family.get("status") == "rejected" else "unsupported",
            family.get("reason", "fling_hp_restore_berry_family_unavailable"),
            base,
        )
    common = {**base, "berry_family_authority": deepcopy(family)}
    if (
        fling_execution_authority.get("fling_hp_restore_berry_support") != _SUPPORT
        or fling_execution_authority.get("fling_hp_restore_berry_authority") != family
        or fling_execution_authority.get("resolved_base_power") != 10
    ):
        return _result(
            "rejected", "fling_hp_restore_berry_execution_family_binding_mismatch",
            common,
        )

    leaf = _source_leaf_binding(source_leaf, base)
    if isinstance(leaf, str):
        return _result("rejected", leaf, common)
    common = {
        **common,
        "source_leaf_id": source_leaf["leaf_id"],
        "source_leaf_binding": deepcopy(leaf),
        "berry_eat_item_interaction_authority": deepcopy(
            dict(berry_eat_item_interaction_authority)
        ),
    }
    interaction_error = _interaction_error(
        berry_eat_item_interaction_authority,
        base=base,
        source_leaf_id=source_leaf["leaf_id"],
    )
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
            post_hit_hp=leaf.get("target_final_hp"),
        )
    if (
        outcome != "post_hit_target_eat_item_dispatched"
        or berry_eat_item_interaction_authority.get("target_eat_occurred") is not True
        or berry_eat_item_interaction_authority.get("target_eat_item_dispatched") is not True
    ):
        return _result("rejected", "fling_hp_restore_berry_eat_prerequisite_invalid", common)

    direct = assess_fling_berry_target_eat_item_consequence_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {**common, "target_eat_item_consequence_readiness": deepcopy(direct)}
    if direct.get("status") != "resolved" or direct.get("readiness") != "ready":
        status = direct.get("status") if direct.get("status") in {"incomplete", "rejected"} else "rejected"
        return _result(
            status,
            direct.get("reason", "fling_hp_restore_berry_direct_eat_item_not_ready"),
            common,
        )

    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(
        berry_eat_item_interaction_authority,
    )
    common = {**common, "target_intrinsic_on_eat_readiness": deepcopy(intrinsic)}
    if intrinsic.get("status") != "resolved":
        status = intrinsic.get("status") if intrinsic.get("status") in {"incomplete", "rejected"} else "rejected"
        return _result(
            status,
            intrinsic.get("reason", "fling_hp_restore_berry_intrinsic_on_eat_unavailable"),
            common,
        )

    post_hp = leaf.get("target_final_hp")
    if not isinstance(post_hp, int) or isinstance(post_hp, bool) or post_hp < 0:
        return _result("incomplete", "fling_hp_restore_post_hit_hp_unknown", common)
    raw = _pokemon(runtime_snapshot, target)
    maximum = raw.get("max_hp") if isinstance(raw, Mapping) else None
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0 or post_hp > maximum:
        return _result("incomplete", "fling_hp_restore_max_hp_unknown", common)
    max_hp_authority = {
        "status": "resolved",
        "schema_version": "runtime-d0-fling-target-max-hp-authority-v1",
        "owner": deepcopy(dict(target)),
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "maximum_hp": maximum,
        "provenance": "exact_runtime_target_max_hp_v1",
    }
    common = {
        **common,
        "post_hit_hp": post_hp,
        "maximum_hp": maximum,
        "target_max_hp_authority": max_hp_authority,
        "heal_family": family["heal_family"],
    }

    if intrinsic.get("readiness") == "suppressed_by_target_klutz":
        return _terminal(
            "intrinsic_suppressed_by_target_klutz",
            "fling_hp_restore_berry_intrinsic_on_eat_suppressed",
            common,
            nominal_heal=0,
            actual_heal=0,
            final_hp=post_hp,
            healing_prevented_at_item_check=None,
        )
    if intrinsic.get("readiness") != "executes":
        return _result("rejected", "fling_hp_restore_berry_intrinsic_state_invalid", common)

    current = freeze_runtime_d0_current_healing_prevented_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        recipient=target,
    )
    item_check = materialize_detached_current_healing_prevented_at_item_check_authority(
        strategy_d0=strategy_d0,
        terminal_leaf=source_leaf,
        recipient=target,
        current_healing_prevented_authority=current,
    )
    common = {
        **common,
        "current_healing_prevented_authority": deepcopy(current),
        "healing_prevented_at_item_check": deepcopy(item_check),
    }
    if item_check.get("status") != "resolved":
        status = item_check.get("status") if item_check.get("status") in {"incomplete", "rejected"} else "rejected"
        return _result(
            status,
            item_check.get("reason", "fling_hp_restore_healing_prevented_unknown"),
            common,
        )

    nominal = nominal_fling_hp_restore_amount(family=family, maximum_hp=maximum)
    if item_check.get("state") == "known_present":
        return _terminal(
            "healing_prevented",
            "fling_hp_restore_try_heal_blocked",
            common,
            nominal_heal=nominal,
            actual_heal=0,
            final_hp=post_hp,
        )
    if item_check.get("state") != "known_absent":
        return _result("incomplete", "fling_hp_restore_healing_prevented_unknown", common)

    actual = min(nominal, maximum - post_hp)
    final_hp = post_hp + actual
    return _terminal(
        "healed" if actual > 0 else "no_effect_full_hp",
        "fling_hp_restore_battle_heal_applied" if actual > 0 else "fling_hp_restore_target_full_hp",
        common,
        nominal_heal=nominal,
        actual_heal=actual,
        final_hp=final_hp,
    )


def materialize_detached_fling_hp_restore_berry_target_effect(
    *, authority: Mapping[str, Any], source_leaf: Mapping[str, Any],
) -> dict[str, Any]:
    if not validate_fling_hp_restore_berry_target_effect_authority(authority):
        return {
            "status": "rejected",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "reason": "fling_hp_restore_berry_target_effect_authority_invalid",
        }
    outcome = authority["outcome"]
    if outcome == "not_applicable":
        return {
            "status": "not_applicable",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "outcome": outcome,
            "authority": deepcopy(dict(authority)),
        }
    if source_leaf.get("leaf_id") != authority.get("source_leaf_id"):
        return {
            "status": "rejected",
            "schema_version": DETACHED_SCHEMA_VERSION,
            "reason": "fling_hp_restore_source_leaf_mismatch",
        }
    updated = deepcopy(dict(source_leaf))
    consequences = deepcopy(dict(updated.get("consequences", {})))
    consequences["target_final_hp"] = authority["final_hp"]
    consequences["target_ko"] = False
    payload = {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": outcome,
        "item_id": authority["item_id"],
        "heal_family": authority["heal_family"],
        "target": deepcopy(authority["target"]),
        "post_hit_hp": authority["post_hit_hp"],
        "maximum_hp": authority["maximum_hp"],
        "nominal_heal": authority["nominal_heal"],
        "actual_heal": authority["actual_heal"],
        "final_hp": authority["final_hp"],
        "authority": deepcopy(dict(authority)),
        "provenance": "detached_authenticated_fling_hp_restore_berry_target_effect_v1",
    }
    consequences["fling_hp_restore_berry_target_effect"] = deepcopy(payload)
    updated["consequences"] = consequences
    return {
        "status": "resolved",
        "schema_version": DETACHED_SCHEMA_VERSION,
        "outcome": outcome,
        "leaf": updated,
        "consequence": payload,
        "provenance": payload["provenance"],
    }


def validate_detached_fling_hp_restore_berry_target_effect(
    *, consequence: Any, source_leaf: Mapping[str, Any], expected_target: Mapping[str, Any],
) -> bool:
    if (
        not isinstance(consequence, Mapping)
        or consequence.get("status") != "resolved"
        or consequence.get("schema_version") != DETACHED_SCHEMA_VERSION
        or consequence.get("target") != dict(expected_target)
        or consequence.get("provenance")
        != "detached_authenticated_fling_hp_restore_berry_target_effect_v1"
    ):
        return False
    authority = consequence.get("authority")
    if (
        not validate_fling_hp_restore_berry_target_effect_authority(authority)
        or authority.get("target") != dict(expected_target)
        or authority.get("source_leaf_id") != source_leaf.get("leaf_id")
    ):
        return False
    for key in (
        "item_id", "heal_family", "post_hit_hp", "maximum_hp",
        "nominal_heal", "actual_heal", "final_hp", "outcome",
    ):
        if consequence.get(key) != authority.get(key):
            return False
    forbidden = {
        "target_item_after", "item_after", "consumed_target_item",
        "held_item_consumption", "replacement_item",
    }
    return forbidden.isdisjoint(consequence)


def validate_fling_hp_restore_berry_target_effect_authority(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("status") != "resolved"
        or value.get("outcome") not in {
            "healed", "healing_prevented",
            "intrinsic_suppressed_by_target_klutz", "no_effect_full_hp",
        }
    ):
        return False
    family = resolve_canonical_fling_hp_restore_berry(value.get("item_id"))
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
        or execution.get("fling_hp_restore_berry_support") != _SUPPORT
        or execution.get("fling_hp_restore_berry_authority") != family
        or execution.get("resolved_base_power") != 10
        or execution.get("actor") != value.get("actor")
        or execution.get("target") != value.get("target")
        or execution.get("action_id") != value.get("action_id")
        or execution.get("user_item_before", {}).get("value") != value.get("item_id")
        or not isinstance(interaction, Mapping)
        or interaction.get("schema_version") != _EAT_SCHEMA
        or interaction.get("status") != "resolved"
        or interaction.get("outcome") != "post_hit_target_eat_item_dispatched"
        or interaction.get("target_eat_occurred") is not True
        or interaction.get("target_eat_item_dispatched") is not True
        or interaction.get("fling_execution_authority") != execution
        or interaction.get("source_hit", {}).get("source_leaf_id") != value.get("source_leaf_id")
        or direct.get("status") != "resolved"
        or direct.get("readiness") != "ready"
        or value.get("target_eat_item_consequence_readiness") != direct
        or intrinsic.get("status") != "resolved"
        or value.get("target_intrinsic_on_eat_readiness") != intrinsic
    ):
        return False
    maximum = value.get("maximum_hp")
    post = value.get("post_hit_hp")
    nominal = value.get("nominal_heal")
    actual = value.get("actual_heal")
    final = value.get("final_hp")
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (maximum, post, nominal, actual, final)):
        return False
    if maximum <= 0 or post < 0 or post > maximum or actual < 0 or final != post + actual or final > maximum:
        return False
    leaf_binding = value.get("source_leaf_binding")
    max_hp_authority = value.get("target_max_hp_authority")
    if (
        not isinstance(leaf_binding, Mapping)
        or leaf_binding.get("target_final_hp") != post
        or not isinstance(max_hp_authority, Mapping)
        or max_hp_authority.get("status") != "resolved"
        or max_hp_authority.get("schema_version") != "runtime-d0-fling-target-max-hp-authority-v1"
        or max_hp_authority.get("owner") != value.get("target")
        or max_hp_authority.get("maximum_hp") != maximum
        or max_hp_authority.get("provenance") != "exact_runtime_target_max_hp_v1"
        or any(
            max_hp_authority.get(key) != value.get(key)
            for key in _BINDING_KEYS
        )
    ):
        return False
    outcome = value["outcome"]
    if intrinsic.get("readiness") == "suppressed_by_target_klutz":
        return (
            outcome == "intrinsic_suppressed_by_target_klutz"
            and nominal == 0 and actual == 0 and final == post
            and value.get("healing_prevented_at_item_check") is None
        )
    if intrinsic.get("readiness") != "executes":
        return False
    expected_nominal = nominal_fling_hp_restore_amount(family=family, maximum_hp=maximum)
    check = value.get("healing_prevented_at_item_check")
    if not isinstance(check, Mapping) or check.get("status") != "resolved":
        return False
    if nominal != expected_nominal:
        return False
    if check.get("state") == "known_present":
        return outcome == "healing_prevented" and actual == 0 and final == post
    if check.get("state") != "known_absent":
        return False
    expected_actual = min(nominal, maximum - post)
    expected_outcome = "healed" if expected_actual > 0 else "no_effect_full_hp"
    return actual == expected_actual and final == post + expected_actual and outcome == expected_outcome


def _base(d0: Any, execution: Any, actor: Any, target: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "invalid_runtime_strategy_d0"
    if not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return "fling_hp_restore_owner_identity_invalid"
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or active.get(actor["side"]) != dict(actor)
        or active.get(target["side"]) != dict(target)
        or d0.get("decision_owner") != dict(actor)
    ):
        return "fling_hp_restore_owner_binding_invalid"
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
        return "fling_hp_restore_execution_authority_invalid"
    expected = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        return "fling_hp_restore_execution_binding_mismatch"
    item = execution.get("user_item_before")
    if not isinstance(item, Mapping) or item.get("status") != "known" or not isinstance(item.get("value"), str):
        return "fling_hp_restore_item_identity_unknown"
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
        or not isinstance(value.get("consequences"), Mapping)
        or not isinstance(value.get("provenance"), Mapping)
    ):
        return "fling_hp_restore_source_leaf_invalid"
    p = value["provenance"]
    c = value["consequences"]
    if any(p.get(key) != base.get(key) for key in _BINDING_KEYS):
        return "fling_hp_restore_source_leaf_binding_mismatch"
    if (
        p.get("attacker") != base["actor"]
        or p.get("target") != base["target"]
        or p.get("move_id") != "fling"
        or p.get("fling_execution_authority") != base["fling_execution_authority"]
    ):
        return "fling_hp_restore_source_leaf_identity_mismatch"
    return {
        "leaf_id": value["leaf_id"],
        "candidate_id": value["candidate_id"],
        "hit_state": value.get("hit_state"),
        "source_hit_context": deepcopy(c.get("source_hit_context")),
        "target_final_hp": c.get("target_final_hp"),
        "target_ko": c.get("target_ko"),
        "provenance": {
            key: deepcopy(p.get(key))
            for key in (*_BINDING_KEYS, "attacker", "target", "move_id", "fling_execution_authority")
        },
    }


def _interaction_error(value: Any, *, base: Mapping[str, Any], source_leaf_id: str) -> str | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != _EAT_SCHEMA:
        return "fling_hp_restore_eat_item_authority_invalid"
    if value.get("status") != "resolved":
        return value.get("reason", "fling_hp_restore_eat_item_authority_unresolved")
    if (
        value.get("phase") != "post_hit_target_berry_interaction"
        or value.get("actor") != base["actor"]
        or value.get("target") != base["target"]
        or value.get("action_id") != base["action_id"]
        or value.get("item_id") != base["item_id"]
        or value.get("fling_execution_authority") != base["fling_execution_authority"]
        or any(value.get(key) != base.get(key) for key in _BINDING_KEYS)
    ):
        return "fling_hp_restore_eat_item_authority_binding_mismatch"
    source_hit = value.get("source_hit")
    if not isinstance(source_hit, Mapping) or source_hit.get("source_leaf_id") != source_leaf_id:
        return "fling_hp_restore_eat_item_source_leaf_mismatch"
    return None


def _pokemon(snapshot: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
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
        and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _status(value: Any) -> str:
    if isinstance(value, Mapping) and value.get("status") in {"incomplete", "unsupported", "rejected"}:
        return value["status"]
    return "rejected"


def _terminal(outcome: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": "resolved",
        **deepcopy(dict(base)),
        "outcome": outcome,
        "reason": reason,
        **deepcopy(extra),
        "provenance": "strict_runtime_d0_fling_hp_restore_berry_target_effect_v1",
    }


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
    }
