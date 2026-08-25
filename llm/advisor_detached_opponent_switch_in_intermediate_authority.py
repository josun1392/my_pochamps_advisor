"""Detached hypothetical switch-in authority for one selectable opponent target."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_switch_entry_hazards import evaluate_entry_hazards
from llm.advisor_switch_hazard_authority import normalize_switch_hazard_context


SCHEMA_VERSION = "detached-opponent-switch-in-intermediate-authority-v1"


def materialize_detached_opponent_switch_in_intermediate_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    switch_response_authority: Mapping[str, Any],
    selected_response_action_id: str,
) -> dict[str, Any]:
    """Materialize one hypothetical opponent switch-in without state writeback."""
    base = _base(strategy_d0)
    if not base or not isinstance(selected_response_action_id, str) or not selected_response_action_id:
        return _result("rejected", "invalid_switch_in_request", base)
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    action = _selected_action(switch_response_authority, base, selected_response_action_id)
    if action.get("status") != "resolved":
        return _result(action["status"], action["reason"], base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    target = action["target_owner"]
    roster = state.get("opponent_side", {}).get("pokemon") if isinstance(state, Mapping) and isinstance(state.get("opponent_side"), Mapping) else None
    current = roster.get(target["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(current, Mapping) or current.get("pokemon_id") != target["pokemon_id"]:
        return _result("rejected", "switch_target_runtime_identity_mismatch", base, selected_response_action_id=selected_response_action_id)
    hp = _hp_authority(current)
    if hp is None:
        return _result("incomplete", "switch_target_hp_or_faint_unknown", base, selected_response_action_id=selected_response_action_id, target_owner=target)
    if hp["fainted"]:
        return _result("rejected", "selectable_switch_target_is_fainted", base, selected_response_action_id=selected_response_action_id, target_owner=target)
    hazards = _hazards(state, base["session_id"])
    entry = _entry_consequence(hazards, current, hp, target)
    if entry.get("status") != "resolved":
        return _result(entry["status"], entry["reason"], base, selected_response_action_id=selected_response_action_id, target_owner=target, entry_hazard_context=hazards)
    post_hp = entry["post_hp"]
    if post_hp == 0:
        return _result("unsupported", "replacement_required_after_switch_entry_ko", base, selected_response_action_id=selected_response_action_id, target_owner=target, entry_hazard_context=hazards, entry_consequence=entry)
    fields = _fields(current)
    hypothetical = {
        "schema_version": SCHEMA_VERSION,
        "hypothetical": True,
        "active_owner": deepcopy(target),
        "replaced_active_owner": deepcopy(base["opponent_actor"]),
        "hp_authority": {"status": "known", "current_hp": post_hp, "maximum_hp": hp["maximum_hp"], "provenance": "detached_switch_entry_v1"},
        "fainted_authority": {"status": "known", "value": False, "provenance": "detached_switch_entry_v1"},
        "condition_authority": fields["condition"],
        "item_authority": fields["item"],
        "ability_authority": fields["ability"],
        "type_authority": fields["type"],
        "final_stats_authority": fields["final_stats"],
        "stage_authority": fields["stages"],
        "substitute_authority": {"status": "unknown", "reason": "opponent_switch_in_substitute_untracked"},
        "entry_hazard_context": deepcopy(hazards),
        "entry_consequence": deepcopy(entry),
    }
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "selected_response_action_id": selected_response_action_id,
        "target_owner": deepcopy(target),
        "switch_response_authority_provenance": deepcopy(switch_response_authority.get("response_set_provenance")),
        "hypothetical_switch_in_state": hypothetical,
        "current_authority_writeback": "forbidden",
        "reason": None,
    }


def _selected_action(authority: Any, base: Mapping[str, Any], action_id: str) -> dict:
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_actor", "opponent_actor")
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or any(authority.get(key) != base.get(key) for key in required):
        return {"status": "rejected", "reason": "switch_response_authority_binding_mismatch"}
    actions = authority.get("actions")
    if not isinstance(actions, (tuple, list)):
        return {"status": "rejected", "reason": "switch_response_actions_invalid"}
    matching = [row for row in actions if isinstance(row, Mapping) and row.get("action_id") == action_id]
    if len(matching) != 1:
        return {"status": "rejected", "reason": "selected_switch_response_unknown"}
    action = matching[0]
    target = action.get("target_owner")
    if action.get("action_type") != "manual_switch" or action.get("acting_side") != "opponent" or action.get("target_side") != "self" or action.get("selectability") != "selectable" or not _owner(target, "opponent", base["session_id"]) or target == base["opponent_actor"]:
        return {"status": "incomplete", "reason": "selected_switch_response_not_selectable"}
    if action_id not in authority.get("selectable_response_action_ids", ()):
        return {"status": "rejected", "reason": "selectable_switch_response_set_mismatch"}
    return {"status": "resolved", "target_owner": deepcopy(dict(target))}


def _hp_authority(current: Mapping[str, Any]) -> dict | None:
    hp, maximum, fainted = current.get("current_hp"), current.get("max_hp"), current.get("fainted")
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0 or not isinstance(fainted, bool) or not 0 <= hp <= maximum or fainted is not (hp == 0):
        return None
    return {"current_hp": hp, "maximum_hp": maximum, "fainted": fainted}


def _hazards(state: Any, session_id: str) -> dict:
    raw = state.get("switch_hazard_context") if isinstance(state, Mapping) else None
    return normalize_switch_hazard_context(raw, session_id=session_id, affected_side="opponent")


def _entry_consequence(hazards: Mapping[str, Any], current: Mapping[str, Any], hp: Mapping[str, Any], target_owner: Mapping[str, Any]) -> dict:
    if not isinstance(hazards, Mapping) or any(hazards.get(key) == "unknown" for key in ("stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web")):
        return {"status": "incomplete", "reason": "switch_entry_hazards_unknown"}
    if hazards.get("toxic_spikes_layers") != 0 or hazards.get("sticky_web") != "absent":
        return {"status": "unsupported", "reason": "switch_entry_effect_not_supported_by_detached_adapter"}
    if hazards.get("stealth_rock") == "absent" and hazards.get("spikes_layers") == 0:
        return {"status": "resolved", "damage": 0, "post_hp": hp["current_hp"], "hazard_ko": False, "effect": "known_absent_entry_hazards"}
    target = {
        "side": "opponent",
        "hp_authority": {"status": "known", "current_hp": hp["current_hp"], "maximum_hp": hp["maximum_hp"]},
        "item_authority": _simple_authority(current.get("known_item")),
        "ability_authority": _simple_authority(current.get("current_ability")),
        "current_type_authority": _simple_authority(current.get("current_type")),
        "prospective_groundedness_authority": _groundedness_authority(current.get("prospective_groundedness_context"), target_owner),
    }
    evaluated = evaluate_entry_hazards(hazards=hazards, target=target)
    if evaluated.get("status") != "complete":
        return {"status": "incomplete", "reason": str(evaluated.get("reason") or "switch_entry_hazard_authority_incomplete")}
    return {"status": "resolved", "damage": evaluated["damage"], "post_hp": evaluated["post_hazard_hp"], "hazard_ko": evaluated["hazard_ko"], "effect": "supported_stealth_rock_or_spikes", "hazard_evidence": deepcopy(evaluated)}


def _fields(current: Mapping[str, Any]) -> dict:
    return {
        "condition": _simple_authority(current.get("condition")),
        "item": _simple_authority(current.get("known_item")),
        "ability": _simple_authority(current.get("current_ability")),
        "type": _simple_authority(current.get("current_type")),
        "final_stats": _simple_authority(current.get("current_final_stats")),
        "stages": _simple_authority(current.get("stat_stages")),
    }


def _simple_authority(value: Any) -> dict:
    if value is None or is_unknown_battle_fact(value):
        return {"status": "unknown"}
    return {"status": "known", "value": deepcopy(value), "provenance": "runtime_battle_state_v1"}


def _groundedness_authority(value: Any, target_owner: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != "identity-groundedness-v1" or any(value.get(key) != target_owner.get(key) for key in ("side", "slot_index", "pokemon_id")):
        return {"status": "unknown"}
    status = value.get("status")
    return {"status": status} if status in {"grounded", "ungrounded"} else {"status": "unknown"}


def _base(d0: Any) -> dict:
    owners = d0.get("active_owners") if isinstance(d0, Mapping) else None
    own, opponent = owners.get("self") if isinstance(owners, Mapping) else None, owners.get("opponent") if isinstance(owners, Mapping) else None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(own, "self", d0.get("session_id")) or not _owner(opponent, "opponent", d0.get("session_id")):
        return {}
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")), "own_actor": deepcopy(dict(own)), "opponent_actor": deepcopy(dict(opponent))}


def _owner(value: Any, side: str, session_id: Any) -> bool:
    return isinstance(value, Mapping) and value.get("session_id") == session_id and value.get("side") == side and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
