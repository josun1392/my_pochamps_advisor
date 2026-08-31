"""Strict D0 authority for detached Population Bomb per-attempt execution.

This boundary deliberately freezes the *repeated* accuracy contract without
materializing hit, damage, or terminal paths.  Population Bomb is therefore
not accidentally treated as an ordinary action-level-accuracy multi-hit move.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_d0_critical_hit_authority,
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-population-bomb-per-hit-accuracy-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_MOVE_ID = "population-bomb"
_MAX_ATTEMPTS = 10


def freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze canonical base Population Bomb execution inputs, fail closed."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    active = strategy_d0.get("active_owners", {})
    attacker = strategy_d0.get("decision_owner")
    target = active.get("opponent" if isinstance(attacker, Mapping) and attacker.get("side") == "self" else "self")
    if not _owner(attacker) or not _owner(target) or attacker != active.get(attacker["side"]):
        return _result("rejected", "runtime_population_bomb_active_identity_unavailable", base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {
        **base, "action_id": action.get("action_id"), "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)), "move_metadata_authority": deepcopy(metadata_authority),
        "provenance": "runtime_d0_canonical_population_bomb_per_hit_accuracy_execution_authority_v1",
    }
    if metadata_authority.get("status") != "resolved":
        return _result(metadata_authority.get("status", "rejected"), metadata_authority.get("reason", "population_bomb_move_metadata_unavailable"), common)
    metadata = metadata_authority.get("metadata")
    classification = _classification(metadata, action.get("identity"))
    if classification.get("status") != "resolved":
        return _result(classification["status"], classification["reason"], {**common, "classification": classification})
    critical_source = freeze_runtime_d0_critical_hit_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=attacker, target=target, move_metadata=metadata,
    )
    modifier = freeze_runtime_d0_population_bomb_hit_count_modifier_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
    )
    if modifier.get("status") != "resolved":
        return _result(modifier.get("status", "rejected"), modifier.get("reason", "population_bomb_modifier_authority_unavailable"), {
            **common, "classification": classification, "modifier_authority": deepcopy(modifier),
            "critical_hit_authority": deepcopy(critical_source),
        })
    hit = build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=attacker, target=target, selected_move=metadata,
    )
    probability = _per_attempt_probability(hit, common)
    if probability.get("status") != "resolved":
        return _result(probability.get("status", "rejected"), probability.get("reason", "population_bomb_per_attempt_accuracy_unavailable"), {
            **common, "classification": classification, "modifier_authority": deepcopy(modifier),
            "per_attempt_hit_authority": deepcopy(hit),
        })
    critical = build_runtime_d0_strict_critical_hit_probability_assessment(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=attacker, target=target, move_metadata=metadata,
    )
    if critical.get("status") != "resolved":
        return _result(critical.get("status", "rejected"), critical.get("reason", "population_bomb_critical_authority_unavailable"), {
            **common, "classification": classification, "modifier_authority": deepcopy(modifier),
            "per_attempt_hit_authority": deepcopy(hit), "critical_hit_authority": deepcopy(critical),
        })
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "move_id": _MOVE_ID,
        "maximum_attempt_execution": {
            "status": "resolved", "maximum_attempts": _MAX_ATTEMPTS,
            "semantics": "canonical_fixed_ten_attempt_multiaccuracy",
        },
        "per_attempt_accuracy_execution": {
            "status": "resolved", "semantics": "independent_accuracy_check_per_attempt_stop_on_first_miss",
            **probability["probabilities"], "per_attempt_hit_authority": deepcopy(hit),
        },
        "per_hit_critical_execution": {
            "status": "resolved", "semantics": "independent_canonical_critical_roll_per_landed_hit",
            "per_hit_critical_probability": deepcopy(critical["critical_probability"]),
            "critical_hit_authority": deepcopy(critical),
        },
        "modifier_authority": modifier,
        "execution_exclusions": {
            "action_level_accuracy": "forbidden", "aggregate_total_damage": "forbidden",
            "skill_link_or_loaded_dice": "requires_separate_exact_population_bomb_modifier_execution_authority",
            "per_hit_secondary": "unsupported", "drain_or_recoil": "unsupported",
            "contact_or_item_consumption": "requires_separate_exact_owner",
            "substitute_or_replacement": "requires_separate_exact_owner",
        },
}


def freeze_runtime_d0_population_bomb_hit_count_modifier_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the current D0 Skill Link/Loaded Dice execution modifier.

    This intentionally owns only Population Bomb's hit-count modifier; it does
    not turn the descriptive multi-hit helper into runtime authority.
    """
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    attacker = strategy_d0.get("decision_owner")
    active = strategy_d0.get("active_owners", {})
    target = active.get("opponent" if isinstance(attacker, Mapping) and attacker.get("side") == "self" else "self")
    if not _owner(attacker) or not _owner(target) or attacker != active.get(attacker["side"]):
        return _result("rejected", "runtime_population_bomb_active_identity_unavailable", base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {**base, "action_id": action.get("action_id"), "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_metadata_authority": deepcopy(metadata_authority)}
    if metadata_authority.get("status") != "resolved":
        return _result(metadata_authority.get("status", "rejected"), metadata_authority.get("reason", "population_bomb_move_metadata_unavailable"), common)
    classification = _classification(metadata_authority.get("metadata"), action.get("identity"))
    if classification.get("status") != "resolved":
        return _result(classification["status"], classification["reason"], {**common, "classification": classification})
    critical = freeze_runtime_d0_critical_hit_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=attacker, target=target, move_metadata=metadata_authority["metadata"])
    source = _mapping(critical.get("source_authority"))
    ability, item = _mapping(source.get("attacker_ability")), _mapping(source.get("attacker_item"))
    if ability.get("status") == "unknown": return _result("incomplete", "population_bomb_attacker_ability_unknown", common)
    if item.get("status") == "unknown": return _result("incomplete", "population_bomb_attacker_item_unknown", common)
    if ability.get("status") not in {"known", "known_absent"} or item.get("status") not in {"known", "known_absent"}:
        return _result("rejected", "population_bomb_modifier_source_authority_invalid", common)
    skill_link, loaded_dice = ability.get("value") == "skill-link", item.get("value") == "loaded-dice"
    if loaded_dice:
        plan = {"kind": "single_accuracy_then_uniform_guaranteed_hits", "support": tuple(range(4, 11)), "conditional_probability": _fraction(Fraction(1, 7)), "semantics": "loaded_dice_precedes_skill_link", "selected_count_source": "loaded-dice"}
    elif skill_link:
        plan = {"kind": "single_accuracy_then_fixed_guaranteed_hits", "count": _MAX_ATTEMPTS, "semantics": "skill_link_fixed_ten"}
    else:
        plan = {"kind": "existing_independent_multiaccuracy", "count": _MAX_ATTEMPTS, "semantics": "exact_known_non_applicability"}
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **common, "classification": classification,
            "attacker_ability": deepcopy(dict(ability)), "attacker_item": deepcopy(dict(item)),
            "modifier_execution_plan": plan, "provenance": "runtime_d0_population_bomb_hit_count_modifier_authority_v1"}


