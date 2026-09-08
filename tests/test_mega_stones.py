from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.items import canonical_mega_stone_id, get_mega_form, is_mega_stone, load_mega_stones


AUDITED_LEGAL_MEGA_STONE_ALIASES = {
    "altarianite": ("altariaite", "altaria", "altaria-mega"),
    "chandelurite": ("chandelureite", "chandelure", "chandelure-mega"),
    "chimechite": ("chimechoite", "chimecho", "chimecho-mega"),
    "clefablite": ("clefableite", "clefable", "clefable-mega"),
    "crabominite": ("crabominableite", "crabominable", "crabominable-mega"),
    "dragoninite": ("dragoniteite", "dragonite", "dragonite-mega"),
    "drampanite": ("drampaite", "drampa", "drampa-mega"),
    "excadrite": ("excadrillite", "excadrill", "excadrill-mega"),
    "feraligite": ("feraligatrite", "feraligatr", "feraligatr-mega"),
    "floettite": ("floetteite", "floette-eternal", "floette-mega"),
    "glalitite": ("glalieite", "glalie", "glalie-mega"),
    "glimmoranite": ("glimmoraite", "glimmora", "glimmora-mega"),
    "greninjite": ("greninjaite", "greninja", "greninja-mega"),
    "hawluchanite": ("hawluchaite", "hawlucha", "hawlucha-mega"),
    "lopunnite": ("lopunnyite", "lopunny", "lopunny-mega"),
    "sharpedonite": ("sharpedoite", "sharpedo", "sharpedo-mega"),
    "skarmorite": ("skarmoryite", "skarmory", "skarmory-mega"),
    "starminite": ("starmieite", "starmie", "starmie-mega"),
}


def test_mega_stone_lookup() -> None:
    assert is_mega_stone("charizardite-y")
    assert get_mega_form("charizardite-y", "charizard") == "charizard-mega-y"
    assert get_mega_form("charizardite-y", "blastoise") is None
    assert get_mega_form("charizardite-x", "charizard") == "charizard-mega-x"
    assert is_mega_stone("red-orb")
    assert get_mega_form("red-orb", "groudon") == "groudon-primal"


@pytest.mark.parametrize("legal_item_id, expected", AUDITED_LEGAL_MEGA_STONE_ALIASES.items())
def test_audited_legal_mega_stone_ids_resolve_to_existing_canonical_entries(
    legal_item_id: str, expected: tuple[str, str, str],
) -> None:
    canonical_item_id, base_species, mega_form = expected

    assert canonical_mega_stone_id(legal_item_id) == canonical_item_id
    assert is_mega_stone(legal_item_id) is True
    assert get_mega_form(legal_item_id, base_species) == mega_form


def test_altarianite_resolves_only_through_the_explicit_altariaite_alias() -> None:
    assert canonical_mega_stone_id("altarianite") == "altariaite"
    assert canonical_mega_stone_id("altariaite") == "altariaite"
    assert canonical_mega_stone_id("Altarianite") is None
    assert canonical_mega_stone_id("altariaite-extra") is None


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
