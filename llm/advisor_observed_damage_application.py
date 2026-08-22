"""Shared bounded F0-to-F1 application of already-trusted exact damage."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state


OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def apply_exact_observed_damage(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    user: Mapping[str, Any], target_owner: Mapping[str, Any], damage_amount: int,
) -> dict[str, Any]:
    """Apply one already-resolved, exact positive damage amount to an exact target.

    This is deliberately not a move executor or damage calculator.  Callers
    establish their bounded move/result/provenance contract before using it.
    """
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_damage_branch")
    if not _valid_damage_authority(active, user, target_owner, damage_amount):
        return _result("rejected", "invalid_observed_damage_authority")

    state = deepcopy(dict(branch_state))
    current_target = state["active"][target_owner["side"]]
    post_hp = max(0, current_target["current_hp"] - damage_amount)
    target_fainted = post_hp == 0
    current_target["current_hp"] = post_hp
    current_target["fainted"] = target_fainted
    _sync_hp(state, target_owner["side"], post_hp, current_target["max_hp"])
    resulting_fingerprint = fingerprint_transition_preview_state(state)
    if resulting_fingerprint is None:
        return _result("rejected", "unserializable_observed_damage_branch")
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": resulting_fingerprint,
        "next_state": state,
        "damage_application": {
            "user": deepcopy(dict(user)), "target_owner": deepcopy(dict(target_owner)),
            "damage": damage_amount, "post_hp": post_hp, "target_fainted": target_fainted,
        },
        "materialization": "pure_idempotent",
    }


def apply_exact_observed_recoil(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    recoil_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply an already-observed exact self-HP loss on one current F1 branch."""
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_recoil_branch")
    if not isinstance(recoil_authority, Mapping):
        return _result("rejected", "invalid_observed_recoil_authority")
    owner, recoil_amount = recoil_authority.get("owner"), recoil_authority.get("recoil_amount")
    if not (
        exact_owner(owner) and isinstance(recoil_amount, int) and not isinstance(recoil_amount, bool) and recoil_amount > 0
        and recoil_authority.get("source_branch_fingerprint") == source_branch_fingerprint
        and _current_owner(active, owner) and _active_hp_is_exact(active[owner["side"]])
        and active[owner["side"]].get("fainted") is False
    ):
        return _result("rejected", "invalid_observed_recoil_authority")
    state = deepcopy(dict(branch_state))
    current = state["active"][owner["side"]]
    post_hp = max(0, current["current_hp"] - recoil_amount)
    current["current_hp"], current["fainted"] = post_hp, post_hp == 0
    _sync_hp(state, owner["side"], post_hp, current["max_hp"])
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None:
        return _result("rejected", "unserializable_observed_recoil_branch")
    return {"status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
            "resulting_branch_fingerprint": fingerprint, "next_state": state,
            "recoil_application": {"owner": deepcopy(dict(owner)), "recoil": recoil_amount,
                                   "post_hp": post_hp, "owner_fainted": post_hp == 0},
            "materialization": "pure_idempotent"}


