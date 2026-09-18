import hashlib
from pathlib import Path

import pytest

from advisor.canonical_fling_major_status_cure_berry import (
    COMMIT,
    EXPECTED_ITEMS_SHA256,
    SCHEMA_VERSION,
    canonical_fling_major_status_cure_berry_ids,
    resolve_canonical_fling_major_status_cure_berry,
)


ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT / "items.ts"


@pytest.mark.parametrize(
    ("item_id", "conditions"),
    (
        ("cheri-berry", ("paralysis",)),
        ("chesto-berry", ("sleep",)),
        ("aspear-berry", ("freeze",)),
        ("rawst-berry", ("burn",)),
        ("pecha-berry", ("poison", "toxic")),
    ),
)
def test_exact_five_berry_family(item_id, conditions):
    result = resolve_canonical_fling_major_status_cure_berry(item_id)
    assert result["status"] == "resolved"
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["item_id"] == item_id
    assert result["removable_conditions"] == conditions
    assert result["effect_family"] == "single_major_status_cure"
    assert result["fling_item_metadata"]["effect"]["kind"] == "berry_effect"


def test_non_family_berry_is_not_admitted():
    assert resolve_canonical_fling_major_status_cure_berry("oran-berry") == {
        "status": "not_applicable",
        "item_id": "oran-berry",
        "reason": "fling_item_not_single_major_status_cure_berry",
    }
    assert canonical_fling_major_status_cure_berry_ids() == (
        "cheri-berry",
        "chesto-berry",
        "aspear-berry",
        "pecha-berry",
        "rawst-berry",
    )


def test_pinned_items_source_binding_is_exact():
    assert COMMIT == "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
    assert hashlib.sha256(ITEMS.read_bytes()).hexdigest() == EXPECTED_ITEMS_SHA256
    result = resolve_canonical_fling_major_status_cure_berry("cheri-berry")
    assert result["source_provenance"] == {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "source_path": "data/items.ts",
        "local_snapshot": f"data/vendor/pokemon_showdown/{COMMIT}/items.ts",
        "sha256": EXPECTED_ITEMS_SHA256,
    }
