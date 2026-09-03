"""Exact same-immediate-pair switch provenance for Stakeout.

This owner consumes the existing opponent-switch materialization.  It does not
derive a switch from active identity, hazards, or retained battle history.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.modifiers._q12 import MUL_2_0


SCHEMA_VERSION = "runtime-d0-stakeout-switch-authority-v1"


def freeze_runtime_d0_stakeout_switch_authority(
    *, root_strategy_d0: Mapping[str, Any], post_switch_strategy_d0: Mapping[str, Any],
    post_switch_runtime_snapshot: Mapping[str, Any], own_action: Mapping[str, Any],
    switch_response_authority: Mapping[str, Any], switch_in_authority: Mapping[str, Any],
    pair_id: str, response_action_id: str,
) -> dict[str, Any]:
    base = _base(root_strategy_d0, post_switch_strategy_d0, own_action, pair_id, response_action_id)
    if base is None:
        return _result("rejected", "stakeout_pair_identity_invalid", {})
    original, attacker, target = base["original_opponent"], base["attacker"], base["target"]
    if not isinstance(switch_in_authority, Mapping) or switch_in_authority.get("schema_version") != "detached-opponent-switch-in-intermediate-authority-v1" or switch_in_authority.get("status") != "resolved":
        return _result("rejected", "stakeout_switch_in_authority_invalid", base)
    root_bindings = {
        "session_id": root_strategy_d0["session_id"], "source_runtime_fingerprint": root_strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": root_strategy_d0["strategy_preview_fingerprint"], "decision_owner": root_strategy_d0["decision_owner"],
    }
    if any(switch_in_authority.get(key) != item for key, item in root_bindings.items()):
        return _result("rejected", "stakeout_switch_in_root_binding_mismatch", base)
    if switch_in_authority.get("own_actor") != attacker or switch_in_authority.get("opponent_actor") != original:
        return _result("rejected", "stakeout_switch_in_actor_binding_mismatch", base)
    if switch_in_authority.get("target_owner") != target or switch_in_authority.get("selected_response_action_id") != base["response_action_id"]:
        return _result("rejected", "stakeout_incoming_target_binding_mismatch", base)
    hypothetical = switch_in_authority.get("hypothetical_switch_in_state")
    if not isinstance(hypothetical, Mapping) or hypothetical.get("active_owner") != target or hypothetical.get("replaced_active_owner") != original:
        return _result("rejected", "stakeout_switch_result_identity_mismatch", base)
    action = _response_action(switch_response_authority, root_strategy_d0, base["response_action_id"])
    if action is None or action.get("target_owner") != target:
        return _result("rejected", "stakeout_switch_response_binding_mismatch", base)
    ability = _attacker_ability(post_switch_runtime_snapshot, attacker)
    if ability is None:
        return _result("incomplete", "stakeout_attacker_ability_unknown", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "attacker_ability": ability,
        "response_kind": "switch", "same_turn_switch_result": "proven_immediate_pair_switch",
        "incoming_target": deepcopy(dict(target)), "post_switch_attack_target": deepcopy(dict(target)),
        "outcome": "applicable", "modifier_q12": MUL_2_0,
        "switch_in_authority": deepcopy(dict(switch_in_authority)),
        "provenance": "exact_opponent_switch_response_to_post_entry_attack_target_v1",
    }


def valid_runtime_d0_stakeout_switch_authority(
    value: Any, *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move_id: str,
) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("status") != "resolved":
        return False
    expected = {
        "post_switch_session_id": strategy_d0.get("session_id"), "post_switch_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "post_switch_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "post_switch_decision_owner": strategy_d0.get("decision_owner"),
        "attacker": attacker, "target": target, "incoming_target": target, "post_switch_attack_target": target,
    }
    if any(value.get(key) != item for key, item in expected.items()):
        return False
    switch = value.get("switch_in_authority")
    root = {
        "session_id": value.get("root_session_id"), "source_runtime_fingerprint": value.get("root_runtime_fingerprint"),
        "source_branch_fingerprint": value.get("root_branch_fingerprint"), "decision_owner": value.get("root_decision_owner"),
    }
    if not all(isinstance(root[key], str) and root[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) or root["decision_owner"] != attacker:
        return False
    if not isinstance(switch, Mapping) or switch.get("schema_version") != "detached-opponent-switch-in-intermediate-authority-v1" or switch.get("status") != "resolved":
        return False
    if any(switch.get(key) != item for key, item in root.items()) or switch.get("own_actor") != attacker or switch.get("opponent_actor") != value.get("original_opponent") or switch.get("target_owner") != target or switch.get("selected_response_action_id") != value.get("response_action_id"):
        return False
    hypothetical = switch.get("hypothetical_switch_in_state")
    if not isinstance(hypothetical, Mapping) or hypothetical.get("active_owner") != target or hypothetical.get("replaced_active_owner") != value.get("original_opponent"):
        return False
    return (
        value.get("attacker_ability") == "stakeout" and value.get("attack_action_id") in {move_id, f"attack:{move_id}"}
        and value.get("response_kind") == "switch" and value.get("same_turn_switch_result") == "proven_immediate_pair_switch"
        and value.get("outcome") == "applicable" and value.get("modifier_q12") == MUL_2_0
    )


def _base(root: Any, post: Any, action: Any, pair_id: Any, response_action_id: Any) -> dict[str, Any] | None:
    if not isinstance(root, Mapping) or not isinstance(post, Mapping) or root.get("status") != "resolved" or post.get("status") != "resolved" or not isinstance(action, Mapping) or action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str) or not isinstance(pair_id, str) or not isinstance(response_action_id, str):
        return None
    attacker, original = root.get("active_owners", {}).get("self"), root.get("active_owners", {}).get("opponent")
    target = post.get("active_owners", {}).get("opponent")
    if root.get("decision_owner") != attacker or post.get("decision_owner") != attacker or not all(_owner(row) for row in (attacker, original, target)) or target == original:
        return None
    return {
        "pair_id": pair_id, "attacker": deepcopy(dict(attacker)), "original_opponent": deepcopy(dict(original)), "target": deepcopy(dict(target)),
        "attack_action_id": action["action_id"], "response_action_id": response_action_id,
        "root_session_id": root["session_id"], "root_runtime_fingerprint": root["source_runtime_fingerprint"], "root_branch_fingerprint": root["strategy_preview_fingerprint"], "root_decision_owner": deepcopy(dict(root["decision_owner"])),
        "post_switch_session_id": post["session_id"], "post_switch_runtime_fingerprint": post["source_runtime_fingerprint"], "post_switch_branch_fingerprint": post["strategy_preview_fingerprint"], "post_switch_decision_owner": deepcopy(dict(post["decision_owner"])),
    }


def _response_action(value: Any, root: Mapping[str, Any], action_id: str) -> Mapping[str, Any] | None:
    expected = {"session_id": root.get("session_id"), "source_runtime_fingerprint": root.get("source_runtime_fingerprint"), "source_branch_fingerprint": root.get("strategy_preview_fingerprint"), "decision_owner": root.get("decision_owner")}
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or any(value.get(key) != item for key, item in expected.items()):
        return None
    rows = value.get("actions")
    matched = [row for row in rows if isinstance(row, Mapping) and row.get("action_id") == action_id] if isinstance(rows, (tuple, list)) else []
    if len(matched) != 1 or action_id not in value.get("selectable_response_action_ids", ()): return None
    row = matched[0]
    return row if row.get("action_type") == "manual_switch" and row.get("acting_side") == "opponent" and row.get("response_kind", "switch") == "switch" and row.get("selectability") == "selectable" else None


def _attacker_ability(snapshot: Any, attacker: Mapping[str, Any]) -> str | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get("self_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    raw = roster.get(attacker.get("slot_index")) if isinstance(roster, Mapping) else None
    ability = raw.get("current_ability") if isinstance(raw, Mapping) else None
    return ability if isinstance(ability, str) and ability else None


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and isinstance(value.get("pokemon_id"), str) and isinstance(value.get("session_id"), str)


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
