"""Detached Fling throw consequence; current runtime/D0 is never mutated."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_fling_item_execution_authority import SCHEMA_VERSION


def materialize_detached_fling_item_throw(*, authority: Mapping[str, Any], source_leaf: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION or authority.get("status") != "resolved" or authority.get("outcome") != "ready_throw":
        return {"status": "incomplete", "reason": "fling_throw_authority_unavailable"}
    if not isinstance(source_leaf, Mapping) or source_leaf.get("hit_state") not in {"hit", "miss"}:
        return {"status": "rejected", "reason": "fling_throw_source_leaf_invalid"}
    provenance = source_leaf.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("move_id") != "fling" or provenance.get("attacker") != authority.get("actor") or source_leaf.get("candidate_id") != authority.get("action_id"):
        return {"status": "rejected", "reason": "fling_throw_leaf_binding_mismatch"}
    before, after = authority.get("user_item_before"), authority.get("item_after")
    if not isinstance(before, Mapping) or before.get("status") != "known" or not isinstance(before.get("value"), str) or after != {"state": "known_absent", "item": None}:
        return {"status": "rejected", "reason": "fling_throw_item_transition_invalid"}
    return {"status": "resolved", "outcome": "thrown", "timing": "prepare_hit_before_accuracy_protection_immunity_damage", "item_before": before["value"], "item_after": None, "source_leaf": source_leaf["leaf_id"], "authority": deepcopy(dict(authority)), "provenance": "detached_fling_item_throw_v1"}
