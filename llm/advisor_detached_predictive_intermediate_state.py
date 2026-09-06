"""Materialize one exact first-action terminal leaf into detached state.

This owner is intentionally a projection boundary, not a second damage engine:
it reads an already-normalized terminal leaf and overlays only its exact
consequences on frozen D0 authority.  The output is never reducer authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0, runtime_strategy_d0_freshness


SCHEMA_VERSION = "detached-predictive-intermediate-state-v1"
HORIZON = "immediate_action_pair"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STAGE_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")


def materialize_detached_predictive_intermediate_state(
    *, strategy_d0: Mapping[str, Any], terminal_leaf: Mapping[str, Any],
    root_predictive_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project exact leaf consequences without mutating D0 or runtime state."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    if isinstance(terminal_leaf, Mapping) and terminal_leaf.get("action_type") == "manual_switch":
        return _result("unsupported", "manual_switch_terminal_leaf_intermediate_state_adapter_unavailable", base)
    bound = _leaf_binding(terminal_leaf, strategy_d0, root_predictive_authority)
    if isinstance(bound, str):
        return _result("rejected", bound, base)
    consequences = terminal_leaf.get("consequences")
    if not isinstance(consequences, Mapping):
        return _result("rejected", "terminal_leaf_consequences_missing", base)
    own_hp, target_hp = consequences.get("own_final_hp"), consequences.get("target_final_hp")
    if not _hp(own_hp) or not _hp(target_hp):
        return _result("incomplete", "terminal_leaf_exact_post_action_hp_missing", {**base, **bound})
    actor, target = bound["attacker"], bound["target"]
    stage_effects = _stage_effects(terminal_leaf, consequences)
    if isinstance(stage_effects, str):
        return _result("rejected", stage_effects, {**base, **bound})
    flinch = _flinch_cancellation_consequence(consequences, target)
    if isinstance(flinch, str):
        return _result("rejected", flinch, {**base, **bound})
    state = {
        "schema_version": SCHEMA_VERSION,
        "status": "resolved",
        "horizon": HORIZON,
        **base,
        "first_action": {
            "candidate_id": terminal_leaf["candidate_id"], "action_type": terminal_leaf["action_type"],
            "move_id": bound["move_id"], "leaf_id": terminal_leaf["leaf_id"],
            "branch_path": deepcopy(tuple(terminal_leaf["branch_path"])),
            "probability": deepcopy(dict(terminal_leaf["probability"])),
            "damage_roll": deepcopy(terminal_leaf.get("damage_roll")),
            "hit_state": terminal_leaf.get("hit_state"), "critical_state": terminal_leaf.get("critical_state"),
            "provenance": deepcopy(dict(terminal_leaf["provenance"])),
            "root_predictive_authority": _root_provenance(root_predictive_authority),
        },
        "active": {
            actor["side"]: _participant(strategy_d0, actor, own_hp, stage_effects, "self"),
            target["side"]: _participant(strategy_d0, target, target_hp, stage_effects, "target"),
        },
        "unchanged_authority": _unchanged_authority(strategy_d0),
        "second_action_compatibility": {
            "faint_cancellation": {
                "status": "resolved", "actor_can_act": own_hp > 0,
                "target_can_act": target_hp > 0,
                "rule": "second_selected_action_cancelled_if_its_actor_is_fainted",
            },
            "flinch_cancellation": flinch,
            "other_cancellation_mechanics": {
                "status": "unsupported", "reason": "disable_lock_and_related_cancellation_not_materialized_v1",
            },
        },
        "provenance": "exact_terminal_leaf_to_detached_intermediate_state_v1",
    }
    return state


def freeze_detached_actor_neutral_root_predictive_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one opponent-root action to the original D0 without mutating it.

    The resulting synthetic D0 is only an input to the existing strict
    predictive builders.  It is deliberately tagged hypothetical and carries
    the original own-side D0 binding separately, so a later leaf cannot be
    mistaken for current reducer authority.
    """
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    parsed = _opponent_root_action(opponent_action, strategy_d0)
    if isinstance(parsed, str):
        return _result("rejected", parsed, base)
    predictive_d0 = freeze_runtime_strategy_d0(runtime_snapshot=runtime_snapshot, decision_owner=parsed["actor"])
    if predictive_d0.get("status") != "resolved":
        return _result("incomplete", predictive_d0.get("reason", "actor_neutral_root_d0_unavailable"), base)
    return {
        "status": "resolved", "schema_version": "detached-actor-neutral-root-predictive-authority-v1",
        "hypothetical": True, "horizon": HORIZON, **base,
        "root_actor": deepcopy(dict(parsed["actor"])), "root_target": deepcopy(dict(parsed["target"])),
        "root_action_id": parsed["action_id"], "move_id": parsed["move_id"],
        "move_metadata": deepcopy(parsed["metadata"]),
        "predictive_strategy_d0": deepcopy(dict(predictive_d0)),
        "predictive_runtime_snapshot": deepcopy(dict(runtime_snapshot)),
        "provenance": "original_frozen_d0_to_actor_neutral_opponent_root_predictive_context_v1",
    }


