"""Exact post-damage continuation authority for U-turn, Volt Switch, and Flip Turn."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage_pivot_moves import canonical_damage_pivot_metadata, is_canonical_damage_pivot


SCHEMA_VERSION = "damage-pivot-continuation-authority-v1"


def freeze_damage_pivot_continuation_authority(*, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], move_metadata: Mapping[str, Any], attack_terminal_leaf: Mapping[str, Any], replacement_authority: Mapping[str, Any] | None) -> dict[str, Any]:
    """Bind one terminal attack leaf to its exact optional self-switch continuation.

    This owner does not choose a replacement, execute a switch, or alter attack
    probabilities.  It only states whether a caller-provided exact replacement
    may be consumed after this already-materialized terminal attack.
    """
    base = _base(strategy_d0, action, move_metadata, attack_terminal_leaf)
    if base is None:
        return _result("rejected", "pivot_attack_terminal_binding_invalid", {})
    metadata = canonical_damage_pivot_metadata(move_metadata)
    if not is_canonical_damage_pivot(metadata):
        return _result("not_applicable", "move_has_no_canonical_damage_pivot", base, move_metadata=metadata)
    consequences = attack_terminal_leaf.get("consequences")
    if not isinstance(consequences, Mapping):
        return _result("rejected", "pivot_attack_terminal_consequences_missing", base, move_metadata=metadata)
    attacker_hp, target_hp = consequences.get("own_final_hp"), consequences.get("target_final_hp")
    if not _hp(attacker_hp) or not _hp(target_hp):
        return _result("incomplete", "pivot_post_attack_hp_unknown", base, move_metadata=metadata)
    if attack_terminal_leaf.get("hit_state") != "hit" or consequences.get("damage") in (None, 0):
        return _result("not_applicable", "pivot_attack_did_not_affect_target", base, move_metadata=metadata, attacker_final_hp=attacker_hp, attacker_fainted=attacker_hp == 0, target_final_hp=target_hp, target_fainted=target_hp == 0)
    if attacker_hp == 0:
        return _result("not_applicable", "pivot_user_fainted_during_attack", base, move_metadata=metadata, attacker_final_hp=0, attacker_fainted=True, target_final_hp=target_hp, target_fainted=target_hp == 0)
    parsed = _replacement(replacement_authority, base)
    if isinstance(parsed, str):
        return _result("incomplete", parsed, base, move_metadata=metadata, attacker_final_hp=attacker_hp, attacker_fainted=False, target_final_hp=target_hp, target_fainted=target_hp == 0)
    if parsed is None:
        return _result("not_applicable", "pivot_no_exact_legal_replacement", base, move_metadata=metadata, attacker_final_hp=attacker_hp, attacker_fainted=False, target_final_hp=target_hp, target_fainted=target_hp == 0)
    return {"status": "applies", "schema_version": SCHEMA_VERSION, **base, "canonical_pivot_capability": "self_switch_after_successful_attack", "move_metadata": metadata, "attack_terminal": deepcopy(dict(attack_terminal_leaf)), "attacker_final_hp": attacker_hp, "attacker_fainted": False, "target_final_hp": target_hp, "target_fainted": target_hp == 0, "replacement_authority": deepcopy(parsed), "selected_replacement_owner": deepcopy(parsed["owner"]), "provenance": "exact_terminal_attack_to_post_damage_self_switch_v1"}


def _base(d0: Any, action: Any, move: Any, leaf: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(move, Mapping) or not isinstance(leaf, Mapping): return None
    attacker, target, provenance = d0.get("decision_owner"), d0.get("active_owners", {}).get("opponent"), leaf.get("provenance")
    if not isinstance(attacker, Mapping) or not isinstance(target, Mapping) or action.get("action_id") != f"attack:{move.get('move_id')}" or leaf.get("candidate_id") != action.get("action_id") or not isinstance(provenance, Mapping): return None
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": attacker, "attacker": attacker, "target": target, "move_id": move.get("move_id")}
    if any(provenance.get(key) != value for key, value in expected.items()) or not isinstance(move.get("move_id"), str): return None
    return {**deepcopy(expected), "action_id": action["action_id"], "attack_leaf_id": leaf.get("leaf_id")}


def _replacement(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None | str:
    if value is None: return "pivot_replacement_authority_missing"
    if not isinstance(value, Mapping): return "pivot_replacement_authority_invalid"
    if value.get("status") == "known_none": return None
    owner = value.get("owner")
    expected = {key: base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    if value.get("status") != "resolved" or any(value.get(key) != item for key, item in expected.items()) or not isinstance(owner, Mapping) or owner.get("side") != "self" or owner == base.get("attacker"):
        return "pivot_replacement_authority_invalid"
    return deepcopy(dict(value))


def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
