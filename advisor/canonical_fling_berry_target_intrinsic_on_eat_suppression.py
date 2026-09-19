"""Pinned target-side item-suppression contract for Fling Berry intrinsic onEat."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "canonical-fling-berry-target-intrinsic-on-eat-suppression-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
_BATTLE_SHA256 = "1d413692d0ed518e992593c0644a5456ab5497cbf3baf2542e65d9fba8d054b1"
_POKEMON_SHA256 = "803d22124bef93566c4654e5a20a95f7dc7a8818e8b242a27b56bc6dc951b0df"
_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT
_IGNORE_KLUTZ_IDS = frozenset({
    "abilityshield",
    "machobrace",
    "poweranklet",
    "powerband",
    "powerbelt",
    "powerbracer",
    "powerlens",
    "powerweight",
})


def _showdown_id(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _blocks(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^\t([a-z0-9]+): \{", text, flags=re.MULTILINE))
    out: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        out[match.group(1)] = text[match.start():end]
    return out


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any] | None, str | None]:
    paths = {
        "items": (_VENDOR / "items.ts", _ITEMS_SHA256),
        "battle": (_VENDOR / "sim" / "battle.ts", _BATTLE_SHA256),
        "pokemon": (_VENDOR / "sim" / "pokemon.ts", _POKEMON_SHA256),
    }
    raw: dict[str, bytes] = {}
    for key, (path, expected) in paths.items():
        try:
            value = path.read_bytes()
        except OSError:
            return None, f"fling_berry_target_item_{key}_source_missing"
        if hashlib.sha256(value).hexdigest().lower() != expected.lower():
            return None, f"fling_berry_target_item_{key}_source_hash_mismatch"
        raw[key] = value

    items = raw["items"].decode("utf-8")
    battle = raw["battle"].decode("utf-8")
    pokemon = raw["pokemon"].decode("utf-8")

    battle_required = (
        "effect.effectType === 'Item'",
        "(target instanceof Pokemon) && target.ignoringItem()",
        "handler suppressed by Embargo, Klutz or Magic Room",
        "return relayVar;",
    )
    if any(token not in battle for token in battle_required):
        return None, "fling_berry_target_item_battle_single_event_contract_changed"

    pokemon_required = (
        "ignoringItem(isFling = false)",
        "this.volatiles['embargo'] || this.battle.field.pseudoWeather['magicroom']",
        "if (isFling) return this.battle.gen >= 5 && this.hasAbility('klutz');",
        "return !this.getItem().ignoreKlutz && this.hasAbility('klutz');",
    )
    if any(token not in pokemon for token in pokemon_required):
        return None, "fling_berry_target_item_ignoring_item_contract_changed"

    blocks = _blocks(items)
    actual = frozenset(
        item_id for item_id, block in blocks.items()
        if "ignoreKlutz: true" in block
    )
    if actual != _IGNORE_KLUTZ_IDS:
        return None, "fling_berry_target_item_ignore_klutz_set_changed"

    return {
        "blocks": blocks,
        "ignore_klutz_ids": actual,
        "source_provenance": {
            "repository": "https://github.com/smogon/pokemon-showdown",
            "commit_sha": COMMIT,
            "battle_source_path": "sim/battle.ts",
            "battle_sha256": _BATTLE_SHA256,
            "pokemon_source_path": "sim/pokemon.ts",
            "pokemon_sha256": _POKEMON_SHA256,
            "items_source_path": "data/items.ts",
            "items_sha256": _ITEMS_SHA256,
            "single_event_item_callback_suppression": "target_ignoring_item_returns_existing_relay_value",
            "ordinary_target_klutz_rule": "suppressed_unless_current_held_item_ignore_klutz_true",
        },
    }, None


def resolve_canonical_fling_berry_target_intrinsic_on_eat_suppression_contract() -> dict[str, Any]:
    loaded, error = _load()
    if error:
        return {"status": "rejected", "reason": error}
    assert loaded is not None
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "ignore_klutz_showdown_item_ids": tuple(sorted(loaded["ignore_klutz_ids"])),
        "source_provenance": dict(loaded["source_provenance"]),
        "provenance": "pinned_showdown_fling_berry_target_intrinsic_on_eat_suppression_v1",
    }


def resolve_canonical_target_item_ignore_klutz(item_id: Any) -> dict[str, Any]:
    loaded, error = _load()
    if error:
        return {"status": "rejected", "reason": error}
    if not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "reason": "target_held_item_identity_unknown"}
    assert loaded is not None
    showdown_id = _showdown_id(item_id)
    block = loaded["blocks"].get(showdown_id)
    if block is None:
        return {
            "status": "incomplete",
            "item_id": item_id,
            "showdown_item_id": showdown_id,
            "reason": "target_held_item_not_authenticated_in_pinned_items_source",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "item_id": item_id,
        "showdown_item_id": showdown_id,
        "ignore_klutz": showdown_id in loaded["ignore_klutz_ids"],
        "source_provenance": dict(loaded["source_provenance"]),
        "provenance": "pinned_showdown_target_item_ignore_klutz_v1",
    }
