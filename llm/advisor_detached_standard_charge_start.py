"""Detached deterministic materialization of one ordinary standard charge start."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import (
    resolve_canonical_charge_move_lifecycle,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_standard_charge_turn_self_stage_effect import (
    freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority,
    stage_effect_consequence,
)
from llm.advisor_observed_damage_application import apply_canonical_stage_delta
from llm.advisor_detached_semi_invulnerable_charge_authority import (
    materialize_detached_semi_invulnerable_charge_state_authority,
    validate_detached_semi_invulnerable_charge_state_authority,
)


SCHEMA_VERSION = "detached-standard-charge-start-v1"
CONTEXT_SCHEMA_VERSION = "detached-standard-charge-lifecycle-context-v1"
_READINESS_SCHEMA = "runtime-d0-standard-charge-start-readiness-authority-v1"
_SUPPORTED_MOVES = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade", "meteor-beam", "skull-bash", "fly", "dig", "dive", "bounce", "phantom-force", "shadow-force"})
_SOLAR_MOVES = frozenset({"solar-beam", "solar-blade"})
_SELF_EFFECT_MOVES = frozenset({"meteor-beam", "skull-bash"})
_SEMI_INVULNERABLE_MOVES = frozenset({"fly", "dig", "dive", "bounce", "phantom-force", "shadow-force"})


def materialize_detached_standard_charge_start(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    readiness_authority: Mapping[str, Any],
) -> dict[str, Any]:
    base = _base(strategy_d0, runtime_snapshot, action, actor, target)
    if isinstance(base, str):
        return _result("rejected", base, {})
    readiness_error = _readiness_error(readiness_authority, base)
    if readiness_error is not None:
        status, reason = readiness_error
        return _result(status, reason, base)

    state = runtime_snapshot.get("state")
    actor_row = _pokemon(state, actor)
    target_row = _pokemon(state, target)
    if actor_row is None:
        return _result("rejected", "standard_charge_actor_no_longer_active", base)
    if target_row is None:
        return _result("rejected", "standard_charge_target_position_no_longer_current", base)
    actor_hp = _exact_hp(actor_row)
    target_hp = _exact_hp(target_row)
    if actor_hp is None or target_hp is None:
        return _result("incomplete", "standard_charge_current_hp_authority_incomplete", base)
    if actor_row.get("fainted") is True:
        return _result("rejected", "standard_charge_actor_already_fainted", base)
    if target_row.get("fainted") is True:
        return _result("rejected", "standard_charge_target_no_longer_actionable", base)

    canonical = readiness_authority["canonical_charge_lifecycle_authority"]
    self_stage_authority = None
    if base["move_id"] in _SELF_EFFECT_MOVES:
        self_stage_authority = freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            action=action,
            actor=actor,
            target=target,
        )
        if self_stage_authority.get("status") != "resolved":
            return _result(
                self_stage_authority.get("status", "incomplete"),
                self_stage_authority.get("reason", "standard_charge_turn_self_stage_effect_unavailable"),
                base,
            )
    leaf_id = f"{base['action_id']}:charge-start"
    semi_state_authority = None
    if base["move_id"] in _SEMI_INVULNERABLE_MOVES:
        semi_state_authority = materialize_detached_semi_invulnerable_charge_state_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, actor=actor, target=target,
            action_id=base["action_id"], move_id=base["move_id"], source_leaf_id=leaf_id,
        )
        if semi_state_authority.get("status") != "resolved":
            return _result(semi_state_authority.get("status", "rejected"), semi_state_authority.get("reason", "semi_invulnerable_charge_state_unavailable"), base)
    probability = {"numerator": 1, "denominator": 1}
    context = {
        "status": "resolved",
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "state": "charging",
        "phase": "turn_one_charge_started",
        "actor": deepcopy(dict(actor)),
        "action_id": base["action_id"],
        "move_id": base["move_id"],
        "canonical_lifecycle_family": canonical["lifecycle_family"],
        "execution_model": canonical["execution_model"],
        "source_target_owner": deepcopy(dict(target)),
        "continuation_target_locator": deepcopy(
            readiness_authority["continuation_target_locator"]
        ),
        "source_charge_start_leaf_id": leaf_id,
        "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"],
        "readiness_authority": deepcopy(dict(readiness_authority)),
        "power_herb_applicability_state": deepcopy(
            readiness_authority["power_herb_applicability_state"]
        ),
        "turn_two_continuation_required": True,
        "immediate_damage_executed": False,
        "charge_turn_damage": 0,
        "pp_consumption_materialized": False,
        **({"semi_invulnerable_charge_state_authority": deepcopy(dict(semi_state_authority))} if isinstance(semi_state_authority, Mapping) else {}),
        "provenance": "detached_standard_charge_lifecycle_context_v1",
    }
    leaf = {
        "leaf_id": leaf_id,
        "candidate_id": f"attack:{base['move_id']}",
        "action_type": "attack",
        "branch_path": ("standard_charge_start",),
        "probability": probability,
        "hit_state": "not_applicable",
        "critical_state": "not_applicable",
        "critical_hit_state": "not_applicable",
        "damage_roll": "not_applicable",
        "contact_state": "not_applicable",
        "secondary_effect_state": "none",
        "damage": 0,
        "consequences": {
            "damage": 0,
            "own_final_hp": actor_hp,
            "actor_final_hp": actor_hp,
            "target_final_hp": target_hp,
            "self_fainted": False,
            "actor_ko": False,
            "target_ko": False,
            "secondary": None,
            "contact": "not_applicable",
            "detached_standard_charge_lifecycle_context": deepcopy(context),
            **(
                {"charge_turn_self_stage_effect": stage_effect_consequence(self_stage_authority)}
                if isinstance(self_stage_authority, Mapping)
                else {}
            ),
            **({"semi_invulnerable_charge_state": deepcopy(dict(semi_state_authority))} if isinstance(semi_state_authority, Mapping) else {}),
        },
        "provenance": {
            "session_id": base["session_id"],
            "source_runtime_fingerprint": base["source_runtime_fingerprint"],
            "source_branch_fingerprint": base["source_branch_fingerprint"],
            "decision_owner": deepcopy(base["decision_owner"]),
            "attacker": deepcopy(dict(actor)),
            "target": deepcopy(dict(target)),
            "move_id": base["move_id"],
            "action_id": base["action_id"],
            "standard_charge_start_readiness_authority": deepcopy(
                dict(readiness_authority)
            ),
            "execution_opportunity_granted_by_outer_gate": True,
            "immediate_damage_execution_grant": False,
        },
    }

    post_snapshot = deepcopy(dict(runtime_snapshot))
    post_snapshot["detached_standard_charge_lifecycle_context"] = deepcopy(context)

    result = {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(base),
        "outcome": "charge_started",
        "probability": probability,
        "action_leaf": leaf,
        "detached_charge_lifecycle_context": context,
        **({"charge_turn_self_stage_effect_authority": deepcopy(dict(self_stage_authority))} if isinstance(self_stage_authority, Mapping) else {}),
        **({"semi_invulnerable_charge_state_authority": deepcopy(dict(semi_state_authority))} if isinstance(semi_state_authority, Mapping) else {}),
        "post_action_runtime_snapshot": post_snapshot,
        "action_execution_opportunity_consumed": True,
        "immediate_damage_executed": False,
        "pp_consumption_materialized": False,
        "provenance": "detached_standard_charge_start_from_readiness_v1",
    }
    if not validate_detached_standard_charge_start(
        result=result,
        strategy_d0=strategy_d0,
        source_runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
    ):
        return _result("rejected", "detached_standard_charge_start_validation_failed", base)
    return result


def validate_detached_standard_charge_start(
    *,
    result: Any,
    strategy_d0: Mapping[str, Any],
    source_runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> bool:
    if not isinstance(result, Mapping):
        return False
    base = _base(strategy_d0, source_runtime_snapshot, action, actor, target)
    if isinstance(base, str):
        return False
    if (
        result.get("status") != "resolved"
        or result.get("schema_version") != SCHEMA_VERSION
        or result.get("outcome") != "charge_started"
        or result.get("probability") != {"numerator": 1, "denominator": 1}
        or result.get("action_execution_opportunity_consumed") is not True
        or result.get("immediate_damage_executed") is not False
        or result.get("pp_consumption_materialized") is not False
    ):
        return False
    for key in (
        "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
        "decision_owner", "actor", "source_target_owner", "action_id", "move_id",
    ):
        if result.get(key) != base.get(key):
            return False

    readiness = result.get("detached_charge_lifecycle_context", {}).get(
        "readiness_authority"
    )
    readiness_error = _readiness_error(readiness, base)
    if readiness_error is not None:
        return False
    context = result.get("detached_charge_lifecycle_context")
    leaf = result.get("action_leaf")
    post_snapshot = result.get("post_action_runtime_snapshot")
    if not isinstance(context, Mapping) or not isinstance(leaf, Mapping):
        return False
    if (
        context.get("status") != "resolved"
        or context.get("schema_version") != CONTEXT_SCHEMA_VERSION
        or context.get("state") != "charging"
        or context.get("phase") != "turn_one_charge_started"
        or context.get("actor") != actor
        or context.get("action_id") != base["action_id"]
        or context.get("move_id") != base["move_id"]
        or context.get("canonical_lifecycle_family") != _expected_family(base["move_id"])
        or context.get("execution_model") != ("semi_invulnerable_then_execute" if base["move_id"] in _SEMI_INVULNERABLE_MOVES else "charge_then_execute")
        or context.get("source_target_owner") != target
        or context.get("continuation_target_locator")
        != readiness["continuation_target_locator"]
        or "pokemon_id" in context.get("continuation_target_locator", {})
        or context.get("source_charge_start_leaf_id") != leaf.get("leaf_id")
        or context.get("source_runtime_fingerprint")
        != base["source_runtime_fingerprint"]
        or context.get("source_branch_fingerprint")
        != base["source_branch_fingerprint"]
        or context.get("power_herb_applicability_state")
        != readiness.get("power_herb_applicability_state")
        or context.get("turn_two_continuation_required") is not True
        or context.get("immediate_damage_executed") is not False
        or context.get("charge_turn_damage") != 0
        or context.get("pp_consumption_materialized") is not False
    ):
        return False
    if context.get("power_herb_applicability_state", {}).get("status") == "active":
        return False

    source_state = source_runtime_snapshot.get("state")
    actor_row = _pokemon(source_state, actor)
    target_row = _pokemon(source_state, target)
    actor_hp = _exact_hp(actor_row) if actor_row is not None else None
    target_hp = _exact_hp(target_row) if target_row is not None else None
    if actor_hp is None or target_hp is None:
        return False

    consequences = leaf.get("consequences")
    provenance = leaf.get("provenance")
    stage_consequence = consequences.get("charge_turn_self_stage_effect") if isinstance(consequences, Mapping) else None
    stage_authority = result.get("charge_turn_self_stage_effect_authority")
    if base["move_id"] in _SELF_EFFECT_MOVES:
        expected_stage = freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=source_runtime_snapshot,
            action=action,
            actor=actor,
            target=target,
        )
        if (
            expected_stage.get("status") != "resolved"
            or stage_authority != expected_stage
            or stage_consequence != stage_effect_consequence(expected_stage)
        ):
            return False
    elif stage_consequence is not None or stage_authority is not None:
        return False
    semi_consequence = consequences.get("semi_invulnerable_charge_state") if isinstance(consequences, Mapping) else None
    semi_authority = result.get("semi_invulnerable_charge_state_authority")
    if base["move_id"] in _SEMI_INVULNERABLE_MOVES:
        if context.get("semi_invulnerable_charge_state_authority") != semi_authority or semi_authority != semi_consequence or validate_detached_semi_invulnerable_charge_state_authority(semi_authority, strategy_d0=strategy_d0, runtime_snapshot=source_runtime_snapshot) is not None:
            return False
    elif semi_consequence is not None or semi_authority is not None or context.get("semi_invulnerable_charge_state_authority") is not None:
        return False
    if (
        leaf.get("leaf_id") != f"{base['action_id']}:charge-start"
        or leaf.get("candidate_id") != f"attack:{base['move_id']}"
        or leaf.get("action_type") != "attack"
        or tuple(leaf.get("branch_path", ())) != ("standard_charge_start",)
        or leaf.get("probability") != {"numerator": 1, "denominator": 1}
        or leaf.get("hit_state") != "not_applicable"
        or leaf.get("critical_state") != "not_applicable"
        or leaf.get("critical_hit_state") != "not_applicable"
        or leaf.get("damage_roll") != "not_applicable"
        or leaf.get("contact_state") != "not_applicable"
        or leaf.get("secondary_effect_state") != "none"
        or leaf.get("damage") != 0
        or not isinstance(consequences, Mapping)
        or consequences.get("damage") != 0
        or consequences.get("own_final_hp") != actor_hp
        or consequences.get("actor_final_hp") != actor_hp
        or consequences.get("target_final_hp") != target_hp
        or consequences.get("self_fainted") is not False
        or consequences.get("actor_ko") is not False
        or consequences.get("target_ko") is not False
        or consequences.get("secondary") is not None
        or consequences.get("contact") != "not_applicable"
        or consequences.get("detached_standard_charge_lifecycle_context") != context
        or not isinstance(provenance, Mapping)
        or provenance.get("session_id") != base["session_id"]
        or provenance.get("source_runtime_fingerprint")
        != base["source_runtime_fingerprint"]
        or provenance.get("source_branch_fingerprint")
        != base["source_branch_fingerprint"]
        or provenance.get("decision_owner") != base["decision_owner"]
        or provenance.get("attacker") != actor
        or provenance.get("target") != target
        or provenance.get("move_id") != base["move_id"]
        or provenance.get("action_id") != base["action_id"]
        or provenance.get("standard_charge_start_readiness_authority") != readiness
        or provenance.get("execution_opportunity_granted_by_outer_gate") is not True
        or provenance.get("immediate_damage_execution_grant") is not False
    ):
        return False

    if not isinstance(post_snapshot, Mapping):
        return False
    expected_snapshot = deepcopy(dict(source_runtime_snapshot))
    expected_snapshot["detached_standard_charge_lifecycle_context"] = deepcopy(context)
    if post_snapshot != expected_snapshot:
        return False
    if post_snapshot.get("state") != source_runtime_snapshot.get("state"):
        return False
    if post_snapshot.get("state_fingerprint") != state_fingerprint(
        dict(source_runtime_snapshot["state"])
    ):
        return False
    return True




def validate_pair_compatible_standard_charge_leaf(leaf: Any) -> str | None:
    """Validate a standard-charge terminal leaf without current runtime access."""
    if not isinstance(leaf, Mapping):
        return "standard_charge_leaf_invalid"
    provenance = leaf.get("provenance")
    consequences = leaf.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping):
        return "standard_charge_leaf_provenance_or_consequence_missing"
    move_id = provenance.get("move_id")
    context = consequences.get("detached_standard_charge_lifecycle_context")
    if move_id not in _SUPPORTED_MOVES:
        return "unexpected_standard_charge_lifecycle_context" if context is not None else None
    if not isinstance(context, Mapping):
        return "standard_charge_lifecycle_context_missing"
    actor = provenance.get("attacker")
    target = provenance.get("target")
    action_id = provenance.get("action_id")
    if (
        not isinstance(actor, Mapping)
        or not isinstance(target, Mapping)
        or actor.get("side") == target.get("side")
        or not isinstance(action_id, str)
        or not action_id
    ):
        return "standard_charge_leaf_identity_invalid"
    base = {
        "session_id": provenance.get("session_id"),
        "source_runtime_fingerprint": provenance.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": provenance.get("source_branch_fingerprint"),
        "decision_owner": provenance.get("decision_owner"),
        "actor": actor,
        "source_target_owner": target,
        "action_id": action_id,
        "move_id": move_id,
    }
    if not all(base.get(key) is not None for key in (
        "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
        "decision_owner",
    )):
        return "standard_charge_leaf_binding_incomplete"
    readiness = provenance.get("standard_charge_start_readiness_authority")
    error = _readiness_error(readiness, base)
    if error is not None:
        return "standard_charge_leaf_readiness_invalid"
    if context.get("readiness_authority") != readiness:
        return "standard_charge_leaf_readiness_context_mismatch"
    canonical = readiness.get("canonical_charge_lifecycle_authority")
    if (
        not isinstance(canonical, Mapping)
        or canonical.get("move_id") != move_id
        or canonical.get("lifecycle_family") != _expected_family(move_id)
        or canonical.get("execution_model") != ("semi_invulnerable_then_execute" if move_id in _SEMI_INVULNERABLE_MOVES else "charge_then_execute")
    ):
        return "standard_charge_leaf_canonical_lifecycle_invalid"
    locator = context.get("continuation_target_locator")
    if (
        context.get("status") != "resolved"
        or context.get("schema_version") != CONTEXT_SCHEMA_VERSION
        or context.get("state") != "charging"
        or context.get("phase") != "turn_one_charge_started"
        or context.get("actor") != actor
        or context.get("action_id") != action_id
        or context.get("move_id") != move_id
        or context.get("canonical_lifecycle_family") != _expected_family(move_id)
        or context.get("execution_model") != ("semi_invulnerable_then_execute" if move_id in _SEMI_INVULNERABLE_MOVES else "charge_then_execute")
        or context.get("source_target_owner") != target
        or not isinstance(locator, Mapping)
        or set(locator) != {"session_id", "side", "slot_index"}
        or "pokemon_id" in locator
        or locator != readiness.get("continuation_target_locator")
        or context.get("source_charge_start_leaf_id") != leaf.get("leaf_id")
        or context.get("source_runtime_fingerprint") != provenance.get("source_runtime_fingerprint")
        or context.get("source_branch_fingerprint") != provenance.get("source_branch_fingerprint")
        or context.get("power_herb_applicability_state") != readiness.get("power_herb_applicability_state")
        or context.get("turn_two_continuation_required") is not True
        or context.get("immediate_damage_executed") is not False
        or context.get("charge_turn_damage") != 0
        or context.get("pp_consumption_materialized") is not False
    ):
        return "standard_charge_lifecycle_context_invalid"
    if context.get("power_herb_applicability_state", {}).get("status") == "active":
        return "standard_charge_active_power_herb_context_invalid"
    stage = consequences.get("charge_turn_self_stage_effect")
    if move_id in _SELF_EFFECT_MOVES:
        expected_stat = "special-attack" if move_id == "meteor-beam" else "defense"
        expected_class = "special_attack_plus_one" if move_id == "meteor-beam" else "defense_plus_one"
        authority = stage.get("authority") if isinstance(stage, Mapping) else None
        previous = stage.get("previous_stage") if isinstance(stage, Mapping) else None
        if (
            not isinstance(stage, Mapping)
            or stage.get("status") != "resolved"
            or stage.get("schema_version") != "standard-charge-turn-self-stage-effect-authority-v1"
            or stage.get("owner") != actor
            or stage.get("stat") != expected_stat
            or stage.get("delta") != 1
            or not isinstance(previous, int) or isinstance(previous, bool) or not -6 <= previous <= 6
            or stage.get("resulting_stage") != apply_canonical_stage_delta(previous, 1)
            or stage.get("action_id") != action_id
            or stage.get("move_id") != move_id
            or stage.get("timing") != "before_charge_move_event"
            or stage.get("provenance") != "exact_pre_charge_move_self_stage_transition_v1"
            or not isinstance(authority, Mapping)
            or authority.get("canonical_lifecycle") != canonical
            or authority.get("stat") != expected_stat
            or authority.get("delta") != 1
            or authority.get("previous_stage") != previous
            or authority.get("resulting_stage") != stage.get("resulting_stage")
            or authority.get("timing") != "before_charge_move_event"
            or canonical.get("charge_turn_side_effect_class") != expected_class
            or canonical.get("charge_turn_side_effect_timing") != "before_charge_move_event"
        ):
            return "standard_charge_leaf_charge_turn_self_stage_effect_invalid"
    elif stage is not None:
        return "unexpected_standard_charge_charge_turn_self_stage_effect"
    own_hp = consequences.get("own_final_hp")
    actor_hp = consequences.get("actor_final_hp")
    target_hp = consequences.get("target_final_hp")
    if (
        leaf.get("candidate_id") != f"attack:{move_id}"
        or leaf.get("action_type") != "attack"
        or tuple(leaf.get("branch_path", ())) != ("standard_charge_start",)
        or leaf.get("probability") != {"numerator": 1, "denominator": 1}
        or leaf.get("hit_state") != "not_applicable"
        or leaf.get("critical_state") != "not_applicable"
        or leaf.get("critical_hit_state") != "not_applicable"
        or leaf.get("damage_roll") != "not_applicable"
        or leaf.get("contact_state") != "not_applicable"
        or leaf.get("secondary_effect_state") != "none"
        or leaf.get("damage") != 0
        or consequences.get("damage") != 0
        or not isinstance(own_hp, int) or isinstance(own_hp, bool) or own_hp <= 0
        or actor_hp != own_hp
        or not isinstance(target_hp, int) or isinstance(target_hp, bool) or target_hp <= 0
        or consequences.get("self_fainted") is not False
        or consequences.get("actor_ko") is not False
        or consequences.get("target_ko") is not False
        or consequences.get("secondary") is not None
        or consequences.get("contact") != "not_applicable"
        or consequences.get("detached_standard_charge_lifecycle_context") != context
        or provenance.get("execution_opportunity_granted_by_outer_gate") is not True
        or provenance.get("immediate_damage_execution_grant") is not False
    ):
        return "standard_charge_leaf_no_damage_semantics_invalid"
    return None


def _base(
    d0: Any,
    snapshot: Any,
    action: Any,
    actor: Any,
    target: Any,
) -> dict[str, Any] | str:
    if (
        not isinstance(d0, Mapping)
        or d0.get("status") != "resolved"
        or not isinstance(snapshot, Mapping)
        or not isinstance(action, Mapping)
        or not isinstance(actor, Mapping)
        or not isinstance(target, Mapping)
    ):
        return "standard_charge_start_request_invalid"
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=d0, runtime_snapshot=snapshot,
    )
    if fresh.get("status") != "current":
        return fresh.get("reason", "stale_runtime_d0")
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or actor != d0.get("decision_owner")
        or active.get(actor.get("side")) != dict(actor)
        or actor.get("side") == target.get("side")
    ):
        return "standard_charge_start_actor_binding_invalid"
    target_side = "opponent" if actor.get("side") == "self" else "self"
    if target.get("side") != target_side or active.get(target_side) != dict(target):
        return "standard_charge_start_target_binding_invalid"
    action_id, move_id = action.get("action_id"), action.get("identity")
    if (
        action.get("action_type") != "attack"
        or not isinstance(action_id, str) or not action_id
        or not isinstance(move_id, str) or move_id not in _SUPPORTED_MOVES
    ):
        return "standard_charge_start_action_identity_invalid"
    return {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "actor": deepcopy(dict(actor)),
        "source_target_owner": deepcopy(dict(target)),
        "action_id": action_id,
        "move_id": move_id,
    }


def _readiness_error(
    value: Any,
    base: Mapping[str, Any],
) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return "incomplete", "standard_charge_start_readiness_authority_missing"
    status = value.get("status")
    if status != "resolved":
        return (
            status if status in {"incomplete", "unsupported", "rejected"} else "rejected",
            value.get("reason", "standard_charge_start_readiness_unavailable"),
        )
    if (
        value.get("schema_version") != _READINESS_SCHEMA
        or value.get("outcome") != "charge_start_ready"
        or value.get("next_semantic_phase") != "charge_turn_start"
        or value.get("action_execution_confirmed") is not False
        or value.get("immediate_damage_execution_grant") is not False
        or value.get("charge_turn_state_materialized") is not False
        or value.get("pp_consumed") is not False
    ):
        return "rejected", "standard_charge_start_readiness_semantics_invalid"
    expected = {
        "session_id": base["session_id"],
        "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"],
        "decision_owner": base["decision_owner"],
        "actor": base["actor"],
        "source_target_owner": base["source_target_owner"],
        "action_id": base["action_id"],
        "move_id": base["move_id"],
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        return "rejected", "standard_charge_start_readiness_binding_mismatch"
    locator = value.get("continuation_target_locator")
    target = base["source_target_owner"]
    if (
        not isinstance(locator, Mapping)
        or set(locator) != {"session_id", "side", "slot_index"}
        or locator
        != {
            "session_id": target["session_id"],
            "side": target["side"],
            "slot_index": target["slot_index"],
        }
    ):
        return "rejected", "standard_charge_start_target_locator_invalid"
    canonical = resolve_canonical_charge_move_lifecycle(base["move_id"])
    if (
        canonical.get("status") != "resolved"
        or value.get("canonical_charge_lifecycle_authority") != canonical
        or canonical.get("lifecycle_family") != _expected_family(base["move_id"])
        or canonical.get("execution_model") != ("semi_invulnerable_then_execute" if base["move_id"] in _SEMI_INVULNERABLE_MOVES else "charge_then_execute")
        or canonical.get("terminal_effect_class") != "damaging_move"
        or canonical.get("canonical_recognition_grants_immediate_execution") is not False
    ):
        return "rejected", "standard_charge_start_canonical_lifecycle_invalid"
    power = value.get("power_herb_applicability_state")
    if not isinstance(power, Mapping) or power.get("status") not in {"not_required", "suppressed"}:
        return "rejected", "standard_charge_start_power_herb_state_invalid"
    return None


def _expected_family(move_id: str) -> str:
    return (
        "weather_sensitive_charge_then_damage" if move_id in _SOLAR_MOVES
        else "charge_turn_self_effect_then_damage" if move_id in _SELF_EFFECT_MOVES
        else "semi_invulnerable_charge_then_damage" if move_id in _SEMI_INVULNERABLE_MOVES
        else "ordinary_charge_then_damage"
    )


def _pokemon(
    state: Any,
    owner: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    return (
        value
        if isinstance(value, Mapping) and value.get("pokemon_id") == owner.get("pokemon_id")
        else None
    )


def _exact_hp(row: Mapping[str, Any]) -> int | None:
    hp, maximum, fainted = row.get("current_hp"), row.get("max_hp"), row.get("fainted")
    if (
        not isinstance(hp, int) or isinstance(hp, bool) or hp < 0
        or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0
        or hp > maximum
        or not isinstance(fainted, bool)
        or fainted != (hp == 0)
    ):
        return None
    return hp


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
