"""Extract the pinned Fling Berry Eat/EatItem interaction boundary.

This is intentionally not a generic ability extractor.  It records only the
ability hooks needed to authenticate Fling's Berry-specific source and target
consumption timing.  Intrinsic Berry effects are out of scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_ABILITIES_SHA256 = "a5efb889fb2d8c0bb828eda9d862064cd15344b00191ab2223f82fcdc655e033"
SCHEMA_VERSION = "canonical-fling-berry-eat-item-interactions-v1"
EXTRACTION_SCHEMA_VERSION = "pinned-showdown-fling-berry-eat-item-extraction-v1"
REPOSITORY = "https://github.com/smogon/pokemon-showdown"

_REQUIRED_FLING_FRAGMENTS = (
    "if (item.isBerry)",
    "source.hasAbility('cudchew')",
    "this.singleEvent('EatItem', source.getAbility(), source.abilityState, source, source, move, item)",
    "this.singleEvent('Eat', item, source.itemState, foe, source, move)",
    "this.runEvent('EatItem', foe, source, move, item)",
)

_EXPLICIT_RELEVANT = frozenset({
    "angershell", "asoneglastrier", "asonespectrier", "berserk",
    "cheekpouch", "cudchew", "harvest", "klutz", "neutralizinggas",
    "ripen", "unnerve",
})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocks(source: str) -> dict[str, str]:
    matches = list(re.finditer(r"^\t([a-z0-9]+):\s*\{", source, re.MULTILINE))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else source.rfind("};")
        result[match.group(1)] = source[match.start():end]
    return result


def _hooks(block: str) -> list[str]:
    names = (
        "onEatItem", "onTryEatItem", "onFoeTryEatItem", "onTryHeal",
        "onChangeBoost", "onResidual",
    )
    return [name for name in names if re.search(rf"\b{name}\s*\(", block)]


def _classify(ability_id: str, block: str) -> dict[str, Any] | None:
    hooks = _hooks(block)
    berry_reference = bool(re.search(r"\bisBerry\b|\b[Bb]erry\b", block))
    if ability_id not in _EXPLICIT_RELEVANT and not (
        "onEatItem" in hooks or "onTryEatItem" in hooks or
        "onFoeTryEatItem" in hooks or berry_reference
    ):
        return None

    roles: list[str] = []
    direct_target = False
    try_eat_only = False
    deferred = False

    if ability_id == "cheekpouch":
        if "onEatItem" not in hooks or "this.heal(pokemon.baseMaxhp / 3)" not in block:
            raise ValueError("Cheek Pouch pinned source shape changed")
        roles = ["target_post_eat_item_consequence"]
        direct_target = True
    elif ability_id == "cudchew":
        required = ("onEatItem", "item.isBerry", "this.effectState.berry = item", "this.runEvent('EatItem'")
        if any(fragment not in block for fragment in required):
            raise ValueError("Cud Chew pinned source shape changed")
        roles = ["target_post_eat_item_delayed_reuse", "source_pre_hit_fling_eat_item_handler"]
        direct_target = True
        deferred = True
    elif ability_id == "ripen":
        required = ("onTryHeal", "(effect as Item).isBerry", "return this.chainModify(2)", "onChangeBoost", "onTryEatItem", "onEatItem")
        if any(fragment not in block for fragment in required):
            raise ValueError("Ripen pinned source shape changed")
        roles = [
            "berry_heal_modifier", "berry_boost_modifier",
            "target_post_eat_item_consequence", "try_eat_notification",
        ]
        direct_target = True
    elif ability_id == "unnerve":
        if "onFoeTryEatItem" not in hooks:
            raise ValueError("Unnerve pinned source shape changed")
        roles = ["opposing_try_eat_blocker"]
        try_eat_only = True
    elif ability_id in {"asoneglastrier", "asonespectrier"}:
        if "onFoeTryEatItem" not in hooks:
            raise ValueError("As One pinned source shape changed")
        roles = ["opposing_try_eat_blocker"]
        try_eat_only = True
    elif ability_id in {"angershell", "berserk"}:
        if "onTryEatItem" not in hooks or "sitrusberry" not in block or "oranberry" not in block:
            raise ValueError(f"{ability_id} pinned source shape changed")
        roles = ["healing_item_try_eat_gate"]
        try_eat_only = True
    elif ability_id == "harvest":
        if "pokemon.lastItem" not in block or ".isBerry" not in block:
            raise ValueError("Harvest pinned source shape changed")
        roles = ["future_residual_last_berry_recovery"]
        deferred = True
    elif ability_id == "klutz":
        if "Pokemon.ignoringItem()" not in block:
            raise ValueError("Klutz pinned source shape changed")
        roles = ["source_item_suppression_external_to_eat_event"]
    elif ability_id == "neutralizinggas":
        if "Pokemon#ignoringAbility" not in block:
            raise ValueError("Neutralizing Gas pinned source shape changed")
        roles = ["generic_ability_suppression_external_to_eat_event"]
    else:
        roles = ["source_evidenced_berry_or_eat_item_hook"]
        direct_target = "onEatItem" in hooks
        try_eat_only = not direct_target and ("onTryEatItem" in hooks or "onFoeTryEatItem" in hooks)

    return {
        "showdown_ability_id": ability_id,
        "hooks": hooks,
        "roles": roles,
        "direct_target_eat_item_hook": direct_target,
        "try_eat_only": try_eat_only,
        "future_lifecycle_deferred": deferred,
        "fling_direct_eat_path": (
            "direct_target_eat_item_hook" if direct_target
            else "try_eat_hook_not_invoked_by_fling_direct_eat" if try_eat_only
            else "no_direct_target_eat_item_hook"
        ),
    }


def extract(*, abilities_ts: Path, moves_ts: Path, fling_manifest: Path, output: Path) -> dict[str, Any]:
    if _sha256(abilities_ts) != EXPECTED_ABILITIES_SHA256:
        raise ValueError("pinned abilities.ts SHA-256 mismatch")

    moves_text = moves_ts.read_text(encoding="utf-8")
    if any(fragment not in moves_text for fragment in _REQUIRED_FLING_FRAGMENTS):
        raise ValueError("pinned Fling Berry timing source changed")

    fling = json.loads(fling_manifest.read_text(encoding="utf-8"))
    provenance = fling.get("source_provenance")
    if not isinstance(provenance, dict) or provenance.get("commit_sha") != COMMIT:
        raise ValueError("Fling manifest commit mismatch")
    rows = fling.get("items")
    if not isinstance(rows, list):
        raise ValueError("Fling manifest rows missing")
    berries = sorted(
        row["item_id"] for row in rows
        if isinstance(row, dict) and isinstance(row.get("effect"), dict)
        and row["effect"].get("kind") == "berry_effect"
    )
    if len(berries) != 28 or len(set(berries)) != 28:
        raise ValueError("expected exactly 28 Fling Berry identities")

    ability_text = abilities_ts.read_text(encoding="utf-8")
    blocks = _blocks(ability_text)
    interactions: dict[str, Any] = {}
    for ability_id in sorted(blocks):
        classified = _classify(ability_id, blocks[ability_id])
        if classified is not None:
            interactions[ability_id] = classified

    missing_required = _EXPLICIT_RELEVANT - set(interactions)
    if missing_required:
        raise ValueError(f"required Berry interaction abilities missing: {sorted(missing_required)}")

    no_relevant = sorted(set(blocks) - set(interactions))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_provenance": {
            "repository": REPOSITORY,
            "commit_sha": COMMIT,
            "abilities": {
                "source_path": "data/abilities.ts",
                "local_snapshot": f"data/vendor/pokemon_showdown/{COMMIT}/abilities.ts",
                "sha256": _sha256(abilities_ts),
            },
            "moves": {
                "source_path": "data/moves.ts",
                "local_snapshot": f"data/vendor/pokemon_showdown/{COMMIT}/moves.ts",
                "sha256": _sha256(moves_ts),
            },
            "fling_manifest": {
                "local_snapshot": "data/static/fling_item_effects.json",
                "sha256": _sha256(fling_manifest),
            },
            "extraction_schema_version": EXTRACTION_SCHEMA_VERSION,
        },
        "fling_timing": {
            "source_pre_hit_cud_chew_dispatch": True,
            "source_pre_hit_requires_target_hit": False,
            "target_eat_after_successful_target_hit": True,
            "target_eat_item_after_successful_eat": True,
            "ordinary_held_berry_trigger_used": False,
        },
        "berry_item_ids": berries,
        "ability_scan": {
            "source_ability_count": len(blocks),
            "relevant_ability_count": len(interactions),
            "no_relevant_direct_hook_showdown_ids": no_relevant,
        },
        "interactions": interactions,
    }
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    vendor = root / "data" / "vendor" / "pokemon_showdown" / COMMIT
    parser.add_argument("--abilities-ts", type=Path, default=vendor / "abilities.ts")
    parser.add_argument("--moves-ts", type=Path, default=vendor / "moves.ts")
    parser.add_argument("--fling-manifest", type=Path, default=root / "data" / "static" / "fling_item_effects.json")
    parser.add_argument("--output", type=Path, default=root / "data" / "static" / "fling_berry_eat_item_interactions.json")
    args = parser.parse_args()
    extract(
        abilities_ts=args.abilities_ts,
        moves_ts=args.moves_ts,
        fling_manifest=args.fling_manifest,
        output=args.output,
    )


if __name__ == "__main__":
    main()
