"""Pinned canonical Leppa Berry PP restoration contract for Fling target Eat."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.canonical_fling_berry_eat_item_interactions import (
    COMMIT as FLING_BERRY_COMMIT,
    resolve_canonical_fling_berry_item_identity,
)
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata

SCHEMA_VERSION = "canonical-fling-leppa-pp-restore-berry-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
EXPECTED_MOVES_SHA256 = "1ded02b7fda2e4cfcc28ad753190f83c3db3ac5947d2825c2663e66d8ce83d6b"
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT
_ITEMS = _VENDOR / "items.ts"
_MOVES = _VENDOR / "moves.ts"


@lru_cache(maxsize=1)
def _source() -> tuple[dict[str, Any] | None, str | None]:
    if COMMIT != FLING_BERRY_COMMIT:
        return None, "fling_leppa_commit_binding_mismatch"
    try:
        items_raw = _ITEMS.read_bytes()
        moves_raw = _MOVES.read_bytes()
    except OSError:
        return None, "fling_leppa_pinned_source_missing"
    items_hash = hashlib.sha256(items_raw).hexdigest()
    moves_hash = hashlib.sha256(moves_raw).hexdigest()
    if items_hash != EXPECTED_ITEMS_SHA256:
        return None, "fling_leppa_items_source_hash_mismatch"
    if moves_hash != EXPECTED_MOVES_SHA256:
        return None, "fling_leppa_moves_source_hash_mismatch"
    items = items_raw.decode("utf-8")
    moves = moves_raw.decode("utf-8")
    marker = "\n\tleppaberry: {"
    start = items.find(marker)
    if start < 0:
        return None, "fling_leppa_source_item_missing"
    end = items.find("\n\tlevelball: {", start)
    block = items[start:end if end >= 0 else len(items)]
    required = (
        "isBerry: true",
        "pokemon.moveSlots.some(move => move.pp === 0)",
        "pokemon.moveSlots.find(move => move.pp === 0) ||",
        "pokemon.moveSlots.find(move => move.pp < move.maxpp)",
        "pokemon.hasAbility('ripen') ? 20 : 10",
        "Math.min(moveSlot.pp + addedPP, moveSlot.maxpp)",
    )
    if any(token not in block for token in required):
        return None, "fling_leppa_items_contract_changed"
    fling_start = moves.find("\n\tfling: {")
    fling_end = moves.find("\n\tfloralhealing: {", fling_start)
    fling = moves[fling_start:fling_end if fling_end >= 0 else len(moves)]
    move_required = (
        "if (this.singleEvent('Eat', item, source.itemState, foe, source, move))",
        "this.runEvent('EatItem', foe, source, move, item);",
        "if (item.id === 'leppaberry') foe.staleness = 'external';",
        "if (item.onEat) foe.ateBerry = true;",
    )
    if any(token not in fling for token in move_required):
        return None, "fling_leppa_moves_contract_changed"
    return {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "items_source_path": "data/items.ts",
        "items_sha256": items_hash,
        "moves_source_path": "data/moves.ts",
        "moves_sha256": moves_hash,
        "selection_priority": ("first_zero_pp", "first_missing_pp"),
        "ordinary_restore": 10,
        "ripen_restore": 20,
        "external_staleness_after_successful_eat_item": True,
    }, None


def resolve_canonical_fling_leppa_pp_restore_berry(item_id: Any) -> dict[str, Any]:
    source, error = _source()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "fling_leppa_item_identity_unknown"}
    if item_id != "leppa-berry":
        return {
            "status": "not_applicable",
            "item_id": item_id,
            "reason": "fling_item_not_leppa_pp_restore_berry",
        }
    berry = resolve_canonical_fling_berry_item_identity(item_id)
    metadata = resolve_canonical_fling_item_metadata(item_id)
    if (
        berry.get("status") != "resolved"
        or metadata.get("status") != "resolved"
        or metadata.get("item_id") != item_id
        or metadata.get("base_power") != 10
        or metadata.get("flingable") is not True
        or metadata.get("effect", {}).get("kind") != "berry_effect"
        or metadata.get("effect", {}).get("item_id") != "leppaberry"
        or metadata.get("support_status") != "unsupported_now"
    ):
        return {
            "status": "rejected",
            "item_id": item_id,
            "reason": "fling_leppa_manifest_binding_invalid",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "item_id": "leppa-berry",
        "showdown_item_id": "leppaberry",
        "effect_family": "fling_leppa_pp_restore",
        "fling_base_power": 10,
        "ordinary_restore_amount": 10,
        "ripen_restore_amount": 20,
        "selection_priority": ("first_zero_pp", "first_missing_pp"),
        "ordinary_held_zero_pp_trigger_applies_to_fling_target_eat": False,
        "external_staleness": {
            "value": True,
            "source": "fling_leppa_successful_target_eat",
            "timing": "after_target_eat_item_dispatch",
        },
        "berry_identity_authority": berry,
        "fling_item_metadata": metadata,
        "source_provenance": source,
        "provenance": "pinned_showdown_fling_leppa_pp_restore_v1",
    }
