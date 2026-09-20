"""Detached, next-decision held-item applicability authority.

This is intentionally a small authority boundary.  It authenticates the
identity of an item before a later executor may hand it to the damage engine;
it does not calculate damage or consume items.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from core.champions_item_repository import normalize_item_id
from llm.advisor_next_turn_predictive_mechanics_authority import validate_next_turn_predictive_mechanics_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state

SCHEMA_VERSION = "detached-next-turn-held-item-effect-applicability-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_detached_next_turn_held_item_effect_applicability(*, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, predictive_mechanics: Mapping[str, Any], holder: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(next_decision_state, next_decision_fingerprint, predictive_mechanics, holder)
    if isinstance(base, str): return _result("rejected", base, {})
    row, other = base["row"], base["other_row"]
    item = _fact(row.get("item"), "item")
    common = {k: deepcopy(v) for k, v in base.items() if k not in {"row", "other_row"}}
    common["raw_item"] = item
    if item["status"] == "unknown": return _result("incomplete", "held_item_effect_current_item_unknown", common)
    if item["status"] == "known_absent": return _resolved(common, "known_no_item", False, None, "current_held_item_known_absent")
    magic = _magic_room(next_decision_state)
    common["magic_room_authority"] = magic
    if magic["status"] != "resolved": return _result("incomplete", "held_item_suppression_field_authority_unknown", common)
    if magic["state"] == "active": return _resolved(common, "suppressed", False, None, "magic_room_item_effects_suppressed")
    ability = _fact(row.get("ability"), "ability")
    common["holder_ability"] = ability
    if ability["status"] != "known": return _result("incomplete", "held_item_effect_holder_ability_unknown", common)
    if ability["value"] != "klutz": return _resolved(common, "active", True, item["value"], "magic_room_inactive_holder_not_klutz")
    opposing = _fact(other.get("ability"), "ability")
    common["opposing_active_ability"] = opposing
    if opposing["status"] != "known": return _result("incomplete", "held_item_effect_klutz_suppression_unknown", common)
    if opposing["value"] == "neutralizing-gas": return _resolved(common, "active", True, item["value"], "klutz_suppressed_by_neutralizing_gas")
    return _resolved(common, "suppressed", False, None, "klutz_item_effects_suppressed")


def validate_detached_next_turn_held_item_effect_applicability(*, authority: Any, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, predictive_mechanics: Mapping[str, Any], holder: Mapping[str, Any]) -> str | None:
    expected = materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=next_decision_state, next_decision_fingerprint=next_decision_fingerprint, predictive_mechanics=predictive_mechanics, holder=holder)
    if expected.get("status") == "rejected": return expected.get("reason")
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "detached_held_item_effect_applicability_mismatch"


def _base(state: Any, fingerprint: Any, predictive: Any, holder: Any) -> dict[str, Any] | str:
    if not isinstance(state, Mapping) or not isinstance(fingerprint, str) or fingerprint_transition_preview_state(state) != fingerprint: return "stale_or_invalid_next_decision_fingerprint"
    if not _owner(holder): return "held_item_effect_holder_identity_invalid"
    if validate_next_turn_predictive_mechanics_authority(authority=predictive, next_decision_state=state, next_decision_fingerprint=fingerprint) is not None: return "next_turn_predictive_mechanics_authority_invalid"
    active, rows = state.get("active"), predictive.get("sides") if isinstance(predictive, Mapping) else None
    other_side = "opponent" if holder["side"] == "self" else "self"
    if not isinstance(active, Mapping) or active.get(holder["side"]) is None or active.get(holder["side"], {}).get("pokemon_id") != holder["pokemon_id"] or predictive.get("active_owners", {}).get(holder["side"]) != dict(holder): return "held_item_effect_holder_identity_mismatch"
    other_owner = predictive.get("active_owners", {}).get(other_side)
    if not _owner(other_owner) or not isinstance(rows, Mapping) or rows.get(holder["side"], {}).get("owner") != dict(holder) or rows.get(other_side, {}).get("owner") != other_owner: return "held_item_effect_predictive_owner_mismatch"
    return {"session_id": holder["session_id"], "source_next_decision_fingerprint": fingerprint, "holder": deepcopy(dict(holder)), "opposing_holder": deepcopy(dict(other_owner)), "predictive_mechanics_authority": deepcopy(dict(predictive)), "row": rows[holder["side"]], "other_row": rows[other_side]}


def _magic_room(state: Mapping[str, Any]) -> dict[str, Any]:
    candidates = [state.get("field"), state.get("current_state", {}).get("field_state_context", {}).get("current_field")]
    for field in candidates:
        if not isinstance(field, Mapping): continue
        value, provenance = field.get("magic_room_status", field.get("magic_room")), field.get("magic_room_status_provenance", field.get("magic_room_provenance"))
        if value in {"active", "inactive"} and isinstance(provenance, Mapping) and provenance.get("event_kind") == "magic_room_field_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_observation_id"), str) and provenance["source_observation_id"] and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance["source_sequence"], bool) and provenance["source_sequence"] >= 1:
            return {"status": "resolved", "state": value, "source_field_provenance": deepcopy(dict(provenance))}
    return {"status": "unknown", "state": "unknown"}


def _fact(value: Any, kind: str) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("value"), str) and value["value"]:
        return {"status": "known", "value": normalize_item_id(value["value"]) if kind == "item" else value["value"]}
    if kind == "item" and isinstance(value, Mapping) and value.get("status") == "known_absent": return {"status": "known_absent", "value": None}
    return {"status": "unknown", "value": None}

def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])

def _resolved(base: Mapping[str, Any], outcome: str, active: bool, effective: str | None, reason: str) -> dict[str, Any]:
    terminal = "required_unrepresented" if active and _is_resist_berry(effective) else "not_required"
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome, "item_effects_active": active, "effective_item_id": effective, "terminal_consumption": terminal, "reason": reason, "provenance": "detached_next_turn_held_item_effect_applicability_v1"}

def _is_resist_berry(item: str | None) -> bool:
    return item in {"babiri-berry", "charti-berry", "chilan-berry", "chople-berry", "coba-berry", "colbur-berry", "haban-berry", "kasib-berry", "kebia-berry", "occa-berry", "passho-berry", "payapa-berry", "rindo-berry", "roseli-berry", "shuca-berry", "tanga-berry", "wacan-berry", "yache-berry"}

def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
