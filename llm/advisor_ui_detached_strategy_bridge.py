"""Pure runtime-controller bridge for detached deterministic strategy.

The caller supplies only the existing structured selection-cycle builder.  This
module owns no UI state, mechanics, provider behavior, or ranking policy.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from llm.advisor_current_execution_authority import freeze_current_execution_authority
from llm.advisor_detached_strategy_orchestration import run_detached_strategy_orchestration
from llm.advisor_detached_opponent_response_profile import materialize_detached_opponent_response_profile
from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority
from llm.advisor_runtime_d0_quick_claw_action_order_authority import freeze_runtime_d0_quick_claw_action_order_authority
from llm.advisor_runtime_d0_focus_sash_survival_authority import freeze_runtime_d0_focus_sash_survival_authority
from llm.advisor_runtime_d0_sturdy_survival_authority import freeze_runtime_d0_sturdy_survival_authority
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from llm.advisor_runtime_d0_nonconsecutive_protection_success_authority import freeze_runtime_d0_nonconsecutive_protection_success_authority
from llm.advisor_hypothetical_protection_effects import canonical_protection_metadata
from advisor.canonical_quick_guard_protection import canonical_quick_guard_protection_metadata
from llm.advisor_runtime_d0_quick_guard_priority_applicability_authority import build_quick_guard_protection_context, freeze_runtime_d0_quick_guard_priority_applicability_authority
from advisor.canonical_mat_block_protection import canonical_mat_block_protection_metadata
from llm.advisor_runtime_d0_mat_block_active_entry_eligibility_authority import freeze_runtime_d0_mat_block_active_entry_eligibility_authority
from llm.advisor_runtime_d0_mat_block_direct_damage_applicability_authority import freeze_runtime_d0_mat_block_direct_damage_applicability_authority, freeze_runtime_d0_mat_block_incoming_bypass_authority
from llm.advisor_runtime_d0_reactive_shield_common_block_context import freeze_runtime_d0_reactive_shield_common_block_context
from llm.advisor_runtime_d0_reactive_shield_damage_status_applicability_resolution import freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution
from llm.advisor_runtime_d0_spiky_shield_reactive_damage_authority import freeze_runtime_d0_spiky_shield_reactive_damage_authority
from llm.advisor_runtime_d0_baneful_bunker_reactive_poison_authority import freeze_runtime_d0_baneful_bunker_reactive_poison_authority
from llm.advisor_runtime_d0_burning_bulwark_reactive_burn_authority import freeze_runtime_d0_burning_bulwark_reactive_burn_authority
from llm.advisor_runtime_d0_reactive_shield_stage_interaction_resolution import freeze_runtime_d0_reactive_shield_stage_interaction_resolution
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    freeze_runtime_d0_silk_trap_speed_drop_interaction_authority,
    freeze_runtime_d0_kings_shield_attack_drop_interaction_authority,
    freeze_runtime_d0_obstruct_defense_drop_interaction_authority,
)
from advisor.canonical_silk_trap_reactive_protection import canonical_silk_trap_metadata, canonical_kings_shield_metadata, canonical_obstruct_metadata
from advisor.canonical_spiky_shield_reactive_damage import canonical_spiky_shield_reactive_damage_metadata
from advisor.canonical_baneful_bunker_reactive_poison import canonical_baneful_bunker_reactive_poison_metadata
from advisor.canonical_burning_bulwark_reactive_burn import canonical_burning_bulwark_reactive_burn_metadata
from llm.advisor_live_secondary_manifest_authority import freeze_live_secondary_manifest_authority
from llm.advisor_runtime_manual_switch_entry_authority import freeze_runtime_d0_manual_switch_entry_authority
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
from llm.advisor_runtime_d0_combined_opponent_response_universe_authority import freeze_runtime_d0_combined_opponent_response_universe_authority
from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
from llm.advisor_runtime_d0_opponent_switch_response_authority import freeze_runtime_d0_opponent_switch_response_authority
from llm.advisor_exact_outcome_descriptive_metrics import project_exact_outcome_descriptive_metrics
from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger
from llm.advisor_predictive_attack_authority import build_predictive_fixed_damage_attack_authority
from llm.advisor_runtime_d0_selection_projection import (
    build_runtime_d0_selection_capture,
    freeze_runtime_d0_bound_selection_projection,
)
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_d0_probabilistic_self_stage_effect_authority,
    freeze_runtime_d0_probabilistic_target_stage_effect_authority,
    freeze_runtime_d0_thunderbolt_paralysis_authority,
    freeze_runtime_incoming_current_state_authority,
    freeze_runtime_normal_formula_predictive_input,
    freeze_runtime_strategy_d0,
    freeze_runtime_seismic_toss_predictive_input,
    freeze_runtime_strategy_selection_authority,
    resolve_runtime_d0_selectable_move_metadata_authority,
    resolve_runtime_strategy_decision_owner,
    resolve_runtime_incoming_owner,
    runtime_strategy_d0_freshness,
)
from llm.advisor_strategy_explanation import explain_detached_strategy


SCHEMA = "ui-detached-strategy-bridge-result-v1"


def run_current_ui_detached_strategy(
    *, runtime_session_manager: Any, captured_session_id: str, decision_owner: Mapping[str, Any] | None = None,
    decision_side: str = "self", selection_cycle_builder: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    opponent_canonical_move_metadata_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    opponent_move_metadata_authority_builder: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Capture one runtime revision and return detached strategy explanation.

    ``selection_cycle_builder`` receives the exact capture token and must use
    the pre-existing structured recommendation/selectability producer.  It is
    deliberately the sole UI-facing seam; no rendered strings are consumed.
    """
    capture = _capture(runtime_session_manager, captured_session_id)
    if capture is None:
        return _result("rejected", "runtime_snapshot_unavailable")
    if decision_owner is None:
        resolved_owner = resolve_runtime_strategy_decision_owner(runtime_snapshot=capture, side=decision_side)
        if resolved_owner.get("status") != "resolved":
            return _result("rejected", resolved_owner.get("reason", "runtime_decision_owner_unavailable"))
        decision_owner = resolved_owner["decision_owner"]
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=capture, decision_owner=decision_owner)
    if d0.get("status") != "resolved":
        return _result("rejected", d0.get("reason", "runtime_d0_unavailable"))
    try:
        prepared = selection_cycle_builder(build_runtime_d0_selection_capture(strategy_d0=d0), deepcopy(dict(capture)))
    except Exception:
        return _result("rejected", "selection_cycle_builder_failed")
    projection = freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=prepared)
    if projection.get("status") != "resolved":
        return _result("rejected", projection.get("reason", "runtime_selection_projection_unavailable"))
    selection = freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=projection)
    if selection.get("status") != "resolved":
        return _result("rejected", selection.get("reason", "runtime_selection_authority_unavailable"))
    incoming = []
    for action in selection.get("actions", []):
        if not isinstance(action, Mapping) or action.get("action_type") != "manual_switch" or action.get("selection") != "selectable":
            continue
        resolved = resolve_runtime_incoming_owner(
            strategy_d0=d0, runtime_snapshot=capture, pokemon_id=action.get("identity"),
        )
        if resolved.get("status") != "resolved":
            continue
        authority = freeze_runtime_incoming_current_state_authority(
            strategy_d0=d0, runtime_snapshot=capture, incoming_owner=resolved["incoming_owner"],
        )
        if authority.get("status") == "resolved":
            entry = freeze_runtime_d0_manual_switch_entry_authority(
                strategy_d0=d0, runtime_snapshot=capture, incoming_authority=authority,
            )
            incoming.append({**authority, "manual_switch_entry_authority": entry})
    execution = freeze_current_execution_authority(selection_snapshot=selection, switch_incoming=incoming)
    if execution.get("status") != "resolved":
        return _result("rejected", execution.get("reason", "runtime_execution_authority_unavailable"))
    predictive_attacks = _runtime_seismic_toss_authorities(
        strategy_d0=d0, runtime_snapshot=capture, selection=selection,
    )
    live_attacks = _runtime_live_attack_authorities(
        strategy_d0=d0, runtime_snapshot=capture, selection=selection,
    )
    orchestration_attacks = {key: value for key, value in live_attacks.items() if key != "secondary_manifest_authorities"}
    provisional = run_detached_strategy_orchestration(
        decision_state=d0["strategy_state"], decision_owner=d0["decision_owner"],
        selection_snapshot=selection, execution_bundle=execution,
        predictive_attacks=predictive_attacks,
        **orchestration_attacks,
    )
    ledgers, metrics = _project_live_ledger_metrics(
        strategy_d0=d0, orchestration=provisional, live_attacks=live_attacks,
    )
    opponent_metadata = opponent_move_metadata_authority_builder(d0, capture) if callable(opponent_move_metadata_authority_builder) else opponent_canonical_move_metadata_authorities
    response_profiles = _project_live_opponent_response_profiles(
        strategy_d0=d0, runtime_snapshot=capture, selection=selection,
        canonical_move_metadata_authorities=opponent_metadata,
    )
    orchestration = run_detached_strategy_orchestration(
        decision_state=d0["strategy_state"], decision_owner=d0["decision_owner"],
        selection_snapshot=selection, execution_bundle=execution,
        predictive_attacks=predictive_attacks, exact_outcome_ledgers=ledgers,
        descriptive_metrics=metrics, opponent_response_profiles=response_profiles, **orchestration_attacks,
    )
    if orchestration.get("status") == "rejected":
        return _result("rejected", orchestration.get("reason", "detached_orchestration_rejected"))
    explanation = explain_detached_strategy(orchestration=orchestration)
    if explanation.get("status") != "resolved":
        return _result("rejected", explanation.get("reason", "strategy_explanation_rejected"))
    current = _capture(runtime_session_manager, captured_session_id)
    if current is None or runtime_strategy_d0_freshness(strategy_d0=d0, runtime_snapshot=current).get("status") != "current":
        return _result("stale", "runtime_state_changed_strategy_result_discarded")
    return {
        "status": "resolved", "schema_version": SCHEMA,
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "strategy_preview_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "selection_completeness": deepcopy(selection["selection_completeness"]),
        "execution_coverage": deepcopy(execution["execution_coverage"]),
        "exact_outcome_ledgers": deepcopy(ledgers),
        "descriptive_metrics": deepcopy(metrics),
        "opponent_response_profiles": deepcopy(response_profiles),
        "orchestration": deepcopy(orchestration), "explanation": deepcopy(explanation),
        "provenance": "runtime_d0_detached_strategy_ui_controller_bridge_v1",
    }


