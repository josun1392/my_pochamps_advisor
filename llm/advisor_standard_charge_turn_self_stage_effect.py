"""Strict pre-ChargeMove self-stage authority for Meteor Beam and Skull Bash."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle
from llm.advisor_observed_damage_application import apply_canonical_stage_delta
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_stage_authority,
    runtime_strategy_d0_freshness,
)

SCHEMA_VERSION = "standard-charge-turn-self-stage-effect-authority-v1"
_EFFECTS = {
    "meteor-beam": ("special-attack", 1, "special_attack_plus_one"),
    "skull-bash": ("defense", 1, "defense_plus_one"),
}
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(strategy_d0, Mapping)
        or strategy_d0.get("status") != "resolved"
        or not _owner(actor)
        or not _owner(target)
        or actor == target
        or actor != strategy_d0.get("decision_owner")
        or not isinstance(action, Mapping)
        or action.get("action_type") != "attack"
    ):
        return _r("rejected", "charge_turn_self_stage_identity_invalid")
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _r("rejected", "charge_turn_self_stage_runtime_stale")
    active = strategy_d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(actor["side"]) != dict(actor) or active.get(target["side"]) != dict(target):
        return _r("rejected", "charge_turn_self_stage_active_owner_mismatch")
    move_id = action.get("identity", action.get("move_id"))
    action_id = action.get("action_id")
    if move_id not in _EFFECTS or not isinstance(action_id, str) or not action_id:
        return _r("unsupported", "charge_turn_self_stage_move_not_supported")
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    stat, delta, effect_class = _EFFECTS[move_id]
    if (
        lifecycle.get("status") != "resolved"
        or lifecycle.get("lifecycle_family") != "charge_turn_self_effect_then_damage"
        or lifecycle.get("execution_model") != "charge_then_execute"
        or lifecycle.get("charge_turn_side_effect_class") != effect_class
        or lifecycle.get("charge_turn_side_effect_timing") != "before_charge_move_event"
    ):
        return _r("rejected", "charge_turn_self_stage_canonical_lifecycle_invalid")
    stages = freeze_runtime_current_stage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=actor,
    )
    if stages.get("status") != "resolved":
        return _r(stages.get("status", "incomplete"), stages.get("reason", "charge_turn_self_stage_current_stage_unavailable"))
    current = stages.get("stages", {}).get(stat)
    if not isinstance(current, Mapping) or current.get("status") != "known":
        return _r("incomplete", f"charge_turn_self_stage_{stat}_unknown")
    previous = current.get("value")
    if not isinstance(previous, int) or isinstance(previous, bool) or not -6 <= previous <= 6:
        return _r("rejected", "charge_turn_self_stage_previous_stage_invalid")
    resulting = apply_canonical_stage_delta(previous, delta)
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action_id,
        "move_id": move_id,
        "canonical_lifecycle": deepcopy(dict(lifecycle)),
        "source_stage_authority": deepcopy(dict(stages)),
        "owner": deepcopy(dict(actor)),
        "stat": stat,
        "delta": delta,
        "previous_stage": previous,
        "resulting_stage": resulting,
        "timing": "before_charge_move_event",
        "applies_once": True,
        "stage_cap_no_change_is_success": resulting == previous,
        "hypothetical": True,
        "observation_emitted": False,
        "provenance": "authenticated_pre_charge_move_self_stage_effect_v1",
    }


def validate_runtime_d0_standard_charge_turn_self_stage_effect_authority(
    *, authority: Any, **kwargs: Any,
) -> str | None:
    expected = freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(**kwargs)
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "charge_turn_self_stage_effect_authority_mismatch"


def validate_standard_charge_turn_self_stage_effect_for_mechanics(
    *,
    authority: Any,
    session_id: str,
    source_state_fingerprint: str,
    decision_owner: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action_id: str,
    move_id: str,
    actor_mechanics: Mapping[str, Any],
) -> str | None:
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != SCHEMA_VERSION:
        return "charge_turn_self_stage_effect_authority_invalid"
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    expected = _EFFECTS.get(move_id)
    if expected is None:
        return "charge_turn_self_stage_effect_move_invalid"
    stat, delta, effect_class = expected
    if (
        authority.get("session_id") != session_id
        or authority.get("source_runtime_fingerprint") != source_state_fingerprint
        or authority.get("decision_owner") != dict(decision_owner)
        or authority.get("actor") != dict(actor)
        or authority.get("target") != dict(target)
        or authority.get("owner") != dict(actor)
        or authority.get("action_id") != action_id
        or authority.get("move_id") != move_id
        or authority.get("canonical_lifecycle") != lifecycle
        or authority.get("stat") != stat
        or authority.get("delta") != delta
        or authority.get("timing") != "before_charge_move_event"
        or authority.get("applies_once") is not True
        or lifecycle.get("lifecycle_family") != "charge_turn_self_effect_then_damage"
        or lifecycle.get("charge_turn_side_effect_class") != effect_class
        or lifecycle.get("charge_turn_side_effect_timing") != "before_charge_move_event"
    ):
        return "charge_turn_self_stage_effect_binding_invalid"
    stages = actor_mechanics.get("current_stages") if isinstance(actor_mechanics, Mapping) else None
    values = stages.get("values") if isinstance(stages, Mapping) and stages.get("status") == "known" else None
    previous = values.get(stat) if isinstance(values, Mapping) else None
    if previous != authority.get("previous_stage"):
        return "charge_turn_self_stage_effect_previous_stage_mismatch"
    if authority.get("resulting_stage") != apply_canonical_stage_delta(previous, delta):
        return "charge_turn_self_stage_effect_resulting_stage_mismatch"
    return None


def stage_effect_consequence(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "owner": deepcopy(dict(authority["owner"])),
        "stat": authority["stat"],
        "previous_stage": authority["previous_stage"],
        "delta": authority["delta"],
        "resulting_stage": authority["resulting_stage"],
        "action_id": authority["action_id"],
        "move_id": authority["move_id"],
        "timing": authority["timing"],
        "authority": deepcopy(dict(authority)),
        "provenance": "exact_pre_charge_move_self_stage_transition_v1",
    }


def apply_stage_effect_to_actor_mechanics(
    actor_mechanics: Mapping[str, Any], authority: Mapping[str, Any],
) -> dict[str, Any] | None:
    error = validate_standard_charge_turn_self_stage_effect_for_mechanics(
        authority=authority,
        session_id=authority.get("session_id"),
        source_state_fingerprint=authority.get("source_runtime_fingerprint"),
        decision_owner=authority.get("decision_owner", {}),
        actor=authority.get("actor", {}),
        target=authority.get("target", {}),
        action_id=authority.get("action_id"),
        move_id=authority.get("move_id"),
        actor_mechanics=actor_mechanics,
    )
    if error is not None:
        return None
    result = deepcopy(dict(actor_mechanics))
    result["current_stages"]["values"][authority["stat"]] = authority["resulting_stage"]
    direct = result.get("direct_mechanics")
    combatant = direct.get("combatant") if isinstance(direct, Mapping) else None
    if isinstance(combatant, dict) and isinstance(combatant.get("stat_stages"), dict):
        combatant["stat_stages"][authority["stat"]] = authority["resulting_stage"]
    return result


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and isinstance(value.get("session_id"), str) and isinstance(value.get("pokemon_id"), str)


def _r(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
