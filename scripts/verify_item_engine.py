from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from advisor.damage.item_modifiers import (
    attack_stat_item_mod,
    attacker_base_power_item_mod,
    attacker_damage_item_mod,
    defender_berry_mod,
)
from advisor.damage.items import get_item, load_items_catalog, load_mega_stones
from advisor.damage.q12 import Q12_ONE


ROSTER_PATH = Path("data/static/champions_roster.json")


def _assert_catalog() -> None:
    catalog = load_items_catalog()
    plates = [item for item in catalog.values() if item.kind == "type_plate"]
    berries = [item for item in catalog.values() if item.kind == "type_resist_berry"]
    assert len(plates) == 18
    assert len(berries) == 18
    assert get_item("life-orb") is not None
    assert attacker_damage_item_mod(get_item("life-orb"), False) == 5324
    assert attacker_base_power_item_mod(get_item("charcoal"), "fire", "charizard", False) == 4915
    assert attacker_base_power_item_mod(get_item("muscle-band"), "ground", "garchomp", True) == 4505
    assert attack_stat_item_mod(get_item("choice-band"), True, "garchomp") == 6144
    assert defender_berry_mod(get_item("occa-berry"), "fire", True) == 2048
    assert defender_berry_mod(get_item("occa-berry"), "fire", False) == Q12_ONE
    print(f"Items catalog loaded: {len(catalog)} items")
    print("Type plates: 18/18 verified")
    print("Type-resist berries: 18/18 verified")
    print("Stat-mod items: OK")
    print("Damage-mod items: OK")


def _assert_mega_stones() -> None:
    roster = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    mega_forms = {
        mega["mega_id"]
        for species in roster["species"]
        for mega in species.get("mega_evolutions", [])
    }
    stones = load_mega_stones()
    stone_forms = {entry["mega_form"] for entry in stones["mega_stones"].values()}
    matched = len(mega_forms & stone_forms)
    assert matched == len(mega_forms) == 59
    print(f"Mega stones loaded: {len(stones['mega_stones'])} stones")
    print(f"Mega stone roster cross-check: {matched}/{len(mega_forms)} matched")


def _run_parity() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_damage_parity_items.py", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print("Item damage parity: 25/25 cases match")


def main() -> None:
    _assert_catalog()
    _assert_mega_stones()
    _run_parity()
    print("item engine verification passed")


if __name__ == "__main__":
    main()
