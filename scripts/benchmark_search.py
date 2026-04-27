from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ko_mapping_loader import KoMappingLoader  # noqa: E402
from core.search_engine import SearchEngine  # noqa: E402


def main() -> int:
    loader = KoMappingLoader()
    engine = SearchEngine(loader)

    queries = ["리", "리자", "리자몽", "char", "테라", "tera"]
    for query in queries:
        start = time.perf_counter_ns()
        results = engine.search(query, limit=10)
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        print(f"{query:10s} -> {len(results):2d} hits, {elapsed_ms:.3f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
