"""One-action handoff adapter for Champions status/confusion opportunity owners.

The gate owns whether an action may run.  This module only binds the already
selected action to the detached selected-action executor and overlays its exact
post-action projection onto the branch snapshot for the pending action.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)


def execute_gated_selected_action(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any],
    metadata_authority: Mapping[str, Any], extension_authorities: Mapping[str, Any] | None = None,
    pending_action: Mapping[str, Any] | None = None, pending_metadata_authority: Mapping[str, Any] | None = None,
    turn_local_endure_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one permitted action and expose branch-local continuation views.

    No gate or order probability enters this adapter.  It simply selects the
    one sparse existing authority belonging to ``action_id`` and preserves the
    selected-action contract's own probability paths.
    """
    metadata = metadata_authority.get("metadata") if isinstance(metadata_authority, Mapping) else None
    if not isinstance(metadata, Mapping):
        return {"status": "rejected", "reason": "gated_selected_action_metadata_invalid"}
    family = _family_authorities(
        strategy_d0, runtime_snapshot, action, actor, target, metadata,
        metadata_authority, extension_authorities, pending_action,
        pending_metadata_authority, turn_local_endure_context,
    )
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, move_metadata=metadata, family_authorities=family,
    )
    if result.get("status") != "resolved":
        return {"status": result.get("status", "incomplete"), "reason": result.get("reason", "gated_selected_action_execution_unavailable"), "execution_result": result}
    paths = []
    for path in result.get("paths", ()):
        if not isinstance(path, Mapping) or not isinstance(path.get("probability"), Mapping):
            return {"status": "rejected", "reason": "gated_selected_action_path_invalid"}
        snapshot = _post_snapshot(runtime_snapshot, path, actor, target)
        if not isinstance(snapshot, Mapping):
            return {"status": "incomplete", "reason": "gated_selected_action_post_state_unavailable"}
        hp = _hp(snapshot, actor), _hp(snapshot, target)
        if None in hp:
            return {"status": "incomplete", "reason": "gated_selected_action_post_hp_unavailable"}
        paths.append({
            "probability": deepcopy(path["probability"]),
            "action_leaf": deepcopy(path.get("action_leaf")) if isinstance(path.get("action_leaf"), Mapping) else None,
            "native_terminal_source": deepcopy(path.get("native_terminal_source")) if isinstance(path.get("native_terminal_source"), Mapping) else None,
            "selected_action_execution": deepcopy(result),
            "selected_action_path": deepcopy(path),
            "post_action_runtime_snapshot": deepcopy(snapshot),
            "final_hp": {actor["side"]: hp[0], target["side"]: hp[1]},
        })
    if not paths:
        return {"status": "rejected", "reason": "gated_selected_action_paths_missing"}
    return {"status": "resolved", "execution_result": result, "paths": tuple(paths)}


def preceding_endure_turn_context(events: Any) -> Mapping[str, Any] | None:
    """Return only a resolved Endure setup established by the prior action.

    Gate callers use this when the later action has received its own execution
    opportunity.  A cancelled Endure never creates a selected-action path, so
    it cannot leak a survival effect into that later action.
    """
    if not isinstance(events, (tuple, list)):
        return None
    for event in reversed(events):
        path = event.get("selected_action_path") if isinstance(event, Mapping) else None
        context = path.get("endure_turn_context") if isinstance(path, Mapping) else None
        if isinstance(context, Mapping):
            return deepcopy(dict(context))
    return None


