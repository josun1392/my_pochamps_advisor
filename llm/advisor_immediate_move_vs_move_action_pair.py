"""Detached, conditional immediate move-vs-move pair materialization."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_exact_equal_speed_action_order_branching import (
    materialize_exact_equal_speed_action_order_branches,
)
from llm.advisor_exact_quick_claw_action_order_branching import (
    materialize_exact_quick_claw_action_order_branches,
)
from llm.advisor_detached_intermediate_predictive_authority import (
    freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_intermediate_paralysis_second_action_authority import (
    consume_detached_sleep_freeze_execution_for_second_action,
)
from llm.advisor_detached_predictive_intermediate_state import (
    freeze_detached_actor_neutral_root_predictive_authority,
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_detached_strategy_orchestration import _normal_formula_facts
from llm.advisor_detached_deterministic_fixed_damage_attack_leaf import (
    materialize_detached_deterministic_fixed_damage_attack_leaf,
)
from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    materialize_detached_fixed_two_hit_per_hit_predictive_leaves,
)
from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger
from llm.advisor_predictive_attack_authority import build_predictive_fixed_damage_attack_authority
from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import (
    freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority,
)
from llm.advisor_hypothetical_protection_effects import (
    canonical_protection_metadata,
    prevent_supported_direct_damage,
    project_self_protection,
)
from advisor.canonical_silk_trap_reactive_protection import canonical_silk_trap_metadata, canonical_kings_shield_metadata, canonical_obstruct_metadata
from advisor.canonical_spiky_shield_reactive_damage import canonical_spiky_shield_reactive_damage_metadata
from advisor.canonical_baneful_bunker_reactive_poison import canonical_baneful_bunker_reactive_poison_metadata
from advisor.canonical_burning_bulwark_reactive_burn import canonical_burning_bulwark_reactive_burn_metadata
from advisor.canonical_quick_guard_protection import canonical_quick_guard_protection_metadata
from llm.advisor_hypothetical_silk_trap_effects import project_silk_trap_protection, project_kings_shield_protection, project_obstruct_protection, project_spiky_shield_protection, project_baneful_bunker_protection, project_burning_bulwark_protection, resolve_silk_trap_speed_effect, resolve_kings_shield_attack_effect, resolve_obstruct_defense_effect
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    freeze_runtime_d0_silk_trap_speed_drop_interaction_authority,
    freeze_runtime_d0_kings_shield_attack_drop_interaction_authority,
    freeze_runtime_d0_obstruct_defense_drop_interaction_authority,
)
from llm.advisor_runtime_d0_spiky_shield_reactive_damage_authority import (
    SCHEMA_VERSION as SPIKY_SHIELD_DAMAGE_SCHEMA_VERSION,
    materialize_detached_spiky_shield_reactive_damage,
)
from llm.advisor_runtime_d0_baneful_bunker_reactive_poison_authority import (
    SCHEMA_VERSION as BANEFUL_BUNKER_POISON_SCHEMA_VERSION,
    materialize_detached_baneful_bunker_reactive_poison,
)
from llm.advisor_runtime_d0_burning_bulwark_reactive_burn_authority import (
    SCHEMA_VERSION as BURNING_BULWARK_BURN_SCHEMA_VERSION,
    materialize_detached_burning_bulwark_reactive_burn,
)
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_d0_contact_reactive_damage_authority import (
    apply_contact_reactive_damage_to_consequences,
    contact_reactive_damage_relevance,
)
from llm.advisor_runtime_d0_contact_reactive_status_authority import (
    contact_reactive_status_branches,
    contact_reactive_status_relevance,
    freeze_runtime_d0_contact_reactive_status_authority,
)
from llm.advisor_runtime_d0_life_orb_immediate_authority import apply_life_orb_recoil_to_consequences
from llm.advisor_runtime_d0_quick_guard_priority_applicability_authority import SCHEMA_VERSION as QUICK_GUARD_SCHEMA_VERSION
from llm.advisor_runtime_d0_analytic_action_order_authority import (
    freeze_runtime_d0_analytic_action_order_authority,
)
from llm.advisor_damage_pivot_continuation import freeze_damage_pivot_continuation_authority
from llm.advisor_detached_pivot_switch_transition import materialize_detached_damage_pivot_switch
from llm.advisor_runtime_d0_mat_block_direct_damage_applicability_authority import SCHEMA_VERSION as MAT_BLOCK_SCHEMA_VERSION
from llm.advisor_detached_pure_status_action_materializer import materialize_detached_pure_status_action
from llm.advisor_predictive_critical_damage_context import materialize_predictive_critical_damage_contexts
from llm.advisor_predictive_critical_hit_uncertainty import compose_predictive_critical_hit_uncertainty
from llm.advisor_predictive_hit_miss_uncertainty import compose_predictive_hit_miss_uncertainty
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_d0_thunderbolt_paralysis_authority,
    freeze_runtime_d0_iron_head_flinch_authority,
    freeze_runtime_d0_fake_out_flinch_authority,
    freeze_runtime_d0_sparkling_aria_burn_clearing_authority,
    freeze_runtime_d0_probabilistic_self_stage_effect_authority,
    freeze_runtime_d0_probabilistic_target_stage_effect_authority,
    freeze_runtime_normal_formula_predictive_input,
    freeze_runtime_seismic_toss_predictive_input,
    resolve_runtime_d0_selectable_move_metadata_authority,
    freeze_runtime_strategy_d0,
)


SCHEMA_VERSION = "immediate-move-vs-move-action-pair-v1"
HORIZON = "immediate_action_pair"
_STATUSES = {"incomplete", "unsupported", "rejected"}


def materialize_immediate_move_vs_move_action_pair(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
    quick_claw_action_order_authority: Mapping[str, Any] | None = None,
    first_action_sturdy_survival_authority: Mapping[str, Any] | None = None,
    first_action_focus_sash_survival_authority: Mapping[str, Any] | None = None,
    opponent_protection_success_authority: Mapping[str, Any] | None = None,
    incoming_contact_authority: Mapping[str, Any] | None = None,
    silk_trap_reactive_interaction_authority: Mapping[str, Any] | None = None,
    kings_shield_reactive_interaction_authority: Mapping[str, Any] | None = None,
    obstruct_reactive_interaction_authority: Mapping[str, Any] | None = None,
    spiky_shield_reactive_damage_authority: Mapping[str, Any] | None = None,
    baneful_bunker_reactive_poison_authority: Mapping[str, Any] | None = None,
    burning_bulwark_reactive_burn_authority: Mapping[str, Any] | None = None,
    quick_guard_priority_applicability_authority: Mapping[str, Any] | None = None,
    mat_block_direct_damage_applicability_authority: Mapping[str, Any] | None = None,
    pure_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    crafty_shield_pure_status_applicability_authority: Mapping[str, Any] | None = None,
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    pivot_replacement_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    pivot_entry_authorities: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate one known-usable opponent move conditional on its selection."""
    base = _base(strategy_d0, own_action, opponent_action)
    if base is None: return _result("rejected", "invalid_pair_request", {})
    orders = _orders(action_order_authority, base, quick_claw_action_order_authority)
    if isinstance(orders, tuple): return _result(*orders, base)
    opponent_meta = _opponent_metadata(opponent_action, base)
    own_meta = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=own_action)
    if own_meta.get("status") != "resolved": return _result(_status(own_meta), own_meta.get("reason", "own_move_metadata_unavailable"), base)
    if isinstance(opponent_meta, tuple): return _result(*opponent_meta, base)
    if own_meta.get("metadata", {}).get("move_id") == "tail-whip" and opponent_meta.get("metadata", {}).get("move_id") == "crafty-shield":
        return _materialize_crafty_shield_tail_whip_pair(base=base, strategy_d0=strategy_d0, own_action=own_action, opponent_action=opponent_action, orders=orders, authorities=pure_status_execution_authorities, crafty=crafty_shield_pure_status_applicability_authority)
    if own_meta.get("metadata", {}).get("move_id") == "tail-whip" and opponent_meta.get("metadata", {}).get("move_id") == "tail-whip":
        return _materialize_tail_whip_status_pair(base=base, strategy_d0=strategy_d0, own_action=own_action, opponent_action=opponent_action, orders=orders, authorities=pure_status_execution_authorities)
    if canonical_quick_guard_protection_metadata(opponent_meta.get("metadata", {}).get("move_id") if isinstance(opponent_meta.get("metadata"), Mapping) else None) is not None:
        return _materialize_quick_guard_pair(base=base, strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_meta=own_meta, orders=orders, authority=quick_guard_priority_applicability_authority)
    if opponent_meta.get("metadata", {}).get("move_id") == "mat-block":
        return _materialize_mat_block_pair(base=base, strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_meta=own_meta, orders=orders, authority=mat_block_direct_damage_applicability_authority)
    if _is_protection_metadata(opponent_meta.get("metadata")) or any(candidate(opponent_meta.get("metadata", {}).get("move_id") if isinstance(opponent_meta.get("metadata"), Mapping) else None) is not None for candidate in (canonical_silk_trap_metadata, canonical_kings_shield_metadata, canonical_obstruct_metadata, canonical_spiky_shield_reactive_damage_metadata, canonical_baneful_bunker_reactive_poison_metadata, canonical_burning_bulwark_reactive_burn_metadata)):
        return _materialize_protection_response_pair(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
            own_meta=own_meta, opponent_meta=opponent_meta, orders=orders,
            opponent_protection_success_authority=opponent_protection_success_authority,
            incoming_contact_authority=incoming_contact_authority,
            silk_trap_reactive_interaction_authority=silk_trap_reactive_interaction_authority,
            kings_shield_reactive_interaction_authority=kings_shield_reactive_interaction_authority,
            obstruct_reactive_interaction_authority=obstruct_reactive_interaction_authority,
            spiky_shield_reactive_damage_authority=spiky_shield_reactive_damage_authority,
            baneful_bunker_reactive_poison_authority=baneful_bunker_reactive_poison_authority,
            burning_bulwark_reactive_burn_authority=burning_bulwark_reactive_burn_authority,
        )
    branches: list[dict[str, Any]] = []
    for order_plan in orders:
        materialized = _materialize_order(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
            own_action=own_action, opponent_action=opponent_action, own_meta=own_meta,
            opponent_meta=opponent_meta, order_plan=order_plan,
            action_order_authority=action_order_authority,
            first_action_sturdy_survival_authority=first_action_sturdy_survival_authority,
            first_action_focus_sash_survival_authority=first_action_focus_sash_survival_authority,
            pending_status_execution_authorities=pending_status_execution_authorities,
            pivot_replacement_authorities=pivot_replacement_authorities,
            pivot_entry_authorities=pivot_entry_authorities,
        )
        if isinstance(materialized, Mapping): return materialized
        branches.extend(materialized)
    mass = sum((_fraction(row["probability"]) for row in branches), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "pair_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {"status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
            "action_order": deepcopy(dict(action_order_authority)),
            **({"exact_action_order_branches": tuple(deepcopy(plan["source_branch"]) for plan in orders if isinstance(plan.get("source_branch"), Mapping))} if any(isinstance(plan.get("source_branch"), Mapping) for plan in orders) else {}),
            "conditional_on": "opponent_selected_exact_known_usable_move",
            "terminal_branches": tuple(branches), "terminal_probability_mass": _fd(mass),
            "aggregation": "none_preserve_first_and_second_leaf_identity",
            "provenance": "strict_detached_immediate_move_vs_move_pair_materialization_v1"}


