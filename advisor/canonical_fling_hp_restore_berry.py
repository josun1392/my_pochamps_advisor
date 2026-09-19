"""Pinned canonical Oran/Sitrus HP-restore Berry family for Fling target Eat."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.canonical_fling_berry_eat_item_interactions import (
    COMMIT as FLING_BERRY_COMMIT,
    resolve_canonical_fling_berry_item_identity,
)
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata

SCHEMA_VERSION = "canonical-fling-hp-restore-berry-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
EXPECTED_BATTLE_SHA256 = "1d413692d0ed518e992593c0644a5456ab5497cbf3baf2542e65d9fba8d054b1"
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR_ROOT = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT
_ITEMS = _VENDOR_ROOT / "items.ts"
_BATTLE = _VENDOR_ROOT / "sim" / "battle.ts"
_FAMILY = {
    "oran-berry": {
        "showdown_item_id": "oranberry",
        "heal_family": "fixed_hp",
        "fixed_nominal_heal": 10,
    },
    "sitrus-berry": {
        "showdown_item_id": "sitrusberry",
        "heal_family": "quarter_base_max_hp",
        "fixed_nominal_heal": None,
    },
}


def nominal_fling_hp_restore_amount(*, family: dict[str, Any], maximum_hp: int) -> int:
    if not isinstance(maximum_hp, int) or isinstance(maximum_hp, bool) or maximum_hp <= 0:
        raise ValueError("maximum_hp must be a positive integer")
    if family.get("heal_family") == "fixed_hp":
        return 10
    if family.get("heal_family") == "quarter_base_max_hp":
        return max(1, maximum_hp // 4)
    raise ValueError("unsupported heal family")


@lru_cache(maxsize=1)
def _source_binding() -> tuple[dict[str, Any] | None, str | None]:
    if COMMIT != FLING_BERRY_COMMIT:
        return None, "fling_hp_restore_commit_binding_mismatch"
    try:
        items_raw = _ITEMS.read_bytes()
        battle_raw = _BATTLE.read_bytes()
    except OSError:
        return None, "fling_hp_restore_pinned_source_missing"
    items_digest = hashlib.sha256(items_raw).hexdigest()
    battle_digest = hashlib.sha256(battle_raw).hexdigest()
    if items_digest != EXPECTED_ITEMS_SHA256:
        return None, "fling_hp_restore_items_source_hash_mismatch"
    if battle_digest != EXPECTED_BATTLE_SHA256:
        return None, "fling_hp_restore_battle_source_hash_mismatch"

    items = items_raw.decode("utf-8")
    battle = battle_raw.decode("utf-8")
    blocks: dict[str, str] = {}
    for canonical_id, spec in _FAMILY.items():
        showdown_id = spec["showdown_item_id"]
        marker = f"\n\t{showdown_id}: {{"
        start = items.find(marker)
        if start < 0:
            return None, f"fling_hp_restore_{showdown_id}_source_item_missing"
        next_item = re.search(r"\n\t[a-z0-9]+: \{", items[start + len(marker):])
        end = len(items) if next_item is None else start + len(marker) + next_item.start()
        blocks[canonical_id] = items[start:end]

    oran_required = (
        "isBerry: true",
        "if (pokemon.hp <= pokemon.maxhp / 2)",
        "this.runEvent('TryHeal', pokemon, null, this.effect, 10)",
        "this.heal(10);",
    )
    if any(token not in blocks["oran-berry"] for token in oran_required):
        return None, "fling_oran_source_contract_changed"
    sitrus_required = (
        "isBerry: true",
        "if (pokemon.hp <= pokemon.maxhp / 2)",
        "this.runEvent('TryHeal', pokemon, null, this.effect, pokemon.baseMaxhp / 4)",
        "this.heal(pokemon.baseMaxhp / 4);",
    )
    if any(token not in blocks["sitrus-berry"] for token in sitrus_required):
        return None, "fling_sitrus_source_contract_changed"
    battle_required = (
        "heal(damage: number",
        "if (damage && damage <= 1) damage = 1;",
        "damage = this.trunc(damage);",
        "damage = this.runEvent('TryHeal', target, source, effect, damage);",
        "if (!damage) return damage;",
        "if (target.hp >= target.maxhp) return false;",
        "const finalDamage = target.heal(damage, source, effect);",
    )
    if any(token not in battle for token in battle_required):
        return None, "fling_hp_restore_battle_heal_contract_changed"
    return {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "items_source_path": "data/items.ts",
        "items_sha256": items_digest,
        "battle_source_path": "sim/battle.ts",
        "battle_sha256": battle_digest,
        "held_update_threshold": "hp_le_half_then_eat_item",
        "battle_heal_order": "positive_min_one_then_trunc_then_try_heal_then_cap",
    }, None


def resolve_canonical_fling_hp_restore_berry(item_id: Any) -> dict[str, Any]:
    source, error = _source_binding()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "fling_hp_restore_item_identity_unknown"}
    spec = _FAMILY.get(item_id)
    if spec is None:
        return {
            "status": "not_applicable",
            "item_id": item_id,
            "reason": "fling_item_not_oran_sitrus_hp_restore_berry",
        }
    berry = resolve_canonical_fling_berry_item_identity(item_id)
    metadata = resolve_canonical_fling_item_metadata(item_id)
    showdown_id = spec["showdown_item_id"]
    if berry.get("status") != "resolved":
        return {
            "status": "rejected", "item_id": item_id,
            "reason": berry.get("reason", "fling_hp_restore_berry_identity_binding_invalid"),
        }
    if (
        metadata.get("status") != "resolved"
        or metadata.get("item_id") != item_id
        or metadata.get("flingable") is not True
        or metadata.get("base_power") != 10
        or metadata.get("effect", {}).get("kind") != "berry_effect"
        or metadata.get("effect", {}).get("item_id") != showdown_id
        or metadata.get("support_status") != "unsupported_now"
        or metadata.get("source", {}).get("upstream_item_id") != showdown_id
        or metadata.get("source", {}).get("upstream_commit") != COMMIT
    ):
        return {
            "status": "rejected", "item_id": item_id,
            "reason": "fling_hp_restore_manifest_binding_invalid",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "item_id": item_id,
        "showdown_item_id": showdown_id,
        "effect_family": "fling_hp_restore_berry",
        "heal_family": spec["heal_family"],
        "fixed_nominal_heal": spec["fixed_nominal_heal"],
        "fling_base_power": 10,
        "is_berry": True,
        "ordinary_held_threshold_applies_to_fling_target_eat": False,
        "sitrus_max_hp_basis": "maintained_exact_runtime_max_hp",
        "battle_heal_rounding": "min_one_then_trunc",
        "berry_identity_authority": berry,
        "fling_item_metadata": metadata,
        "source_provenance": source,
        "provenance": "pinned_showdown_fling_oran_sitrus_hp_restore_berry_v1",
    }
