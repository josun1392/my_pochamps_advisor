"""Strict current-combat authority for an explicitly selectable opponent switch target."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-opponent-switch-target-combat-authority-v1"
_STATS = ("attack", "defense", "special-attack", "special-defense", "speed")
_STAGES = (*_STATS, "accuracy", "evasion")


def freeze_runtime_d0_opponent_switch_target_combat_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], switch_response_authority: Mapping[str, Any], selected_response_action_id: str) -> dict:
    base = _base(strategy_d0)
    if not base or not isinstance(selected_response_action_id, str) or not selected_response_action_id:
        return _result("rejected", "invalid_switch_target_combat_request", base)
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    action = _action(switch_response_authority, base, selected_response_action_id)
    if action.get("status") != "resolved":
        return _result(action["status"], action["reason"], base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    roster = state.get("opponent_side", {}).get("pokemon") if isinstance(state, Mapping) and isinstance(state.get("opponent_side"), Mapping) else None
    target = roster.get(action["target"]["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(target, Mapping) or target.get("pokemon_id") != action["target"]["pokemon_id"]:
        return _result("rejected", "switch_target_runtime_identity_mismatch", base, target_owner=action["target"])
    fields = _fields(target)
    if fields is None:
        return _result("incomplete", "switch_target_current_combat_unknown", base, target_owner=action["target"])
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "selected_response_action_id": selected_response_action_id, "target_owner": deepcopy(action["target"]), "combat_fields": fields, "hypothetical": False, "provenance": "explicit_current_opponent_switch_target_combat_observation_v1", "reason": None}


def _action(authority: Any, base: Mapping[str, Any], action_id: str) -> dict:
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_actor", "opponent_actor")
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or any(authority.get(key) != base.get(key) for key in required):
        return {"status": "rejected", "reason": "switch_response_authority_binding_mismatch"}
    row = next((item for item in authority.get("actions", ()) if isinstance(item, Mapping) and item.get("action_id") == action_id), None)
    target = row.get("target_owner") if isinstance(row, Mapping) else None
    if not isinstance(target, Mapping) or row.get("action_type") != "manual_switch" or row.get("selectability") != "selectable" or action_id not in authority.get("selectable_response_action_ids", ()):
        return {"status": "incomplete", "reason": "selected_switch_response_not_selectable"}
    return {"status": "resolved", "target": dict(target)}


def _fields(target: Mapping[str, Any]) -> dict | None:
    hp, maximum, fainted = target.get("current_hp"), target.get("max_hp"), target.get("fainted")
    stats, stages = target.get("current_final_stats"), target.get("stat_stages")
    required_provenance = "current_opponent_switch_target_combat_observed"
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1 or not 0 <= hp <= maximum or not isinstance(fainted, bool) or fainted is not (hp == 0):
        return None
    if not isinstance(target.get("current_type"), list) or not target["current_type"] or not isinstance(stats, Mapping) or any(not isinstance(stats.get(stat), Mapping) or not isinstance(stats[stat].get("value"), int) for stat in _STATS) or not isinstance(stages, Mapping) or any(not isinstance(stages.get(stat), int) or isinstance(stages[stat], bool) or not -6 <= stages[stat] <= 6 for stat in _STAGES):
        return None
    if target.get("condition") not in {None, "none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"} or not isinstance(target.get("current_ability"), str) or not target["current_ability"]:
        return None
    for key in ("current_hp_provenance", "current_type_provenance", "condition_provenance", "known_item_provenance", "current_ability_provenance"):
        if not isinstance(target.get(key), Mapping) or target[key].get("event_kind") != required_provenance:
            return None
    return {"current_hp": hp, "max_hp": maximum, "fainted": fainted, "type": deepcopy(target["current_type"]), "final_stats": {stat: stats[stat]["value"] for stat in _STATS}, "stages": deepcopy(dict(stages)), "condition": target["condition"], "item": deepcopy(target.get("known_item")), "ability": target["current_ability"]}


def _base(d0: Any) -> dict:
    owners = d0.get("active_owners") if isinstance(d0, Mapping) else None
    own, opponent = owners.get("self") if isinstance(owners, Mapping) else None, owners.get("opponent") if isinstance(owners, Mapping) else None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(own, Mapping) or not isinstance(opponent, Mapping):
        return {}
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(dict(d0["decision_owner"])), "own_actor": deepcopy(dict(own)), "opponent_actor": deepcopy(dict(opponent))}


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
