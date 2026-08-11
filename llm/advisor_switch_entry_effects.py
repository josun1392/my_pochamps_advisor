"""Compose supported frozen switch-entry effects for one candidate B."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_switch_entry_hazards import evaluate_entry_hazards


_CONDITIONS = frozenset({None, "none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"})


def evaluate_switch_entry_effects(*, hazards: Mapping[str, Any], target: Mapping[str, Any], intimidate_authority: Mapping[str, Any] | None = None, download_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate damage first, then supported status and Speed-stage entry effects.

    Each effect retains an independent supportability result.  This lets known
    Stealth Rock/Spikes damage compose into incoming damage even when a later
    non-damaging entry effect correctly remains incomplete.
    """
    damage = evaluate_entry_hazards(hazards=hazards, target=target)
    toxic = _evaluate_toxic_spikes(hazards=hazards, target=target)
    sticky = _evaluate_sticky_web(hazards=hazards, target=target)
    intimidate = _evaluate_intimidate(target=target, damage=damage, authority=intimidate_authority)
    download = _evaluate_download(target=target, damage=damage, authority=download_authority)
    return {
        **deepcopy(damage),
        "toxic_spikes_result": toxic,
        "sticky_web_result": sticky,
        "intimidate_result": intimidate,
        "download_result": download,
        "entry_effects_supportability": "complete" if all(result.get("status") == "complete" for result in (damage, toxic, sticky, intimidate, download)) else "insufficient_context",
    }