def _materialize_tail_whip_status_pair(*, base: Mapping[str, Any], strategy_d0: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any], orders: list[Mapping[str, Any]], authorities: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    """Narrow no-damage pair branch; effects never leave the status materializer."""
    if not isinstance(authorities, Mapping): return _result("incomplete", "pure_status_execution_authorities_required", base)
    materialized: dict[str, Mapping[str, Any]] = {}
    for action, actor, target in ((own_action, base["own_actor"], base["opponent_actor"]), (opponent_action, base["opponent_actor"], base["own_actor"])):
        authority = authorities.get(action.get("action_id"))
        if not isinstance(authority, Mapping): return _result("incomplete", "pure_status_execution_authority_missing", base)
        leaf = materialize_detached_pure_status_action(execution_authority=authority)
        if leaf.get("status") != "resolved": return _result(_status(leaf), leaf.get("reason", "pure_status_materialization_unavailable"), base)
        if leaf.get("actor") != actor or leaf.get("target") != target or leaf.get("action_id") != action.get("action_id") or leaf.get("move_id") != "tail-whip": return _result("rejected", "pure_status_materialization_binding_mismatch", base)
        materialized[action["action_id"]] = leaf
    branches = []
    for plan in orders:
        first_action, second_action = (own_action, opponent_action) if plan["order"] == "own_first" else (opponent_action, own_action)
        first = _pure_status_pair_leaf(materialized[first_action["action_id"]], strategy_d0)
        second = _pure_status_pair_leaf(materialized[second_action["action_id"]], strategy_d0)
        if isinstance(first, str) or isinstance(second, str): return _result("rejected", first if isinstance(first, str) else second, base)
        branches.append(_branch(base, plan["order"], first, {}, second, second["provenance"]["attacker"], plan))
    mass = sum((_fraction(row["probability"]) for row in branches), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "pure_status_pair_probability_mass_not_one", base)
    return {"status":"evaluable", "schema_version":SCHEMA_VERSION, "horizon":HORIZON, **deepcopy(dict(base)), "action_order": {"pure_status": "external_exact_order_authority"}, "terminal_branches": tuple(branches), "terminal_probability_mass": _fd(mass), "aggregation":"none_preserve_pure_status_leaf_identity", "provenance":"strict_tail_whip_pure_status_pair_materialization_v1"}

def _materialize_crafty_shield_tail_whip_pair(*, base: Mapping[str, Any], strategy_d0: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any], orders: list[Mapping[str, Any]], authorities: Mapping[str, Mapping[str, Any]] | None, crafty: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(authorities, Mapping) or not isinstance(authorities.get(own_action.get("action_id")), Mapping): return _result("incomplete","pure_status_execution_authority_missing",base)
    if not isinstance(crafty, Mapping): return _result("incomplete","crafty_shield_applicability_authority_missing",base)
    if crafty.get("status") != "resolved": return _result(_status(crafty),crafty.get("reason","crafty_shield_applicability_unavailable"),base)
    auth=deepcopy(dict(authorities[own_action["action_id"]])); branches=[]
    for plan in orders:
        if plan["order"]=="opponent_first":
            if crafty.get("outcome") not in {"prevented","not_applicable"}: return _result("rejected","crafty_shield_outcome_invalid",base)
            if crafty.get("outcome")=="prevented": auth["accuracy_or_prevention_outcome"]="prevented";auth["prevention_authority"]=deepcopy(dict(crafty))
            status=materialize_detached_pure_status_action(execution_authority=auth)
            if status.get("status")!="resolved":return _result(_status(status),status.get("reason","pure_status_materialization_unavailable"),base)
            second=_pure_status_pair_leaf(status,strategy_d0); first=_crafty_timing_leaf(base, strategy_d0, opponent_action, None, crafty)
        else:
            status=materialize_detached_pure_status_action(execution_authority=auth)
            if status.get("status")!="resolved":return _result(_status(status),status.get("reason","pure_status_materialization_unavailable"),base)
            first=_pure_status_pair_leaf(status,strategy_d0); second=_crafty_timing_leaf(base, strategy_d0, opponent_action, first.get("consequences",{}).get("deterministic_stage_effect"), crafty)
        if isinstance(first,str) or isinstance(second,str):return _result("rejected",first if isinstance(first,str) else second,base)
        branches.append(_branch(base,plan["order"],first,{},second,base["opponent_actor"],plan))
    mass=sum((_fraction(x["probability"]) for x in branches),Fraction())
    return {"status":"evaluable","schema_version":SCHEMA_VERSION,"horizon":HORIZON,**deepcopy(dict(base)),"action_order":deepcopy(dict(crafty)),"terminal_branches":tuple(branches),"terminal_probability_mass":_fd(mass),"provenance":"strict_crafty_shield_tail_whip_pair_v1"} if mass==Fraction(1,1) else _result("rejected","crafty_shield_pair_mass_invalid",base)

def _crafty_timing_leaf(base:Mapping[str,Any], d0:Mapping[str,Any], action:Mapping[str,Any], stage:Any, crafty:Mapping[str,Any])->dict[str,Any]:
    active=d0.get("strategy_state",{}).get("active",{}); own=active.get("opponent",{}).get("current_hp"); target=active.get("self",{}).get("current_hp")
    return {"leaf_id":"crafty_shield_no_retroactive_effect","candidate_id":action["action_id"],"branch_path":("crafty_shield_no_retroactive_effect",),"probability":_fd(Fraction(1,1)),"hit_state":"not_applicable","critical_state":"not_applicable","damage_roll":"not_applicable","consequences":{"own_final_hp":own,"target_final_hp":target,"target_ko":target==0,"self_fainted":own==0,"deterministic_stage_effect":deepcopy(stage),"secondary":None,"crafty_shield_timing":"no_retroactive_effect"},"provenance":{"session_id":base["session_id"],"source_runtime_fingerprint":base["source_runtime_fingerprint"],"source_branch_fingerprint":base["source_branch_fingerprint"],"decision_owner":deepcopy(base["decision_owner"]),"attacker":deepcopy(base["opponent_actor"]),"target":deepcopy(base["own_actor"]),"move_id":"crafty-shield","crafty_shield_applicability_authority":deepcopy(dict(crafty))}}


def _pure_status_pair_leaf(materialized: Mapping[str, Any], strategy_d0: Mapping[str, Any]) -> dict[str, Any] | str:
    actor, target = materialized.get("actor"), materialized.get("target")
    active = strategy_d0.get("strategy_state", {}).get("active", {})
    own_hp = active.get(actor.get("side"), {}).get("current_hp") if isinstance(actor, Mapping) else None
    target_hp = active.get(target.get("side"), {}).get("current_hp") if isinstance(target, Mapping) else None
    if not _hp(own_hp) or not _hp(target_hp): return "pure_status_pair_hp_authority_missing"
    transition = materialized.get("stage_transition")
    if not isinstance(transition, Mapping): return "pure_status_stage_transition_missing"
    return {"leaf_id": f"{materialized['action_id']}:{materialized['outcome']}", "candidate_id": materialized["action_id"], "branch_path": (materialized["outcome"],), "probability": deepcopy(materialized["probability"]), "hit_state":"not_applicable", "critical_state":"not_applicable", "damage_roll":"not_applicable", "consequences":{"own_final_hp":own_hp,"target_final_hp":target_hp,"target_ko":target_hp==0,"self_fainted":own_hp==0,"deterministic_stage_effect":deepcopy(dict(transition)),"secondary":None,"pure_status_outcome":materialized["outcome"]}, "provenance":{"session_id":materialized["session_id"],"source_runtime_fingerprint":materialized["source_runtime_fingerprint"],"source_branch_fingerprint":materialized["source_branch_fingerprint"],"decision_owner":deepcopy(materialized["decision_owner"]),"attacker":deepcopy(actor),"target":deepcopy(target),"move_id":materialized["move_id"],"pure_status_execution_authority":deepcopy(materialized["execution_authority"])}}


