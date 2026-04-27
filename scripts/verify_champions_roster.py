from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


ROSTER_PATH = PROJECT_ROOT / "data" / "static" / "champions_roster.json"


def main() -> int:
    roster = _load_roster()
    species = roster["species"]
    counts = roster["counts"]

    assert counts["species"] == 187
    assert counts["mega_evolutions"] == 59
    assert 180 <= len(species) <= 200
    assert all(item["availability"] in ["normal", "transfer_only", "event"] for item in species)
    assert all(item["name_ko"] for item in species)
    assert all(item["national_dex"] in range(1, 1026) for item in species)
    assert len({item["national_dex"] for item in species}) == len(species)

    floette = next(item for item in species if item["name_en"] == "floette-eternal")
    assert floette["availability"] == "transfer_only"

    tauros = next(item for item in species if item["name_en"] == "tauros")
    assert len(tauros["forms"]) == 4
    assert {form["form_id"] for form in tauros["forms"]} == {
        "tauros",
        "tauros-paldea-combat-breed",
        "tauros-paldea-blaze-breed",
        "tauros-paldea-aqua-breed",
    }

    charizard = next(item for item in species if item["name_en"] == "charizard")
    assert len(charizard["mega_evolutions"]) == 2

    _verify_pokeapi_sample(species)
    print("champions roster verification passed")
    print(f"species={counts['species']}")
    print(f"form_variants={counts['form_variants']}")
    print(f"mega_evolutions={counts['mega_evolutions']}")
    return 0


def _load_roster() -> dict:
    with ROSTER_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _verify_pokeapi_sample(species: list[dict]) -> None:
    supported_forms = [
        form["form_id"]
        for item in species
        for form in item["forms"]
        if form.get("pokeapi_supported") is True
    ]
    sample = random.Random(42).sample(supported_forms, 10)
    for form_id in sample:
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{form_id}/", timeout=15)
        assert response.status_code == 200, f"PokeAPI rejected: {form_id}"


if __name__ == "__main__":
    raise SystemExit(main())
