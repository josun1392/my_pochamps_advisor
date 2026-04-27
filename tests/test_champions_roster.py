from __future__ import annotations

import json
from pathlib import Path

from config.prefetch_config import get_prefetch_targets


ROSTER_PATH = Path("data/static/champions_roster.json")


def test_roster_counts() -> None:
    roster = _load_roster()

    assert roster["counts"]["species"] == 187
    assert roster["counts"]["mega_evolutions"] == 59
    assert len(roster["species"]) == 187


def test_roster_required_special_cases() -> None:
    roster = _load_roster()
    species = roster["species"]

    floette = next(item for item in species if item["name_en"] == "floette-eternal")
    assert floette["availability"] == "transfer_only"

    tauros = next(item for item in species if item["name_en"] == "tauros")
    assert len(tauros["forms"]) == 4

    charizard = next(item for item in species if item["name_en"] == "charizard")
    assert len(charizard["mega_evolutions"]) == 2


def test_roster_has_no_missing_korean_species_names() -> None:
    roster = _load_roster()

    assert all(item["name_ko"] for item in roster["species"])


def test_prefetch_targets_match_roster_species() -> None:
    roster = _load_roster()

    assert get_prefetch_targets() == [item["name_en"] for item in roster["species"]]


def _load_roster() -> dict:
    with ROSTER_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)
