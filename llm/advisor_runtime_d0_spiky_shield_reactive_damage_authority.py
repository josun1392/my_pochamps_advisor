"""Strict detached Spiky Shield blocked-contact HP consequence authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_spiky_shield_reactive_damage import (
    canonical_spiky_shield_reactive_damage_metadata,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-spiky-shield-reactive-damage-authority-v1"
_BLOCK_SCHEMA = "spiky-shield-successful-block-context-v1"
_APPLICABILITY_SCHEMA = "spiky-shield-reactive-damage-applicability-resolution-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def build_spiky_shield_successful_block_context(
    *, session_id: str, shield_owner: Mapping[str, Any], shield_action_id: str,
    blocked_attacker: Mapping[str, Any], blocked_action_id: str, blocked_move_id: str,
    protection_authority: Mapping[str, Any], action_blocked: bool,
    protection_bypass: bool, substitute_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Build explicit protection/non-bypass evidence; it does not resolve either."""
    shield, attacker = _owner(shield_owner), _owner(blocked_attacker)
    if (
        not isinstance(session_id, str) or not session_id or shield["side"] == attacker["side"]
        or not isinstance(shield_action_id, str) or not shield_action_id
        or not isinstance(blocked_action_id, str) or not blocked_action_id
        or not isinstance(blocked_move_id, str) or not blocked_move_id
        or not isinstance(action_blocked, bool) or not isinstance(protection_bypass, bool)
        or not _protection_authority(protection_authority, shield)
        or not _substitute_authority(substitute_authority)
    ):
        raise ValueError("invalid_spiky_shield_successful_block_context")
    return {
        "schema_version": _BLOCK_SCHEMA, "session_id": session_id,
        "shield_owner": shield, "shield_action_id": shield_action_id,
        "shield_move_id": "spiky-shield", "blocked_attacker": attacker,
        "blocked_action_id": blocked_action_id, "blocked_move_id": blocked_move_id,
        "protection_authority": deepcopy(dict(protection_authority)),
        "action_blocked": action_blocked, "protection_bypass": protection_bypass,
        "substitute_authority": deepcopy(dict(substitute_authority)),
        "provenance": "explicit_existing_protection_block_context_v1",
    }


