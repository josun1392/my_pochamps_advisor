"""Strict D0-bound adapter for the existing narrow move action-order engine.

This owner deliberately answers only the mechanical ordering question for one
own attack and one identity-bound known opponent attack.  It neither claims the
opponent attack is usable nor executes either action.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority,
    freeze_runtime_current_stage_authority,
    freeze_runtime_final_combat_stat_authority,
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)
from llm.narrow_action_order import evaluate_action_order


SCHEMA_VERSION = "runtime-d0-action-order-authority-v1"
_STATUSES = frozenset({"resolved", "incomplete", "unsupported", "rejected"})
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_action_order_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one move-vs-move mechanical order result at the current D0."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    own, opponent = strategy_d0["active_owners"].get("self"), strategy_d0["active_owners"].get("opponent")
    if not _owner(own) or not _owner(opponent) or strategy_d0.get("decision_owner") != own:
        return _result("rejected", "runtime_action_order_identity_unavailable", base)
    own_metadata = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=own_action)
    opponent_metadata = _opponent_metadata(strategy_d0, opponent_action, own, opponent)
    common = {**base, "own_action_id": own_action.get("action_id"), "opponent_action_id": opponent_action.get("action_id"),
              "own_actor": deepcopy(dict(own)), "opponent_actor": deepcopy(dict(opponent)),
              "opponent_usability": deepcopy(opponent_action.get("usability")) if isinstance(opponent_action.get("usability"), Mapping) else {"status": "unknown"},
              "own_move_metadata_authority": deepcopy(own_metadata), "opponent_move_metadata_authority": deepcopy(opponent_metadata)}
    for authority in (own_metadata, opponent_metadata):
        if authority.get("status") != "resolved":
            return _result(authority.get("status", "rejected"), authority.get("reason", "move_metadata_unavailable"), common)
    own_move = _move(own_metadata, own_action.get("identity"))
    opponent_move = _move(opponent_metadata, opponent_action.get("move_id"))
    if own_move is None or opponent_move is None:
        return _result("incomplete", "action_order_move_priority_or_metadata_missing", common)

    state = _runtime_state(runtime_snapshot)
    raw_own, raw_opponent = _pokemon(state, own), _pokemon(state, opponent)
    if raw_own is None or raw_opponent is None:
        return _result("rejected", "runtime_action_order_identity_mismatch", common)
    facts = _facts(strategy_d0, runtime_snapshot, state, raw_own, raw_opponent, own, opponent)
    if facts.get("status") != "resolved":
        return _result(facts["status"], facts.get("reason", "runtime_action_order_authority_incomplete"), {**common, "order_input_authority": facts})
    engine = evaluate_action_order(
        self_action=own_move, opponent_action=opponent_move,
        self_final_speed=facts["self_final_speed"], opponent_final_speed=facts["opponent_final_speed"],
        trick_room=facts["trick_room"], trick_room_provenance="trusted_observed_current",
        self_tailwind=facts["self_tailwind"], opponent_tailwind=facts["opponent_tailwind"],
        self_tailwind_provenance="trusted_observed_current", opponent_tailwind_provenance="trusted_observed_current",
        self_paralysis=facts["self_paralysis"], opponent_paralysis=facts["opponent_paralysis"],
        self_paralysis_provenance="trusted_observed_current", opponent_paralysis_provenance="trusted_observed_current",
        self_paralysis_speed_ability_unsupported=facts["self_speed_ability"] == "quick-feet",
        opponent_paralysis_speed_ability_unsupported=facts["opponent_speed_ability"] == "quick-feet",
        self_speed_stage=facts["self_speed_stage"], opponent_speed_stage=facts["opponent_speed_stage"],
        self_speed_item=facts["self_speed_item"], opponent_speed_item=facts["opponent_speed_item"],
        self_speed_ability=facts["self_speed_ability"], opponent_speed_ability=facts["opponent_speed_ability"], weather=facts["weather"],
        self_priority_ability=facts["self_priority_ability"], opponent_priority_ability=facts["opponent_priority_ability"],
        self_gale_wings_full_hp=facts["self_full_hp"], opponent_gale_wings_full_hp=facts["opponent_full_hp"],
        terrain=facts["terrain"], self_grounded=facts["self_grounded"], opponent_grounded=facts["opponent_grounded"],
    )
    status = {"acts_first": "resolved", "acts_second": "resolved", "speed_tie": "resolved", "insufficient_context": "incomplete", "unsupported_mechanic": "unsupported"}.get(engine.get("status"), "rejected")
    result = {"status": status, "schema_version": SCHEMA_VERSION, **common, "order_input_authority": facts, "order_engine": deepcopy(engine), "provenance": "runtime_d0_narrow_action_order_adapter_v1"}
    if engine.get("status") == "acts_first": result["order"] = "own_first"
    elif engine.get("status") == "acts_second": result["order"] = "opponent_first"
    elif engine.get("status") == "speed_tie": result["order"] = "unresolved_tie"
    else: result["reason"] = engine.get("unsupported_reason") or (engine.get("missing_inputs") or ["narrow_action_order_incomplete"])[0]
    return result


def _facts(d0: Mapping[str, Any], snapshot: Mapping[str, Any], state: Mapping[str, Any], raw_self: Mapping[str, Any], raw_opp: Mapping[str, Any], self_owner: Mapping[str, Any], opp_owner: Mapping[str, Any]) -> dict[str, Any]:
    speed_self = freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=self_owner, stat="speed")
    speed_opp = freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=opp_owner, stat="speed")
    stage_self = freeze_runtime_current_stage_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=self_owner)
    stage_opp = freeze_runtime_current_stage_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=opp_owner)
    condition_self = freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=self_owner)
    condition_opp = freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=opp_owner)
    authorities = (speed_self, speed_opp, stage_self, stage_opp, condition_self, condition_opp)
    if any(row.get("status") == "rejected" for row in authorities): return {"status": "rejected", "reason": "runtime_action_order_current_authority_rejected"}
    values = {
        "self_final_speed": _known(speed_self.get("final_stat_authority")), "opponent_final_speed": _known(speed_opp.get("final_stat_authority")),
        "self_speed_stage": _known(stage_self.get("stages", {}).get("speed")), "opponent_speed_stage": _known(stage_opp.get("stages", {}).get("speed")),
        "self_paralysis": _paralysis(condition_self), "opponent_paralysis": _paralysis(condition_opp),
        "self_speed_item": _item(raw_self), "opponent_speed_item": _item(raw_opp),
        "self_speed_ability": _ability(raw_self), "opponent_speed_ability": _ability(raw_opp),
        "self_priority_ability": _ability(raw_self), "opponent_priority_ability": _ability(raw_opp),
        "self_full_hp": _full_hp(d0, self_owner), "opponent_full_hp": _full_hp(d0, opp_owner),
        "self_tailwind": _tailwind(state, "self"), "opponent_tailwind": _tailwind(state, "opponent"),
        "trick_room": _trick_room(state), "weather": _weather(state), "terrain": _terrain(state),
        "self_grounded": "unknown", "opponent_grounded": "unknown",
    }
    # Groundedness is material only to Grassy Glide; the narrow engine requests it then.
    return {"status": "resolved", **values, "speed_authorities": {"self": speed_self, "opponent": speed_opp}, "stage_authorities": {"self": stage_self, "opponent": stage_opp}, "condition_authorities": {"self": condition_self, "opponent": condition_opp}}


def _opponent_metadata(d0: Mapping[str, Any], action: Mapping[str, Any], own: Mapping[str, Any], opponent: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(action, Mapping) or action.get("schema_version") != "runtime-d0-opponent-known-move-action-authority-v1" or action.get("action_type") != "attack" or action.get("opponent_actor") != dict(opponent) or action.get("target_owner") != dict(own):
        return {"status": "rejected", "reason": "opponent_action_binding_mismatch"}
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    if any(action.get(key) != value for key, value in expected.items()): return {"status": "rejected", "reason": "opponent_action_binding_mismatch"}
    value = action.get("metadata_authority")
    if not isinstance(value, Mapping) or value.get("status") not in _STATUSES: return {"status": "rejected", "reason": "opponent_move_metadata_authority_invalid"}
    return deepcopy(dict(value))


def _move(authority: Mapping[str, Any], expected_id: Any) -> dict[str, Any] | None:
    metadata = authority.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != expected_id or not isinstance(expected_id, str): return None
    priority = metadata.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool) or not -7 <= priority <= 7: return None
    category, move_type = metadata.get("category"), metadata.get("type")
    if category not in {"physical", "special", "status"} or not isinstance(move_type, str) or not move_type: return None
    return {"move_id": expected_id, "priority": priority, "category": category, "type": move_type, "triage_healing": metadata.get("triage_healing", "omitted")}


def _known(value: Any) -> Any: return value.get("value") if isinstance(value, Mapping) and value.get("status") == "known" else None
def _paralysis(authority: Mapping[str, Any]) -> str:
    condition = authority.get("condition") if isinstance(authority, Mapping) else None
    if not isinstance(condition, Mapping): return "unknown"
    if condition.get("status") == "known_none": return "not_paralyzed"
    if condition.get("status") == "known_present": return "paralyzed" if condition.get("condition") == "paralysis" else "not_paralyzed"
    return "unknown"
def _ability(raw: Mapping[str, Any]) -> str:
    value, provenance = raw.get("current_ability"), raw.get("current_ability_provenance")
    return value if isinstance(value, str) and value and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation" else "unknown"
def _item(raw: Mapping[str, Any]) -> str:
    value, provenance = raw.get("known_item"), raw.get("known_item_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") not in {"current_item_observed", "item_consumption_observed", "item_removed_observed"}: return "unknown"
    return value if isinstance(value, str) and value else "none" if value is None else "unknown"
def _tailwind(state: Mapping[str, Any], side: str) -> str:
    value = state.get(f"{side}_side", {}).get("tailwind_status") if isinstance(state.get(f"{side}_side"), Mapping) else None
    provenance = state.get(f"{side}_side", {}).get("tailwind_status_provenance") if isinstance(state.get(f"{side}_side"), Mapping) else None
    return value if isinstance(value, str) and value in {"active", "inactive"} and isinstance(provenance, Mapping) and provenance.get("event_kind") == "set_observed_tailwind" and provenance.get("trust") == "user_confirmed_observation" else "unknown"
def _trick_room(state: Mapping[str, Any]) -> str:
    field = state.get("field"); value = field.get("trick_room_status") if isinstance(field, Mapping) else None; provenance = field.get("trick_room_status_provenance") if isinstance(field, Mapping) else None
    return value if isinstance(value, str) and value in {"active", "inactive"} and isinstance(provenance, Mapping) and provenance.get("event_kind") == "set_observed_trick_room" and provenance.get("trust") == "user_confirmed_observation" else "unknown"
def _weather(state: Mapping[str, Any]) -> str:
    field = state.get("field"); value = field.get("weather") if isinstance(field, Mapping) else None; provenance = field.get("weather_provenance") if isinstance(field, Mapping) else None
    if not (isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_weather_observed" and provenance.get("trust") == "user_confirmed_observation"): return "unknown"
    return {"sandstorm": "sand"}.get(value, value) if isinstance(value, str) and value in {"none", "sun", "rain", "sandstorm", "snow"} else "unknown"
def _terrain(state: Mapping[str, Any]) -> str:
    field = state.get("field"); value = field.get("terrain") if isinstance(field, Mapping) else None; provenance = field.get("terrain_provenance") if isinstance(field, Mapping) else None
    return value if isinstance(value, str) and value in {"none", "electric", "grassy", "misty", "psychic"} and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_terrain_observed" and provenance.get("trust") == "user_confirmed_observation" else "unknown"
def _full_hp(d0: Mapping[str, Any], owner: Mapping[str, Any]) -> str:
    current = d0.get("strategy_state", {}).get("current_state", {}).get("runtime_strategy_d0_authority", {}).get("active", {}).get(owner["side"], {})
    hp, maximum = current.get("current_hp", {}), current.get("max_hp", {}) if isinstance(current, Mapping) else ({}, {})
    if not isinstance(hp, Mapping) or not isinstance(maximum, Mapping) or hp.get("status") != "known" or maximum.get("status") != "known": return "unknown"
    return "full" if hp.get("value") == maximum.get("value") else "not_full"
def _runtime_state(snapshot: Any) -> Mapping[str, Any] | None:
    value = snapshot.get("state") if isinstance(snapshot, Mapping) else None; return value if isinstance(value, Mapping) else None
def _pokemon(state: Mapping[str, Any] | None, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return value if isinstance(value, Mapping) and value.get("pokemon_id") == owner["pokemon_id"] else None
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(d0.get("decision_owner")) or not isinstance(d0.get("active_owners"), Mapping): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"]))}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
