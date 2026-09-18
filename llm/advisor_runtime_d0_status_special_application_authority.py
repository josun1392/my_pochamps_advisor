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

SCHEMA_VERSION = "runtime-d0-status-special-application-authority-v1"
_FAMILIES = frozenset({"taunt", "encore", "disable"})


def freeze_runtime_d0_status_special_application_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], target_selected_action: Mapping[str, Any], canonical_move_metadata_authorities: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    from llm.advisor_detached_taunt_action_restriction import materialize_detached_taunt_application
    from llm.advisor_detached_encore_action_restriction import materialize_detached_encore_application
    from llm.advisor_detached_disable_action_restriction import materialize_detached_disable_application
    base = _base(strategy_d0, action, actor, target)
    if base is None: return _result("rejected", "status_special_application_binding_invalid", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current": return _result("rejected", "stale_runtime_d0", base)
    move = base["move_id"]
    accuracy = _accuracy(base, action)
    protection = _protection(base, target_selected_action)
    abilities = _target_abilities(base, runtime_snapshot, actor, target)
    reflection = freeze_runtime_d0_status_special_reflection_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, actor=actor, target=target)
    if move == "taunt":
        result = materialize_detached_taunt_application(strategy_d0=strategy_d0, action=action, actor=actor, target=target, accuracy_authority=accuracy, target_ability_authority=abilities, target_side_ability_authority=abilities, protection_authority=protection, reflection_authority=reflection)
        return _preserve_reflection_evidence(result, reflection)
    history = freeze_runtime_d0_last_executed_move_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    if move == "encore":
        current = freeze_runtime_d0_encore_restriction_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
        meta = freeze_runtime_d0_status_special_last_move_metadata_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target, last_used_move_authority=history, canonical_move_metadata_authorities=canonical_move_metadata_authorities)
        pp = freeze_runtime_d0_encore_locked_move_pp_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target, move_id=history.get("move_id") if isinstance(history, Mapping) else "")
        result = materialize_detached_encore_application(strategy_d0=strategy_d0, action=action, actor=actor, target=target, accuracy_authority=accuracy, last_used_move_authority=history, last_used_move_metadata_authority=meta, last_move_pp_authority=pp, current_encore_authority=current, target_side_ability_authority=abilities, protection_authority=protection, reflection_authority=reflection)
        return _preserve_reflection_evidence(result, reflection)
    current = freeze_runtime_d0_disable_restriction_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    known = freeze_runtime_d0_status_special_current_known_moves_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    result = materialize_detached_disable_application(strategy_d0=strategy_d0, action=action, actor=actor, target=target, accuracy_authority=accuracy, last_used_move_authority=history, current_known_moves_authority=known, current_disable_authority=current, target_side_ability_authority=abilities, protection_authority=protection, reflection_authority=reflection)
    return _preserve_reflection_evidence(result, reflection)


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


def freeze_runtime_d0_status_special_current_ability_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], action_id: str, move_id: str) -> dict[str, Any]:
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or not isinstance(actor, Mapping) or not isinstance(target, Mapping):
        return _result("rejected", "status_special_ability_binding_invalid", {})
    active = strategy_d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target) or actor.get("side") == target.get("side") or not isinstance(action_id, str) or not action_id or not isinstance(move_id, str) or not move_id:
        return _result("rejected", "status_special_ability_binding_invalid", {})
    base = {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action_id, "move_id": move_id}
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    return _current_ability_authority(base, runtime_snapshot, actor, target)


