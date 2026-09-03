"""Strict detached post-contact status authority for contact-status abilities."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-contact-reactive-status-authority-v1"
OVERLAY_SCHEMA_VERSION = "detached-contact-reactive-status-overlay-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_CONDITIONS = frozenset({"burn", "poison", "toxic", "paralysis", "sleep", "freeze"})
_ABILITY_TO_CONDITION = {"static": "paralysis", "flame-body": "burn", "poison-point": "poison"}
_SUPPORTED_ABILITIES = frozenset({*_ABILITY_TO_CONDITION, "effect-spore"})
_ABILITY_ORDER = {"static": 0, "flame-body": 0, "poison-point": 0, "effect-spore": 0}
_EFFECT_SPORE_OUTCOMES = (
    ("sleep", Fraction(11, 100)),
    ("paralysis", Fraction(10, 100)),
    ("poison", Fraction(9, 100)),
    ("none", Fraction(70, 100)),
)
_PREVENTING_ABILITIES = {
    "paralysis": {"limber", "comatose", "purifying-salt"},
    "burn": {"water-veil", "water-bubble", "comatose", "purifying-salt", "thermal-exchange"},
    "poison": {"immunity", "comatose", "purifying-salt"},
    "sleep": {"insomnia", "vital-spirit", "comatose", "purifying-salt"},
}


def contact_reactive_status_relevance(*, runtime_snapshot: Mapping[str, Any], defender: Mapping[str, Any]) -> dict[str, Any]:
    """Classify whether this defender has a supported contact-status ability."""
    modifiers = _current_modifier_authorities(runtime_snapshot, defender)
    if modifiers is None:
        return {"status": "incomplete", "reason": "contact_reactive_status_defender_ability_unknown"}
    ability = modifiers["ability_authority"].get("value")
    return {
        "status": "resolved",
        "relevant": ability in _SUPPORTED_ABILITIES,
        "defender_modifier_authorities": deepcopy(modifiers),
    }


def freeze_runtime_d0_contact_reactive_status_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any],
    defender: Mapping[str, Any],
    source_action: Mapping[str, Any],
    contact_authority: Mapping[str, Any] | None,
    source_hit: Mapping[str, Any],
    attacker_condition_authority: Mapping[str, Any] | None = None,
    attacker_fainted_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one immediate post-damaging-contact status event."""
    base = _base(strategy_d0, attacker, defender, source_action)
    if base is None:
        return _result("rejected", "invalid_contact_reactive_status_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    contact = _contact(contact_authority, base)
    if contact == "mismatch":
        return _result("rejected", "contact_reactive_status_contact_authority_binding_mismatch", base)
    if not isinstance(contact_authority, Mapping) or contact_authority.get("status") != "resolved":
        reason = contact_authority.get("reason", "contact_reactive_status_contact_authority_unavailable") if isinstance(contact_authority, Mapping) else "contact_reactive_status_contact_authority_missing"
        return _result("incomplete", reason, base)
    hit = _source_hit(source_hit, base)
    if isinstance(hit, str):
        return _result("rejected", hit, base)
    if contact_authority.get("contact_state") == "non_contact":
        return _not_applicable(base, contact_authority, hit, "source_hit_known_non_contact")
    if contact_authority.get("contact_state") != "contact":
        return _result("rejected", "contact_reactive_status_contact_state_invalid", base)
    if hit["target_routing"] == "substitute":
        return _not_applicable(base, contact_authority, hit, "source_hit_contacted_substitute_not_holder")
    if hit["actual_damage"] <= 0:
        return _not_applicable(base, contact_authority, hit, "source_hit_no_damage")
    modifiers = _current_modifier_authorities(runtime_snapshot, base["defender"])
    if modifiers is None:
        return _result("incomplete", "contact_reactive_status_defender_ability_unknown", base)
    ability = modifiers["ability_authority"].get("value")
    if ability not in _SUPPORTED_ABILITIES:
        return {
            "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
            "outcome": "no_reactive_source", "reactive_ability": ability,
            "ordered_sources": (), "contact_authority": deepcopy(dict(contact_authority)),
            "source_hit": hit, "defender_modifier_authorities": modifiers,
            "provenance": "runtime_d0_contact_reactive_status_no_source_v1",
        }
    current_condition = _condition_authority(attacker_condition_authority, strategy_d0, runtime_snapshot, base["attacker"])
    if current_condition.get("status") != "resolved":
        return _result(current_condition.get("status", "rejected"), current_condition.get("reason", "contact_reactive_status_attacker_condition_unknown"), base)
    condition_before = _condition_state(current_condition)
    if condition_before is None:
        return _result("incomplete", "contact_reactive_status_attacker_condition_unknown", base)
    attacker_modifiers = _current_modifier_authorities(runtime_snapshot, base["attacker"])
    if attacker_modifiers is None:
        return _result("incomplete", "contact_reactive_status_prevention_authority_unknown", base)
    fainted = _fainted(attacker_fainted_authority)
    if fainted is None:
        return _result("incomplete", "contact_reactive_status_attacker_fainted_authority_unknown", base)
    type_authority = None
    if ability == "effect-spore":
        type_authority = _runtime_type_authority(runtime_snapshot, base["attacker"])
        if type_authority.get("status") != "resolved":
            return _result(type_authority["status"], type_authority["reason"], base)
        immunity = _effect_spore_immunity(type_authority, attacker_modifiers)
        if immunity["outcome"] == "immune":
            return _not_applicable(base, contact_authority, hit, immunity["reason"], reactive_ability=ability,
                                   defender_modifier_authorities=modifiers, attacker_modifier_authorities=attacker_modifiers,
                                   type_authority=type_authority, effect_spore_immunity=immunity)
        return _effect_spore_authority(
            base=base, contact_authority=contact_authority, hit=hit, modifiers=modifiers,
            attacker_modifiers=attacker_modifiers, current_condition=current_condition,
            condition_before=condition_before, type_authority=type_authority, fainted=fainted,
        )
    attempted = _ABILITY_TO_CONDITION[ability]
    prevention = {"status": "resolved", "outcome": "not_prevented", "reason": None}
    if condition_before == "none" and not fainted:
        type_authority = _runtime_type_authority(runtime_snapshot, base["attacker"])
        if type_authority.get("status") != "resolved":
            return _result(type_authority["status"], type_authority["reason"], base)
        prevention = _prevention(attempted, type_authority, attacker_modifiers)
    blocked_reason = (
        "attacker_fainted_before_reactive_status" if fainted else
        "attacker_already_statused" if condition_before != "none" else
        prevention["reason"] if prevention["outcome"] == "prevented" else None
    )
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "outcome": "applies", "reactive_ability": ability,
        "attempted_condition": attempted, "condition_before": condition_before,
        "activation_probability": {"numerator": 3, "denominator": 10},
        "no_activation_probability": {"numerator": 7, "denominator": 10},
        "event_order": _ABILITY_ORDER[ability],
        "blocked_reason": blocked_reason,
        "transition_applies": blocked_reason is None,
        "contact_authority": deepcopy(dict(contact_authority)),
        "source_hit": hit, "condition_authority": current_condition,
        "type_authority": deepcopy(dict(type_authority)) if isinstance(type_authority, Mapping) else None,
        "prevention_authority": deepcopy(dict(prevention)),
        "defender_modifier_authorities": modifiers,
        "attacker_modifier_authorities": attacker_modifiers,
        "attacker_fainted_authority": {"status": "known", "value": fainted},
        "provenance": "runtime_d0_canonical_contact_reactive_status_ability_family_v1",
    }


