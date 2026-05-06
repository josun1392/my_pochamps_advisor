from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from advisor.damage.field import Field, SideField
from advisor.damage.grounded import GroundedInputs, is_grounded
from advisor.damage.modifiers import (
    calc_stab,
    terrain_attack_modifier,
    weather_modifier,
)
from advisor.damage.q12 import M_STAB, M_TERRAIN_BOOST, M_WEATHER_BOOST
from advisor.damage.screens import screen_modifier


def main() -> None:
    field = Field().with_weather("sun").with_terrain("electric")
    if field.weather != "sun" or field.terrain != "electric":
        raise RuntimeError("Field state failed")
    print("Field state: OK")

    if not is_grounded(GroundedInputs(("fire", "flying"), item="iron-ball"), Field()):
        raise RuntimeError("Grounded judgment failed")
    print("Grounded judgment: OK")

    if weather_modifier("fire", "sun") != M_WEATHER_BOOST:
        raise RuntimeError("Weather modifier failed")
    print("Weather modifier: OK")

    if terrain_attack_modifier("electric", "thunderbolt", "electric", True) != M_TERRAIN_BOOST:
        raise RuntimeError("Terrain modifier failed")
    print("Terrain modifier: OK")

    if screen_modifier(SideField(reflect=True), True, False, True) != 2732:
        raise RuntimeError("Screen modifier failed")
    print("Screen modifier: OK")

    if calc_stab(("dragon", "ground"), "dragon", True, "dragon") != 8192:
        raise RuntimeError("Tera STAB failed")
    if calc_stab(("dragon", "ground"), "dragon", True, "steel") != M_STAB:
        raise RuntimeError("Original STAB after Tera failed")
    print("Tera STAB: OK")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_damage_parity_field.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    print("Field damage parity: 23/23 cases match")
    print("field engine verification passed")


if __name__ == "__main__":
    main()
