"""Read-only resolver for the pinned Fling Berry Eat/EatItem interaction manifest."""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-fling-berry-eat-item-interactions-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ABILITIES_SHA256 = "a5efb889fb2d8c0bb828eda9d862064cd15344b00191ab2223f82fcdc655e033"

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _ROOT / "data" / "static" / "fling_berry_eat_item_interactions.json"
_FLING_MANIFEST = _ROOT / "data" / "static" / "fling_item_effects.json"
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _showdown_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "fling_berry_interaction_manifest_unavailable"
    if raw.get("schema_version") != SCHEMA_VERSION:
        return None, "fling_berry_interaction_manifest_schema_invalid"
    provenance = raw.get("source_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("repository") != "https://github.com/smogon/pokemon-showdown" or provenance.get("commit_sha") != COMMIT:
        return None, "fling_berry_interaction_manifest_provenance_invalid"
    abilities = provenance.get("abilities")
    moves = provenance.get("moves")
    fling_manifest = provenance.get("fling_manifest")
    if not all(isinstance(row, Mapping) for row in (abilities, moves, fling_manifest)):
        return None, "fling_berry_interaction_manifest_source_shape_invalid"
    if abilities.get("source_path") != "data/abilities.ts" or abilities.get("sha256") != EXPECTED_ABILITIES_SHA256:
        return None, "fling_berry_interaction_abilities_provenance_invalid"
    ability_path = _ROOT / str(abilities.get("local_snapshot", ""))
    moves_path = _ROOT / str(moves.get("local_snapshot", ""))
    if not ability_path.is_file() or not moves_path.is_file() or not _FLING_MANIFEST.is_file():
        return None, "fling_berry_interaction_source_missing"
    if _sha256(ability_path) != abilities.get("sha256") or _sha256(moves_path) != moves.get("sha256") or _sha256(_FLING_MANIFEST) != fling_manifest.get("sha256"):
        return None, "fling_berry_interaction_source_hash_mismatch"

    berry_ids = raw.get("berry_item_ids")
    scan = raw.get("ability_scan")
    interactions = raw.get("interactions")
    timing = raw.get("fling_timing")
    if not isinstance(berry_ids, list) or len(berry_ids) != 28 or len(set(berry_ids)) != 28 or not all(isinstance(value, str) and value for value in berry_ids):
        return None, "fling_berry_interaction_berry_inventory_invalid"
    if not isinstance(scan, Mapping) or not isinstance(interactions, Mapping) or not isinstance(timing, Mapping):
        return None, "fling_berry_interaction_manifest_shape_invalid"
    no_relevant = scan.get("no_relevant_direct_hook_showdown_ids")
    if not isinstance(no_relevant, list) or not all(isinstance(value, str) and value for value in no_relevant):
        return None, "fling_berry_interaction_ability_scan_invalid"
    if set(interactions) & set(no_relevant):
        return None, "fling_berry_interaction_ability_partition_invalid"
    if scan.get("source_ability_count") != len(interactions) + len(no_relevant) or scan.get("relevant_ability_count") != len(interactions):
        return None, "fling_berry_interaction_ability_count_invalid"
    required_timing = {
        "source_pre_hit_cud_chew_dispatch": True,
        "source_pre_hit_requires_target_hit": False,
        "target_eat_after_successful_target_hit": True,
        "target_eat_item_after_successful_eat": True,
        "ordinary_held_berry_trigger_used": False,
    }
    if dict(timing) != required_timing:
        return None, "fling_berry_interaction_timing_invalid"

    try:
        current_fling = json.loads(_FLING_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "fling_manifest_unavailable"
    current_berries = sorted(
        row["item_id"] for row in current_fling.get("items", [])
        if isinstance(row, Mapping) and isinstance(row.get("effect"), Mapping)
        and row["effect"].get("kind") == "berry_effect"
    )
    if current_berries != sorted(berry_ids):
        return None, "fling_berry_interaction_inventory_binding_mismatch"

    for ability_id, row in interactions.items():
        if not isinstance(ability_id, str) or not isinstance(row, Mapping) or row.get("showdown_ability_id") != ability_id:
            return None, "fling_berry_interaction_ability_row_invalid"
        if not isinstance(row.get("hooks"), list) or not isinstance(row.get("roles"), list):
            return None, "fling_berry_interaction_ability_row_invalid"
        if not isinstance(row.get("direct_target_eat_item_hook"), bool) or not isinstance(row.get("try_eat_only"), bool) or not isinstance(row.get("future_lifecycle_deferred"), bool):
            return None, "fling_berry_interaction_ability_row_invalid"
        if row.get("fling_direct_eat_path") not in {
            "direct_target_eat_item_hook",
            "try_eat_hook_not_invoked_by_fling_direct_eat",
            "no_direct_target_eat_item_hook",
        }:
            return None, "fling_berry_interaction_ability_row_invalid"
    return raw, None


def resolve_canonical_fling_berry_item_identity(item_id: Any) -> dict[str, Any]:
    manifest, error = _load()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "fling_berry_item_identity_unknown"}
    if item_id not in manifest["berry_item_ids"]:
        return {"status": "not_applicable", "item_id": item_id, "reason": "fling_item_not_berry_effect"}
    return {
        "status": "resolved",
        "item_id": item_id,
        "interaction_manifest_schema": SCHEMA_VERSION,
        "source_commit": COMMIT,
        "provenance": "pinned_showdown_fling_berry_identity_v1",
    }


def resolve_canonical_fling_berry_ability_interaction(ability_id: Any) -> dict[str, Any]:
    manifest, error = _load()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(ability_id, str) or not ability_id:
        return {"status": "incomplete", "reason": "fling_berry_ability_identity_unknown"}
    showdown_id = _showdown_id(ability_id)
    row = manifest["interactions"].get(showdown_id)
    if isinstance(row, Mapping):
        return {
            "status": "resolved",
            "ability_id": ability_id,
            "showdown_ability_id": showdown_id,
            "classification": dict(row),
            "provenance": "pinned_showdown_fling_berry_ability_interaction_v1",
        }
    if showdown_id in set(manifest["ability_scan"]["no_relevant_direct_hook_showdown_ids"]):
        return {
            "status": "resolved",
            "ability_id": ability_id,
            "showdown_ability_id": showdown_id,
            "classification": {
                "showdown_ability_id": showdown_id,
                "hooks": [],
                "roles": [],
                "direct_target_eat_item_hook": False,
                "try_eat_only": False,
                "future_lifecycle_deferred": False,
                "fling_direct_eat_path": "no_direct_target_eat_item_hook",
            },
            "provenance": "pinned_showdown_fling_berry_ability_negative_scan_v1",
        }
    return {
        "status": "incomplete",
        "ability_id": ability_id,
        "showdown_ability_id": showdown_id,
        "reason": "fling_berry_ability_not_in_pinned_source_scan",
    }


def resolve_canonical_fling_berry_timing() -> dict[str, Any]:
    manifest, error = _load()
    if error:
        return {"status": "rejected", "reason": error}
    return {
        "status": "resolved",
        "timing": dict(manifest["fling_timing"]),
        "source_commit": COMMIT,
        "provenance": "pinned_showdown_fling_berry_timing_v1",
    }