def _project_live_opponent_response_profiles(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], selection: Mapping[str, Any],
    canonical_move_metadata_authorities: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Mapping[str, Any]]:
    """Compose existing response owners; absent metadata leaves own policy intact."""
    if not isinstance(canonical_move_metadata_authorities, Mapping):
        return {}
    known = freeze_runtime_d0_opponent_known_move_action_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        canonical_move_metadata_authorities=canonical_move_metadata_authorities,
    )
    move_response_set = freeze_runtime_d0_complete_opponent_response_set_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        opponent_known_move_authority=known,
    )
    switch_response_set = freeze_runtime_d0_opponent_switch_response_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    response_set = freeze_runtime_d0_combined_opponent_response_universe_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        move_response_authority=move_response_set,
        switch_response_authority=switch_response_set,
    )
    own_actions = [row for row in selection.get("actions", ()) if isinstance(row, Mapping) and row.get("action_type") == "attack" and row.get("selection") == "selectable"]
    if known.get("status") != "resolved" or response_set.get("status") != "resolved":
        status = "rejected" if "rejected" in {known.get("status"), response_set.get("status")} else "unsupported" if "unsupported" in {known.get("status"), response_set.get("status")} else "incomplete"
        reason = response_set.get("reason") or known.get("reason") or "opponent_response_authority_unavailable"
        return {row["action_id"]: {"status": status, "reason": reason} for row in own_actions if isinstance(row.get("action_id"), str)}
    by_id = {row.get("action_id"): row for row in response_set.get("actions", ()) if isinstance(row, Mapping)}
    result = {}
    for own in own_actions:
        action_id = own.get("action_id")
        if not isinstance(action_id, str):
            continue
        orders = {
            response_id: freeze_runtime_d0_action_order_authority(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                own_action=own, opponent_action=by_id.get(response_id, {}),
            )
            for response_id in response_set.get("selectable_response_action_ids", ())
            if by_id.get(response_id, {}).get("response_kind") == "move"
        }
        quick_claw_orders = {
            response_id: freeze_runtime_d0_quick_claw_action_order_authority(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own,
                opponent_action=by_id.get(response_id, {}), action_order_authority=orders[response_id],
            )
            for response_id in orders
        }
        active_owners = strategy_d0.get("active_owners")
        focus_sash_authorities = None
        response_authority_bundles = None
        if isinstance(active_owners, Mapping) and isinstance(active_owners.get("self"), Mapping) and isinstance(active_owners.get("opponent"), Mapping):
            own_metadata = resolve_runtime_d0_selectable_move_metadata_authority(
                strategy_d0=strategy_d0, action=own,
            )
            focus_sash_authorities = {
                response_id: {
                    "own_first": freeze_runtime_d0_focus_sash_survival_authority(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                        holder=active_owners["opponent"], attacker=active_owners["self"],
                        action=own, move_metadata=own_metadata.get("metadata", {}),
                    ),
                    "opponent_first": freeze_runtime_d0_focus_sash_survival_authority(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                        holder=active_owners["self"], attacker=active_owners["opponent"],
                        action=by_id[response_id], move_metadata=by_id[response_id].get("metadata_authority", {}).get("metadata", {}),
                    ),
                }
                for response_id in orders
            }
            response_authority_bundles = {}
            for response_id in orders:
                response = by_id[response_id]
                response_metadata = response.get("metadata_authority", {}).get("metadata", {})
                authorities: dict[str, Any] = {}
                if _is_damaging_metadata(own_metadata.get("metadata")) and _is_damaging_metadata(response_metadata):
                    authorities["first_action_sturdy_survival_authorities_by_order"] = {
                        "own_first": freeze_runtime_d0_sturdy_survival_authority(
                            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                            defender=active_owners["opponent"], attacker=active_owners["self"],
                            action=own, move_metadata=own_metadata.get("metadata", {}),
                        ),
                        "opponent_first": freeze_runtime_d0_sturdy_survival_authority(
                            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                            defender=active_owners["self"], attacker=active_owners["opponent"],
                            action=response, move_metadata=response_metadata,
                        ),
                    }
                if _is_direct_heal_metadata(response_metadata):
                    authorities["direct_heal_execution_authorities"] = {
                        response_id: freeze_runtime_d0_direct_heal_execution_authority(
                            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                            action=response, actor=active_owners["opponent"],
                        ),
                    }
                if canonical_protection_metadata(response_metadata.get("move_id") if isinstance(response_metadata, Mapping) else None) is not None:
                    protection = freeze_runtime_d0_nonconsecutive_protection_success_authority(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                        protection_owner=active_owners["opponent"], protection_action=response,
                    )
                    authorities["opponent_protection_success_authority"] = protection.get("protection_success_authority", protection)
                if canonical_quick_guard_protection_metadata(response_metadata.get("move_id") if isinstance(response_metadata, Mapping) else None) is not None:
                    bypass = own_metadata.get("metadata", {}).get("protection_bypass") if isinstance(own_metadata.get("metadata"), Mapping) else None
                    try:
                        context = build_quick_guard_protection_context(
                            session_id=strategy_d0["session_id"], guard_user=active_owners["opponent"], guard_action_id=response_id,
                            incoming_actor=active_owners["self"], incoming_action_id=own["action_id"], incoming_move_id=own["identity"],
                            selected_target=active_owners["opponent"], protection_authority={"status": "resolved", "owner": deepcopy(dict(active_owners["opponent"])), "metadata": {"move_id": "quick-guard"}}, protection_bypass=bypass,
                        )
                    except (TypeError, ValueError):
                        context = None
                    authorities["quick_guard_priority_applicability_authority"] = freeze_runtime_d0_quick_guard_priority_applicability_authority(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, guard_user=active_owners["opponent"], guard_action_id=response_id,
                        incoming_actor=active_owners["self"], incoming_action=own, selected_target=active_owners["opponent"], protection_context=context,
                    )
                if canonical_mat_block_protection_metadata(response_metadata.get("move_id") if isinstance(response_metadata, Mapping) else None) is not None:
                    eligibility = freeze_runtime_d0_mat_block_active_entry_eligibility_authority(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                        mat_block_user=active_owners["opponent"], mat_block_action=response,
                    )
                    own_meta = own_metadata.get("metadata") if isinstance(own_metadata.get("metadata"), Mapping) else {}
                    bypass = freeze_runtime_d0_mat_block_incoming_bypass_authority(
                        strategy_d0=strategy_d0, incoming_actor=active_owners["self"], incoming_action=own,
                        frozen_move_metadata=own_meta,
                    )
                    incoming = {"action_id": own["action_id"], "move_id": own["identity"], "category": own_meta.get("category")}
                    authorities["mat_block_direct_damage_applicability_authority"] = freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
                        eligibility_authority=eligibility, bypass_authority=bypass, incoming_action=incoming,
                        protected_recipients=(deepcopy(dict(active_owners["opponent"])),),
                    )
                if _is_canonical_reactive_shield(response_metadata.get("move_id") if isinstance(response_metadata, Mapping) else None):
                    common = freeze_runtime_d0_reactive_shield_common_block_context(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                        shield_owner=active_owners["opponent"], shield_action=response,
                        blocked_attacker=active_owners["self"], blocked_action=own,
                        frozen_move_metadata=own_metadata.get("metadata") if isinstance(own_metadata.get("metadata"), Mapping) else {},
                    )
                    authorities["reactive_shield_common_block_context"] = common
                    success = common.get("protection_success_authority") if isinstance(common, Mapping) else None
                    if isinstance(success, Mapping):
                        authorities["opponent_protection_success_authority"] = success
                    contact = common.get("contact_authority") if isinstance(common, Mapping) else None
                    if isinstance(contact, Mapping):
                        authorities["incoming_contact_authority"] = contact
                    stage_field = _stage_reactive_shield_field(response_metadata.get("move_id") if isinstance(response_metadata, Mapping) else None)
                    if stage_field is not None and isinstance(common, Mapping) and common.get("outcome") == "protection_applies_contact":
                        stage_result = freeze_runtime_d0_reactive_shield_stage_interaction_resolution(
                            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                            common_block_context=common,
                        )
                        interaction_resolution = stage_result.get("interaction_resolution") if isinstance(stage_result, Mapping) else None
                        protection = stage_result.get("protection_authority") if isinstance(stage_result, Mapping) else None
                        lower = stage_field[1](
                            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                            shield_owner=active_owners["opponent"], blocked_attacker=active_owners["self"],
                            blocked_action={"action_id": own["action_id"], "identity": own["identity"]},
                            contact_authority=contact if isinstance(contact, Mapping) else {},
                            protection_authority=protection if isinstance(protection, Mapping) else {},
                            interaction_resolution=interaction_resolution if isinstance(interaction_resolution, Mapping) else None,
                        )
                        if isinstance(lower, Mapping) and lower.get("status") == "resolved" and isinstance(interaction_resolution, Mapping):
                            authorities[stage_field[0]] = interaction_resolution
                    damage_status_field = _damage_status_reactive_shield_field(response_metadata.get("move_id") if isinstance(response_metadata, Mapping) else None)
                    if damage_status_field is not None and isinstance(common, Mapping) and common.get("outcome") == "protection_applies_contact":
                        adapter = freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(
                            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, common_block_context=common,
                        )
                        block = adapter.get("protection_block_context") if isinstance(adapter, Mapping) else None
                        applicability = adapter.get("applicability_resolution") if isinstance(adapter, Mapping) else None
                        if isinstance(block, Mapping) and isinstance(contact, Mapping):
                            lower = damage_status_field[1](
                                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                                shield_owner=active_owners["opponent"], shield_action_id=response_id,
                                blocked_attacker=active_owners["self"],
                                blocked_action={"action_id": own["action_id"], "identity": own["identity"]},
                                contact_authority=contact, protection_block_context=block,
                                applicability_resolution=applicability if isinstance(applicability, Mapping) else None,
                            )
                            if isinstance(lower, Mapping) and lower.get("status") == "resolved":
                                authorities[damage_status_field[0]] = lower
                response_authority_bundles[response_id] = {
                    "status": "resolved", "schema_version": "live-opponent-response-authority-bundle-v1",
                    "session_id": strategy_d0["session_id"],
                    "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
                    "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
                    "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
                    "own_action_id": own["action_id"], "opponent_response_action_id": response_id,
                    "ordinary_pair_authorities": authorities,
                    "provenance": "runtime_d0_live_opponent_response_sparse_authority_bundle_v1",
                }
        result[action_id] = materialize_detached_opponent_response_profile(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own,
            response_set_authority=response_set, action_order_authorities=orders,
            quick_claw_action_order_authorities=quick_claw_orders,
            **({"first_action_focus_sash_survival_authorities": focus_sash_authorities} if focus_sash_authorities is not None else {}),
            **({"response_authority_bundles": response_authority_bundles} if response_authority_bundles is not None else {}),
        )
    return result