def _hp(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _materialize_protection_response_pair(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any],
    own_meta: Mapping[str, Any], opponent_meta: Mapping[str, Any], orders: list[Mapping[str, Any]],
    opponent_protection_success_authority: Mapping[str, Any] | None,
    incoming_contact_authority: Mapping[str, Any] | None,
    silk_trap_reactive_interaction_authority: Mapping[str, Any] | None,
    kings_shield_reactive_interaction_authority: Mapping[str, Any] | None,
    obstruct_reactive_interaction_authority: Mapping[str, Any] | None,
    spiky_shield_reactive_damage_authority: Mapping[str, Any] | None,
    baneful_bunker_reactive_poison_authority: Mapping[str, Any] | None,
    burning_bulwark_reactive_burn_authority: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Materialize only the existing exact ordinary self-protection contract."""
    branches: list[dict[str, Any]] = []
    for plan in orders:
        if plan["order"] == "own_first":
            first = _attack_ledger(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                actor=base["own_actor"], target=base["opponent_actor"], metadata_authority=own_meta,
            )
            if first.get("status") != "evaluable":
                return _result(_status(first), f"first_action_{first.get('reason', 'ledger_unavailable')}", base)
            for leaf in first["terminal_leaves"]:
                branches.append(_protection_branch(
                    base, plan, leaf, "cancelled_due_to_faint" if leaf["consequences"].get("target_ko") is True else "executed_protection",
                ))
            continue
        protection = _resolved_protection(
            strategy_d0=strategy_d0, opponent=base["opponent_actor"], own=base["own_actor"],
            metadata=opponent_meta["metadata"], success_authority=opponent_protection_success_authority,
        )
        if protection.get("status") != "resolved":
            return _result(_status(protection), protection.get("reason", "opponent_protection_authority_unavailable"), base)
        bypass = prevent_supported_direct_damage(
            effect=protection, opponent_action={"move": _protection_targeted_attack_metadata(own_meta["metadata"])},
            protected_owner=base["opponent_actor"],
        )
        if bypass.get("status") != "resolved":
            return _result(_status(bypass), bypass.get("reason", "protection_bypass_authority_unavailable"), base)
        reactive = None
        spiky_damage = None
        baneful_poison = None
        burning_burn = None
        if canonical_silk_trap_metadata(opponent_meta["metadata"].get("move_id")) is not None:
            if isinstance(incoming_contact_authority, Mapping) and incoming_contact_authority.get("status") == "resolved" and incoming_contact_authority.get("contact_state") == "non_contact":
                interaction = None
            else:
                interaction = freeze_runtime_d0_silk_trap_speed_drop_interaction_authority(
                    strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                    shield_owner=base["opponent_actor"], blocked_attacker=base["own_actor"],
                    blocked_action={"action_id":base["own_action_id"], "identity":own_meta["metadata"].get("move_id")},
                    contact_authority=incoming_contact_authority, protection_authority=protection,
                    interaction_resolution=silk_trap_reactive_interaction_authority,
                )
                if interaction.get("status") != "resolved":
                    return _result(_status(interaction), interaction.get("reason", "silk_trap_reactive_authority_unavailable"), base)
            reactive = resolve_silk_trap_speed_effect(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, blocked_action={"action_id":base["own_action_id"],"identity":own_meta["metadata"].get("move_id")}, blocked_attacker=base["own_actor"], shield_owner=base["opponent_actor"], contact_authority=incoming_contact_authority, reactive_interaction_authority=interaction)
            if reactive.get("status") != "resolved": return _result(_status(reactive), reactive.get("reason", "silk_trap_reactive_authority_unavailable"), base)
        elif canonical_kings_shield_metadata(opponent_meta["metadata"].get("move_id")) is not None:
            if isinstance(incoming_contact_authority, Mapping) and incoming_contact_authority.get("status") == "resolved" and incoming_contact_authority.get("contact_state") == "non_contact":
                interaction = None
            else:
                interaction = freeze_runtime_d0_kings_shield_attack_drop_interaction_authority(
                    strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                    shield_owner=base["opponent_actor"], blocked_attacker=base["own_actor"],
                    blocked_action={"action_id":base["own_action_id"], "identity":own_meta["metadata"].get("move_id")},
                    contact_authority=incoming_contact_authority, protection_authority=protection,
                    interaction_resolution=kings_shield_reactive_interaction_authority,
                )
                if interaction.get("status") != "resolved": return _result(_status(interaction), interaction.get("reason", "kings_shield_reactive_authority_unavailable"), base)
            reactive = resolve_kings_shield_attack_effect(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, blocked_action={"action_id":base["own_action_id"],"identity":own_meta["metadata"].get("move_id")}, blocked_attacker=base["own_actor"], shield_owner=base["opponent_actor"], contact_authority=incoming_contact_authority, reactive_interaction_authority=interaction)
            if reactive.get("status") != "resolved": return _result(_status(reactive), reactive.get("reason", "kings_shield_reactive_authority_unavailable"), base)
        elif canonical_obstruct_metadata(opponent_meta["metadata"].get("move_id")) is not None:
            if isinstance(incoming_contact_authority, Mapping) and incoming_contact_authority.get("status") == "resolved" and incoming_contact_authority.get("contact_state") == "non_contact": interaction = None
            else:
                interaction = freeze_runtime_d0_obstruct_defense_drop_interaction_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, shield_owner=base["opponent_actor"], blocked_attacker=base["own_actor"], blocked_action={"action_id":base["own_action_id"], "identity":own_meta["metadata"].get("move_id")}, contact_authority=incoming_contact_authority, protection_authority=protection, interaction_resolution=obstruct_reactive_interaction_authority)
                if interaction.get("status") != "resolved": return _result(_status(interaction), interaction.get("reason", "obstruct_reactive_authority_unavailable"), base)
            reactive = resolve_obstruct_defense_effect(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, blocked_action={"action_id":base["own_action_id"],"identity":own_meta["metadata"].get("move_id")}, blocked_attacker=base["own_actor"], shield_owner=base["opponent_actor"], contact_authority=incoming_contact_authority, reactive_interaction_authority=interaction)
            if reactive.get("status") != "resolved": return _result(_status(reactive), reactive.get("reason", "obstruct_reactive_authority_unavailable"), base)
        elif canonical_spiky_shield_reactive_damage_metadata(opponent_meta["metadata"].get("move_id")) is not None:
            spiky_damage = _spiky_shield_reactive_damage(
                base=base, contact_authority=incoming_contact_authority,
                authority=spiky_shield_reactive_damage_authority,
            )
            if spiky_damage.get("status") != "resolved":
                return _result(_status(spiky_damage), spiky_damage.get("reason", "spiky_shield_reactive_damage_authority_unavailable"), base)
        elif canonical_baneful_bunker_reactive_poison_metadata(opponent_meta["metadata"].get("move_id")) is not None:
            baneful_poison = _baneful_bunker_reactive_poison(
                base=base, contact_authority=incoming_contact_authority,
                authority=baneful_bunker_reactive_poison_authority,
            )
            if baneful_poison.get("status") != "resolved":
                return _result(_status(baneful_poison), baneful_poison.get("reason", "baneful_bunker_reactive_poison_authority_unavailable"), base)
        elif canonical_burning_bulwark_reactive_burn_metadata(opponent_meta["metadata"].get("move_id")) is not None:
            burning_burn = _burning_bulwark_reactive_burn(
                base=base, contact_authority=incoming_contact_authority,
                authority=burning_bulwark_reactive_burn_authority,
            )
            if burning_burn.get("status") != "resolved":
                return _result(_status(burning_burn), burning_burn.get("reason", "burning_bulwark_reactive_burn_authority_unavailable"), base)
        leaf = _protection_leaf(base, strategy_d0, opponent_meta["metadata"], reactive, spiky_damage, baneful_poison, burning_burn)
        if leaf is None:
            return _result("incomplete", "exact_protection_hp_authority_missing", base)
        branches.append(_protection_branch(base, plan, leaf, "prevented_by_protection"))
    mass = sum((_fraction(row["probability"]) for row in branches), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "pair_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
        "conditional_on": "opponent_selected_exact_known_usable_move",
        "terminal_branches": tuple(branches), "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_protection_and_attack_identity",
        "provenance": "strict_detached_immediate_protection_response_pair_materialization_v1",
    }


def _materialize_quick_guard_pair(*, base: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], own_meta: Mapping[str, Any], orders: list[Mapping[str, Any]], authority: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(authority, Mapping): return _result("incomplete", "quick_guard_priority_applicability_authority_missing", base)
    expected = {"schema_version": QUICK_GUARD_SCHEMA_VERSION, "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"], "guard_user": base["opponent_actor"], "guard_action_id": base["opponent_action_id"], "guard_move_id": "quick-guard", "incoming_actor": base["own_actor"], "incoming_action_id": base["own_action_id"], "incoming_move_id": own_meta["metadata"].get("move_id"), "selected_target": base["opponent_actor"]}
    if any(authority.get(key) != value for key, value in expected.items()): return _result("rejected", "quick_guard_priority_applicability_authority_binding_mismatch", base)
    if authority.get("status") != "resolved": return _result(_status(authority), authority.get("reason", "quick_guard_priority_applicability_unavailable"), base)
    branches=[]
    for plan in orders:
        ledger=_attack_ledger(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot,actor=base["own_actor"],target=base["opponent_actor"],metadata_authority=own_meta)
        if ledger.get("status")!="evaluable": return _result(_status(ledger), "quick_guard_incoming_attack_ledger_unavailable", base)
        if plan["order"]=="opponent_first" and authority.get("outcome")=="applies":
            leaf=_protection_leaf(base,strategy_d0,{"move_id":"quick-guard"})
            if leaf is None:return _result("incomplete","quick_guard_protection_leaf_unavailable",base)
            leaf["consequences"]["quick_guard_priority_applicability"]=deepcopy(dict(authority))
            branches.append(_protection_branch(base,plan,leaf,"prevented_by_protection"))
        elif authority.get("outcome")=="not_applicable" or plan["order"]=="own_first":
            for leaf in ledger["terminal_leaves"]: branches.append(_protection_branch(base,plan,leaf,"executed_protection"))
        else:return _result("rejected","quick_guard_priority_applicability_outcome_invalid",base)
    mass=sum((_fraction(row["probability"]) for row in branches),Fraction())
    if mass!=Fraction(1,1):return _result("rejected","pair_terminal_probability_mass_not_one",base)
    return {"status":"evaluable","schema_version":SCHEMA_VERSION,"horizon":HORIZON,**base,"conditional_on":"opponent_selected_exact_known_usable_move","terminal_branches":tuple(branches),"terminal_probability_mass":_fd(mass),"aggregation":"none_preserve_quick_guard_applicability_provenance","provenance":"strict_detached_quick_guard_protection_pair_materialization_v1"}


def _materialize_mat_block_pair(*, base: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], own_meta: Mapping[str, Any], orders: list[Mapping[str, Any]], authority: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(authority, Mapping): return _result("incomplete", "mat_block_direct_damage_applicability_authority_missing", base)
    expected = {"schema_version": MAT_BLOCK_SCHEMA_VERSION, "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"], "mat_block_user": base["opponent_actor"], "mat_block_action_id": base["opponent_action_id"], "mat_block_move_id": "mat-block"}
    if any(authority.get(key) != value for key, value in expected.items()): return _result("rejected", "mat_block_direct_damage_applicability_authority_binding_mismatch", base)
    incoming = authority.get("incoming_action")
    if not isinstance(incoming, Mapping) or incoming.get("action_id") != base["own_action_id"] or incoming.get("move_id") != own_meta["metadata"].get("move_id"): return _result("rejected", "mat_block_incoming_action_binding_mismatch", base)
    if authority.get("status") != "resolved": return _result(_status(authority), authority.get("reason", "mat_block_direct_damage_applicability_unavailable"), base)
    recipients = authority.get("protected_recipients")
    if not isinstance(recipients, tuple) or base["opponent_actor"] not in recipients: return _result("rejected", "mat_block_protected_target_binding_mismatch", base)
    branches=[]
    for plan in orders:
        ledger=_attack_ledger(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot,actor=base["own_actor"],target=base["opponent_actor"],metadata_authority=own_meta)
        if ledger.get("status")!="evaluable": return _result(_status(ledger), "mat_block_incoming_attack_ledger_unavailable", base)
        if plan["order"]=="opponent_first" and authority.get("outcome")=="applies":
            leaf=_protection_leaf(base,strategy_d0,{"move_id":"mat-block"})
            if leaf is None:return _result("incomplete","mat_block_protection_leaf_unavailable",base)
            leaf["consequences"]["mat_block_direct_damage_applicability"]=deepcopy(dict(authority))
            branches.append(_protection_branch(base,plan,leaf,"prevented_by_mat_block"))
        elif authority.get("outcome")=="not_applicable" or plan["order"]=="own_first":
            for leaf in ledger["terminal_leaves"]: branches.append(_protection_branch(base,plan,leaf,"executed_protection"))
        else:return _result("rejected","mat_block_direct_damage_applicability_outcome_invalid",base)
    mass=sum((_fraction(row["probability"]) for row in branches),Fraction())
    if mass!=Fraction(1,1):return _result("rejected","pair_terminal_probability_mass_not_one",base)
    return {"status":"evaluable","schema_version":SCHEMA_VERSION,"horizon":HORIZON,**base,"conditional_on":"opponent_selected_exact_known_usable_move","terminal_branches":tuple(branches),"terminal_probability_mass":_fd(mass),"aggregation":"none_preserve_mat_block_applicability_provenance","provenance":"strict_detached_mat_block_protection_pair_materialization_v1"}


def _resolved_protection(*, strategy_d0: Mapping[str, Any], opponent: Mapping[str, Any], own: Mapping[str, Any], metadata: Mapping[str, Any], success_authority: Mapping[str, Any] | None) -> dict[str, Any]:
    action = {"owner": deepcopy(dict(opponent)), "move": {"move_id": metadata.get("move_id"), "category": metadata.get("category"), "target": metadata.get("target"), "accuracy": metadata.get("accuracy")}}
    branch = deepcopy(dict(strategy_d0["strategy_state"]))
    active = branch.get("active")
    row = active.get("opponent") if isinstance(active, dict) else None
    if not isinstance(row, Mapping) or any(row.get(key) != opponent.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")):
        return _result("rejected", "protection_actor_neutral_branch_identity_mismatch", {})
    active["self"] = deepcopy(dict(active["opponent"]))
    if canonical_silk_trap_metadata(metadata.get("move_id")) is not None:
        return project_silk_trap_protection(branch_state=branch, action=action, owner=opponent, success_authority=success_authority or {})
    if canonical_kings_shield_metadata(metadata.get("move_id")) is not None:
        return project_kings_shield_protection(branch_state=branch, action=action, owner=opponent, success_authority=success_authority or {})
    if canonical_obstruct_metadata(metadata.get("move_id")) is not None:
        return project_obstruct_protection(branch_state=branch, action=action, owner=opponent, success_authority=success_authority or {})
    if canonical_spiky_shield_reactive_damage_metadata(metadata.get("move_id")) is not None:
        return project_spiky_shield_protection(branch_state=branch, action=action, owner=opponent, success_authority=success_authority or {})
    if canonical_baneful_bunker_reactive_poison_metadata(metadata.get("move_id")) is not None:
        return project_baneful_bunker_protection(branch_state=branch, action=action, owner=opponent, success_authority=success_authority or {})
    if canonical_burning_bulwark_reactive_burn_metadata(metadata.get("move_id")) is not None:
        return project_burning_bulwark_protection(branch_state=branch, action=action, owner=opponent, success_authority=success_authority or {})
    return project_self_protection(
        branch_state=branch, action=action,
        expected_owner=opponent, success_authority=success_authority or {},
    )


def _protection_targeted_attack_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {"category": metadata.get("category"), "protection_bypass": metadata.get("protection_bypass")}


def _is_protection_metadata(metadata: Any) -> bool:
    return isinstance(metadata, Mapping) and canonical_protection_metadata(metadata.get("move_id")) is not None


def _protection_leaf(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], metadata: Mapping[str, Any], reactive: Mapping[str, Any] | None = None, spiky_damage: Mapping[str, Any] | None = None, baneful_poison: Mapping[str, Any] | None = None, burning_burn: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    active = strategy_d0.get("strategy_state", {}).get("active", {})
    own_hp = active.get("self", {}).get("current_hp") if isinstance(active, Mapping) else None
    opponent_hp = active.get("opponent", {}).get("current_hp") if isinstance(active, Mapping) else None
    if not isinstance(own_hp, int) or isinstance(own_hp, bool) or own_hp < 0 or not isinstance(opponent_hp, int) or isinstance(opponent_hp, bool) or opponent_hp < 0:
        return None
    reactive_post_hp = spiky_damage.get("post_hp") if isinstance(spiky_damage, Mapping) and spiky_damage.get("outcome") == "applies" else own_hp
    if not isinstance(reactive_post_hp, int) or isinstance(reactive_post_hp, bool) or reactive_post_hp < 0:
        return None
    return {
        "leaf_id": "protect:success", "candidate_id": f"protection:{metadata['move_id']}",
        "action_type": "protection", "branch_path": ("protect:success",),
        "probability": _fd(Fraction(1, 1)), "hit_state": "not_applicable",
        "critical_state": "not_applicable", "damage_roll": "not_applicable",
        "consequences": {
            "own_final_hp": opponent_hp, "target_final_hp": reactive_post_hp,
            "target_ko": reactive_post_hp == 0, "self_fainted": opponent_hp == 0,
            "deterministic_stage_effect": deepcopy(reactive.get("effect")) if isinstance(reactive, Mapping) and reactive.get("applies") is True else None,
            "silk_trap_reactive_consequence": deepcopy(reactive) if isinstance(reactive, Mapping) else None,
            "spiky_shield_reactive_damage": deepcopy(spiky_damage) if isinstance(spiky_damage, Mapping) else None,
            "baneful_bunker_reactive_poison": deepcopy(baneful_poison) if isinstance(baneful_poison, Mapping) else None,
            "burning_bulwark_reactive_burn": deepcopy(burning_burn) if isinstance(burning_burn, Mapping) else None,
            "reactive_shield_condition_transition": deepcopy(baneful_poison.get("transition")) if isinstance(baneful_poison, Mapping) and baneful_poison.get("outcome") == "applies" else deepcopy(burning_burn.get("transition")) if isinstance(burning_burn, Mapping) and burning_burn.get("outcome") == "applies" else None,
            "secondary": None,
        },
        "provenance": {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(dict(base["decision_owner"])), "attacker": deepcopy(dict(base["opponent_actor"])), "target": deepcopy(dict(base["own_actor"])), "move_id": metadata["move_id"]},
    }


def _spiky_shield_reactive_damage(*, base: Mapping[str, Any], contact_authority: Mapping[str, Any] | None, authority: Mapping[str, Any] | None) -> dict[str, Any]:
    """Consume only a frozen Spiky Shield result; pair code never recalculates it."""
    if not isinstance(authority, Mapping):
        return {"status": "incomplete", "reason": "spiky_shield_reactive_damage_authority_missing"}
    expected = {
        "schema_version": SPIKY_SHIELD_DAMAGE_SCHEMA_VERSION,
        "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"],
        "shield_owner": base["opponent_actor"], "shield_action_id": base["opponent_action_id"],
        "shield_move_id": "spiky-shield", "blocked_attacker": base["own_actor"],
        "blocked_action_id": base["own_action_id"],
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        return {"status": "rejected", "reason": "spiky_shield_reactive_damage_authority_binding_mismatch"}
    if authority.get("status") != "resolved":
        return {"status": _status(authority), "reason": authority.get("reason", "spiky_shield_reactive_damage_authority_unavailable")}
    if not isinstance(contact_authority, Mapping) or authority.get("blocked_move_id") != contact_authority.get("move_id"):
        return {"status": "rejected", "reason": "spiky_shield_blocked_move_identity_mismatch"}
    if authority.get("contact_authority") != contact_authority:
        return {"status": "rejected", "reason": "spiky_shield_contact_provenance_mismatch"}
    if authority.get("outcome") == "not_applicable":
        return {"status": "resolved", "outcome": "not_applicable", "authority": deepcopy(dict(authority))}
    if authority.get("outcome") != "applies":
        return {"status": "rejected", "reason": "spiky_shield_reactive_damage_outcome_invalid"}
    overlay = materialize_detached_spiky_shield_reactive_damage(authority=authority)
    if overlay.get("status") != "resolved":
        return {"status": _status(overlay), "reason": overlay.get("reason", "spiky_shield_reactive_damage_overlay_invalid")}
    if overlay.get("owner") != base["own_actor"]:
        return {"status": "rejected", "reason": "spiky_shield_reactive_damage_overlay_owner_mismatch"}
    return {"status": "resolved", "outcome": "applies", "post_hp": overlay["hypothetical_hp_authority"]["current_hp"], "fainted": overlay["hypothetical_fainted_authority"]["value"], "authority": deepcopy(dict(authority)), "overlay": overlay}


def _baneful_bunker_reactive_poison(*, base: Mapping[str, Any], contact_authority: Mapping[str, Any] | None, authority: Mapping[str, Any] | None) -> dict[str, Any]:
    """Consume one frozen Baneful Bunker result; pair code never resolves eligibility."""
    if not isinstance(authority, Mapping):
        return {"status": "incomplete", "reason": "baneful_bunker_reactive_poison_authority_missing"}
    expected = {
        "schema_version": BANEFUL_BUNKER_POISON_SCHEMA_VERSION,
        "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"],
        "shield_owner": base["opponent_actor"], "shield_action_id": base["opponent_action_id"],
        "shield_move_id": "baneful-bunker", "blocked_attacker": base["own_actor"],
        "blocked_action_id": base["own_action_id"],
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        return {"status": "rejected", "reason": "baneful_bunker_reactive_poison_authority_binding_mismatch"}
    if authority.get("status") != "resolved":
        return {"status": _status(authority), "reason": authority.get("reason", "baneful_bunker_reactive_poison_authority_unavailable")}
    if not isinstance(contact_authority, Mapping) or authority.get("blocked_move_id") != contact_authority.get("move_id"):
        return {"status": "rejected", "reason": "baneful_bunker_blocked_move_identity_mismatch"}
    if authority.get("contact_authority") != contact_authority:
        return {"status": "rejected", "reason": "baneful_bunker_contact_provenance_mismatch"}
    overlay = materialize_detached_baneful_bunker_reactive_poison(authority=authority)
    if overlay.get("status") != "resolved":
        return {"status": _status(overlay), "reason": overlay.get("reason", "baneful_bunker_reactive_poison_overlay_invalid")}
    if overlay.get("owner") != base["own_actor"]:
        return {"status": "rejected", "reason": "baneful_bunker_reactive_poison_overlay_owner_mismatch"}
    if authority.get("outcome") == "not_applicable":
        if overlay.get("transition_applied") is not False:
            return {"status": "rejected", "reason": "baneful_bunker_no_effect_transition_invalid"}
        return {"status": "resolved", "outcome": "not_applicable", "authority": deepcopy(dict(authority)), "overlay": overlay}
    transition = overlay.get("hypothetical_condition_authority")
    if authority.get("outcome") != "applies" or overlay.get("transition_applied") is not True or not isinstance(transition, Mapping) or transition.get("status") != "known_present" or transition.get("condition") != "poison" or transition.get("condition_before") != "known_none" or transition.get("condition_after") != "poison" or transition.get("trigger") != "baneful_bunker_successful_blocked_contact":
        return {"status": "rejected", "reason": "baneful_bunker_reactive_poison_transition_invalid"}
    return {"status": "resolved", "outcome": "applies", "transition": deepcopy(dict(transition)), "authority": deepcopy(dict(authority)), "overlay": overlay}


def _burning_bulwark_reactive_burn(*, base: Mapping[str, Any], contact_authority: Mapping[str, Any] | None, authority: Mapping[str, Any] | None) -> dict[str, Any]:
    """Consume one frozen Burning Bulwark result; pair code never resolves eligibility."""
    if not isinstance(authority, Mapping):
        return {"status": "incomplete", "reason": "burning_bulwark_reactive_burn_authority_missing"}
    expected = {
        "schema_version": BURNING_BULWARK_BURN_SCHEMA_VERSION,
        "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"],
        "shield_owner": base["opponent_actor"], "shield_action_id": base["opponent_action_id"],
        "shield_move_id": "burning-bulwark", "blocked_attacker": base["own_actor"],
        "blocked_action_id": base["own_action_id"],
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        return {"status": "rejected", "reason": "burning_bulwark_reactive_burn_authority_binding_mismatch"}
    if authority.get("status") != "resolved":
        return {"status": _status(authority), "reason": authority.get("reason", "burning_bulwark_reactive_burn_authority_unavailable")}
    if not isinstance(contact_authority, Mapping) or authority.get("blocked_move_id") != contact_authority.get("move_id"):
        return {"status": "rejected", "reason": "burning_bulwark_blocked_move_identity_mismatch"}
    if authority.get("contact_authority") != contact_authority:
        return {"status": "rejected", "reason": "burning_bulwark_contact_provenance_mismatch"}
    overlay = materialize_detached_burning_bulwark_reactive_burn(authority=authority)
    if overlay.get("status") != "resolved":
        return {"status": _status(overlay), "reason": overlay.get("reason", "burning_bulwark_reactive_burn_overlay_invalid")}
    if overlay.get("owner") != base["own_actor"]:
        return {"status": "rejected", "reason": "burning_bulwark_reactive_burn_overlay_owner_mismatch"}
    if authority.get("outcome") == "not_applicable":
        if overlay.get("transition_applied") is not False:
            return {"status": "rejected", "reason": "burning_bulwark_no_effect_transition_invalid"}
        return {"status": "resolved", "outcome": "not_applicable", "authority": deepcopy(dict(authority)), "overlay": overlay}
    transition = overlay.get("hypothetical_condition_authority")
    if authority.get("outcome") != "applies" or overlay.get("transition_applied") is not True or not isinstance(transition, Mapping) or transition.get("status") != "known_present" or transition.get("condition") != "burn" or transition.get("condition_before") != "known_none" or transition.get("condition_after") != "burn" or transition.get("trigger") != "burning_bulwark_successful_blocked_contact":
        return {"status": "rejected", "reason": "burning_bulwark_reactive_burn_transition_invalid"}
    return {"status": "resolved", "outcome": "applies", "transition": deepcopy(dict(transition)), "authority": deepcopy(dict(authority)), "overlay": overlay}


def _protection_branch(base: Mapping[str, Any], plan: Mapping[str, Any], first: Mapping[str, Any], state: str) -> dict[str, Any]:
    order_probability = plan["probability"]
    source = plan.get("source_branch")
    return {
        "pair_leaf_id": (f"{source['order_branch_id']}/" if isinstance(source, Mapping) else "") + f"{first['leaf_id']}/second_{state}",
        "action_order": plan["order"],
        **({"action_order_branch": deepcopy(dict(source)), "action_order_conditional_probability": _fd(order_probability)} if isinstance(source, Mapping) else {}),
        "first_action_leaf": deepcopy(dict(first)), "intermediate_state_id": None,
        "second_action": {"state": state, "actor": deepcopy(dict(base["opponent_actor"] if plan["order"] == "own_first" else base["own_actor"])), "conditional_probability": _fd(Fraction(1, 1)), "reason": state},
        "probability": _fd(order_probability * _fraction(first["probability"])), "provenance": deepcopy(dict(base)),
    }


def _materialize_order(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    base: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    own_meta: Mapping[str, Any], opponent_meta: Mapping[str, Any], order_plan: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
    first_action_sturdy_survival_authority: Mapping[str, Any] | None,
    first_action_focus_sash_survival_authority: Mapping[str, Any] | None,
    pending_status_execution_authorities: Mapping[str, Mapping[str, Any]] | None,
    pivot_replacement_authorities: Mapping[str, Mapping[str, Any]] | None,
    pivot_entry_authorities: Mapping[str, Mapping[str, Any]] | None,
) -> list[dict[str, Any]] | dict[str, Any]:
    order = order_plan["order"]
    first_actor = base["own_actor"] if order == "own_first" else base["opponent_actor"]
    first_meta = own_meta if order == "own_first" else opponent_meta
    first_d0, first_snapshot, root = strategy_d0, runtime_snapshot, None
    if order == "opponent_first":
        root = freeze_detached_actor_neutral_root_predictive_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, opponent_action=opponent_action)
        if root.get("status") != "resolved": return _result(_status(root), root.get("reason", "opponent_root_predictive_authority_unavailable"), base)
        first_d0, first_snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
    first_action = own_action if order == "own_first" else opponent_action
    first_analytic = _analytic_order_authority(
        strategy_d0=first_d0, actor=first_actor, target=base["opponent_actor"] if first_actor == base["own_actor"] else base["own_actor"],
        base=base, plan=order_plan, source_action_order_authority=action_order_authority,
    ) if first_actor == base["own_actor"] else None
    first = _attack_ledger(strategy_d0=first_d0, runtime_snapshot=first_snapshot, actor=first_actor,
                                   target=base["opponent_actor"] if first_actor == base["own_actor"] else base["own_actor"], metadata_authority=first_meta,
                                   sturdy_survival_authority=first_action_sturdy_survival_authority,
                                   focus_sash_survival_authority=first_action_focus_sash_survival_authority, action=first_action,
                                   analytic_action_order_authority=first_analytic)
    if first.get("status") != "evaluable": return _result(_status(first), f"first_action_{first.get('reason', 'ledger_unavailable')}", base, first_action_ledger=first)
    branches: list[dict[str, Any]] = []
    second_actor = base["opponent_actor"] if order == "own_first" else base["own_actor"]
    second_meta = opponent_meta if order == "own_first" else own_meta
    second_action_id = opponent_action.get("action_id") if order == "own_first" else own_action.get("action_id")
    for leaf in first["terminal_leaves"]:
        intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=strategy_d0, terminal_leaf=leaf, root_predictive_authority=root)
        if intermediate.get("status") != "resolved": return _result(_status(intermediate), intermediate.get("reason", "intermediate_state_unavailable"), base)
        # A self-switching damaging move changes the defensive owner for the
        # already-selected opposing action.  This belongs after the complete
        # terminal leaf (including recoil/contact consequences), before the
        # ordinary second-action actor/target handoff.
        if order == "own_first":
            pivot = freeze_damage_pivot_continuation_authority(
                strategy_d0=strategy_d0, action=own_action,
                move_metadata=own_meta["metadata"], attack_terminal_leaf=leaf,
                replacement_authority=(pivot_replacement_authorities or {}).get(leaf["leaf_id"]),
            )
            if pivot.get("status") == "applies":
                precursor = freeze_detached_intermediate_predictive_authority(
                    strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
                    intermediate_state=intermediate, actor=first_actor, target=second_actor,
                    move_metadata_authority=own_meta,
                )
                if precursor.get("status") != "resolved": return _result(_status(precursor), precursor.get("reason", "pivot_post_attack_authority_unavailable"), base, first_leaf_id=leaf["leaf_id"])
                switched = materialize_detached_damage_pivot_switch(intermediate_authority=precursor, pivot_authority=pivot, entry_authority=(pivot_entry_authorities or {}).get(leaf["leaf_id"]))
                if switched.get("status") != "resolved": return _result(_status(switched), switched.get("reason", "pivot_switch_transition_unavailable"), base, first_leaf_id=leaf["leaf_id"])
                incoming = switched.get("resulting_active_owner")
                post_snapshot = switched.get("runtime_snapshot")
                if not isinstance(incoming, Mapping) or not isinstance(post_snapshot, Mapping): return _result("rejected", "pivot_post_switch_target_missing", base, first_leaf_id=leaf["leaf_id"])
                if _fainted(intermediate, second_actor):
                    branches.append(_branch(base, order, leaf, intermediate, None, second_actor, order_plan, pivot_transition=switched)); continue
                post_d0 = freeze_runtime_strategy_d0(runtime_snapshot=post_snapshot, decision_owner=second_actor)
                if post_d0.get("status") != "resolved": return _result(_status(post_d0), post_d0.get("reason", "pivot_post_switch_d0_unavailable"), base, first_leaf_id=leaf["leaf_id"])
                second = _attack_ledger(strategy_d0=post_d0, runtime_snapshot=post_snapshot, actor=second_actor, target=_owner_identity(incoming),
                    metadata_authority=opponent_meta, action=opponent_action)
                if second.get("status") != "evaluable": return _result(_status(second), f"second_action_{second.get('reason', 'ledger_unavailable')}", base, first_leaf_id=leaf["leaf_id"])
                for second_leaf in second["terminal_leaves"]:
                    branches.append(_branch(base, order, leaf, intermediate, second_leaf, second_actor, order_plan, pivot_transition=switched))
                continue
            if pivot.get("status") in {"incomplete", "rejected"} and own_meta["metadata"].get("move_id") in {"u-turn", "volt-switch", "flip-turn"}:
                return _result(_status(pivot), pivot.get("reason", "pivot_continuation_unavailable"), base, first_leaf_id=leaf["leaf_id"])
        if _fainted(intermediate, second_actor):
            branches.append(_branch(base, order, leaf, intermediate, None, second_actor, order_plan)); continue
        if _fainted(intermediate, first_actor):
            branches.append(_branch(base, order, leaf, intermediate, None, second_actor, order_plan)); continue
        flinch = _pending_second_action_flinch(intermediate, second_actor)
        if isinstance(flinch, str):
            return _result("rejected", flinch, base, first_leaf_id=leaf["leaf_id"])
        if flinch:
            branches.append(_branch(base, order, leaf, intermediate, None, second_actor, order_plan, {
                "execution_branch_id": "second_action:flinched", "state": "cancelled_due_to_flinch",
                "conditional_probability": _fd(Fraction(1, 1)), "reason": "second_action_cancelled_due_to_flinch",
            }))
            continue
        authority = freeze_detached_intermediate_predictive_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            intermediate_state=intermediate, actor=second_actor,
            target=base["opponent_actor"] if second_actor == base["own_actor"] else base["own_actor"], move_metadata_authority=second_meta)
        paralysis = consume_detached_sleep_freeze_execution_for_second_action(
            intermediate_predictive_authority=authority,
            pending_action_id=second_action_id,
            pending_status_execution_authority=(pending_status_execution_authorities or {}).get(second_action_id) if isinstance(second_action_id, str) else None,
        )
        if paralysis.get("status") != "resolved": return _result(_status(paralysis), paralysis.get("reason", "second_action_intermediate_authority_unavailable"), base, first_leaf_id=leaf["leaf_id"])
        inputs = paralysis["builder_inputs"]
        execution = paralysis.get("second_action_execution_branches")
        if not isinstance(execution, tuple) or not execution: return _result("rejected", "second_action_execution_branches_invalid", base, first_leaf_id=leaf["leaf_id"])
        if any(not _execution_branch(row) for row in execution) or sum((_fraction(row["conditional_probability"]) for row in execution), Fraction()) != Fraction(1, 1):
            return _result("rejected", "second_action_execution_branch_mass_invalid", base, first_leaf_id=leaf["leaf_id"])
        executable = [row for row in execution if isinstance(row, Mapping) and row.get("state") == "executed"]
        second = None
        if executable:
            second_analytic = _analytic_order_authority(
                strategy_d0=inputs["strategy_d0"], actor=inputs["attacker"], target=inputs["target"], base=base, plan=order_plan, source_action_order_authority=action_order_authority,
            ) if second_actor == base["own_actor"] else None
            second = _attack_ledger(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"],
                actor=inputs["attacker"], target=inputs["target"], metadata_authority=_metadata_for_inputs(second_meta, inputs), action=opponent_action if order == "own_first" else own_action,
                analytic_action_order_authority=second_analytic)
            if second.get("status") != "evaluable": return _result(_status(second), f"second_action_{second.get('reason', 'ledger_unavailable')}", base, first_leaf_id=leaf["leaf_id"])
        for execution_branch in execution:
            if execution_branch["state"] == "cancelled_due_to_paralysis":
                branches.append(_branch(base, order, leaf, intermediate, None, second_actor, order_plan, execution_branch)); continue
            for second_leaf in second["terminal_leaves"]:
                branches.append(_branch(base, order, leaf, intermediate, second_leaf, second_actor, order_plan, execution_branch))
    return branches


def _attack_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata_authority: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None = None, focus_sash_survival_authority: Mapping[str, Any] | None = None, action: Mapping[str, Any] | None = None, analytic_action_order_authority: Mapping[str, Any] | None = None, stakeout_switch_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    metadata = _metadata_for_inputs(metadata_authority, None)
    if metadata is None: return _result("rejected", "predictive_move_metadata_authority_invalid", {})
    if metadata.get("move_id") == "seismic-toss":
        return _seismic_toss_ledger(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, actor=actor, target=target, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority)
    if metadata.get("move_id") in {"double-hit", "double-kick"}:
        return _fixed_two_hit_ledger(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, actor=actor,
            target=target, metadata_authority=metadata_authority,
            sturdy_survival_authority=sturdy_survival_authority,
            focus_sash_survival_authority=focus_sash_survival_authority,
            action=action,
            analytic_action_order_authority=analytic_action_order_authority,
            stakeout_switch_authority=stakeout_switch_authority,
        )
    return _normal_formula_ledger(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, actor=actor, target=target, metadata_authority=metadata, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority, action=action, analytic_action_order_authority=analytic_action_order_authority, stakeout_switch_authority=stakeout_switch_authority)


def _fixed_two_hit_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata_authority: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None, focus_sash_survival_authority: Mapping[str, Any] | None = None, action: Mapping[str, Any] | None = None, analytic_action_order_authority: Mapping[str, Any] | None = None, stakeout_switch_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Adapt already-validated canonical metadata to the fixed-two-hit owner.

    This is only a tagged D0-local selection view.  It neither looks up move
    data nor promotes the detached actor-neutral D0 to current authority.
    """
    metadata = _metadata_for_inputs(metadata_authority, None)
    opposing_side = "opponent" if isinstance(actor, Mapping) and actor.get("side") == "self" else "self"
    if metadata is None or actor != strategy_d0.get("decision_owner") or target != strategy_d0.get("active_owners", {}).get(opposing_side):
        return _result("rejected", "fixed_two_hit_predictive_role_or_metadata_invalid", {})
    action_id = f"attack:{metadata['move_id']}"
    projection = {
        "status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1",
        "candidate_id": action_id, "move_id": metadata["move_id"], "metadata": deepcopy(dict(metadata)),
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "active_attacker": deepcopy(dict(strategy_d0["decision_owner"])),
        "provenance": "strict_detached_pair_metadata_to_fixed_two_hit_d0_selection_view_v1",
    }
    action = {"action_id": action_id, "action_type": "attack", "identity": metadata["move_id"], "move_metadata_authority": projection}
    relevance = contact_reactive_damage_relevance(runtime_snapshot=runtime_snapshot, defender=target)
    if relevance.get("status") != "resolved":
        return _result(_status(relevance), relevance.get("reason", "fixed_two_hit_contact_reactive_relevance_unknown"), {})
    status_relevance = contact_reactive_status_relevance(runtime_snapshot=runtime_snapshot, defender=target)
    if status_relevance.get("status") != "resolved":
        return _result(_status(status_relevance), status_relevance.get("reason", "fixed_two_hit_contact_reactive_status_relevance_unknown"), {})
    contact = None
    if relevance.get("relevant") is True or status_relevance.get("relevant") is True:
        contact = freeze_runtime_d0_canonical_contact_classification_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action, attacker=actor, target=target,
        )
        if contact.get("status") not in {"resolved"}:
            return _result(_status(contact), contact.get("reason", "fixed_two_hit_contact_authority_unavailable"), {})
    execution = freeze_runtime_d0_fixed_two_hit_multi_hit_execution_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
    )
    if execution.get("status") != "resolved":
        return _result(_status(execution), execution.get("reason", "fixed_two_hit_execution_authority_unavailable"), {})
    leaves = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        execution_authority=execution, sturdy_survival_authority=sturdy_survival_authority,
        focus_sash_survival_authority=focus_sash_survival_authority,
        contact_reactive_contact_authority=contact,
        analytic_action_order_authority=analytic_action_order_authority,
        stakeout_switch_authority=stakeout_switch_authority,
    )
    if leaves.get("status") != "evaluable":
        return _result(_status(leaves), leaves.get("reason", "fixed_two_hit_terminal_leaves_unavailable"), {})
    return leaves


