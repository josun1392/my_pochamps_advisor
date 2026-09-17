"""Life Orb's runtime, generator, and retained metadata must agree."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from advisor.damage.item_modifiers import M_LIFE_ORB, attacker_damage_item_mod
from advisor.damage.items import get_item


_ROOT = Path(__file__).resolve().parents[1]


def _items_generator():
    path = _ROOT / "scripts" / "build_items_catalog.py"
    spec = importlib.util.spec_from_file_location("items_catalog_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _life_orb_value(path: str) -> int:
    raw = json.loads((_ROOT / path).read_text(encoding="utf-8"))
    if path.endswith("items_damage.json"):
        return raw["stat_boost_items"]["life-orb"]["multiplier_q12"]
    return raw["life-orb"]["multiplier_q12"]


def test_life_orb_q12_matches_checked_in_smogon_parity_authority():
    smogon_gen789 = (_ROOT / "tools/smogon_bridge/node_modules/@smogon/calc/src/mechanics/gen789.ts").read_text(encoding="utf-8")

    assert "attacker.hasItem('Life Orb')" in smogon_gen789
    assert "finalMods.push(5324)" in smogon_gen789
    assert M_LIFE_ORB == 5324


def test_life_orb_runtime_generator_and_static_metadata_share_one_value():
    generated = _items_generator().build_items_catalog()
    generated_life_orb = generated["stat_boost_items"]["life-orb"]["multiplier_q12"]

    assert generated == json.loads((_ROOT / "data/static/items_damage.json").read_text(encoding="utf-8"))
    assert generated_life_orb == M_LIFE_ORB
    assert _life_orb_value("data/static/items_damage.json") == M_LIFE_ORB
    # items.json is retained compatibility/effect metadata, not the Champions
    # legality source, but it must not preserve a conflicting damage constant.
    assert _life_orb_value("data/static/items.json") == M_LIFE_ORB


def test_life_orb_runtime_modifier_uses_the_canonical_value_once():
    assert attacker_damage_item_mod(get_item("life-orb"), False) == M_LIFE_ORB
    assert attacker_damage_item_mod(get_item("life-orb"), True) == M_LIFE_ORB
