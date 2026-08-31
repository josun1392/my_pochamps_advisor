"""Strict detached post-contact damage authority for Rocky Helmet/Rough Skin/Iron Barbs."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-contact-reactive-damage-authority-v1"
OVERLAY_SCHEMA_VERSION = "detached-contact-reactive-attacker-hp-overlay-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_ABILITIES = {"rough-skin": 8, "iron-barbs": 8}
_ITEMS = {"rocky-helmet": 6}


def contact_reactive_damage_relevance(*, runtime_snapshot: Mapping[str, Any], defender: Mapping[str, Any]) -> dict[str, Any]:
    """Classify whether this defender can trigger the supported family."""
    modifiers = _current_modifier_authorities(runtime_snapshot, defender)
    if modifiers is None:
        return {"status": "incomplete", "reason": "contact_reactive_defender_item_or_ability_unknown"}
    return {
        "status": "resolved",
        "relevant": bool(_sources(modifiers)),
        "defender_modifier_authorities": deepcopy(modifiers),
    }


def freeze_runtime_d0_contact_reactive_damage_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any],
    defender: Mapping[str, Any],
    source_action: Mapping[str, Any],
    contact_authority: Mapping[str, Any] | None,
    source_hit: Mapping[str, Any],
    attacker_hp_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve only immediate post-damaging-hit contact reactive damage."""
    base = _base(strategy_d0, attacker, defender, source_action)
    if base is None:
        return _result("rejected", "invalid_contact_reactive_damage_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    contact = _contact(contact_authority, base)
    if contact == "mismatch":
        return _result("rejected", "contact_reactive_contact_authority_binding_mismatch", base)
    if not isinstance(contact_authority, Mapping) or contact_authority.get("status") != "resolved":
        return _result("incomplete", contact_authority.get("reason", "contact_reactive_contact_authority_unavailable") if isinstance(contact_authority, Mapping) else "contact_reactive_contact_authority_missing", base)
    hit = _source_hit(source_hit, base)
    if isinstance(hit, str):
        return _result("rejected", hit, base)
    if contact_authority.get("contact_state") == "non_contact":
        return _not_applicable(base, contact_authority, hit, "source_hit_known_non_contact")
    if contact_authority.get("contact_state") != "contact":
        return _result("rejected", "contact_reactive_contact_state_invalid", base)
    if hit["target_routing"] == "substitute":
        return _not_applicable(base, contact_authority, hit, "source_hit_contacted_substitute_not_holder")
    if hit["actual_damage"] <= 0:
        return _not_applicable(base, contact_authority, hit, "source_hit_no_damage")
    attacker_hp = _attacker_hp(attacker_hp_authority, strategy_d0, runtime_snapshot, base["attacker"])
    if attacker_hp.get("status") != "resolved":
        return _result(attacker_hp["status"], attacker_hp["reason"], base)
    if attacker_hp["fainted"]:
        return _not_applicable(base, contact_authority, hit, "attacker_already_fainted", attacker_hp=attacker_hp)
    modifiers = _current_modifier_authorities(runtime_snapshot, base["defender"])
    if modifiers is None:
        return _result("incomplete", "contact_reactive_defender_item_or_ability_unknown", base)
    attacker_modifier = _current_modifier_authorities(runtime_snapshot, base["attacker"])
    if attacker_modifier is None:
        return _result("incomplete", "contact_reactive_attacker_ability_unknown", base)
    if attacker_modifier["ability_authority"].get("value") == "magic-guard":
        return _result("unsupported", "contact_reactive_magic_guard_prevention_unsupported", base)
    sources = _sources(modifiers)
    if not sources:
        return {
            "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
            "outcome": "no_reactive_source", "ordered_sources": (),
            "contact_authority": deepcopy(dict(contact_authority)), "source_hit": hit,
            "attacker_hp_authority": attacker_hp,
            "defender_modifier_authorities": modifiers,
            "attacker_modifier_authorities": attacker_modifier,
            "provenance": "runtime_d0_contact_reactive_damage_no_source_v1",
        }
    events = []
    current = attacker_hp["current_hp"]
    for order_index, source in enumerate(sources, 1):
        damage = attacker_hp["maximum_hp"] // source["denominator"]
        post = max(0, current - damage)
        events.append({
            "order_index": order_index, "source_kind": source["source_kind"],
            "source_owner": deepcopy(dict(base["defender"])),
            "damage_fraction": {"numerator": 1, "denominator": source["denominator"]},
            "rounding": "floor", "attacker_max_hp": attacker_hp["maximum_hp"],
            "pre_hp": current, "reactive_damage": damage,
            "post_hp": post, "fainted": post == 0,
        })
        current = post
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "outcome": "applies", "ordered_sources": tuple(events),
        "pre_hp": attacker_hp["current_hp"], "max_hp": attacker_hp["maximum_hp"],
        "post_hp": current, "fainted": current == 0,
        "contact_authority": deepcopy(dict(contact_authority)), "source_hit": hit,
        "attacker_hp_authority": attacker_hp,
        "defender_modifier_authorities": modifiers,
        "attacker_modifier_authorities": attacker_modifier,
        "provenance": "runtime_d0_canonical_contact_reactive_damage_family_v1",
    }