def _current_ability_authority(base: Mapping[str, Any], snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    def one(owner: Mapping[str, Any]) -> tuple[str | None, Mapping[str, Any] | None, bool]:
        side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; row = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
        provenance = row.get("current_ability_provenance") if isinstance(row, Mapping) else None; ability = row.get("current_ability") if isinstance(row, Mapping) else None
        known = isinstance(ability, str) and bool(ability) and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation"
        return ability, provenance if isinstance(provenance, Mapping) else None, known
    target_ability, target_provenance, target_known = one(target); actor_ability, actor_provenance, actor_known = one(actor)
    if not target_known or not actor_known: return _result("incomplete", "status_special_current_ability_authority_missing", base)
    if "neutralizing-gas" in {target_ability, actor_ability}: return _result("incomplete", "status_special_ability_suppression_unresolved", base)
    return _authority(base, ability=target_ability, ability_provenance=deepcopy(dict(target_provenance)), actor_ability=actor_ability, actor_ability_provenance=deepcopy(dict(actor_provenance)))


def _target_abilities(base: Mapping[str, Any], snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return _current_ability_authority(base, snapshot, actor, target)


def freeze_runtime_d0_status_special_reflection_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None: return _result("rejected", "status_special_reflection_binding_invalid", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    abilities = _target_abilities(base, runtime_snapshot, actor, target)
    reflection = _reflection(base, abilities)
    if reflection.get("status") == "resolved":
        reflection["validation_request"] = {"strategy_d0": deepcopy(strategy_d0), "runtime_snapshot": deepcopy(runtime_snapshot), "action": deepcopy(action), "actor": deepcopy(actor), "target": deepcopy(target)}
    return reflection


def validate_runtime_d0_status_special_reflection_authority(authority: Any) -> dict[str, Any]:
    try:
        if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != SCHEMA_VERSION:
            raise ValueError()
        request = authority.get("validation_request")
        if not isinstance(request, Mapping):
            raise ValueError()
        expected = freeze_runtime_d0_status_special_reflection_authority(**request)
        if expected != authority:
            raise ValueError()
        return {"status": "resolved", "authority": deepcopy(dict(authority))}
    except (KeyError, TypeError, ValueError):
        return {"status": "rejected", "reason": "status_special_reflection_provenance_invalid"}


def _reflection(base: Mapping[str, Any], abilities: Mapping[str, Any]) -> dict[str, Any]:
    if abilities.get("status") != "resolved": return _result(abilities.get("status", "incomplete"), abilities.get("reason", "status_special_ability_authority_missing"), base)
    if abilities.get("ability") == "magic-bounce":
        return _authority(base, outcome="reflected", reflection_kind="ability", reflection_ability_id="magic-bounce", reflector=deepcopy(dict(base["target"])), reflector_ability_authority=deepcopy(dict(abilities)))
    return _authority(base, outcome="not_applicable", reflection_kind="none", reflection_ability_id=None, reflector=None, reflector_ability_authority=deepcopy(dict(abilities)))


def _preserve_reflection_evidence(result: Mapping[str, Any], reflection: Mapping[str, Any]) -> dict[str, Any]:
    frozen = deepcopy(dict(result))
    if reflection.get("status") == "resolved" and reflection.get("outcome") == "reflected":
        frozen["reflection_authority"] = deepcopy(dict(reflection))
    return frozen


def freeze_runtime_d0_status_special_last_move_metadata_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any], last_used_move_authority: Mapping[str, Any], canonical_move_metadata_authorities: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or not isinstance(owner, Mapping) or strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner):
        return _result("rejected", "last_executed_move_metadata_binding_invalid", {})
    base = {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "owner": deepcopy(dict(owner))}
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    if (
        not isinstance(last_used_move_authority, Mapping)
        or last_used_move_authority.get("status") != "resolved"
        or last_used_move_authority.get("owner") != dict(owner)
        or any(last_used_move_authority.get(key) != base[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner"))
    ):
        return _result("incomplete", "last_executed_move_metadata_history_unavailable", base)
    move = last_used_move_authority.get("move_id")
    entry = canonical_move_metadata_authorities.get(move) if isinstance(canonical_move_metadata_authorities, Mapping) and isinstance(move, str) else None
    row = entry.get("metadata") if isinstance(entry, Mapping) else None
    if not isinstance(row, Mapping) or row.get("move_id") != move:
        return _result("incomplete", "last_executed_move_metadata_missing", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(base), "metadata": deepcopy(dict(row)), "provenance": "frozen_canonical_last_move_metadata_v1"}


def freeze_runtime_d0_status_special_current_known_moves_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or not isinstance(owner, Mapping):
        return _result("rejected", "current_known_moves_binding_invalid", {})
    if strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner):
        return _result("rejected", "current_known_moves_binding_invalid", {})
    base = {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "owner": deepcopy(dict(owner))}
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None; side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; row = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    moves, provenance = (row.get("known_move_ids"), row.get("known_move_ids_provenance")) if isinstance(row, Mapping) else (None, None)
    if not isinstance(moves, list) or not isinstance(provenance, Mapping) or set(provenance) != set(moves) or any(not isinstance(x, str) or not x for x in moves) or any(not isinstance(provenance.get(x), Mapping) or provenance[x].get("trust") != "user_confirmed_observation" for x in moves):
        return _result("incomplete", "current_known_moves_authority_missing", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(base), "move_ids": deepcopy(moves), "moveset_completeness": "complete" if len(moves) == 4 else "partial", "provenance": "strict_runtime_d0_known_move_identity_v1"}
