"""Sun-only detached Solar Power EOT adapter for the deterministic Turn Engine."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_ice_body_end_of_turn import _ability, _field_weather_authority, _owners, _requires_residual_ordering, _result, _sync_hp
from llm.advisor_solar_power_residual_core import evaluate_solar_power_residual
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def project_solar_power_end_of_turn(*, pre_end_of_turn: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("status") != "resolved" or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn": return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state"); source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None: return _result("rejected", "invalid_pre_end_of_turn_branch")
    state = deepcopy(dict(source)); owners = _owners(state)
    if owners is None: return _result("rejected", "invalid_active_owner")
    if not _field_weather_authority(state, source_fp, owners["self"]["session_id"], "sun"): return _result("rejected", "stale_or_invalid_branch_sun_authority")
    if _requires_residual_ordering(state, "solar-power"): return _result("incomplete", "solar_power_residual_ordering_unresolved")
    abilities = {side: _ability(state, side) for side in ("self", "opponent")}
    if any(value is None for value in abilities.values()): return _result("incomplete", "solar_power_current_ability_authority")
    trace = []
    for side in ("self", "opponent"):
        active = state["active"][side]
        if abilities[side] != "solar-power": continue
        if active["fainted"]:
            trace.append({"sequence": len(trace)+1, "effect":"solar_power_residual", "owner":deepcopy(owners[side]), "weather":"sun", "execution_status":"skipped", "provenance":"detached_branch_solar_power_residual_v1", "status":"complete", "outcome":"fainted_before_eot"}); continue
        residual = evaluate_solar_power_residual(active_abilities=abilities, target_side=side, current_hp=active["current_hp"], maximum_hp=active["max_hp"])
        if residual.get("status") != "complete": return _result("incomplete", "canonical_solar_power_authority")
        if "post_hp" in residual:
            active["current_hp"], active["fainted"] = residual["post_hp"], residual["post_hp"] == 0; _sync_hp(state, side, residual["post_hp"], residual["max_hp"])
        trace.append({"sequence":len(trace)+1,"effect":"solar_power_residual","owner":deepcopy(owners[side]),"weather":"sun","execution_status":"prevented" if residual.get("outcome", "").startswith("suppressed") else "executed","provenance":"detached_branch_solar_power_residual_v1",**deepcopy(residual)})
    if not trace: return _result("incomplete", "solar_power_active_ability_required")
    return {"status":"resolved","source_pre_end_of_turn_fingerprint":source_fp,"resulting_branch_fingerprint":fingerprint_transition_preview_state(state),"eot_consequence_trace":trace,"next_state":state,"boundary":{"phase":"end_of_turn"},"limitations":["solar_power_sun_only","poison_toxic_or_sandstorm_ordering_fails_closed","no_reducer_or_runtime_writeback"]}
