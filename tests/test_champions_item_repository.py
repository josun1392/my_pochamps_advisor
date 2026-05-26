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
    normalize_item_id,
)


REQUIRED_ITEM_FIELDS = {
    "item_id",
    "name_en",
    "name_ko",
    "category",
    "legal",
    "legality_status",
    "legality_confidence",
    "effect_support_status",
    "ui_status",
    "effect_support",
    "notes",
}
ALLOWED_CATEGORIES = {"mega_stone", "berry", "hold_item", "type_boosting_item", "utility_item"}
ALLOWED_LEGALITY_STATUSES = {"legal", "not_legal_or_unconfirmed", "unconfirmed", "source_conflict"}
ALLOWED_EFFECT_SUPPORT_STATUSES = {
    LEGAL_AND_DAMAGE_SUPPORTED,
    LEGAL_BUT_NOT_MODELED,
    DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL,
    "unsupported_or_unknown",
    "not_applicable",
}
ALLOWED_UI_STATUSES = {
    "recognized_not_modeled",
    "recognized_modeled",
    "selectable_not_modeled",
    "hidden_normal_ui",
    "damage_test_only",
}


def test_fixture_loads_with_source_refs_and_regulation() -> None:
    data = load_champions_legal_items()

    assert data["regulation"] == "m_a"
    assert data["format"] == "pokemon_champions"
    assert data["source_kind"] == "third_party_cross_checked"
    assert data["fetched_at"]
    assert data["expected_legal_item_count"] == 117
    assert {source["name"] for source in data["source_refs"]} >= {
        "MetaVGC",
        "RotomPicks",
        "Serebii",
        "ChampDex",
    }


def test_full_fixture_has_expected_count_and_categories() -> None:
    data = load_champions_legal_items()
    legal_items = data["items"]

    assert len(legal_items) == 117
    assert data["counts"]["legal_items"] == 117
    assert sum(1 for item in legal_items if item["category"] == "hold_item") == 12
    assert sum(1 for item in legal_items if item["category"] == "type_boosting_item") == 18
    assert sum(
        1
        for item in legal_items
        if item["category"] in {"hold_item", "type_boosting_item"}
    ) == 30
    assert sum(1 for item in legal_items if item["category"] == "mega_stone") == 59
    assert sum(1 for item in legal_items if item["category"] == "berry") == 28


def test_fixture_item_ids_are_unique_across_sections() -> None:
    data = load_champions_legal_items()
    item_ids = [
        item["item_id"]
        for item in [*data["items"], *data["damage_supported_non_legal_items"]]
    ]

    assert len(item_ids) == len(set(item_ids))


def test_every_fixture_item_has_required_fields_and_allowed_statuses() -> None:
    data = load_champions_legal_items()

    for item in [*data["items"], *data["damage_supported_non_legal_items"]]:
        assert REQUIRED_ITEM_FIELDS <= set(item)
        assert item["item_id"] == normalize_item_id(item["item_id"])
        assert item["name_en"]
        assert item["category"] in ALLOWED_CATEGORIES
        assert item["legality_status"] in ALLOWED_LEGALITY_STATUSES
        assert item["effect_support_status"] in ALLOWED_EFFECT_SUPPORT_STATUSES
        assert item["ui_status"] in ALLOWED_UI_STATUSES
        assert isinstance(item["effect_support"], dict)
        assert isinstance(item["notes"], list)


def test_source_conflict_and_unconfirmed_items_are_explicitly_tracked() -> None:
    data = load_champions_legal_items()
    all_items = [*data["items"], *data["damage_supported_non_legal_items"]]

    conflict_or_unconfirmed = [
        item
        for item in all_items
        if item["legality_status"] in {"source_conflict", "unconfirmed"}
    ]

    assert {item["item_id"] for item in conflict_or_unconfirmed} == {
        "muscle-band",
        "wise-glasses",
    }


def test_damage_supported_non_legal_items_are_not_in_normal_legal_items() -> None:
    data = load_champions_legal_items()
    legal_item_ids = {item["item_id"] for item in data["items"]}
    damage_test_item_ids = {
        item["item_id"] for item in data["damage_supported_non_legal_items"]
    }

    assert {"choice-band", "choice-specs", "life-orb"} <= damage_test_item_ids
    assert not {"choice-band", "choice-specs", "life-orb"} & legal_item_ids


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

    assert len(legal_items) == 117
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
    assert repo.get_legality_status("King's Rock") == "legal"
    assert normalize_item_id("King\u2019s Rock") == "kings-rock"


def test_invalid_fixture_missing_required_fields_raises(tmp_path) -> None:
    fixture_path = tmp_path / "bad_items.json"
    fixture_path.write_text(json.dumps({"format": "pokemon_champions"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_champions_legal_items(fixture_path)
