from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.pokemon_stat_sample_repository import PokemonStatSampleRepository
from llm.opponent_assumptions import (
    OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K,
    build_opponent_assumptions_debug_summary,
    build_opponent_assumptions_payload,
    format_opponent_assumptions_debug_json,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a safe opponent_assumptions debug summary for one species.",
    )
    parser.add_argument(
        "--species",
        required=True,
        help="Opponent species id or slug, for example rotom-wash.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K,
        help=f"Maximum possible samples to include. Default: {OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K}.",
    )
    return parser.parse_args(argv)


def build_debug_json(*, species_id: str, top_k: int) -> str:
    assumptions = build_opponent_assumptions_payload(
        {"species_id": species_id},
        PokemonStatSampleRepository(),
        top_k=top_k,
    )
    summary = build_opponent_assumptions_debug_summary({"opponent_assumptions": assumptions})
    return format_opponent_assumptions_debug_json(summary)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(build_debug_json(species_id=args.species, top_k=args.top_k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
