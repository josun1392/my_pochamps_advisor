from __future__ import annotations

import json

import pytest

from core.champions_item_repository import (
    DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL,
    LEGAL_AND_DAMAGE_SUPPORTED,
    LEGAL_BUT_NOT_MODELED,
    UNKNOWN,
    ChampionsItemRepository,
    load_champions_legal_items,
)


def test_fixture_loads_with_source_refs_and_regulation() -> None:
    data = load_champions_legal_items()

    assert data["regulation"] == "m_a"
    assert data["format"] == "pokemon_champions"
    assert {source["name"] for source in data["source_refs"]} >= {
        "MetaVGC",
        "RotomPicks",
        "Serebii",
        "ChampDex",
    }


@pytest.mark.parametrize("item_id", ["choice-scarf", "focus-sash", "leftovers", "sitrus-berry"])
def test_legal_sentinels_are_legal_but_not_modeled(item_id: str) -> None:
    repo = ChampionsItemRepository()

    classification = repo.classify_item(item_id)

    assert classification["legal"] is True
    assert classification["legality_status"] == "legal"
    assert classification["classification"] == LEGAL_BUT_NOT_MODELED
    assert classification["effect_support_status"] == LEGAL_BUT_NOT_MODELED
    assert repo.is_legal_item(item_id) is True


def test_legal_damage_supported_sentinel_is_classified_separately() -> None:
    repo = ChampionsItemRepository()

    classification = repo.classify_item("metal-coat")

    assert classification["legal"] is True
    assert classification["classification"] == LEGAL_AND_DAMAGE_SUPPORTED
    assert classification["effect_support"]["damage_modifier"] == "supported_by_engine"


@pytest.mark.parametrize("item_id", ["choice-band", "choice-specs", "life-orb"])
def test_core_damage_supported_items_are_not_treated_as_champions_legal(item_id: str) -> None:
    repo = ChampionsItemRepository()

    classification = repo.classify_item(item_id)

    assert classification["legal"] is False
    assert classification["legality_status"] == "not_legal_or_unconfirmed"
    assert classification["classification"] == DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL
    assert classification["effect_support_status"] == DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL
    assert repo.is_legal_item(item_id) is False


@pytest.mark.parametrize("item_id", ["muscle-band", "wise-glasses"])
def test_unconfirmed_damage_supported_items_are_kept_out_of_legal_items(item_id: str) -> None:
    repo = ChampionsItemRepository()

    classification = repo.classify_item(item_id)

    assert classification["legal"] is False
    assert classification["legality_status"] == "unconfirmed"
    assert classification["classification"] == DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL


def test_unknown_item_classifies_as_unknown() -> None:
    repo = ChampionsItemRepository()

    classification = repo.classify_item("mystery-item")

    assert classification["classification"] == UNKNOWN
    assert classification["legality_status"] == UNKNOWN
    assert classification["effect_support_status"] == UNKNOWN
    assert classification["ui_status"] == UNKNOWN


def test_list_legal_items_returns_only_legal_fixture_items() -> None:
    repo = ChampionsItemRepository()

    legal_items = repo.list_legal_items()

    assert legal_items
    assert all(item["legal"] is True for item in legal_items)
    assert {item["item_id"] for item in legal_items} >= {"choice-scarf", "focus-sash", "leftovers"}
    assert "choice-band" not in {item["item_id"] for item in legal_items}


def test_list_damage_supported_non_legal_items_returns_mismatch_items() -> None:
    repo = ChampionsItemRepository()

    items = repo.list_damage_supported_non_legal_items()
    item_ids = {item["item_id"] for item in items}

    assert {"choice-band", "choice-specs", "life-orb"} <= item_ids
    assert all(item["classification"] == DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL for item in items)


def test_repository_supports_normalized_lookup() -> None:
    repo = ChampionsItemRepository()

    assert repo.get_legality_status("Choice Scarf") == "legal"
    assert repo.get_effect_support_status("choice_scarf") == LEGAL_BUT_NOT_MODELED
    assert repo.get_ui_status("CHOICE-SCARF") == "recognized_not_modeled"


def test_invalid_fixture_missing_required_fields_raises(tmp_path) -> None:
    fixture_path = tmp_path / "bad_items.json"
    fixture_path.write_text(json.dumps({"format": "pokemon_champions"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_champions_legal_items(fixture_path)
