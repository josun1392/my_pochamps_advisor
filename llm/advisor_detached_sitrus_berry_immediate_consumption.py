"""Exact single-hit Sitrus Berry consequence for one detached terminal leaf."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_detached_current_healing_prevented_at_item_check_authority import (
    materialize_detached_current_healing_prevented_at_item_check_authority,
)
from llm.advisor_runtime_d0_item_suppression_field_authority import (
    resolve_runtime_d0_item_suppression_field_authority,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_current_healing_prevented_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "detached-sitrus-berry-immediate-consumption-v1"
_BINDING_KEYS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SITRUS = "sitrus-berry"


def materialize_detached_sitrus_berry_immediate_consumption(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    terminal_leaf: Mapping[str, Any], holder: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach the one exact Sitrus consequence when this leaf proves it.

    The function never changes current D0/runtime state.  A non-Sitrus holder
    is intentionally a neutral result; an asserted but untrusted Sitrus
    holder is incomplete because it could change this branch's outcome.
    """
    base = _base(strategy_d0, holder)
    if base is None:
        return _result("rejected", "invalid_sitrus_detached_request", {}, terminal_leaf)
    # This post-hit owner is opt-in on an explicit current Sitrus identity.
    # Unrelated leaves must retain their existing pair behavior, including
    # test-only detached seams that deliberately do not carry a runtime view.
    raw = _pokemon(runtime_snapshot, holder)
    if raw is None or raw.get("known_item") != _SITRUS:
        return _result("resolved", "sitrus_not_currently_held", base, terminal_leaf, outcome="not_applicable")
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base, terminal_leaf)
    parsed_leaf = _leaf(terminal_leaf, base, holder)
    if isinstance(parsed_leaf, str):
        return _result("rejected", parsed_leaf, base, terminal_leaf)
    item = _item(raw)
    if item["status"] != "known" or item["value"] != _SITRUS:
        return _result("resolved", "sitrus_not_currently_held", base, terminal_leaf, outcome="not_applicable", item_before=item)
    if item["trusted"] is not True:
        return _result("incomplete", "sitrus_item_authority_untrusted", base, terminal_leaf, item_before=item)
    single = _single_hit(move_metadata)
    if isinstance(single, str):
        return _result("incomplete", single, base, terminal_leaf, item_before=item)
    post_hp = parsed_leaf["post_hit_hp"]
    if post_hp == 0:
        return _result("resolved", "sitrus_holder_fainted", base, terminal_leaf, outcome="not_triggered", item_before=item)
    maximum = raw.get("max_hp")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0 or post_hp > maximum:
        return _result("incomplete", "sitrus_max_hp_authority_unknown", base, terminal_leaf, item_before=item)
    threshold = maximum // 2
    if post_hp > threshold:
        return _result("resolved", "sitrus_threshold_not_reached", base, terminal_leaf, outcome="not_triggered", item_before=item,
                       post_hit_hp=post_hp, maximum_hp=maximum, trigger_threshold=threshold)
    if not parsed_leaf["successful_direct_damage"]:
        return _result("resolved", "sitrus_no_successful_direct_damage", base, terminal_leaf, outcome="not_triggered", item_before=item,
                       post_hit_hp=post_hp, maximum_hp=maximum, trigger_threshold=threshold)
    field = resolve_runtime_d0_item_suppression_field_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if field.get("status") != "resolved":
        return _result("incomplete", "sitrus_item_suppression_authority_unknown", base, terminal_leaf, item_before=item, item_suppression_field_authority=field)
    if field.get("state") == "active":
        return _result("resolved", "sitrus_magic_room_suppressed", base, terminal_leaf, outcome="suppressed", item_before=item,
                       item_suppression_field_authority=field, post_hit_hp=post_hp, maximum_hp=maximum, trigger_threshold=threshold)
    modifiers = _modifiers(strategy_d0, runtime_snapshot, holder, parsed_leaf["attacker"])
    if modifiers.get("status") != "resolved":
        return _result("incomplete", "sitrus_modifier_authority_unknown", base, terminal_leaf, item_before=item,
                       item_suppression_field_authority=field, modifier_authority=modifiers)
    if modifiers.get("blocked"):
        return _result("resolved", modifiers["reason"], base, terminal_leaf, outcome="suppressed", item_before=item,
                       item_suppression_field_authority=field, modifier_authority=modifiers,
                       post_hit_hp=post_hp, maximum_hp=maximum, trigger_threshold=threshold)
    current = freeze_runtime_d0_current_healing_prevented_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, recipient=holder,
    )
    item_check = materialize_detached_current_healing_prevented_at_item_check_authority(
        strategy_d0=strategy_d0, terminal_leaf=terminal_leaf, recipient=holder,
        current_healing_prevented_authority=current,
    )
    if item_check.get("status") != "resolved":
        return _result(_status(item_check), item_check.get("reason", "sitrus_healing_prevented_authority_unknown"), base, terminal_leaf,
                       item_before=item, item_suppression_field_authority=field, modifier_authority=modifiers,
                       healing_prevented_at_item_check=item_check)
    if item_check.get("state") == "known_present":
        return _result("resolved", "sitrus_healing_prevented", base, terminal_leaf, outcome="suppressed", item_before=item,
                       item_suppression_field_authority=field, modifier_authority=modifiers,
                       healing_prevented_at_item_check=item_check, post_hit_hp=post_hp, maximum_hp=maximum, trigger_threshold=threshold)
    if item_check.get("state") != "known_absent":
        return _result("incomplete", "sitrus_healing_prevented_authority_unknown", base, terminal_leaf, item_before=item,
                       healing_prevented_at_item_check=item_check)
    heal = maximum // 4
    final_hp = min(maximum, post_hp + heal)
    consequence = {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "outcome": "activated",
        **base, "holder": deepcopy(dict(holder)), "item_before": _SITRUS,
        "item_after": {"status": "known_absent", "value": None, "consumption_cause": "sitrus_berry"},
        "post_hit_hp": post_hp, "maximum_hp": maximum, "trigger_threshold": threshold,
        "heal_amount": heal, "final_hp": final_hp,
        "source_leaf_id": terminal_leaf["leaf_id"], "source_leaf_path": deepcopy(terminal_leaf.get("branch_path")),
        "source_attacker": deepcopy(dict(parsed_leaf["attacker"])),
        "healing_prevented_at_item_check": deepcopy(dict(item_check)),
        "item_suppression_field_authority": deepcopy(dict(field)),
        "modifier_authority": deepcopy(dict(modifiers)), "hypothetical": True,
        "provenance": "exact_single_hit_sitrus_berry_post_hit_consumption_v1",
    }
    updated = deepcopy(dict(terminal_leaf)); consequences = deepcopy(dict(updated["consequences"]))
    consequences["target_final_hp"] = final_hp
    consequences["target_ko"] = False
    consequences["sitrus_berry_immediate_consumption"] = consequence
    updated["consequences"] = consequences
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "outcome": "activated", **base,
            "leaf": updated, "sitrus_consequence": deepcopy(consequence), "provenance": consequence["provenance"]}


