"""Reuse frozen opponent incoming mechanics for one detached switched-in defender."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_opponent_action_evaluator import evaluate_opponent_action_candidate


def evaluate_switch_incoming_opponent_action(*, transition: Mapping[str, Any], entry_hazard_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate direct redirected move mechanics only; never a full switch outcome."""
    validated = _validate(transition)
    if validated is None:
        return _unavailable("invalid_switch_transition")
    target, action = validated
    hazard = deepcopy(dict(entry_hazard_result)) if isinstance(entry_hazard_result, Mapping) else None
    if isinstance(hazard, Mapping) and hazard.get("status") == "complete" and hazard.get("hazard_ko") is True:
        return _hazard_ko(transition, target, action, hazard)
    if _known_value(target.get("fainted_authority")) is True:
        return _unavailable("target_already_fainted")
    adapted_target = _target_after_entry_effects(target, hazard)
    adapted = _adapt_opponent_candidate(action, adapted_target, entry_effect_result=hazard)
    row = evaluate_opponent_action_candidate(adapted)
    return {
        "switch_candidate_id": transition["self_action"]["candidate_id"],
        "target_pokemon_id": target["pokemon_id"], "target_slot_index": target["slot_index"],
        "opponent_candidate_id": action.get("candidate_id"),
        "direct_incoming_supportability": row.get("mechanical_evaluation_status"),
        "move_success_evidence": deepcopy(row.get("move_success")),
        "damage_evidence": deepcopy(row.get("incoming_damage")),
        "q12_evidence": deepcopy(row.get("incoming_q12")),
        "entry_hazard_result": hazard,
        # Entry/exit mechanics are intentionally not executed.  Direct KO and
        # probability, if present in damage_evidence, are explicitly not a
        # complete switch-sequence survival claim.
        "full_switch_outcome_supportability": "unsupported_mechanic",
        "incompleteness_reasons": ["entry_effects_not_applied"],
    }


