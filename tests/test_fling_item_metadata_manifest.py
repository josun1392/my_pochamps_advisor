import hashlib
import json
from pathlib import Path

from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata
from scripts.extract_fling_item_metadata import extract


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
ITEMS = ROOT / "data/vendor/pokemon_showdown" / COMMIT / "items.ts"
MANIFEST = ROOT / "data/static/fling_item_effects.json"


def test_pinned_source_and_manifest_cover_champions_exactly_once(tmp_path):
    raw = json.loads(MANIFEST.read_text(encoding="utf-8")); catalog = json.loads((ROOT / "data/static/champions_legal_items.json").read_text(encoding="utf-8"))
    assert raw["source_provenance"]["commit_sha"] == COMMIT and len(COMMIT) == 40
    assert hashlib.sha256(ITEMS.read_bytes()).hexdigest() == raw["source_provenance"]["sha256"]
    assert {row["item_id"] for row in raw["items"]} == {row["item_id"] for row in catalog["items"]}
    again = tmp_path / "again.json"; extract(items_ts=ITEMS, champions=ROOT / "data/static/champions_legal_items.json", output=again, commit=COMMIT)
    assert again.read_bytes() == MANIFEST.read_bytes()


def test_resolver_has_exact_bp_effect_classes_and_fails_closed():
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))["items"]
    assert any(row["flingable"] and row["base_power"] == 10 for row in records)
    assert any(row["flingable"] and row["base_power"] == 30 for row in records)
    assert any(row["flingable"] and row["base_power"] >= 80 for row in records)
    # The current 117-item Champions universe has no item with an
    # unconditional `onTakeItem: false`; conditional species restrictions are
    # preserved for the later execution authority rather than misclassified.
    assert all(row["flingable"] for row in records)
    assert any(row["effect"]["kind"] == "berry_effect" and row["support_status"] == "unsupported_now" for row in records)
    assert resolve_canonical_fling_item_metadata("not-an-item")["status"] == "incomplete"
