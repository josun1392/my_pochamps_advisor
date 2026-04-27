from __future__ import annotations

import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.parse_bulbapedia_roster import SEREBII_URL  # noqa: E402


def main() -> int:
    response = requests.get(SEREBII_URL, timeout=30)
    response.raise_for_status()
    text = response.text
    print(f"Serebii reachable: {response.status_code}")
    print(f"Page bytes: {len(text.encode('utf-8'))}")
    print("Manual cross-check source retained for roster review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
