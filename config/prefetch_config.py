from __future__ import annotations

import json
from pathlib import Path


CHAMPIONS_ROSTER_PATH = Path("data/static/champions_roster.json")


def get_prefetch_targets() -> list[str]:
    with CHAMPIONS_ROSTER_PATH.open("r", encoding="utf-8") as file:
        roster = json.load(file)
    return [species["name_en"] for species in roster["species"]]