def materialize_detached_contact_reactive_damage(*, authority: Mapping[str, Any]) -> dict[str, Any]:
    """Project the exact attacker HP overlay from an already-frozen authority."""
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION:
        return {"status": "rejected", "reason": "invalid_contact_reactive_damage_authority"}
    if authority.get("status") != "resolved":
        return {"status": authority.get("status", "rejected"), "reason": authority.get("reason", "contact_reactive_damage_unavailable")}
    if authority.get("outcome") != "applies":
        hp = authority.get("attacker_hp_authority")
        if not isinstance(hp, Mapping) or not _hp_values(hp.get("current_hp"), hp.get("maximum_hp"), hp.get("fainted")):
            return {"status": "rejected", "reason": "contact_reactive_no_effect_hp_authority_invalid"}
        return {
            "status": "resolved", "schema_version": OVERLAY_SCHEMA_VERSION,
            "owner": deepcopy(dict(authority["attacker"])),
            "outcome": authority["outcome"], "ordered_sources": (),
            "hypothetical_hp_authority": {"status": "known", "current_hp": hp["current_hp"], "maximum_hp": hp["maximum_hp"]},
            "hypothetical_fainted_authority": {"status": "known", "value": hp["fainted"]},
            "source_authority": deepcopy(dict(authority)),
            "provenance": "detached_contact_reactive_damage_no_effect_overlay_v1",
        }
    if not all(isinstance(authority.get(key), int) and not isinstance(authority[key], bool) and authority[key] >= 0 for key in ("pre_hp", "max_hp", "post_hp")):
        return {"status": "rejected", "reason": "contact_reactive_damage_result_invalid"}
    ordered = authority.get("ordered_sources")
    if not isinstance(ordered, tuple) or not ordered:
        return {"status": "rejected", "reason": "contact_reactive_damage_sources_missing"}
    current = authority["pre_hp"]
    for index, row in enumerate(ordered, 1):
        if not isinstance(row, Mapping) or row.get("order_index") != index or row.get("source_kind") not in {"rough-skin", "iron-barbs", "rocky-helmet"}:
            return {"status": "rejected", "reason": "contact_reactive_damage_source_invalid"}
        fraction = row.get("damage_fraction")
        if not isinstance(fraction, Mapping) or fraction.get("numerator") != 1 or fraction.get("denominator") not in {6, 8}:
            return {"status": "rejected", "reason": "contact_reactive_damage_fraction_invalid"}
        damage, post = row.get("reactive_damage"), row.get("post_hp")
        if not isinstance(damage, int) or isinstance(damage, bool) or damage < 0 or post != max(0, current - damage) or row.get("pre_hp") != current or row.get("fainted") is not (post == 0):
            return {"status": "rejected", "reason": "contact_reactive_damage_hp_transition_invalid"}
        current = post
    if current != authority["post_hp"] or authority.get("fainted") is not (current == 0):
        return {"status": "rejected", "reason": "contact_reactive_damage_final_hp_invalid"}
    return {
        "status": "resolved", "schema_version": OVERLAY_SCHEMA_VERSION,
        "owner": deepcopy(dict(authority["attacker"])),
        "outcome": "applies", "ordered_sources": deepcopy(tuple(ordered)),
        "hypothetical_hp_authority": {"status": "known", "current_hp": current, "maximum_hp": authority["max_hp"]},
        "hypothetical_fainted_authority": {"status": "known", "value": current == 0},
        "source_authority": deepcopy(dict(authority)),
        "provenance": "detached_contact_reactive_damage_attacker_hp_overlay_v1",
    }


