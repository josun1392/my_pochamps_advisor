"""Strict immediate Life Orb damage-modifier and post-move recoil authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.item_modifiers import M_LIFE_ORB
from advisor.damage.move_categories import has_secondary_effect
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-life-orb-immediate-authority-v1"
OVERLAY_SCHEMA_VERSION = "detached-life-orb-attacker-hp-overlay-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_life_orb_immediate_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any],
    target: Mapping[str, Any],
    source_action: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
    qualifying_damage: bool,
    attacker_hp_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve Life Orb boost/recoil for one completed immediate action path."""
    base = _base(strategy_d0, attacker, target, source_action, move_metadata)
    if base is None:
        return _result("rejected", "invalid_life_orb_immediate_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    if not isinstance(qualifying_damage, bool):
        return _result("rejected", "life_orb_qualifying_damage_invalid", base)
    hp = _attacker_hp(attacker_hp_authority, strategy_d0, runtime_snapshot, base["attacker"])
    if hp.get("status") != "resolved":
        return _result(hp["status"], hp["reason"], base)
    modifiers = _current_modifier_authorities(runtime_snapshot, base["attacker"])
    if modifiers is None:
        return _result("incomplete", "life_orb_current_item_or_ability_unknown", base)
    target_modifiers = _current_modifier_authorities(runtime_snapshot, base["target"])
    if target_modifiers is None:
        return _result("incomplete", "life_orb_target_ability_unknown", base)
    item = modifiers["item_authority"].get("value")
    formula_applicable = _ordinary_formula_applicable(move_metadata)
    damage_modifier = {
        "applies": item == "life-orb" and formula_applicable,
        "modifier_q12": M_LIFE_ORB if item == "life-orb" and formula_applicable else 4096,
        "fraction": {"numerator": M_LIFE_ORB if item == "life-orb" and formula_applicable else 4096, "denominator": 4096},
        "damage_formula_applicable": formula_applicable,
        "provenance": "canonical_life_orb_final_damage_modifier_q12_v1",
    }
    if item != "life-orb":
        return {
            "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
            "outcome": "known_no_effect", "damage_modifier": damage_modifier,
            "recoil": _recoil_record("known_non_life_orb", hp, 0, hp["current_hp"], suppressed_by=None, eligible=False),
            "attacker_modifier_authorities": modifiers, "target_modifier_authorities": target_modifiers,
            "provenance": "runtime_d0_life_orb_known_no_effect_v1",
        }
    if hp["fainted"]:
        return _resolved(base, hp, modifiers, target_modifiers, damage_modifier, "fainted_before_recoil", 0, hp["current_hp"], suppressed_by=None, eligible=False)
    target_neutralizing_gas = target_modifiers["ability_authority"].get("value") == "neutralizing-gas"
    ability = modifiers["ability_authority"].get("value")
    if ability == "magic-guard" and not target_neutralizing_gas:
        return _resolved(base, hp, modifiers, target_modifiers, damage_modifier, "recoil_suppressed", 0, hp["current_hp"], suppressed_by="magic-guard", eligible=qualifying_damage)
    if ability == "sheer-force" and not target_neutralizing_gas:
        sheer = _sheer_force_applicability(move_metadata)
        if sheer.get("status") != "resolved":
            return _result(sheer.get("status", "incomplete"), sheer.get("reason", "life_orb_sheer_force_applicability_unknown"), base)
        if sheer["boosted"] is True:
            result = _resolved(base, hp, modifiers, target_modifiers, damage_modifier, "recoil_suppressed", 0, hp["current_hp"], suppressed_by="sheer-force", eligible=qualifying_damage)
            result["sheer_force_applicability_authority"] = sheer
            return result
    if not qualifying_damage:
        return _resolved(base, hp, modifiers, target_modifiers, damage_modifier, "not_triggered", 0, hp["current_hp"], suppressed_by=None, eligible=False)
    recoil = max(1, hp["maximum_hp"] // 10)
    return _resolved(base, hp, modifiers, target_modifiers, damage_modifier, "recoiled", recoil, max(0, hp["current_hp"] - recoil), suppressed_by=None, eligible=True)


def materialize_detached_life_orb_recoil(*, authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION:
        return {"status": "rejected", "reason": "invalid_life_orb_immediate_authority"}
    if authority.get("status") != "resolved":
        return {"status": authority.get("status", "rejected"), "reason": authority.get("reason", "life_orb_immediate_authority_unavailable")}
    recoil = authority.get("recoil")
    if not _valid_recoil_record(recoil, authority.get("attacker_hp_authority")):
        return {"status": "rejected", "reason": "life_orb_recoil_record_invalid"}
    return {
        "status": "resolved", "schema_version": OVERLAY_SCHEMA_VERSION,
        "owner": deepcopy(dict(authority["attacker"])),
        "outcome": authority["outcome"], "recoil": deepcopy(dict(recoil)),
        "hypothetical_hp_authority": {"status": "known", "current_hp": recoil["post_hp"], "maximum_hp": recoil["max_hp"]},
        "hypothetical_fainted_authority": {"status": "known", "value": recoil["post_hp"] == 0},
        "source_authority": deepcopy(dict(authority)),
        "provenance": "detached_life_orb_attacker_hp_overlay_v1",
    }


def apply_life_orb_recoil_to_consequences(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any],
    target: Mapping[str, Any],
    source_action: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
    qualifying_damage: bool,
    consequences: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(consequences, Mapping):
        return {"status": "rejected", "reason": "life_orb_consequences_invalid"}
    relevance = _life_orb_item_relevance(runtime_snapshot, attacker)
    if relevance.get("status") != "resolved":
        return relevance
    if relevance.get("relevant") is False:
        return {"status": "resolved", "consequences": deepcopy(dict(consequences)), "authority": None, "overlay": None}
    own = consequences.get("own_final_hp")
    maximum = _runtime_max_hp(runtime_snapshot, attacker)
    if not isinstance(own, int) or isinstance(own, bool) or maximum is None:
        return {"status": "incomplete", "reason": "life_orb_attacker_hp_unknown"}
    authority = freeze_runtime_d0_life_orb_immediate_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=attacker, target=target,
        source_action=source_action, move_metadata=move_metadata, qualifying_damage=qualifying_damage,
        attacker_hp_authority={"status": "resolved", "current_hp": own, "maximum_hp": maximum, "fainted": own == 0, "provenance": "detached_post_move_attacker_hp_v1"},
    )
    if authority.get("status") != "resolved":
        return authority
    overlay = materialize_detached_life_orb_recoil(authority=authority)
    if overlay.get("status") != "resolved":
        return overlay
    updated = deepcopy(dict(consequences))
    updated["own_final_hp"] = overlay["hypothetical_hp_authority"]["current_hp"]
    updated["self_fainted"] = overlay["hypothetical_fainted_authority"]["value"]
    updated["life_orb"] = {"outcome": authority["outcome"], "authority": deepcopy(dict(authority)), "overlay": overlay}
    return {"status": "resolved", "consequences": updated, "authority": authority, "overlay": overlay}


def _life_orb_item_relevance(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != owner.get("pokemon_id"):
        return {"status": "incomplete", "reason": "life_orb_current_item_unknown"}
    item, provenance = pokemon.get("known_item"), pokemon.get("known_item_provenance")
    if isinstance(item, str) and item == "life-orb" and _trusted(provenance, "current_item_observed"):
        return {"status": "resolved", "relevant": True}
    return {"status": "resolved", "relevant": False}


def _resolved(base, hp, modifiers, target_modifiers, damage_modifier, outcome, recoil, post, *, suppressed_by, eligible):
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "outcome": outcome, "damage_modifier": damage_modifier,
        "recoil": _recoil_record(outcome, hp, recoil, post, suppressed_by=suppressed_by, eligible=eligible),
        "attacker_hp_authority": hp,
        "attacker_modifier_authorities": modifiers, "target_modifier_authorities": target_modifiers,
        "provenance": "runtime_d0_canonical_life_orb_immediate_damage_and_recoil_v1",
    }


def _recoil_record(outcome, hp, recoil, post, *, suppressed_by, eligible):
    return {
        "eligible": eligible, "outcome": outcome,
        "damage_fraction": {"numerator": 1, "denominator": 10},
        "rounding": "floor_minimum_one_when_applicable",
        "pre_hp": hp["current_hp"], "max_hp": hp["maximum_hp"],
        "recoil_damage": recoil, "post_hp": post,
        "fainted": post == 0, "suppressed_by": suppressed_by,
    }


def _base(d0, attacker, target, action, move):
    try:
        attacker_owner, target_owner = _owner(attacker), _owner(target)
    except ValueError:
        return None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or attacker_owner["side"] == target_owner["side"] or not isinstance(action, Mapping) or not isinstance(move, Mapping):
        return None
    if not isinstance(action.get("action_id"), str) or not action["action_id"] or action.get("identity") != move.get("move_id"):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(attacker_owner["side"]) != attacker_owner or active.get(target_owner["side"]) != target_owner:
        return None
    return {
        "session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")),
        "attacker": attacker_owner, "target": target_owner,
        "source_action_id": action["action_id"], "source_move_id": move["move_id"],
    }


