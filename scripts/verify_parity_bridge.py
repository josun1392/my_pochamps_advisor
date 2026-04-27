from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from advisor.parity.bridge import BRIDGE_DIR, call_smogon_calc
from advisor.parity.schemas import DamageRequest


EXAMPLE_REQUEST = BRIDGE_DIR / "examples" / "example_request.json"


def main() -> None:
    node_version = _node_version()
    _assert_node_modules()
    package = _load_package()
    calc_version = package["dependencies"]["@smogon/calc"]
    request = DamageRequest.model_validate_json(
        EXAMPLE_REQUEST.read_text(encoding="utf-8")
    )

    start = time.perf_counter()
    node_result = subprocess.run(
        ["node", "calc.js"],
        input=request.model_dump_json(by_alias=True),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=BRIDGE_DIR,
        timeout=5.0,
        check=False,
    )
    latency_ms = (time.perf_counter() - start) * 1000
    if node_result.returncode != 0:
        raise RuntimeError(f"Node bridge failed: {node_result.stderr}")
    json.loads(node_result.stdout)

    response = call_smogon_calc(request)
    if response.damage_min != 133 or response.damage_max != 157:
        raise RuntimeError(
            "Unexpected sample roll range: "
            f"{response.damage_min}-{response.damage_max}"
        )

    print("parity bridge verification passed")
    print(f"node version: {node_version}")
    print(f"@smogon/calc version: {calc_version}")
    print(f"sample call latency: {latency_ms:.1f}ms")


def _node_version() -> str:
    result = subprocess.run(
        ["node", "--version"],
        capture_output=True,
        text=True,
        timeout=5.0,
        check=True,
    )
    version = result.stdout.strip()
    major = int(version.lstrip("v").split(".", maxsplit=1)[0])
    if major < 18:
        raise RuntimeError(f"Node.js >=18 is required, found {version}")
    return version


def _assert_node_modules() -> None:
    if not (BRIDGE_DIR / "node_modules").exists():
        raise RuntimeError(
            "tools/smogon_bridge/node_modules not found. "
            "Run: cd tools/smogon_bridge && npm install"
        )


def _load_package() -> dict:
    return json.loads((BRIDGE_DIR / "package.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