def _evaluate_toxic_spikes(*, hazards: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    item = _authority(target, "item_authority")
    if _known_value(item) == "heavy-duty-boots":
        return _complete("prevented_by_heavy_duty_boots")
    if not _known_authority(item):
        return _incomplete("item_unknown")
    layers = _hazard_value(hazards, "toxic_spikes_layers", {0, 1, 2})
    if layers is None:
        return _incomplete("toxic_spikes_unknown")
    if layers == 0:
        return _complete("absent")
    grounded = _grounded(target)
    if grounded is None:
        return _incomplete("prospective_groundedness_unknown")
    if grounded is False:
        return _complete("ungrounded")
    types = _types(target)
    if types is None:
        return _incomplete("current_type_unknown")
    if "poison" in types:
        return _complete("absorbed", removes_toxic_spikes=True)
    if "steel" in types:
        return _complete("status_immune")
    condition_authority = _authority(target, "persistent_condition_authority")
    if not _known_authority(condition_authority):
        return _incomplete("condition_unknown")
    condition = _known_value(condition_authority)
    if condition not in _CONDITIONS:
        return _incomplete("condition_unknown")
    if condition not in {None, "none"}:
        return _complete("already_statused", post_condition=condition)
    ability = _authority(target, "ability_authority")
    if not _known_authority(ability):
        return _incomplete("ability_unknown")
    interaction = _interaction(target, "toxic_spikes")
    if interaction is None:
        return _incomplete("toxic_spikes_interaction_unknown")
    if interaction == "blocked":
        return _complete("status_prevented")
    return _complete("status_applied", post_condition="toxic" if layers == 2 else "poison")


def _evaluate_sticky_web(*, hazards: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    item = _authority(target, "item_authority")
    if _known_value(item) == "heavy-duty-boots":
        return _complete("prevented_by_heavy_duty_boots")
    if not _known_authority(item):
        return _incomplete("item_unknown")
    present = _hazard_value(hazards, "sticky_web", {"present", "absent"})
    if present is None:
        return _incomplete("sticky_web_unknown")
    if present == "absent":
        return _complete("absent")
    grounded = _grounded(target)
    if grounded is None:
        return _incomplete("prospective_groundedness_unknown")
    if grounded is False:
        return _complete("ungrounded")
    if not _known_authority(_authority(target, "ability_authority")):
        return _incomplete("ability_unknown")
    interaction = _interaction(target, "sticky_web")
    if interaction is None:
        return _incomplete("sticky_web_interaction_unknown")
    if interaction == "blocked":
        return _complete("speed_drop_prevented")
    speed = _authority(target, "prospective_speed_stage_authority")
    stage = _known_value(speed)
    if not isinstance(stage, int) or isinstance(stage, bool) or not -6 <= stage <= 6:
        return _incomplete("prospective_speed_stage_unknown")
    after = max(-6, stage - 1)
    return _complete("speed_stage_lowered" if after < stage else "speed_stage_minimum", speed_stage_before=stage, speed_stage_after=after)


def _evaluate_intimidate(*, target: Mapping[str, Any], damage: Mapping[str, Any], authority: Mapping[str, Any] | None) -> dict[str, Any]:
    ability = _authority(target, "ability_authority")
    if not _known_authority(ability):
        return _incomplete("candidate_ability_unknown")
    if _known_value(ability) != "intimidate":
        return _complete("not_applicable")
    if damage.get("status") != "complete":
        return _incomplete("prior_entry_hazards_incomplete")
    if damage.get("hazard_ko") is True:
        return _complete("not_activated_hazard_ko")
    source = {"side": "self", "slot_index": target.get("slot_index"), "pokemon_id": target.get("pokemon_id")}
    if not _valid_intimidate_authority(authority, session_id=target.get("session_id")) or authority.get("source") != source:
        return _incomplete("intimidate_interaction_unknown")
    opponent = authority.get("target")
    if not _identity(opponent, "opponent"):
        return _incomplete("opposing_active_unknown")
    interaction, before = authority.get("interaction"), authority.get("target_attack_stage")
    if interaction not in {"lowered", "blocked", "reversed"}:
        return _incomplete("intimidate_interaction_unknown")
    if not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _incomplete("opposing_attack_stage_unknown")
    if interaction == "blocked":
        return _complete("attack_drop_prevented", opponent_identity=deepcopy(dict(opponent)), attack_stage_before=before, attack_stage_after=before)
    after = max(-6, before - 1) if interaction == "lowered" else min(6, before + 1)
    outcome = "attack_stage_lowered" if interaction == "lowered" and after < before else "attack_stage_minimum" if interaction == "lowered" else "attack_stage_reversed" if after > before else "attack_stage_maximum"
    return _complete(outcome, opponent_identity=deepcopy(dict(opponent)), attack_stage_before=before, attack_stage_after=after)


def _evaluate_download(*, target: Mapping[str, Any], damage: Mapping[str, Any], authority: Mapping[str, Any] | None) -> dict[str, Any]:
    ability = _authority(target, "ability_authority")
    if not _known_authority(ability):
        return _incomplete("candidate_ability_unknown")
    if _known_value(ability) != "download":
        return _complete("not_applicable")
    if damage.get("status") != "complete":
        return _incomplete("prior_entry_hazards_incomplete")
    if damage.get("hazard_ko") is True:
        return _complete("not_activated_hazard_ko")
    source = {"side": "self", "slot_index": target.get("slot_index"), "pokemon_id": target.get("pokemon_id")}
    if not _valid_download_authority(authority, session_id=target.get("session_id")) or authority.get("source") != source:
        return _incomplete("download_authority_unknown")
    if authority.get("applicability") == "unknown":
        return _incomplete("download_applicability_unknown")
    if authority.get("applicability") == "blocked":
        return _complete("ability_suppressed")
    defense, special_defense = authority.get("target_defense"), authority.get("target_special_defense")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (defense, special_defense)):
        return _incomplete("opposing_defensive_stats_unknown")
    stat = "attack" if defense < special_defense else "special-attack"
    stages = _authority(target, "prospective_offensive_stages_authority")
    before = stages.get(stat) if isinstance(stages, Mapping) else None
    if not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _incomplete(f"prospective_{stat}_stage_unknown")
    after = min(6, before + 1)
    outcome = f"{stat}_stage_raised" if after > before else f"{stat}_stage_maximum"
    return _complete(outcome, boosted_stat=stat, stage_before=before, stage_after=after, opponent_identity=deepcopy(dict(authority["target"])))


def _hazard_value(hazards: Any, key: str, allowed: set[Any]) -> Any | None:
    required = {"schema_version", "session_id", "affected_side", "stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web"}
    if not isinstance(hazards, Mapping) or set(hazards) != required or hazards.get("schema_version") != "switch-hazard-context-v2" or hazards.get("affected_side") != "self":
        return None
    value = hazards.get(key)
    return value if value in allowed else None


def _authority(target: Any, key: str) -> Any:
    return target.get(key) if isinstance(target, Mapping) else None


def _known_authority(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and set(value) == {"status", "value"}


def _known_value(value: Any) -> Any:
    return value.get("value") if _known_authority(value) else None


def _grounded(target: Mapping[str, Any]) -> bool | None:
    value = _authority(target, "prospective_groundedness_authority")
    if not isinstance(value, Mapping) or set(value) != {"status"}:
        return None
    if value.get("status") == "grounded":
        return True
    if value.get("status") == "ungrounded":
        return False
    return None


def _types(target: Mapping[str, Any]) -> list[str] | None:
    value = _authority(target, "current_type_authority")
    types = _known_value(value)
    return deepcopy(types) if isinstance(types, list) and 1 <= len(types) <= 2 and all(isinstance(type_, str) and type_ for type_ in types) else None


def _interaction(target: Mapping[str, Any], key: str) -> str | None:
    value = _authority(target, "prospective_entry_interactions_authority")
    if not isinstance(value, Mapping) or set(value) != {"toxic_spikes", "sticky_web"}:
        return None
    result = value.get(key)
    return result if result in {"applicable", "blocked"} else None


def _identity(value: Any, side: str) -> bool:
    return isinstance(value, Mapping) and value.get("side") == side and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _valid_intimidate_authority(value: Any, *, session_id: Any) -> bool:
    required = {"schema_version", "session_id", "source", "target", "interaction", "target_attack_stage"}
    return isinstance(value, Mapping) and set(value) == required and value.get("schema_version") == "switch-entry-intimidate-authority-v1" and value.get("session_id") == session_id and _identity(value.get("source"), "self") and _identity(value.get("target"), "opponent")


def _valid_download_authority(value: Any, *, session_id: Any) -> bool:
    required = {"schema_version", "session_id", "source", "target", "applicability", "target_defense", "target_special_defense"}
    return isinstance(value, Mapping) and set(value) == required and value.get("schema_version") == "switch-entry-download-authority-v1" and value.get("session_id") == session_id and value.get("applicability") in {"applicable", "blocked", "unknown"} and _identity(value.get("source"), "self") and _identity(value.get("target"), "opponent")


def _complete(outcome: str, **details: Any) -> dict[str, Any]:
    return {"status": "complete", "outcome": outcome, **deepcopy(details)}


def _incomplete(reason: str) -> dict[str, Any]:
    return {"status": "insufficient_context", "outcome": None, "reason": reason}