def _ordinary_formula_applicable(move: Mapping[str, Any]) -> bool:
    return move.get("category") in {"physical", "special"} and isinstance(move.get("power"), int) and not isinstance(move.get("power"), bool) and move["power"] > 0


def _sheer_force_applicability(move: Mapping[str, Any]) -> dict[str, Any]:
    move_id = move.get("move_id")
    if not isinstance(move_id, str) or not move_id:
        return {"status": "rejected", "reason": "life_orb_sheer_force_move_identity_invalid"}
    return {"status": "resolved", "move_id": move_id, "boosted": has_secondary_effect(move_id), "provenance": "canonical_move_flags_sheer_force_applicability_v1"}


def _attacker_hp(value: Any, d0: Mapping[str, Any], snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    maximum = _runtime_max_hp(snapshot, owner)
    if maximum is None:
        return {"status": "incomplete", "reason": "life_orb_attacker_max_hp_unknown"}
    if value is None:
        row = d0.get("strategy_state", {}).get("active", {}).get(owner["side"]) if isinstance(d0.get("strategy_state", {}).get("active"), Mapping) else None
        current = row.get("current_hp") if isinstance(row, Mapping) else None
        fainted = row.get("fainted") if isinstance(row, Mapping) else None
        if not _hp_values(current, maximum, fainted):
            return {"status": "incomplete", "reason": "life_orb_attacker_hp_unknown"}
        return {"status": "resolved", "current_hp": current, "maximum_hp": maximum, "fainted": fainted, "provenance": "runtime_strategy_d0_v1"}
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or not _hp_values(value.get("current_hp"), value.get("maximum_hp"), value.get("fainted")) or value.get("maximum_hp") != maximum:
        return {"status": "rejected", "reason": "life_orb_attacker_hp_authority_invalid"}
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


def _valid_recoil_record(value: Any, hp: Any) -> bool:
    return (
        isinstance(value, Mapping) and isinstance(hp, Mapping)
        and value.get("pre_hp") == hp.get("current_hp")
        and value.get("max_hp") == hp.get("maximum_hp")
        and isinstance(value.get("recoil_damage"), int) and not isinstance(value.get("recoil_damage"), bool)
        and value["recoil_damage"] >= 0
        and value.get("post_hp") == max(0, value["pre_hp"] - value["recoil_damage"])
        and value.get("fainted") is (value["post_hp"] == 0)
    )


def _hp_values(current: Any, maximum: Any, fainted: Any) -> bool:
    return isinstance(current, int) and not isinstance(current, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 and 0 <= current <= maximum and fainted is (current == 0)


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _owner(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_OWNER_KEYS) or not isinstance(value.get("session_id"), str) or not value["session_id"] or value.get("side") not in {"self", "opponent"} or not isinstance(value.get("slot_index"), int) or isinstance(value["slot_index"], bool) or value["slot_index"] < 0 or not isinstance(value.get("pokemon_id"), str) or not value["pokemon_id"]:
        raise ValueError("invalid_life_orb_owner")
    return deepcopy(dict(value))


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
