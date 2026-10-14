"""Append canonical pinned native runtime abilities; never overwrite V1/V2."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from advisor.learned_encoder import fingerprint
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from scripts.build_showdown_public_categories import OUTPUT as LEGACY

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "models/showdown_public_categories_v3/catalog.json"


def build(checkout):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip() != SHOWDOWN_COMMIT:
        raise ValueError("runtime_ability_engine_pin_mismatch")
    native = json.loads(subprocess.check_output(["node", str(ROOT / "tools/showdown_bridge/runtime-abilities.cjs"), str(checkout)], text=True, encoding="utf-8"))
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
    ids = sorted(a["id"] for a in native["abilities"])
    if not set(legacy["abilities"]) <= set(ids) or len(ids) + 3 > 512:
        raise ValueError("canonical_ability_domain_incompatible_with_existing_transport")
    abilities = legacy["abilities"] + sorted(set(ids) - set(legacy["abilities"]))
    return {"schema_version": "showdown-public-runtime-categories-v3", "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID, "scope": "all_canonical_pinned_format_Dex_abilities_not_initial_set_legality",
            "legacy_catalog_sha256": sha256(LEGACY.read_bytes()).hexdigest(),
            "legacy_ability_count": len(legacy["abilities"]), "abilities": abilities,
            "token_map_sha256": fingerprint({name: i + 3 for i, name in enumerate(abilities)}),
            "native_registry_sha256": fingerprint(native), "native_registry": native,
            "assignment": "legacy_prefix_unchanged_new_canonical_ids_sorted_appended",
            "source_sha256": {name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                              for name in ("tools/showdown_bridge/runtime-abilities.cjs", "scripts/build_showdown_runtime_categories.py")}}


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument("--checkout",type=Path,required=True);p.add_argument("--check",action="store_true");a=p.parse_args()
    result = build(a.checkout)
    if a.check:
        if json.loads(OUTPUT.read_text(encoding="utf-8")) != result:raise ValueError("runtime_category_catalog_out_of_date")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"abilities":len(result["abilities"]),"legacy":result["legacy_ability_count"],"added":len(result["abilities"])-result["legacy_ability_count"],"token_map_sha256":result["token_map_sha256"]}))

if __name__ == "__main__":main()