def apply_exact_observed_drain_consequence(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, drain_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Apply a drain-family exact F1 consequence: healing or Liquid-Ooze damage."""
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint or not isinstance(drain_authority, Mapping): return _result("rejected", "stale_or_invalid_observed_drain_branch")
    owner, kind, amount = drain_authority.get("owner"), drain_authority.get("consequence"), drain_authority.get("amount")
    if not (exact_owner(owner) and drain_authority.get("source_branch_fingerprint") == source_branch_fingerprint and kind in {"heal", "self_damage"} and isinstance(amount, int) and not isinstance(amount, bool) and amount > 0 and _current_owner(active, owner) and _active_hp_is_exact(active[owner["side"]]) and active[owner["side"]].get("fainted") is False): return _result("rejected", "invalid_observed_drain_authority")
    state = deepcopy(dict(branch_state)); current = state["active"][owner["side"]]
    post = min(current["max_hp"], current["current_hp"] + amount) if kind == "heal" else max(0, current["current_hp"] - amount)
    current["current_hp"], current["fainted"] = post, post == 0; _sync_hp(state, owner["side"], post, current["max_hp"])
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None: return _result("rejected", "unserializable_observed_drain_branch")
    return {"status":"resolved","source_branch_fingerprint":source_branch_fingerprint,"resulting_branch_fingerprint":fingerprint,"next_state":state,"drain_application":{"owner":deepcopy(dict(owner)),"consequence":kind,"amount":amount,"post_hp":post,"owner_fainted":post==0},"materialization":"pure_idempotent"}


def apply_exact_observed_self_stage_consequence(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    stage_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply one exact F1-bound self-stage consequence to its active owner.

    This consumes no move metadata and performs no secondary-effect resolution.
    Its caller establishes the bounded move/result contract.
    """
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if (
        not isinstance(active, Mapping)
        or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint
        or not isinstance(stage_authority, Mapping)
    ):
        return _result("rejected", "stale_or_invalid_observed_self_stage_branch")
    owner, stat, delta = (
        stage_authority.get("owner"),
        stage_authority.get("stat"),
        stage_authority.get("delta"),
    )
    if not (
        exact_owner(owner)
        and stage_authority.get("schema_version") == "observed-flame-charge-self-stage-authority-v1"
        and stage_authority.get("provenance") == "trusted_observed_damage_plus_self_stage_result_v1"
        and stage_authority.get("source_branch_fingerprint") == source_branch_fingerprint
        and stat in {"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"}
        and isinstance(delta, int) and not isinstance(delta, bool) and -6 <= delta <= 6 and delta != 0
        and _current_owner(active, owner)
        and active[owner["side"]].get("fainted") is False
    ):
        return _result("rejected", "invalid_observed_self_stage_authority")
    state = deepcopy(dict(branch_state))
    previous = _sync_stage(state, owner["side"], stat, delta)
    if previous is None:
        return _result("rejected", "invalid_observed_self_stage_authority")
    projected = max(-6, min(6, previous + delta))
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None:
        return _result("rejected", "unserializable_observed_self_stage_branch")
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": fingerprint,
        "next_state": state,
        "self_stage_application": {
            "owner": deepcopy(dict(owner)), "stat": stat, "previous_stage": previous,
            "delta": delta, "projected_stage": projected,
        },
        "materialization": "pure_idempotent",
    }


def apply_exact_observed_target_stage_consequence(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    stage_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply Acid Spray's exact F1-bound target Special Defense drop only."""
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if (
        not isinstance(active, Mapping)
        or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint
        or not isinstance(stage_authority, Mapping)
    ):
        return _result("rejected", "stale_or_invalid_observed_target_stage_branch")
    owner, stat, delta = (
        stage_authority.get("owner"),
        stage_authority.get("stat"),
        stage_authority.get("delta"),
    )
    if not (
        exact_owner(owner)
        and stage_authority.get("schema_version") == "observed-acid-spray-target-stage-authority-v1"
        and stage_authority.get("provenance") == "trusted_observed_damage_plus_target_stage_result_v1"
        and stage_authority.get("source_branch_fingerprint") == source_branch_fingerprint
        and stat == "special-defense" and delta == -2
        and _current_owner(active, owner) and active[owner["side"]].get("fainted") is False
    ):
        return _result("rejected", "invalid_observed_target_stage_authority")
    baseline = _exact_current_stage(branch_state, owner["side"], stat)
    previous, consumes_overlay = _effective_target_stage(branch_state, owner, stat, baseline)
    if previous is None:
        return _result("rejected", "invalid_observed_target_stage_authority")
    projected = max(-6, min(6, previous + delta))
    if projected == previous:
        return _result("rejected", "target_stage_already_at_bound")
    state = deepcopy(dict(branch_state))
    synced = _set_exact_stage(state, owner["side"], stat, projected)
    if synced != baseline:
        return _result("rejected", "invalid_observed_target_stage_authority")
    if consumes_overlay:
        state.pop("predicted_stage_context", None)
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None:
        return _result("rejected", "unserializable_observed_target_stage_branch")
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": fingerprint, "next_state": state,
        "target_stage_application": {
            "owner": deepcopy(dict(owner)), "stat": stat, "previous_stage": previous,
            "delta": delta, "projected_stage": projected,
        },
        "materialization": "pure_idempotent",
    }


