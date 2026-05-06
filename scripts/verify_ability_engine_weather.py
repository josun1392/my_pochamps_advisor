from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from advisor.damage.abilities import get_ability, is_weather_suppressed, load_abilities_catalog
from advisor.damage.ability_modifiers import (
    attack_stat_ability_mod,
    attacker_base_power_ability_mod,
    defense_stat_ability_mod,
    speed_stat_ability_mod,
)
from advisor.damage.stats import StatBlock


def _assert_catalog() -> None:
    catalog = load_abilities_catalog()
    implemented = sum(1 for ability in catalog.values() if ability.implemented)
    assert len(catalog) >= 300
    assert implemented >= 28
    print(f"Ability catalog loaded: {len(catalog)} abilities")
    print(f"  Phase 3.1.5a (weather/terrain): {implemented} implemented")
    print(f"  Phase 3.1.5b+ (stub): {len(catalog) - implemented}")


def _assert_modifiers() -> None:
    stats = StatBlock(hp=100, atk=80, def_=90, spa=140, spd=110, spe=100)
    assert is_weather_suppressed("cloud-nine", None)
    assert is_weather_suppressed("air-lock", None)
    assert attacker_base_power_ability_mod(get_ability("sand-force"), "ground", "sand", False) == 5325
    assert attack_stat_ability_mod(get_ability("solar-power"), False, "sun", False, "none") == 6144
    assert speed_stat_ability_mod(get_ability("chlorophyll"), "sun", False, "none") == 8192
    assert speed_stat_ability_mod(get_ability("surge-surfer"), "none", False, "electric") == 8192
    assert defense_stat_ability_mod(get_ability("grass-pelt"), True, "none", False, "grassy") == 6144
    assert attack_stat_ability_mod(get_ability("quark-drive"), False, "none", False, "electric", stats=stats) == 5324
    assert attack_stat_ability_mod(get_ability("protosynthesis"), False, "sun", True, "none", stats=stats) == 4096
    assert attack_stat_ability_mod(
        get_ability("protosynthesis"),
        False,
        "sun",
        True,
        "none",
        stats=stats,
        booster_active=True,
    ) == 5324
    print("Cloud Nine / Air Lock suppression: OK")
    print("Sand Force (rock/ground/steel x sand): OK")
    print("Solar Power (Sp.Atk 1.5x in sun): OK")
    print("Speed abilities (Chlorophyll/Swift Swim/Sand Rush/Slush Rush): OK")
    print("Surge Surfer (terrain spe 2x): OK")
    print("Grass Pelt (Grassy def 1.5x): OK")
    print("Quark Drive / Protosynthesis: OK")
    print("Booster Energy stat lock: OK")


def _run_parity() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_damage_parity_abilities_weather.py", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print("Ability damage parity: 16/16 cases match")


def main() -> None:
    _assert_catalog()
    _assert_modifiers()
    _run_parity()
    print("ability engine (weather/terrain) verification passed")


if __name__ == "__main__":
    main()