def _participant(d0: Mapping[str, Any], owner: Mapping[str, Any], hp: int, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    current_stages = d0.get("current_stage_authority", {}).get(owner["side"], {})
    current_condition = d0.get("current_condition_authority", {}).get(owner["side"], {})
    current_item = d0.get("strategy_state", {}).get("current_state", {}).get("runtime_strategy_d0_authority", {}).get("active", {}).get(owner["side"], {}).get("known_item", {})
    return {
        "owner": deepcopy(dict(owner)),
        "hypothetical_hp": {"status": "known", "value": hp, "source": "exact_terminal_leaf"},
        "hypothetical_fainted": {"status": "known", "value": hp == 0, "source": "exact_terminal_leaf"},
        "current_item_authority": deepcopy(current_item) if isinstance(current_item, Mapping) else {"status": "unknown"},
        "hypothetical_item": _item(current_item, effects, role),
        "current_stage_authority": deepcopy(current_stages),
        "hypothetical_stages": _stages(current_stages, effects, role),
        "current_condition_authority": deepcopy(current_condition),
        "hypothetical_condition": _condition(current_condition, effects, role),
    }


def _stages(authority: Any, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    source = authority.get("stages") if isinstance(authority, Mapping) else None
    result: dict[str, Any] = {}
    for stat in _STAGE_KEYS:
        current = source.get(stat) if isinstance(source, Mapping) else None
        value = {"status": "unknown", "reason": "current_stage_authority_unknown"}
        if isinstance(current, Mapping) and current.get("status") == "known":
            value = {"status": "known", "value": current.get("value"), "source": "frozen_current_stage_authority"}
        matching = [effect for effect in effects if effect.get("owner") == role and effect.get("stat") == stat]
        if matching:
            effect = matching[-1]
            resulting = effect.get("resulting_stage")
            if isinstance(resulting, int) and not isinstance(resulting, bool) and -6 <= resulting <= 6:
                value = {"status": "known", "value": resulting, "source": "exact_terminal_leaf_stage_effect", "effect": deepcopy(dict(effect))}
        result[stat] = value
    return result


def _condition(authority: Any, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    current = authority.get("condition") if isinstance(authority, Mapping) else None
    result = deepcopy(dict(current)) if isinstance(current, Mapping) else {"status": "unknown", "reason": "current_condition_authority_unknown"}
    for effect in effects:
        condition = effect.get("hypothetical_self_condition")
        if role == "self" and isinstance(condition, Mapping) and isinstance(condition.get("resulting_condition"), str):
            return {"status": "known_present", "condition": condition["resulting_condition"], "source": "exact_terminal_leaf_condition_effect", "effect": deepcopy(dict(condition))}
        condition = effect.get("hypothetical_target_condition")
        if role == "target" and isinstance(condition, Mapping) and isinstance(condition.get("resulting_condition"), str):
            return {"status": "known_present", "condition": condition["resulting_condition"], "source": "exact_terminal_leaf_condition_effect", "effect": deepcopy(dict(condition))}
        removal = effect.get("hypothetical_target_condition_removal")
        if role == "target" and isinstance(removal, Mapping):
            return {"status": "known_none", "source": "exact_terminal_leaf_condition_removal", "effect": deepcopy(dict(removal))}
    return result


def _item(authority: Any, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    result = deepcopy(dict(authority)) if isinstance(authority, Mapping) else {"status": "unknown", "reason": "current_item_authority_unknown"}
    for effect in effects:
        item = effect.get("hypothetical_target_item")
        if role == "target" and isinstance(item, Mapping):
            return deepcopy(dict(item))
    return result


def _stage_effects(leaf: Mapping[str, Any], consequences: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...] | str:
    result: list[Mapping[str, Any]] = []
    deterministic = consequences.get("deterministic_stage_effect")
    if isinstance(deterministic, Mapping):
        damage = consequences.get("damage")
        branches = deterministic.get("branches")
        matching = [row for row in branches if isinstance(row, Mapping) and row.get("raw_damage") == damage] if isinstance(branches, (tuple, list)) else []
        if not matching or not isinstance(matching[0].get("effects"), (tuple, list)):
            return "deterministic_stage_effect_leaf_identity_missing"
        if any(row.get("effects") != matching[0].get("effects") for row in matching):
            return "deterministic_stage_effect_leaf_identity_ambiguous"
        result.extend(row for row in matching[0]["effects"] if isinstance(row, Mapping))
    secondary = consequences.get("secondary")
    if isinstance(secondary, Mapping) and secondary.get("branch") == "effect":
        stage = secondary.get("hypothetical_stage_effect")
        if isinstance(stage, Mapping): result.append(stage)
        condition = secondary.get("hypothetical_target_condition")
        if isinstance(condition, Mapping): result.append({"owner": "target", "hypothetical_target_condition": condition})
        removal = secondary.get("hypothetical_target_condition_removal")
        if removal is not None:
            if not _condition_removal(removal, leaf.get("leaf_id")):
                return "terminal_leaf_condition_removal_consequence_invalid"
            result.append({"owner": "target", "hypothetical_target_condition_removal": removal})
    focus = consequences.get("focus_sash_survival")
    item_after = focus.get("item_after") if isinstance(focus, Mapping) else None
    if isinstance(focus, Mapping) and focus.get("outcome") == "applied" and isinstance(item_after, Mapping) and item_after.get("status") == "known_absent":
        result.append({"owner": "target", "hypothetical_target_item": {"status": "known_absent", "value": None, "source": "exact_terminal_leaf_focus_sash_consumption", "effect": deepcopy(dict(focus))}})
    knock_off = consequences.get("knock_off_item_removal")
    if isinstance(knock_off, Mapping) and knock_off.get("outcome") == "removed" and knock_off.get("item_after") is None:
        authority = knock_off.get("authority")
        if not isinstance(authority, Mapping) or authority.get("move_id") != "knock-off" or not isinstance(knock_off.get("item_before"), str):
            return "terminal_leaf_knock_off_item_removal_invalid"
        result.append({"owner": "target", "hypothetical_target_item": {"status": "known_absent", "value": None, "source": "exact_terminal_leaf_knock_off_item_removal", "effect": deepcopy(dict(knock_off))}})
    status = consequences.get("contact_reactive_status")
    overlay = status.get("overlay") if isinstance(status, Mapping) else None
    transition = overlay.get("hypothetical_condition_authority") if isinstance(overlay, Mapping) else None
    if isinstance(transition, Mapping) and overlay.get("transition_applied") is True and transition.get("status") == "known_present" and isinstance(transition.get("condition"), str):
        result.append({
            "owner": "self",
            "hypothetical_self_condition": {
                "schema_version": "detached-hypothetical-current-condition-v1",
                "previous_condition": {"status": "known_none"},
                "resulting_condition": transition["condition"],
                "source_reactive_status": deepcopy(dict(status)),
                "provenance": "contact_reactive_status_successful_damage_roll_v1",
            },
        })
    return tuple(deepcopy(dict(effect)) for effect in result)


def _condition_removal(value: Any, leaf_id: Any) -> bool:
    return isinstance(value, Mapping) and value == {
        "schema_version": "detached-hypothetical-target-condition-removal-v1",
        "condition_before": "burn", "condition_removed": "burn", "condition_after": "none",
        "removal_trigger": "successful_damaging_hit_target_survives",
        "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1",
        "source_leaf_id": leaf_id,
    }


def _flinch_cancellation_consequence(consequences: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | str:
    """Expose only an exact terminal-leaf flinch marker for the pending action."""
    secondary = consequences.get("secondary")
    if not isinstance(secondary, Mapping) or "hypothetical_target_flinch" not in secondary:
        return {"status": "resolved", "affected_owner": deepcopy(dict(target)), "state": "not_flinched", "provenance": "no_exact_first_action_flinch_consequence"}
    marker = secondary.get("hypothetical_target_flinch")
    provenance = marker.get("provenance") if isinstance(marker, Mapping) else None
    if secondary.get("branch") != "effect" or not isinstance(marker, Mapping) or marker.get("schema_version") != "detached-hypothetical-immediate-flinch-v1" or marker.get("state") != "flinched" or provenance not in {"iron_head_successful_damage_roll_secondary_v1", "fake_out_successful_damage_roll_secondary_v1"}:
        return "terminal_leaf_flinch_consequence_invalid"
    return {"status": "resolved", "affected_owner": deepcopy(dict(target)), "state": "flinched", "provenance": "exact_terminal_leaf_iron_head_flinch_secondary" if provenance == "iron_head_successful_damage_roll_secondary_v1" else "exact_terminal_leaf_fake_out_flinch_secondary"}


def _unchanged_authority(d0: Mapping[str, Any]) -> dict[str, Any]:
    current = d0.get("strategy_state", {}).get("current_state", {}).get("runtime_strategy_d0_authority", {})
    active = current.get("active") if isinstance(current, Mapping) else None
    field = current.get("field") if isinstance(current, Mapping) else None
    # Supported first-action leaves do not currently own type/item/ability or
    # field mutation.  Preserve only this narrow immutable authority summary.
    return {"status": "resolved", "active_current_authority": deepcopy(active) if isinstance(active, Mapping) else {}, "field_current_authority": deepcopy(field) if isinstance(field, Mapping) else {}, "carry_forward_rule": "only facts without a represented first_action consequence"}


def _leaf_binding(leaf: Any, d0: Mapping[str, Any], root_authority: Mapping[str, Any] | None = None) -> dict[str, Any] | str:
    if not isinstance(leaf, Mapping) or leaf.get("action_type") != "attack" or not isinstance(leaf.get("candidate_id"), str) or not isinstance(leaf.get("leaf_id"), str) or not isinstance(leaf.get("branch_path"), (tuple, list)) or not _fraction(leaf.get("probability")):
        return "invalid_terminal_leaf"
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping): return "terminal_leaf_provenance_missing"
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")
    if any(key not in provenance for key in required): return "terminal_leaf_provenance_incomplete"
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    root = _root_leaf_binding(root_authority, d0)
    if any(provenance.get(key) != value for key, value in expected.items()):
        if isinstance(root, str): return root if root_authority is not None else "terminal_leaf_binding_mismatch"
        expected = root["leaf_binding"]
        if any(provenance.get(key) != value for key, value in expected.items()): return "terminal_leaf_root_predictive_binding_mismatch"
    attacker, target = provenance["attacker"], provenance["target"]
    if not _owner(attacker) or not _owner(target) or attacker["side"] == target["side"] or d0.get("active_owners", {}).get(attacker["side"]) != dict(attacker) or d0.get("active_owners", {}).get(target["side"]) != dict(target): return "terminal_leaf_actor_target_identity_mismatch"
    if leaf["candidate_id"] != f"attack:{provenance['move_id']}": return "terminal_leaf_candidate_move_mismatch"
    if isinstance(root, Mapping) and (attacker != root["actor"] or target != root["target"] or provenance["move_id"] != root["move_id"]): return "terminal_leaf_root_actor_target_or_move_mismatch"
    return {"attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": provenance["move_id"]}


def _opponent_root_action(value: Any, d0: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "runtime-d0-opponent-known-move-action-authority-v1": return "opponent_root_action_authority_invalid"
    actor, target = value.get("opponent_actor"), value.get("target_owner")
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    if any(value.get(key) != item for key, item in expected.items()) or not _owner(actor) or not _owner(target) or actor != d0.get("active_owners", {}).get("opponent") or target != d0.get("active_owners", {}).get("self"): return "opponent_root_action_binding_mismatch"
    metadata = value.get("metadata_authority")
    move_id = value.get("move_id")
    if not isinstance(metadata, Mapping) or metadata.get("status") != "resolved" or metadata.get("move_id") != move_id or not isinstance(metadata.get("metadata"), Mapping) or metadata["metadata"].get("move_id") != move_id: return "opponent_root_move_metadata_authority_invalid"
    if value.get("selectability") != "selectable" or not isinstance(value.get("usability"), Mapping) or value["usability"].get("status") != "known_usable": return "opponent_root_action_not_known_usable"
    if not isinstance(value.get("action_id"), str) or not isinstance(move_id, str) or not move_id: return "opponent_root_action_identity_missing"
    return {"actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": value["action_id"], "move_id": move_id, "metadata": deepcopy(dict(metadata["metadata"]))}


def _root_leaf_binding(value: Any, d0: Mapping[str, Any]) -> dict[str, Any] | str:
    if value is None: return "root_predictive_authority_not_supplied"
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "detached-actor-neutral-root-predictive-authority-v1" or value.get("hypothetical") is not True: return "invalid_root_predictive_authority"
    original = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    if any(value.get(key) != item for key, item in original.items()): return "root_predictive_authority_original_d0_mismatch"
    predictive = value.get("predictive_strategy_d0")
    actor, target, move_id = value.get("root_actor"), value.get("root_target"), value.get("move_id")
    if not isinstance(predictive, Mapping) or predictive.get("status") != "resolved" or not _owner(actor) or not _owner(target) or not isinstance(move_id, str): return "root_predictive_authority_payload_invalid"
    expected = {"session_id": predictive.get("session_id"), "source_runtime_fingerprint": predictive.get("source_runtime_fingerprint"), "source_branch_fingerprint": predictive.get("strategy_preview_fingerprint"), "decision_owner": predictive.get("decision_owner")}
    if not all(value for value in expected.values()) or expected["decision_owner"] != actor: return "root_predictive_authority_predictive_d0_invalid"
    return {"leaf_binding": expected, "actor": actor, "target": target, "move_id": move_id}


def _root_provenance(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("schema_version") != "detached-actor-neutral-root-predictive-authority-v1": return None
    return {"schema_version": value["schema_version"], "hypothetical": True, "root_action_id": value.get("root_action_id"), "root_actor": deepcopy(value.get("root_actor")), "root_target": deepcopy(value.get("root_target")), "provenance": value.get("provenance")}


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(d0.get("decision_owner")) or not isinstance(d0.get("active_owners"), Mapping): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"]))}
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _fraction(value: Any) -> bool: return isinstance(value, Mapping) and isinstance(value.get("numerator"), int) and not isinstance(value.get("numerator"), bool) and isinstance(value.get("denominator"), int) and not isinstance(value.get("denominator"), bool) and 0 < value["denominator"] and 0 < value["numerator"] <= value["denominator"]
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