def _family_authorities(
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    metadata: Mapping[str, Any],
    metadata_authority: Mapping[str, Any],
    ext: Mapping[str, Any] | None,
    pending_action: Mapping[str, Any] | None,
    pending_metadata_authority: Mapping[str, Any] | None,
    turn_local_endure_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    ext = ext if isinstance(ext, Mapping) else {}
    action_id = action.get("action_id")
    move_id = metadata.get("move_id")
    def pick(name: str) -> Any:
        value = ext.get(name)
        if isinstance(value, Mapping) and "status" not in value:
            value = value.get(action_id)
        return deepcopy(value) if isinstance(value, Mapping) else value
    out: dict[str, Any] = {
        "sturdy_survival_authority": pick("first_action_sturdy_survival_authority"),
        "focus_sash_survival_authority": pick("first_action_focus_sash_survival_authority"),
    }
    if move_id in {"sky-attack", "razor-wind", "freeze-shock", "ice-burn"}:
        branch_action = _branch_bound_selected_action(
            strategy_d0=strategy_d0,
            action=action,
            metadata=metadata,
            metadata_authority=metadata_authority,
        )
        if isinstance(branch_action, Mapping) and branch_action.get("status") == "rejected":
            out["standard_charge_start_readiness_authority"] = branch_action
        else:
            out["standard_charge_start_readiness_authority"] = (
                freeze_runtime_d0_standard_charge_start_readiness_authority(
                    strategy_d0=strategy_d0,
                    runtime_snapshot=runtime_snapshot,
                    action=branch_action,
                    actor=actor,
                    target=target,
                )
            )
    if turn_local_endure_context is not None:
        if not isinstance(turn_local_endure_context, Mapping):
            out["endure_turn_context"] = {"status": "rejected", "reason": "gated_endure_turn_context_invalid"}
        elif turn_local_endure_context.get("endure_user") != target:
            out["endure_turn_context"] = {"status": "rejected", "reason": "gated_endure_turn_context_target_binding_mismatch"}
        else:
            out["endure_turn_context"] = deepcopy(dict(turn_local_endure_context))
    if move_id in {"recover", "slack-off", "soft-boiled"}:
        supplied = pick("direct_heal_execution_authorities")
        # The supplied record proves this exact selected move was frozen at the
        # root.  The canonical owner must still bind HP to the gate's current
        # detached branch, rather than reuse root HP after a status transition.
        if isinstance(supplied, Mapping):
            from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
            if all(supplied.get(k) == value for k, value in (("session_id", strategy_d0.get("session_id")), ("actor", actor), ("action_id", action_id), ("move_id", move_id))):
                out["direct_heal_execution_authority"] = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, actor=actor)
            else:
                out["direct_heal_execution_authority"] = {"status": "rejected", "reason": "gated_direct_heal_root_authority_binding_mismatch"}
    elif move_id == "rest":
        # Rest is its own strict, self-targeted materializer.  It must replay
        # against the gate's detached branch rather than reuse root HP/status.
        # A supplied live record is only an action-identity witness; the
        # selected-action executor rebinds the actual materialization below.
        supplied = pick("rest_execution_authorities")
        if isinstance(supplied, Mapping):
            if all(supplied.get(k) == value for k, value in (("session_id", strategy_d0.get("session_id")), ("actor", actor), ("action_id", action_id), ("move_id", "rest"))):
                out["rest_execution_authority"] = supplied
            else:
                out["rest_execution_authority"] = {"status": "rejected", "reason": "gated_rest_root_authority_binding_mismatch"}
    elif move_id in {"trick", "switcheroo"}:
        out["atomic_item_swap_execution_authority"] = pick("atomic_item_swap_status_execution_authorities")
    elif move_id in {"taunt", "encore", "disable"}:
        out["status_special_application_authority"] = pick(f"{move_id}_application_authorities")
    elif move_id in {"u-turn", "volt-switch", "flip-turn"}:
        out["pivot_replacement_authorities"] = deepcopy(ext.get("pivot_replacement_authorities"))
        out["pivot_entry_authorities"] = deepcopy(ext.get("pivot_entry_authorities"))
    elif move_id == "endure":
        from llm.advisor_runtime_d0_endure_turn_survival_authority import freeze_runtime_d0_endure_turn_survival_authority
        out["endure_turn_survival_authority"] = freeze_runtime_d0_endure_turn_survival_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, endure_user=actor, endure_action=action)
    elif move_id in {"protect", "detect", "quick-guard", "mat-block", "silk-trap", "kings-shield", "obstruct", "spiky-shield", "baneful-bunker", "burning-bulwark"}:
        out["protection_execution_result"] = _protection_setup(
            strategy_d0=strategy_d0, action=action, actor=actor, target=target, metadata=metadata,
            pending_action=pending_action, pending_metadata_authority=pending_metadata_authority, ext=ext,
        )
    return {key: value for key, value in out.items() if value is not None}