def materialize_detached_contact_reactive_status(*, authority: Mapping[str, Any], branch: str) -> dict[str, Any]:
    """Project one exact activation/no-activation branch into detached condition state."""
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION:
        return {"status": "rejected", "reason": "invalid_contact_reactive_status_authority"}
    if authority.get("status") != "resolved":
        return {"status": authority.get("status", "rejected"), "reason": authority.get("reason", "contact_reactive_status_unavailable")}
    allowed = {"activation", "no_activation"} if authority.get("reactive_ability") != "effect-spore" else {"sleep", "paralysis", "poison", "none"}
    if branch not in allowed:
        return {"status": "rejected", "reason": "contact_reactive_status_branch_invalid"}
    if authority.get("outcome") != "applies":
        return _overlay_no_transition(authority, branch, authority.get("reason", authority.get("outcome", "not_applicable")))
    if authority.get("reactive_ability") == "effect-spore":
        if not _valid_effect_spore_outcomes(authority.get("effect_spore_outcomes")):
            return {"status": "rejected", "reason": "effect_spore_outcomes_invalid"}
        outcome = next((row for row in authority.get("effect_spore_outcomes", ()) if isinstance(row, Mapping) and row.get("outcome") == branch), None)
        if not isinstance(outcome, Mapping):
            return {"status": "rejected", "reason": "effect_spore_outcome_missing"}
        probability = outcome.get("probability")
        if not isinstance(probability, Mapping):
            return {"status": "rejected", "reason": "effect_spore_outcome_probability_invalid"}
        if branch == "none":
            return _overlay_no_transition(authority, branch, "no_activation", probability=probability)
        if outcome.get("transition_applies") is not True:
            return _overlay_no_transition(authority, branch, outcome.get("blocked_reason", "activation_no_transition"), probability=probability)
        transition = {
            "status": "known_present", "condition": branch,
            "condition_before": "known_none", "condition_after": branch,
            "trigger": "successful_damaging_contact_hit",
            "source_consequence_id": f"contact_reactive_status:effect-spore:{branch}",
            "source_hit": deepcopy(dict(authority["source_hit"])),
            "provenance": "detached_contact_reactive_status_condition_transition_v1",
        }
        return {
            "status": "resolved", "schema_version": OVERLAY_SCHEMA_VERSION,
            "branch": branch, "probability": deepcopy(dict(probability)),
            "transition_applied": True, "owner": deepcopy(dict(authority["attacker"])),
            "hypothetical_condition_authority": transition, "source_authority": deepcopy(dict(authority)),
            "cancels_remaining_hits": branch == "sleep",
            "cancellation_reason": "effect_spore_sleep_cancels_remaining_hits" if branch == "sleep" else None,
            "provenance": "detached_contact_reactive_status_overlay_v1",
        }
    probability = authority["activation_probability"] if branch == "activation" else authority["no_activation_probability"]
    if branch == "no_activation":
        return _overlay_no_transition(authority, branch, "no_activation", probability=probability)
    if probability != {"numerator": 3, "denominator": 10}:
        return {"status": "rejected", "reason": "contact_reactive_status_activation_probability_invalid"}
    if authority.get("transition_applies") is not True:
        return _overlay_no_transition(authority, branch, authority.get("blocked_reason", "activation_no_transition"), probability=probability)
    attempted = authority.get("attempted_condition")
    if attempted not in {"paralysis", "burn", "poison"} or authority.get("condition_before") != "none":
        return {"status": "rejected", "reason": "contact_reactive_status_transition_invalid"}
    transition = {
        "status": "known_present", "condition": attempted,
        "condition_before": "known_none", "condition_after": attempted,
        "trigger": "successful_damaging_contact_hit",
        "source_consequence_id": f"contact_reactive_status:{authority['reactive_ability']}:{attempted}",
        "source_hit": deepcopy(dict(authority["source_hit"])),
        "provenance": "detached_contact_reactive_status_condition_transition_v1",
    }
    return {
        "status": "resolved", "schema_version": OVERLAY_SCHEMA_VERSION,
        "branch": branch, "probability": deepcopy(probability),
        "transition_applied": True, "owner": deepcopy(dict(authority["attacker"])),
        "hypothetical_condition_authority": transition,
        "source_authority": deepcopy(dict(authority)),
        "provenance": "detached_contact_reactive_status_overlay_v1",
    }