def _is_damaging_metadata(metadata: Any) -> bool:
    return isinstance(metadata, Mapping) and metadata.get("category") in {"physical", "special"}


def _is_direct_heal_metadata(metadata: Any) -> bool:
    return isinstance(metadata, Mapping) and metadata.get("move_id") in {"recover", "slack-off", "soft-boiled"} and metadata.get("category") == "status" and metadata.get("target") == "self"


def _is_canonical_reactive_shield(move_id: Any) -> bool:
    return any(resolver(move_id) is not None for resolver in (
        canonical_silk_trap_metadata, canonical_kings_shield_metadata, canonical_obstruct_metadata,
        canonical_spiky_shield_reactive_damage_metadata, canonical_baneful_bunker_reactive_poison_metadata,
        canonical_burning_bulwark_reactive_burn_metadata,
    ))


def _stage_reactive_shield_field(move_id: Any) -> tuple[str, Callable[..., Mapping[str, Any]]] | None:
    """Return the one lower stage-consequence owner for a canonical stage shield."""
    if canonical_silk_trap_metadata(move_id) is not None:
        return ("silk_trap_reactive_interaction_authority", freeze_runtime_d0_silk_trap_speed_drop_interaction_authority)
    if canonical_kings_shield_metadata(move_id) is not None:
        return ("kings_shield_reactive_interaction_authority", freeze_runtime_d0_kings_shield_attack_drop_interaction_authority)
    if canonical_obstruct_metadata(move_id) is not None:
        return ("obstruct_reactive_interaction_authority", freeze_runtime_d0_obstruct_defense_drop_interaction_authority)
    return None