def build_spiky_shield_reactive_damage_applicability_resolution(
    *, session_id: str, shield_owner: Mapping[str, Any], blocked_attacker: Mapping[str, Any],
    blocked_action_id: str, blocked_move_id: str, outcome: str,
    ability_authority: Mapping[str, Any], item_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Build trusted exact applicability evidence without guessing modifier mechanics."""
    shield, attacker = _owner(shield_owner), _owner(blocked_attacker)
    if (
        not isinstance(session_id, str) or not session_id or shield["side"] == attacker["side"]
        or not isinstance(blocked_action_id, str) or not blocked_action_id
        or not isinstance(blocked_move_id, str) or not blocked_move_id
        or outcome not in {"applies", "prevented"}
        or not _modifier_authority(ability_authority) or not _modifier_authority(item_authority)
    ):
        raise ValueError("invalid_spiky_shield_reactive_damage_applicability_resolution")
    return {
        "schema_version": _APPLICABILITY_SCHEMA, "session_id": session_id,
        "shield_owner": shield, "blocked_attacker": attacker,
        "blocked_action_id": blocked_action_id, "blocked_move_id": blocked_move_id,
        "outcome": outcome, "ability_authority": deepcopy(dict(ability_authority)),
        "item_authority": deepcopy(dict(item_authority)),
        "provenance": "explicit_canonical_spiky_shield_damage_applicability_v1",
    }


def freeze_runtime_d0_spiky_shield_reactive_damage_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    shield_owner: Mapping[str, Any], shield_action_id: str,
    blocked_attacker: Mapping[str, Any], blocked_action: Mapping[str, Any],
    contact_authority: Mapping[str, Any] | None,
    protection_block_context: Mapping[str, Any] | None,
    applicability_resolution: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Freeze a current exact Spiky Shield HP consequence, never a hit result."""
    base = _base(strategy_d0, shield_owner, shield_action_id, blocked_attacker, blocked_action)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_spiky_shield_damage_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    context = _block_context(protection_block_context, base)
    if context is None:
        return _result("rejected", "spiky_shield_protection_block_context_binding_mismatch", base)
    if context["substitute_authority"].get("status") != "known_absent":
        return _result("incomplete", "spiky_shield_substitute_or_routing_authority_unresolved", base)
    contact = _contact(contact_authority, base)
    if contact == "mismatch":
        return _result("rejected", "spiky_shield_contact_authority_binding_mismatch", base)
    if not isinstance(contact_authority, Mapping) or contact_authority.get("status") != "resolved":
        return _result("incomplete", contact_authority.get("reason", "spiky_shield_contact_authority_unavailable") if isinstance(contact_authority, Mapping) else "spiky_shield_contact_authority_missing", base)
    if not context["action_blocked"] or context["protection_bypass"]:
        return _not_applicable(base, context, contact_authority, "protection_failed_or_bypassed")
    if contact_authority.get("contact_state") == "non_contact":
        return _not_applicable(base, context, contact_authority, "blocked_action_known_non_contact")
    if contact_authority.get("contact_state") != "contact":
        return _result("rejected", "spiky_shield_contact_state_invalid", base)
    hp = _runtime_hp_authority(strategy_d0, runtime_snapshot, base["blocked_attacker"])
    if hp.get("status") != "resolved":
        return _result(hp["status"], hp["reason"], base)
    if hp["fainted"]:
        return _not_applicable(base, context, contact_authority, "blocked_attacker_already_fainted", hp=hp)
    applicability = _applicability(applicability_resolution, base)
    if applicability == "mismatch":
        return _result("rejected", "spiky_shield_damage_applicability_binding_mismatch", base)
    if not isinstance(applicability, Mapping):
        return _result("incomplete", "spiky_shield_reactive_damage_applicability_missing", base)
    if applicability["ability_authority"].get("status") == "unknown" or applicability["item_authority"].get("status") == "unknown":
        return _result("incomplete", "spiky_shield_relevant_modifier_authority_unknown", base)
    current = _current_modifier_authorities(runtime_snapshot, base["blocked_attacker"])
    if current is None:
        return _result("incomplete", "spiky_shield_relevant_modifier_authority_unknown", base)
    if current != {"ability_authority": applicability["ability_authority"], "item_authority": applicability["item_authority"]}:
        return _result("rejected", "spiky_shield_relevant_modifier_authority_binding_mismatch", base)
    if applicability["outcome"] == "prevented":
        return _not_applicable(base, context, contact_authority, "reactive_damage_prevented", hp=hp, applicability=applicability)
    damage = max(1, hp["maximum_hp"] // 8)
    post_hp = max(0, hp["current_hp"] - damage)
    metadata = canonical_spiky_shield_reactive_damage_metadata("spiky-shield")
    if metadata is None:
        return _result("rejected", "canonical_spiky_shield_damage_metadata_invalid", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "outcome": "applies", "rule_id": "spiky_shield_blocked_contact_max_hp_eighth_floor_minimum_one",
        "pre_hp": hp["current_hp"], "max_hp": hp["maximum_hp"],
        "damage_fraction": {"numerator": 1, "denominator": 8}, "rounding": "floor",
        "minimum_damage": 1, "reactive_damage": damage, "post_hp": post_hp,
        "fainted": post_hp == 0, "contact_authority": deepcopy(dict(contact_authority)),
        "protection_block_context": context, "hp_authority": hp,
        "applicability_resolution": applicability, "canonical_metadata": metadata,
        "provenance": "runtime_d0_canonical_spiky_shield_blocked_contact_damage_v1",
    }


def materialize_detached_spiky_shield_reactive_damage(*, authority: Mapping[str, Any]) -> dict[str, Any]:
    """Project only the authority's exact HP/faint overlay; never mutate runtime."""
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION:
        return {"status": "rejected", "reason": "invalid_spiky_shield_reactive_damage_authority"}
    if authority.get("status") != "resolved":
        return {"status": authority.get("status", "rejected"), "reason": authority.get("reason", "spiky_shield_damage_unavailable")}
    if authority.get("outcome") != "applies" or not all(isinstance(authority.get(key), int) and not isinstance(authority[key], bool) and authority[key] >= 0 for key in ("pre_hp", "max_hp", "reactive_damage", "post_hp")):
        return {"status": "rejected", "reason": "spiky_shield_reactive_damage_result_invalid"}
    if authority["post_hp"] != max(0, authority["pre_hp"] - authority["reactive_damage"]) or authority.get("fainted") is not (authority["post_hp"] == 0):
        return {"status": "rejected", "reason": "spiky_shield_reactive_damage_hp_transition_invalid"}
    return {
        "status": "resolved", "owner": deepcopy(dict(authority["blocked_attacker"])),
        "hypothetical_hp_authority": {"status": "known", "current_hp": authority["post_hp"], "maximum_hp": authority["max_hp"]},
        "hypothetical_fainted_authority": {"status": "known", "value": authority["fainted"]},
        "source_authority": deepcopy(dict(authority)),
        "provenance": "detached_spiky_shield_reactive_damage_hp_overlay_v1",
    }


def _base(d0: Any, shield: Any, shield_action_id: Any, attacker: Any, action: Any) -> dict[str, Any] | None:
    try:
        shield_owner, blocked_attacker = _owner(shield), _owner(attacker)
    except ValueError:
        return None
    if (
        not isinstance(d0, Mapping) or d0.get("status") != "resolved" or shield_owner["side"] == blocked_attacker["side"]
        or not isinstance(shield_action_id, str) or not shield_action_id or not isinstance(action, Mapping)
        or not isinstance(action.get("action_id"), str) or not action["action_id"]
        or not isinstance(action.get("identity"), str) or not action["identity"]
    ):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(shield_owner["side"]) != shield_owner or active.get(blocked_attacker["side"]) != blocked_attacker:
        return None
    return {
        "session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")),
        "shield_owner": shield_owner, "shield_action_id": shield_action_id, "shield_move_id": "spiky-shield",
        "blocked_attacker": blocked_attacker, "blocked_action_id": action["action_id"], "blocked_move_id": action["identity"],
    }


