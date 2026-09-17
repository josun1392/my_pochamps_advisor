"""Production admission contract for Champions legal type-boost items."""
from __future__ import annotations

import json
from pathlib import Path

from advisor.damage.item_modifiers import attacker_base_power_item_mod
from advisor.damage.items import get_champions_supported_type_boost_item, load_champions_supported_type_boost_items
from llm.advisor_direct_mechanics import _attacker_item_modifier_context
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result


def _metadata_supported_type_boost_ids() -> set[str]:
    raw = json.loads(Path("data/static/champions_legal_items.json").read_text(encoding="utf-8"))
    return {
        row["item_id"]
        for row in raw["items"]
        if row.get("legal") is True
        and row.get("category") == "type_boosting_item"
        and row.get("effect_support_status") == "legal_and_damage_supported"
        and row.get("effect_support", {}).get("damage_modifier") == "supported_by_engine"
    }


def test_metadata_qualified_champions_type_boosters_are_all_production_admitted():
    expected_ids = _metadata_supported_type_boost_ids()
    effects = load_champions_supported_type_boost_items()

    assert len(expected_ids) == 17
    assert set(effects) == expected_ids
    assert effects["black-belt"].boosted_types == ("fighting",)
    assert effects["charcoal"].boosted_types == ("fire",)
    assert effects["twisted-spoon"].boosted_types == ("psychic",)
    assert all(effect.multiplier_q12 == 4915 for effect in effects.values())

    for item_id, effect in effects.items():
        assert get_champions_supported_type_boost_item(item_id) == effect
        assert attacker_base_power_item_mod(effect, effect.boosted_types[0], "", False) == 4915
        live_context = _attacker_item_modifier_context(
            stat_provenance={"attacker": {"known_item": {"status": "known", "value": item_id}}},
            direct_attacker={"item": {"status": "known"}},
            category="physical",
            move_type=effect.boosted_types[0],
            defender_types=(),
        )
        assert live_context["unsupported_reason"] is None
        assert live_context["item_effect"] == effect

    assert effects["magnet"].boosted_types == ("electric",)


def test_charcoal_is_live_direct_damage_boost_only_for_matching_move_type():
    field = {"weather": "none", "side_effects": []}
    baseline_fire = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, **field)
    charcoal_fire = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, item="charcoal", **field)
    baseline_water = _modifier_result(category="special", move_type="water", move_id="surf", power=90, **field)
    charcoal_water = _modifier_result(category="special", move_type="water", move_id="surf", power=90, item="charcoal", **field)

    assert charcoal_fire["status"] == "known"
    assert charcoal_fire["damage_range"]["maximum"] > baseline_fire["damage_range"]["maximum"]
    assert charcoal_fire["applied_damage_modifiers"] == ["item_charcoal_type_boost"]
    assert charcoal_water["status"] == "known"
    assert charcoal_water["damage_range"] == baseline_water["damage_range"]
    assert charcoal_water["applied_damage_modifiers"] == []


def test_other_item_admission_boundaries_remain_closed_or_unchanged():
    assert get_champions_supported_type_boost_item("fairy-feather") is None
    assert get_champions_supported_type_boost_item("odd-incense") is None

    unsupported = _modifier_result(item="fairy-feather")
    unknown = _modifier_result(item="made-up-item")
    life_orb = _modifier_result(category="physical", item="life-orb")

    assert unsupported["status"] == "unsupported_mechanic"
    assert unsupported["unsupported_reason"] == "item_modifier"
    assert unknown["status"] == "unsupported_mechanic"
    assert unknown["unsupported_reason"] == "item_modifier"
    assert life_orb["status"] == "known"
    assert life_orb["applied_damage_modifiers"] == ["item_life_orb_boost"]
