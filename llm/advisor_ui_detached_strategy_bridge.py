"""Pure runtime-controller bridge for detached deterministic strategy.

The caller supplies only the existing structured selection-cycle builder.  This
module owns no UI state, mechanics, provider behavior, or ranking policy.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from llm.advisor_current_execution_authority import freeze_current_execution_authority
from llm.advisor_detached_strategy_orchestration import run_detached_strategy_orchestration
from llm.advisor_runtime_d0_selection_projection import (
    build_runtime_d0_selection_capture,
    freeze_runtime_d0_bound_selection_projection,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_incoming_current_state_authority,
    freeze_runtime_strategy_d0,
    freeze_runtime_strategy_selection_authority,
    resolve_runtime_strategy_decision_owner,
    resolve_runtime_incoming_owner,
    runtime_strategy_d0_freshness,
)
from llm.advisor_strategy_explanation import explain_detached_strategy


SCHEMA = "ui-detached-strategy-bridge-result-v1"


def run_current_ui_detached_strategy(
    *, runtime_session_manager: Any, captured_session_id: str, decision_owner: Mapping[str, Any] | None = None,
    decision_side: str = "self", selection_cycle_builder: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
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
    orchestration = run_detached_strategy_orchestration(
        decision_state=d0["strategy_state"], decision_owner=d0["decision_owner"],
        selection_snapshot=selection, execution_bundle=execution,
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
        "orchestration": deepcopy(orchestration), "explanation": deepcopy(explanation),
        "provenance": "runtime_d0_detached_strategy_ui_controller_bridge_v1",
    }


def _capture(manager: Any, session_id: str) -> Mapping[str, Any] | None:
    if not isinstance(session_id, str) or not session_id or not callable(getattr(manager, "capture_runtime_state_snapshot", None)):
        return None
    value = manager.capture_runtime_state_snapshot(session_id)
    return value if isinstance(value, Mapping) else None


def _result(status: str, reason: str) -> dict[str, str]:
    return {"status": status, "schema_version": SCHEMA, "reason": reason}
