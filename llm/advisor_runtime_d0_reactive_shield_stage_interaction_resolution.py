"""Strict producer for the three reactive-shield stage interaction results."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_reactive_shield_stage_modifier import (
    canonical_reactive_shield_stage_ability_interaction,
    canonical_reactive_shield_stage_source_ignore_state,
)
from llm.advisor_runtime_d0_reactive_shield_common_block_context import SCHEMA_VERSION as COMMON_SCHEMA
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    build_silk_trap_speed_drop_interaction_resolution,
    build_kings_shield_attack_drop_interaction_resolution,
    build_obstruct_defense_drop_interaction_resolution,
    _current_modifier_authorities,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_current_stage_authority, runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-reactive-shield-stage-interaction-resolution-v1"
_FAMILY = {"silk_trap": ("silk-trap", "speed", -1, build_silk_trap_speed_drop_interaction_resolution), "kings_shield": ("kings-shield", "attack", -1, build_kings_shield_attack_drop_interaction_resolution), "obstruct": ("obstruct", "defense", -2, build_obstruct_defense_drop_interaction_resolution)}


def freeze_runtime_d0_reactive_shield_stage_interaction_resolution(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], common_block_context: Mapping[str, Any] | None) -> dict[str, Any]:
    base = _base(strategy_d0, common_block_context)
    if base is None:
        return _result("rejected", "reactive_shield_common_context_binding_invalid", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    if common_block_context.get("status") != "resolved":
        return _result(_status(common_block_context), common_block_context.get("reason", "reactive_shield_common_context_unavailable"), base)
    if not _common_facts_match(common_block_context, base):
        return _result("rejected", "reactive_shield_common_context_fact_binding_mismatch", base)
    if common_block_context.get("outcome") != "protection_applies_contact":
        return _resolved_not_applicable(base, "reactive_shield_stage_interaction_requires_contact_protection")
    stage = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=base["blocked_attacker"])
    stat = base["stage_stat"]
    stage_row = stage.get("stages", {}).get(stat) if isinstance(stage, Mapping) else None
    if not isinstance(stage_row, Mapping) or stage_row.get("status") != "known":
        return _result("incomplete", f"reactive_shield_{stat}_stage_unknown", base, stage_authority=stage)
    target_modifiers = _current_modifier_authorities(runtime_snapshot, base["blocked_attacker"])
    if target_modifiers is None:
        return _result("incomplete", "reactive_shield_target_modifier_authority_unknown", base)
    ability = target_modifiers["ability_authority"]
    item = target_modifiers["item_authority"]
    if item.get("status") != "known_absent":
        return _result("incomplete", "reactive_shield_item_interaction_unmaintained", base, ability_authority=ability, item_authority=item)
    interaction = canonical_reactive_shield_stage_ability_interaction(ability.get("value"))
    if interaction is None:
        return _result("incomplete", "reactive_shield_ability_interaction_unmaintained", base, ability_authority=ability, item_authority=item)
    if interaction in {"prevented", "reversed"}:
        source_modifiers = _current_modifier_authorities(runtime_snapshot, base["shield_owner"])
        source_ability = source_modifiers.get("ability_authority") if isinstance(source_modifiers, Mapping) else None
        if not isinstance(source_ability, Mapping) or canonical_reactive_shield_stage_source_ignore_state(source_ability.get("value")) != "does_not_ignore_target_ability":
            return _result("incomplete", "reactive_shield_source_ability_ignore_state_unmaintained", base, ability_authority=ability, item_authority=item, source_ability_authority=source_ability)
    else:
        source_ability = None
    outcome, delta = {"applies": ("applies", base["requested_delta"]), "prevented": ("prevented", 0), "reversed": ("reversed", -base["requested_delta"])}[interaction]
    builder = _FAMILY[base["shield_family"]][3]
    resolution = builder(session_id=base["session_id"], shield_owner=base["shield_owner"], blocked_attacker=base["blocked_attacker"], blocked_action_id=base["blocked_action_id"], blocked_move_id=base["blocked_move_id"], outcome=outcome, resulting_delta=delta, ability_authority=ability, item_authority=item)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": outcome, "resulting_delta": delta, "interaction_resolution": resolution, "stage_authority": deepcopy(dict(stage)), "ability_authority": deepcopy(dict(ability)), "item_authority": deepcopy(dict(item)), **({"source_ability_authority": deepcopy(dict(source_ability))} if isinstance(source_ability, Mapping) else {}), "protection_authority": {"status": "resolved", "owner": deepcopy(dict(base["shield_owner"])), "metadata": {"move_id": base["shield_move_id"]}, "provenance": "derived_from_reactive_shield_common_block_context_v1"}, "provenance": "runtime_d0_canonical_reactive_shield_stage_interaction_resolution_v1"}


def _base(d0: Any, context: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(context, Mapping) or context.get("schema_version") != COMMON_SCHEMA:
        return None
    family = context.get("shield_family")
    if family not in _FAMILY:
        return None
    move_id, stat, delta, _builder = _FAMILY[family]
    required = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": d0.get("decision_owner")}
    if any(context.get(key) != value for key, value in required.items()) or context.get("shield_move_id") != move_id or d0.get("active_owners", {}).get("opponent") != context.get("shield_owner") or d0.get("active_owners", {}).get("self") != context.get("blocked_attacker"):
        return None
    if not all(isinstance(context.get(key), str) and context[key] for key in ("shield_action_id", "blocked_action_id", "blocked_move_id")):
        return None
    return {**{key: deepcopy(value) if isinstance(value, Mapping) else value for key, value in required.items()}, "shield_owner": deepcopy(dict(context["shield_owner"])), "shield_action_id": context["shield_action_id"], "shield_move_id": move_id, "shield_family": family, "blocked_attacker": deepcopy(dict(context["blocked_attacker"])), "blocked_action_id": context["blocked_action_id"], "blocked_move_id": context["blocked_move_id"], "stage_stat": stat, "requested_delta": delta}


def _resolved_not_applicable(base: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "interaction_resolution": None, "reason": reason, "provenance": "runtime_d0_reactive_shield_stage_interaction_resolution_v1"}


def _common_facts_match(context: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    success, bypass, contact = context.get("protection_success_authority"), context.get("bypass_authority"), context.get("contact_authority")
    return isinstance(success, Mapping) and success.get("schema_version") == "branch-protection-success-v1" and success.get("owner") == base["shield_owner"] and success.get("previous_successful_protection_count") == 0 and success.get("provenance") == "explicit_branch_nonconsecutive_protection" and isinstance(bypass, Mapping) and bypass.get("status") == "resolved" and bypass.get("bypassed") is False and all(bypass.get(key) == base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) and bypass.get("blocked_attacker") == base["blocked_attacker"] and bypass.get("blocked_action_id") == base["blocked_action_id"] and bypass.get("blocked_move_id") == base["blocked_move_id"] and isinstance(contact, Mapping) and contact.get("status") == "resolved" and contact.get("contact_state") == "contact" and all(contact.get(key) == base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) and contact.get("action_id") == base["blocked_action_id"] and contact.get("move_id") == base["blocked_move_id"] and contact.get("attacker") == base["blocked_attacker"] and contact.get("target") == base["shield_owner"]


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "rejected", "unsupported"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
