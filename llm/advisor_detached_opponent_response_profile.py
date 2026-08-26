"""Materialize exact conditional pair evidence for one own attack response set."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_exact_action_pair_descriptive_metrics import (
    project_exact_immediate_action_pair_descriptive_metrics,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    materialize_immediate_move_vs_move_action_pair,
)
from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import (
    materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair,
)
from llm.advisor_immediate_attack_vs_opponent_switch_action_pair import (
    materialize_immediate_attack_vs_opponent_switch_action_pair,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "detached-opponent-response-profile-v1"
RESPONSE_SET_SCHEMAS = {
    "runtime-d0-complete-opponent-response-set-authority-v1",
    "runtime-d0-combined-opponent-response-universe-authority-v1",
}
HORIZON = "immediate_action_pair"


def materialize_detached_opponent_response_profile(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], response_set_authority: Mapping[str, Any],
    action_order_authorities: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build every required pair, ledger, and metric without response policy."""
    base = _base(strategy_d0, own_action, response_set_authority)
    if base is None:
        return _result("rejected", "invalid_response_profile_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    expected = response_set_authority.get("selectable_response_action_ids")
    actions = response_set_authority.get("actions")
    if response_set_authority.get("status") != "resolved" or not isinstance(expected, tuple) or not isinstance(actions, tuple):
        return _result(_status(response_set_authority), response_set_authority.get("reason", "complete_response_set_unavailable"), base)
    if response_set_authority.get("schema_version") == "runtime-d0-combined-opponent-response-universe-authority-v1":
        if response_set_authority.get("universe_state") == "complete_zero_response_universe" and not expected:
            return _result("incomplete", "combined_response_universe_has_zero_selectable_responses", base)
        if response_set_authority.get("universe_state") != "complete_with_selectable_responses":
            return _result("rejected", "combined_response_universe_state_invalid", base)
    elif not expected:
        return _result("incomplete", "complete_response_set_has_zero_selectable_responses", base)
    action_by_id = {row.get("action_id"): row for row in actions if isinstance(row, Mapping)}
    all_ids = response_set_authority.get("response_action_ids", response_set_authority.get("known_action_ids", ()))
    if not isinstance(all_ids, tuple) or tuple(action_by_id) != all_ids or set(expected) - set(action_by_id):
        return _result("rejected", "response_set_action_identity_invalid", base)
    move_ids = tuple(action_id for action_id in expected if action_by_id[action_id].get("response_kind", "move") == "move")
    if not isinstance(action_order_authorities, Mapping) or set(action_order_authorities) != set(move_ids):
        return _result("rejected", "response_profile_action_order_set_mismatch", base)
    entries = []
    profile_status = "evaluable"
    for action_id in expected:
        action = action_by_id[action_id]
        kind = action.get("response_kind", "move")
        if action.get("selectability") != "selectable" or kind not in {"move", "switch"}:
            return _result("rejected", "selectable_response_action_payload_invalid", base)
        if kind == "move":
            if action.get("usability", {}).get("status") != "known_usable":
                return _result("rejected", "selectable_move_response_usability_invalid", base)
            pair_builder = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair if own_action.get("identity") in {"bullet-seed", "rock-blast"} else materialize_immediate_move_vs_move_action_pair
            pair = pair_builder(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own_action,
                                opponent_action=action, action_order_authority=action_order_authorities[action_id])
        else:
            switch_authority = response_set_authority.get("source_switch_response_authority")
            if not isinstance(switch_authority, Mapping):
                return _result("rejected", "combined_switch_response_authority_missing", base)
            pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own_action,
                switch_response_authority=switch_authority,
                selected_switch_response_action_id=action_id,
            )
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
        metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
        entry = {"opponent_response_action_id": action_id, "response_kind": kind, "pair": deepcopy(pair), "exact_pair_outcome_ledger": deepcopy(ledger), "descriptive_metrics": deepcopy(metrics)}
        entries.append(entry)
        status = _entry_status(pair, ledger, metrics)
        if status == "rejected":
            return _result("rejected", _reason(pair, ledger, metrics), base, response_entries=tuple(entries))
        if status == "unsupported":
            profile_status = "unsupported"
        elif status == "incomplete" and profile_status != "unsupported":
            profile_status = "incomplete"
    if profile_status != "evaluable":
        return _result(profile_status, "required_response_pair_not_evaluable", base, response_entries=tuple(entries))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
        "selectable_response_action_ids": tuple(expected), "response_entries": tuple(entries),
        "response_set_provenance": deepcopy(response_set_authority.get("response_set_provenance")),
        "response_probability": "not_modeled", "ranking_influence": "none",
        "provenance": "strict_detached_complete_opponent_response_profile_v1",
    }


def _base(d0: Any, own: Any, response_set: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(own, Mapping) or own.get("action_type") != "attack" or not isinstance(own.get("action_id"), str) or not isinstance(response_set, Mapping) or response_set.get("schema_version") not in RESPONSE_SET_SCHEMAS:
        return None
    self_owner, opponent = d0.get("active_owners", {}).get("self"), d0.get("active_owners", {}).get("opponent")
    if d0.get("decision_owner") != self_owner or not isinstance(self_owner, Mapping) or not isinstance(opponent, Mapping):
        return None
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": d0.get("decision_owner"), "opponent_actor": opponent, "target_owner": self_owner}
    if any(response_set.get(key) != value for key, value in expected.items()):
        return None
    return {"own_action_id": own["action_id"], **{key: deepcopy(value) if isinstance(value, Mapping) else value for key, value in expected.items()}}


def _entry_status(*items: Mapping[str, Any]) -> str:
    statuses = [item.get("status") if isinstance(item, Mapping) else "rejected" for item in items]
    if "rejected" in statuses: return "rejected"
    if "unsupported" in statuses: return "unsupported"
    if any(status not in {"evaluable", "resolved"} for status in statuses): return "incomplete"
    return "evaluable"


def _reason(*items: Mapping[str, Any]) -> str:
    return next((item.get("reason") for item in items if isinstance(item, Mapping) and isinstance(item.get("reason"), str)), "response_profile_component_rejected")


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
