from __future__ import annotations

import json
import subprocess
from pathlib import Path

from advisor.parity.schemas import DamageRequest, DamageResponse


BRIDGE_DIR = Path(__file__).resolve().parents[2] / "tools" / "smogon_bridge"


class ParityBridgeError(RuntimeError):
    """Raised when the Node.js Smogon bridge cannot return a valid response."""


def call_smogon_calc(
    request: DamageRequest,
    timeout_s: float = 5.0,
) -> DamageResponse:
    """Call @smogon/calc through the Node.js subprocess bridge."""
    payload = request.model_dump_json(by_alias=True)
    try:
        result = subprocess.run(
            ["node", "calc.js"],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_s,
            cwd=BRIDGE_DIR,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ParityBridgeError(
            f"smogon calc timed out after {timeout_s}s"
        ) from exc
    except OSError as exc:
        raise ParityBridgeError(f"failed to start smogon calc: {exc}") from exc

    if result.returncode != 0:
        raise ParityBridgeError(f"smogon calc failed: {result.stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        preview = result.stdout[:200]
        raise ParityBridgeError(
            f"invalid JSON from smogon bridge: {preview}"
        ) from exc

    return DamageResponse.model_validate(data)