def apply_exact_observed_life_orb_consequence(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    life_orb_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply one exact F1-bound canonical Life Orb HP consequence."""
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if (
        not isinstance(active, Mapping)
        or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint
        or not isinstance(life_orb_authority, Mapping)
    ):
        return _result("rejected", "stale_or_invalid_life_orb_branch")
    owner, amount = life_orb_authority.get("owner"), life_orb_authority.get("recoil_amount")
    if not (
        exact_owner(owner)
        and life_orb_authority.get("schema_version") == "life-orb-post-hit-authority-v1"
        and life_orb_authority.get("provenance") == "trusted_observed_life_orb_post_hit_v1"
        and life_orb_authority.get("source_branch_fingerprint") == source_branch_fingerprint
        and isinstance(amount, int) and not isinstance(amount, bool) and amount > 0
        and _current_owner(active, owner) and _active_hp_is_exact(active[owner["side"]])
        and active[owner["side"]].get("fainted") is False
    ):
        return _result("rejected", "invalid_life_orb_authority")
    state = deepcopy(dict(branch_state))
    current = state["active"][owner["side"]]
    post_hp = max(0, current["current_hp"] - amount)
    current["current_hp"], current["fainted"] = post_hp, post_hp == 0
    _sync_hp(state, owner["side"], post_hp, current["max_hp"])
    fingerprint = fingerprint_transition_preview_state(state)
    if fingerprint is None:
        return _result("rejected", "unserializable_life_orb_branch")
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": fingerprint, "next_state": state,
        "life_orb_application": {
            "owner": deepcopy(dict(owner)), "recoil": amount, "post_hp": post_hp,
            "owner_fainted": post_hp == 0,
        },
        "materialization": "pure_idempotent",
    }


def exact_owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and set(value) == set(OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _valid_damage_authority(active: Mapping[str, Any], user: Any, target: Any, damage: Any) -> bool:
    return (
        exact_owner(user) and exact_owner(target)
        and isinstance(damage, int) and not isinstance(damage, bool) and damage > 0
        and user["session_id"] == target["session_id"]
        and user["side"] != target["side"]
        and _current_owner(active, user) and _current_owner(active, target)
        and _active_hp_is_exact(active[target["side"]])
        and active[user["side"]].get("fainted") is False and active[target["side"]].get("fainted") is False
    )


def _current_owner(active: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    current = active.get(owner["side"])
    return isinstance(current, Mapping) and dict(owner) == {key: current.get(key) for key in OWNER_KEYS}


def _active_hp_is_exact(active: Mapping[str, Any]) -> bool:
    hp, maximum = active.get("current_hp"), active.get("max_hp")
    return (
        isinstance(hp, int) and not isinstance(hp, bool)
        and isinstance(maximum, int) and not isinstance(maximum, bool)
        and maximum > 0 and 0 < hp <= maximum
    )


def _sync_hp(state: Mapping[str, Any], side: str, hp: int, maximum: int) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    if not isinstance(current, dict):
        return
    rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current.get("current_hp_context"), Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == side:
                row["current_hp"], row["maximum_hp"] = hp, maximum
    direct = current.get("direct_mechanics_context")
    role = "attacker" if side == "self" else "defender"
    combatant = direct.get(role) if isinstance(direct, Mapping) else None
    if isinstance(combatant, dict):
        combatant["current_hp"], combatant["max_hp"] = hp, maximum


def _sync_stage(state: Mapping[str, Any], side: str, stat: str, delta: int) -> int | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("stat_stage_context", {}).get("current_stages") if isinstance(current, Mapping) else None
    match = next((
        row for row in rows
        if isinstance(row, dict)
        and row.get("side") == side and row.get("stat") == stat
        and row.get("status") == "user_confirmed"
        and row.get("source") == "user_confirmed_current_stat_stage"
        and row.get("confidence") == "known"
        and isinstance(row.get("stage"), int) and not isinstance(row.get("stage"), bool)
        and -6 <= row["stage"] <= 6
    ), None) if isinstance(rows, list) else None
    if match is None:
        return None
    previous = match["stage"]
    match["stage"] = max(-6, min(6, previous + delta))
    direct = current.get("direct_mechanics_context") if isinstance(current, Mapping) else None
    role = "attacker" if side == "self" else "defender"
    combatant = direct.get(role) if isinstance(direct, Mapping) else None
    if isinstance(combatant, dict) and isinstance(combatant.get("boosts"), dict):
        combatant["boosts"][stat] = match["stage"]
    return previous


def _exact_current_stage(state: Mapping[str, Any], side: str, stat: str) -> int | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("stat_stage_context", {}).get("current_stages") if isinstance(current, Mapping) else None
    match = next((
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("side") == side and row.get("stat") == stat
        and row.get("status") == "user_confirmed"
        and row.get("source") == "user_confirmed_current_stat_stage"
        and row.get("confidence") == "known"
        and isinstance(row.get("stage"), int) and not isinstance(row.get("stage"), bool)
        and -6 <= row["stage"] <= 6
    ), None) if isinstance(rows, list) else None
    return match["stage"] if match is not None else None


def _effective_target_stage(
    state: Mapping[str, Any], owner: Mapping[str, Any], stat: str, baseline: int | None,
) -> tuple[int | None, bool]:
    if baseline is None:
        return None, False
    overlay = state.get("predicted_stage_context") if isinstance(state, Mapping) else None
    if overlay is None:
        return baseline, False
    if not isinstance(overlay, Mapping):
        return None, False
    if overlay.get("owner") != dict(owner) or overlay.get("stat") != stat:
        return baseline, False
    previous, delta, projected = overlay.get("previous_stage"), overlay.get("delta"), overlay.get("projected_stage")
    if not (
        overlay.get("schema_version") == "hypothetical-self-stage-v1"
        and previous == baseline
        and isinstance(delta, int) and not isinstance(delta, bool) and -6 <= delta <= 6
        and isinstance(projected, int) and not isinstance(projected, bool) and -6 <= projected <= 6
        and projected == max(-6, min(6, previous + delta))
    ):
        return None, False
    return projected, True


def _set_exact_stage(state: Mapping[str, Any], side: str, stat: str, stage: int) -> int | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("stat_stage_context", {}).get("current_stages") if isinstance(current, Mapping) else None
    match = next((
        row for row in rows
        if isinstance(row, dict) and row.get("side") == side and row.get("stat") == stat
        and row.get("status") == "user_confirmed"
        and row.get("source") == "user_confirmed_current_stat_stage"
        and row.get("confidence") == "known"
        and isinstance(row.get("stage"), int) and not isinstance(row.get("stage"), bool)
        and -6 <= row["stage"] <= 6
    ), None) if isinstance(rows, list) else None
    if match is None:
        return None
    previous = match["stage"]
    match["stage"] = stage
    direct = current.get("direct_mechanics_context") if isinstance(current, Mapping) else None
    role = "attacker" if side == "self" else "defender"
    combatant = direct.get(role) if isinstance(direct, Mapping) else None
    if isinstance(combatant, dict) and isinstance(combatant.get("boosts"), dict):
        combatant["boosts"][stat] = stage
    return previous


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
