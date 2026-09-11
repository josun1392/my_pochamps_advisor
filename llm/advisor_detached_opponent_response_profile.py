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
LIVE_RESPONSE_BUNDLE_SCHEMA = "live-opponent-response-authority-bundle-v1"
_ORDINARY_PAIR_BUNDLE_KEYS = {
    "first_action_sturdy_survival_authorities_by_order",
    "direct_heal_execution_authorities",
}


def materialize_detached_opponent_response_profile(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], response_set_authority: Mapping[str, Any],
    action_order_authorities: Mapping[str, Mapping[str, Any]],
    quick_claw_action_order_authorities: Mapping[str, Mapping[str, Any]] | None = None,
    first_action_focus_sash_survival_authorities: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    response_authority_bundles: Mapping[str, Mapping[str, Any]] | None = None,
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
    if quick_claw_action_order_authorities is not None and set(quick_claw_action_order_authorities) != set(move_ids):
        return _result("rejected", "response_profile_quick_claw_order_set_mismatch", base)
    if first_action_focus_sash_survival_authorities is not None and set(first_action_focus_sash_survival_authorities) != set(move_ids):
        return _result("rejected", "response_profile_focus_sash_authority_set_mismatch", base)
    if response_authority_bundles is not None and set(response_authority_bundles) != set(move_ids):
        return _result("rejected", "response_profile_authority_bundle_set_mismatch", base)
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
            pair_builder = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair if own_action.get("identity") in {"bullet-seed", "rock-blast", "population-bomb", "triple-axel", "triple-kick"} else materialize_immediate_move_vs_move_action_pair
            bundle_kwargs: dict[str, Any] = {}
            if response_authority_bundles is not None:
                bundle_kwargs = _bundle_kwargs(
                    bundle=response_authority_bundles.get(action_id), base=base,
                    opponent_action=action, runtime_snapshot=runtime_snapshot,
                    ordinary_pair=pair_builder is materialize_immediate_move_vs_move_action_pair,
                )
                if "status" in bundle_kwargs:
                    return _result(bundle_kwargs["status"], bundle_kwargs["reason"], base)
            pair = pair_builder(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, own_action=own_action,
                                opponent_action=action, action_order_authority=action_order_authorities[action_id],
                                **({"quick_claw_action_order_authority": quick_claw_action_order_authorities[action_id]} if quick_claw_action_order_authorities is not None else {}),
                                **({"first_action_focus_sash_survival_authorities_by_order": first_action_focus_sash_survival_authorities[action_id]} if first_action_focus_sash_survival_authorities is not None else {}),
                                **bundle_kwargs)
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


def _bundle_kwargs(*, bundle: Any, base: Mapping[str, Any], opponent_action: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], ordinary_pair: bool) -> dict[str, Any]:
    if not isinstance(bundle, Mapping) or bundle.get("schema_version") != LIVE_RESPONSE_BUNDLE_SCHEMA:
        return {"status": "rejected", "reason": "live_response_authority_bundle_invalid"}
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id")
    if any(bundle.get(key) != base.get(key) for key in required):
        return {"status": "rejected", "reason": "live_response_authority_bundle_binding_mismatch"}
    if bundle.get("opponent_response_action_id") != opponent_action.get("action_id"):
        return {"status": "rejected", "reason": "live_response_authority_bundle_response_binding_mismatch"}
    if bundle.get("status") != "resolved":
        return {"status": _status(bundle), "reason": bundle.get("reason", "live_response_authority_bundle_unavailable")}
    values = bundle.get("ordinary_pair_authorities")
    if not isinstance(values, Mapping) or set(values) - _ORDINARY_PAIR_BUNDLE_KEYS or not all(isinstance(value, Mapping) for value in values.values()):
        return {"status": "rejected", "reason": "live_response_authority_bundle_payload_invalid"}
    # The specialized gate owns its own extension composition.  Passing even
    # unrelated authority maps would turn a valid status-gated pair incomplete.
    if not ordinary_pair or _status_or_confusion_gate(runtime_snapshot, base):
        return {}
    return deepcopy(dict(values))


def _status_or_confusion_gate(snapshot: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    if not isinstance(state, Mapping):
        return True
    for owner in (base.get("target_owner"), base.get("opponent_actor")):
        if not isinstance(owner, Mapping):
            return True
        row = state.get(f"{owner.get('side')}_side", {}).get("pokemon", {}).get(owner.get("slot_index"))
        if not isinstance(row, Mapping):
            return True
        if row.get("condition") in {"sleep", "freeze"} or row.get("current_confusion") == "confused":
            return True
    return False


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