def _seismic_toss_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None = None, focus_sash_survival_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    frozen = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=actor, target=target, move_id="seismic-toss",
    )
    if frozen.get("status") != "resolved": return _result(_status(frozen), frozen.get("reason", "fixed_damage_predictive_input_unavailable"), {})
    authority = build_predictive_fixed_damage_attack_authority(
        branch_state=strategy_d0["strategy_state"], decision_owner=actor, target_owner=target,
        move_id="seismic-toss", predictive_input=frozen["predictive_input"],
    )
    leaf = materialize_detached_deterministic_fixed_damage_attack_leaf(
        strategy_d0=strategy_d0, attacker=actor, target=target,
        move_id="seismic-toss", predictive_authority=authority,
        sturdy_survival_authority=sturdy_survival_authority,
        focus_sash_survival_authority=focus_sash_survival_authority,
    )
    if leaf.get("status") != "evaluable": return _result(_status(leaf), leaf.get("reason", "fixed_damage_terminal_leaf_unavailable"), {})
    action = {"action_id": "attack:seismic-toss", "action_type": "attack", "identity": "seismic-toss"}
    move = {"move_id": "seismic-toss", "category": "physical", "damage": "level"}
    updated = []
    for row in leaf["terminal_leaves"]:
        consequences = row.get("consequences", {})
        applied = apply_life_orb_recoil_to_consequences(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target,
            source_action=action, move_metadata=move,
            qualifying_damage=isinstance(consequences.get("damage"), int) and consequences["damage"] > 0,
            consequences=consequences,
        )
        if applied.get("status") != "resolved":
            return _result(_status(applied), applied.get("reason", "fixed_damage_life_orb_recoil_unavailable"), {})
        updated_row = deepcopy(dict(row)); updated_row["consequences"] = applied["consequences"]; updated.append(updated_row)
    result = deepcopy(dict(leaf)); result["terminal_leaves"] = tuple(updated); return result


