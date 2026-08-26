"""Strict D0 authority for Skill Link / Loaded Dice 2--5 hit modifiers."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_critical_hit_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-variable-multi-hit-count-modifier-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SUPPORTED_MOVES = frozenset({"bullet-seed", "rock-blast"})


def freeze_runtime_d0_variable_multi_hit_count_modifier_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
    critical_hit_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze the exact count distribution; never neutralize unknown sources."""
    base = _base(strategy_d0, attacker, target, move_metadata)
    if base is None:
        return _result("rejected", "variable_multi_hit_modifier_identity_or_metadata_mismatch", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    classification = _classification(move_metadata)
    if isinstance(classification, str):
        return _result("incomplete" if classification.endswith("metadata_missing") else "unsupported", classification, base)
    critical = critical_hit_authority or freeze_runtime_d0_critical_hit_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=attacker, target=target, move_metadata=move_metadata,
    )
    if not _critical_binding(critical, base):
        return _result("rejected", "variable_multi_hit_modifier_critical_authority_binding_mismatch", base)
    source = critical.get("source_authority") if isinstance(critical, Mapping) else None
    ability = _mapping(source).get("attacker_ability")
    item = _mapping(source).get("attacker_item")
    ability, item = _mapping(ability), _mapping(item)
    if ability.get("status") == "unknown":
        return _result("incomplete", "variable_multi_hit_attacker_ability_unknown", base)
    if item.get("status") == "unknown":
        return _result("incomplete", "variable_multi_hit_attacker_item_unknown", base)
    if ability.get("status") not in {"known", "known_absent"} or item.get("status") not in {"known", "known_absent"}:
        return _result("rejected", "variable_multi_hit_modifier_source_authority_invalid", base)
    # Tier-A ordering is canonical: Skill Link converts the range to five
    # before Loaded Dice's below-four reroll can apply.
    if ability.get("value") == "skill-link":
        modifier, distribution = "skill_link", _distribution(((5, Fraction(1, 1)),))
    elif item.get("value") == "loaded-dice":
        modifier, distribution = "loaded_dice", _distribution(((4, Fraction(1, 2)), (5, Fraction(1, 2))))
    else:
        modifier, distribution = "none", _distribution(((2, Fraction(7, 20)), (3, Fraction(7, 20)), (4, Fraction(3, 20)), (5, Fraction(3, 20))))
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "move_id": move_metadata["move_id"],
        "attacker_ability": deepcopy(dict(ability)), "attacker_item": deepcopy(dict(item)),
        "modifier": modifier,
        "hit_count_distribution": distribution,
        "root_mass": {"numerator": 1, "denominator": 1},
        "critical_hit_authority": deepcopy(dict(critical)),
        "provenance": "runtime_d0_exact_skill_link_loaded_dice_hit_count_modifier_authority_v1",
    }


def _base(d0: Any, attacker: Any, target: Any, move: Any) -> dict[str, Any] | None:
    active = d0.get("active_owners") if isinstance(d0, Mapping) else None
    if (
        not isinstance(d0, Mapping) or d0.get("status") != "resolved"
        or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1"
        or not _owner(attacker) or not _owner(target) or not isinstance(active, Mapping)
        or attacker != d0.get("decision_owner") or active.get(attacker["side"]) != dict(attacker)
        or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]
        or not isinstance(move, Mapping)
    ):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)),
        "move_id": move.get("move_id"),
    }


def _classification(move: Mapping[str, Any]) -> str | None:
    if not isinstance(move.get("move_id"), str) or not move["move_id"]:
        return "variable_multi_hit_modifier_metadata_missing"
    if move["move_id"] not in _SUPPORTED_MOVES or (move.get("min_hits"), move.get("max_hits")) != (2, 5):
        return "variable_multi_hit_modifier_family_unsupported"
    return None


def _critical_binding(value: Any, base: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and all(value.get(key) == base[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target")) and _mapping(value.get("move")).get("move_id") == base["move_id"]


def _distribution(rows: tuple[tuple[int, Fraction], ...]) -> tuple[dict[str, Any], ...]:
    if sum((probability for _count, probability in rows), Fraction()) != Fraction(1, 1):
        raise ValueError("exact modifier distribution must have unit mass")
    return tuple({"hit_count": count, "probability": {"numerator": probability.numerator, "denominator": probability.denominator}} for count, probability in rows)


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