def apply_contact_reactive_damage_to_consequences(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any],
    defender: Mapping[str, Any],
    source_action: Mapping[str, Any],
    contact_authority: Mapping[str, Any] | None,
    source_hit: Mapping[str, Any],
    consequences: Mapping[str, Any],
) -> dict[str, Any]:
    """Return copied consequences with attacker HP updated by contact reaction."""
    if not isinstance(consequences, Mapping):
        return {"status": "rejected", "reason": "contact_reactive_consequences_invalid"}
    own = consequences.get("own_final_hp")
    maximum = _runtime_max_hp(runtime_snapshot, attacker)
    if not isinstance(own, int) or isinstance(own, bool) or maximum is None:
        return {"status": "incomplete", "reason": "contact_reactive_attacker_hp_unknown"}
    authority = freeze_runtime_d0_contact_reactive_damage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=attacker, defender=defender,
        source_action=source_action, contact_authority=contact_authority, source_hit=source_hit,
        attacker_hp_authority={"status": "resolved", "current_hp": own, "maximum_hp": maximum, "fainted": own == 0, "provenance": "detached_post_hit_attacker_hp_v1"},
    )
    if authority.get("status") != "resolved":
        return authority
    if authority.get("outcome") != "applies":
        updated = deepcopy(dict(consequences))
        updated["contact_reactive_damage"] = {
            "outcome": authority["outcome"],
            "ordered_sources": (),
            "source_hit": deepcopy(dict(source_hit)),
            "authority": deepcopy(dict(authority)),
        }
        return {"status": "resolved", "consequences": updated, "authority": authority, "overlay": None}
    overlay = materialize_detached_contact_reactive_damage(authority=authority)
    if overlay.get("status") != "resolved":
        return overlay
    updated = deepcopy(dict(consequences))
    hp = overlay["hypothetical_hp_authority"]["current_hp"]
    updated["own_final_hp"] = hp
    updated["self_fainted"] = overlay["hypothetical_fainted_authority"]["value"]
    updated["contact_reactive_damage"] = {
        "outcome": authority["outcome"],
        "ordered_sources": deepcopy(authority.get("ordered_sources", ())),
        "source_hit": deepcopy(dict(source_hit)),
        "authority": deepcopy(dict(authority)),
        "overlay": overlay,
    }
    return {"status": "resolved", "consequences": updated, "authority": authority, "overlay": overlay}


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
        return "contact_reactive_source_hit_missing"
    action_id, move_id = value.get("source_action_id"), value.get("source_move_id")
    actual = value.get("actual_damage")
    target_routing = value.get("target_routing", "target")
    if action_id != base["source_action_id"] or move_id != base["source_move_id"]:
        return "contact_reactive_source_hit_binding_mismatch"
    if target_routing not in {"target", "substitute"}:
        return "contact_reactive_source_hit_routing_invalid"
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        return "contact_reactive_source_hit_damage_invalid"
    return deepcopy(dict(value))


def _attacker_hp(value: Any, d0: Mapping[str, Any], snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    maximum = _runtime_max_hp(snapshot, owner)
    if maximum is None:
        return {"status": "incomplete", "reason": "contact_reactive_attacker_max_hp_unknown"}
    if value is None:
        active = d0.get("strategy_state", {}).get("active", {})
        row = active.get(owner["side"]) if isinstance(active, Mapping) else None
        current = row.get("current_hp") if isinstance(row, Mapping) else None
        fainted = row.get("fainted") if isinstance(row, Mapping) else None
        if not _hp_values(current, maximum, fainted):
            return {"status": "incomplete", "reason": "contact_reactive_attacker_hp_unknown"}
        return {"status": "resolved", "current_hp": current, "maximum_hp": maximum, "fainted": fainted, "provenance": "runtime_strategy_d0_v1"}
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or not _hp_values(value.get("current_hp"), value.get("maximum_hp"), value.get("fainted")) or value.get("maximum_hp") != maximum:
        return {"status": "rejected", "reason": "contact_reactive_attacker_hp_authority_invalid"}
    return deepcopy(dict(value))


def _runtime_max_hp(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> int | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(row, Mapping) or row.get("pokemon_id") != owner.get("pokemon_id"):
        return None
    maximum = row.get("max_hp")
    return maximum if isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 else None


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


def _sources(modifiers: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    sources: list[dict[str, Any]] = []
    ability = modifiers["ability_authority"].get("value")
    if ability in _ABILITIES:
        sources.append({"source_kind": ability, "denominator": _ABILITIES[ability]})
    item = modifiers["item_authority"].get("value")
    if item in _ITEMS:
        sources.append({"source_kind": item, "denominator": _ITEMS[item]})
    return tuple(sources)


def _not_applicable(base: Mapping[str, Any], contact: Mapping[str, Any], hit: Mapping[str, Any], reason: str, *, attacker_hp: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "ordered_sources": (), "reason": reason, "contact_authority": deepcopy(dict(contact)), "source_hit": deepcopy(dict(hit)), **({"attacker_hp_authority": deepcopy(dict(attacker_hp))} if attacker_hp else {}), "provenance": "runtime_d0_contact_reactive_damage_not_applicable_v1"}


def _hp_values(current: Any, maximum: Any, fainted: Any) -> bool:
    return isinstance(current, int) and not isinstance(current, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 and 0 <= current <= maximum and fainted is (current == 0)


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _owner(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_OWNER_KEYS) or not isinstance(value.get("session_id"), str) or not value["session_id"] or value.get("side") not in {"self", "opponent"} or not isinstance(value.get("slot_index"), int) or isinstance(value["slot_index"], bool) or value["slot_index"] < 0 or not isinstance(value.get("pokemon_id"), str) or not value["pokemon_id"]:
        raise ValueError("invalid_contact_reactive_owner")
    return deepcopy(dict(value))


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