def _normal_formula_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata_authority: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None = None, focus_sash_survival_authority: Mapping[str, Any] | None = None, action: Mapping[str, Any] | None = None, analytic_action_order_authority: Mapping[str, Any] | None = None, stakeout_switch_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    metadata = _metadata_for_inputs(metadata_authority, None)
    if metadata is None: return _result("rejected", "predictive_move_metadata_authority_invalid", {})
    sparkling_aria = None
    if metadata["move_id"] == "sparkling-aria":
        sparkling_aria = freeze_runtime_d0_sparkling_aria_burn_clearing_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=actor, target=target, move_metadata=metadata,
        )
        if sparkling_aria.get("status") != "resolved":
            return _result(_status(sparkling_aria), sparkling_aria.get("reason", "sparkling_aria_burn_clearing_authority_unavailable"), {})
    native = build_runtime_d0_native_damage_context(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata, sparkling_aria_burn_clearing_authority=sparkling_aria, analytic_action_order_authority=analytic_action_order_authority, stakeout_switch_authority=stakeout_switch_authority)
    normal = freeze_runtime_normal_formula_predictive_input(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata, native_damage_context=native)
    hit = build_runtime_d0_strict_hit_probability_assessment(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, selected_move=metadata)
    crit = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata)
    source_action = action if isinstance(action, Mapping) else {"action_id": f"attack:{metadata['move_id']}", "action_type": "attack", "identity": metadata["move_id"]}
    if any(row.get("status") != "resolved" for row in (normal, hit, crit)):
        row = next(row for row in (normal, hit, crit) if row.get("status") != "resolved")
        return _result(_status(row), row.get("reason", "normal_formula_predictive_authority_unavailable"), {})
    relevance = contact_reactive_damage_relevance(runtime_snapshot=runtime_snapshot, defender=target)
    if relevance.get("status") != "resolved":
        return _result(_status(relevance), relevance.get("reason", "contact_reactive_relevance_unknown"), {})
    status_relevance = contact_reactive_status_relevance(runtime_snapshot=runtime_snapshot, defender=target)
    if status_relevance.get("status") != "resolved":
        return _result(_status(status_relevance), status_relevance.get("reason", "contact_reactive_status_relevance_unknown"), {})
    contact = None
    if relevance.get("relevant") is True or status_relevance.get("relevant") is True:
        contact = freeze_runtime_d0_canonical_contact_classification_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=source_action, attacker=actor, target=target)
        if contact.get("status") != "resolved":
            return _result(_status(contact), contact.get("reason", "contact_authority_unavailable"), {})
    thunderbolt = None
    iron_head_flinch = None
    fake_out_flinch = None
    self_stage = None
    target_stage = None
    if metadata["move_id"] == "thunderbolt":
        thunderbolt = freeze_runtime_d0_thunderbolt_paralysis_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=actor, target=target, move_metadata=metadata,
        )
        if thunderbolt.get("status") != "resolved":
            return _result(_status(thunderbolt), thunderbolt.get("reason", "thunderbolt_paralysis_authority_unavailable"), {})
    if metadata["move_id"] == "iron-head":
        iron_head_flinch = freeze_runtime_d0_iron_head_flinch_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=actor, target=target, move_metadata=metadata,
        )
        if iron_head_flinch.get("status") != "resolved":
            return _result(_status(iron_head_flinch), iron_head_flinch.get("reason", "iron_head_flinch_authority_unavailable"), {})
    if metadata["move_id"] == "fake-out":
        if not isinstance(action, Mapping): return _result("incomplete", "fake_out_action_identity_required", {})
        fake_out_flinch = freeze_runtime_d0_fake_out_flinch_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata, fake_out_action=action)
        if fake_out_flinch.get("status") == "ineligible": fake_out_flinch = None
        elif fake_out_flinch.get("status") != "resolved": return _result(_status(fake_out_flinch), fake_out_flinch.get("reason", "fake_out_flinch_authority_unavailable"), {})
    if metadata["move_id"] == "metal-claw":
        self_stage = freeze_runtime_d0_probabilistic_self_stage_effect_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=actor, target=target, move_metadata=metadata,
        )
        if self_stage.get("status") != "resolved":
            return _result(_status(self_stage), self_stage.get("reason", "metal_claw_self_stage_authority_unavailable"), {})
    if metadata["move_id"] == "shadow-ball":
        target_stage = freeze_runtime_d0_probabilistic_target_stage_effect_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            attacker=actor, target=target, move_metadata=metadata,
        )
        if target_stage.get("status") != "resolved":
            return _result(_status(target_stage), target_stage.get("reason", "shadow_ball_target_stage_authority_unavailable"), {})
    candidate = {"candidate_id": f"attack:{metadata['move_id']}", "action_type": "attack", "session_id": strategy_d0["session_id"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"]))}
    own_hp = strategy_d0["strategy_state"]["active"][actor["side"]]["current_hp"]
    interval_input = {"snapshot_damage_input": normal["snapshot_damage_input"], "stat_provenance": normal["stat_provenance"], "trusted_level": normal["trusted_level"]}
    paired = materialize_predictive_critical_damage_contexts(branch_state=strategy_d0["strategy_state"], decision_owner=actor, target_owner=target, source_runtime_fingerprint=strategy_d0["source_runtime_fingerprint"], **interval_input)
    if paired.get("status") != "resolved": return _result(_status(paired), paired.get("reason", "critical_damage_context_unavailable"), {})
    post_input = {"move_metadata": metadata, **normal["post_hit_authority"], "target_sturdy_survival_authority": sturdy_survival_authority, "target_focus_sash_survival_authority": focus_sash_survival_authority}
    non = _normal_formula_facts(candidate, paired["non_critical_context"], own_hp, post_input, normal,
        probabilistic_self_stage_effect_authority=self_stage,
        probabilistic_target_stage_effect_authority=target_stage,
        thunderbolt_paralysis_authority=thunderbolt, iron_head_flinch_authority=iron_head_flinch or fake_out_flinch, sparkling_aria_burn_clearing_authority=sparkling_aria, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority)
    critical = _normal_formula_facts(candidate, paired["critical_context"], own_hp, post_input, normal,
        probabilistic_self_stage_effect_authority=self_stage,
        probabilistic_target_stage_effect_authority=target_stage,
        thunderbolt_paralysis_authority=thunderbolt, iron_head_flinch_authority=iron_head_flinch or fake_out_flinch, sparkling_aria_burn_clearing_authority=sparkling_aria, sturdy_survival_authority=sturdy_survival_authority, focus_sash_survival_authority=focus_sash_survival_authority)
    if any(isinstance(authority, Mapping) and authority.get("status") == "ready" for authority in (sturdy_survival_authority, focus_sash_survival_authority)):
        failed = next((fact.get("post_hit_failure") for fact in (non, critical) if isinstance(fact.get("post_hit_failure"), Mapping)), None)
        if failed is not None:
            return _result(_status(failed), failed.get("reason", "survival_post_hit_authority_unavailable"), {})
    non_consequences = _consequences(paired["non_critical_context"], non)
    critical_consequences = _consequences(paired["critical_context"], critical)
    critical = compose_predictive_critical_hit_uncertainty(candidate=candidate, strict_critical_hit_probability=crit, paired_damage_contexts=paired, non_critical_consequences=non_consequences, critical_consequences=critical_consequences)
    if critical.get("status") != "resolved": return _result(_status(critical), critical.get("reason", "critical_uncertainty_unavailable"), {})
    hit_consequences = {"critical_hit_uncertainty": critical, "guaranteed_facts": critical["guaranteed_facts"]}
    uncertainty = compose_predictive_hit_miss_uncertainty(candidate=candidate, strict_hit_probability=hit, hit_consequences=hit_consequences,
        miss_baseline={"attacker_current_hp": own_hp, "target_current_hp": strategy_d0["strategy_state"]["active"][target["side"]]["current_hp"]})
    if uncertainty.get("status") != "resolved": return _result(_status(uncertainty), uncertainty.get("reason", "hit_miss_uncertainty_unavailable"), {})
    bindings = {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "attacker": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "move_id": metadata["move_id"]}
    ledger = normalize_exact_predictive_outcome_ledger(candidate=candidate, predictive_consequence=uncertainty,
        component_manifest={"accuracy": {"status": "resolved"}, "critical": {"status": "resolved"}, "damage_roll": {"status": "resolved"}, "secondary": {"status": "resolved" if any(item is not None for item in (thunderbolt, iron_head_flinch, fake_out_flinch, sparkling_aria, self_stage, target_stage)) else "not_applicable"}}, bindings=bindings)
    ledger = _apply_contact_reactive_to_normal_ledger(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, ledger=ledger,
        attacker=actor, defender=target, source_action=source_action, contact_authority=contact,
    )
    ledger = _apply_contact_reactive_status_to_normal_ledger(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, ledger=ledger,
        attacker=actor, defender=target, source_action=source_action, contact_authority=contact,
    )
    return _apply_life_orb_to_normal_ledger(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, ledger=ledger,
        attacker=actor, target=target, source_action=source_action, move_metadata=metadata,
    )


def _apply_contact_reactive_to_normal_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], ledger: Mapping[str, Any], attacker: Mapping[str, Any], defender: Mapping[str, Any], source_action: Mapping[str, Any], contact_authority: Mapping[str, Any] | None) -> dict[str, Any]:
    if ledger.get("status") != "evaluable":
        return deepcopy(dict(ledger))
    if contact_authority is None:
        return deepcopy(dict(ledger))
    leaves = ledger.get("terminal_leaves")
    if not isinstance(leaves, tuple):
        return _result("rejected", "contact_reactive_normal_ledger_leaves_invalid", {})
    updated = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return _result("rejected", "contact_reactive_normal_leaf_invalid", {})
        if leaf.get("hit_state") != "hit":
            updated.append(deepcopy(dict(leaf))); continue
        consequences = leaf.get("consequences")
        source_hit = consequences.get("source_hit_context") if isinstance(consequences, Mapping) else None
        if isinstance(source_hit, Mapping):
            source_hit = {**deepcopy(dict(source_hit)), "source_action_id": source_action["action_id"], "source_move_id": source_action["identity"]}
        result = apply_contact_reactive_damage_to_consequences(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=attacker, defender=defender,
            source_action=source_action, contact_authority=contact_authority, source_hit=source_hit or {},
            consequences=consequences or {},
        )
        if result.get("status") != "resolved":
            return _result(_status(result), result.get("reason", "contact_reactive_damage_unavailable"), {})
        row = deepcopy(dict(leaf)); row["consequences"] = result["consequences"]; updated.append(row)
    result = deepcopy(dict(ledger)); result["terminal_leaves"] = tuple(updated)
    result["component_manifest"] = {**deepcopy(dict(result.get("component_manifest", {}))), "contact_reactive_damage": {"status": "resolved"}}
    return result