def _target_after_entry_effects(target: Mapping[str, Any], hazard: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(hazard, Mapping):
        return target
    copy = deepcopy(dict(target)); hp = copy.get("hp_authority")
    if hazard.get("status") == "complete" and isinstance(hazard.get("post_hazard_hp"), int) and isinstance(hp, Mapping) and hp.get("status") == "known":
        copy["hp_authority"] = deepcopy(dict(hp)); copy["hp_authority"]["current_hp"] = hazard["post_hazard_hp"]
    toxic = hazard.get("toxic_spikes_result")
    if isinstance(toxic, Mapping) and toxic.get("status") == "complete" and toxic.get("post_condition") in {"poison", "toxic"}:
        copy["persistent_condition_authority"] = {"status": "known", "value": toxic["post_condition"]}
    sticky = hazard.get("sticky_web_result")
    if isinstance(sticky, Mapping) and sticky.get("status") == "complete" and isinstance(sticky.get("speed_stage_after"), int):
        copy["prospective_speed_stage_authority"] = {"status": "known", "value": sticky["speed_stage_after"]}
    return copy


def _hazard_ko(transition: Mapping[str, Any], target: Mapping[str, Any], action: Mapping[str, Any], hazard: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "switch_candidate_id": transition["self_action"]["candidate_id"],
        "target_pokemon_id": target["pokemon_id"], "target_slot_index": target["slot_index"],
        "opponent_candidate_id": action.get("candidate_id"),
        "direct_incoming_supportability": "not_applicable",
        "move_success_evidence": None,
        "damage_evidence": None, "q12_evidence": None,
        "entry_hazard_result": deepcopy(dict(hazard)),
        "full_switch_outcome_supportability": "unsupported_mechanic",
        "incompleteness_reasons": ["other_entry_effects_not_applied"],
    }


def _validate(transition: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    if not isinstance(transition, Mapping) or transition.get("supportability") != "complete" or transition.get("switch_execution_status") != "executed" or transition.get("order_result") != "self_switch_first" or transition.get("target_redirection_supportability") != "complete":
        return None
    action, self_action = transition.get("redirected_opponent_action"), transition.get("self_action")
    post = transition.get("post_switch_snapshot")
    target = post.get("target_roster_mechanics") if isinstance(post, Mapping) else None
    active = post.get("self_active") if isinstance(post, Mapping) else None
    if not all(isinstance(value, Mapping) for value in (action, self_action, target, active)):
        return None
    if target.get("session_id") != self_action.get("session_id") or target.get("side") != "self":
        return None
    if target.get("slot_index") != self_action.get("target_slot_index") or target.get("pokemon_id") != self_action.get("target_pokemon_id"):
        return None
    if active.get("slot_index") != target.get("slot_index") or active.get("pokemon_id") != target.get("pokemon_id"):
        return None
    redirect = action.get("redirected_target")
    if not isinstance(redirect, Mapping) or redirect.get("side") != "self" or redirect.get("slot_index") != target.get("slot_index") or redirect.get("pokemon_id") != target.get("pokemon_id"):
        return None
    if action.get("role") != "opponent_action" or action.get("acting_side") != "opponent" or action.get("target_side") != "self":
        return None
    return target, action


def _adapt_opponent_candidate(action: Mapping[str, Any], target: Mapping[str, Any], *, entry_effect_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    candidate = deepcopy(dict(action)); snapshot = candidate.get("mechanics_snapshot")
    if not isinstance(snapshot, Mapping):
        return candidate
    snapshot = deepcopy(dict(snapshot)); battle = snapshot.get("battle_context")
    battle = deepcopy(dict(battle)) if isinstance(battle, Mapping) else {}
    current = deepcopy(dict(battle.get("current_state"))) if isinstance(battle.get("current_state"), Mapping) else {}
    _replace_self_authority(current, target)
    _replace_opponent_attack_stage(current, action, entry_effect_result)
    provenance = deepcopy(dict(battle.get("stat_provenance"))) if isinstance(battle.get("stat_provenance"), Mapping) else {}
    provenance["defender"] = _defender_provenance(target)
    snapshot["defender"] = {"species_id": target["pokemon_id"], "slot_index": target["slot_index"]}
    battle["current_state"] = current; battle["stat_provenance"] = provenance; snapshot["battle_context"] = battle
    candidate["mechanics_snapshot"] = snapshot
    return candidate


def _replace_self_authority(current: dict[str, Any], target: Mapping[str, Any]) -> None:
    # Remove active A records before optionally supplying B-owned equivalents.
    for key, list_key in (("ability_context", "current_abilities"), ("current_type_context", "current_types"), ("current_hp_context", "current_hp"), ("final_stat_context", "current_final_stats"), ("condition_context", "current_conditions"), ("stat_stage_context", "current_stages")):
        context = current.get(key)
        if isinstance(context, Mapping):
            current[key] = {list_key: [deepcopy(entry) for entry in context.get(list_key, []) if isinstance(entry, Mapping) and entry.get("side") != "self"]}
    ability = _known_value(target.get("ability_authority"))
    if isinstance(ability, str): current.setdefault("ability_context", {"current_abilities": []})["current_abilities"].append({"side": "self", "ability": ability})
    hp = target.get("hp_authority")
    if isinstance(hp, Mapping) and hp.get("status") == "known" and hp.get("provenance") == "user_confirmed_current_hp":
        current.setdefault("current_hp_context", {"current_hp": []})["current_hp"].append({"side": "self", "current_hp": hp["current_hp"], "maximum_hp": hp["maximum_hp"], "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"})
    condition = _known_value(target.get("persistent_condition_authority"))
    if condition in {None, "none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"}:
        current.setdefault("condition_context", {"current_conditions": []})["current_conditions"].append({"side": "self", "condition_type": "none" if condition is None else condition, "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"})
    speed_stage = _known_value(target.get("prospective_speed_stage_authority"))
    if isinstance(speed_stage, int) and not isinstance(speed_stage, bool) and -6 <= speed_stage <= 6:
        current.setdefault("stat_stage_context", {"current_stages": []})["current_stages"].append({"side": "self", "stat": "speed", "stage": speed_stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"})


def _replace_opponent_attack_stage(current: dict[str, Any], action: Mapping[str, Any], entry_effect_result: Mapping[str, Any] | None) -> None:
    """Inject only an identity-matched post-Intimidate Attack stage.

    The action snapshot remains the owner of the opponent move.  This replaces
    its stale side-stage record only after the frozen entry result has already
    proved the exact opposing active identity and clamped transition.
    """
    result = entry_effect_result.get("intimidate_result") if isinstance(entry_effect_result, Mapping) else None
    identity = result.get("opponent_identity") if isinstance(result, Mapping) else None
    stage = result.get("attack_stage_after") if isinstance(result, Mapping) else None
    if not _matches_action_attacker(action, identity) or not isinstance(stage, int) or isinstance(stage, bool) or not -6 <= stage <= 6:
        return
    context = current.get("stat_stage_context")
    entries = context.get("current_stages") if isinstance(context, Mapping) else []
    if not isinstance(entries, list):
        return
    current["stat_stage_context"] = {"current_stages": [deepcopy(entry) for entry in entries if isinstance(entry, Mapping) and not (entry.get("side") == "opponent" and entry.get("stat") == "attack")]}
    current["stat_stage_context"]["current_stages"].append({"side": "opponent", "stat": "attack", "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"})


def _matches_action_attacker(action: Mapping[str, Any], identity: Any) -> bool:
    if not isinstance(identity, Mapping) or identity.get("side") != "opponent":
        return False
    snapshot = action.get("mechanics_snapshot") if isinstance(action, Mapping) else None
    attacker = snapshot.get("attacker") if isinstance(snapshot, Mapping) else None
    return isinstance(attacker, Mapping) and attacker.get("species_id") == identity.get("pokemon_id") and attacker.get("slot_index") == identity.get("slot_index")


def _defender_provenance(target: Mapping[str, Any]) -> dict[str, Any]:
    types, base, final = (_known_value(target.get(key)) for key in ("current_type_authority", "base_stat_authority", "final_stat_authority"))
    type_known = isinstance(types, list) and all(isinstance(value, str) and value for value in types)
    stats = lambda value: isinstance(value, Mapping) and all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] > 0 for key in ("hp", "attack", "defense", "special-attack", "special-defense", "speed"))
    return {
        "pokemon_identity": target["pokemon_id"], "side": "self", "slot_index": target["slot_index"], "session_id": target["session_id"],
        "types": {"available": type_known, "value": deepcopy(types) if type_known else None},
        "type_authority": {"status": "known", "basis": "current_type_context", "reason": None} if type_known else {"status": "unknown", "basis": "current_type_context", "reason": "current_type_unknown"},
        "base_stats": {"available": stats(base), "value": deepcopy(base) if stats(base) else None},
        "final_stats": {"available": stats(final), "value": deepcopy(final) if stats(final) else None},
        "known_ability": {"available": isinstance(_known_value(target.get("ability_authority")), str), "value": _known_value(target.get("ability_authority"))},
        "known_item": {"available": target.get("item_authority", {}).get("status") == "known", "value": _known_value(target.get("item_authority"))},
    }


def _known_value(authority: Any) -> Any:
    return authority.get("value") if isinstance(authority, Mapping) and authority.get("status") == "known" else None


def _unavailable(reason: str) -> dict[str, Any]:
    return {"switch_candidate_id": None, "opponent_candidate_id": None, "direct_incoming_supportability": "insufficient_context", "move_success_evidence": None, "damage_evidence": None, "q12_evidence": None, "entry_hazard_result": None, "full_switch_outcome_supportability": "insufficient_context", "incompleteness_reasons": [reason]}
