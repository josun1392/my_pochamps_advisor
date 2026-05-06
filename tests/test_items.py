from __future__ import annotations

from advisor.damage.items import get_item


def test_type_boost_item_lookup() -> None:
    item = get_item("charcoal")
    assert item is not None
    assert item.boosted_types == ("fire",)
    assert item.multiplier_q12 == 4915


def test_life_orb_lookup() -> None:
    item = get_item("life-orb")
    assert item is not None
    assert item.multiplier_q12 == 5324


def test_missing_item_lookup() -> None:
    assert get_item(None) is None
    assert get_item("nonexistent") is None


def test_all_type_plates_lookup() -> None:
    plates = [
        "blank-plate",
        "flame-plate",
        "splash-plate",
        "zap-plate",
        "meadow-plate",
        "icicle-plate",
        "fist-plate",
        "toxic-plate",
        "earth-plate",
        "sky-plate",
        "mind-plate",
        "insect-plate",
        "stone-plate",
        "spooky-plate",
        "draco-plate",
        "dread-plate",
        "iron-plate",
        "pixie-plate",
    ]
    assert all(get_item(item_id) is not None for item_id in plates)


def test_all_type_resist_berries_lookup() -> None:
    berries = [
        "occa-berry",
        "passho-berry",
        "wacan-berry",
        "rindo-berry",
        "yache-berry",
        "chople-berry",
        "kebia-berry",
        "shuca-berry",
        "coba-berry",
        "payapa-berry",
        "tanga-berry",
        "charti-berry",
        "kasib-berry",
        "haban-berry",
        "colbur-berry",
        "babiri-berry",
        "roseli-berry",
        "chilan-berry",
    ]
    assert all(get_item(item_id) is not None for item_id in berries)


def test_soul_dew_lookup() -> None:
    item = get_item("soul-dew")
    assert item is not None
    assert item.species_lock == ("latios", "latias")
    assert item.boosted_types == ("psychic", "dragon")