def _apply_contact_reactive_status_to_normal_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], ledger: Mapping[str, Any], attacker: Mapping[str, Any], defender: Mapping[str, Any], source_action: Mapping[str, Any], contact_authority: Mapping[str, Any] | None) -> dict[str, Any]:
    if ledger.get("status") != "evaluable":
        return deepcopy(dict(ledger))
    if contact_authority is None:
        return deepcopy(dict(ledger))
    leaves = ledger.get("terminal_leaves")
    if not isinstance(leaves, tuple):
        return _result("rejected", "contact_reactive_status_normal_ledger_leaves_invalid", {})
    updated = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return _result("rejected", "contact_reactive_status_normal_leaf_invalid", {})
        if leaf.get("hit_state") != "hit":
            updated.append(deepcopy(dict(leaf))); continue
        consequences = leaf.get("consequences")
        source_hit = consequences.get("source_hit_context") if isinstance(consequences, Mapping) else None
        if isinstance(source_hit, Mapping):
            source_hit = {**deepcopy(dict(source_hit)), "source_action_id": source_action["action_id"], "source_move_id": source_action["identity"]}
        authority = freeze_runtime_d0_contact_reactive_status_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=attacker, defender=defender,
            source_action=source_action, contact_authority=contact_authority, source_hit=source_hit or {},
            attacker_fainted_authority={"status": "known", "value": bool(isinstance(consequences, Mapping) and consequences.get("self_fainted") is True)},
        )
        if authority.get("status") != "resolved":
            return _result(_status(authority), authority.get("reason", "contact_reactive_status_unavailable"), {})
        if authority.get("outcome") != "applies":
            row = deepcopy(dict(leaf))
            row["consequences"] = {**deepcopy(dict(consequences or {})), "contact_reactive_status": {"outcome": authority["outcome"], "authority": deepcopy(dict(authority)), "overlay": None}}
            updated.append(row)
            continue
        for branch in contact_reactive_status_branches(authority=authority):
            overlay = branch.get("overlay")
            if not isinstance(overlay, Mapping) or overlay.get("status") != "resolved":
                return _result("rejected", "contact_reactive_status_overlay_invalid", {})
            row = _multiply_leaf_probability(leaf, branch["factor"], f"contact_reactive_status:{branch['branch']}")
            row["consequences"] = {**deepcopy(dict(consequences or {})), "contact_reactive_status": {"outcome": "applies", "branch": branch["branch"], "authority": deepcopy(dict(authority)), "overlay": deepcopy(dict(overlay))}}
            updated.append(row)
    result = deepcopy(dict(ledger)); result["terminal_leaves"] = tuple(updated)
    result["component_manifest"] = {**deepcopy(dict(result.get("component_manifest", {}))), "contact_reactive_status": {"status": "resolved"}}
    return result


