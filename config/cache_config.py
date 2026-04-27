from __future__ import annotations

from pathlib import Path


POKEAPI_BASE = "https://pokeapi.co/api/v2"
CONCURRENT_LIMIT = 5
REQUEST_DELAY_MS = 100
MAX_RETRIES = 3
CACHE_DIR = Path("data/cache/pokemon")
POKEMON_CACHE_META = Path("data/cache/_meta.json")
POKEMON_FAILURE_LOG = Path("data/cache/_failures.log")
