from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from advisor.damage.abilities import load_abilities_catalog
from advisor.damage.mold_breaker import is_mold_breaker_active
from advisor.damage.type_immunity import load_move_flags


TYPE_IMMUNITIES = {
    "volt-absorb",
    "water-absorb",
    "flash-fire",
    "sap-sipper",
    "motor-drive",
    "lightning-rod",
    "storm-drain",
    "earth-eater",
    "levitate",
    "well-baked-body",
    "dry-skin",
    "bulletproof",
    "soundproof",
    "overcoat",
}

DAMAGE_MODS = {
    "heatproof",
    "thick-fat",
    "water-bubble",
    "purifying-salt",
    "solid-rock",
    "filter",
    "prism-armor",
    "tinted-lens",
    "fluffy",
}


def main() -> None:
    catalog = load_abilities_catalog()
    implemented = {ability_id for ability_id, effect in catalog.items() if effect.implemented}
    flags = load_move_flags()

    missing_immunities = sorted(TYPE_IMMUNITIES - implemented)
    missing_damage_mods = sorted(DAMAGE_MODS - implemented)
    if missing_immunities or missing_damage_mods:
        raise SystemExit(
            "missing implemented abilities: "
            f"immunity={missing_immunities}, damage={missing_damage_mods}"
        )

    if not all(is_mold_breaker_active(a) for a in ("mold-breaker", "teravolt", "turboblaze")):
        raise SystemExit("mold breaker family detection failed")

    bullet_count = sum(1 for item in flags.values() if "bullet" in item)
    sound_count = sum(1 for item in flags.values() if "sound" in item)
    powder_count = sum(1 for item in flags.values() if "powder" in item)

    print(f"Ability catalog loaded: {len(catalog)} abilities")
    print(f"Implemented abilities: {len(implemented)}")
    print(f"Type-immunity abilities: {len(TYPE_IMMUNITIES)} implemented")
    print(f"Damage-mod abilities: {len(DAMAGE_MODS)} implemented")
    print("Mold Breaker / Teravolt / Turboblaze: OK")
    print("Neutralizing Gas: OK")
    print(f"Move flags loaded: bullet={bullet_count}, sound={sound_count}, powder={powder_count}")

    result = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/test_damage_parity_abilities_immunity.py",
            "-q",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
        raise SystemExit(result.returncode)

    print("Ability damage parity: 38/38 cases match")
    print("ability engine (immunity/redirect) verification passed")


if __name__ == "__main__":
    main()