def _multiply_leaf_probability(leaf: Mapping[str, Any], factor: Fraction, branch_name: str) -> dict[str, Any]:
    result = deepcopy(dict(leaf))
    current = _fraction(result.get("probability"))
    probability = current * factor
    result["probability"] = _fd(probability)
    result["leaf_id"] = f"{result['leaf_id']}/{branch_name}"
    branch_path = result.get("branch_path")
    if isinstance(branch_path, tuple):
        result["branch_path"] = branch_path + ({"branch": branch_name, "conditional_probability": _fd(factor)},)
    conditional = result.get("conditional_factors")
    if isinstance(conditional, tuple):
        result["conditional_factors"] = conditional + (_fd(factor),)
    return result


def _apply_life_orb_to_normal_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], ledger: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], source_action: Mapping[str, Any], move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    if ledger.get("status") != "evaluable":
        return deepcopy(dict(ledger))
    leaves = ledger.get("terminal_leaves")
    if not isinstance(leaves, tuple):
        return _result("rejected", "life_orb_normal_ledger_leaves_invalid", {})
    updated = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return _result("rejected", "life_orb_normal_leaf_invalid", {})
        if leaf.get("hit_state") != "hit":
            updated.append(deepcopy(dict(leaf))); continue
        consequences = leaf.get("consequences")
        applied = apply_life_orb_recoil_to_consequences(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=attacker, target=target,
            source_action=source_action, move_metadata=move_metadata,
            qualifying_damage=isinstance(consequences, Mapping) and isinstance(consequences.get("damage"), int) and consequences["damage"] > 0,
            consequences=consequences or {},
        )
        if applied.get("status") != "resolved":
            return _result(_status(applied), applied.get("reason", "life_orb_recoil_unavailable"), {})
        row = deepcopy(dict(leaf)); row["consequences"] = applied["consequences"]; updated.append(row)
    result = deepcopy(dict(ledger)); result["terminal_leaves"] = tuple(updated)
    result["component_manifest"] = {**deepcopy(dict(result.get("component_manifest", {}))), "life_orb": {"status": "resolved"}}
    return result


