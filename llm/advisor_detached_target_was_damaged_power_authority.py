"""Pair-local Assurance power authority from exact prior target HP-loss evidence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_target_was_damaged_power_family import resolve_canonical_target_was_damaged_power_move


SCHEMA_VERSION = "detached-target-was-damaged-power-authority-v1"
_SELF_DAMAGE_KINDS = frozenset({"damage_based_recoil", "life_orb_recoil", "contact_reactive_damage"})


def materialize_detached_target_was_damaged_power_authority(*, strategy_d0: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], target: Mapping[str, Any], source_terminal_leaf: Mapping[str, Any] | None = None, execution_order_provenance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    canonical = resolve_canonical_target_was_damaged_power_move(move=move)
    if canonical.get("status") != "resolved": return _bad(canonical.get("status", "rejected"), canonical.get("reason", "catalog_unavailable"))
    bindings = _bindings(strategy_d0, move, user, target)
    if isinstance(bindings, str): return _bad("rejected", bindings)
    if source_terminal_leaf is None:
        return _resolved(canonical, bindings, None, execution_order_provenance)
    event = _qualifying_event(source_terminal_leaf, target)
    if isinstance(event, str): return _bad("rejected", event)
    return _resolved(canonical, bindings, event, execution_order_provenance)


def _bindings(d0: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | str:
    if not all(isinstance(value, Mapping) for value in (d0, move, user, target)): return "target_was_damaged_power_request_invalid"
    if not all(isinstance(d0.get(key), str) and d0.get(key) for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return "target_was_damaged_power_d0_provenance_missing"
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(user.get("side")) != user or active.get(target.get("side")) != target or user == target: return "target_was_damaged_power_active_identity_mismatch"
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "user": deepcopy(dict(user)), "target": deepcopy(dict(target)), "move_id": move.get("move_id")}


def _qualifying_event(leaf: Mapping[str, Any], assurance_target: Mapping[str, Any]) -> dict[str, Any] | None | str:
    if not isinstance(leaf, Mapping) or leaf.get("action_type") != "attack" or not isinstance(leaf.get("leaf_id"), str): return "target_was_damaged_power_source_leaf_invalid"
    provenance, consequences = leaf.get("provenance"), leaf.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping): return "target_was_damaged_power_source_leaf_provenance_invalid"
    # Direct damage is eligible only when this exact leaf targeted Assurance's
    # current target and proves underlying-Pokémon (not Substitute) HP loss.
    if provenance.get("target") == assurance_target:
        hit = consequences.get("source_hit_context")
        if isinstance(hit, Mapping) and hit.get("target_routing") == "target":
            pre, post = hit.get("target_pre_hp"), hit.get("target_post_hp")
            if isinstance(pre, int) and isinstance(post, int) and pre >= post and pre - post > 0:
                return _event(leaf, assurance_target, "direct_attack_damage", pre - post, {"source_hit": deepcopy(dict(hit))})
            if not all(isinstance(value, int) for value in (pre, post)) or pre < post: return "target_was_damaged_power_direct_hp_loss_unproven"
    # When the Assurance target was the preceding attacker, only explicitly
    # modeled self/indirect HP-loss records count.  Do not infer loss from a
    # final-HP delta, which could conflate healing and unknown mutations.
    if provenance.get("attacker") != assurance_target: return None
    recoil = consequences.get("damage_based_recoil")
    if isinstance(recoil, Mapping) and _positive_transition(recoil, "attacker_pre_hp", "attacker_post_hp", "recoil_damage"):
        return _event(leaf, assurance_target, "damage_based_recoil", recoil["recoil_damage"], {"recoil": deepcopy(dict(recoil))})
    life = consequences.get("life_orb")
    authority = life.get("authority") if isinstance(life, Mapping) else None
    life_recoil = authority.get("recoil") if isinstance(authority, Mapping) else None
    if isinstance(life_recoil, Mapping) and _positive_transition(life_recoil, "pre_hp", "post_hp", "recoil_damage"):
        return _event(leaf, assurance_target, "life_orb_recoil", life_recoil["recoil_damage"], {"life_orb": deepcopy(dict(life))})
    contact = consequences.get("contact_reactive_damage")
    if isinstance(contact, Mapping) and contact.get("outcome") == "applies":
        rows = contact.get("ordered_sources")
        if not isinstance(rows, (tuple, list)): return "target_was_damaged_power_contact_source_invalid"
        for row in rows:
            if not isinstance(row, Mapping) or row.get("source_kind") not in {"rough-skin", "iron-barbs", "rocky-helmet"}: return "target_was_damaged_power_contact_source_invalid"
            if _positive_transition(row, "pre_hp", "post_hp", "reactive_damage"):
                return _event(leaf, assurance_target, "contact_reactive_damage", row["reactive_damage"], {"contact_source": deepcopy(dict(row))})
    return None


def _positive_transition(row: Mapping[str, Any], pre_key: str, post_key: str, loss_key: str) -> bool:
    pre, post, loss = row.get(pre_key), row.get(post_key), row.get(loss_key)
    return all(isinstance(value, int) and not isinstance(value, bool) for value in (pre, post, loss)) and pre > post >= 0 and loss == pre - post and loss > 0


def _event(leaf: Mapping[str, Any], target: Mapping[str, Any], kind: str, loss: int, evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {"pair_branch_source_leaf_id": leaf["leaf_id"], "target": deepcopy(dict(target)), "source_kind": kind, "actual_hp_loss": loss, "event_order": "before_assurance_execution", **deepcopy(dict(evidence))}


def _resolved(canonical: Mapping[str, Any], bindings: Mapping[str, Any], event: Mapping[str, Any] | None, order: Mapping[str, Any] | None) -> dict[str, Any]:
    effect = canonical["effect"]; condition = isinstance(event, Mapping)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(bindings)), "trigger_family": "target_was_damaged_this_turn", "canonical_base_power": effect["power"], "target_was_damaged_before_execution": condition, "selected_base_power": effect["boosted_power"] if condition else effect["power"], "qualifying_damage_event": deepcopy(dict(event)) if condition else None, "execution_order_provenance": deepcopy(dict(order)) if isinstance(order, Mapping) else None, "qualifying_source_kind_policy": tuple(sorted(_SELF_DAMAGE_KINDS | {"direct_attack_damage"})), "rule": deepcopy(dict(effect)), "provenance": "exact_d0_pair_branch_target_was_damaged_before_execution_v1"}


def _bad(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
