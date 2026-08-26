"""Strict D0 authority for a future ordinary variable multi-hit executor.

This owner deliberately freezes only an action-level hit-count distribution.
It does not turn an aggregate multi-hit damage result into per-hit execution.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from advisor.damage.multihit import MultiHitAttacker, MultiHitMove
from advisor.probability.multi_hit import compute_multihit_distribution
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_strict_critical_hit_probability_assessment,
    freeze_runtime_d0_critical_hit_authority,
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)
from llm.advisor_runtime_d0_variable_multi_hit_count_modifier_authority import (
    freeze_runtime_d0_variable_multi_hit_count_modifier_authority,
)


SCHEMA_VERSION = "runtime-d0-variable-two-to-five-hit-count-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
# Explicit mechanics catalog, never a move-name or metadata-shape heuristic.
_SUPPORTED_ORDINARY_TWO_TO_FIVE_HIT_MOVES = frozenset({"bullet-seed", "rock-blast"})


def freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze exact standard 2--5 hit-count authority for one own attack."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    active = strategy_d0.get("active_owners", {})
    own = strategy_d0.get("decision_owner")
    opponent = active.get("opponent" if isinstance(own, Mapping) and own.get("side") == "self" else "self")
    if not _owner(own) or not _owner(opponent) or own != active.get(own["side"]):
        return _result("rejected", "runtime_variable_multi_hit_active_identity_unavailable", base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {
        **base, "action_id": action.get("action_id"), "attacker": deepcopy(dict(own)),
        "target": deepcopy(dict(opponent)), "move_metadata_authority": deepcopy(metadata_authority),
        "provenance": "runtime_d0_canonical_variable_two_to_five_hit_count_execution_authority_v1",
    }
    if metadata_authority.get("status") != "resolved":
        return _result(metadata_authority.get("status", "rejected"), metadata_authority.get("reason", "variable_multi_hit_move_metadata_unavailable"), common)
    metadata = metadata_authority.get("metadata")
    classification = _classification(metadata, action.get("identity"))
    if classification.get("status") != "resolved":
        return _result(classification["status"], classification["reason"], {**common, "classification": classification})
    # The existing critical authority is also the strict current ability/item
    # boundary.  Skill Link and Loaded Dice therefore cannot be ignored: each
    # is unsupported there, while missing values remain incomplete.
    critical_source = freeze_runtime_d0_critical_hit_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=own, target=opponent, move_metadata=metadata,
    )
    modifier = freeze_runtime_d0_variable_multi_hit_count_modifier_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=own, target=opponent, move_metadata=metadata,
        critical_hit_authority=critical_source,
    )
    if modifier["status"] != "resolved":
        return _result(modifier["status"], modifier["reason"], {
            **common, "classification": classification,
            "hit_count_modifier_authority": modifier,
            "critical_hit_authority": deepcopy(critical_source),
        })
    critical = build_runtime_d0_strict_critical_hit_probability_assessment(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=own, target=opponent, move_metadata=metadata,
    )
    if critical.get("status") != "resolved":
        return _result(critical.get("status", "rejected"), critical.get("reason", "variable_multi_hit_critical_authority_unavailable"), {
            **common, "classification": classification,
            "hit_count_modifier_authority": modifier,
            "critical_hit_authority": deepcopy(critical),
        })
    distribution = modifier["hit_count_distribution"]
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "move_id": metadata["move_id"], "hit_count_execution": {
            "status": "resolved", "semantics": "canonical_standard_two_to_five_hit_count_before_per_hit_execution",
            "distribution": distribution, "root_mass": {"numerator": 1, "denominator": 1},
        },
        "accuracy_execution": {
            "status": "resolved", "semantics": "action_level_once_before_hit_sequence",
            "accuracy": "always_hit" if metadata.get("always_hit") is True else metadata["accuracy"],
        },
        "per_hit_critical_execution": {
            "status": "resolved", "semantics": "independent_canonical_critical_roll_per_hit",
            "per_hit_critical_probability": deepcopy(critical["critical_probability"]),
            "critical_hit_authority": deepcopy(critical),
        },
        "hit_count_modifier_authority": modifier,
        "execution_exclusions": {
            "aggregate_total_damage": "forbidden", "fixed_two_hit": "handled_by_separate_authority",
            "multiaccuracy": "unsupported", "escalating_power": "unsupported",
            "skill_link_or_loaded_dice": "supported_by_runtime_d0_modifier_authority_v1",
            "per_hit_secondary": "unsupported", "drain_or_recoil": "unsupported",
            "contact_or_item_consumption": "requires_separate_exact_owner",
            "substitute_or_replacement": "requires_separate_exact_owner",
        },
    }


def _classification(metadata: Any, expected_move_id: Any) -> dict[str, Any]:
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != expected_move_id or not isinstance(expected_move_id, str) or not expected_move_id:
        return {"status": "rejected", "reason": "variable_multi_hit_metadata_action_identity_mismatch"}
    minimum, maximum = metadata.get("min_hits"), metadata.get("max_hits")
    if minimum is None or maximum is None:
        return {"status": "incomplete", "reason": "variable_multi_hit_count_metadata_missing"}
    if not _int(minimum) or not _int(maximum):
        return {"status": "incomplete", "reason": "variable_multi_hit_count_metadata_invalid"}
    if (minimum, maximum) != (2, 5):
        return {"status": "unsupported", "reason": "multi_hit_family_not_canonical_variable_two_to_five"}
    if metadata.get("move_id") not in _SUPPORTED_ORDINARY_TWO_TO_FIVE_HIT_MOVES:
        return {"status": "unsupported", "reason": "variable_multi_hit_move_not_in_supported_execution_catalog"}
    if metadata.get("category") not in {"physical", "special"} or not _int(metadata.get("power")) or not isinstance(metadata.get("type"), str) or not metadata["type"]:
        return {"status": "incomplete", "reason": "variable_multi_hit_normal_formula_metadata_missing"}
    if metadata.get("always_hit") is not True and (not _int(metadata.get("accuracy")) or not 1 <= metadata["accuracy"] <= 100):
        return {"status": "incomplete", "reason": "variable_multi_hit_action_accuracy_missing"}
    if metadata.get("multiaccuracy") is True or metadata.get("bp_escalation") is True:
        return {"status": "unsupported", "reason": "variable_multi_hit_multiaccuracy_or_escalating_power_unsupported"}
    if metadata.get("drain") not in {None, 0} or metadata.get("recoil") not in {None, 0} or metadata.get("self_ko") not in {None, False}:
        return {"status": "unsupported", "reason": "variable_multi_hit_drain_recoil_or_self_faint_unsupported"}
    if not _neutral_secondary_metadata(metadata):
        return {"status": "unsupported", "reason": "variable_multi_hit_per_hit_secondary_unsupported"}
    return {"status": "resolved", "move_id": metadata["move_id"], "min_hits": 2, "max_hits": 5, "damage_model": "ordinary_normal_formula_per_hit"}


def _hit_count_modifier_authority(critical: Any) -> dict[str, Any]:
    """Extract the existing exact ability/item facts without raw rereads."""
    if not isinstance(critical, Mapping):
        return {"status": "rejected", "reason": "variable_multi_hit_critical_authority_invalid"}
    source = _mapping(critical.get("source_authority"))
    ability, item = _mapping(source.get("attacker_ability")), _mapping(source.get("attacker_item"))
    if ability.get("status") == "unknown":
        return {"status": "incomplete", "reason": "variable_multi_hit_attacker_ability_unknown"}
    if item.get("status") == "unknown":
        return {"status": "incomplete", "reason": "variable_multi_hit_attacker_item_unknown"}
    if ability.get("status") not in {"known", "known_absent"} or item.get("status") not in {"known", "known_absent"}:
        return {"status": "rejected", "reason": "variable_multi_hit_modifier_authority_invalid"}
    if ability.get("value") == "skill-link":
        return {"status": "unsupported", "reason": "variable_multi_hit_skill_link_requires_separate_execution_authority"}
    if item.get("value") == "loaded-dice":
        return {"status": "unsupported", "reason": "variable_multi_hit_loaded_dice_requires_separate_execution_authority"}
    return {"status": "resolved", "attacker_ability": deepcopy(ability), "attacker_item": deepcopy(item), "provenance": "runtime_d0_critical_source_authority_v1"}


def _standard_distribution(metadata: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | None:
    try:
        raw = compute_multihit_distribution(
            MultiHitMove(metadata["move_id"], multihit=(2, 5), base_power=metadata["power"]),
            MultiHitAttacker(),
        )
    except (TypeError, ValueError, KeyError):
        return None
    if set(raw) != {2, 3, 4, 5} or sum(raw.values(), Fraction(0, 1)) != Fraction(1, 1):
        return None
    return tuple({"hit_count": count, "probability": {"numerator": probability.numerator, "denominator": probability.denominator}} for count, probability in sorted(raw.items()))


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(value.get("decision_owner")):
        return None
    return {"session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"], "source_branch_fingerprint": value["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(value["decision_owner"]))}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and _int(value.get("slot_index")) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _neutral_secondary_metadata(metadata: Mapping[str, Any]) -> bool:
    chance, changes, ailment = metadata.get("effect_chance"), metadata.get("stat_changes"), metadata.get("ailment")
    return chance in (None, 0) and (changes is None or changes == () or changes == [] or changes == {}) and (ailment is None or ailment == "none" or ailment == [])


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
