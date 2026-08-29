"""Freeze an exact blocked-attacker Silk Trap Speed interaction result.

The current ability/item records identify prerequisites only.  This boundary
therefore requires a separately explicit, identity-bound interaction result;
it never guesses Clear Body, Contrary, or any item behaviour from a name.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_stage_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-silk-trap-speed-drop-interaction-authority-v1"
RESOLUTION_SCHEMA_VERSION = "silk-trap-speed-drop-interaction-resolution-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def build_silk_trap_speed_drop_interaction_resolution(
    *, session_id: str, shield_owner: Mapping[str, Any], blocked_attacker: Mapping[str, Any],
    blocked_action_id: str, blocked_move_id: str, outcome: str,
    resulting_delta: int | None, ability_authority: Mapping[str, Any],
    item_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Build trusted exact outcome evidence; this is not a mechanics resolver.

    ``resulting_delta`` is explicit for a reversal so this module never assumes
    that reversing a -1 stage request necessarily produces +1.
    """
    shield, attacker = _owner(shield_owner), _owner(blocked_attacker)
    if (
        not isinstance(session_id, str) or not session_id or shield["side"] == attacker["side"]
        or not isinstance(blocked_action_id, str) or not blocked_action_id
        or not isinstance(blocked_move_id, str) or not blocked_move_id
        or outcome not in {"applies", "prevented", "reversed"}
        or not _modifier_authority(ability_authority) or not _modifier_authority(item_authority)
    ):
        raise ValueError("invalid_silk_trap_speed_drop_interaction_resolution")
    if outcome == "applies" and resulting_delta != -1:
        raise ValueError("invalid_silk_trap_applies_delta")
    if outcome == "prevented" and resulting_delta != 0:
        raise ValueError("invalid_silk_trap_prevented_delta")
    if outcome == "reversed" and (
        not isinstance(resulting_delta, int) or isinstance(resulting_delta, bool)
        or not -12 <= resulting_delta <= 12 or resulting_delta == -1
    ):
        raise ValueError("invalid_silk_trap_reversed_delta")
    return {
        "schema_version": RESOLUTION_SCHEMA_VERSION,
        "session_id": session_id, "shield_owner": shield,
        "blocked_attacker": attacker, "blocked_action_id": blocked_action_id,
        "blocked_move_id": blocked_move_id, "outcome": outcome,
        "resulting_delta": resulting_delta,
        "ability_authority": deepcopy(dict(ability_authority)),
        "item_authority": deepcopy(dict(item_authority)),
        "provenance": "explicit_canonical_silk_trap_stage_interaction_result_v1",
    }


def build_kings_shield_attack_drop_interaction_resolution(**kwargs: Any) -> dict[str, Any]:
    """Use the same explicit-result schema, tagged for King's Shield Attack."""
    result = build_silk_trap_speed_drop_interaction_resolution(**kwargs)
    result["shield_move_id"] = "kings-shield"
    result["stage_stat"] = "attack"
    return result


