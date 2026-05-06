from __future__ import annotations

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from advisor.damage.q12 import M_DOUBLE, M_STAB, chain_modifiers
from advisor.damage.stats import calc_stat_gen9
from advisor.damage.types import TYPES, load_type_chart


def main() -> None:
    if chain_modifiers([M_STAB, M_DOUBLE]) != 12288:
        raise RuntimeError("Q12 arithmetic failed")
    print("Q12 arithmetic: OK")

    if calc_stat_gen9(130, 252, 31, 50, 1.0, is_hp=False) != 182:
        raise RuntimeError("stat calculation failed")
    print("Stat calculation: OK")

    chart = load_type_chart()
    if len(chart) != len(TYPES) or any(len(row) != len(TYPES) for row in chart.values()):
        raise RuntimeError("type chart is not 18x18")
    print("Type chart loaded: 18x18")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_damage_parity.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    print("Vanilla damage parity: 10/10 cases match")
    print("damage engine verification passed")


if __name__ == "__main__":
    main()