def _damage_status_reactive_shield_field(move_id: Any) -> tuple[str, Callable[..., Mapping[str, Any]]] | None:
    """Return one lower damage/status consequence owner for a canonical reactive shield."""
    if canonical_spiky_shield_reactive_damage_metadata(move_id) is not None:
        return ("spiky_shield_reactive_damage_authority", freeze_runtime_d0_spiky_shield_reactive_damage_authority)
    if canonical_baneful_bunker_reactive_poison_metadata(move_id) is not None:
        return ("baneful_bunker_reactive_poison_authority", freeze_runtime_d0_baneful_bunker_reactive_poison_authority)
    if canonical_burning_bulwark_reactive_burn_metadata(move_id) is not None:
        return ("burning_bulwark_reactive_burn_authority", freeze_runtime_d0_burning_bulwark_reactive_burn_authority)
    return None


def _capture(manager: Any, session_id: str) -> Mapping[str, Any] | None:
    if not isinstance(session_id, str) or not session_id or not callable(getattr(manager, "capture_runtime_state_snapshot", None)):
        return None
    value = manager.capture_runtime_state_snapshot(session_id)
    return value if isinstance(value, Mapping) else None


def _runtime_seismic_toss_authorities(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], selection: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    """Supply only exact runtime-produced Seismic Toss authority to orchestration."""
    target_side = "opponent" if strategy_d0["decision_owner"]["side"] == "self" else "self"
    target = strategy_d0.get("active_owners", {}).get(target_side)
    if not isinstance(target, Mapping):
        return {}
    resolved: dict[str, Mapping[str, Any]] = {}
    for action in selection.get("actions", []):
        if not isinstance(action, Mapping) or action.get("action_type") != "attack" or action.get("identity") != "seismic-toss":
            continue
        frozen = freeze_runtime_seismic_toss_predictive_input(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=strategy_d0["decision_owner"], target=target, move_id="seismic-toss",
        )
        if frozen.get("status") != "resolved":
            continue
        authority = build_predictive_fixed_damage_attack_authority(
            branch_state=strategy_d0["strategy_state"], decision_owner=strategy_d0["decision_owner"],
            target_owner=target, move_id="seismic-toss", predictive_input=frozen["predictive_input"],
        )
        if authority.get("status") == "resolved":
            resolved[action["action_id"]] = authority
    return resolved


