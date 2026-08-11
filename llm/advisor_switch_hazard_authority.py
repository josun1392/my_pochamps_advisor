"""Detached session/affected-side authority for supported entry hazards."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def build_switch_hazard_context(*, session_id: str, affected_side: str, stealth_rock: str = "unknown", spikes_layers: int | str = "unknown", toxic_spikes_layers: int | str = "unknown", sticky_web: str = "unknown") -> dict[str, Any]:
    if not isinstance(session_id, str) or not session_id or affected_side not in {"self", "opponent"} or stealth_rock not in {"present", "absent", "unknown"} or sticky_web not in {"present", "absent", "unknown"}:
        raise ValueError("invalid_switch_hazard_context")
    if spikes_layers != "unknown" and (not isinstance(spikes_layers, int) or isinstance(spikes_layers, bool) or spikes_layers not in {0, 1, 2, 3}):
        raise ValueError("invalid_switch_hazard_context")
    if toxic_spikes_layers != "unknown" and (not isinstance(toxic_spikes_layers, int) or isinstance(toxic_spikes_layers, bool) or toxic_spikes_layers not in {0, 1, 2}):
        raise ValueError("invalid_switch_hazard_context")
    return deepcopy({"schema_version": "switch-hazard-context-v2", "session_id": session_id, "affected_side": affected_side, "stealth_rock": stealth_rock, "spikes_layers": spikes_layers, "toxic_spikes_layers": toxic_spikes_layers, "sticky_web": sticky_web})


def normalize_switch_hazard_context(value: Any, *, session_id: str, affected_side: str) -> dict[str, Any]:
    unknown = build_switch_hazard_context(session_id=session_id, affected_side=affected_side)
    if not isinstance(value, Mapping):
        return unknown
    try:
        if value.get("schema_version") == "switch-hazard-context-v1" and set(value) == {"schema_version", "session_id", "affected_side", "stealth_rock", "spikes_layers"}:
            if value.get("session_id") != session_id or value.get("affected_side") != affected_side:
                return unknown
            return build_switch_hazard_context(session_id=session_id, affected_side=affected_side, stealth_rock=value.get("stealth_rock"), spikes_layers=value.get("spikes_layers"))
        expected = build_switch_hazard_context(session_id=session_id, affected_side=affected_side, stealth_rock=value.get("stealth_rock"), spikes_layers=value.get("spikes_layers"), toxic_spikes_layers=value.get("toxic_spikes_layers"), sticky_web=value.get("sticky_web"))
    except (TypeError, ValueError):
        return unknown
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else unknown


def project_switch_hazard_context(runtime_state: Mapping[str, Any], *, affected_side: str = "self") -> dict[str, Any]:
    """Read one detached side-owned hazard authority from canonical state."""
    session = runtime_state.get("session_id") if isinstance(runtime_state, Mapping) else None
    if not isinstance(session, str) or not session:
        raise ValueError("invalid_switch_hazard_context")
    return normalize_switch_hazard_context(runtime_state.get("switch_hazard_context"), session_id=session, affected_side=affected_side)
