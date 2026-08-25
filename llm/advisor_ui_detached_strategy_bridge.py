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
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
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
            incoming.append(authority)
    execution = freeze_current_execution_authority(selection_snapshot=selection, switch_incoming=incoming)
    if execution.get("status") != "resolved":
        return _result("rejected", execution.get("reason", "runtime_execution_authority_unavailable"))
    predictive_attacks = _runtime_seismic_toss_authorities(
        strategy_d0=d0, runtime_snapshot=capture, selection=selection,
    )
    live_attacks = _runtime_live_attack_authorities(
        strategy_d0=d0, runtime_snapshot=capture, selection=selection,
    )
    provisional = run_detached_strategy_orchestration(
        decision_state=d0["strategy_state"], decision_owner=d0["decision_owner"],
        selection_snapshot=selection, execution_bundle=execution,
        predictive_attacks=predictive_attacks,
        **live_attacks,
    )
    ledgers, metrics = _project_live_ledger_metrics(
        strategy_d0=d0, orchestration=provisional, live_attacks=live_attacks,
    )
    response_profiles = _project_live_opponent_response_profiles(
        strategy_d0=d0, runtime_snapshot=capture, selection=selection,
        canonical_move_metadata_authorities=opponent_canonical_move_metadata_authorities,
    )
    orchestration = run_detached_strategy_orchestration(
        decision_state=d0["strategy_state"], decision_owner=d0["decision_owner"],
        selection_snapshot=selection, execution_bundle=execution,
        predictive_attacks=predictive_attacks, exact_outcome_ledgers=ledgers,
        descriptive_metrics=metrics, opponent_response_profiles=response_profiles, **live_attacks,
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
    response_set = freeze_runtime_d0_complete_opponent_response_set_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        opponent_known_move_authority=known,
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
        orders = {response_id: freeze_runtime_d0_action_order_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own, opponent_action=by_id.get(response_id, {})) for response_id in response_set.get("selectable_response_action_ids", ())}
        result[action_id] = materialize_detached_opponent_response_profile(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own,
            response_set_authority=response_set, action_order_authorities=orders,
        )
    return result


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
    values = [
        live_attacks.get(name, {}).get(candidate_id)
        for name in (
            "probabilistic_self_stage_effect_authorities",
            "probabilistic_target_stage_effect_authorities",
            "thunderbolt_paralysis_authorities",
        )
        if isinstance(live_attacks.get(name, {}).get(candidate_id), Mapping)
    ]
    if not values:
        return "not_applicable"
    return values[0].get("status", "incomplete") if len(values) == 1 else "rejected"


def _result(status: str, reason: str) -> dict[str, str]:
    return {"status": status, "schema_version": SCHEMA, "reason": reason}
