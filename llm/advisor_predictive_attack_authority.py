"""Present-tense, D0-bound predictive authority for one fixed-damage attack.

This module deliberately produces neither an observed-result schema nor a
mutated outcome branch.  It is a narrow authority contract for a fresh Seismic
Toss action; a later predictive-outcome adapter may consume it.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_battle_state_context import build_fixed_damage_assessment
from llm.advisor_substitute import substitute_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state


_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SCHEMA = "deterministic-predictive-attack-authority-v1"
_INPUT_SCHEMA = "current-predictive-fixed-damage-input-v1"
_PROVENANCE = "trusted_current_predictive_fixed_damage_input_v1"


def build_predictive_fixed_damage_attack_authority(
    *, branch_state: Mapping[str, Any], decision_owner: Mapping[str, Any], target_owner: Mapping[str, Any],
    move_id: str, predictive_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Predict Seismic Toss exactly from strict current authority at D0.

    Normal formula moves remain out of scope because their legal random rolls
    require an interval/branch-set contract rather than one exact outcome.
    """
    fingerprint = fingerprint_transition_preview_state(branch_state)
    if not isinstance(fingerprint, str) or not _owner(decision_owner) or not _owner(target_owner):
        return _result("rejected", "invalid_d0_authority")
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    attacker = active.get(decision_owner["side"]) if isinstance(active, Mapping) else None
    target = active.get(target_owner["side"]) if isinstance(active, Mapping) else None
    if decision_owner["side"] == target_owner["side"] or not _same_owner(attacker, decision_owner) or not _same_owner(target, target_owner):
        return _result("rejected", "foreign_attacker_or_target")
    if not _valid_input(predictive_input, fingerprint, decision_owner, target_owner, move_id):
        return _result("rejected", "stale_or_invalid_predictive_input")
    if move_id != "seismic-toss":
        return _authority(fingerprint, decision_owner, target_owner, move_id, "unsupported", "unsupported_execution_family")
    if not _exact_hp(target):
        return _authority(fingerprint, decision_owner, target_owner, move_id, "exact_incomplete", "target_hp_unknown")
    if target["fainted"]:
        return _authority(fingerprint, decision_owner, target_owner, move_id, "exact_incomplete", "target_already_fainted")

    substitute = substitute_state(branch_state, target_owner)
    if substitute["state"] in {"unknown", "legacy_untracked"}:
        return _authority(fingerprint, decision_owner, target_owner, move_id, "exact_incomplete", "substitute_state_unknown")
    level = predictive_input["attacker_level_authority"]["value"]
    assessment = build_fixed_damage_assessment(
        {"move_id": move_id},
        {"current_hp": [{"side": "opponent", "current_hp": target["current_hp"], "maximum_hp": target["max_hp"]}]},
        {"opponent_active": {"types": predictive_input["target_type_authority"]["value"]}},
        {"level": level},
    )
    if not isinstance(assessment, Mapping) or assessment.get("status") != "resolved":
        return _authority(fingerprint, decision_owner, target_owner, move_id, "exact_incomplete", "fixed_damage_input_incomplete")
    damage = assessment["damage"]
    if substitute["state"] == "known_active":
        before = substitute["substitute_hp"]
        after = max(0, before - damage)
        result = {"damage": damage, "damage_route": "substitute", "substitute_hp_before": before, "substitute_hp_after": after, "substitute_broken": after == 0, "target_fainted": False}
    else:
        after = max(0, target["current_hp"] - damage)
        result = {"damage": damage, "damage_route": "target", "target_hp_before": target["current_hp"], "target_hp_after": after, "target_fainted": after == 0}
    return _authority(fingerprint, decision_owner, target_owner, move_id, "exact_complete", "fixed_damage_exact", result)


def _valid_input(value: Any, fingerprint: str, owner: Mapping[str, Any], target: Mapping[str, Any], move: str) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != _INPUT_SCHEMA or value.get("provenance") != _PROVENANCE:
        return False
    level = value.get("attacker_level_authority")
    types = value.get("target_type_authority")
    return value.get("session_id") == owner["session_id"] and value.get("source_branch_fingerprint") == fingerprint and value.get("decision_owner") == dict(owner) and value.get("attacker") == dict(owner) and value.get("target") == dict(target) and value.get("move_id") == move and isinstance(level, Mapping) and level.get("status") == "known" and isinstance(level.get("value"), int) and not isinstance(level.get("value"), bool) and 1 <= level["value"] <= 100 and isinstance(types, Mapping) and types.get("status") == "known" and isinstance(types.get("value"), list) and bool(types["value"]) and all(isinstance(item, str) and item for item in types["value"])


def _authority(fingerprint: str, owner: Mapping[str, Any], target: Mapping[str, Any], move: str, completeness: str, reason: str, result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    value = {"status": "resolved", "schema_version": _SCHEMA, "authority_class": "current_predictive_execution_authority", "session_id": owner["session_id"], "source_branch_fingerprint": fingerprint, "decision_owner": deepcopy(dict(owner)), "attacker": deepcopy(dict(owner)), "target": deepcopy(dict(target)), "move_id": move, "completeness": completeness, "reason": reason, "provenance": "current_predictive_fixed_damage_v1"}
    if result is not None:
        value["predicted_result"] = deepcopy(dict(result))
    return value


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _same_owner(active: Any, owner: Mapping[str, Any]) -> bool:
    return isinstance(active, Mapping) and dict(owner) == {key: active.get(key) for key in _OWNER_KEYS}


def _exact_hp(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and isinstance(value.get("max_hp"), int) and not isinstance(value.get("max_hp"), bool) and 0 <= value["current_hp"] <= value["max_hp"] and value["max_hp"] > 0 and value.get("fainted") is (value["current_hp"] == 0)


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