def freeze_runtime_d0_silk_trap_speed_drop_interaction_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    shield_owner: Mapping[str, Any], blocked_attacker: Mapping[str, Any],
    blocked_action: Mapping[str, Any], contact_authority: Mapping[str, Any],
    protection_authority: Mapping[str, Any], interaction_resolution: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Freeze one current, exact Silk Trap outcome for a blocked contact action."""
    base = _base(strategy_d0, shield_owner, blocked_attacker, blocked_action)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_silk_trap_interaction_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    if not _contact_matches(contact_authority, base):
        return _result("rejected", "silk_trap_contact_authority_binding_mismatch", base)
    if contact_authority.get("status") != "resolved":
        return _result("incomplete", contact_authority.get("reason", "silk_trap_contact_authority_unavailable"), base)
    if contact_authority.get("contact_state") == "non_contact":
        return _result("incomplete", "silk_trap_reactive_consequence_not_applicable_to_non_contact", base)
    if contact_authority.get("contact_state") != "contact":
        return _result("rejected", "silk_trap_contact_state_invalid", base)
    if not _protection_matches(protection_authority, base):
        return _result("rejected", "silk_trap_protection_context_binding_mismatch", base)
    if protection_authority.get("status") != "resolved":
        return _result("incomplete", protection_authority.get("reason", "silk_trap_protection_unavailable"), base)
    stage = freeze_runtime_current_stage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=blocked_attacker,
    )
    if stage.get("status") == "rejected":
        return _result("rejected", stage.get("reason", "silk_trap_speed_stage_authority_rejected"), base)
    speed = stage.get("stages", {}).get("speed") if isinstance(stage, Mapping) else None
    if not isinstance(speed, Mapping) or speed.get("status") != "known":
        return _result("incomplete", "silk_trap_blocked_attacker_speed_stage_unknown", base)
    before = speed.get("value")
    if not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _result("rejected", "silk_trap_blocked_attacker_speed_stage_invalid", base)
    if interaction_resolution is None:
        return _result("incomplete", "silk_trap_speed_drop_interaction_result_missing", base)
    resolution = _resolution(interaction_resolution, base)
    if resolution is None:
        return _result("rejected", "silk_trap_speed_drop_interaction_result_binding_mismatch", base)
    if resolution["ability_authority"].get("status") == "unknown" or resolution["item_authority"].get("status") == "unknown":
        return _result("incomplete", "silk_trap_relevant_modifier_authority_unknown", base)
    current_modifiers = _current_modifier_authorities(runtime_snapshot, blocked_attacker)
    if current_modifiers is None:
        return _result("incomplete", "silk_trap_relevant_modifier_authority_unknown", base)
    if (
        resolution["ability_authority"] != current_modifiers["ability_authority"]
        or resolution["item_authority"] != current_modifiers["item_authority"]
    ):
        return _result("rejected", "silk_trap_relevant_modifier_authority_binding_mismatch", base)
    after = max(-6, min(6, before + resolution["resulting_delta"]))
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "outcome": resolution["outcome"], "requested_delta": -1,
        "resulting_delta": resolution["resulting_delta"],
        "speed_stage_before": before, "speed_stage_after": after,
        "contact_authority": deepcopy(dict(contact_authority)),
        "protection_authority": deepcopy(dict(protection_authority)),
        "stage_authority": deepcopy(dict(stage)),
        "ability_authority": deepcopy(resolution["ability_authority"]),
        "item_authority": deepcopy(resolution["item_authority"]),
        "interaction_resolution": deepcopy(resolution),
        "provenance": "runtime_d0_explicit_silk_trap_speed_drop_interaction_v1",
    }


def freeze_runtime_d0_kings_shield_attack_drop_interaction_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    shield_owner: Mapping[str, Any], blocked_attacker: Mapping[str, Any],
    blocked_action: Mapping[str, Any], contact_authority: Mapping[str, Any],
    protection_authority: Mapping[str, Any], interaction_resolution: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Strict King's Shield wrapper over the proven D0 interaction checks."""
    resolved = freeze_runtime_d0_silk_trap_speed_drop_interaction_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        shield_owner=shield_owner, blocked_attacker=blocked_attacker,
        blocked_action=blocked_action, contact_authority=contact_authority,
        protection_authority={**dict(protection_authority), "metadata": {"move_id": "silk-trap"}},
        interaction_resolution=_as_silk_resolution(interaction_resolution),
    )
    if resolved.get("status") != "resolved":
        return resolved
    stage = freeze_runtime_current_stage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=blocked_attacker,
    )
    attack = stage.get("stages", {}).get("attack") if isinstance(stage, Mapping) else None
    if not isinstance(attack, Mapping) or attack.get("status") != "known":
        return _result("incomplete", "kings_shield_blocked_attacker_attack_stage_unknown", _base(strategy_d0, shield_owner, blocked_attacker, blocked_action) or {})
    before = attack.get("value")
    if not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _result("rejected", "kings_shield_blocked_attacker_attack_stage_invalid", _base(strategy_d0, shield_owner, blocked_attacker, blocked_action) or {})
    delta = resolved["resulting_delta"]
    return {**resolved, "shield_move_id": "kings-shield", "stage_stat": "attack",
            "attack_stage_before": before, "attack_stage_after": max(-6, min(6, before + delta)),
            "stage_authority": deepcopy(dict(stage)),
            "provenance": "runtime_d0_explicit_kings_shield_attack_drop_interaction_v1"}


