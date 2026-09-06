"""Strict, read-only D0 authority for Fling's pre-hit item throw boundary."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_d0_item_suppression_field_authority import resolve_runtime_d0_item_suppression_field_authority
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-fling-item-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_fling_item_execution_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve Fling through its canonical pre-hit throw point.

    A ready throw consumes the item even if later hit resolution is a miss,
    Protect, or type immunity. Pre-execution cancellation is deliberately not
    represented here: callers must not materialize this authority for a move
    that never reaches Fling's prepare-hit boundary.
    """
    base = _base(strategy_d0, action, actor, target)
    if base is None:
        return _result("rejected", "fling_identity_or_d0_invalid", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    catalog = resolve_canonical_fling_core_move(move=_metadata(action))
    if catalog.get("status") != "resolved" or _metadata(action) != catalog.get("metadata"):
        return _result("rejected", "fling_catalog_metadata_mismatch", base, canonical_move=catalog)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    actor_raw, target_raw = _pokemon(state, actor), _pokemon(state, target)
    if actor_raw is None or target_raw is None:
        return _result("rejected", "fling_runtime_identity_mismatch", base, canonical_move=catalog)
    item = _item_authority(actor_raw, actor, base)
    field = resolve_runtime_d0_item_suppression_field_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    abilities = _ability_and_suppression(actor_raw, target_raw, actor, target, base)
    common = {"canonical_move": catalog, "user_item_before": item, "item_suppression_field_authority": field, "ability_suppression_authority": abilities}
    if item["status"] == "unknown":
        return _terminal("incomplete_authority", "incomplete", "fling_user_item_unknown", base, common)
    if field.get("status") != "resolved":
        return _terminal("incomplete_authority", "incomplete", "fling_item_suppression_field_unknown", base, common)
    if abilities.get("status") != "resolved":
        return _terminal("incomplete_authority", "incomplete", "fling_ability_or_suppression_unknown", base, common)
    if field.get("state") == "active":
        return _terminal("failed_item_suppressed", "resolved", "fling_magic_room_active", base, common)
    if item["status"] == "known_absent":
        return _terminal("failed_no_item", "resolved", "fling_user_known_item_absent", base, common)
    if abilities["klutz_active"]:
        return _terminal("failed_klutz", "resolved", "fling_klutz_active", base, common)
    metadata = resolve_canonical_fling_item_metadata(item["value"])
    common["fling_item_metadata"] = metadata
    if metadata.get("status") != "resolved":
        return _terminal("incomplete_authority", metadata.get("status", "incomplete"), metadata.get("reason", "fling_item_metadata_unknown"), base, common)
    effect = metadata.get("effect")
    if not metadata.get("flingable") or not isinstance(metadata.get("base_power"), int) or isinstance(metadata["base_power"], bool) or metadata["base_power"] <= 0 or not isinstance(effect, Mapping):
        return _terminal("incomplete_authority", "incomplete", "fling_item_execution_eligibility_unknown", base, common)
    if effect.get("kind") != "none" or metadata.get("support_status") != "not_applicable":
        return _terminal("unsupported_mandatory_item_effect", "unsupported", "fling_mandatory_item_effect_unsupported", base, common)
    common["item_after"] = {"state": "known_absent", "item": None}
    common["resolved_base_power"] = metadata["base_power"]
    return _terminal("ready_throw", "resolved", "fling_prepare_hit_throw_ready", base, common)


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(actor) or not _owner(target) or not isinstance(action, Mapping):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or actor != d0.get("decision_owner") or active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target) or actor.get("side") == target.get("side"):
        return None
    action_id, selected = action.get("action_id"), action.get("identity")
    if action.get("action_type") != "attack" or not isinstance(action_id, str) or not action_id or selected != "fling":
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action_id, "selected_move_id": "fling", "execution_move_id": "fling", "move_id": "fling", "move_family": "fling_core_item_power_and_throw"}


def _metadata(action: Mapping[str, Any]) -> Mapping[str, Any]:
    source = action.get("move_metadata_authority") or action.get("metadata_authority")
    return source.get("metadata") if isinstance(source, Mapping) and source.get("status") == "resolved" and isinstance(source.get("metadata"), Mapping) else {}


def _item_authority(raw: Mapping[str, Any], owner: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    value, provenance = raw.get("known_item"), raw.get("known_item_provenance")
    common = {"owner": deepcopy(dict(owner)), "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "runtime_item_provenance": deepcopy(provenance) if isinstance(provenance, Mapping) else None}
    if isinstance(value, str) and value and not is_unknown_battle_fact(value): return {"status": "known", "value": value, **common}
    if value is None and isinstance(provenance, Mapping) and provenance.get("event_kind") in {"current_item_observed", "current_opponent_switch_target_combat_observed", "item_consumption_observed", "item_removed_observed"}: return {"status": "known_absent", "value": None, **common}
    return {"status": "unknown", "value": None, **common}


def _ability_and_suppression(actor_raw: Mapping[str, Any], target_raw: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    def one(raw: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
        value, provenance = raw.get("current_ability"), raw.get("current_ability_provenance")
        return {"status": "known", "owner": deepcopy(dict(owner)), "value": value, "runtime_ability_provenance": deepcopy(provenance)} if isinstance(value, str) and value and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation" else {"status": "unknown", "owner": deepcopy(dict(owner))}
    own, foe = one(actor_raw, actor), one(target_raw, target)
    if own["status"] != "known" or foe["status"] != "known": return {"status": "incomplete", "actor": own, "target": foe}
    gas = own["value"] == "neutralizing-gas" or foe["value"] == "neutralizing-gas"
    return {"status": "resolved", "actor": own, "target": foe, "neutralizing_gas_active": gas, "klutz_active": own["value"] == "klutz" and not gas, "provenance": "runtime_d0_fling_ability_suppression_v1", "binding": {key: deepcopy(base[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "actor", "target")}}


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; raw = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return raw if isinstance(raw, Mapping) and raw.get("pokemon_id") == owner["pokemon_id"] else None
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _terminal(outcome: str, status: str, reason: str, base: Mapping[str, Any], common: Mapping[str, Any]) -> dict[str, Any]:
    result = {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), **deepcopy(dict(common)), "outcome": outcome, "reason": reason, "provenance": "strict_runtime_d0_fling_item_execution_freeze_v1"}
    result.setdefault("item_after", {"state": "known_present", "item": result.get("user_item_before", {}).get("value")} if result.get("user_item_before", {}).get("status") == "known" else {"state": "known_absent", "item": None} if result.get("user_item_before", {}).get("status") == "known_absent" else {"state": "unknown", "item": None})
    return result
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
