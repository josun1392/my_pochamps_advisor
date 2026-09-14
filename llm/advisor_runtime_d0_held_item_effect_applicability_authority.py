"""Strict current held-item effect applicability composed from field and ability facts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from core.champions_item_repository import normalize_item_id
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_d0_item_suppression_field_authority import (
    resolve_runtime_d0_item_suppression_field_authority,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-held-item-effect-applicability-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def resolve_runtime_d0_held_item_effect_applicability_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], holder: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve whether this holder's exact current held item may have an effect.

    This is deliberately a narrow consumer boundary: Magic Room and active,
    unsuppressed Klutz are the only item-effect suppressors it classifies.
    Unknown evidence is never promoted to an active item effect.
    """
    base = _base(strategy_d0, holder)
    if base is None:
        return _result("rejected", "invalid_held_item_effect_applicability_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    raw_holder = _pokemon(state, holder)
    if raw_holder is None:
        return _result("rejected", "held_item_effect_holder_identity_mismatch", base)
    item = _item(raw_holder)
    common = {**base, "current_item_authority": item}
    if item["status"] == "unknown":
        return _result("incomplete", "held_item_effect_current_item_unknown", common)
    if item["status"] == "known_absent":
        return _resolved(common, outcome="known_no_item", item_effects_active=False,
                         reason="current_held_item_known_absent")

    field = resolve_runtime_d0_item_suppression_field_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    common["item_suppression_field_authority"] = deepcopy(dict(field))
    if field.get("status") != "resolved":
        return _result("incomplete", "held_item_suppression_field_authority_unknown", common)
    if field.get("item_effects_suppressed") is True:
        return _resolved(common, outcome="suppressed", item_effects_active=False,
                         reason="magic_room_item_effects_suppressed",
                         ability_suppression_authority={"status": "not_required", "reason": "magic_room_active"})
    if field.get("item_effects_suppressed") is not False:
        return _result("rejected", "held_item_suppression_field_result_invalid", common)

    holder_ability = _ability(raw_holder, holder)
    common["holder_ability_authority"] = holder_ability
    if holder_ability["status"] != "known":
        return _result("incomplete", "held_item_effect_holder_ability_unknown", common)
    if holder_ability["ability_id"] != "klutz":
        return _resolved(common, outcome="active", item_effects_active=True,
                         reason="magic_room_inactive_holder_not_klutz",
                         ability_suppression_authority={"status": "resolved", "outcome": "not_applicable", "reason": "holder_not_klutz"})

    other = _other_owner(strategy_d0, holder)
    raw_other = _pokemon(state, other) if other is not None else None
    if raw_other is None:
        return _result("rejected", "held_item_effect_other_active_identity_mismatch", common)
    other_ability = _ability(raw_other, other)
    common["other_active_ability_authority"] = other_ability
    if other_ability["status"] != "known":
        return _result("incomplete", "held_item_effect_klutz_suppression_unknown", common)
    if other_ability["ability_id"] == "neutralizing-gas":
        return _resolved(common, outcome="active", item_effects_active=True,
                         reason="klutz_suppressed_by_neutralizing_gas",
                         ability_suppression_authority={"status": "resolved", "outcome": "suppressed", "reason": "opposing_neutralizing_gas"})
    return _resolved(common, outcome="suppressed", item_effects_active=False,
                     reason="klutz_item_effects_suppressed",
                     ability_suppression_authority={"status": "resolved", "outcome": "applies", "reason": "active_klutz"})


def _base(d0: Any, holder: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(holder):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(holder["side"]) != dict(holder):
        return None
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner")
    if not all(d0.get(key) for key in required):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])), "holder": deepcopy(dict(holder)),
    }


def _other_owner(d0: Mapping[str, Any], holder: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = "opponent" if holder["side"] == "self" else "self"
    value = d0.get("active_owners", {}).get(side)
    return value if _owner(value) else None


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return value if isinstance(value, Mapping) and value.get("pokemon_id") == owner["pokemon_id"] else None


def _item(raw: Mapping[str, Any]) -> dict[str, Any]:
    value, provenance = raw.get("known_item"), raw.get("known_item_provenance")
    trusted = isinstance(provenance, Mapping) and provenance.get("event_kind") in {"current_item_observed", "item_consumption_observed", "item_removed_observed"} and provenance.get("trust") == "user_confirmed_observation"
    if isinstance(value, str) and value and not is_unknown_battle_fact(value) and trusted:
        return {"status": "known", "item_id": normalize_item_id(value), "source_provenance": deepcopy(dict(provenance))}
    if value is None and trusted and (provenance.get("status") == "known_absent" or provenance.get("event_kind") in {"item_consumption_observed", "item_removed_observed"}):
        return {"status": "known_absent", "item_id": None, "source_provenance": deepcopy(dict(provenance))}
    return {"status": "unknown", "item_id": None}


def _ability(raw: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    value, provenance = raw.get("current_ability"), raw.get("current_ability_provenance")
    if isinstance(value, str) and value and not is_unknown_battle_fact(value) and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation":
        return {"status": "known", "owner": deepcopy(dict(owner)), "ability_id": value, "source_provenance": deepcopy(dict(provenance))}
    return {"status": "unknown", "owner": deepcopy(dict(owner))}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _resolved(base: Mapping[str, Any], *, outcome: str, item_effects_active: bool, reason: str, ability_suppression_authority: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome,
            "item_effects_active": item_effects_active, "reason": reason,
            "ability_suppression_authority": deepcopy(dict(ability_suppression_authority)),
            "provenance": "runtime_d0_held_item_effect_applicability_v1"}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