def _as_silk_resolution(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return value
    adapted = deepcopy(dict(value)); adapted.pop("shield_move_id", None); adapted.pop("stage_stat", None)
    return adapted


def _base(d0: Any, shield: Any, attacker: Any, action: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping):
        return None
    try:
        shield_owner, blocked_attacker = _owner(shield), _owner(attacker)
    except ValueError:
        return None
    active = d0.get("active_owners")
    if (
        not isinstance(active, Mapping) or active.get(shield_owner["side"]) != shield_owner
        or active.get(blocked_attacker["side"]) != blocked_attacker
        or shield_owner["side"] == blocked_attacker["side"]
        or not all(isinstance(d0.get(key), str) and d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint"))
        or not isinstance(action.get("action_id"), str) or not action["action_id"]
        or not isinstance(action.get("identity"), str) or not action["identity"]
    ):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0.get("decision_owner")),
        "shield_owner": shield_owner, "blocked_attacker": blocked_attacker,
        "blocked_action_id": action["action_id"], "blocked_move_id": action["identity"],
    }


def _contact_matches(value: Any, base: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and all(value.get(key) == expected for key, expected in {
        "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"],
        "action_id": base["blocked_action_id"], "move_id": base["blocked_move_id"],
        "attacker": base["blocked_attacker"], "target": base["shield_owner"],
    }.items())


def _protection_matches(value: Any, base: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("owner") == base["shield_owner"] and value.get("metadata", {}).get("move_id") == "silk-trap"


def _resolution(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        expected = build_silk_trap_speed_drop_interaction_resolution(
            session_id=base["session_id"], shield_owner=base["shield_owner"], blocked_attacker=base["blocked_attacker"],
            blocked_action_id=base["blocked_action_id"], blocked_move_id=base["blocked_move_id"],
            outcome=value.get("outcome"), resulting_delta=value.get("resulting_delta"),
            ability_authority=value.get("ability_authority"), item_authority=value.get("item_authority"),
        )
    except (TypeError, ValueError):
        return None
    return expected if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else None


def _modifier_authority(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "known_absent", "unknown"}:
        return False
    if value["status"] == "known":
        return set(value) == {"status", "value"} and isinstance(value.get("value"), str) and bool(value["value"])
    return set(value) == {"status"}


def _current_modifier_authorities(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != owner.get("pokemon_id"):
        return None
    ability, ability_provenance = pokemon.get("current_ability"), pokemon.get("current_ability_provenance")
    if not isinstance(ability, str) or not ability or not _trusted(ability_provenance, "current_ability_observed"):
        return None
    item, item_provenance = pokemon.get("known_item"), pokemon.get("known_item_provenance")
    if not _trusted(item_provenance, "current_item_observed"):
        return None
    if item is None and item_provenance.get("status") == "known_absent":
        item_authority = {"status": "known_absent"}
    elif isinstance(item, str) and item and item_provenance.get("status") == "known":
        item_authority = {"status": "known", "value": item}
    else:
        return None
    return {"ability_authority": {"status": "known", "value": ability}, "item_authority": item_authority}


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _owner(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_OWNER_KEYS) or not isinstance(value.get("session_id"), str) or not value["session_id"] or value.get("side") not in {"self", "opponent"} or not isinstance(value.get("slot_index"), int) or isinstance(value["slot_index"], bool) or value["slot_index"] < 0 or not isinstance(value.get("pokemon_id"), str) or not value["pokemon_id"]:
        raise ValueError("invalid_silk_trap_interaction_owner")
    return deepcopy(dict(value))


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