def _classification(metadata: Any, expected_move_id: Any) -> dict[str, Any]:
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != expected_move_id or expected_move_id != _MOVE_ID:
        return {"status": "rejected", "reason": "population_bomb_metadata_action_identity_mismatch"}
    minimum, maximum = metadata.get("min_hits"), metadata.get("max_hits")
    if minimum is None or maximum is None:
        return {"status": "incomplete", "reason": "population_bomb_count_metadata_missing"}
    if not _int(minimum) or not _int(maximum):
        return {"status": "incomplete", "reason": "population_bomb_count_metadata_invalid"}
    if (minimum, maximum) != (_MAX_ATTEMPTS, _MAX_ATTEMPTS) or metadata.get("multiaccuracy") is not True:
        return {"status": "unsupported", "reason": "population_bomb_noncanonical_multiaccuracy_semantics"}
    if metadata.get("category") not in {"physical", "special"} or not _positive_int(metadata.get("power")) or not isinstance(metadata.get("type"), str) or not metadata["type"]:
        return {"status": "incomplete", "reason": "population_bomb_normal_formula_metadata_missing"}
    if metadata.get("always_hit") is not True and (not _int(metadata.get("accuracy")) or not 1 <= metadata["accuracy"] <= 100):
        return {"status": "incomplete", "reason": "population_bomb_per_attempt_accuracy_metadata_missing"}
    if metadata.get("drain") not in {None, 0} or metadata.get("recoil") not in {None, 0} or metadata.get("self_ko") not in {None, False}:
        return {"status": "unsupported", "reason": "population_bomb_drain_recoil_or_self_faint_unsupported"}
    if not _neutral_secondary_metadata(metadata):
        return {"status": "unsupported", "reason": "population_bomb_per_hit_secondary_unsupported"}
    return {"status": "resolved", "move_id": _MOVE_ID, "maximum_attempts": _MAX_ATTEMPTS, "damage_model": "ordinary_normal_formula_per_landed_hit"}