def _runtime_live_attack_authorities(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], selection: Mapping[str, Any],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    """Build existing strict attack authorities from candidate-bound D0 metadata.

    This is a structural projection only.  It never consults prepared UI data
    or a move repository after selection metadata has been frozen at D0.
    """
    target_side = "opponent" if strategy_d0["decision_owner"]["side"] == "self" else "self"
    target = strategy_d0.get("active_owners", {}).get(target_side)
    if not isinstance(target, Mapping):
        return {}
    result: dict[str, dict[str, Mapping[str, Any]]] = {
        "normal_formula_inputs": {}, "hit_probability_authorities": {},
        "critical_hit_probability_authorities": {},
        "probabilistic_self_stage_effect_authorities": {},
        "probabilistic_target_stage_effect_authorities": {},
        "thunderbolt_paralysis_authorities": {},
        "sturdy_survival_authorities": {}, "focus_sash_survival_authorities": {},
        "secondary_manifest_authorities": {},
    }
    for action in selection.get("actions", []):
        if not isinstance(action, Mapping) or action.get("action_type") != "attack":
            continue
        candidate_id = action.get("action_id")
        metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(
            strategy_d0=strategy_d0, action=action,
        )
        if not isinstance(candidate_id, str) or metadata_authority.get("status") != "resolved":
            continue
        metadata = metadata_authority.get("metadata")
        if not isinstance(metadata, Mapping):
            continue
        result["secondary_manifest_authorities"][candidate_id] = freeze_live_secondary_manifest_authority(
            strategy_d0=strategy_d0, action=action, metadata_authority=metadata_authority,
        )
        result["sturdy_survival_authorities"][candidate_id] = freeze_runtime_d0_sturdy_survival_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            defender=target, attacker=strategy_d0["decision_owner"], action=action, move_metadata=metadata,
        )
        result["focus_sash_survival_authorities"][candidate_id] = freeze_runtime_d0_focus_sash_survival_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            holder=target, attacker=strategy_d0["decision_owner"], action=action, move_metadata=metadata,
        )
        native = build_runtime_d0_native_damage_context(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=strategy_d0["decision_owner"], target=target, move_metadata=metadata,
        )
        normal = freeze_runtime_normal_formula_predictive_input(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=strategy_d0["decision_owner"], target=target, move_metadata=metadata,
            native_damage_context=native,
        )
        if normal.get("status") == "resolved":
            result["normal_formula_inputs"][candidate_id] = normal
        hit = build_runtime_d0_strict_hit_probability_assessment(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=strategy_d0["decision_owner"], target=target, selected_move=metadata,
        )
        result["hit_probability_authorities"][candidate_id] = hit
        critical = build_runtime_d0_strict_critical_hit_probability_assessment(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=strategy_d0["decision_owner"], target=target, move_metadata=metadata,
        )
        result["critical_hit_probability_authorities"][candidate_id] = critical
        move_id = metadata.get("move_id")
        if move_id == "metal-claw":
            result["probabilistic_self_stage_effect_authorities"][candidate_id] = freeze_runtime_d0_probabilistic_self_stage_effect_authority(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=strategy_d0["decision_owner"], target=target, move_metadata=metadata,
            )
        elif move_id == "shadow-ball":
            result["probabilistic_target_stage_effect_authorities"][candidate_id] = freeze_runtime_d0_probabilistic_target_stage_effect_authority(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=strategy_d0["decision_owner"], target=target, move_metadata=metadata,
            )
        elif move_id == "thunderbolt":
            result["thunderbolt_paralysis_authorities"][candidate_id] = freeze_runtime_d0_thunderbolt_paralysis_authority(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=strategy_d0["decision_owner"], target=target, move_metadata=metadata,
            )
    return result


