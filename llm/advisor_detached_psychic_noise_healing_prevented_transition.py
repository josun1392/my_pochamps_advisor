"""Typed same-hit Psychic Noise consequence for one detached terminal leaf."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "detached-psychic-noise-healing-prevented-transition-v1"
_BINDING_KEYS = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_detached_psychic_noise_healing_prevented_transition(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], source_leaf: Mapping[str, Any],
) -> dict[str, Any]:
    """Project only a proven, surviving direct Psychic Noise hit.

    The leaf remains the sole success proof.  A candidate, selected action, or
    move ID has no effect here; misses, non-damaging routes, and KOs return a
    non-applying result and never fabricate an opposite current-state fact.
    """
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_psychic_noise_transition_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    leaf = _leaf(source_leaf, base, strategy_d0)
    if isinstance(leaf, str):
        return _result("rejected", leaf, base)
    if leaf["hit_state"] != "hit":
        return _result("not_applicable", "psychic_noise_hit_not_successful", {**base, **leaf})
    source = source_leaf["consequences"].get("source_hit_context")
    if not _direct_surviving_damage(source):
        return _result("not_applicable", "psychic_noise_effect_not_proven_applicable", {**base, **leaf})
    target_hp = source_leaf["consequences"].get("target_final_hp")
    if target_hp != source["target_post_hp"]:
        return _result("rejected", "psychic_noise_terminal_hp_source_mismatch", {**base, **leaf})
    if not _positive_int(target_hp):
        return _result("not_applicable", "psychic_noise_target_not_surviving", {**base, **leaf})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base, **leaf,
        "outcome": "applied", "recipient": deepcopy(leaf["recipient"]),
        "state_after": "known_present", "hypothetical": True,
        "source_hit": deepcopy(dict(source)),
        "provenance": "detached_successful_psychic_noise_same_hit_transition_v1",
    }


def attach_detached_psychic_noise_healing_prevented_transitions(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach successful transitions branch-locally without altering probability."""
    if not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable":
        return deepcopy(dict(ledger)) if isinstance(ledger, Mapping) else {"status": "rejected", "reason": "psychic_noise_ledger_invalid"}
    leaves = ledger.get("terminal_leaves")
    if not isinstance(leaves, tuple):
        return {"status": "rejected", "reason": "psychic_noise_terminal_leaves_invalid"}
    rows = []
    for leaf in leaves:
        transition = materialize_detached_psychic_noise_healing_prevented_transition(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, source_leaf=leaf,
        )
        if transition.get("status") == "resolved":
            row = deepcopy(dict(leaf))
            row["consequences"] = {**deepcopy(dict(row["consequences"])), "healing_prevented_transition": transition}
            rows.append(row)
        elif transition.get("status") == "not_applicable":
            rows.append(deepcopy(dict(leaf)))
        else:
            return {"status": transition.get("status", "rejected"), "reason": transition.get("reason", "psychic_noise_transition_unavailable")}
    return {**deepcopy(dict(ledger)), "terminal_leaves": tuple(rows), "component_manifest": {**deepcopy(dict(ledger.get("component_manifest", {}))), "psychic_noise_healing_prevented": {"status": "resolved"}}}


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(d0.get("active_owners"), Mapping):
        return None
    values = {key: d0.get("strategy_preview_fingerprint") if key == "source_branch_fingerprint" else d0.get(key) for key in _BINDING_KEYS}
    if not all(values.values()):
        return None
    if not _owner(d0["active_owners"].get("self")) or not _owner(d0["active_owners"].get("opponent")):
        return None
    return deepcopy(values)


def _leaf(value: Any, base: Mapping[str, Any], d0: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("action_type") != "attack" or not isinstance(value.get("leaf_id"), str) or not value["leaf_id"]:
        return "psychic_noise_terminal_leaf_invalid"
    if value.get("hit_state") not in {"hit", "miss", "missed", "not_applicable"} or not isinstance(value.get("consequences"), Mapping):
        return "psychic_noise_terminal_leaf_outcome_invalid"
    provenance = value.get("provenance")
    if not isinstance(provenance, Mapping) or any(provenance.get(key) != base.get(key) for key in _BINDING_KEYS):
        return "psychic_noise_terminal_leaf_binding_mismatch"
    attacker, recipient = provenance.get("attacker"), provenance.get("target")
    if not _owner(attacker) or not _owner(recipient) or attacker.get("side") == recipient.get("side"):
        return "psychic_noise_terminal_leaf_identity_invalid"
    if d0["active_owners"].get(attacker["side"]) != dict(attacker) or d0["active_owners"].get(recipient["side"]) != dict(recipient):
        return "psychic_noise_terminal_leaf_active_identity_mismatch"
    if provenance.get("move_id") != "psychic-noise":
        return "psychic_noise_move_binding_mismatch"
    return {"source_leaf_id": value["leaf_id"], "source_leaf_path": deepcopy(value.get("branch_path")), "recipient": deepcopy(dict(recipient)), "source_attacker": deepcopy(dict(attacker)), "source_move_id": "psychic-noise", "hit_state": value["hit_state"]}


def _direct_surviving_damage(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and value.get("target_routing") == "target"
        and all(_nonnegative_int(value.get(key)) for key in ("target_pre_hp", "target_post_hp", "actual_damage"))
        and value["target_pre_hp"] > value["target_post_hp"]
        and value["actual_damage"] == value["target_pre_hp"] - value["target_post_hp"]
    )


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
