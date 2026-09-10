"""Bind current and same-hit Healing Prevented facts at an item check."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "detached-current-healing-prevented-at-item-check-authority-v1"
CURRENT_SCHEMA_VERSION = "runtime-d0-current-healing-prevented-authority-v1"
PSYCHIC_NOISE_TRANSITION_SCHEMA_VERSION = "detached-psychic-noise-healing-prevented-transition-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_BINDING_KEYS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")


def materialize_detached_current_healing_prevented_at_item_check_authority(
    *, strategy_d0: Mapping[str, Any], terminal_leaf: Mapping[str, Any],
    recipient: Mapping[str, Any], current_healing_prevented_authority: Mapping[str, Any],
    root_predictive_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve Healing Prevented at one post-hit held-item check.

    The caller must supply a current-state authority.  A successful Psychic
    Noise leaf may replace that state only through its typed exact transition;
    an omitted transition is deliberately incomplete rather than inferred.
    """
    base = _base(strategy_d0, recipient)
    if base is None:
        return _result("rejected", "invalid_healing_prevented_item_check_request", {})
    leaf = _leaf_binding(terminal_leaf, strategy_d0, recipient, root_predictive_authority)
    if isinstance(leaf, str):
        return _result("rejected", leaf, base)
    current = _current_binding(current_healing_prevented_authority, base, recipient)
    if isinstance(current, str):
        return _result("incomplete" if current.endswith("_unknown") else "rejected", current, {**base, **leaf})
    transition = _same_hit_transition(terminal_leaf, leaf, recipient)
    if isinstance(transition, str):
        return _result("incomplete" if transition.endswith("_unavailable") else "rejected", transition, {**base, **leaf})
    effective = "known_present" if isinstance(transition, Mapping) else current["state"]
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        **base, **leaf, "recipient": deepcopy(dict(recipient)),
        "state": effective,
        "current_healing_prevented_authority": deepcopy(dict(current_healing_prevented_authority)),
        "same_hit_transition": deepcopy(dict(transition)) if isinstance(transition, Mapping) else None,
        "provenance": "exact_current_or_same_hit_healing_prevented_at_item_check_v1",
    }


def _base(d0: Any, recipient: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(recipient):
        return None
    if d0.get("active_owners", {}).get(recipient["side"]) != dict(recipient):
        return None
    values = {key: d0.get("strategy_preview_fingerprint") if key == "source_branch_fingerprint" else d0.get(key) for key in _BINDING_KEYS}
    if not all(values.values()):
        return None
    return deepcopy(values)


def _leaf_binding(leaf: Any, d0: Mapping[str, Any], recipient: Mapping[str, Any], root: Mapping[str, Any] | None) -> dict[str, Any] | str:
    if not isinstance(leaf, Mapping) or leaf.get("action_type") != "attack" or not isinstance(leaf.get("consequences"), Mapping):
        return "healing_prevented_terminal_leaf_invalid"
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping) or not _owner(provenance.get("attacker")) or provenance.get("target") != dict(recipient) or not isinstance(provenance.get("move_id"), str):
        return "healing_prevented_terminal_leaf_identity_invalid"
    original = {key: d0.get("strategy_preview_fingerprint") if key == "source_branch_fingerprint" else d0.get(key) for key in _BINDING_KEYS}
    if root is None:
        if any(provenance.get(key) != value for key, value in original.items()):
            return "healing_prevented_terminal_leaf_binding_mismatch"
    else:
        if not isinstance(root, Mapping) or root.get("status") != "resolved" or root.get("schema_version") != "detached-actor-neutral-root-predictive-authority-v1" or root.get("hypothetical") is not True or any(root.get(key) != value for key, value in original.items()):
            return "healing_prevented_actor_neutral_root_binding_mismatch"
        predictive = root.get("predictive_strategy_d0")
        root_actor, root_target = root.get("root_actor"), root.get("root_target")
        if not isinstance(predictive, Mapping) or predictive.get("status") != "resolved" or root_target != dict(recipient) or provenance.get("attacker") != root_actor or any(provenance.get(key) != (predictive.get("strategy_preview_fingerprint") if key == "source_branch_fingerprint" else predictive.get(key)) for key in _BINDING_KEYS):
            return "healing_prevented_actor_neutral_root_predictive_binding_mismatch"
    return {key: deepcopy(provenance[key]) for key in _BINDING_KEYS} | {"source_move_id": provenance["move_id"], "source_attacker": deepcopy(dict(provenance["attacker"]))}


def _current_binding(value: Any, base: Mapping[str, Any], recipient: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("schema_version") != CURRENT_SCHEMA_VERSION:
        return "current_healing_prevented_authority_invalid"
    if any(value.get(key) != base.get(key) for key in _BINDING_KEYS) or value.get("recipient") != dict(recipient):
        return "current_healing_prevented_authority_binding_mismatch"
    if value.get("status") == "incomplete" and value.get("state") == "unknown":
        return "current_healing_prevented_unknown"
    if value.get("status") != "resolved" or value.get("state") not in {"known_present", "known_absent"}:
        return "current_healing_prevented_authority_invalid"
    return value


def _same_hit_transition(leaf: Mapping[str, Any], binding: Mapping[str, Any], recipient: Mapping[str, Any]) -> Mapping[str, Any] | str | None:
    transition = leaf["consequences"].get("healing_prevented_transition")
    if binding["source_move_id"] != "psychic-noise":
        return None if transition is None else "healing_prevented_unexpected_same_hit_transition"
    if not isinstance(transition, Mapping):
        return "psychic_noise_healing_prevented_transition_unavailable"
    required = {"status", "schema_version", "outcome", "recipient", "state_after", *_BINDING_KEYS}
    if not required.issubset(set(transition)) or transition.get("status") != "resolved" or transition.get("schema_version") != PSYCHIC_NOISE_TRANSITION_SCHEMA_VERSION or transition.get("outcome") != "applied" or transition.get("recipient") != dict(recipient) or transition.get("state_after") != "known_present":
        return "psychic_noise_healing_prevented_transition_invalid"
    if any(transition.get(key) != binding.get(key) for key in _BINDING_KEYS):
        return "psychic_noise_healing_prevented_transition_binding_mismatch"
    return transition


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
