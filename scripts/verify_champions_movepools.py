from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


ROSTER_PATH = PROJECT_ROOT / "data" / "static" / "champions_roster.json"
MOVEPOOL_DIR = PROJECT_ROOT / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"


def main() -> int:
    expected = _expected_entities(_load_json(ROSTER_PATH))
    existing = {path.stem for path in MOVEPOOL_DIR.glob("*.json")}
    missing = sorted(expected - existing)
    extra = sorted(existing - expected)
    assert not missing, f"missing Champions movepool fixtures: {missing[:20]}"
    assert not extra, f"unexpected Champions movepool fixtures: {extra[:20]}"

    empty_available: list[str] = []
    globally_denied: dict[str, list[str]] = {}
    hidden_power: list[str] = []
    unavailable: list[str] = []
    total_moves = 0
    for entity_id in sorted(expected):
        data = _load_json(MOVEPOOL_DIR / f"{entity_id}.json")
        assert data["pokemon_id"] == entity_id
        assert data["format"] == "pokemon_champions"
        assert data["regulation"] == "M-A"
        moves = data.get("moves")
        assert isinstance(moves, list)
        move_ids = [move.get("move_id") for move in moves if isinstance(move, dict)]
        assert len(move_ids) == len(set(move_ids)), f"duplicate move ids in {entity_id}"
        total_moves += len(move_ids)
        if data.get("status") and data.get("status") != "available":
            unavailable.append(entity_id)
        elif not move_ids:
            empty_available.append(entity_id)
        denied = sorted({"tera-blast"} & set(move_ids))
        if denied:
            globally_denied[entity_id] = denied
        if "hidden-power" in move_ids:
            hidden_power.append(entity_id)

    assert not empty_available, f"available fixtures with no moves: {empty_available[:20]}"
    assert not globally_denied, f"globally denied moves present: {globally_denied}"
    assert not hidden_power, f"hidden-power present in Champions movepools: {hidden_power[:20]}"

    print("Champions movepool verification passed")
    print(f"entities: {len(expected)}")
    print(f"total listed move entries: {total_moves}")
    print(f"unavailable source fixtures: {unavailable}")
    return 0


def _expected_entities(roster: dict[str, Any]) -> set[str]:
    entities: set[str] = set()
    for species in roster["species"]:
        for form in species["forms"]:
            entities.add(form["form_id"])
        for mega in species["mega_evolutions"]:
            entities.add(mega["mega_id"])
    return entities


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
