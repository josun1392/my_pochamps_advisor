"""Pinned Showdown authority for persistent Berry-eaten state and Belch gating."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
REPOSITORY = "https://github.com/smogon/pokemon-showdown"
POKEMON_SHA256 = "803d22124bef93566c4654e5a20a95f7dc7a8818e8b242a27b56bc6dc951b0df"

_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT

_REQUIRED_POKEMON = (
    "ateBerry: boolean",
    "this.ateBerry = false;",
    "this.battle.singleEvent('Eat', item, this.itemState, this, source, sourceEffect);",
    "this.battle.runEvent('EatItem', this, source, sourceEffect, item);",
    "this.usedItemThisTurn = true;",
    "this.ateBerry = true;",
    "clearVolatile(",
    "faint(",
)
_MOVE_BLOCKS = {
    "belch": ("belch: {", "\n\tbellydrum: {"),
    "bug-bite": ("bugbite: {", "\n\tbugbuzz: {"),
    "fling": ("fling: {", "\n\tflipturn: {"),
    "pluck": ("pluck: {", "\n\tpoisonfang: {"),
}
_ABILITY_BLOCKS = {
    "cud-chew": ("cudchew: {", "\n\tcuriousmedicine: {"),
}


def _bounded_block(text: str, start_marker: str, end_marker: str) -> str | None:
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0 or end <= start:
        return None
    return text[start:end]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def resolve_canonical_berry_eaten_lifecycle() -> dict[str, Any]:
    pokemon = _VENDOR / "sim" / "pokemon.ts"
    moves = _VENDOR / "moves.ts"
    abilities = _VENDOR / "abilities.ts"
    if not pokemon.is_file() or not moves.is_file() or not abilities.is_file():
        return {"status": "rejected", "reason": "pinned_berry_eaten_source_missing"}
    if _sha256(pokemon) != POKEMON_SHA256:
        return {"status": "rejected", "reason": "pinned_showdown_pokemon_source_hash_mismatch"}
    p = pokemon.read_text(encoding="utf-8")
    m = moves.read_text(encoding="utf-8")
    a = abilities.read_text(encoding="utf-8")
    if any(fragment not in p for fragment in _REQUIRED_POKEMON):
        return {"status": "rejected", "reason": "pinned_pokemon_berry_eaten_contract_changed"}
    move_blocks = {
        name: _bounded_block(m, start, end)
        for name, (start, end) in _MOVE_BLOCKS.items()
    }
    ability_blocks = {
        name: _bounded_block(a, start, end)
        for name, (start, end) in _ABILITY_BLOCKS.items()
    }
    if any(block is None for block in move_blocks.values()):
        return {"status": "rejected", "reason": "pinned_move_berry_eaten_block_missing"}
    if any(block is None for block in ability_blocks.values()):
        return {"status": "rejected", "reason": "pinned_ability_berry_eaten_block_missing"}
    belch = move_blocks["belch"]
    bug_bite = move_blocks["bug-bite"]
    fling = move_blocks["fling"]
    pluck = move_blocks["pluck"]
    cud_chew = ability_blocks["cud-chew"]
    if (
        "if (!pokemon.ateBerry) pokemon.disableMove('belch');" not in belch
        or "return source.ateBerry;" not in belch
        or "if (item.onEat) foe.ateBerry = true;" not in fling
        or "if (item.onEat) source.ateBerry = true;" not in bug_bite
        or "if (item.onEat) source.ateBerry = true;" not in pluck
    ):
        return {"status": "rejected", "reason": "pinned_move_berry_eaten_contract_changed"}
    if "if (item.onEat) pokemon.ateBerry = true;" not in cud_chew:
        return {"status": "rejected", "reason": "pinned_ability_berry_eaten_contract_changed"}
    clear_start = p.find("\n\tclearVolatile(")
    faint_start = p.find("\n\tfaint(")
    if clear_start < 0 or faint_start < 0:
        return {"status": "rejected", "reason": "pinned_berry_eaten_lifecycle_method_missing"}
    clear_end = p.find("\n\thasType(", clear_start)
    faint_end = p.find("\n\tdamage(", faint_start)
    if clear_end < 0 or faint_end < 0:
        return {"status": "rejected", "reason": "pinned_berry_eaten_lifecycle_method_boundary_missing"}
    clear_block = p[clear_start:clear_end]
    faint_block = p[faint_start:faint_end]
    if "ateBerry =" in clear_block or "ateBerry =" in faint_block:
        return {"status": "rejected", "reason": "pinned_berry_eaten_persistence_contract_changed"}
    return {
        "status": "resolved",
        "repository": REPOSITORY,
        "commit_sha": COMMIT,
        "pokemon_source_path": "sim/pokemon.ts",
        "pokemon_sha256": POKEMON_SHA256,
        "initial_state": "known_false",
        "generic_successful_eat_item_transition": "known_true",
        "clear_volatile_resets": False,
        "faint_resets": False,
        "direct_writers": ("fling", "bug-bite", "pluck", "cud-chew"),
        "belch_selection_reader": True,
        "belch_execution_reader": True,
        "provenance": "pinned_showdown_berry_eaten_lifecycle_v1",
    }