def contact_reactive_status_branches(*, authority: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return serialized exact branches for an already-frozen event."""
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("outcome") != "applies":
        branch = "none" if isinstance(authority, Mapping) and authority.get("reactive_ability") == "effect-spore" else "no_activation"
        overlay = materialize_detached_contact_reactive_status(authority=authority, branch=branch)
        return ({"branch": "not_applicable", "factor": Fraction(1, 1), "overlay": overlay},)
    if authority.get("reactive_ability") == "effect-spore":
        rows = []
        for outcome, probability in _EFFECT_SPORE_OUTCOMES:
            overlay = materialize_detached_contact_reactive_status(authority=authority, branch=outcome)
            rows.append({"branch": outcome, "factor": probability, "overlay": overlay})
        return tuple(rows)
    return (
        {"branch": "activation", "factor": Fraction(3, 10), "overlay": materialize_detached_contact_reactive_status(authority=authority, branch="activation")},
        {"branch": "no_activation", "factor": Fraction(7, 10), "overlay": materialize_detached_contact_reactive_status(authority=authority, branch="no_activation")},
    )


def condition_from_overlay(overlay: Mapping[str, Any] | None, fallback: str) -> str:
    if not isinstance(overlay, Mapping) or overlay.get("transition_applied") is not True:
        return fallback
    condition = overlay.get("hypothetical_condition_authority")
    value = condition.get("condition") if isinstance(condition, Mapping) else None
    return value if value in _CONDITIONS else fallback


def _valid_effect_spore_outcomes(value: Any) -> bool:
    if not isinstance(value, (tuple, list)) or len(value) != len(_EFFECT_SPORE_OUTCOMES):
        return False
    expected = {
        outcome: _fraction(probability)
        for outcome, probability in _EFFECT_SPORE_OUTCOMES
    }
    actual: dict[str, Mapping[str, Any]] = {}
    for row in value:
        if not isinstance(row, Mapping) or row.get("outcome") not in expected or row["outcome"] in actual:
            return False
        actual[row["outcome"]] = row
    return set(actual) == set(expected) and all(
        row.get("probability") == expected[outcome]
        and isinstance(row.get("transition_applies"), bool)
        and (outcome != "none" or row.get("transition_applies") is False)
        for outcome, row in actual.items()
    )


def _effect_spore_authority(*, base: Mapping[str, Any], contact_authority: Mapping[str, Any], hit: Mapping[str, Any], modifiers: Mapping[str, Any], attacker_modifiers: Mapping[str, Any], current_condition: Mapping[str, Any], condition_before: str, type_authority: Mapping[str, Any], fainted: bool) -> dict[str, Any]:
    outcomes = []
    for condition, probability in _EFFECT_SPORE_OUTCOMES:
        if condition == "none":
            outcomes.append({"outcome": condition, "probability": _fraction(probability), "transition_applies": False, "blocked_reason": "no_activation", "prevention_authority": None})
            continue
        prevention = _prevention(condition, type_authority, attacker_modifiers)
        blocked = (
            "attacker_fainted_before_reactive_status" if fainted else
            "attacker_already_statused" if condition_before != "none" else
            prevention["reason"] if prevention["outcome"] == "prevented" else None
        )
        outcomes.append({"outcome": condition, "probability": _fraction(probability), "transition_applies": blocked is None, "blocked_reason": blocked, "prevention_authority": deepcopy(dict(prevention))})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)),
        "outcome": "applies", "reactive_ability": "effect-spore", "condition_before": condition_before,
        "effect_spore_immunity": {"status": "resolved", "outcome": "not_immune", "reason": None},
        "effect_spore_outcomes": tuple(outcomes), "event_order": _ABILITY_ORDER["effect-spore"],
        "contact_authority": deepcopy(dict(contact_authority)), "source_hit": deepcopy(dict(hit)),
        "condition_authority": deepcopy(dict(current_condition)), "type_authority": deepcopy(dict(type_authority)),
        "defender_modifier_authorities": deepcopy(dict(modifiers)), "attacker_modifier_authorities": deepcopy(dict(attacker_modifiers)),
        "attacker_fainted_authority": {"status": "known", "value": fainted},
        "provenance": "runtime_d0_canonical_contact_reactive_status_ability_family_v1",
    }


def _effect_spore_immunity(types: Mapping[str, Any], modifiers: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    values = set(types.get("types", ()))
    ability = modifiers["ability_authority"].get("value")
    item = modifiers["item_authority"].get("value")
    if "grass" in values:
        return {"status": "resolved", "outcome": "immune", "reason": "attacker_grass_type_immune"}
    if ability == "overcoat":
        return {"status": "resolved", "outcome": "immune", "reason": "attacker_overcoat_immune"}
    if item == "safety-goggles":
        return {"status": "resolved", "outcome": "immune", "reason": "attacker_safety_goggles_immune"}
    return {"status": "resolved", "outcome": "not_immune", "reason": None}


def _overlay_no_transition(authority: Mapping[str, Any], branch: str, reason: Any, *, probability: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "resolved", "schema_version": OVERLAY_SCHEMA_VERSION,
        "branch": branch, "probability": deepcopy(dict(probability)) if isinstance(probability, Mapping) else {"numerator": 1, "denominator": 1},
        "transition_applied": False, "blocked_reason": reason,
        "owner": deepcopy(dict(authority["attacker"])) if isinstance(authority.get("attacker"), Mapping) else None,
        "source_authority": deepcopy(dict(authority)),
        "provenance": "detached_contact_reactive_status_no_transition_v1",
    }


def _base(d0: Any, attacker: Any, defender: Any, action: Any) -> dict[str, Any] | None:
    try:
        attacker_owner, defender_owner = _owner(attacker), _owner(defender)
    except ValueError:
        return None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or attacker_owner["side"] == defender_owner["side"] or not isinstance(action, Mapping) or not isinstance(action.get("action_id"), str) or not action.get("action_id") or not isinstance(action.get("identity"), str) or not action.get("identity"):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(attacker_owner["side"]) != attacker_owner or active.get(defender_owner["side"]) != defender_owner:
        return None
    return {
        "session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")),
        "attacker": attacker_owner, "defender": defender_owner, "source_action_id": action["action_id"], "source_move_id": action["identity"],
    }


def _contact(value: Any, base: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping):
        return None
    expected = {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"], "action_id": base["source_action_id"], "attacker": base["attacker"], "target": base["defender"]}
    move_id = value.get("move_id")
    metadata = value.get("move_metadata_authority")
    if move_id is None and isinstance(metadata, Mapping):
        move_id = metadata.get("move_id")
    return None if all(value.get(key) == item for key, item in expected.items()) and move_id == base["source_move_id"] else "mismatch"


def _source_hit(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping):
        return "contact_reactive_status_source_hit_missing"
    actual = value.get("actual_damage")
    target_routing = value.get("target_routing", "target")
    if value.get("source_action_id") != base["source_action_id"] or value.get("source_move_id") != base["source_move_id"]:
        return "contact_reactive_status_source_hit_binding_mismatch"
    if target_routing not in {"target", "substitute"}:
        return "contact_reactive_status_source_hit_routing_invalid"
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        return "contact_reactive_status_source_hit_damage_invalid"
    return deepcopy(dict(value))


def _condition_authority(value: Mapping[str, Any] | None, d0: Mapping[str, Any], snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    if value is None:
        return freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=owner)
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("owner") != owner:
        return {"status": "rejected", "reason": "contact_reactive_status_condition_authority_invalid"}
    condition = value.get("condition")
    if not isinstance(condition, Mapping) or condition.get("status") not in {"known_none", "known_present"}:
        return {"status": "rejected", "reason": "contact_reactive_status_condition_authority_invalid"}
    return deepcopy(dict(value))


def _condition_state(authority: Mapping[str, Any]) -> str | None:
    condition = authority.get("condition")
    if not isinstance(condition, Mapping):
        return None
    if condition.get("status") == "known_none":
        return "none"
    if condition.get("status") == "known_present" and condition.get("condition") in _CONDITIONS:
        return condition["condition"]
    return None


def _fainted(value: Any) -> bool | None:
    if value is None:
        return False
    if not isinstance(value, Mapping) or value.get("status") != "known" or not isinstance(value.get("value"), bool):
        return None
    return value["value"]


def _runtime_type_authority(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    pokemon = _runtime_pokemon(snapshot, owner)
    if pokemon is None:
        return {"status": "rejected", "reason": "contact_reactive_status_attacker_runtime_identity_mismatch"}
    types, provenance = pokemon.get("current_type"), pokemon.get("current_type_provenance")
    if not isinstance(types, list) or not types or any(not isinstance(item, str) or not item for item in types) or len(types) != len(set(types)) or not _trusted(provenance, "current_type_observed"):
        return {"status": "incomplete", "reason": "contact_reactive_status_attacker_type_unknown"}
    return {"status": "resolved", "types": tuple(types), "provenance": "runtime_current_type_observed"}


def _prevention(condition: str, types: Mapping[str, Any], modifiers: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    values = set(types.get("types", ()))
    if condition == "paralysis" and "electric" in values:
        return {"status": "resolved", "outcome": "prevented", "reason": "attacker_electric_type_immune"}
    if condition == "burn" and "fire" in values:
        return {"status": "resolved", "outcome": "prevented", "reason": "attacker_fire_type_immune"}
    if condition == "poison" and {"poison", "steel"} & values:
        return {"status": "resolved", "outcome": "prevented", "reason": "attacker_poison_or_steel_type_immune"}
    ability = modifiers["ability_authority"].get("value")
    if ability in _PREVENTING_ABILITIES[condition]:
        return {"status": "resolved", "outcome": "prevented", "reason": f"attacker_{ability}_prevents_{condition}"}
    return {"status": "resolved", "outcome": "not_prevented", "reason": None}


def _current_modifier_authorities(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    pokemon = _runtime_pokemon(snapshot, owner)
    if pokemon is None:
        return None
    ability, ability_provenance = pokemon.get("current_ability"), pokemon.get("current_ability_provenance")
    item, item_provenance = pokemon.get("known_item"), pokemon.get("known_item_provenance")
    if not isinstance(ability, str) or not ability or not _trusted(ability_provenance, "current_ability_observed") or not _trusted(item_provenance, "current_item_observed"):
        return None
    if item is None and item_provenance.get("status") == "known_absent":
        item_authority = {"status": "known_absent"}
    elif isinstance(item, str) and item and item_provenance.get("status") == "known":
        item_authority = {"status": "known", "value": item}
    else:
        return None
    return {"ability_authority": {"status": "known", "value": ability}, "item_authority": item_authority}


def _runtime_pokemon(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    return pokemon if isinstance(pokemon, Mapping) and pokemon.get("pokemon_id") == owner.get("pokemon_id") else None


def _not_applicable(base: Mapping[str, Any], contact: Mapping[str, Any], hit: Mapping[str, Any], reason: str, **extra: Any) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "reason": reason, "contact_authority": deepcopy(dict(contact)), "source_hit": deepcopy(dict(hit)), **deepcopy(extra), "provenance": "runtime_d0_contact_reactive_status_not_applicable_v1"}


def _fraction(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _owner(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_OWNER_KEYS) or not isinstance(value.get("session_id"), str) or not value["session_id"] or value.get("side") not in {"self", "opponent"} or not isinstance(value.get("slot_index"), int) or isinstance(value["slot_index"], bool) or value["slot_index"] < 0 or not isinstance(value.get("pokemon_id"), str) or not value["pokemon_id"]:
        raise ValueError("invalid_contact_reactive_status_owner")
    return deepcopy(dict(value))


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
