"""Small .env loader for local app configuration.

This intentionally avoids printing or logging secrets. Callers can choose
whether existing process environment variables win over values from the file.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = PROJECT_ROOT / "config" / ".env"
LEGACY_ENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv(path: str | Path | None = None, *, override: bool = False) -> None:
    """Load KEY=VALUE pairs from a local .env file if it exists."""
    env_path = Path(path) if path is not None else _default_env_path()
    if not env_path.exists() or not env_path.is_file():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or (key in os.environ and not override):
            continue
        os.environ[key] = _clean_value(value.strip())


def _clean_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _default_env_path() -> Path:
    if DEFAULT_ENV_PATH.exists():
        return DEFAULT_ENV_PATH
    return LEGACY_ENV_PATH
