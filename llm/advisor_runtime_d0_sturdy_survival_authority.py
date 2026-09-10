"""Frozen, identity-bound current Sturdy survival authority for one attack."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ability_interaction_authority import normalize_ability_applicability_context
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-sturdy-survival-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_sturdy_survival_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    defender: Mapping[str, Any], attacker: Mapping[str, Any], action: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind current, effective Sturdy readiness to one selected live action."""
    base = _base(strategy_d0, defender, attacker, action, move_metadata)
    if base is None:
        return _result("rejected", "invalid_sturdy_survival_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    row = _pokemon(state, defender)
    preview = strategy_d0.get("strategy_state", {}).get("active", {}).get(defender["side"])
    hp = _hp(preview)
    if row is None:
        return _result("rejected", "sturdy_defender_identity_mismatch", base)
    if hp is None:
        return _result("incomplete", "sturdy_hp_unknown", base)
    ability = _ability(row.get("current_ability"))
    payload = {**base, "current_hp": hp["current_hp"], "maximum_hp": hp["max_hp"], "current_ability_authority": ability}
    if ability["status"] == "unknown":
        return _result("incomplete", "sturdy_ability_unknown", payload)
    if ability["value"] != "sturdy":
        return _result("resolved", "known_non_sturdy_ability", payload, outcome="known_no_effect", sturdy_available=False, eligible=False)
    applicability = normalize_ability_applicability_context(
        state.get("ability_applicability_context") if isinstance(state, Mapping) else None,
        session_id=defender["session_id"], source=defender, ability_id="sturdy",
    )
    payload["sturdy_applicability_authority"] = applicability
    if applicability["status"] == "unknown":
        return _result("incomplete", "sturdy_applicability_unknown", payload)
    if applicability["status"] == "not_applicable":
        return _result("resolved", "sturdy_suppressed", payload, outcome="known_no_effect", sturdy_available=False, eligible=False)
    if hp["current_hp"] != hp["max_hp"] or hp["current_hp"] <= 1:
        return _result("resolved", "sturdy_hp_not_eligible", payload, outcome="known_no_effect", sturdy_available=True, eligible=False)
    return _result("ready", None, payload, outcome="available", sturdy_available=True, eligible=True)


def _base(d0: Any, defender: Any, attacker: Any, action: Any, metadata: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(defender) or not _owner(attacker) or defender["side"] == attacker["side"]:
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(defender["side"]) != dict(defender) or active.get(attacker["side"]) != dict(attacker):
        return None
    if not isinstance(action, Mapping) or action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str):
        return None
    move_id = metadata.get("move_id") if isinstance(metadata, Mapping) else None
    if not isinstance(move_id, str) or not move_id or action.get("identity", action.get("move_id")) != move_id:
        return None
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "defender": deepcopy(dict(defender)), "attacker": deepcopy(dict(attacker)),
        "action_id": action["action_id"], "move_id": move_id,
        "provenance": "runtime_d0_current_sturdy_survival_authority_v1",
    }


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return row if isinstance(row, Mapping) and row.get("pokemon_id") == owner["pokemon_id"] else None


def _hp(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    hp, maximum, fainted = value.get("current_hp"), value.get("max_hp"), value.get("fainted")
    if isinstance(hp, int) and not isinstance(hp, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 and 0 <= hp <= maximum and fainted is (hp == 0):
        return {"current_hp": hp, "max_hp": maximum}
    return None


def _ability(value: Any) -> dict[str, Any]:
    if isinstance(value, str) and value and not is_unknown_battle_fact(value):
        return {"status": "known", "value": value, "source": "runtime_current_ability", "trust": "runtime_current"}
    return {"status": "unknown", "value": None, "source": "unknown", "trust": "unknown"}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str | None, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
