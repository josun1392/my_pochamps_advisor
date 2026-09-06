"""Statically extract the Champions Fling inventory from pinned Showdown data.

This intentionally does not evaluate TypeScript callbacks.  It only balances
braces and reads the Fling fields consumed by Showdown's Fling move owner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "canonical-fling-item-effects-v1"
EXTRACTION_SCHEMA = "pinned-showdown-fling-static-extraction-v1"


def _blocks(source: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    # Item definitions are exactly one tab indented in Showdown's table;
    # nested `fling` and callback objects are deeper-indented.
    matches = list(re.finditer(r"^\t([a-z0-9]+):\s*\{", source, re.MULTILINE))
    for index, match in enumerate(matches):
        item_id, block_start = match.group(1), match.end() - 1
        # Slicing at the next table-row boundary avoids interpreting arbitrary
        # callback/template implementation details outside this item record.
        block_end = matches[index + 1].start() if index + 1 < len(matches) else source.rfind("};")
        rows[item_id] = source[block_start:block_end]
    return rows


def _matching(value: str, start: int) -> int:
    depth, quote, escaped = 0, None, False
    for index in range(start, len(value)):
        char = value[index]
        if quote:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == quote: quote = None
            continue
        if char in "\"'`": quote = char; continue
        if char == "{": depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0: return index
    raise ValueError("unbalanced TypeScript item block")


def _fling_block(block: str) -> str | None:
    match = re.search(r"\bfling\s*:\s*\{", block)
    return block[match.end() - 1:_matching(block, match.end() - 1) + 1] if match else None


def _record(item_id: str, block: str, commit: str) -> dict:
    fling = _fling_block(block)
    source = {"upstream_item_id": item_id, "upstream_commit": commit, "extraction": EXTRACTION_SCHEMA}
    berry = bool(re.search(r"\bisBerry\s*:\s*true", block))
    default_power = 10 if berry else 90 if re.search(r"\bonPlate\s*:", block) else 70 if re.search(r"\bonDrive\s*:", block) else 80 if re.search(r"\bmegaStone\s*:", block) else 50 if re.search(r"\bonMemory\s*:", block) else None
    if re.search(r"\bonTakeItem\s*:\s*false", block):
        return {"item_id": item_id, "flingable": False, "base_power": None,
                "effect": {"kind": "none", "classification": "explicit_canonical_non_flingable"},
                "support_status": "not_applicable", "source": source}
    if fling is None and default_power is None:
        return {"item_id": item_id, "flingable": False, "base_power": None,
                "effect": {"kind": "none", "classification": "explicit_canonical_non_flingable"},
                "support_status": "not_applicable", "source": source}
    power = re.search(r"\bbasePower\s*:\s*(\d+)", fling or "")
    if fling is not None and not power:
        raise ValueError(f"{item_id}: fling block lacks integer basePower")
    if berry:
        effect, support = {"kind": "berry_effect", "item_id": item_id}, "unsupported_now"
    elif status := re.search(r"\bstatus\s*:\s*['\"]([^'\"]+)", fling or ""):
        condition = {"brn": "burn", "psn": "poison", "tox": "toxic", "par": "paralysis"}.get(status.group(1), status.group(1))
        effect, support = {"kind": "major_status", "condition": condition}, "unsupported_now"
    elif volatile := re.search(r"\bvolatileStatus\s*:\s*['\"]([^'\"]+)", fling or ""):
        effect, support = ({"kind": "flinch"}, "unsupported_now") if volatile.group(1) == "flinch" else ({"kind": "known_unsupported", "upstream_volatile_status": volatile.group(1)}, "unsupported_now")
    elif re.search(r"\beffect\s*:", fling or ""):
        effect, support = {"kind": "known_unsupported", "detail": "upstream_fling_effect_callback"}, "unsupported_now"
    else:
        effect, support = {"kind": "none", "classification": "explicit_no_target_effect"}, "not_applicable"
    return {"item_id": item_id, "flingable": True, "base_power": int(power.group(1)) if power else default_power, "effect": effect, "support_status": support, "source": source}


def extract(*, items_ts: Path, champions: Path, output: Path, commit: str) -> dict:
    blocks = _blocks(items_ts.read_text(encoding="utf-8"))
    catalog = json.loads(champions.read_text(encoding="utf-8"))
    item_ids = [row["item_id"] for row in catalog["items"]]
    if len(item_ids) != 117 or len(set(item_ids)) != 117: raise ValueError("Champions item universe must contain 117 unique ids")
    normalized = {item_id: item_id.replace("-", "") for item_id in item_ids}
    missing = sorted(item_id for item_id, upstream_id in normalized.items() if upstream_id not in blocks)
    if missing: raise ValueError(f"pinned Showdown source missing Champions ids: {missing}")
    digest = hashlib.sha256(items_ts.read_bytes()).hexdigest()
    records = [{**_record(normalized[item_id], blocks[normalized[item_id]], commit), "item_id": item_id} for item_id in sorted(item_ids)]
    snapshot = f"data/vendor/pokemon_showdown/{commit}/items.ts"
    manifest = {"schema_version": SCHEMA, "source_provenance": {"repository": "https://github.com/smogon/pokemon-showdown", "commit_sha": commit, "path": "data/items.ts", "local_snapshot": snapshot, "sha256": digest, "extraction_schema_version": EXTRACTION_SCHEMA}, "champions_item_universe_count": len(item_ids), "items": records}
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--items-ts", type=Path, required=True); parser.add_argument("--champions", type=Path, default=Path("data/static/champions_legal_items.json")); parser.add_argument("--output", type=Path, default=Path("data/static/fling_item_effects.json")); parser.add_argument("--commit", required=True)
    args = parser.parse_args(); extract(items_ts=args.items_ts, champions=args.champions, output=args.output, commit=args.commit)


if __name__ == "__main__": main()
