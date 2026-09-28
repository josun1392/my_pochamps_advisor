"""Read-only UI readiness projection for structured recommendations."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_EXACT_MISSING_FACTS = {
    "attacker.status": ("Attacker current condition needed", "current_condition"),
    "defender.status": ("Defender current condition needed", "current_condition"),
    "attacker.condition": ("Attacker current condition needed", "current_condition"),
    "defender.condition": ("Defender current condition needed", "current_condition"),
    "self_paralysis": ("Self paralysis state needed", "current_condition"),
    "opponent_paralysis": ("Opponent paralysis state needed", "current_condition"),
    "attacker.boosts": ("Attacker stat stages needed", "current_stat_stage"),
    "defender.boosts": ("Defender stat stages needed", "current_stat_stage"),
    "attacker.attack_stage": ("Attacker Attack stage needed", "current_stat_stage"),
    "attacker.special-attack_stage": ("Attacker Special Attack stage needed", "current_stat_stage"),
    "attacker.defense_stage": ("Attacker Defense stage needed", "current_stat_stage"),
    "defender.attack_stage": ("Defender Attack stage needed", "current_stat_stage"),
    "defender.defense_stage": ("Defender Defense stage needed", "current_stat_stage"),
    "defender.special-defense_stage": ("Defender Special Defense stage needed", "current_stat_stage"),
    "self_speed_stage": ("Self Speed stage needed", "current_stat_stage"),
    "opponent_speed_stage": ("Opponent Speed stage needed", "current_stat_stage"),
    "attacker.final_stats": ("Attacker final stats needed", "current_final_stat"),
    "defender.final_stats": ("Defender final stats needed", "current_final_stat"),
    "self_final_speed": ("Self final Speed needed", "current_final_stat"),
    "opponent_final_speed": ("Opponent final Speed needed", "current_final_stat"),
    "battle_format": ("Battle format not confirmed", "current_battle_format"),
    "effective_priority": ("Priority/action context needed", None),
    "opponent_action": ("Opponent action context needed for this mechanic", None),
}


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
    "item": ("Held item unknown", "current_item"),
    "hazard": ("Hazard state not confirmed", "field_profile"),
    "toxic_progression": ("Toxic progression authority missing", None),
    "switch_permission": ("Switch permission needed", "switch_permission"),
    "previous_damage": ("Previous damage authority missing", "current_observed_damage"),
    "qualifying_direct_damage": ("Opponent move/result authority missing", None),
    "turn_event": ("Opponent move/result authority missing", None),
}


def _fact(path: str) -> tuple[str, str | None]:
    token = path.lower()
    exact = _EXACT_MISSING_FACTS.get(token)
    if exact is not None:
        return exact
    for needle, result in _MISSING_FACTS.items():
        if needle in token:
            return result
    return ("Required deterministic authority is unavailable", None)


def _is_globally_blocking_missing(*, source_name: str, path: str) -> bool:
    """Keep legacy scalar evidence from becoming a false global prerequisite."""
    return not (source_name == "action_order" and path == "opponent_action")


def build_recommendation_readiness(*, prepared_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Project canonical candidate incompleteness without evaluating new rules."""
    if not isinstance(prepared_cycle, Mapping) or prepared_cycle.get("status") not in {"ready", "no_selectable_candidates"}:
        return {
            "status": "unavailable",
            "missing": [],
            "unsupported": ["Recommendation context unavailable"],
            "action": None,
        }
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
        for source_name in ("mechanics_result", "action_order", "move_success"):
            source = candidate.get(source_name)
            if not isinstance(source, Mapping):
                continue
            if source.get("status") == "insufficient_context":
                for path in source.get("missing_inputs", ()):
                    if (
                        not isinstance(path, str)
                        or path in seen_missing
                        or not _is_globally_blocking_missing(source_name=source_name, path=path)
                    ):
                        continue
                    seen_missing.add(path)
                    label, action = _fact(path)
                    missing.append({"path": path, "label": label, "action": action})
            elif source.get("status") == "unsupported_mechanic":
                reason = source.get("unsupported_reason")
                if isinstance(reason, str) and reason not in seen_unsupported:
                    seen_unsupported.add(reason)
                    unsupported.append("This selected mechanic is not supported yet")
    action = next((entry["action"] for entry in missing if entry["action"] == "current_item"), None)
    if action is None:
        action = next((entry["action"] for entry in missing if entry["action"] is not None), None)
    status = "ready" if not missing and not unsupported else "incomplete" if missing else "unsupported"
    return {"status": status, "missing": deepcopy(missing), "unsupported": unsupported, "action": action}
