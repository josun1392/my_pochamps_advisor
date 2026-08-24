"""Detached authority for catalogued deterministic damaging-move stage effects."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

_STATS = frozenset({"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"})
_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "deterministic_move_stage_effects.json"

def build_deterministic_move_stage_effect_metadata(move_metadata: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Classify detached canonical move metadata without applying any stage."""
    move_id = _value(move_metadata, "move_id")
    if not isinstance(move_id, str) or not move_id: return _result("unknown", "canonical_move_identity_required")
    changes = _changes(_value(move_metadata, "stat_changes"))
    if changes is None: return _result("unknown", "canonical_stat_changes_unknown", move_id=move_id)
    if not changes: return _result("no_effect", "no_canonical_stage_effect", move_id=move_id)
    chance = _value(move_metadata, "effect_chance")
    if isinstance(chance, bool) or not isinstance(chance, int) or not 0 <= chance <= 100: return _result("unknown", "canonical_effect_chance_unknown", move_id=move_id)
    if chance != 100: return _result("probabilistic", "canonical_stage_effect_not_guaranteed", move_id=move_id)
    entry = _catalog().get(move_id)
    if not isinstance(entry, Mapping): return _result("unsupported", "deterministic_stage_effect_conditions_unmodeled", move_id=move_id)
    effects = _effects(entry.get("effects"))
    if effects is None or tuple((row["stat"], row["delta"]) for row in effects) != changes: return _result("unsupported", "catalog_metadata_stage_effect_mismatch", move_id=move_id)
    if _value(move_metadata, "category") != entry.get("category"): return _result("unsupported", "catalog_metadata_move_category_mismatch", move_id=move_id)
    conditions = entry.get("conditions")
    if not _conditions(conditions): return _result("unsupported", "catalog_stage_effect_conditions_invalid", move_id=move_id)
    return {"status": "deterministic", "schema_version": "deterministic-move-stage-effect-authority-v1", "move_id": move_id, "effects": deepcopy(effects), "conditions": deepcopy(dict(conditions)), "provenance": "canonical-maintained-gen9-mechanics-catalog-v1+canonical-pokeapi-move-metadata"}

def _catalog() -> Mapping[str, Any]:
    try: value = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {}
    return value.get("moves", {}) if isinstance(value, Mapping) else {}

def _value(metadata: Mapping[str, Any] | Any, key: str) -> Any: return metadata.get(key) if isinstance(metadata, Mapping) else getattr(metadata, key, None)

def _changes(value: Any) -> tuple[tuple[str, int], ...] | None:
    if value is None: return None
    if not isinstance(value, (list, tuple)): return None
    result = []
    for item in value:
        stat, delta = (item.get("stat"), item.get("change")) if isinstance(item, Mapping) else item if isinstance(item, tuple) and len(item) == 2 else (None, None)
        if not isinstance(stat, str) or stat not in _STATS or isinstance(delta, bool) or not isinstance(delta, int) or not -6 <= delta <= 6 or delta == 0: return None
        result.append((stat, delta))
    return tuple(result)

def _effects(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list) or not value: return None
    result = []
    for item in value:
        if not isinstance(item, Mapping) or item.get("owner") not in {"self", "target"}: return None
        stat, delta = item.get("stat"), item.get("delta")
        if not isinstance(stat, str) or stat not in _STATS or isinstance(delta, bool) or not isinstance(delta, int) or not -6 <= delta <= 6 or delta == 0: return None
        result.append({"owner": item["owner"], "stat": stat, "delta": delta})
    return result

def _conditions(value: Any) -> bool: return isinstance(value, Mapping) and all(isinstance(value.get(key), bool) for key in ("requires_successful_damaging_hit", "blocked_by_substitute", "target_must_survive"))
def _result(status: str, reason: str, *, move_id: str | None = None) -> dict[str, Any]:
    value = {"status": status, "reason": reason, "schema_version": "deterministic-move-stage-effect-authority-v1"}
    if move_id is not None: value["move_id"] = move_id
    return value
