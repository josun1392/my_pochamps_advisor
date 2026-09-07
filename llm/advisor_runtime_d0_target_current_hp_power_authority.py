"""Strict execution-time target-HP power authority for the closed move family."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_target_current_hp_power_family import resolve_canonical_target_current_hp_power_move
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-target-current-hp-power-authority-v1"


def freeze_runtime_d0_target_current_hp_power_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    canonical = resolve_canonical_target_current_hp_power_move(move=move)
    if canonical.get("status") != "resolved":
        return _bad(canonical.get("status", "rejected"), canonical.get("reason", "target_current_hp_power_catalog_unavailable"))
    if not all(isinstance(value, Mapping) for value in (strategy_d0, runtime_snapshot, user, target)):
        return _bad("rejected", "target_current_hp_power_request_invalid")
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")
    if not all(isinstance(strategy_d0.get(key), str) and strategy_d0[key] for key in required):
        return _bad("rejected", "target_current_hp_power_d0_provenance_missing")
    active = strategy_d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(user.get("side")) != user or active.get(target.get("side")) != target or user == target:
        return _bad("rejected", "target_current_hp_power_active_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _bad("rejected", freshness.get("reason", "target_current_hp_power_stale_d0"))
    preview = strategy_d0.get("strategy_state", {}).get("active", {}).get(target.get("side"))
    if not isinstance(preview, Mapping):
        return _bad("incomplete", "target_current_hp_power_target_hp_missing")
    current, maximum = preview.get("current_hp"), preview.get("max_hp")
    if isinstance(current, bool) or not isinstance(current, int):
        return _bad("incomplete", "target_current_hp_power_target_current_hp_missing")
    if isinstance(maximum, bool) or not isinstance(maximum, int):
        return _bad("incomplete", "target_current_hp_power_target_max_hp_missing")
    if maximum <= 0 or current <= 0 or current > maximum:
        return _bad("rejected", "target_current_hp_power_target_hp_invalid")
    move_id = canonical["move_id"]
    multiplier, additive, variant = (100, 0, "hard-press-current-hp-ratio") if move_id == "hard-press" else (120, 1, "crush-grip-wring-out-current-hp-ratio")
    intermediate = multiplier * current // maximum
    power = max(1, intermediate + additive)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "user": deepcopy(dict(user)), "target": deepcopy(dict(target)), "move_id": move_id,
        "family": "target_current_hp_power", "target_current_hp": current, "target_max_hp": maximum,
        "target_hp_provenance": "runtime_strategy_d0_execution_path_active_hp_v1", "formula_variant": variant,
        "ratio_numerator": multiplier * current, "ratio_denominator": maximum,
        "intermediate_power": intermediate, "resolved_base_power": power,
        "rule": deepcopy(dict(canonical["effect"]),), "provenance": "strict_runtime_d0_execution_time_target_hp_power_v1",
    }


def _bad(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
