from __future__ import annotations

import json
from pathlib import Path

from advisor.damage.items import get_mega_form, is_mega_stone, load_mega_stones


def test_mega_stone_lookup() -> None:
    assert is_mega_stone("charizardite-y")
    assert get_mega_form("charizardite-y", "charizard") == "charizard-mega-y"
    assert get_mega_form("charizardite-y", "blastoise") is None
    assert get_mega_form("charizardite-x", "charizard") == "charizard-mega-x"
    assert is_mega_stone("red-orb")
    assert get_mega_form("red-orb", "groudon") == "groudon-primal"


def test_all_champions_megas_have_stones() -> None:
    roster = json.loads(Path("data/static/champions_roster.json").read_text(encoding="utf-8"))
    stones = load_mega_stones()["mega_stones"]
    stone_forms = {entry["mega_form"] for entry in stones.values()}
    mega_forms = {
        mega["mega_id"]
        for species in roster["species"]
        for mega in species.get("mega_evolutions", [])
    }

    assert len(mega_forms) == 59
    assert mega_forms <= stone_forms
