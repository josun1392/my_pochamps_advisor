"""Build bounded, native-validated M-C banks with species-disjoint reservations."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import gzip
from hashlib import sha256
import json
import subprocess
from time import perf_counter
from advisor.learned_coherent_curriculum import EXTRA_UNSEEN
from advisor.learned_roster import BROAD_UNSEEN
from advisor.learning_resources import WindowsJob, atomic_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-teams", type=int, default=2048)
    parser.add_argument("--validation-teams", type=int, default=256)
    parser.add_argument("--test-teams", type=int, default=512)
    parser.add_argument("--unseen-teams", type=int, default=512)
    parser.add_argument("--fresh-unseen-species", type=int, default=20)
    parser.add_argument("--reserved-species-file", type=Path)
    parser.add_argument(
        "--curriculum-version",
        default="showdown-learning-curriculum-v6",
        choices=[
            "showdown-learning-curriculum-v6",
            "showdown-learning-curriculum-v6-fresh17",
        ],
    )
    parser.add_argument("--max-runtime-seconds", type=int, default=300)
    args = parser.parse_args()
    counts = {
        split: getattr(args, f"{split}_teams")
        for split in ("train", "validation", "test", "unseen")
    }
    if (
        any(not 8 <= n <= 4096 for n in counts.values())
        or not 30 <= args.max_runtime_seconds <= 600
    ):
        parser.error("bounded team counts/runtime required")
    args.output.mkdir(parents=True, exist_ok=False)
    job = WindowsJob(memory_mib=2048, cpu_percent=12.5)
    started = perf_counter()
    request = {
        "reserved_species": json.loads(
            args.reserved_species_file.read_text(encoding="utf-8")
        )
        if args.reserved_species_file
        else [p[0] for p in BROAD_UNSEEN + EXTRA_UNSEEN],
        "fresh_unseen_species": args.fresh_unseen_species,
        "counts": counts,
        "curriculum_version": args.curriculum_version,
    }
    script = (
        Path(__file__).resolve().parents[1]
        / "tools/showdown_bridge/learning-curriculum.cjs"
    )
    response = subprocess.run(
        ["node", str(script), str(args.checkout.resolve())],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=args.max_runtime_seconds,
        check=True,
    )
    bank = json.loads(response.stdout)
    # Static public species data is stored separately: policies never read team banks.
    public_dex = bank.pop("public_dex")
    atomic_json(
        args.output / "public_dex.json",
        {
            "engine_commit": bank["engine_commit"],
            "format_id": bank["format_id"],
            "species": public_dex,
        },
    )
    raw = json.dumps(bank, sort_keys=True, separators=(",", ":")).encode()
    compressed = gzip.compress(raw, mtime=0)
    (args.output / "teams.json.gz").write_bytes(compressed)
    manifest = {key: value for key, value in bank.items() if key != "teams"}
    manifest.update(
        bank_sha256=sha256(compressed).hexdigest(),
        content_sha256=sha256(raw).hexdigest(),
        wall_seconds=perf_counter() - started,
        resources=job.usage(),
    )
    atomic_json(args.output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "counts",
                    "attempts",
                    "legal_base_species",
                    "wall_seconds",
                    "resources",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