def _base_modifier_authority(critical: Any) -> dict[str, Any]:
    source = critical.get("source_authority") if isinstance(critical, Mapping) else None
    ability = _mapping(_mapping(source).get("attacker_ability"))
    item = _mapping(_mapping(source).get("attacker_item"))
    if ability.get("status") == "unknown":
        return {"status": "incomplete", "reason": "population_bomb_attacker_ability_unknown"}
    if item.get("status") == "unknown":
        return {"status": "incomplete", "reason": "population_bomb_attacker_item_unknown"}
    if ability.get("status") not in {"known", "known_absent"} or item.get("status") not in {"known", "known_absent"}:
        return {"status": "rejected", "reason": "population_bomb_modifier_source_authority_invalid"}
    if ability.get("value") == "skill-link":
        return {"status": "unsupported", "reason": "population_bomb_skill_link_requires_separate_execution_authority"}
    if item.get("value") == "loaded-dice":
        return {"status": "unsupported", "reason": "population_bomb_loaded_dice_requires_separate_execution_authority"}
    return {"status": "resolved", "attacker_ability": deepcopy(dict(ability)), "attacker_item": deepcopy(dict(item)), "semantics": "exact_known_non_applicability_of_population_bomb_count_modifiers", "provenance": "runtime_d0_critical_source_authority_v1"}


def _per_attempt_probability(hit: Any, base: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(hit, Mapping) or hit.get("status") != "resolved":
        return {"status": hit.get("status", "rejected") if isinstance(hit, Mapping) else "rejected", "reason": hit.get("reason", "population_bomb_per_attempt_hit_authority_invalid") if isinstance(hit, Mapping) else "population_bomb_per_attempt_hit_authority_invalid"}
    if any(hit.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) or hit.get("attacker") != base.get("attacker") or hit.get("target") != base.get("target") or hit.get("move_id") != _MOVE_ID:
        return {"status": "rejected", "reason": "population_bomb_per_attempt_hit_authority_binding_mismatch"}
    if hit.get("result") == "always_hit":
        probability = Fraction(1, 1)
    elif _int(hit.get("probability_percent")) and 0 <= hit["probability_percent"] <= 100:
        probability = Fraction(hit["probability_percent"], 100)
    else:
        return {"status": "rejected", "reason": "population_bomb_per_attempt_hit_probability_invalid"}
    miss = 1 - probability
    return {"status": "resolved", "probabilities": {"hit_probability": _fraction(probability), "miss_probability": _fraction(miss), "root_mass": _fraction(probability + miss)}}


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(value.get("decision_owner")):
        return None
    return {"session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"], "source_branch_fingerprint": value["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(value["decision_owner"]))}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and _int(value.get("slot_index")) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _neutral_secondary_metadata(metadata: Mapping[str, Any]) -> bool:
    chance, changes, ailment = metadata.get("effect_chance"), metadata.get("stat_changes"), metadata.get("ailment")
    return chance in (None, 0) and (changes is None or changes == () or changes == [] or changes == {}) and (ailment is None or ailment == "none" or ailment == [])


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _fraction(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_int(value: Any) -> bool:
    return _int(value) and value > 0


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
