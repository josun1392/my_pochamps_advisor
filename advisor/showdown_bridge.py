"""Pinned, offline Showdown subprocess transport, matching the parity bridge style."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

SHOWDOWN_COMMIT = "942cda71d14bf0618bd57991708a2e2734b6daba"
FORMAT_ID = "gen9championsbssregmc"
SCHEMA_VERSION = "detached-showdown-v1"
OBSERVATION_SCHEMA_VERSION = "showdown-observed-projection-v2"
BRIDGE_SCRIPT = Path(__file__).resolve().parents[1] / "tools/showdown_bridge/bridge.cjs"


class ShowdownBridgeError(RuntimeError):
    """Sanitized infrastructure failure; never contains child stdout/stderr."""


class ShowdownBridge:
    def __init__(self, checkout: str | Path, *, timeout_s: float = 10.0):
        self.checkout = Path(checkout).resolve()
        self.timeout_s = timeout_s

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Explicit opt-in only. Validate the external pin before every batch."""
        self._verify_checkout()
        try:
            result = subprocess.run(
                ["node", str(BRIDGE_SCRIPT), str(self.checkout)],
                input=json.dumps(request, ensure_ascii=False, allow_nan=False),
                capture_output=True, text=True, encoding="utf-8", timeout=self.timeout_s,
                check=False,
            )
            response = json.loads(result.stdout)
        except subprocess.TimeoutExpired as exc:
            raise ShowdownBridgeError("showdown_timeout") from exc
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            raise ShowdownBridgeError("showdown_unavailable_or_invalid_response") from exc
        if result.returncode != 0 or not isinstance(response, dict):
            raise ShowdownBridgeError("showdown_bridge_failed")
        return self._validate_response(request, response)

    def _verify_checkout(self) -> None:
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=self.checkout,
                capture_output=True, text=True, encoding="utf-8", timeout=5, check=True,
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"], cwd=self.checkout,
                capture_output=True, text=True, encoding="utf-8", timeout=5, check=True,
            ).stdout.strip()
            if revision != SHOWDOWN_COMMIT or dirty:
                raise ShowdownBridgeError("showdown_revision_or_tracked_sources_mismatch")
        except subprocess.TimeoutExpired as exc:
            raise ShowdownBridgeError("showdown_timeout") from exc
        except (OSError, subprocess.CalledProcessError, ValueError) as exc:
            raise ShowdownBridgeError("showdown_unavailable_or_invalid_response") from exc

    def _validate_response(self, request: dict, response: dict) -> dict:
        if request.get("schema_version") == "showdown-environment-v1":
            if (response.get("schema_version") != request["schema_version"] or
                response.get("engine_commit") != SHOWDOWN_COMMIT or response.get("format_id") != FORMAT_ID or
                not isinstance(response.get("results"), list) or
                len(response["results"]) != len(request["requests"]) or
                not isinstance(response.get("resources"), dict) or
                any(type(response["resources"].get(key)) is not int or response["resources"][key] < 0
                    for key in ("episodes", "rss_bytes", "heap_used_bytes")) or
                any(not isinstance(row, dict) or row.get("owner") != expected.get("owner") or
                    row.get("status") not in {"ready", "saved", "closed", "rejected", "preview"}
                    for row, expected in zip(response["results"], request["requests"]))):
                raise ShowdownBridgeError("showdown_environment_response_mismatch")
            for row, expected in zip(response["results"], request["requests"]):
                if row["status"] == "rejected":
                    continue
                if (row["status"] == "preview") != (expected["operation"] == "inspect_preview"):
                    raise ShowdownBridgeError("showdown_preview_operation_mismatch")
                revision = (0 if expected["operation"] in {"reset", "restart", "import_native", "inspect_preview"} else
                            expected["revision"] + (1 if expected["operation"] == "step" else 0))
                if type(row.get("revision")) is not int or row["revision"] != revision:
                    raise ShowdownBridgeError("showdown_environment_revision_mismatch")
            return response
        if "observation_schema_version" in request and response.get("observation_schema_version") != request["observation_schema_version"]:
            raise ShowdownBridgeError("showdown_response_binding_mismatch")
        for key, value in (("schema_version", SCHEMA_VERSION), ("engine_commit", SHOWDOWN_COMMIT),
                           ("format_id", FORMAT_ID), ("session_id", request["session_id"]),
                           ("source_runtime_fingerprint", request["source_runtime_fingerprint"])):
            if response.get(key) != value:
                raise ShowdownBridgeError("showdown_response_binding_mismatch")
        if not isinstance(response.get("scenarios"), list):
            raise ShowdownBridgeError("showdown_invalid_scenarios_response")
        expected_ids = [s["scenario_id"] for s in request["scenarios"]]
        rows = response["scenarios"]
        if (any(not isinstance(row, dict) for row in rows) or
            [row.get("scenario_id") for row in rows] != expected_ids or
            any(row.get("status") not in {"simulated", "rejected"} for row in rows)):
            raise ShowdownBridgeError("showdown_invalid_scenarios_response")
        return response
