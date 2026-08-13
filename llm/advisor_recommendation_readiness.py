"""Read-only UI readiness projection for structured recommendations."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_MISSING_FACTS = {
    "current_hp": ("Current HP needed", "current_hp"),
    "max_hp": ("Maximum HP needed", "current_hp"),
    "current_type": ("Current type needed", "current_type"),
    "condition": ("Current condition needed", "current_condition"),
    "stat_stage": ("Current stat stages needed", "current_stat_stage"),
    "weather": ("Weather not confirmed", "current_field_state"),
    "terrain": ("Terrain not confirmed", "current_field_state"),
    "grounded": ("Groundedness not confirmed", "current_field_state"),
    "ability": ("Current ability unknown", "current_ability"),
    "item": ("Held item unknown", None),
    "hazard": ("Hazard state not confirmed", "field_profile"),
    "toxic_progression": ("Toxic progression authority missing", None),
    "switch_permission": ("Switch permission needed", "switch_permission"),
    "previous_damage": ("Previous damage authority missing", "current_observed_damage"),
    "qualifying_direct_damage": ("Opponent move/result authority missing", None),
    "turn_event": ("Opponent move/result authority missing", None),
}


def _fact(path: str) -> tuple[str, str | None]:
    token = path.lower()
    for needle, result in _MISSING_FACTS.items():
        if needle in token:
            return result
    return ("Required deterministic authority is unavailable", None)


def build_recommendation_readiness(*, prepared_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Project canonical candidate incompleteness without evaluating new rules."""
    candidates = prepared_cycle.get("candidates") if isinstance(prepared_cycle, Mapping) else None
    if not isinstance(candidates, list):
        return {"status": "unavailable", "missing": [], "unsupported": ["Recommendation context unavailable"], "action": None}
    missing: list[dict[str, Any]] = []
    unsupported: list[str] = []
    seen_missing: set[str] = set()
    seen_unsupported: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        for source in (candidate.get("mechanics_result"), candidate.get("action_order"), candidate.get("move_success")):
            if not isinstance(source, Mapping):
                continue
            if source.get("status") == "insufficient_context":
                for path in source.get("missing_inputs", ()):
                    if not isinstance(path, str) or path in seen_missing:
                        continue
                    seen_missing.add(path)
                    label, action = _fact(path)
                    missing.append({"path": path, "label": label, "action": action})
            elif source.get("status") == "unsupported_mechanic":
                reason = source.get("unsupported_reason")
                if isinstance(reason, str) and reason not in seen_unsupported:
                    seen_unsupported.add(reason)
                    unsupported.append("This selected mechanic is not supported yet")
    action = next((entry["action"] for entry in missing if entry["action"] is not None), None)
    status = "ready" if not missing and not unsupported else "incomplete" if missing else "unsupported"
    return {"status": status, "missing": deepcopy(missing), "unsupported": unsupported, "action": action}