def _consequences(interval: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    return {"interval": interval, "post_hit": facts.get("post_hit"), "stage_effects": facts.get("stage_effects"), "damage_roll_uncertainty": facts.get("damage_roll_uncertainty"), "probabilistic_self_stage_effect_uncertainty": facts.get("probabilistic_self_stage_effect_uncertainty"), "probabilistic_target_stage_effect_uncertainty": facts.get("probabilistic_target_stage_effect_uncertainty"), "thunderbolt_paralysis_uncertainty": facts.get("thunderbolt_paralysis_uncertainty"), "iron_head_flinch_uncertainty": facts.get("iron_head_flinch_uncertainty"), "sparkling_aria_burn_clearing_uncertainty": facts.get("sparkling_aria_burn_clearing_uncertainty"), "guaranteed_facts": facts}

def _base(d0: Any, own: Any, opponent: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(own, Mapping) or own.get("action_type") != "attack" or not isinstance(own.get("action_id"), str): return None
    self_owner, opp_owner = d0.get("active_owners", {}).get("self"), d0.get("active_owners", {}).get("opponent")
    if not isinstance(self_owner, Mapping) or not isinstance(opp_owner, Mapping) or d0.get("decision_owner") != self_owner: return None
    return {"pair_id": f"pair:{own['action_id']}:{opponent.get('action_id') if isinstance(opponent, Mapping) else None}", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "own_action_id": own["action_id"], "opponent_action_id": opponent.get("action_id") if isinstance(opponent, Mapping) else None, "own_actor": deepcopy(dict(self_owner)), "opponent_actor": deepcopy(dict(opp_owner))}
def _orders(value: Any, base: Mapping[str, Any], quick_claw_authority: Mapping[str, Any] | None = None) -> list[dict[str, Any]] | tuple[str, str]:
    if not isinstance(value, Mapping) or value.get("schema_version") != "runtime-d0-action-order-authority-v1": return ("rejected", "action_order_authority_invalid")
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor"):
        if value.get(key) != base.get(key): return ("rejected", "action_order_binding_mismatch")
    if value.get("status") != "resolved": return (_status(value), value.get("reason", "action_order_unavailable"))
    if quick_claw_authority is not None:
        quick = _quick_claw_orders(quick_claw_authority, base)
        if isinstance(quick, tuple): return quick
        if quick is not None: return quick
    return _base_orders(value, base)


def _base_orders(value: Mapping[str, Any], base: Mapping[str, Any]) -> list[dict[str, Any]] | tuple[str, str]:
    if value.get("order") in {"own_first", "opponent_first"}:
        return [{"order": value["order"], "probability": Fraction(1, 1), "source_branch": None}]
    if value.get("order") != "unresolved_tie": return ("incomplete", "action_order_unavailable")
    branching = materialize_exact_equal_speed_action_order_branches(action_order_authority=value)
    if branching.get("status") != "resolved": return (_status(branching), branching.get("reason", "equal_speed_order_branching_unavailable"))
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor"):
        if branching.get(key) != base.get(key): return ("rejected", "equal_speed_order_branching_binding_mismatch")
    rows = branching.get("order_branches")
    if not isinstance(rows, tuple) or len(rows) != 2: return ("rejected", "equal_speed_order_branches_invalid")
    plans: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("order") not in {"own_first", "opponent_first"} or not isinstance(row.get("order_branch_id"), str):
            return ("rejected", "equal_speed_order_branch_invalid")
        try: probability = _fraction(row["conditional_probability"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError): return ("rejected", "equal_speed_order_probability_invalid")
        if probability != Fraction(1, 2): return ("rejected", "equal_speed_order_probability_not_one_half")
        plans.append({"order": row["order"], "probability": probability, "source_branch": deepcopy(dict(row))})
    if {plan["order"] for plan in plans} != {"own_first", "opponent_first"}: return ("rejected", "equal_speed_order_branches_not_exhaustive")
    return plans


def _quick_claw_orders(value: Mapping[str, Any], base: Mapping[str, Any]) -> list[dict[str, Any]] | tuple[str, str] | None:
    if value.get("schema_version") != "runtime-d0-quick-claw-action-order-authority-v1": return ("rejected", "quick_claw_action_order_authority_invalid")
    if any(value.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")): return ("rejected", "quick_claw_action_order_authority_binding_mismatch")
    if value.get("status") != "resolved": return (_status(value), value.get("reason", "quick_claw_action_order_unavailable"))
    if value.get("outcome") == "known_no_effect": return None
    if value.get("outcome") != "applicable": return ("rejected", "quick_claw_action_order_outcome_invalid")
    materialized = materialize_exact_quick_claw_action_order_branches(quick_claw_authority=value)
    if materialized.get("status") != "resolved": return (_status(materialized), materialized.get("reason", "quick_claw_order_branching_unavailable"))
    rows = materialized.get("order_branches")
    if not isinstance(rows, tuple) or len(rows) not in {2, 3}: return ("rejected", "quick_claw_order_branches_invalid")
    plans = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("order") not in {"own_first", "opponent_first"} or row.get("mechanic") != "quick_claw" or not isinstance(row.get("order_branch_id"), str): return ("rejected", "quick_claw_order_branch_invalid")
        probability = _fraction(row.get("conditional_probability"))
        if probability <= 0: return ("rejected", "quick_claw_order_probability_invalid")
        plans.append({"order": row["order"], "probability": probability, "source_branch": deepcopy(dict(row))})
    if sum((plan["probability"] for plan in plans), Fraction()) != Fraction(1, 1): return ("rejected", "quick_claw_order_branch_mass_invalid")
    return plans
def _opponent_metadata(action: Any, base: Mapping[str, Any]) -> Mapping[str, Any] | tuple[str, str]:
    if not isinstance(action, Mapping) or action.get("status") != "resolved": return (_status(action) if isinstance(action, Mapping) else "rejected", action.get("reason", "opponent_action_invalid") if isinstance(action, Mapping) else "opponent_action_invalid")
    if action.get("selectability") != "selectable" or action.get("usability", {}).get("status") != "known_usable": return ("incomplete", "opponent_action_not_known_usable")
    if any(action.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) or action.get("action_id") != base.get("opponent_action_id"): return ("rejected", "opponent_action_binding_mismatch")
    meta = action.get("metadata_authority")
    if not isinstance(meta, Mapping) or meta.get("status") != "resolved": return (_status(meta) if isinstance(meta, Mapping) else "rejected", "opponent_move_metadata_unavailable")
    return {"status": "resolved", "move_id": action.get("move_id"), "metadata": deepcopy(meta.get("metadata")), "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(dict(base["decision_owner"]))}
def _metadata_for_inputs(authority: Any, inputs: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if isinstance(authority, Mapping) and isinstance(authority.get("move_id"), str) and authority.get("category") in {"physical", "special"}:
        metadata = authority
        if inputs is not None and metadata.get("move_id") != inputs.get("move_metadata", {}).get("move_id"): return None
        return deepcopy(dict(metadata))
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or not isinstance(authority.get("metadata"), Mapping): return None
    metadata = authority["metadata"]
    if inputs is not None and metadata.get("move_id") != inputs.get("move_metadata", {}).get("move_id"): return None
    return deepcopy(dict(metadata))
def _fainted(state: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    row = state.get("active", {}).get(owner.get("side"), {}) if isinstance(state.get("active"), Mapping) else {}; return isinstance(row, Mapping) and row.get("hypothetical_fainted", {}).get("value") is True
def _owner_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
def _pending_second_action_flinch(state: Mapping[str, Any], actor: Mapping[str, Any]) -> bool | str:
    compatibility = state.get("second_action_compatibility") if isinstance(state, Mapping) else None
    flinch = compatibility.get("flinch_cancellation") if isinstance(compatibility, Mapping) else None
    if not isinstance(flinch, Mapping) or flinch.get("status") != "resolved" or flinch.get("affected_owner") != actor:
        return "intermediate_flinch_cancellation_authority_invalid"
    if flinch.get("state") == "not_flinched": return False
    if flinch.get("state") == "flinched" and flinch.get("provenance") == "exact_terminal_leaf_iron_head_flinch_secondary": return True
    return "intermediate_flinch_cancellation_state_invalid"
def _branch(base: Mapping[str, Any], order: str, first: Mapping[str, Any], intermediate: Mapping[str, Any], second: Mapping[str, Any] | None, second_actor: Mapping[str, Any], order_plan: Mapping[str, Any], execution_branch: Mapping[str, Any] | None = None, pivot_transition: Mapping[str, Any] | None = None) -> dict[str, Any]:
    first_p = _fraction(first["probability"]); second_p = Fraction(1, 1) if second is None else _fraction(second["probability"])
    order_p = order_plan["probability"]
    execution_p = Fraction(1, 1) if execution_branch is None else _fraction(execution_branch["conditional_probability"])
    cancellation = execution_branch.get("state") if isinstance(execution_branch, Mapping) and execution_branch.get("state") != "executed" else "cancelled_due_to_faint"
    path = f"{first['leaf_id']}/" + (f"second_{cancellation}" if second is None else f"{second['leaf_id']}")
    source_branch = order_plan.get("source_branch")
    second_action = {"state": cancellation if second is None else "executed", "actor": deepcopy(dict(second_actor)), "conditional_probability": _fd(execution_p * second_p), **({"reason": f"second_action_cancelled_due_to_{cancellation.removeprefix('cancelled_due_to_')}"} if second is None else {"leaf": deepcopy(dict(second))})}
    if execution_branch is not None and (execution_p != Fraction(1, 1) or execution_branch.get("state") != "executed"):
        second_action["execution_branch"] = deepcopy(dict(execution_branch))
        second_action["execution_conditional_probability"] = _fd(execution_p)
        if second is not None: second_action["mechanical_leaf_probability"] = _fd(second_p)
    return {"pair_leaf_id": (f"{source_branch['order_branch_id']}/" if isinstance(source_branch, Mapping) else "") + path, "action_order": order, **({"action_order_branch": deepcopy(dict(source_branch)), "action_order_conditional_probability": _fd(order_p)} if isinstance(source_branch, Mapping) else {}), "first_action_leaf": deepcopy(dict(first)), "intermediate_state_id": f"intermediate:{first['candidate_id']}:{first['leaf_id']}", "second_action": second_action, **({"pivot_transition": deepcopy(dict(pivot_transition))} if isinstance(pivot_transition, Mapping) else {}), "probability": _fd(order_p * first_p * execution_p * second_p), "provenance": deepcopy(dict(base))}


def _analytic_order_authority(*, strategy_d0: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], base: Mapping[str, Any], plan: Mapping[str, Any], source_action_order_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Project the chosen order branch; the direct evaluator validates it again."""
    return freeze_runtime_d0_analytic_action_order_authority(
        strategy_d0=strategy_d0, attacker=actor, target=target,
        own_action_id=base["own_action_id"], opponent_action_id=base["opponent_action_id"],
        action_order=plan["order"], source_action_order_authority=source_action_order_authority,
        action_order_branch=plan.get("source_branch"),
    )


def _execution_branch(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("state") not in {"executed", "cancelled_due_to_paralysis", "cancelled_due_to_flinch"} or not isinstance(value.get("execution_branch_id"), str): return False
    try: probability = _fraction(value["conditional_probability"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return False
    if probability <= 0: return False
    if value["state"] == "cancelled_due_to_paralysis":
        return probability == Fraction(1, 4) and value.get("reason") == "second_action_cancelled_due_to_paralysis"
    if value["state"] == "cancelled_due_to_flinch":
        return probability == Fraction(1, 1) and value.get("execution_branch_id") == "second_action:flinched" and value.get("reason") == "second_action_cancelled_due_to_flinch"
    return probability in {Fraction(1, 1), Fraction(3, 4)}
def _fraction(value: Mapping[str, Any]) -> Fraction: return Fraction(value["numerator"], value["denominator"])
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _status(value: Mapping[str, Any]) -> str: return value.get("status") if isinstance(value, Mapping) and value.get("status") in _STATUSES else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