def _base(d0: Any, holder: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(holder) or d0.get("active_owners", {}).get(holder["side"]) != dict(holder):
        return None
    values = {key: d0.get("strategy_preview_fingerprint") if key == "source_branch_fingerprint" else d0.get(key) for key in _BINDING_KEYS}
    return deepcopy(values) if all(values.values()) else None


def _leaf(value: Any, base: Mapping[str, Any], holder: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("action_type") != "attack" or not isinstance(value.get("leaf_id"), str) or not isinstance(value.get("consequences"), Mapping):
        return "sitrus_terminal_leaf_invalid"
    provenance, consequences = value.get("provenance"), value["consequences"]
    if not isinstance(provenance, Mapping) or provenance.get("target") != dict(holder) or not _owner(provenance.get("attacker")):
        return "sitrus_terminal_leaf_identity_mismatch"
    if any(provenance.get(key) != base[key] for key in _BINDING_KEYS):
        return "sitrus_terminal_leaf_binding_mismatch"
    post_hp, damage = consequences.get("target_final_hp"), consequences.get("damage")
    if not isinstance(post_hp, int) or isinstance(post_hp, bool) or post_hp < 0:
        return "sitrus_terminal_leaf_post_hit_hp_unknown"
    direct = value.get("hit_state") == "hit" and isinstance(damage, int) and not isinstance(damage, bool) and damage > 0
    return {"post_hit_hp": post_hp, "successful_direct_damage": direct, "attacker": deepcopy(dict(provenance["attacker"]))}


def _pokemon(snapshot: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    raw = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return raw if isinstance(raw, Mapping) and raw.get("pokemon_id") == owner["pokemon_id"] else None


def _item(raw: Mapping[str, Any]) -> dict[str, Any]:
    value, provenance = raw.get("known_item"), raw.get("known_item_provenance")
    known = isinstance(value, str) and bool(value)
    trusted = known and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_item_observed" and provenance.get("trust") == "user_confirmed_observation"
    return {"status": "known" if known else "unknown", "value": value if known else None, "trusted": trusted,
            "runtime_item_provenance": deepcopy(dict(provenance)) if isinstance(provenance, Mapping) else None}


def _single_hit(metadata: Any) -> str | None:
    if not isinstance(metadata, Mapping): return "sitrus_move_metadata_unknown"
    low, high = metadata.get("min_hits"), metadata.get("max_hits")
    if low is None and high is None: return None
    if low == high == 1: return None
    return "sitrus_multi_hit_lifecycle_unsupported"


def _modifiers(d0: Mapping[str, Any], snapshot: Mapping[str, Any], holder: Mapping[str, Any], attacker: Mapping[str, Any]) -> dict[str, Any]:
    holder_raw, attacker_raw = _pokemon(snapshot, holder), _pokemon(snapshot, attacker)
    if holder_raw is None or attacker_raw is None: return {"status": "rejected", "reason": "sitrus_modifier_runtime_identity_mismatch"}
    def ability(raw: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
        value, provenance = raw.get("current_ability"), raw.get("current_ability_provenance")
        if not isinstance(value, str) or not value or not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_ability_observed" or provenance.get("trust") != "user_confirmed_observation":
            return {"status": "unknown", "owner": deepcopy(dict(owner))}
        return {"status": "known", "owner": deepcopy(dict(owner)), "value": value, "provenance": deepcopy(dict(provenance))}
    own, foe = ability(holder_raw, holder), ability(attacker_raw, attacker)
    if own["status"] != "known" or foe["status"] != "known": return {"status": "incomplete", "holder": own, "attacker": foe}
    gas = own["value"] == "neutralizing-gas" or foe["value"] == "neutralizing-gas"
    if gas: return {"status": "incomplete", "holder": own, "attacker": foe, "reason": "sitrus_neutralizing_gas_interaction_unsupported"}
    if own["value"] in {"ripen", "cheek-pouch", "cud-chew"}: return {"status": "incomplete", "holder": own, "attacker": foe, "reason": f"sitrus_{own['value']}_interaction_unsupported"}
    if own["value"] == "klutz": return {"status": "resolved", "holder": own, "attacker": foe, "blocked": True, "reason": "sitrus_klutz_suppressed"}
    if foe["value"] == "unnerve": return {"status": "resolved", "holder": own, "attacker": foe, "blocked": True, "reason": "sitrus_unnerve_suppressed"}
    return {"status": "resolved", "holder": own, "attacker": foe, "blocked": False, "reason": "sitrus_modifier_authority_safe"}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _status(value: Mapping[str, Any]) -> str:
    return "rejected" if value.get("status") == "rejected" else "incomplete"


def _result(status: str, reason: str, base: Mapping[str, Any], leaf: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason,
            "leaf": deepcopy(dict(leaf)) if isinstance(leaf, Mapping) else leaf, **deepcopy(extra)}
