"""Current-D0 facts for the bounded standard-charge terminal kernel.

This module is deliberately a fact freezer.  It cannot grant an attack: a
caller must later adapt this bundle into an authenticated execution contract.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_champions_confusion_progression import valid_confusion_progression
from llm.advisor_champions_status_progression import valid_progression
from llm.advisor_runtime_d0_focus_sash_survival_authority import freeze_runtime_d0_focus_sash_survival_authority
from llm.advisor_runtime_d0_held_item_effect_applicability_authority import resolve_runtime_d0_held_item_effect_applicability_authority
from llm.advisor_runtime_d0_life_orb_immediate_authority import freeze_runtime_d0_life_orb_immediate_authority
from llm.advisor_runtime_d0_sturdy_survival_authority import freeze_runtime_d0_sturdy_survival_authority
from llm.advisor_runtime_strategy_d0 import (
    _native_field_state, _native_side_effects,
    _roster, _runtime_current_type, _runtime_known_string, _runtime_snapshot,
    _same_runtime_owner, _valid_d0, freeze_runtime_current_condition_authority,
    freeze_runtime_current_critical_state_authority,
    freeze_runtime_current_stage_authority, freeze_runtime_final_combat_stat_authority,
    runtime_strategy_d0_freshness,
)
from llm.advisor_substitute import substitute_state
from llm.advisor_identity_groundedness import project_identity_groundedness


PARTICIPANT_SCHEMA_VERSION = "runtime-d0-standard-charge-participant-mechanics-authority-v1"
TERMINAL_SCHEMA_VERSION = "runtime-d0-standard-charge-terminal-mechanics-authority-v1"
_STATS = ("attack", "defense", "special-attack", "special-defense", "speed")
_ROLES = {"actor", "target"}


def freeze_runtime_d0_standard_charge_participant_mechanics_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], owner: Mapping[str, Any], participant_role: str, move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze one owner-bound mechanics row; this is not an execution grant."""
    base = _base(strategy_d0, runtime_snapshot, action, actor, target, move_metadata)
    if base is None or participant_role not in _ROLES or owner != (actor if participant_role == "actor" else target):
        return _result("rejected", "standard_charge_participant_identity_or_role_mismatch")
    state, _, _ = _runtime_snapshot(runtime_snapshot)
    raw = _roster(state, owner["side"]).get(owner["slot_index"]) if state else None
    preview = strategy_d0.get("strategy_state", {}).get("active", {}).get(owner["side"])
    if not isinstance(raw, Mapping) or not _same_runtime_owner(raw, owner) or not isinstance(preview, Mapping):
        return _result("rejected", "standard_charge_participant_runtime_identity_mismatch")
    stage = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=owner)
    condition = freeze_runtime_current_condition_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=owner)
    critical = freeze_runtime_current_critical_state_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=owner)
    stats = {stat: freeze_runtime_final_combat_stat_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=owner, stat=stat) for stat in _STATS}
    missing = []
    values = {}
    for stat, authority in stats.items():
        value = authority.get("final_stat_authority", {}).get("value") if authority.get("status") == "resolved" else None
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0: missing.append(f"final_stat.{stat}")
        else: values[stat] = value
    level = raw.get("current_level") if _trusted(raw.get("current_level_provenance"), "current_level_observed") else None
    hp = {"current_hp": preview.get("current_hp"), "maximum_hp": preview.get("max_hp")}
    stage_rows = stage.get("stages") if stage.get("status") == "resolved" else None
    stages = ({key: stage_rows.get(key, {}).get("value") for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")} if isinstance(stage_rows, Mapping) else None)
    if not isinstance(level, int) or isinstance(level, bool) or level <= 0: missing.append("current_level")
    if not isinstance(hp["current_hp"], int) or isinstance(hp["current_hp"], bool) or not isinstance(hp["maximum_hp"], int) or isinstance(hp["maximum_hp"], bool) or hp["maximum_hp"] <= 0 or hp["current_hp"] < 0 or hp["current_hp"] > hp["maximum_hp"]: missing.append("current_hp")
    if not isinstance(raw.get("fainted"), bool) or (isinstance(hp["current_hp"], int) and raw.get("fainted") is not (hp["current_hp"] == 0)): missing.append("fainted")
    if not isinstance(stages, Mapping) or any(not isinstance(stages.get(key), int) for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")): missing.append("current_stages")
    cond = condition.get("condition") if condition.get("status") == "resolved" else None
    if not isinstance(cond, Mapping) or cond.get("status") not in {"known_none", "known_present"}: missing.append("condition")
    item = _item(raw)
    ability_value = _runtime_known_string(raw.get("current_ability")) if _trusted(raw.get("current_ability_provenance"), "current_ability_observed") else None
    ability = _known(ability_value) if ability_value else {"status": "unknown"}
    types = _runtime_current_type(raw) if _trusted(raw.get("current_type_provenance"), "current_type_observed") else None
    if item["status"] not in {"known", "known_absent"}: missing.append("item")
    if ability["status"] != "known": missing.append("ability")
    if not isinstance(types, list) or not types: missing.append("types")
    sub = substitute_state(strategy_d0.get("strategy_state", {}), owner)
    if sub.get("state") not in {"known_active", "known_inactive"}: missing.append("substitute")
    crit_volatiles, lucky_chant = _critical(critical)
    if crit_volatiles["status"] == "unknown" or lucky_chant["status"] == "unknown": missing.append("critical_state")
    field_raw = _native_field_state(state); side_effects = _native_side_effects(state)
    field = {"status": "known", "weather": field_raw.get("weather"), "terrain": field_raw.get("terrain")} if field_raw.get("weather") != "unknown" and field_raw.get("terrain") != "unknown" else {"status": "unknown"}
    try:
        grounded_row = project_identity_groundedness(state, side=owner["side"])
    except (TypeError, ValueError):
        grounded_row = {}
    groundedness = (
        {"status": "known", "value": grounded_row["status"]}
        if grounded_row.get("session_id") == owner["session_id"]
        and grounded_row.get("side") == owner["side"]
        and grounded_row.get("slot_index") == owner["slot_index"]
        and grounded_row.get("pokemon_id") == owner["pokemon_id"]
        and grounded_row.get("status") in {"grounded", "ungrounded"}
        else {"status": "unknown"}
    )
    if field["status"] == "unknown": missing.append("field")
    if not isinstance(side_effects, list): missing.append("side_conditions")
    status_progression = _status_progression(raw, owner, cond)
    confusion_state, confusion_progression = _confusion(raw, owner)
    if status_progression["status"] == "unknown": missing.append("status_progression")
    if confusion_state["status"] == "unknown" or confusion_progression["status"] == "unknown": missing.append("confusion_progression")
    final_stats = {"hp": hp["maximum_hp"], **values} if len(values) == len(_STATS) and isinstance(hp.get("maximum_hp"), int) and not isinstance(hp.get("maximum_hp"), bool) and hp["maximum_hp"] > 0 else None
    direct_mechanics = _direct_mechanics_from_facts(level=level, hp=hp, final_stats=final_stats, stages=stages, condition=cond, item=item, ability=ability, types=types, field=field)
    if direct_mechanics["status"] == "unknown": missing.append("direct_mechanics")
    row = {**base, "schema_version": PARTICIPANT_SCHEMA_VERSION, "owner": deepcopy(dict(owner)), "participant_role": participant_role, "mechanics_only": True, "execution_grant": False,
        "current_level": _known(level) if isinstance(level, int) and not isinstance(level, bool) and level > 0 else {"status": "unknown"}, "current_final_stats": {"status": "known", "values": final_stats} if isinstance(final_stats, Mapping) else {"status": "incomplete", "values": values}, "current_hp": {"status": "known", **hp} if not "current_hp" in missing else {"status": "unknown"}, "fainted": raw.get("fainted") if isinstance(raw.get("fainted"), bool) else None,
        "current_stages": {"status": "known", "values": dict(stages)} if isinstance(stages, Mapping) else {"status": "unknown"}, "condition": deepcopy(cond) if isinstance(cond, Mapping) else {"status": "unknown"}, "item": item, "ability": ability, "types": _known(list(types)) if isinstance(types, list) else {"status": "unknown"},
        "substitute": {"status": sub.get("state"), **({"substitute_hp": sub["substitute_hp"]} if "substitute_hp" in sub else {})} if sub.get("state") in {"known_active", "known_inactive"} else {"status": "unknown"}, "critical_hit_volatiles": crit_volatiles, "lucky_chant": lucky_chant,
        "field": field, "groundedness": groundedness, "side_conditions": _known({effect: True for side_row in side_effects if side_row.get("side") == owner["side"] for effect in [side_row.get("effect")]}) if isinstance(side_effects, list) else {"status": "unknown"}, "direct_mechanics": direct_mechanics,
        "status_progression": status_progression, "confusion_state": confusion_state, "confusion_progression": confusion_progression,
        "provenance": "runtime_d0_current_standard_charge_participant_mechanics_v1"}
    if missing:
        row.update(status="incomplete", reason=missing[0], missing_authority=tuple(sorted(set(missing))))
    else: row["status"] = "resolved"
    return row


def freeze_runtime_d0_standard_charge_terminal_mechanics_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any], actor_participant_mechanics_authority: Mapping[str, Any] | None = None, target_participant_mechanics_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Bind current terminal facts for a future specialised caller, not an attack."""
    base = _base(strategy_d0, runtime_snapshot, action, actor, target, move_metadata)
    if base is None: return _result("rejected", "standard_charge_terminal_mechanics_identity_mismatch")
    effect = resolve_canonical_standard_charge_turn_two_effect(base["move_id"])
    if effect.get("status") != "resolved": return _result("rejected", "standard_charge_terminal_effect_unavailable")
    actor_row = actor_participant_mechanics_authority or freeze_runtime_d0_standard_charge_participant_mechanics_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, actor=actor, target=target, owner=actor, participant_role="actor", move_metadata=move_metadata)
    target_row = target_participant_mechanics_authority or freeze_runtime_d0_standard_charge_participant_mechanics_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, actor=actor, target=target, owner=target, participant_role="target", move_metadata=move_metadata)
    if actor_participant_mechanics_authority is not None and validate_runtime_d0_standard_charge_participant_mechanics_authority(
        authority=actor_row, strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, owner=actor, participant_role="actor", move_metadata=move_metadata,
    ).get("status") != "resolved":
        return _result("rejected", "standard_charge_terminal_participant_authority_tampered")
    if target_participant_mechanics_authority is not None and validate_runtime_d0_standard_charge_participant_mechanics_authority(
        authority=target_row, strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, owner=target, participant_role="target", move_metadata=move_metadata,
    ).get("status") != "resolved":
        return _result("rejected", "standard_charge_terminal_participant_authority_tampered")
    if not _participant_valid(actor_row, base, actor, "actor") or not _participant_valid(target_row, base, target, "target"):
        return _result("rejected", "standard_charge_terminal_participant_authority_tampered")
    sturdy = freeze_runtime_d0_sturdy_survival_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, defender=target, attacker=actor, action=action, move_metadata=effect["move"])
    sash = freeze_runtime_d0_focus_sash_survival_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, holder=target, attacker=actor, action=action, move_metadata=effect["move"])
    life = freeze_runtime_d0_life_orb_immediate_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, source_action=action, move_metadata=effect["move"], qualifying_damage=False)
    actor_item = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, holder=actor)
    target_item = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, holder=target)
    supports = (sturdy, sash, life, actor_item, target_item)
    support_statuses = tuple(row.get("status") if isinstance(row, Mapping) else None for row in supports)
    status = "resolved" if actor_row.get("status") == target_row.get("status") == "resolved" and all(value == "resolved" for value in support_statuses) else "incomplete"
    result = {"status": status, "schema_version": TERMINAL_SCHEMA_VERSION, **base, "move_metadata": deepcopy(dict(effect["move"])), "authenticated_move_metadata": deepcopy(dict(effect["move"])), "canonical_terminal_effect": effect, "actor_participant_mechanics_authority": deepcopy(dict(actor_row)), "target_participant_mechanics_authority": deepcopy(dict(target_row)), "target_sturdy_authority": sturdy, "target_focus_sash_authority": sash, "attacker_life_orb_authority": life, "actor_held_item_effect_applicability_authority": actor_item, "target_held_item_effect_applicability_authority": target_item, "mechanics_only": True, "execution_grant": False, "provenance": "runtime_d0_standard_charge_terminal_mechanics_bundle_v1"}
    if result["status"] == "incomplete":
        result["reason"] = "standard_charge_participant_mechanics_incomplete" if actor_row.get("status") != "resolved" or target_row.get("status") != "resolved" else "standard_charge_support_authority_incomplete"
    return result


def _base(d0: Any, snapshot: Any, action: Any, actor: Any, target: Any, metadata: Any) -> dict[str, Any] | None:
    if not _valid_d0(d0) or not _owner(actor) or not _owner(target) or actor == target or actor != d0.get("decision_owner") or not isinstance(action, Mapping) or action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str) or not isinstance(metadata, Mapping): return None
    move_id = metadata.get("move_id")
    active = d0.get("active_owners")
    if not isinstance(move_id, str) or action.get("identity", action.get("move_id")) != move_id or not isinstance(active, Mapping) or active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target): return None
    if runtime_strategy_d0_freshness(strategy_d0=d0, runtime_snapshot=snapshot).get("status") != "current": return None
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    if effect.get("status") != "resolved": return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action["action_id"], "move_id": move_id, "source_action_id": action["action_id"], "source_move_id": move_id}


def _participant_valid(value: Any, base: Mapping[str, Any], owner: Mapping[str, Any], role: str) -> bool:
    return isinstance(value, Mapping) and value.get("schema_version") == PARTICIPANT_SCHEMA_VERSION and value.get("owner") == dict(owner) and value.get("participant_role") == role and all(value.get(key) == base[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "target", "action_id", "move_id", "source_action_id", "source_move_id"))


def validate_runtime_d0_standard_charge_participant_mechanics_authority(*, authority: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], owner: Mapping[str, Any], participant_role: str, move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Replay one participant row from current D0 and reject any mutation."""
    expected = freeze_runtime_d0_standard_charge_participant_mechanics_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, owner=owner, participant_role=participant_role,
        move_metadata=move_metadata,
    )
    if expected.get("status") not in {"resolved", "incomplete"}:
        return _result("rejected", "standard_charge_participant_replay_unavailable")
    if not isinstance(authority, Mapping) or dict(authority) != expected:
        return _result("rejected", "standard_charge_participant_authority_tampered")
    return {"status": "resolved", "schema_version": "runtime-d0-standard-charge-participant-mechanics-replay-v1", "authority": deepcopy(dict(expected)), "provenance": "runtime_d0_standard_charge_participant_replay_v1"}


def validate_runtime_d0_standard_charge_terminal_mechanics_authority(*, authority: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Replay the full mechanics-only terminal bundle and reject nested tampering."""
    expected = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, move_metadata=move_metadata,
    )
    if expected.get("status") not in {"resolved", "incomplete"}:
        return _result("rejected", "standard_charge_terminal_replay_unavailable")
    if not isinstance(authority, Mapping) or dict(authority) != expected:
        return _result("rejected", "standard_charge_terminal_mechanics_authority_tampered")
    return {"status": "resolved", "schema_version": "runtime-d0-standard-charge-terminal-mechanics-replay-v1", "authority": deepcopy(dict(expected)), "provenance": "runtime_d0_standard_charge_terminal_mechanics_replay_v1"}


def _direct_mechanics_from_facts(*, level: Any, hp: Mapping[str, Any], final_stats: Mapping[str, Any] | None, stages: Mapping[str, Any] | None, condition: Mapping[str, Any] | None, item: Mapping[str, Any], ability: Mapping[str, Any], types: Any, field: Mapping[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 100
        or not isinstance(final_stats, Mapping)
        or not isinstance(stages, Mapping)
        or not isinstance(condition, Mapping) or condition.get("status") not in {"known_none", "known_present"}
        or item.get("status") not in {"known", "known_absent"}
        or ability.get("status") != "known"
        or not isinstance(types, list) or not types
        or field.get("status") != "known"
        or not isinstance(hp.get("current_hp"), int) or isinstance(hp.get("current_hp"), bool)
        or not isinstance(hp.get("maximum_hp"), int) or isinstance(hp.get("maximum_hp"), bool)
    ):
        return {"status": "unknown"}
    condition_value = condition.get("condition") if condition.get("status") == "known_present" else None
    return {
        "status": "known",
        "combatant": {
            "level": level,
            "current_hp": hp["current_hp"],
            "max_hp": hp["maximum_hp"],
            "stats": deepcopy(dict(final_stats)),
            "boosts": {key: stages[key] for key in _STATS},
            "status": condition_value,
            "item": item.get("value") if item["status"] == "known" else None,
            "ability": ability["value"],
            "types": deepcopy(list(types)),
        },
    }


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _item(raw: Mapping[str, Any]) -> dict[str, Any]:
    value = raw.get("known_item"); provenance = raw.get("known_item_provenance")
    trusted = isinstance(provenance, Mapping) and provenance.get("event_kind") in {"current_item_observed", "item_consumption_observed", "item_removed_observed"} and provenance.get("trust") == "user_confirmed_observation"
    if isinstance(value, str) and value and trusted: return _known(value)
    if value is None and trusted and (provenance.get("status") == "known_absent" or provenance.get("event_kind") in {"item_consumption_observed", "item_removed_observed"}): return {"status": "known_absent", "value": None}
    return {"status": "unknown"}


def _status_progression(raw: Mapping[str, Any], owner: Mapping[str, Any], condition: Mapping[str, Any] | None) -> dict[str, Any]:
    current = condition.get("condition") if isinstance(condition, Mapping) and condition.get("status") == "known_present" else None
    if current not in {"sleep", "freeze"}: return {"status": "not_applicable"}
    row = raw.get("champions_status_progression")
    return {"status": "known", "value": deepcopy(dict(row))} if valid_progression(row, dict(owner)) and row.get("condition") == current else {"status": "unknown"}


def _confusion(raw: Mapping[str, Any], owner: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    state = raw.get("current_confusion"); provenance = raw.get("confusion_provenance")
    trusted = isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_confusion_observed" and provenance.get("trust") == "user_confirmed_observation"
    if state == "none" and trusted: return {"status": "known_none"}, {"status": "not_applicable"}
    row = raw.get("champions_confusion_progression")
    if state == "confused" and trusted and valid_confusion_progression(row, dict(owner)):
        return {"status": "known_confused", "value": "confused"}, {"status": "known", "value": deepcopy(dict(row))}
    return {"status": "unknown"}, {"status": "unknown"}


def _known(value: Any) -> dict[str, Any]: return {"status": "known", "value": deepcopy(value)}
def _critical(authority: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    volatiles = authority.get("crit_volatiles", {}).get("volatiles") if isinstance(authority.get("crit_volatiles"), Mapping) else None
    lucky = authority.get("lucky_chant", {}).get("lucky_chant") if isinstance(authority.get("lucky_chant"), Mapping) else None
    if not isinstance(volatiles, Mapping) or any(row.get("status") == "unknown" for row in volatiles.values() if isinstance(row, Mapping)) or not isinstance(lucky, Mapping) or lucky.get("status") == "unknown": return {"status": "unknown"}, {"status": "unknown"}
    present = tuple(key for key, row in volatiles.items() if isinstance(row, Mapping) and row.get("status") == "known_present")
    return _known(list(present)), {"status": "known_active" if lucky.get("status") == "known_present" else "known_inactive"}
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == {"session_id", "side", "slot_index", "pokemon_id"} and value.get("side") in {"self", "opponent"}
def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": TERMINAL_SCHEMA_VERSION, "reason": reason}