def _branch_bound_selected_action(
    *,
    strategy_d0: Mapping[str, Any],
    action: Mapping[str, Any],
    metadata: Mapping[str, Any],
    metadata_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebind immutable selected move metadata to this exact gated branch."""
    if (
        not isinstance(action, Mapping)
        or not isinstance(metadata, Mapping)
        or not isinstance(metadata_authority, Mapping)
        or metadata_authority.get("status") != "resolved"
        or metadata_authority.get("metadata") != metadata
        or action.get("identity") != metadata.get("move_id")
        or not isinstance(action.get("action_id"), str)
    ):
        return {"status": "rejected", "reason": "gated_standard_charge_move_metadata_invalid"}
    rebound = deepcopy(dict(metadata_authority))
    rebound.update({
        "status": "resolved",
        "candidate_id": action["action_id"],
        "move_id": metadata["move_id"],
        "session_id": strategy_d0.get("session_id"),
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(strategy_d0.get("decision_owner")),
        "active_attacker": deepcopy(strategy_d0.get("decision_owner")),
        "metadata": deepcopy(dict(metadata)),
        "branch_rebound_from_gated_selected_action": True,
    })
    rebound_action = deepcopy(dict(action))
    rebound_action["move_metadata_authority"] = rebound
    return rebound_action


def _protection_setup(*, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata: Mapping[str, Any], pending_action: Mapping[str, Any] | None, pending_metadata_authority: Mapping[str, Any] | None, ext: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze a protection setup without executing the authenticated pending move."""
    pending_meta = pending_metadata_authority.get("metadata") if isinstance(pending_metadata_authority, Mapping) else None
    if not isinstance(pending_action, Mapping) or not isinstance(pending_meta, Mapping) or not isinstance(pending_action.get("action_id"), str):
        return {"status": "incomplete", "reason": "protection_pending_action_context_missing"}
    base = {"session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(strategy_d0.get("decision_owner")), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action.get("action_id"), "move_id": metadata.get("move_id")}
    if any(not base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "action_id", "move_id")):
        return {"status": "rejected", "reason": "protection_setup_binding_invalid"}
    move_id = metadata["move_id"]
    if move_id == "quick-guard":
        applicability = ext.get("quick_guard_priority_applicability_authority")
        if not isinstance(applicability, Mapping): return {"status":"incomplete", "reason":"quick_guard_priority_applicability_authority_missing"}
        if applicability.get("status") != "resolved": return {"status": applicability.get("status", "incomplete"), "reason": applicability.get("reason", "quick_guard_priority_applicability_unavailable")}
        if applicability.get("guard_user") != actor or applicability.get("guard_action_id") != action["action_id"] or applicability.get("incoming_actor") != target or applicability.get("incoming_action_id") != pending_action["action_id"]:
            return {"status":"rejected", "reason":"quick_guard_setup_binding_mismatch"}
        return {"status":"resolved", **base, "pending_action_context":{"actor":deepcopy(dict(target)),"action_id":pending_action["action_id"],"move_metadata":deepcopy(dict(pending_meta))}, "protection_setup_kind":"quick_guard", "quick_guard_priority_applicability_authority":deepcopy(dict(applicability)), "pending_action_executed":False, "provenance":"gated_one_action_quick_guard_setup_v1"}
    if move_id == "mat-block":
        applicability=ext.get("mat_block_direct_damage_applicability_authority")
        if not isinstance(applicability, Mapping): return {"status":"incomplete", "reason":"mat_block_direct_damage_applicability_authority_missing"}
        if applicability.get("status") != "resolved": return {"status":applicability.get("status","incomplete"),"reason":applicability.get("reason","mat_block_direct_damage_applicability_unavailable")}
        incoming=applicability.get("incoming_action")
        if applicability.get("mat_block_user") != actor or applicability.get("mat_block_action_id") != action["action_id"] or not isinstance(incoming, Mapping) or incoming.get("action_id") != pending_action["action_id"]:
            return {"status":"rejected", "reason":"mat_block_setup_binding_mismatch"}
        return {"status":"resolved", **base, "pending_action_context":{"actor":deepcopy(dict(target)),"action_id":pending_action["action_id"],"move_metadata":deepcopy(dict(pending_meta))}, "protection_setup_kind":"mat_block", "mat_block_direct_damage_applicability_authority":deepcopy(dict(applicability)), "pending_action_executed":False, "provenance":"gated_one_action_mat_block_setup_v1"}
    success = ext.get("opponent_protection_success_authority")
    if not isinstance(success, Mapping): return {"status":"incomplete", "reason":"protection_success_authority_missing"}
    inner = success.get("protection_success_authority", success)
    if not isinstance(inner, Mapping) or inner.get("owner") != actor:
        return {"status":"rejected", "reason":"protection_success_authority_binding_mismatch"}
    deferred = {key: deepcopy(value) for key, value in ext.items() if key in {"incoming_contact_authority","silk_trap_reactive_interaction_authority","kings_shield_reactive_interaction_authority","obstruct_reactive_interaction_authority","spiky_shield_reactive_damage_authority","baneful_bunker_reactive_poison_authority","burning_bulwark_reactive_burn_authority"} and isinstance(value, Mapping)}
    return {"status":"resolved", **base, "pending_action_context":{"actor":deepcopy(dict(target)),"action_id":pending_action["action_id"],"move_metadata":deepcopy(dict(pending_meta))}, "protection_success_authority":deepcopy(dict(inner)), "deferred_reactive_authorities":deferred, "pending_action_executed":False, "provenance":"gated_one_action_protection_setup_v1"}


def consume_deferred_protection_setup(*, setup_path: Mapping[str, Any] | None, pending_action: Mapping[str, Any], pending_metadata_authority: Mapping[str, Any], pending_branch_snapshot: Mapping[str, Any], selected_path: Mapping[str, Any]) -> dict[str, Any]:
    """Apply only the deferred block decision after the pending action executes.

    The pending action's selected executor has already supplied its own action
    probability.  This adapter neither samples nor executes it; it replaces a
    proven blocked direct consequence with the branch state immediately before
    that attempt.  Reactive evidence is carried forward for the exact family
    consumer and is never applied at setup time.
    """
    setup = setup_path.get("protection_setup") if isinstance(setup_path, Mapping) else None
    if not isinstance(setup, Mapping): return {"status":"not_applicable"}
    pending = setup.get("pending_action_context")
    meta = pending_metadata_authority.get("metadata") if isinstance(pending_metadata_authority, Mapping) else None
    if not isinstance(pending, Mapping) or pending.get("action_id") != pending_action.get("action_id") or not isinstance(meta, Mapping) or pending.get("move_metadata") != meta:
        return {"status":"rejected", "reason":"deferred_protection_pending_action_binding_mismatch"}
    kind=setup.get("protection_setup_kind")
    if kind == "quick_guard":
        authority=setup.get("quick_guard_priority_applicability_authority"); blocks=isinstance(authority, Mapping) and authority.get("status")=="resolved" and authority.get("outcome")=="applies"
    elif kind == "mat_block":
        authority=setup.get("mat_block_direct_damage_applicability_authority"); blocks=isinstance(authority, Mapping) and authority.get("status")=="resolved" and authority.get("outcome")=="applies"
    else:
        success=setup.get("protection_success_authority"); blocks=isinstance(success, Mapping) and meta.get("category") in {"physical","special"} and meta.get("protection_bypass") is False
    if not blocks: return {"status":"resolved", "outcome":"not_blocked", "selected_path":deepcopy(dict(selected_path))}
    state=deepcopy(pending_branch_snapshot.get("state"))
    if not isinstance(state, Mapping): return {"status":"rejected", "reason":"deferred_protection_branch_snapshot_invalid"}
    snapshot={"status":"runtime_snapshot_ready","session_id":state.get("session_id",pending_branch_snapshot.get("session_id")),"state":state,"state_fingerprint":state_fingerprint(state)}
    actor=pending.get("actor"); target=setup.get("actor")
    ahp=_hp(snapshot, actor) if isinstance(actor, Mapping) else None; thp=_hp(snapshot,target) if isinstance(target,Mapping) else None
    if ahp is None or thp is None:return {"status":"incomplete","reason":"deferred_protection_post_block_hp_unknown"}
    # Damage/status reactive authorities are already exact lower-owner results.
    # Consume them only now, after the pending action obtained an opportunity.
    deferred = setup.get("deferred_reactive_authorities", {})
    if isinstance(deferred, Mapping):
        for key in ("spiky_shield_reactive_damage_authority", "baneful_bunker_reactive_poison_authority", "burning_bulwark_reactive_burn_authority"):
            value = deferred.get(key)
            if not isinstance(value, Mapping): continue
            if value.get("status") != "resolved" or value.get("shield_owner") != target or value.get("blocked_attacker") != actor or value.get("blocked_action_id") != pending_action.get("action_id"):
                return {"status":"rejected", "reason":"deferred_reactive_authority_binding_mismatch"}
            row=state.get(f"{actor['side']}_side",{}).get("pokemon",{}).get(actor.get("slot_index"))
            if not isinstance(row, Mapping): return {"status":"rejected","reason":"deferred_reactive_attacker_missing"}
            if key == "spiky_shield_reactive_damage_authority" and value.get("outcome") == "applies":
                hp=value.get("post_hp"); faint=value.get("fainted")
                if not isinstance(hp,int) or not isinstance(faint,bool): return {"status":"rejected","reason":"deferred_spiky_result_invalid"}
                row["current_hp"],row["fainted"]=hp,faint
            elif key in {"baneful_bunker_reactive_poison_authority","burning_bulwark_reactive_burn_authority"} and value.get("outcome") == "applies":
                condition=value.get("condition_after")
                if not isinstance(condition,str): return {"status":"rejected","reason":"deferred_reactive_condition_invalid"}
                row["condition"]=condition
        stage_row=state.get(f"{actor['side']}_side",{}).get("pokemon",{}).get(actor.get("slot_index"))
        if not isinstance(stage_row, Mapping): return {"status":"rejected","reason":"deferred_stage_attacker_missing"}
        for key, stat in (("silk_trap_reactive_interaction_authority", "speed"), ("kings_shield_reactive_interaction_authority", "attack"), ("obstruct_reactive_interaction_authority", "defense")):
            resolution=deferred.get(key)
            if not isinstance(resolution, Mapping): continue
            if resolution.get("shield_owner") != target or resolution.get("blocked_attacker") != actor or resolution.get("blocked_action_id") != pending_action.get("action_id"):
                return {"status":"rejected","reason":"deferred_stage_authority_binding_mismatch"}
            if resolution.get("outcome") not in {"applies","prevented","reversed"}: return {"status":"rejected","reason":"deferred_stage_outcome_invalid"}
            delta=resolution.get("resulting_delta")
            if not isinstance(delta,int) or isinstance(delta,bool): return {"status":"rejected","reason":"deferred_stage_delta_invalid"}
            if resolution.get("outcome") != "prevented":
                stages=stage_row.get("stat_stages")
                current=stages.get(stat) if isinstance(stages,Mapping) else None
                if not isinstance(current,int) or isinstance(current,bool) or not -6 <= current <= 6: return {"status":"incomplete","reason":"deferred_stage_current_authority_unknown"}
                stages[stat]=max(-6,min(6,current+delta))
        snapshot={"status":"runtime_snapshot_ready","session_id":state.get("session_id",pending_branch_snapshot.get("session_id")),"state":state,"state_fingerprint":state_fingerprint(state)}
        ahp=_hp(snapshot, actor); thp=_hp(snapshot,target)
    return {"status":"resolved", "outcome":"blocked", "selected_path":{**deepcopy(dict(selected_path)),"post_action_runtime_snapshot":snapshot,"final_hp":{actor["side"]:ahp,target["side"]:thp},"deferred_protection_setup":deepcopy(dict(setup)),"deferred_reactive_authorities":deepcopy(deferred) if isinstance(deferred,Mapping) else {},"pending_action_executed":True}}

def _post_snapshot(source: Mapping[str, Any], path: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any]) -> Mapping[str, Any] | None:
    explicit = path.get("post_action_runtime_snapshot")
    if isinstance(explicit, Mapping) and isinstance(explicit.get("state"), Mapping):
        return explicit
    state = deepcopy(source.get("state"))
    projection = path.get("post_action_state")
    if not isinstance(state, Mapping) or not isinstance(projection, Mapping):
        return None
    active = projection.get("active")
    if not isinstance(active, Mapping):
        return None
    for owner in (actor, target):
        part = active.get(owner.get("side"))
        row = state.get(f"{owner.get('side')}_side", {}).get("pokemon", {}).get(owner.get("slot_index"))
        if not isinstance(part, Mapping) or not isinstance(row, Mapping):
            return None
        hp = part.get("hypothetical_hp", {}).get("value")
        fainted = part.get("hypothetical_fainted", {}).get("value")
        if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(fainted, bool):
            return None
        row["current_hp"], row["fainted"] = hp, fainted
        condition = part.get("hypothetical_condition", {})
        if condition.get("status") == "known" and isinstance(condition.get("value"), str):
            row["condition"] = condition["value"]
        item = part.get("hypothetical_item", {})
        if item.get("status") == "known": row["item"] = item.get("value")
        stages = part.get("hypothetical_stages", {})
        if isinstance(stages.get("value"), Mapping): row["stages"] = deepcopy(stages["value"])
    return {"status": "runtime_snapshot_ready", "session_id": state.get("session_id", source.get("session_id")), "state": state, "state_fingerprint": state_fingerprint(state)}


def _hp(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> int | None:
    row = snapshot.get("state", {}).get(f"{owner.get('side')}_side", {}).get("pokemon", {}).get(owner.get("slot_index"))
    value = row.get("current_hp") if isinstance(row, Mapping) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
