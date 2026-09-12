"""Strict live producer for the bounded Taunt/Encore/Disable response families."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_runtime_d0_last_executed_move_authority import freeze_runtime_d0_last_executed_move_authority
from llm.advisor_runtime_d0_taunt_restriction_authority import freeze_runtime_d0_taunt_restriction_authority
from llm.advisor_runtime_d0_encore_restriction_authority import freeze_runtime_d0_encore_restriction_authority
from llm.advisor_runtime_d0_disable_restriction_authority import freeze_runtime_d0_disable_restriction_authority
from llm.advisor_runtime_d0_encore_locked_move_pp_authority import freeze_runtime_d0_encore_locked_move_pp_authority
from llm.advisor_detached_taunt_action_restriction import materialize_detached_taunt_application
from llm.advisor_detached_encore_action_restriction import materialize_detached_encore_application
from llm.advisor_detached_disable_action_restriction import materialize_detached_disable_application

SCHEMA_VERSION = "runtime-d0-status-special-application-authority-v1"
_FAMILIES = frozenset({"taunt", "encore", "disable"})


def freeze_runtime_d0_status_special_application_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], target_selected_action: Mapping[str, Any], canonical_move_metadata_authorities: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None: return _result("rejected", "status_special_application_binding_invalid", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current": return _result("rejected", "stale_runtime_d0", base)
    move = base["move_id"]
    accuracy = _accuracy(base, action)
    protection = _protection(base, target_selected_action)
    abilities = _target_abilities(base, runtime_snapshot, actor, target)
    reflection = _reflection(base, abilities)
    if move == "taunt":
        return materialize_detached_taunt_application(strategy_d0=strategy_d0, action=action, actor=actor, target=target, accuracy_authority=accuracy, target_ability_authority=abilities, target_side_ability_authority=abilities, protection_authority=protection, reflection_authority=reflection)
    history = freeze_runtime_d0_last_executed_move_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    if move == "encore":
        current = freeze_runtime_d0_encore_restriction_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
        meta = _last_move_metadata(base, history, target, canonical_move_metadata_authorities)
        pp = freeze_runtime_d0_encore_locked_move_pp_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target, move_id=history.get("move_id") if isinstance(history, Mapping) else "")
        return materialize_detached_encore_application(strategy_d0=strategy_d0, action=action, actor=actor, target=target, accuracy_authority=accuracy, last_used_move_authority=history, last_used_move_metadata_authority=meta, last_move_pp_authority=pp, current_encore_authority=current, target_side_ability_authority=abilities, protection_authority=protection, reflection_authority=reflection)
    current = freeze_runtime_d0_disable_restriction_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    known = _known_moves(base, runtime_snapshot, target)
    return materialize_detached_disable_application(strategy_d0=strategy_d0, action=action, actor=actor, target=target, accuracy_authority=accuracy, last_used_move_authority=history, current_known_moves_authority=known, current_disable_authority=current, target_side_ability_authority=abilities, protection_authority=protection, reflection_authority=reflection)


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(actor, Mapping) or not isinstance(target, Mapping): return None
    active = d0.get("active_owners")
    meta = action.get("metadata_authority", action.get("move_metadata_authority")); row = meta.get("metadata") if isinstance(meta, Mapping) else None
    if not isinstance(active, Mapping) or active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target) or actor.get("side") == target.get("side") or not isinstance(row, Mapping): return None
    move = row.get("move_id")
    if move not in _FAMILIES or row.get("category") != "status" or row.get("accuracy") != 100 or row.get("priority") != 0 or action.get("identity", action.get("move_id")) != move: return None
    bindings = (("session_id", "session_id"), ("source_runtime_fingerprint", "source_runtime_fingerprint"), ("source_branch_fingerprint", "strategy_preview_fingerprint"), ("decision_owner", "decision_owner"))
    if any(action.get(key) != d0[value] for key, value in bindings): return None
    if action.get("opponent_actor", action.get("active_attacker", dict(actor))) != dict(actor): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action.get("action_id"), "move_id": move}


def _authority(base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), **deepcopy(extra), "provenance": "strict_runtime_d0_status_special_application_inputs_v1"}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}


def _accuracy(base: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]: return _authority(base, outcome="hit", accuracy=100)


def _protection(base: Mapping[str, Any], target_action: Any) -> dict[str, Any]:
    meta = target_action.get("move_metadata_authority", target_action.get("metadata_authority")) if isinstance(target_action, Mapping) else None
    row = meta.get("metadata") if isinstance(meta, Mapping) else None
    if not isinstance(row, Mapping): return _result("incomplete", "status_special_target_action_metadata_missing", base)
    # A selected ordinary action is exact evidence that no concurrent
    # protection response blocks this status move. Protection selections need
    # their dedicated success authority and remain incomplete here.
    if row.get("move_id") in {"protect", "detect", "king's-shield", "kings-shield", "spiky-shield", "baneful-bunker", "burning-bulwark", "silk-trap", "obstruct"}:
        return _result("incomplete", "status_special_protection_authority_required", base)
    return _authority(base, outcome="not_applicable")


def _target_abilities(base: Mapping[str, Any], snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    def one(owner: Mapping[str, Any]) -> tuple[str | None, bool]:
        side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; row = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
        provenance = row.get("current_ability_provenance") if isinstance(row, Mapping) else None; ability = row.get("current_ability") if isinstance(row, Mapping) else None
        return (ability, isinstance(ability, str) and bool(ability) and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation")
    target_ability, target_known = one(target); actor_ability, actor_known = one(actor)
    if not target_known or not actor_known: return _result("incomplete", "status_special_current_ability_authority_missing", base)
    if "neutralizing-gas" in {target_ability, actor_ability}: return _result("incomplete", "status_special_ability_suppression_unresolved", base)
    return _authority(base, ability=target_ability)


def _reflection(base: Mapping[str, Any], abilities: Mapping[str, Any]) -> dict[str, Any]:
    if abilities.get("status") != "resolved": return _result(abilities.get("status", "incomplete"), abilities.get("reason", "status_special_ability_authority_missing"), base)
    return _authority(base, outcome="reflected" if abilities.get("ability") == "magic-bounce" else "not_applicable")


def _last_move_metadata(base: Mapping[str, Any], history: Mapping[str, Any], target: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    move = history.get("move_id") if isinstance(history, Mapping) else None; entry = catalog.get(move) if isinstance(catalog, Mapping) and isinstance(move, str) else None; row = entry.get("metadata") if isinstance(entry, Mapping) else None
    if not isinstance(row, Mapping) or row.get("move_id") != move: return _result("incomplete", "last_executed_move_metadata_missing", {**base, "owner": deepcopy(dict(target))})
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(dict(base["decision_owner"])), "owner": deepcopy(dict(target)), "metadata": deepcopy(dict(row)), "provenance": "frozen_canonical_last_move_metadata_v1"}


def _known_moves(base: Mapping[str, Any], snapshot: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None; side = state.get(f"{target['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; row = roster.get(target["slot_index"]) if isinstance(roster, Mapping) else None
    moves, provenance = (row.get("known_move_ids"), row.get("known_move_ids_provenance")) if isinstance(row, Mapping) else (None, None)
    if not isinstance(moves, list) or not isinstance(provenance, Mapping) or set(provenance) != set(moves) or any(not isinstance(x, str) or not x for x in moves) or any(not isinstance(provenance.get(x), Mapping) or provenance[x].get("trust") != "user_confirmed_observation" for x in moves): return _result("incomplete", "current_known_moves_authority_missing", {**base, "owner": deepcopy(dict(target))})
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(dict(base["decision_owner"])), "owner": deepcopy(dict(target)), "move_ids": deepcopy(moves), "moveset_completeness": "complete" if len(moves) == 4 else "partial", "provenance": "strict_runtime_d0_known_move_identity_v1"}
