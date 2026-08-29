"""Strict D0-bound recipient expansion for one observed doubles action.

This owner proves targeting only.  It neither blocks Wide Guard nor executes
damage for more than one recipient.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-doubles-action-target-set-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SELECTION_TARGETS = frozenset({"selected-pokemon", "normal", "ally", "user-or-ally"})
_SUPPORTED = frozenset({"selected-pokemon", "normal", "all-opponents", "all-other-pokemon", "all-pokemon", "user", "ally", "user-and-allies", "user-or-ally"})


def freeze_runtime_d0_doubles_action_target_set_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], acting_owner: Mapping[str, Any], decision_point: str) -> dict[str, Any]:
    base = _base(strategy_d0, action, acting_owner, decision_point)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_action_target_set_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping) or state.get("session_id") != base["session_id"]:
        return _result("rejected", "runtime_snapshot_session_mismatch", base)
    if not _doubles_format(state):
        return _result("incomplete", "current_doubles_format_unavailable", base)
    topology = state.get("doubles_active_topology_context")
    if topology is None:
        return _result("incomplete", "doubles_active_topology_observation_missing", base)
    if not _topology(state, topology):
        return _result("rejected", "doubles_active_topology_context_invalid", base)
    targeting = state.get("selected_action_targeting_context")
    if targeting is None:
        return _result("incomplete", "selected_action_targeting_observation_missing", base)
    if not _targeting(state, targeting, base):
        return _result("rejected", "selected_action_targeting_binding_mismatch", base)
    last = state.get("last_applied_observation_sequence")
    if last != targeting["provenance"]["source_sequence"]:
        return _result("rejected", "stale_selected_action_targeting_observation", base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {**base, "move_metadata_authority": deepcopy(metadata_authority), "topology_authority": deepcopy(topology), "selected_target_authority": deepcopy(targeting)}
    if metadata_authority.get("status") != "resolved":
        return _result("rejected" if metadata_authority.get("status") == "rejected" else "incomplete", metadata_authority.get("reason", "canonical_move_target_metadata_unavailable"), common)
    metadata = metadata_authority.get("metadata")
    target_class = metadata.get("target") if isinstance(metadata, Mapping) else None
    if not isinstance(target_class, str):
        return _result("incomplete", "canonical_move_target_class_missing", common)
    if target_class not in _SUPPORTED:
        return _result("incomplete", "canonical_move_target_class_unsupported", {**common, "canonical_target_class": target_class, "recipient_classification": "unsupported"})
    rows = topology["active_owners"]
    selected = targeting["selected_target"]
    if target_class in _SELECTION_TARGETS and selected is None:
        return _result("incomplete", "selected_target_required", {**common, "canonical_target_class": target_class})
    if selected is not None and not any(_same(selected, row) for row in rows):
        return _result("rejected", "selected_target_not_active_in_doubles_topology", {**common, "canonical_target_class": target_class})
    recipients = _expand(target_class, base["acting_owner"], selected, rows)
    if recipients is None:
        return _result("rejected", "canonical_target_binding_impossible", {**common, "canonical_target_class": target_class})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "canonical_target_class": target_class,
        "recipient_classification": _classification(target_class),
        "selected_target": deepcopy(selected), "recipients": tuple(recipients),
        "provenance": "runtime_d0_exact_doubles_action_target_set_observation_v1",
    }


def _base(d0: Any, action: Any, actor: Any, decision_point: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(actor) or not isinstance(action, Mapping) or not isinstance(decision_point, str) or not decision_point:
        return None
    if actor != d0.get("decision_owner") or d0.get("active_owners", {}).get(actor.get("side")) != dict(actor):
        return None
    action_id, move_id = action.get("action_id"), action.get("identity")
    if not isinstance(action_id, str) or not action_id or not isinstance(move_id, str) or not move_id:
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "acting_owner": deepcopy(dict(actor)), "action_id": action_id, "move_id": move_id, "decision_point": decision_point}


def _doubles_format(state: Mapping[str, Any]) -> bool:
    field = state.get("field"); provenance = field.get("battle_format_provenance") if isinstance(field, Mapping) else None
    return isinstance(field, Mapping) and field.get("battle_format") == "doubles" and isinstance(provenance, Mapping) and provenance.get("event_kind") in {"session_battle_format_initialized", "current_battle_format_observed"} and provenance.get("trust") == "user_confirmed_observation"


def _topology(state: Mapping[str, Any], value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != "doubles-active-topology-context-v1" or value.get("session_id") != state.get("session_id") or not isinstance(value.get("active_owners"), list) or len(value["active_owners"]) != 4:
        return False
    rows = value["active_owners"]
    if len({(row.get("side"), row.get("slot_index")) for row in rows if isinstance(row, Mapping)}) != 4 or any(sum(isinstance(row, Mapping) and row.get("side") == side for row in rows) != 2 for side in ("self", "opponent")):
        return False
    return all(isinstance(row, Mapping) and _owner_without_active(row, state.get("session_id")) and row.get("active") is True for row in rows) and isinstance(value.get("provenance"), Mapping) and value["provenance"].get("event_kind") == "doubles_active_topology_observed" and value["provenance"].get("trust") == "user_confirmed_observation"


def _targeting(state: Mapping[str, Any], value: Any, base: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != "selected-action-targeting-context-v1" or value.get("session_id") != base["session_id"]:
        return False
    return value.get("actor") == base["acting_owner"] and all(value.get(key) == base[key] for key in ("decision_point", "action_id", "move_id")) and (value.get("selected_target") is None or _owner(value.get("selected_target"))) and isinstance(value.get("provenance"), Mapping) and value["provenance"].get("event_kind") == "selected_action_targeting_observed" and value["provenance"].get("trust") == "user_confirmed_observation"


def _expand(target_class: str, actor: Mapping[str, Any], selected: Mapping[str, Any] | None, rows: list[Mapping[str, Any]]) -> list[dict[str, Any]] | None:
    if target_class in {"selected-pokemon", "normal"}:
        if selected is None or selected.get("side") == actor.get("side"): return None
        return [_recipient(selected, actor, True)]
    if target_class == "ally":
        if selected is None or selected.get("side") != actor.get("side") or _same(selected, actor): return None
        return [_recipient(selected, actor, True)]
    if target_class == "user-or-ally":
        if selected is None or selected.get("side") != actor.get("side"): return None
        return [_recipient(selected, actor, True)]
    if target_class == "user": return [_recipient(actor, actor, False)]
    if target_class == "all-opponents": return [_recipient(row, actor, False) for row in rows if row.get("side") != actor.get("side")]
    if target_class == "user-and-allies": return [_recipient(row, actor, False) for row in rows if row.get("side") == actor.get("side")]
    if target_class == "all-other-pokemon": return [_recipient(row, actor, False) for row in rows if not _same(row, actor)]
    if target_class == "all-pokemon": return [_recipient(row, actor, False) for row in rows]
    return None


def _recipient(owner: Mapping[str, Any], actor: Mapping[str, Any], selected: bool) -> dict[str, Any]:
    relation = "self" if _same(owner, actor) else "ally" if owner.get("side") == actor.get("side") else "opponent"
    return {"side": owner["side"], "active_slot_index": owner["slot_index"], "owner": {key: owner[key] for key in _OWNER_KEYS}, "relation": relation, "selected": selected}


def _classification(value: str) -> str:
    return "single_target" if value in {"selected-pokemon", "normal"} else "ally" if value in {"ally", "user-or-ally"} else "self" if value == "user" else "self_and_ally" if value == "user-and-allies" else "spread_multi_target"


def _owner(value: Any) -> bool:
    return _owner_without_active(value, value.get("session_id") if isinstance(value, Mapping) else None)


def _owner_without_active(value: Any, session_id: Any) -> bool:
    return isinstance(value, Mapping) and set(value) in ({*_OWNER_KEYS}, {*_OWNER_KEYS, "active"}) and value.get("session_id") == session_id and isinstance(session_id, str) and bool(session_id) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _same(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in _OWNER_KEYS)


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