def _project_live_ledger_metrics(
    *, strategy_d0: Mapping[str, Any], orchestration: Mapping[str, Any], live_attacks: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    """Normalize live evidence with an explicit manifest; unavailable stays absent."""
    ledgers: dict[str, Mapping[str, Any]] = {}
    metrics: dict[str, Mapping[str, Any]] = {}
    for evidence in orchestration.get("candidates", []):
        if not isinstance(evidence, Mapping):
            continue
        candidate_id, action_type = evidence.get("candidate_id"), evidence.get("action_type")
        if not isinstance(candidate_id, str) or action_type not in {"attack", "manual_switch"}:
            continue
        candidate = {
            "candidate_id": candidate_id, "action_type": action_type,
            "session_id": strategy_d0["session_id"],
            "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
            "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        }
        if action_type == "attack":
            normal = live_attacks.get("normal_formula_inputs", {}).get(candidate_id)
            hit = live_attacks.get("hit_probability_authorities", {}).get(candidate_id)
            critical = live_attacks.get("critical_hit_probability_authorities", {}).get(candidate_id)
            if not isinstance(normal, Mapping) or not isinstance(hit, Mapping) or not isinstance(critical, Mapping):
                continue
            bindings = {
                "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
                "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
                "attacker": deepcopy(dict(strategy_d0["decision_owner"])), "target": deepcopy(dict(normal["target"])), "move_id": normal["move_id"],
            }
            secondary = _secondary_manifest_status(candidate_id, live_attacks)
            manifest = {
                "accuracy": {"status": hit.get("status", "incomplete")},
                "critical": {"status": critical.get("status", "incomplete")},
                "damage_roll": {"status": "resolved" if normal.get("status") == "resolved" else "incomplete"},
                "secondary": {"status": secondary},
            }
            consequence = evidence.get("uncertainty") if evidence.get("evidence_class") == "hit_miss_uncertainty" else None
        else:
            bindings = {
                "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
                "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
            }
            manifest = {name: {"status": "not_applicable"} for name in ("accuracy", "critical", "damage_roll", "secondary")}
            consequence = {"status": "complete", "outcome": evidence.get("outcome")} if evidence.get("evidence_class") == "exact_outcome" else None
        ledger = normalize_exact_predictive_outcome_ledger(
            candidate=candidate, predictive_consequence=consequence,
            component_manifest=manifest, bindings=bindings,
        )
        metric = project_exact_outcome_descriptive_metrics(ledger=ledger)
        ledgers[candidate_id], metrics[candidate_id] = ledger, metric
    return ledgers, metrics


def _secondary_manifest_status(candidate_id: str, live_attacks: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> str:
    classification = live_attacks.get("secondary_manifest_authorities", {}).get(candidate_id)
    if not isinstance(classification, Mapping):
        return "incomplete"
    status = classification.get("status")
    if status in {"not_applicable", "incomplete", "rejected"}:
        return status
    if status != "secondary_authority_required":
        return "rejected"
    required_map = classification.get("required_authority_map")
    authority = live_attacks.get(required_map, {}).get(candidate_id) if isinstance(required_map, str) else None
    if not isinstance(authority, Mapping):
        return "incomplete"
    return authority.get("status") if authority.get("status") in {"resolved", "incomplete", "rejected"} else "incomplete"


def _result(status: str, reason: str) -> dict[str, str]:
    return {"status": status, "schema_version": SCHEMA, "reason": reason}