def _block_context(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        expected = build_spiky_shield_successful_block_context(
            session_id=base["session_id"], shield_owner=base["shield_owner"], shield_action_id=base["shield_action_id"],
            blocked_attacker=base["blocked_attacker"], blocked_action_id=base["blocked_action_id"], blocked_move_id=base["blocked_move_id"],
            protection_authority=value.get("protection_authority"), action_blocked=value.get("action_blocked"),
            protection_bypass=value.get("protection_bypass"), substitute_authority=value.get("substitute_authority"),
        )
    except (TypeError, ValueError):
        return None
    return expected if value == expected else None


def _contact(value: Any, base: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping):
        return None
    expected = {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"], "action_id": base["blocked_action_id"], "move_id": base["blocked_move_id"], "attacker": base["blocked_attacker"], "target": base["shield_owner"]}
    return None if all(value.get(key) == item for key, item in expected.items()) else "mismatch"


def _applicability(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str | None:
    if not isinstance(value, Mapping):
        return None
    try:
        expected = build_spiky_shield_reactive_damage_applicability_resolution(
            session_id=base["session_id"], shield_owner=base["shield_owner"], blocked_attacker=base["blocked_attacker"],
            blocked_action_id=base["blocked_action_id"], blocked_move_id=base["blocked_move_id"], outcome=value.get("outcome"),
            ability_authority=value.get("ability_authority"), item_authority=value.get("item_authority"),
        )
    except (TypeError, ValueError):
        return "mismatch"
    return expected if value == expected else "mismatch"


def _runtime_hp_authority(d0: Mapping[str, Any], snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(row, Mapping) or row.get("pokemon_id") != owner["pokemon_id"]:
        return {"status": "rejected", "reason": "spiky_shield_blocked_attacker_runtime_identity_mismatch"}
    hp, maximum, fainted = row.get("current_hp"), row.get("max_hp"), row.get("fainted")
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool):
        return {"status": "incomplete", "reason": "spiky_shield_blocked_attacker_hp_unknown"}
    if maximum < 1 or hp < 0 or hp > maximum or fainted is not (hp == 0):
        return {"status": "rejected", "reason": "spiky_shield_blocked_attacker_hp_invalid"}
    return {"status": "resolved", "current_hp": hp, "maximum_hp": maximum, "fainted": fainted, "provenance": "runtime_battle_state_v1"}


def _current_modifier_authorities(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != owner.get("pokemon_id"):
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


def _not_applicable(base: Mapping[str, Any], context: Mapping[str, Any], contact: Mapping[str, Any], reason: str, *, hp: Mapping[str, Any] | None = None, applicability: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "reactive_damage": None, "reason": reason, "contact_authority": deepcopy(dict(contact)), "protection_block_context": deepcopy(dict(context)), **({"hp_authority": deepcopy(dict(hp))} if hp else {}), **({"applicability_resolution": deepcopy(dict(applicability))} if applicability else {}), "provenance": "runtime_d0_canonical_spiky_shield_no_reactive_damage_v1"}


def _protection_authority(value: Any, shield: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "resolved" and value.get("owner") == shield and isinstance(value.get("metadata"), Mapping) and value["metadata"].get("move_id") == "spiky-shield"


def _substitute_authority(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") in {"known_absent", "unknown"} and set(value).issuperset({"status"})


def _modifier_authority(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "known_absent", "unknown"}:
        return False
    return (value["status"] == "known" and set(value) == {"status", "value"} and isinstance(value.get("value"), str) and bool(value["value"])) or (value["status"] != "known" and set(value) == {"status"})


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _owner(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_OWNER_KEYS) or not isinstance(value.get("session_id"), str) or not value["session_id"] or value.get("side") not in {"self", "opponent"} or not isinstance(value.get("slot_index"), int) or isinstance(value["slot_index"], bool) or value["slot_index"] < 0 or not isinstance(value.get("pokemon_id"), str) or not value["pokemon_id"]:
        raise ValueError("invalid_spiky_shield_owner")
    return deepcopy(dict(value))


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
