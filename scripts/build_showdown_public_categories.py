"""Extract public categorical names from committed pinned native metadata.

This is a vocabulary, not a new legality authority or opponent-set dataset.
No engine downloads, game mechanics, current battle truth or training artifacts.
"""
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path

from advisor.learned_encoder import identifier
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "models/showdown_public_categories_v1/catalog.json"


def build():
    sources = {
        name: ROOT / "models/showdown_mc_domain_v1" / name
        for name in ("catalog.json", "inventory.json.gz")
    }
    catalog = json.loads(sources["catalog.json"].read_text(encoding="utf-8"))
    inventory = json.loads(gzip.decompress(sources["inventory.json.gz"].read_bytes()))
    for source in (catalog, inventory):
        if source["engine_commit"] != SHOWDOWN_COMMIT or source["format_id"] != FORMAT_ID:
            raise ValueError("public_category_source_identity_mismatch")
    return {
        "schema_version": "showdown-public-categories-v1",
        "engine_commit": SHOWDOWN_COMMIT,
        "format_id": FORMAT_ID,
        "scope": "public_display_vocabulary_not_set_or_team_legality",
        "source_sha256": {name: sha256(path.read_bytes()).hexdigest() for name, path in sources.items()},
        "species": sorted(catalog["species"]),
        "moves": sorted(set(catalog["moves"]) | {"recharge"}),
        "abilities": sorted({identifier(a) for a in inventory["abilities"] + inventory["transformation_abilities"]}),
        "items": sorted(inventory["items"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    if args.check:
        if json.loads(OUTPUT.read_text(encoding="utf-8")) != result:
            raise ValueError("public_category_catalog_out_of_date")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({name: len(result[name]) for name in ("species", "moves", "abilities", "items")}))


if __name__ == "__main__":
    main()
