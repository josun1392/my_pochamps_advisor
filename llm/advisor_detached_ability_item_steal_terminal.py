"""Production binding shared by completed single-hit and graph action owners."""
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_detached_completed_action_terminal_effect_adapter import (
    attach_detached_completed_action_terminal_effect, bind_native_terminal_source,
)
from llm.advisor_runtime_d0_ability_item_steal_completion_authority import (
    freeze_runtime_d0_ability_item_steal_completion_from_runtime_branch,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness, _native_item_authority
from llm.advisor_runtime_d0_life_orb_immediate_authority import _sheer_force_applicability
from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata


def pickpocket_sheer_force(snapshot, actor, target, leaf):
    def ability(owner):
        return snapshot.get("state", {}).get(f"{owner.get('side')}_side", {}).get("pokemon", {}).get(owner.get("slot_index"), {}).get("current_ability")
    attacker, defender = ability(actor), ability(target)
    base = {"action_id": leaf["candidate_id"], "move_id": leaf["provenance"]["move_id"]}
    if not isinstance(attacker, str) or not isinstance(defender, str):
        return {"status": "incomplete", **base, "reason": "pickpocket_attacker_ability_unknown"}
    canonical = _sheer_force_applicability({"move_id": base["move_id"]})
    return {"status": canonical["status"], **base, "prevents_trigger": attacker == "sheer-force" and defender != "neutralizing-gas" and canonical.get("boosted") is True,
            "attacker_ability": attacker, "defender_ability": defender, "canonical_applicability": canonical,
            "provenance": "canonical_sheer_force_to_pickpocket_terminal_v1"}


def attach_ability_item_steal(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], leaf: Mapping[str, Any], intermediate: Mapping[str, Any], family: str, graph=None, terminal_edge=None):
    """Invoke only after the owner has materialized an exact terminal state."""
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return {"status": "rejected", "reason": "ability_steal_stale_runtime"}, deepcopy(dict(leaf))
    intermediate = deepcopy(dict(intermediate))
    for active in intermediate.get("active", {}).values():
        item = active.get("hypothetical_item", {})
        if item.get("reason") == "current_item_authority_unknown":
            owner = active["owner"]
            raw = runtime_snapshot.get("state", {}).get(f"{owner['side']}_side", {}).get("pokemon", {}).get(owner["slot_index"], {})
            active["hypothetical_item"] = _native_item_authority(raw.get("known_item"), raw.get("known_item_provenance"))
    row = deepcopy(dict(leaf))
    actor, target = leaf["provenance"]["attacker"], leaf["provenance"]["target"]
    if "contact" not in row["consequences"]:
        contact = canonical_move_contact_metadata(leaf["provenance"]["move_id"])
        if contact.get("status") == "resolved":
            row["consequences"]["contact"] = ("successful_contact_eligible" if contact["contact_state"] == "contact" else "successful_non_contact") if leaf.get("hit_state") == "hit" else "not_applicable"
    leaf = row
    native = terminal_edge if terminal_edge is not None else {
        "terminal": True, "edge_id": leaf["leaf_id"],
        "terminal_reason": leaf["consequences"].get("terminal_reason", "exact_terminal_leaf"),
    }
    source = bind_native_terminal_source(family=family, terminal_edge=native, action_id=leaf["candidate_id"], move_id=leaf["provenance"]["move_id"], actor=actor, target=target)
    if source.get("status") != "resolved":
        return source, row
    for direction, holder, donor in (("magician_attacker_hit", actor, target), ("pickpocket_defender_contact", target, actor)):
        raw = runtime_snapshot.get("state", {}).get(f"{holder.get('side')}_side", {}).get("pokemon", {}).get(holder.get("slot_index"), {})
        if raw.get("current_ability") != direction.split("_")[0]:
            continue
        sheer = pickpocket_sheer_force(runtime_snapshot, actor, target, leaf) if direction.startswith("pickpocket") else None
        effect = freeze_runtime_d0_ability_item_steal_completion_from_runtime_branch(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, trigger_direction=direction,
            ability_holder=holder, donor=donor, intermediate_state=intermediate,
            source_terminal_leaf=leaf, sheer_force=sheer, graph=graph, terminal_edge=terminal_edge,
        )
        if graph is None and isinstance(effect.get("completion"), dict):
            effect["completion"]["terminal_reason"] = source["terminal_reason"]
        if effect.get("status") != "resolved":
            return effect, row
        attached = attach_detached_completed_action_terminal_effect(terminal_source=source, detached_state=intermediate, effect_kind="ability_item_steal", effect_authority=effect, sheer_force=sheer)
        if attached.get("status") != "resolved":
            return attached, row
        if attached.get("result") == "applied":
            attached["source_leaf"] = deepcopy(dict(leaf))
            row["consequences"]["ability_item_steal"] = deepcopy(effect)
            row["provenance"]["ability_item_steal_completion_authority"] = deepcopy(effect)
            row["provenance"]["ability_item_steal_terminal_effect"] = attached
            return {"status": "resolved"}, row
    return {"status": "resolved"}, row
