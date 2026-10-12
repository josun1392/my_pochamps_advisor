"""Reproduce a native-authority M-C inventory and full-domain curriculum bank."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import gzip
from hashlib import sha256
import json
import subprocess
from time import perf_counter
from advisor.learning_resources import WindowsJob, atomic_json

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "models/showdown_mc_domain_v1"
BANK = ROOT / "models/showdown_full_domain_v7"


def native(checkout, request, timeout):
    response = subprocess.run(
        ["node", str(ROOT / "tools/showdown_bridge/full-domain.cjs"), str(checkout)],
        input=json.dumps(request),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
    )
    if response.returncode:
        raise RuntimeError(f"native_domain_failed: {response.stderr[-1800:]}")
    return json.loads(response.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--domain-output", type=Path, default=DOMAIN)
    parser.add_argument("--bank-output", type=Path, default=BANK)
    parser.add_argument("--teams", type=int, default=2048)
    parser.add_argument("--max-runtime-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 8 <= args.teams <= 4096 or not 30 <= args.max_runtime_seconds <= 600:
        parser.error("bounded counts/runtime required")
    if args.domain_output.exists() or args.bank_output.exists():
        parser.error("output already exists; preserved artifacts cannot be overwritten")
    job = WindowsJob(memory_mib=2048, cpu_percent=12.5)
    start = perf_counter()
    inventory = native(args.checkout, {"operation": "audit"}, args.max_runtime_seconds)
    catalog_process = subprocess.run(
        [
            "node",
            str(ROOT / "tools/showdown_bridge/learning-catalog.cjs"),
            str(args.checkout),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=args.max_runtime_seconds,
        check=True,
    )
    catalog = json.loads(catalog_process.stdout)
    catalog["legal_domain_version"] = inventory["schema_version"]
    # Runtime annotations are outside immutable deterministic domain content.
    raw = json.dumps(inventory, separators=(",", ":"), ensure_ascii=True).encode()
    digest = sha256(raw).hexdigest()
    compressed = gzip.compress(raw, mtime=0)
    # Coordinator-only temporary plaintext for native IPC, removed on completion.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="poke-mc-domain-") as directory:
        temporary = Path(directory) / "inventory.json"
        temporary.write_bytes(raw)
        historical = json.loads(
            (ROOT / "models/showdown_native_curriculum_v6/manifest.json").read_text()
        )["unseen_base_species"]
        bank = native(
            args.checkout,
            {
                "operation": "build",
                "inventory": str(temporary),
                "inventory_sha256": digest,
                "reserved_species": historical,
                "new_reserved_per_split": 12,
                "counts": {
                    "train": args.teams,
                    "validation": 256,
                    "test": 256,
                    "unseen": 256,
                },
            },
            max(1, args.max_runtime_seconds - (perf_counter() - start)),
        )
    args.bank_output.mkdir(parents=True)
    args.domain_output.mkdir(parents=True)
    (args.domain_output / "inventory.json.gz").write_bytes(compressed)
    atomic_json(args.domain_output / "catalog.json", catalog)
    atomic_json(
        args.domain_output / "public_dex.json",
        {
            "engine_commit": inventory["engine_commit"],
            "format_id": inventory["format_id"],
            "inventory_content_sha256": digest,
            "species": inventory["public_dex"],
        },
    )
    bankraw = json.dumps(bank, sort_keys=True, separators=(",", ":")).encode()
    packed = gzip.compress(bankraw, mtime=0)
    (args.bank_output / "teams.json.gz").write_bytes(packed)
    manifest = {k: v for k, v in bank.items() if k != "teams"}
    manifest.update(
        bank_sha256=sha256(packed).hexdigest(),
        content_sha256=sha256(bankraw).hexdigest(),
    )
    tool_sources = [
        "tools/showdown_bridge/legal-domain.cjs",
        "tools/showdown_bridge/full-domain.cjs",
        "tools/showdown_bridge/learning-catalog.cjs",
        "scripts/build_showdown_full_domain.py",
    ]
    tool_hashes = {
        name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in tool_sources
    }
    manifest["tool_source_sha256"] = tool_hashes
    atomic_json(args.bank_output / "manifest.json", manifest)
    summary = {
        "schema_version": inventory["schema_version"],
        "tool_source_sha256": tool_hashes,
        "engine_commit": inventory["engine_commit"],
        "format_id": inventory["format_id"],
        "content_sha256": digest,
        "compressed_sha256": sha256(compressed).hexdigest(),
        "public_dex_sha256": sha256(
            (args.domain_output / "public_dex.json").read_bytes()
        ).hexdigest(),
        "counts": {
            "public_catalog_species": len(catalog["species"]),
            "base_species": len(inventory["base_species"]),
            "forms": len(inventory["species"]),
            "moves": len(inventory["moves"]),
            "abilities": len(inventory["abilities"]),
            "items": len(inventory["items"]),
        },
        "wall_seconds": perf_counter() - start,
        "catalog_sha256": sha256(
            (args.domain_output / "catalog.json").read_bytes()
        ).hexdigest(),
        "resources": job.usage(),
    }
    atomic_json(args.domain_output / "manifest.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
